"""study/a3-2.template.html에 현재 소스·결과를 넣어 study/a3-2.html을 만든다.

넣는 것: 원본 Python 함수 발췌(줄 번호 포함), 축소한 결과 그림, 위젯 데이터(실제 검출 결과와 정답, 픽셀 시계열,
마스크 조각, 비율 검정 거리), results.json 요약. 실행 전 `python -m src.run_all`로 outputs/를 최신으로 만든다.
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

from src import cache as K  # noqa: E402
from src import evaluate as E  # noqa: E402
from src import experiments as X  # noqa: E402
from src import synthetic as S  # noqa: E402
from src.features import TargetMatcher  # noqa: E402
from src.figures import draw_tracks  # noqa: E402
from src.image_io import imread  # noqa: E402
from src.motion import MotionDetector, MotionParams  # noqa: E402
from src.tracker import Tracker  # noqa: E402

STUDY = ROOT / "study"
TEMPLATE = STUDY / "a3-2.template.html"
OUTPUT = STUDY / "a3-2.html"
MANIFEST = STUDY / "source-manifest.json"
RESULTS = ROOT / "outputs" / "results.json"
REPLAY_SCENARIOS = ("crossing", "crossing_same", "single", "pause", "lighting")

EXCERPTS = [
    ("src/motion.py", ["RunningAverageSubtractor.apply", "foreground_mask", "clean_mask", "find_detections"]),
    ("src/tracker.py", ["iou", "make_kalman", "Tracker.cost_matrix", "Tracker.update"]),
    ("src/hungarian.py", ["hungarian", "greedy", "gated_assignment"]),
    ("src/features.py", ["TargetMatcher.match"]),
    ("src/evaluate.py", ["match_frame", "stable_switches", "failure_runs"]),
    ("src/zone.py", ["IntrusionZone.update"]),
    ("src/pipeline.py", ["VideoAnalyzer.process"]),
    ("src/app.py", ["handle_key"]),
]

FIGURES = [
    ("01_scenarios.png", "합성 테스트 영상 6종과 정답 박스(청록)"),
    ("02_pipeline.png", "한 프레임의 처리 단계: 입력 → MOG2 원본(회색=그림자) → 그림자 제거·열림·닫힘 → 박스·ID·궤적"),
    ("03_id_timeline.png", "교차 영상에서 각 사람에게 붙은 추적 ID의 시간 변화 (회색 = 한 덩어리 박스)"),
    ("04_crossing_frames.png", "통과(pass)와 되돌아감(bounce): 탐욕 추적기와 칼만 추적기의 전·병합·후"),
    ("05_xt_pass_bounce.png", "가로 위치–시간 그래프: 굵은 선 = 정답, 점 = 추적 결과(ID별 색)"),
    ("06_rules_heatmap.png", "규칙 변형 × 교차 이벤트별 ID Switch (왼쪽: 옷 색이 다름, 오른쪽: 같음)"),
    ("07_param_sweep.png", "거리 임계값과 기억 길이 탐색 (점선 dev, 실선 test)"),
    ("08_learning_rate.png", "배경 학습률 4가지: 멈춘 사람이 사라지는 시간 vs 조명 변화에서 회복하는 시간"),
    ("09_bg_masks.png", "배경 모델별 전경 마스크: 정지·재출발·조명 켜짐·국소 조명"),
    ("10_feature_curves.png", "특징점 매칭률과 검출 성공률: 회전·기울임·가림·크기·밝기·흐림"),
    ("11_feature_matches.png", "ORB 매칭 예: 정면, 평면 회전 60°, 3D 기울임 60°, 50% 가림 (초록 = RANSAC inlier)"),
    ("12_generalization.png", "학습하지 않은 특징의 일반화: 같은 시리즈·무관한 표지·색 반전·선 그림"),
    ("13_target_video.png", "등록 물체 영상에서 프레임별 inlier 수와 TARGET DETECTED 구간"),
    ("14_hungarian.png", "보너스 1: 탐욕 할당이 최적이 아닌 비율과 실행 시간"),
    ("15_zone.png", "보너스 2: 침입 구역 경고와 들어감·나감 로그"),
]


def text_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def byte_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_node(tree, qualname):
    body, node = tree.body, None
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


def figure_data_uri(path, max_width=1100):
    img = plt.imread(path)[..., :3]
    h, w = img.shape[:2]
    factor = max(1, math.ceil(w / max_width))
    if factor > 1:
        h2, w2 = h // factor * factor, w // factor * factor
        img = img[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor, 3).mean(axis=(1, 3))
    buf = io.BytesIO()
    plt.imsave(buf, np.clip(img, 0, 1), format="jpg", pil_kwargs={"quality": 78})
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def jpeg_uri(bgr, width=256, quality=62):
    h, w = bgr.shape[:2]
    small = cv2.resize(bgr, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def replay_payload():
    """추적기 재생 위젯: test 분할의 프레임별 검출 박스와 정답 박스. JS가 이 검출로 추적·판정을 다시 계산한다."""
    out = {}
    cache = X.detection_cache("test", REPLAY_SCENARIOS)   # run_all과 같은 검출 (캐시가 켜져 있으면 재사용)
    for sc in REPLAY_SCENARIOS:
        gt, dets = cache[sc]
        out[sc] = {
            "video": gt["video"], "frames": gt["frames"], "objects": gt["objects"],
            "dets": [[list(d.bbox) for d in fr] for fr in dets],
            "gt": [[[o["id"], *(o["bbox"] or [0, 0, 0, 0]), o["vis"], 1 if o["bbox"] else 0] for o in fr if o["id"] != "T"]
                   for fr in gt["gt"]],
            "events": [{**{k: e[k] for k in ("index", "kind", "label", "start", "end")}, "extra": bool(e.get("extra"))}
                       for e in gt["events"]],
        }
    return out


def scrub_payload(step=2):
    """1절 프레임 넘기기: 교차 영상의 통과·되돌아감 구간을 두 추적기로 그린 작은 JPEG."""
    gt, dets = X.detection_cache("test", ("crossing",))["crossing"]
    outs = {k: E.track_detections(dets, Tracker(**kw)) for k, kw in (("baseline", {}), ("kalman", {"kalman": True}))}
    ev = {e["kind"]: e for e in gt["events"]}
    want = {}
    for kind in ("pass", "bounce"):
        e = ev[kind]
        want[kind] = list(range(e["start"], e["end"] + 1, step))
    need = {i for v in want.values() for i in v}
    frames = {}
    for i, f in enumerate(E.read_frames(S.DATA / gt["video"])):
        if i in need:
            frames[i] = f
    payload = {}
    for kind, idx in want.items():
        payload[kind] = {"frames": idx, "label": ev[kind]["label"]}
        for k, o in outs.items():
            payload[kind][k] = []
            for i in idx:
                trails = {}
                for j in range(max(0, i - 40), i + 1):
                    for tid, _, c in o[j]:
                        trails.setdefault(tid, []).append((int(c[0]), int(c[1])))
                img = draw_tracks(frames[i], o[i], trails)
                cv2.putText(img, f"f{i}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                payload[kind][k].append(jpeg_uri(img))
    return payload


def pixel_series():
    """배경 모델 위젯: 사람이 멈췄던 자리 한 픽셀과 국소 조명 영역 한 픽셀의 회색값 시계열."""
    out = {}
    pg = S.load_gt("pause", "test")
    stop = next(e for e in pg["events"] if e.get("resume") and e["resume"] - e["start"] >= 150)
    o = next(o for o in pg["gt"][stop["start"] + 5] if o["id"] == "A")
    x, y, w, h = o["bbox"]
    px = (x + w // 2, y + int(h * 0.42))           # 셔츠 한가운데
    lg = S.load_gt("lighting", "test")
    lamp = next(e for e in lg["events"] if e["kind"] == "lamp")
    for name, gt, (pxx, pyy), marks in (("pause", pg, px, [stop["start"], stop["resume"]]),
                                        ("lighting", lg, (150, 120), [e["start"] for e in lg["events"]])):
        vals = []
        for f in E.read_frames(S.DATA / gt["video"]):
            vals.append(int(cv2.cvtColor(f[pyy:pyy + 1, pxx:pxx + 1], cv2.COLOR_BGR2GRAY)[0, 0]))
        out[name] = {"values": vals, "pixel": [int(pxx), int(pyy)], "marks": marks,
                     "events": [{"kind": e["kind"], "start": e["start"], "end": e["end"],
                                 "resume": e.get("resume")} for e in gt["events"]]}
    del lamp
    return out


def morph_payload():
    """모폴로지 위젯: 교차 영상 한 프레임의 MOG2 원본 마스크(그림자 127 포함) 조각과 OpenCV 타원 커널."""
    gt = S.load_gt("crossing", "test")
    det = MotionDetector(MotionParams())
    target = 95
    for i, f in enumerate(E.read_frames(S.DATA / gt["video"])):
        _, _, raw = det(f)
        if i == target:
            break
    ys, xs = np.nonzero(raw > 200)
    x0, y0 = max(0, int(xs.min()) - 12), max(0, int(ys.min()) - 10)
    x1, y1 = min(raw.shape[1], int(xs.max()) + 13), min(raw.shape[0], int(ys.max()) + 10)
    crop = raw[y0:y1, x0:x1]
    kernels = {k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)).tolist() for k in (1, 3, 5, 7, 9, 11, 15, 21)}
    return {"w": int(crop.shape[1]), "h": int(crop.shape[0]), "origin": [x0, y0], "frame": target,
            "data": base64.b64encode(np.ascontiguousarray(crop).tobytes()).decode("ascii"), "kernels": kernels,
            "min_area": MotionParams().min_area}


def ratio_payload():
    """비율 검정 위젯: 등록 이미지의 각 ORB 특징점에 대한 1·2등 해밍 거리와 1등 매칭이 정답인지."""
    texture = imread(S.TARGET_DIR / "target.png")
    m = TargetMatcher(texture, "orb")
    out = {}
    for name, cond in (("frontal", {}), ("yaw60", {"yaw": 60}), ("occ50", {"occlusion": 0.5}), ("roll60", {"roll": 60})):
        img, corners, H = next(X._views(texture, cond, 1, seed=5))
        kp, des = m.detector.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
        rows = []
        for pair in m.matcher.knnMatch(m.ref_des, des, k=2):
            if len(pair) < 2:
                continue
            a, b = pair
            p = cv2.perspectiveTransform(np.float32([[m.ref_kp[a.queryIdx].pt]]), H)[0, 0]
            ok = float(np.hypot(*(np.float32(kp[a.trainIdx].pt) - p))) < 5.0
            rows.append([int(a.distance), int(b.distance), int(ok)])
        out[name] = rows
    return {"n_ref": m.n_ref, "views": out}


def results_payload():
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    bg = {k: {kk: vv for kk, vv in v.items() if not kk.endswith("_series")} for k, v in res["background"].items()}
    keep_var = {sp: {k: {"label": v["label"], "kwargs": v["kwargs"],
                         "scenarios": {sc: {kk: vv for kk, vv in s.items()} for sc, s in v["scenarios"].items()}}
                     for k, v in res["variants"][sp].items()} for sp in res["variants"]}
    return {
        "environment": res["environment"], "criteria": res["criteria"], "params": res["params"],
        "table": res["table"], "log": res["log"], "variants": keep_var, "tuned": res["tuned"],
        "hungarian": res["hungarian"], "zone": {k: v for k, v in res["zone"].items() if k != "events"},
        "zone_events": res["zone"]["events"][:12], "background": bg,
        "features": {"table": res["features"]["table"], "generalization": res["features"]["generalization"],
                     "video": {k: v for k, v in res["features"]["video"].items() if k in ("segments", "ms_per_frame")}},
        "speed": res["speed"], "events": {sc: [{k: e[k] for k in ("index", "kind", "label", "switches", "fails", "memo")}
                                              for e in evs] for sc, evs in res["events"].items()},
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="", help="run_all --cache와 같은 폴더를 주면 검출을 다시 계산하지 않는다")
    K.configure(ap.parse_args(argv).cache)
    cv2.setNumThreads(2)
    template = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*__DATA__*/null"
    if template.count(marker) != 1:
        raise SystemExit("템플릿에 데이터 자리표시자가 정확히 하나 있어야 한다")
    data = {
        "code": code_excerpts(),
        "images": [{"file": f, "caption": c, "src": figure_data_uri(ROOT / "outputs" / f)} for f, c in FIGURES
                   if (ROOT / "outputs" / f).exists()],
        "replay": replay_payload(),
        "scrub": scrub_payload(),
        "pixels": pixel_series(),
        "morph": morph_payload(),
        "ratio": ratio_payload(),
        "results": results_payload(),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUTPUT.write_text(template.replace(marker, payload), encoding="utf-8", newline="\n")
    sources = sorted({rel for rel, _ in EXCERPTS}) + ["study/a3-2.template.html"]
    manifest = {
        "hash_mode": "UTF-8 텍스트는 CRLF를 LF로 바꾼 뒤 SHA-256, 영상·그림·결과는 원래 바이트의 SHA-256",
        "text": {rel: text_hash(ROOT / rel) for rel in sources},
        "binary": {**{f"outputs/{f}": byte_hash(ROOT / "outputs" / f) for f, _ in FIGURES if (ROOT / "outputs" / f).exists()},
                   "outputs/results.json": byte_hash(RESULTS),
                   **{f"data/synthetic/{sc}_test.mp4": byte_hash(S.DATA / f"{sc}_test.mp4") for sc in REPLAY_SCENARIOS}},
        "excerpts": [{k: v for k, v in item.items() if k != "text"} for item in data["code"]],
        "html_bytes": OUTPUT.stat().st_size,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KB), "
          f"{len(data['code'])} excerpts, {len(data['images'])} figures")


if __name__ == "__main__":
    main()
