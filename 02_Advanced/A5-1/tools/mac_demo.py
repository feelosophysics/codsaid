"""Mac 시연용 libomp 탐색·실행 도구. 시스템과 패키지 파일은 수정하지 않는다."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import struct
import sys
import sysconfig


ROOT = Path(__file__).resolve().parents[1]
BUNDLED_LIB = ROOT / "environment/mac-intel-openmp/libomp.dylib"
BUNDLED_SHA256 = "1194e8e2a2f821844e2abe1d8446d7178051436086ae84f4e02036b124bed5fa"
# 두 패키지를 함께 사용해 OpenMP 충돌도 검사한다. 중복 런타임 오류를
# 숨기는 KMP_DUPLICATE_LIB_OK 옵션은 사용하지 않는다.
PROBE = """
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import xgboost
X = np.array([[0., 0.], [0., 1.], [1., 0.], [1., 1.]] * 4)
y = np.array([0, 0, 1, 1] * 4)
RandomForestClassifier(n_estimators=2, n_jobs=1, random_state=42).fit(X, y).predict(X)
xgboost.XGBClassifier(n_estimators=2, max_depth=1, n_jobs=1).fit(X, y).predict(X)
print('XGBoost + scikit-learn 학습 검사 OK:', xgboost.__version__)
"""


def verified_bundled_library() -> Path | None:
    """Intel Mac용으로 고정한 런타임의 무결성과 실행 조건을 검사한다."""
    if platform.machine() != "x86_64":
        return None
    if not BUNDLED_LIB.is_file():
        raise RuntimeError(
            f"시연용 런타임이 없습니다: {BUNDLED_LIB}\n"
            "environment/mac-intel-openmp 폴더까지 포함한 최신 A5-1을 가져오세요."
        )
    data = BUNDLED_LIB.read_bytes()
    if hashlib.sha256(data).hexdigest() != BUNDLED_SHA256:
        raise RuntimeError("시연용 libomp의 SHA-256이 다릅니다. 최신 원본을 다시 가져오세요.")
    if struct.unpack_from("<II", data) != (0xFEEDFACF, 0x01000007):
        raise RuntimeError("시연용 libomp가 Intel 64비트 Mach-O 파일이 아닙니다.")
    version = platform.mac_ver()[0]
    if not version or int(version.split(".")[0]) < 11:
        raise RuntimeError(f"동봉 런타임은 macOS 11 이상이 필요합니다. 현재: {version}")
    return BUNDLED_LIB


def with_library(env: dict[str, str], library: Path) -> dict[str, str]:
    candidate_env = env.copy()
    previous = env.get("DYLD_LIBRARY_PATH", "")
    candidate_env["DYLD_LIBRARY_PATH"] = str(library.parent) + (
        os.pathsep + previous if previous else ""
    )
    return candidate_env


def install_notebook_kernel(env: dict[str, str]) -> str:
    """이 컴퓨터의 사용자에게 같은 Python과 libomp를 쓰는 커널을 등록한다."""
    from ipykernel.kernelspec import install

    # 실행 위치가 notebooks/여도 프로젝트의 src를 불러올 수 있게 한다.
    kernel_env = {"PYTHONUTF8": "1", "PYTHONPATH": str(ROOT)}
    for key in ("DYLD_LIBRARY_PATH",):
        if key in env:
            kernel_env[key] = env[key]
    return install(
        user=True,
        kernel_name="a5-1-mac-demo",
        display_name="A5-1 Mac (uv + libomp)",
        env=kernel_env,
    )


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
    # Intel 시연에서는 검증된 런타임을 우선한다. sklearn의 기존 파일은
    # 필요한 심벌이 없어 실패한 것으로 현장 로그에서 확인했다.
    bundled = verified_bundled_library()
    if bundled is not None:
        print(f"검증된 Intel Mac libomp 23.1.3 연결: {bundled}", flush=True)
        candidate_env = with_library(env, bundled)
        result = probe(candidate_env)
        if result.returncode == 0:
            print(result.stdout.strip(), flush=True)
            return candidate_env
        print("동봉 런타임의 실제 학습 검사에 실패했습니다.", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return None
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
        candidate_env = with_library(env, library)
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true", help="로딩 확인만 하고 종료")
    mode.add_argument("--install-kernel", action="store_true", help="Mac 노트북용 사용자 커널 등록")
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
    if args.install_kernel:
        location = install_notebook_kernel(env)
        print(f"노트북 커널 등록 완료: {location}", flush=True)
        print("노트북에서 'A5-1 Mac (uv + libomp)' 커널을 선택하고 재시작하세요.", flush=True)
        print("폴더를 이동하거나 새 Mac에 클론하면 이 명령을 다시 실행하세요.", flush=True)
        return 0
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
    except (subprocess.SubprocessError, OSError, RuntimeError) as exc:
        print(f"시연 실행 오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
