"""Sequential, reversible migration of the existing Advanced mission environments.

Run one mission at a time with an installed Python 3.12.13. Locked restoration is
offline first; --allow-download permits cache misses without package upgrades.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
VERSION = "3.12.13"
RUN = "2026-10-20-python31213"
PROJECTS = ("A1-1", "A2-1", "A3-1", "A3-2", "A4-1", "A4-2", "A5-1", "A5-2", "A6-1", "A6-2")


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", choices=PROJECTS)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if args.attempt < 1:
        parser.error("attempt must be positive")
    suffix = "" if args.attempt == 1 else f"-attempt{args.attempt}"
    project = REPO / "02_Advanced" / args.project
    venv = project / ".venv"
    evidence = project / "environment" / (RUN + suffix)
    temp = WORKSPACE / ".newlearn" / "tmp" / "learning-python31213" / (args.project + suffix)
    backup = temp / "previous-runtime"
    for target, boundary in ((project, REPO), (venv, project), (temp, WORKSPACE / ".newlearn" / "tmp")):
        if not target.resolve().is_relative_to(boundary.resolve()):
            raise ValueError(f"Path escapes workspace: {target}")
        cursor = target
        while cursor != boundary:
            if cursor.is_symlink() or cursor.is_junction():
                raise ValueError(f"Linked path disallowed: {cursor}")
            cursor = cursor.parent
    if evidence.exists() or temp.exists():
        raise FileExistsError("A prior attempt exists; inspect it before retrying")
    if not (venv / "pyvenv.cfg").is_file():
        raise FileNotFoundError("Existing environment required")
    evidence.mkdir(parents=True)
    temp.mkdir(parents=True)
    env = {**os.environ, "UV_CACHE_DIR": str(WORKSPACE / ".newlearn/tmp/uv-cache"),
           "UV_NO_PROGRESS": "1", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "MPLBACKEND": "Agg", "MPLCONFIGDIR": str(temp / "matplotlib"),
           "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
           "NUMEXPR_NUM_THREADS": "2", "A5_N_JOBS": "2"}
    uv = str(Path.home() / ".local/bin/uv.exe")
    report = {"project": args.project, "target_python": VERSION, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "steps": []}

    def save():
        (evidence / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(label, command, timeout=600):
        started = time.monotonic()
        completed = subprocess.run(command, cwd=project, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=timeout)
        (evidence / (label + ".log")).write_text(completed.stdout, encoding="utf-8")
        report["steps"].append({"label": label, "command": command, "exit_code": completed.returncode,
                                "seconds": round(time.monotonic() - started, 3)})
        save()
        print(f"{args.project}: {label}: exit {completed.returncode} ({time.monotonic()-started:.1f}s)", flush=True)
        if completed.returncode:
            print(completed.stdout[-6000:], flush=True)
            raise RuntimeError(f"{label} failed")
        return completed.stdout

    def freeze(label):
        text = run(label, [uv, "pip", "freeze", "--offline", "--python", str(venv / "Scripts/python.exe")])
        # uv writes the environment banner to stderr; retain only requirements.
        return sorted(line for line in text.splitlines() if line and not line.startswith("Using "))

    pin = project / ".python-version"
    pin_before = pin.read_bytes()
    config_before = (venv / "pyvenv.cfg").read_text(encoding="utf-8")
    (evidence / "pyvenv-before.cfg").write_text(config_before, encoding="utf-8")
    (evidence / "python-version-before.txt").write_bytes(pin_before)
    inputs = {name: digest(project / name) for name in ("pyproject.toml", "uv.lock")}
    report["input_hashes_before"] = inputs
    before = freeze("packages-before")
    (evidence / "requirements-before.txt").write_text("\n".join(before) + "\n", encoding="utf-8")
    migrated = False
    pin_changed = False
    try:
        already_pinned = "version_info = 3.12.13" in config_before and "cpython-3.12.13-" in config_before
        if not already_pinned:
            venv.rename(backup)
            migrated = True
            pin.write_text(VERSION + "\n", encoding="utf-8")
            pin_changed = True
            run("create", [uv, "venv", "--offline", "--no-python-downloads", "--python", VERSION, str(venv)])
            try:
                run("restore", [uv, "sync", "--locked", "--offline", "--no-python-downloads", "--python", VERSION])
            except RuntimeError:
                if not args.allow_download or "Network connectivity is disabled" not in (evidence / "restore.log").read_text(encoding="utf-8"):
                    raise
                run("restore-download", [uv, "sync", "--locked", "--no-python-downloads", "--python", VERSION])
        elif pin.read_text(encoding="utf-8").strip() != VERSION:
            pin.write_text(VERSION + "\n", encoding="utf-8")
            pin_changed = True
        after = freeze("packages-after")
        (evidence / "requirements-after.txt").write_text("\n".join(after) + "\n", encoding="utf-8")
        if before != after:
            report["package_difference"] = {"removed": sorted(set(before)-set(after)), "added": sorted(set(after)-set(before))}
            raise RuntimeError("Installed package versions changed")
        run("dependency-check", [uv, "pip", "check", "--python", str(venv / "Scripts/python.exe")])
        prefix = [uv, "run", "--offline", "--no-sync", "--no-python-downloads", "python", "-B"]
        run("python", prefix + ["-c", "import sys,json; assert sys.version_info[:3]==(3,12,13); assert 'cpython-3.12.13-' in sys.base_prefix; print(json.dumps(dict(version=sys.version,executable=sys.executable,base=sys.base_prefix)))"])
        tests = ["-m", "unittest", "discover", "-s", "tests"]
        if args.project == "A4-2":
            tests += ["-t", "."]
        run("tests", prefix + tests + ["-v"])
        run("runtime", prefix + [str(REPO / "tools/verify_python_runtime.py"), args.project, str(temp / "runtime-output")])
        smoke = temp / "runtime-output/result.json"
        report["runtime"] = json.loads(smoke.read_text(encoding="utf-8"))
        config = (venv / "pyvenv.cfg").read_text(encoding="utf-8")
        if "version_info = 3.12.13" not in config or "cpython-3.12.13-" not in config:
            raise RuntimeError("Environment is not pinned to the patch installation")
        if inputs != {name: digest(project / name) for name in inputs}:
            raise RuntimeError("Project requirements or lockfile changed")
        (evidence / "pyvenv-after.cfg").write_text(config, encoding="utf-8")
        report.update(status="passed", recreated=migrated, package_count=len(after), packages_identical=True,
                      lockfile_unchanged=True, executable_bytes=(venv / "Scripts/python.exe").stat().st_size,
                      executable_sha256=digest(venv / "Scripts/python.exe"), completed_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        save()
        print(json.dumps({k: report[k] for k in ("project", "status", "recreated", "package_count")}), flush=True)
    except BaseException as error:
        if migrated:
            if venv.exists():
                venv.rename(temp / "failed-runtime")
            backup.rename(venv)
        if pin_changed:
            pin.write_bytes(pin_before)
        report.update(status="failed", restored_previous_environment=migrated, error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
