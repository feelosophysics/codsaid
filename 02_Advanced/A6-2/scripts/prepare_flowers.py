"""Flowers102 미러(Parquet, 약 346MB)를 받아 데이지형 꽃 8종만 data/flowers_subset/에 풀고 원본을 지운다.

실행: uv run python scripts/prepare_flowers.py [--keep-raw]
"""
import argparse

from perfdiag.common import utf8_console
from perfdiag.vision.data import CLASS_KO, MANIFEST, build_subset, download_parquet


def main():
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-raw", action="store_true", help="원본 Parquet을 지우지 않는다")
    args = parser.parse_args()
    download_parquet()
    df = build_subset(keep_raw=args.keep_raw)
    table = df.groupby(["class", "split"]).size().unstack()[["train", "validation", "test"]]
    table.index = [f"{name} ({CLASS_KO[name]})" for name in table.index]
    print(table.to_string())
    print(f"합계 {len(df)}장 → {MANIFEST}")


if __name__ == "__main__":
    main()
