"""모든 검증·실험을 순서대로 실행한다: 구현 → 검증 → 실험 → 보너스.

실행: uv run python scripts/run_all.py [--skip-bonus]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
STEPS = [
    ("MNIST 내려받기", ["download_mnist.py"]),
    ("Gradient Check", ["gradient_check.py"]),
    ("XOR 학습 (He)", ["train_xor.py", "--init", "he"]),
    ("XOR 학습 (Zero, 실패 재현)", ["train_xor.py", "--init", "zero", "--epochs", "50"]),
    ("초기화 실험", ["init_experiment.py"]),
    ("MNIST 1 epoch", ["train_mnist.py"]),
]
BONUS = [
    ("보너스: 활성화 함수", ["bonus_activations.py"]),
    ("보너스: Dropout·L2", ["bonus_regularization.py"]),
]
EXPECTED_FAILURE = {"XOR 학습 (Zero, 실패 재현)"}  # 실패하는 것이 정상인 단계


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔(cp949)에서 한글·기호 출력
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-bonus", action="store_true")
    args = parser.parse_args()
    steps = STEPS + ([] if args.skip_bonus else BONUS)
    results = []
    for title, command in steps:
        print(f"\n{'=' * 70}\n▶ {title}: {' '.join(command)}\n{'=' * 70}", flush=True)
        start = time.perf_counter()
        code = subprocess.call([sys.executable, str(SCRIPTS / command[0]), *command[1:]])
        ok = (code != 0) if title in EXPECTED_FAILURE else (code == 0)
        results.append((title, ok, code, time.perf_counter() - start))
    print(f"\n{'=' * 70}\n요약")
    for title, ok, code, seconds in results:
        note = " (실패가 기대 결과)" if title in EXPECTED_FAILURE else ""
        print(f"  {'OK  ' if ok else 'FAIL'} {title:<28} exit={code} {seconds:6.1f}초{note}")
    return 0 if all(ok for _, ok, _, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
