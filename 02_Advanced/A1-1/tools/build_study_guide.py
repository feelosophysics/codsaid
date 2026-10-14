"""Build an offline HTML guide from exact source excerpts and verified calculations."""
import ast
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from src.pipeline import DataAnalyzer, iqr_bounds

STUDY = ROOT / "study"
SOURCE_FILES = ["src/run_analysis.py", "src/pipeline.py", "src/sample_data.py", "src/report.py", "tests/test_pipeline.py",
                "src/bonus.py", "tests/test_bonus.py"]
EXCERPTS = {
    "flow": ("src/run_analysis.py", "def run_analysis(", "    return analyzer"),
    "state": ("src/pipeline.py", "    def __init__(", "        self.audit = {}"),
    "join": ("src/pipeline.py", "        overlap =", "        self.images = np.load"),
    "checks": ("src/pipeline.py", "        comparable =", "        overlap ="),
    "fill": ("src/pipeline.py", "            global_value =", "            changes[column] ="),
    "grain": ("src/pipeline.py", "        product_counts =", "        line_counts ="),
    "image": ("src/pipeline.py", "        axes =", "        self.df[\"name_word_count\"] ="),
    "iqr": ("src/pipeline.py", "def iqr_bounds(", "    return float(q1"),
    "flag": ("src/pipeline.py", "    def detect_outliers(", "        return self.df.loc[flag].copy()"),
    "treat": ("src/pipeline.py", "    def treat_outliers(", "        return values.loc[values.between"),
    "eligible": ("src/pipeline.py", "        valid =", "        purchases[date_col] = dates"),
    "aggregate": ("src/pipeline.py", "        grouped = purchases.groupby", "        result[\"recency\"] ="),
    "score": ("src/pipeline.py", "        for variable, ascending, score in", "        result[\"rfm_score\"] ="),
    "segment": ("src/pipeline.py", "        vip_cutoff =", '                                       ["Inactive", "New", "VIP", "Loyal"], default="Regular")'),
    "summary": ("src/pipeline.py", "    def segment_summary(", "        return summary"),
    "sample": ("src/sample_data.py", "    # Broadcasting constructs", "    images = np.clip"),
    "test": ("tests/test_pipeline.py", "    def test_rfm_counts_orders_not_lines", '        self.assertEqual(rfm.loc["C", "segment"], "New")'),
    "chart": ("src/report.py", '    valid = df.customer_id', '    monthly = monthly.reindex'),
}


def digest(data, text=False):
    # Git can change LF/CRLF at checkout. Ignore that representation difference
    # for UTF-8 text, while preserving exact binary integrity for images/arrays.
    if text:
        data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def calculations(analyzer):
    records = [
        {"customer_id": "A", "order_id": "O1", "order_date": "2026-10-01", "amount": 20000},
        {"customer_id": "A", "order_id": "O1", "order_date": "2026-10-01", "amount": 10000},
        {"customer_id": "A", "order_id": "O2", "order_date": "2026-10-08", "amount": 20000},
        {"customer_id": "B", "order_id": "O3", "order_date": "2026-09-01", "amount": 100000},
        {"customer_id": "C", "order_id": "O4", "order_date": "2026-10-09", "amount": 5000},
    ]
    tiny = pd.DataFrame(records)
    tiny["order_date"] = pd.to_datetime(tiny.order_date)
    tiny["quantity"] = 1
    tiny["unit_price"] = tiny.amount
    demo = DataAnalyzer(ROOT / "data/sample/transactions.csv")
    demo.df = tiny
    cases = []
    for reference in ["2026-10-10", "2026-10-11", "2026-11-10"]:
        rfm = demo.calculate_rfm(reference_date=reference)
        cases.append({"reference": reference, "expected": rfm.reset_index().to_dict(orient="records")})
    configs = []
    for recent, inactive, loyal in [(30, 90, 4), (7, 90, 4), (30, 180, 4), (30, 90, 8)]:
        result = analyzer.calculate_rfm(recent_days=recent, inactive_days=inactive, loyal_orders=loyal)
        configs.append({"recent": recent, "inactive": inactive, "loyal": loyal,
                        "expected": result.segment.value_counts().to_dict()})
    analyzer.calculate_rfm()
    iqrs = []
    for high, threshold in [(100, 1.5), (6, 1.5), (100, 0.5), (4, 3.0)]:
        values = pd.Series([1, 2, 3, 4, high])
        lower, upper = iqr_bounds(values, threshold)
        iqrs.append({"high": high, "threshold": threshold, "lower": lower, "upper": upper,
                     "flagged": ((values < lower) | (values > upper)).to_list(),
                     "clipped": values.clip(lower, upper).to_list()})
    images = []
    for brightness, contrast, pattern in [(20, 1, "gradient"), (50, 0, "uniform"), (180, 2, "gradient")]:
        pixels = np.clip(brightness + np.array([0, 20, 40, 60]) * (contrast if pattern == "gradient" else 0), 0, 255)
        batch = np.repeat(pixels, 3).reshape(1, 2, 2, 3)
        images.append({"brightness": brightness, "contrast": contrast, "pattern": pattern,
                       "pixels": pixels.to_list() if hasattr(pixels, "to_list") else pixels.tolist(),
                       "mean": float(batch.mean(axis=(1, 2, 3))[0]),
                       "std": float(batch.std(axis=(1, 2, 3))[0])})
    imputation = []
    for repeat in [1, 3, 6]:
        for strategy in ["median", "mean"]:
            products = pd.DataFrame({"category": ["Home", "Home", "Home"], "price": [10., 40., np.nan]})
            DataAnalyzer._fill_by_group(products, ["price"], "category", strategy)
            weighted = pd.Series([10.] * repeat + [40.])
            imputation.append({"repeat": repeat, "strategy": strategy,
                               "correct": float(products.loc[2, "price"]),
                               "weighted": float(getattr(weighted, strategy)())})
    return {"tiny_records": records, "tiny_cases": cases, "segment_cases": configs,
            "iqr_cases": iqrs, "image_cases": images, "imputation_cases": imputation}


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    sources, manifest = {}, {"date": datetime.now(timezone(timedelta(hours=9))).date().isoformat(), "mission": "A1-1",
                            "hash_mode": "UTF-8 text: CRLF normalized to LF; binary: exact bytes",
                            "files": {}, "excerpts": {}}
    for file in SOURCE_FILES:
        data = (ROOT / file).read_bytes()
        text = data.decode("utf-8").replace("\r\n", "\n")
        symbols = [{"name": node.name, "line": node.lineno} for node in ast.walk(ast.parse(text))
                   if isinstance(node, (ast.ClassDef, ast.FunctionDef))]
        sources[file] = {"text": text, "symbols": sorted(symbols, key=lambda item: item["line"]),
                         "sha256": digest(data, text=True)}
        manifest["files"][file] = digest(data, text=True)
    template = (STUDY / "a1-1.template.html").read_text(encoding="utf-8")
    for name, (file, begin, end) in EXCERPTS.items():
        lines = sources[file]["text"].splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith(begin))
        finish = next(i for i, line in enumerate(lines[start:], start=start) if line.startswith(end))
        snippet = "\n".join(lines[start:finish + 1])
        manifest["excerpts"][name] = {"file": file, "start": start + 1, "end": finish + 1, "text": snippet}
        rendered = (f'<figure class="code-block" data-excerpt="{name}"><figcaption>'
                    f'<span>{file} · L{start + 1}–L{finish + 1}</span>'
                    f'<button type="button" class="source-link" data-file="{file}" data-line="{start + 1}">전체 코드에서 보기 ↗</button>'
                    '</figcaption><pre><code>' + "\n".join(
                        f'<span class="code-line"><span class="line-num" aria-hidden="true">{i + 1}</span><span>{html.escape(lines[i])}</span></span>'
                        for i in range(start, finish + 1)) + '</code></pre></figure>')
        template = template.replace(f"@@CODE:{name}@@", rendered)
    analyzer = DataAnalyzer(ROOT / "data/sample/transactions.csv")
    analyzer.load_data()
    analyzer.handle_missing_values()
    analyzer.engineer_features()
    analyzer.calculate_rfm()
    evidence = calculations(analyzer)
    dataset = {"sources": sources, "rfm": analyzer.rfm.reset_index().to_dict(orient="records"),
               "tiny": evidence["tiny_records"], "vip_cutoff": analyzer.audit["rfm"]["vip_monetary_cutoff"]}
    embedded = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    template = template.replace("@@DATA@@", embedded)
    bonus = ROOT / 'results/bonus'
    rates = pd.read_csv(bonus / 'cohort_retention.csv', index_col=0)
    template = template.replace('@@COHORT_TABLE@@', rates.map(lambda x: '미관측' if pd.isna(x) else f'{x:.0%}').to_html())
    template = template.replace('@@BONUS_RFM@@', html.escape((bonus / 'rfm_interactive.html').read_text(encoding='utf-8'), quote=True))
    for name in ['image_features.png', 'cohort_retention.png']:
        image = bonus / name
        template = template.replace(f'@@BONUS_IMAGE:{image.stem}@@', 'data:image/png;base64,' + base64.b64encode(image.read_bytes()).decode('ascii'))
        manifest['files'][image.relative_to(ROOT).as_posix()] = digest(image.read_bytes())
    for name in ['image_features.csv', 'cohort_sizes.csv', 'cohort_counts.csv', 'cohort_retention.csv', 'summary.json', 'rfm_interactive.html']:
        file = bonus / name
        manifest['files'][file.relative_to(ROOT).as_posix()] = digest(file.read_bytes(), text=True)
    for image in (ROOT / "results/figures").glob("*.png"):
        template = template.replace(f"@@IMAGE:{image.stem}@@", "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii"))
        manifest["files"][image.relative_to(ROOT).as_posix()] = digest(image.read_bytes())
    for file in ["data/sample/transactions.csv", "data/sample/products.csv", "data/sample/images.npy", "data/sample/customers.csv",
                 "results/rfm_customers.csv", "results/segment_summary.csv", "results/audit.json"]:
        manifest["files"][file] = digest((ROOT / file).read_bytes(), text=Path(file).suffix != ".npy")
    if re.search(r"@@[A-Z]+[:@]", template):
        raise RuntimeError("Unresolved template placeholders")
    (STUDY / "a1-1.html").write_text(template, encoding="utf-8")
    (STUDY / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (STUDY / "calculation-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built offline guide: {len(EXCERPTS)} exact excerpts, {len(sources)} sources, eight images and offline Plotly; {len(template.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
