"""전체 파이프라인을 미션 순서대로 실행한다.

  0 데이터     시계열 CSV(저장소에 포함, 없을 때만 받기) · 꽃 이미지(없을 때만 받기)
  1 베이스라인  ts_baselines        ← 딥러닝보다 먼저
  2 딥러닝     ts_deep · vision_transfer
  3 진단·분석  ts_leakage · 그림 · 태깅 도구 · 오차 분석
  4 개선       vision_improve
  5 보너스     bonus_hparam_search · bonus_attention
  6 문서       리포트 생성

오차 분석은 annotations/error_tags.csv(사람이 검수한 태그)가 있어야 진행한다. 없으면 태깅 도구까지 만들고 멈춘다.
CPU 6스레드 기준 약 2시간 걸린다. --skip-bonus로 보너스를 건너뛸 수 있다.

실행: uv run python scripts/run_all.py
"""
import argparse
import subprocess
import sys
import time

from perfdiag.common import FLOWERS, ROOT, utf8_console
from perfdiag.timeseries.data import SERIES

STEPS = [
    ("ts_baselines", ["scripts/ts_baselines.py"]),
    ("ts_deep", ["scripts/ts_deep.py"]),
    ("ts_leakage", ["scripts/ts_leakage.py"]),
    ("ts_figures", ["scripts/ts_figures.py"]),
    ("vision_transfer", ["scripts/vision_transfer.py"]),
    ("vision_figures", ["scripts/vision_figures.py"]),
    ("tagging_page", ["tools/build_tagging_page.py"]),
    ("vision_error_analysis", ["scripts/vision_error_analysis.py"]),
    ("vision_improve", ["scripts/vision_improve.py"]),
    ("bonus_hparam_search", ["scripts/bonus_hparam_search.py"]),
    ("bonus_attention", ["scripts/bonus_attention.py"]),
    ("bonus_figures", ["scripts/bonus_figures.py"]),
    ("reports", ["tools/build_reports.py"]),
]


def call(args):
    start = time.perf_counter()
    print(f"\n▶ {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)
    print(f"  ({time.perf_counter() - start:.0f}초)", flush=True)


def main():
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-bonus", action="store_true")
    args = parser.parse_args()
    if not all(cfg.csv.exists() for cfg in SERIES.values()):
        call(["scripts/fetch_timeseries.py"])
    if not (FLOWERS / "manifest.csv").exists():
        call(["scripts/prepare_flowers.py"])
    for name, step in STEPS:
        if args.skip_bonus and name.startswith("bonus"):
            continue
        if name == "vision_error_analysis" and not (ROOT / "annotations" / "error_tags.csv").exists():
            print("\nannotations/error_tags.csv가 없어 멈춘다. annotations/tagging.html에서 태그를 달고 저장한 뒤 다시 실행한다.")
            return
        call(step)


if __name__ == "__main__":
    main()
