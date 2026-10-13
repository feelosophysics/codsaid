"""study/a3-1.template.html에 현재 소스·결과를 넣어 study/a3-1.html을 만든다.

넣는 것: 원본 Python 함수 발췌(줄 번호 포함), 축소한 결과 그림, 위젯용 작은 회색 이미지·윤곽선·정답 꼭짓점,
results.json 요약. 실행 전 `python -m src.run_all`로 outputs/를 최신으로 만든다.
"""
import ast
import base64
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.image_io import imread  # noqa: E402
from src.scanner import ScanParams, scan, stage_images  # noqa: E402

STUDY = ROOT / "study"
TEMPLATE = STUDY / "a3-1.template.html"
OUTPUT = STUDY / "a3-1.html"
MANIFEST = STUDY / "source-manifest.json"
DATA = ROOT / "data" / "synthetic"
RESULTS = ROOT / "outputs" / "results.json"

EXCERPTS = [
    ("src/scanner.py", ["preprocess", "detect_edges", "find_document_quad", "warp_document", "enhance", "scan"]),
    ("src/geometry.py", ["order_points_sum_diff", "order_points", "is_convex", "output_size_by_distance",
                         "estimate_aspect_ratio", "corner_error"]),
    ("src/convolution.py", ["gaussian_kernel_1d", "convolve_loops", "convolve_vectorized", "convolve_strided",
                            "blur_separable"]),
    ("src/eda.py", ["darkening_experiment"]),
    ("src/evaluate.py", ["judge", "sweep_summary"]),
    ("src/app.py", ["run_gui"]),
    ("src/webcam.py", ["process_frame"]),
    ("src/pdf_export.py", ["save_pdf"]),
]

FIGURES = [
    ("01_dataset.png", "합성 테스트셋 20장과 정답 꼭짓점(청록)"),
    ("03_histogram_by_condition.png", "조건별 평균 히스토그램, 전역 통계, 경계 대비"),
    ("04_darkening.png", "E01을 점점 어둡게: 히스토그램 압축, 경계 기울기, Canny 검출률"),
    ("05_pipeline_E01.png", "E01 쉬운 케이스의 5단계"),
    ("05_pipeline_S03.png", "S03 강한 그림자: 검출은 성공, 이진화에 그림자 경계가 남음"),
    ("06_detection.png", "기본 파라미터 검출 결과: 정답(청록)과 검출(빨강)"),
    ("07_failures.png", "실패·부분 성공 8건의 엣지와 윤곽선 후보"),
    ("08_parameter_sweep.png", "266개 파라미터 조합 × 20장 판정표"),
    ("09_dilemma.png", "성공 영역이 겹치지 않는 이미지 쌍"),
    ("10_rule_variants.png", "규칙을 더하고 뺄 때의 판정 변화"),
    ("11_aspect_ratio.png", "보너스 2: 종횡비 오차, 변 길이 vs 원근 보정"),
    ("12_convolution.png", "보너스 1: 컨볼루션 구현별 시간과 OpenCV 대비 오차"),
    ("14_threshold.png", "전역 Otsu vs 적응형 이진화 (S02)"),
]

WIDGET_IMAGES = ("E01", "S04", "C02", "C03", "C05")
WIDGET_W, WIDGET_H = 240, 320
CONTOUR_IDS = ("E01", "C04", "C05")


def text_hash(path):
    """줄바꿈을 LF로 통일한 UTF-8 텍스트의 SHA-256 (Git 체크아웃 차이에 무관)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def byte_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_node(tree, qualname):
    body = tree.body
    node = None
    for part in qualname.split("."):
        node = next(n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part)
        body = node.body
    return node


def code_excerpts():
    items = []
    for rel, names in EXCERPTS:
        source = (ROOT / rel).read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        for name in names:
            node = find_node(tree, name)
            items.append({"file": rel, "name": name, "start": node.lineno, "end": node.end_lineno,
                          "text": "\n".join(lines[node.lineno - 1:node.end_lineno])})
    return items


def figure_data_uri(path, max_width=1000):
    img = plt.imread(path)[..., :3]
    h, w = img.shape[:2]
    factor = max(1, math.ceil(w / max_width))
    if factor > 1:
        h2, w2 = h // factor * factor, w // factor * factor
        img = img[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor, 3).mean(axis=(1, 3))
    buf = io.BytesIO()
    plt.imsave(buf, np.clip(img, 0, 1), format="jpg", pil_kwargs={"quality": 80})
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def jpeg_uri(bgr, max_side=420, quality=78):
    h, w = bgr.shape[:2]
    s = max_side / max(h, w)
    small = cv2.resize(bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def gray_payload(gray):
    return {"w": int(gray.shape[1]), "h": int(gray.shape[0]),
            "data": base64.b64encode(np.ascontiguousarray(gray, np.uint8).tobytes()).decode("ascii")}


def widget_images(labels):
    """위젯용 240×320 회색 이미지와, 같은 배율로 줄인 정답 꼭짓점."""
    out = {}
    for i in WIDGET_IMAGES:
        lab = labels[i]
        img = imread(DATA / lab["file"])
        h, w = img.shape[:2]
        gray = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (WIDGET_W, WIDGET_H), interpolation=cv2.INTER_AREA)
        sx, sy = WIDGET_W / w, WIDGET_H / h
        out[i] = {**gray_payload(gray), "corners": [[x * sx, y * sy] for x, y in lab["corners"]],
                  "condition": lab["condition_name"], "note": lab["note"]}
    return out


def contours_payload(labels):
    """approxPolyDP 위젯용: 면적 조건을 통과한 가장 큰 윤곽선의 원본 점(축소본 좌표)."""
    out = {}
    for i in CONTOUR_IDS:
        r = scan(imread(DATA / labels[i]["file"]), warp=False)
        area_min = r.params.min_area_ratio * r.closed.size
        area_max = r.params.max_area_ratio * r.closed.size
        best = None
        for c in sorted(r.contours, key=cv2.contourArea, reverse=True):
            a = cv2.contourArea(c)
            if area_min <= a <= area_max:
                best = c
                break
        pts = best.reshape(-1, 2)
        out[i] = {"w": int(r.closed.shape[1]), "h": int(r.closed.shape[0]), "points": pts.tolist(),
                  "note": labels[i]["note"]}
    return out


def shadow_page():
    """적응형 이진화 위젯용: S02를 펴낸 결과의 회색본 (폭 180)."""
    lab = json.loads((DATA / "labels.json").read_text(encoding="utf-8"))["images"]
    s02 = next(x for x in lab if x["id"] == "S02")
    r = scan(imread(DATA / s02["file"]), ScanParams())
    gray = cv2.cvtColor(r.warped, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    small = cv2.resize(gray, (180, round(h * 180 / w)), interpolation=cv2.INTER_AREA)
    return gray_payload(small)


def stage_payload(labels):
    """1장의 5단계 그림 (E01)."""
    r = scan(imread(DATA / labels["E01"]["file"]))
    return [{"name": n, "src": jpeg_uri(img)} for n, img in stage_images(r).items()]


def results_payload():
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    keep_rows = ("id", "condition", "condition_name", "status", "error_ratio", "max_error_px", "reason", "n_contours",
                 "aspect_error", "distance_aspect_error", "rotation_shift")
    sweep = dict(res["sweep"])
    sweep.pop("per_config_success", None)
    return {
        "params": res["params"], "summary": res["summary"],
        "rows": [{k: r[k] for k in keep_rows if k in r} for r in res["rows"]],
        "sweep": sweep,
        "rules": [{"name": v["name"], "success": v["success"], "status": v["status"]} for v in res["rules"]],
        "darkening": res["darkening"], "convolution": res["convolution"],
        "eda": {k: {m: v[m] for m in ("mean", "std", "doc_bg_contrast", "boundary_step_p10", "boundary_gradient_median")}
                for k, v in res["eda"].items()},
        "environment": res["environment"],
    }


def main():
    template = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*__DATA__*/null"
    if template.count(marker) != 1:
        raise SystemExit("템플릿에 데이터 자리표시자가 정확히 하나 있어야 한다")
    labels = {x["id"]: x for x in json.loads((DATA / "labels.json").read_text(encoding="utf-8"))["images"]}
    data = {
        "code": code_excerpts(),
        "images": [{"file": f, "caption": c, "src": figure_data_uri(ROOT / "outputs" / f)} for f, c in FIGURES],
        "gray": widget_images(labels),
        "contours": contours_payload(labels),
        "shadowPage": shadow_page(),
        "stages": stage_payload(labels),
        "results": results_payload(),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUTPUT.write_text(template.replace(marker, payload), encoding="utf-8", newline="\n")

    sources = sorted({rel for rel, _ in EXCERPTS}) + ["study/a3-1.template.html", "data/synthetic/labels.json"]
    manifest = {
        "hash_mode": "UTF-8 텍스트는 CRLF를 LF로 바꾼 뒤 SHA-256, 이미지·결과는 원래 바이트의 SHA-256",
        "text": {rel: text_hash(ROOT / rel) for rel in sources},
        "binary": {**{f"outputs/{f}": byte_hash(ROOT / "outputs" / f) for f, _ in FIGURES},
                   "outputs/results.json": byte_hash(RESULTS),
                   **{f"data/synthetic/{i}.jpg": byte_hash(DATA / f"{i}.jpg")
                      for i in sorted(set(WIDGET_IMAGES) | set(CONTOUR_IDS) | {"S02"})}},
        "excerpts": [{k: v for k, v in item.items() if k != "text"} for item in data["code"]],
        "html_bytes": OUTPUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KB), "
          f"{len(data['code'])} excerpts, {len(data['images'])} figures")


if __name__ == "__main__":
    main()
