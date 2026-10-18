"""A1-1 분석의 실행 순서를 묶는 진입점이다.

A1-1 폴더에서 python -m src.run_analysis로 실행한다.
-m은 패키지 안의 모듈을 실행하라는 뜻이며, .pipeline 같은 상대 import를 지원한다.
입력 준비 → 전처리 → 피처 → 이상치 표시 → RFM → 보고서 → 보너스 순서다.
"""
import argparse
from pathlib import Path

from .pipeline import DataAnalyzer
from .report import write_report
from .sample_data import generate_sample_data


def run_analysis(data_dir, output_dir, reference_date=None, include_bonus=True,
                 customers_path=None, observation_end=None):
    """분석 단계를 순서대로 실행하고 결과 파일과 분석 객체를 만든다.

    Args:
        data_dir (str | pathlib.Path): 거래·상품·이미지 입력 폴더.
        output_dir (str | pathlib.Path): 결과를 저장할 폴더.
        reference_date (str | None): RFM 기준일. 생략하면 마지막 구매 다음 날.
        include_bonus (bool): 이미지 고급 피처·가입 코호트·Plotly도 실행할지 여부.
        customers_path (str | pathlib.Path | None): 보너스용 가입 고객 CSV 경로.
        observation_end (str | None): 코호트 데이터 수집이 끝난 날짜.

    Returns:
        DataAnalyzer: 처리된 표·RFM·audit을 보관한 객체.
            보너스 실행 시 df에 보너스 피처도 추가된다.

    Raises:
        ValueError: 데이터나 분석 옵션이 각 단계의 입력 조건에 맞지 않는 경우.
        OSError: 입력을 읽거나 결과 파일을 저장할 수 없는 경우.
    """
    data_dir = Path(data_dir)
    # 클래스 이름 뒤 ()로 객체를 만든다. 생성만으로 파일을 읽지는 않는다.
    analyzer = DataAnalyzer(data_dir / "transactions.csv")
    # 메서드(객체의 기능)를 호출하며 앞 단계의 결과를 다음 단계가 사용한다.
    # 이 순서가 전체 코드를 이해하는 지도다. 구현 세부는 pipeline.py에 있다.
    analyzer.load_data()
    analyzer.handle_missing_values()
    analyzer.engineer_features()
    analyzer.detect_outliers("shipping_days")
    analyzer.detect_outliers("unit_price")
    analyzer.calculate_rfm(reference_date=reference_date)
    # 필수 보고서를 먼저 저장해 22컬럼 결과와 필수 차트 6종을 만든다.
    # 보너스는 이후 df에 피처를 더하고 별도의 bonus 폴더에 저장한다.
    write_report(analyzer, output_dir)
    if include_bonus:
        # 필요한 경우에 import한다. 앞의 .은 같은 src 패키지 안이라는 뜻이다.
        from .bonus import write_bonus
        analyzer.audit['bonus'] = write_bonus(analyzer, output_dir, customers_path, observation_end)
    return analyzer


def main():
    """터미널 옵션을 읽고 입력 생성 여부와 분석 실행을 결정한다.

    --generate-sample은 지정 폴더의 샘플을 다시 저장한다.
    --skip-bonus는 가입일 자료 없이 필수 분석만 실행할 때 사용한다.
    """
    # argparse는 터미널의 --이름 값을 Python에서 쓸 수 있는 값으로 바꾼다.
    parser = argparse.ArgumentParser(description="A1-1 ecommerce analysis")
    parser.add_argument("--data-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    # store_true는 옵션을 적으면 True, 생략하면 False가 되는 스위치다.
    parser.add_argument("--generate-sample", action="store_true", help="Create/replace synthetic input files")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reference-date", help="YYYY-MM-DD; default latest purchase + one day")
    parser.add_argument('--skip-bonus', action='store_true', help='Run required analysis without signup cohorts or Plotly')
    parser.add_argument('--customers-path', type=Path, help='Customer table with customer_id and signup_date')
    parser.add_argument('--observation-end', help='Last fully captured date for cohort observation, YYYY-MM-DD')
    # type=Path/int는 문자열 입력을 경로/정수로 바꾼다. default는 생략 시 값이다.
    args = parser.parse_args()
    if args.generate_sample:
        generate_sample_data(args.data_dir, args.seed)
    # not args.skip_bonus는 '보너스를 건너뛰지 않을 때 실행한다'는 뜻이다.
    analyzer = run_analysis(args.data_dir, args.output_dir, args.reference_date,
                            not args.skip_bonus, args.customers_path, args.observation_end)
    print(analyzer.segment_summary().round(2).to_string())
    print(f"Saved six required charts, tables and interpretations to {args.output_dir.resolve()}")
    if not args.skip_bonus:
        print(f"Saved three bonus results to {(args.output_dir / 'bonus').resolve()}")


if __name__ == "__main__":
    # 직접 실행할 때만 main을 호출한다. 다른 모듈에서 import하면 분석을 시작하지 않는다.
    main()
