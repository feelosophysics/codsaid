"""Run from repository root: python -m src.run_analysis --generate-sample."""
import argparse
from pathlib import Path

from .pipeline import DataAnalyzer
from .report import write_report
from .sample_data import generate_sample_data


def run_analysis(data_dir, output_dir, reference_date=None, include_bonus=True,
                 customers_path=None, observation_end=None):
    data_dir = Path(data_dir)
    analyzer = DataAnalyzer(data_dir / "transactions.csv")
    analyzer.load_data()
    analyzer.handle_missing_values()
    analyzer.engineer_features()
    analyzer.detect_outliers("shipping_days")
    analyzer.detect_outliers("unit_price")
    analyzer.calculate_rfm(reference_date=reference_date)
    write_report(analyzer, output_dir)
    if include_bonus:
        from .bonus import write_bonus
        analyzer.audit['bonus'] = write_bonus(analyzer, output_dir, customers_path, observation_end)
    return analyzer


def main():
    parser = argparse.ArgumentParser(description="A1-1 ecommerce analysis")
    parser.add_argument("--data-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--generate-sample", action="store_true", help="Create/replace synthetic input files")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reference-date", help="YYYY-MM-DD; default latest purchase + one day")
    parser.add_argument('--skip-bonus', action='store_true', help='Run required analysis without signup cohorts or Plotly')
    parser.add_argument('--customers-path', type=Path, help='Customer table with customer_id and signup_date')
    parser.add_argument('--observation-end', help='Last fully captured date for cohort observation, YYYY-MM-DD')
    args = parser.parse_args()
    if args.generate_sample:
        generate_sample_data(args.data_dir, args.seed)
    analyzer = run_analysis(args.data_dir, args.output_dir, args.reference_date,
                            not args.skip_bonus, args.customers_path, args.observation_end)
    print(analyzer.segment_summary().round(2).to_string())
    print(f"Saved six required charts, tables and interpretations to {args.output_dir.resolve()}")
    if not args.skip_bonus:
        print(f"Saved three bonus results to {(args.output_dir / 'bonus').resolve()}")


if __name__ == "__main__":
    main()
