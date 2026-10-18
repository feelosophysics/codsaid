"""전체 실험: EDA → 기본 파라미터 평가 → 파라미터 탐색 → 규칙 추가 실험 → 보너스 → 그림·results.json.

실행:
  python -m src.run_all                                  # 합성 데이터 20장 (data/synthetic)
  python -m src.run_all --data data/real --out outputs/real   # 직접 찍은 사진 (labels.json 있으면 정답 비교)
  python -m src.run_all --quick                          # 파라미터 탐색 생략 (약 1분 단축)

--threads로 OpenCV 스레드 수를 제한한다 (기본 2). 파라미터 탐색은 4천 번 이상 스캔하므로 CPU를 오래 쓴다.

이 파일은 새 계산 방법을 만들지 않는다. scanner·evaluate·eda·convolution의 함수를 미션 조건으로 부르고,
그림(outputs/*.png)과 숫자(outputs/results.json)를 남긴다. REPORT.md의 숫자는 이 results.json에서 온다.
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

# __file__은 이 파일의 경로. resolve()로 절대 경로, parents[1]은 두 단계 위(src의 상위) = A3-1 폴더.
# 어느 폴더에서 실행해도 data/·outputs/ 위치가 같게 된다.
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
    """시작 후 경과 시간을 붙여 진행 상황을 출력한다.

    기본값 리스트 t0는 함수를 정의할 때 한 번만 만들어져 모든 호출이 같은 리스트를 쓴다.
    보통은 피하는 문법이지만, 여기서는 "프로그램 시작 시각"을 전역 변수 없이 기억하는 데 일부러 쓴다.

    Args:
        msg: 출력할 문장.
        t0: 시작 시각을 담은 리스트. 호출할 때 넘기지 않는다.
    """
    # {값:6.1f}는 폭 6칸, 소수 1자리. flush=True는 버퍼에 모아 두지 않고 즉시 화면에 내보낸다.
    print(f"[{time.perf_counter() - t0[0]:6.1f}s] {msg}", flush=True)


def strip(row):
    """JSON에 넣을 수 있게 넘파이 값을 바꾼다.

    json.dumps는 NumPy 배열·숫자를 모른다. default 함수가 그런 값을 만날 때마다 불려
    tolist()가 있으면 리스트로, 없으면 float로 바꾼다. 다시 loads해 순수 파이썬 dict를 얻는다.

    Args:
        row: NumPy 값이 섞인 dict 또는 list.

    Returns:
        dict 또는 list: 같은 구조의 순수 파이썬 값.
    """
    # hasattr(o, "tolist")는 "o에 tolist라는 기능이 있는가". NumPy 배열·숫자에는 있다.
    return json.loads(json.dumps(row, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))


def run_eda(dataset, out):
    """이미지별 밝기 통계와 히스토그램 그림, E01 어둡게 하기 실험을 실행한다.

    Args:
        dataset: evaluate.load_dataset()의 결과.
        out: 그림을 저장할 폴더 Path.

    Returns:
        tuple: (stats, dark). stats는 {이미지 id: 통계 dict}, dark는 darkening_experiment의 행 목록 또는 None.
    """
    # {키: 값 for ...}는 dict 컴프리헨션. 이미지 id마다 통계 dict를 만든다.
    stats = {lab["id"]: eda.image_stats(img, lab.get("corners")) for lab, img in dataset}
    figures.histogram_grid(dataset, stats, out / "02_histograms.png")
    dark = None
    ids = [lab["id"] for lab, _ in dataset]
    if "E01" in ids and dataset[ids.index("E01")][0].get("corners"):
        lab, img = dataset[ids.index("E01")]
        dark = eda.darkening_experiment(img, lab["corners"])
        for r in dark:  # 어둡게 만든 이미지에서 문서 검출 여부도 기록
            # 주의: 여기서는 factor마다 다른 seed로, 회색이 아닌 컬러 이미지에 잡음을 더하고 반올림 없이 uint8로 바꾼다.
            # 같은 행의 기울기·검출률(darkening_experiment)과는 잡음이 다른 이미지다. 경향 비교용으로 읽는다.
            rng = np.random.default_rng(int(r["factor"] * 1000))
            dimg = np.clip(img.astype(np.float64) * r["factor"] + rng.normal(0, 3.0, img.shape), 0, 255).astype(np.uint8)
            r["found"] = evaluate.judge(scan(dimg, warp=False), lab)["status"]  # dict를 제자리에서 채운다
    return stats, dark


def convolution_bonus(dataset, out):
    """E01(또는 첫 이미지)의 회색 축소본으로 실행 시간과 OpenCV 대비 오차를 잰다.

    실행 결과: 네 NumPy 방법 모두 cv2.GaussianBlur와 최대 차이 0.0(실수 결과 그대로 비교).
    시간은 실행할 때마다 달라지므로, 다시 실행하면 results.json의 times·speedup_vs_loops와 12번 그림이 바뀐다.

    Args:
        dataset: evaluate.load_dataset()의 결과.
        out: 그림을 저장할 폴더 Path.

    Returns:
        dict: ksize, shape, times(초), max_abs_diff_vs_opencv, speedup_vs_loops.
    """
    img = dataset[0][1]  # 첫 번째 (label, image) 튜플의 이미지
    for lab, im in dataset:
        if lab["id"] == "E01":
            img = im
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # (360, 480)은 (가로, 세로). 결과 shape는 (480, 360)이다. 이중 for문이 너무 오래 걸리지 않도록 줄인다.
    gray = cv2.resize(gray, (360, 480), interpolation=cv2.INTER_AREA).astype(np.float64)
    ksize = 5
    res = convolution.benchmark(gray, ksize)
    t0 = time.perf_counter()
    for _ in range(5):
        ref = cv2.GaussianBlur(gray, (ksize, ksize), 0)
    res["opencv"] = {"seconds": (time.perf_counter() - t0) / 5, "output": ref}  # 5번 평균
    labels = {"loops": "NumPy double for-loop", "vectorized": "NumPy shifted sum (k^2 loops)",
              "strided": "NumPy sliding window + einsum", "separable": "NumPy separable 1D x 2",
              "opencv": "cv2.GaussianBlur"}
    # labels[k]로 내부 이름을 그림용 영어 이름으로 바꾼다. v["output"] − ref는 (480, 360) 차이 배열.
    bench = {"ksize": ksize, "shape": list(gray.shape), "times": {labels[k]: v["seconds"] for k, v in res.items()},
             "max_abs_diff_vs_opencv": {labels[k]: float(np.abs(v["output"] - ref).max()) for k, v in res.items()}}
    loops = res["loops"]["seconds"]
    bench["speedup_vs_loops"] = {labels[k]: loops / v["seconds"] for k, v in res.items()}
    figures.convolution_figure(bench, {"blurred": res["vectorized"]["output"],
                                       "diff": np.abs(res["vectorized"]["output"] - ref)}, out / "12_convolution.png")
    return bench


def main(argv=None):
    """모든 실험을 순서대로 실행하고 그림과 results.json을 저장한다.

    Args:
        argv: 인자 문자열 목록. None이면 실제 명령줄을 읽는다.

    Returns:
        int: 종료 코드 0.
    """
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

    # 1. EDA
    stats, dark = run_eda(dataset, out)
    # all(...)은 모든 이미지에 정답 꼭짓점이 있을 때만 True. 실제 사진 폴더처럼 정답이 없으면 평가 그림을 건너뛴다.
    has_gt = all(lab.get("corners") for lab, _ in dataset)
    if has_gt:
        rows_tmp = evaluate.evaluate(dataset)
        figures.histogram_by_condition(dataset, stats, rows_tmp, out / "03_histogram_by_condition.png")
    if dark:
        figures.darkening_figure(dark, stats.get("S04"), out / "04_darkening.png")
    log("EDA 완료")

    # 2. 기본 파라미터로 20장 평가하고 결과 이미지를 저장한다
    params = ScanParams()
    rows, results = evaluate.evaluate(dataset, params, warp=True)
    summary = evaluate.summarize(rows)
    gallery, pdf_pages = [], []
    # zip으로 세 목록(데이터, 결과, 평가 행)의 같은 위치를 함께 꺼낸다. (lab, _)로 튜플 안의 이미지는 버린다.
    for (lab, _), res, row in zip(dataset, results, rows):
        if res.found:
            imwrite(out / "scans" / f"scanned_{lab['id']}.png", res.scanned)
            imwrite(out / "scans" / f"warped_{lab['id']}.jpg", res.warped, jpeg_quality=85)
            if row["status"] in ("success", "partial", "unknown"):
                gallery.append((lab["id"], res.warped, res.scanned))
                pdf_pages.append(res.scanned)
    figures.detection_grid(dataset, results, rows, out / "06_detection.png")
    ids = [lab["id"] for lab, _ in dataset]
    # 앞의 리스트가 비면(지정한 id가 하나도 없으면) or 뒤의 처음 4장을 쓴다.
    for pid in [p for p in PIPELINE_IDS if p in ids] or ids[:4]:
        i = ids.index(pid)
        figures.pipeline_figure(results[i], dataset[i][0], rows[i], out / f"05_pipeline_{pid}.png")
    # 실패·부분 성공만 모은다. FAILURE_NOTES에 설명이 없으면 실패 이유 앞 40글자를 쓴다.
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
        # {값:<14}는 왼쪽 정렬로 14칸을 차지하게 한다(표처럼 줄이 맞는다).
        log(f"  {s['name']:<14} 성공 {s['success']}/{s['n']}  부분 {s['partial']}  실패 {s['fail']}")
    log("기본 파라미터 평가 완료")

    # 3. 파라미터 탐색과 규칙 추가 실험 (정답이 있을 때만)
    sweep = rules = None  # 두 변수에 같은 값 None을 넣는다
    if not args.quick and has_gt:
        configs, matrix, sweep_ids = evaluate.parameter_sweep(
            dataset, params, progress=lambda j, n: log(f"  파라미터 탐색 {j}/{n}") if j % 60 == 0 else None)
        sweep = evaluate.sweep_summary(configs, matrix, sweep_ids)
        figures.sweep_figure(configs, matrix, sweep_ids, sweep, out / "08_parameter_sweep.png")
        if sweep["disjoint_pairs"]:
            figures.dilemma_figure(configs, matrix, sweep_ids, sweep["disjoint_pairs"][:2], out / "09_dilemma.png")
        # 판정 행렬 (20, 266)을 압축 파일로 저장해 그림을 다시 그리거나 다른 분석을 할 때 탐색을 반복하지 않게 한다.
        np.savez_compressed(out / "sweep_matrix.npz", matrix=matrix, configs=np.array(configs), ids=np.array(sweep_ids))
        log(f"파라미터 탐색 완료: 최적 단일 조합 {sweep['best']['success']}/20, 이미지별 최적 {sweep['oracle_success']}/20")
        rules = evaluate.rule_experiment(dataset, params)
        figures.rule_variant_figure(rules, ids, out / "10_rule_variants.png")
        log("규칙 추가 실험 완료")

    # 4. 보너스 1
    bench = convolution_bonus(dataset, out)
    log("보너스 1 컨볼루션 비교 완료")

    # 5. 모든 숫자를 results.json 하나에 모은다. tools/build_report.py와 HTML 학습 자료가 이 파일을 읽는다.
    doc = {
        "environment": {"python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__,
                        "matplotlib": matplotlib.__version__, "platform": platform.platform()},
        "data": str(data_dir.relative_to(ROOT)).replace("\\", "/"),  # Windows 경로의 \를 /로 바꿔 운영체제와 무관하게 적는다
        "params": params.to_dict(),
        "criteria": {"success_max_corner_error_ratio": evaluate.SUCCESS_RATIO,
                     "partial_max_corner_error_ratio": evaluate.PARTIAL_RATIO},
        "summary": summary,
        "rows": [strip(r) for r in rows],
        "eda": stats,
        # 히스토그램(256칸 × 7개)은 너무 길어 뺀다. {k: v for ... if k != "hist"}는 hist 키만 뺀 새 dict.
        "darkening": [{k: v for k, v in r.items() if k != "hist"} for r in dark] if dark else None,
        "sweep": sweep,
        "rules": rules,
        "convolution": bench,
    }
    # ensure_ascii=False는 한글을 \uXXXX로 바꾸지 않고 그대로 저장한다.
    (out / "results.json").write_text(json.dumps(strip(doc), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"저장: {(out / 'results.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
