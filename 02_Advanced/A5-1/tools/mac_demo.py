"""Mac 시연용 libomp 탐색·실행 도구. 시스템과 패키지 파일은 수정하지 않는다."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig


ROOT = Path(__file__).resolve().parents[1]
PROBE = "import xgboost; print('XGBoost OK:', xgboost.__version__)"


def library_candidates() -> list[Path]:
    """현재 Python 환경을 우선하고, 알려진 로컬 설치 위치만 탐색한다."""
    sites = dict.fromkeys(
        Path(sysconfig.get_path(key)) for key in ("purelib", "platlib")
    )
    paths: list[Path] = []
    for site in sites:
        for pattern in (
            "sklearn/.dylibs/libomp.dylib",
            "scikit_learn.libs/libomp.dylib",
            "xgboost/lib/libomp.dylib",
            "*/.dylibs/libomp.dylib",
        ):
            paths.extend(sorted(site.glob(pattern)))
    paths.extend([
        Path(sys.prefix) / "lib/libomp.dylib",
        Path("/usr/local/opt/libomp/lib/libomp.dylib"),
        Path("/opt/homebrew/opt/libomp/lib/libomp.dylib"),
        Path("/usr/local/lib/libomp.dylib"),
        Path.home() / ".local/lib/libomp.dylib",
        Path.home() / "lib/libomp.dylib",
    ])
    return list(dict.fromkeys(path.resolve() for path in paths if path.is_file()))


def probe(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """별도 프로세스에서 실제 로딩을 검사하여 실패한 라이브러리를 남기지 않는다."""
    return subprocess.run(
        [sys.executable, "-c", PROBE], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=60,
    )


def find_working_environment() -> dict[str, str] | None:
    env = os.environ.copy()
    result = probe(env)
    if result.returncode == 0:
        print(result.stdout.strip(), flush=True)
        print("현재 설정으로 실행 가능합니다. 추가 연결은 필요 없습니다.", flush=True)
        return env
    # libomp 이외의 오류를 경로 변경으로 덮지 않는다.
    if "libomp" not in result.stderr:
        print(result.stderr, file=sys.stderr)
        return None

    candidates = library_candidates()
    if not candidates:
        print("사용 가능한 위치에서 libomp.dylib를 찾지 못했습니다.", file=sys.stderr)
    for library in candidates:
        print(f"libomp 검사: {library}", flush=True)
        candidate_env = env.copy()
        previous = env.get("DYLD_LIBRARY_PATH", "")
        candidate_env["DYLD_LIBRARY_PATH"] = str(library.parent) + (
            os.pathsep + previous if previous else ""
        )
        result = probe(candidate_env)
        if result.returncode == 0:
            print(result.stdout.strip(), flush=True)
            print(f"이번 실행에 연결한 라이브러리 폴더: {library.parent}", flush=True)
            return candidate_env
        print("이 후보는 불러오지 못했습니다.", flush=True)

    print("XGBoost 로딩에 실패했습니다. 아래 오류를 전달해 주세요.", file=sys.stderr)
    print(result.stderr, file=sys.stderr)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="로딩 확인만 하고 종료")
    args = parser.parse_args()
    if sys.platform != "darwin":
        print("이 도구는 macOS 전용입니다.", file=sys.stderr)
        return 1
    print(f"Python: {sys.executable}\nCPU: {platform.machine()}", flush=True)
    env = find_working_environment()
    if env is None:
        return 1
    if args.check_only:
        return 0
    # 기존 입력 데이터가 있으면 재생성하지 않는다.
    if not (ROOT / "finance_data.csv").exists():
        print("시연에 필요한 합성 데이터를 생성합니다.", flush=True)
        subprocess.run([sys.executable, "data_gen.py"], cwd=ROOT, env=env, check=True)
    output = ROOT / "results/mac-demo"
    print(f"분석을 시작합니다. 결과 저장 위치: {output}", flush=True)
    print("전체 모델 비교에는 시간이 걸립니다. 중단하려면 Ctrl+C를 누르세요.", flush=True)
    subprocess.run(
        [sys.executable, "-u", "-m", "src.run_all", "--output", str(output)],
        cwd=ROOT, env=env, check=True,
    )
    print(f"시연 완료. 보고서: {output / 'report.md'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n사용자가 실행을 중단했습니다.", file=sys.stderr)
        raise SystemExit(130)
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"시연 실행 오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
