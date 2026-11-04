"""AAPL 일봉(yfinance)과 서울 일별 기상(Open-Meteo)을 내려받아 data/timeseries/에 CSV로 저장한다.

저장한 CSV를 git에 넣어 두므로 보통은 다시 실행할 필요가 없다. 인터넷이 없어도 같은 숫자를 재현한다.
다시 받으면 공급자의 사후 수정 때문에 값이 조금 달라질 수 있다.
"""
import argparse

from perfdiag.common import TIMESERIES, utf8_console
from perfdiag.timeseries.data import SERIES, fetch_aapl, fetch_seoul_weather


def main():
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="이미 있어도 다시 내려받는다")
    args = parser.parse_args()
    TIMESERIES.mkdir(parents=True, exist_ok=True)
    for name, fetch in (("aapl", fetch_aapl), ("seoul", fetch_seoul_weather)):
        path = SERIES[name].csv
        if path.exists() and not args.force:
            print(f"있음: {path.name} (다시 받으려면 --force)")
            continue
        df = fetch()
        df.to_csv(path, float_format="%.6f", lineterminator="\n")
        print(f"저장: {path.name}  {len(df)}행  {df.index[0]} ~ {df.index[-1]}")


if __name__ == "__main__":
    main()
