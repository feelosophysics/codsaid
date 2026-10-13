"""전체 실험: EDA → 기본 파라미터 평가 → 파라미터 탐색 → 규칙 추가 실험 → 보너스 → 그림·results.json.

실행:
  python -m src.run_all                                  # 합성 데이터 20장 (data/synthetic)
  python -m src.run_all --data data/real --out outputs/real   # 직접 찍은 사진 (labels.json 있으면 정답 비교)
  python -m src.run_all --quick                          # 파라미터 탐색 생략 (약 1분 단축)

--threads로 OpenCV 스레드 수를 제한한다 (기본 2). 파라미터 탐색은 4천 번 이상 스캔하므로 CPU를 오래 쓴다.
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path

import cv2
import matplotlib
import numpy as np

from . import convolution, eda, evaluate, figures
from .image_io import imwrite
from .pdf_export import save_pdf
from .scanner import ScanParams, scan

ROOT = Path(__file__).resolve().parents[1]

# 그림에 붙이는 짧은 실패 설명 (합성 데이터 ID 기준). 자세한 분석은 REPORT.md에 있다.
FAILURE_NOTES = {
    "E03": "blue stripe ~ brown desk\nin gray (80 vs 97)",
    "S04": "low light: border step\nbelow Canny thresholds",
    "S05": "glare saturates the corner;\nborder breaks open",
    "T04": "same blue-stripe border,\nfar side foreshortened",
    "C02": "plaid lines join the border;\nlargest quad is not the paper",
    "C03": "white paper on white desk\n+ overlapping sheet",
    "C04": "finger covers BR corner;\nquad snaps to the hand",
    "C05": "crumple ridges make\n7-9 vertex contour",
}
PIPELINE_IDS = ("E01", "S03", "T05", "C02")


def log(msg, t0=[time.perf_counter()]):  # noqa: B006 — 시작 시각 공유용
    print(f"[{time.perf_counter() - t0[0]:6.1f}s] {msg}", flush=True)


def strip(row):
    """JSON에 넣을 수 있게 넘파이 값을 바꾼다."""
    return json.loads(json.dumps(row, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))


def run_eda(dataset, out):
    stats = {lab["id"]: eda.image_stats(img, lab.get("corners")) for lab, img in dataset}
    figures.histogram_grid(dataset, stats, out / "02_histograms.png")
    dark = None
    ids = [lab["id"] for lab, _ in dataset]
    if "E01" in ids and dataset[ids.index("E01")][0].get("corners"):
        lab, img = dataset[ids.index("E01")]
        dark = eda.darkening_experiment(img, lab["corners"])
        for r in dark:  # 어둡게 만든 이미지에서 문서 검출 여부도 기록
            rng = np.random.default_rng(int(r["factor"] * 1000))
            dimg = np.clip(img.astype(np.float64) * r["factor"] + rng.normal(0, 3.0, img.shape), 0, 255).astype(np.uint8)
            r["found"] = evaluate.judge(scan(dimg, warp=False), lab)["status"]
    return stats, dark


def convolution_bonus(dataset, out):
    """E01(또는 첫 이미지)의 회색 축소본으로 실행 시간과 OpenCV 대비 오차를 잰다."""
    img = dataset[0][1]
    for lab, im in dataset:
        if lab["id"] == "E01":
            img = im
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (360, 480), interpolation=cv2.INTER_AREA).astype(np.float64)
    ksize = 5
    res = convolution.benchmark(gray, ksize)
    t0 = time.perf_counter()
    for _ in range(5):
        ref = cv2.GaussianBlur(gray, (ksize, ksize), 0)
    res["opencv"] = {"seconds": (time.perf_counter() - t0) / 5, "output": ref}
    labels = {"loops": "NumPy double for-loop", "vectorized": "NumPy shifted sum (k^2 loops)",
              "strided": "NumPy sliding window + einsum", "separable": "NumPy separable 1D x 2",
              "opencv": "cv2.GaussianBlur"}
    bench = {"ksize": ksize, "shape": list(gray.shape), "times": {labels[k]: v["seconds"] for k, v in res.items()},
             "max_abs_diff_vs_opencv": {labels[k]: float(np.abs(v["output"] - ref).max()) for k, v in res.items()}}
    loops = res["loops"]["seconds"]
    bench["speedup_vs_loops"] = {labels[k]: loops / v["seconds"] for k, v in res.items()}
    figures.convolution_figure(bench, {"blurred": res["vectorized"]["output"],
                                       "diff": np.abs(res["vectorized"]["output"] - ref)}, out / "12_convolution.png")
    return bench


def main(argv=None):
    parser = argparse.ArgumentParser(description="A3-1 전체 실험")
    parser.add_argument("--data", default="data/synthetic")
    parser.add_argument("--out", default="outputs")
    parser.add_argument("--threads", type=int, default=2, help="OpenCV 스레드 수 (0이면 제한 없음)")
    parser.add_argument("--quick", action="store_true", help="파라미터 탐색과 규칙 실험을 건너뛴다")
    args = parser.parse_args(argv)
    evaluate.limit_threads(args.threads)
    data_dir, out = ROOT / args.data, ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "scans").mkdir(exist_ok=True)

    dataset = evaluate.load_dataset(data_dir)
    log(f"데이터 {len(dataset)}장: {data_dir.relative_to(ROOT)}")
    figures.dataset_overview(dataset, out / "01_dataset.png")

    stats, dark = run_eda(dataset, out)
    has_gt = all(lab.get("corners") for lab, _ in dataset)
    if has_gt:
        rows_tmp = evaluate.evaluate(dataset)
        figures.histogram_by_condition(dataset, stats, rows_tmp, out / "03_histogram_by_condition.png")
    if dark:
        figures.darkening_figure(dark, stats.get("S04"), out / "04_darkening.png")
    log("EDA 완료")

    params = ScanParams()
    rows, results = evaluate.evaluate(dataset, params, warp=True)
    summary = evaluate.summarize(rows)
    gallery, pdf_pages = [], []
    for (lab, _), res, row in zip(dataset, results, rows):
        if res.found:
            imwrite(out / "scans" / f"scanned_{lab['id']}.png", res.scanned)
            imwrite(out / "scans" / f"warped_{lab['id']}.jpg", res.warped, jpeg_quality=85)
            if row["status"] in ("success", "partial", "unknown"):
                gallery.append((lab["id"], res.warped, res.scanned))
                pdf_pages.append(res.scanned)
    figures.detection_grid(dataset, results, rows, out / "06_detection.png")
    ids = [lab["id"] for lab, _ in dataset]
    for pid in [p for p in PIPELINE_IDS if p in ids] or ids[:4]:
        i = ids.index(pid)
        figures.pipeline_figure(results[i], dataset[i][0], rows[i], out / f"05_pipeline_{pid}.png")
    bad = [(dataset[i][0], results[i], rows[i], FAILURE_NOTES.get(ids[i], rows[i]["reason"][:40]))
           for i in range(len(ids)) if rows[i]["status"] in ("fail", "partial")]
    if bad:
        figures.failure_panels(bad, out / "07_failures.png")
    if has_gt:
        figures.aspect_figure(rows, out / "11_aspect_ratio.png")
    if gallery:
        figures.scan_gallery(gallery[:12], out / "13_scans.png")
        save_pdf(pdf_pages, out / "scans.pdf")  # 보너스 3
    shadow_id = "S02" if "S02" in ids and results[ids.index("S02")].found else None
    if shadow_id:
        figures.threshold_comparison(results[ids.index(shadow_id)].warped, out / "14_threshold.png")
    for s in summary:
        log(f"  {s['name']:<14} 성공 {s['success']}/{s['n']}  부분 {s['partial']}  실패 {s['fail']}")
    log("기본 파라미터 평가 완료")

    sweep = rules = None
    if not args.quick and has_gt:
        configs, matrix, sweep_ids = evaluate.parameter_sweep(
            dataset, params, progress=lambda j, n: log(f"  파라미터 탐색 {j}/{n}") if j % 60 == 0 else None)
        sweep = evaluate.sweep_summary(configs, matrix, sweep_ids)
        figures.sweep_figure(configs, matrix, sweep_ids, sweep, out / "08_parameter_sweep.png")
        if sweep["disjoint_pairs"]:
            figures.dilemma_figure(configs, matrix, sweep_ids, sweep["disjoint_pairs"][:2], out / "09_dilemma.png")
        np.savez_compressed(out / "sweep_matrix.npz", matrix=matrix, configs=np.array(configs), ids=np.array(sweep_ids))
        log(f"파라미터 탐색 완료: 최적 단일 조합 {sweep['best']['success']}/20, 이미지별 최적 {sweep['oracle_success']}/20")
        rules = evaluate.rule_experiment(dataset, params)
        figures.rule_variant_figure(rules, ids, out / "10_rule_variants.png")
        log("규칙 추가 실험 완료")

    bench = convolution_bonus(dataset, out)
    log("보너스 1 컨볼루션 비교 완료")

    doc = {
        "environment": {"python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__,
                        "matplotlib": matplotlib.__version__, "platform": platform.platform()},
        "data": str(data_dir.relative_to(ROOT)).replace("\\", "/"),
        "params": params.to_dict(),
        "criteria": {"success_max_corner_error_ratio": evaluate.SUCCESS_RATIO,
                     "partial_max_corner_error_ratio": evaluate.PARTIAL_RATIO},
        "summary": summary,
        "rows": [strip(r) for r in rows],
        "eda": stats,
        "darkening": [{k: v for k, v in r.items() if k != "hist"} for r in dark] if dark else None,
        "sweep": sweep,
        "rules": rules,
        "convolution": bench,
    }
    (out / "results.json").write_text(json.dumps(strip(doc), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"저장: {(out / 'results.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
