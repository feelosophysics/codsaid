"""Run from repository root: python -m src.run_analysis --generate-sample."""
import argparse
from pathlib import Path

from .pipeline import DataAnalyzer
from .report import write_report
from .sample_data import generate_sample_data


def run_analysis(data_dir, output_dir, reference_date=None):
    data_dir = Path(data_dir)
    analyzer = DataAnalyzer(data_dir / "transactions.csv")
    analyzer.load_data()
    analyzer.handle_missing_values()
    analyzer.engineer_features()
    analyzer.detect_outliers("shipping_days")
    analyzer.detect_outliers("unit_price")
    analyzer.calculate_rfm(reference_date=reference_date)
    write_report(analyzer, output_dir)
    return analyzer


def main():
    parser = argparse.ArgumentParser(description="A1-1 ecommerce analysis")
    parser.add_argument("--data-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--generate-sample", action="store_true", help="Create/replace synthetic input files")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reference-date", help="YYYY-MM-DD; default latest purchase + one day")
    args = parser.parse_args()
    if args.generate_sample:
        generate_sample_data(args.data_dir, args.seed)
    analyzer = run_analysis(args.data_dir, args.output_dir, args.reference_date)
    print(analyzer.segment_summary().round(2).to_string())
    print(f"Saved six charts, tables, audit and interpretations to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
