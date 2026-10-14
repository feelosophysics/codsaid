"""정답과 추적 결과를 비교해 ID Switch, 추적 실패, 유지율을 판정한다.

프레임 단위 평가에 사용하는 판정 기준:
- 정답 객체와 추적 객체의 대응: 프레임마다 IoU ≥ 0.3이거나 추적 중심점이 정답 박스 안이면 후보이고,
  후보 중 IoU 합이 최대가 되게 일대일로 짝짓는다 (src/hungarian.py).
- 병합: 추적 박스 하나가 정답 객체 두 개 이상을 각각 50% 이상 덮으면 '한 덩어리' 박스다. 이 박스는 누구의 ID인지
  정할 수 없으므로 덮인 객체들에 MERGED로 기록하고, ID 판정에서는 건너뛰며, 실패로는 세지 않는다(박스는 있다).
  겹침이 풀린 뒤 붙는 ID가 5프레임 이상 유지되는지 확인해 전환을 판정하기 위해서다.
- ID Switch: 정답 객체에 붙은 추적 ID가 다른 ID로 바뀌어 그 ID가 5프레임 이상 유지되면 1회.
  새 ID가 붙기 시작한 프레임을 전환 시점으로 기록한다. (짝 없는·병합 프레임은 세지도 끊지도 않는다.)
- 추적 실패: 정답 객체가 보이는데(가시율 ≥ 0.5) 10프레임 이상 연속으로 짝이 없으면 1회.
- 가림: 가시율 < 0.5인 프레임은 실패 판정에서 빼고(연속 구간을 끊는다) 가림 프레임 수로 따로 적는다.
"""
from collections import Counter

import cv2
import numpy as np

from .hungarian import gated_assignment
from .motion import MotionDetector
from .tracker import iou_matrix

MATCH_IOU = 0.3
MERGED = -1          # 한 덩어리 박스에 덮인 프레임 표시
MERGE_COVER = 0.5
SWITCH_PERSIST = 5
FAIL_FRAMES = 10
VISIBLE = 0.5


# ---------------------------------------------------------------- 실행

def read_frames(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없다: {path}")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        yield frame
    cap.release()


def detect_video(path, params):
    """영상 전체의 프레임별 검출 목록. 추적기 비교 실험은 이 결과를 재사용한다."""
    det = MotionDetector(params)
    return [det(f)[0] for f in read_frames(path)]


def track_detections(detections, tracker):
    """프레임별 [(id, bbox, centroid)] — 이번 프레임에 검출과 짝지어진(화면에 표시되는) 추적만."""
    out = []
    for d in detections:
        tracker.update(d)
        out.append([(t.id, t.bbox, t.centroid) for t in tracker.visible_tracks()])
    return out


# ---------------------------------------------------------------- 대응

def match_frame(gt_objs, tracks):
    """정답 객체 id → 추적 id (병합 박스에 덮였으면 MERGED, 짝 없으면 키 없음)."""
    objs = [o for o in gt_objs if o.get("bbox")]
    if not objs or not tracks:
        return {}
    gb = np.asarray([o["bbox"] for o in objs], float)
    tb = np.asarray([t[1] for t in tracks], float)
    ious = iou_matrix(gb, tb)
    ix = np.clip(np.minimum(gb[:, None, 0] + gb[:, None, 2], tb[None, :, 0] + tb[None, :, 2])
                 - np.maximum(gb[:, None, 0], tb[None, :, 0]), 0, None)
    iy = np.clip(np.minimum(gb[:, None, 1] + gb[:, None, 3], tb[None, :, 1] + tb[None, :, 3])
                 - np.maximum(gb[:, None, 1], tb[None, :, 1]), 0, None)
    cover = ix * iy / (gb[:, 2:3] * gb[:, 3:4])                # 정답 박스 중 추적 박스가 덮은 비율
    merged = (cover >= MERGE_COVER).sum(axis=0) >= 2            # 두 명 이상을 덮는 추적 박스
    inside = np.array([[g[0] <= t[2][0] <= g[0] + g[2] and g[1] <= t[2][1] <= g[1] + g[3] for t in tracks] for g in gb])
    ok = ((ious >= MATCH_IOU) | inside) & ~merged[None, :]
    cost = np.where(ok, 1.0 - ious, 2.0)
    pairs, rest, _ = gated_assignment(cost, 1.0, "hungarian")
    out = {objs[i]["id"]: tracks[j][0] for i, j in pairs}
    for i in rest:
        if any(merged[j] and cover[i, j] >= MERGE_COVER for j in range(len(tracks))):
            out[objs[i]["id"]] = MERGED
    return out


def sequences(gt, outputs, ids=None):
    """정답 객체별 (프레임별 추적 id 목록, 프레임별 가시율 목록)과 프레임별 대응 표."""
    frames = gt["gt"]
    if ids is None:
        ids = [k for k in gt["objects"] if k != "T"]
    seq = {k: [None] * len(frames) for k in ids}
    vis = {k: [0.0] * len(frames) for k in ids}
    for i, (objs, tracks) in enumerate(zip(frames, outputs)):
        objs = [o for o in objs if o["id"] in seq]
        for o in objs:
            vis[o["id"]][i] = o["vis"] if o.get("bbox") else 0.0
        for k, tid in match_frame(objs, tracks).items():
            seq[k][i] = tid
    return seq, vis


def stable_switches(seq, persist=SWITCH_PERSIST):
    """ID Switch 목록 [(전환 시작 프레임, 이전 id, 새 id)]과 프레임별 '확정 id'."""
    switches = []
    current = None
    cand, cand_start, cand_count = None, None, 0
    established = [None] * len(seq)
    for i, tid in enumerate(seq):
        if tid is not None and tid != MERGED:
            if tid == current:
                cand, cand_count = None, 0
            else:
                if tid != cand:
                    cand, cand_start, cand_count = tid, i, 0
                cand_count += 1
                if cand_count >= persist:
                    if current is not None:
                        switches.append((cand_start, current, cand))
                    current = cand
                    cand, cand_count = None, 0
        established[i] = current
    return switches, established


def failure_runs(seq, vis, min_len=FAIL_FRAMES, visible=VISIBLE):
    """보이는데 짝이 없는 연속 구간 중 min_len 이상인 것 [(시작, 끝)]. 가림 프레임은 구간을 끊는다."""
    runs = []
    start = None
    for i, (tid, v) in enumerate(zip(list(seq) + [0], list(vis) + [0.0])):
        missing = tid is None and v >= visible
        if missing and start is None:
            start = i
        elif not missing and start is not None:
            if i - start >= min_len:
                runs.append((start, i - 1))
            start = None
    return runs


# ---------------------------------------------------------------- 지표

def evaluate_tracking(gt, outputs):
    """시나리오 하나의 전체 지표와 이벤트별 판정."""
    seq, vis = sequences(gt, outputs)
    per_obj = {}
    for k in seq:
        sw, est = stable_switches(seq[k])
        fails = failure_runs(seq[k], vis[k])
        present = [i for i, v in enumerate(vis[k]) if v >= VISIBLE]
        matched = [seq[k][i] for i in present if seq[k][i] not in (None, MERGED)]
        dominant = Counter(matched).most_common(1)[0][0] if matched else None
        per_obj[k] = {
            "switches": sw, "fails": fails, "present": len(present),
            "coverage": len(matched) / len(present) if present else 0.0,
            "retention": sum(1 for t in matched if t == dominant) / len(present) if present else 0.0,
            "ids": sorted(set(matched)), "dominant": dominant,
            "occluded": sum(1 for v in vis[k] if 0 < v < VISIBLE),
            "merged": sum(1 for t in seq[k] if t == MERGED),
        }
    # 정답에 거의 붙지 않은 추적 ID = 유령·오검출 (그림자, 조명, 배경에 남은 자국)
    life = Counter(t[0] for frame in outputs for t in frame)
    hit = Counter(tid for k in seq for tid in seq[k] if tid not in (None, MERGED))
    false_ids = sorted(t for t, n in life.items() if n >= 5 and hit[t] < 0.5 * n)
    events = []
    starts = [e["start"] for e in gt["events"]]
    for n, e in enumerate(gt["events"]):
        s, end = e["start"], e["end"]
        if n + 1 < len(starts) and end >= starts[n + 1]:   # 구간이 겹치면 다음 이벤트 직전까지만 센다
            end = starts[n + 1] - 1
        ev = {"index": e["index"], "kind": e["kind"], "label": e["label"], "start": s, "end": end,
              "extra": bool(e.get("extra")), "switches": 0, "fails": 0, "occluded": 0, "ids": {}, "memo": []}
        for k in e["objects"]:
            if k not in per_obj:
                continue
            o = per_obj[k]
            ns = [x for x in o["switches"] if s <= x[0] <= end]
            nf = [x for x in o["fails"] if x[0] <= end and x[1] >= s]
            ev["switches"] += len(ns)
            ev["fails"] += len(nf)
            ev["occluded"] += sum(1 for i in range(s, end + 1) if 0 < vis[k][i] < VISIBLE)
            ids = [seq[k][i] for i in range(s, end + 1) if seq[k][i] not in (None, MERGED)]
            ev["ids"][k] = [i for i, _ in Counter(ids).most_common()] if ids else []
            for f, a, b in ns:
                ev["memo"].append(f"{k}: ID {a}→{b} (f{f})")
            for a, b in nf:
                ev["memo"].append(f"{k}: {b - a + 1}프레임 미검출 (f{a}–{b})")
        merged = [i for i in range(s, end + 1) if any(k in seq and seq[k][i] == MERGED for k in e["objects"])]
        if merged:
            ev["memo"].append(f"한 덩어리로 검출 {len(merged)}프레임")
        ev["merged"] = len(merged)
        if ev["occluded"]:
            ev["memo"].append(f"50% 이상 가림 {ev['occluded']}프레임 (실패 판정 제외)")
        events.append(ev)
    counted = [e for e in events if not e["extra"]]
    total_present = sum(o["present"] for o in per_obj.values())
    return {
        "scenario": gt["scenario"], "split": gt["split"], "video": gt["video"], "frames": gt["frames"],
        "tests": len(counted),
        "switch_events": sum(1 for e in counted if e["switches"]),
        "switches": sum(e["switches"] for e in counted),
        "fail_events": sum(1 for e in counted if e["fails"]),
        "fails": sum(e["fails"] for e in counted),
        "id_switch_total": sum(len(o["switches"]) for o in per_obj.values()),
        "fail_total": sum(len(o["fails"]) for o in per_obj.values()),
        "coverage": sum(o["coverage"] * o["present"] for o in per_obj.values()) / max(total_present, 1),
        "retention": sum(o["retention"] * o["present"] for o in per_obj.values()) / max(total_present, 1),
        "ids_used": len(life), "false_ids": len(false_ids), "gt_objects": len(per_obj),
        "events": events,
        "objects": {k: {**{kk: vv for kk, vv in o.items() if kk not in ("switches", "fails")},
                        "n_switches": len(o["switches"]), "n_fails": len(o["fails"])} for k, o in per_obj.items()},
    }


def log_rows(result):
    """미션의 기록 템플릿: 영상명 - 조건 - 프레임 범위 - ID Switch 수 - 실패 수 - 관찰 메모."""
    rows = []
    for e in result["events"]:
        rows.append({"video": result["video"], "condition": e["label"] + (" (참고)" if e["extra"] else ""),
                     "frames": f"{e['start']}–{e['end']}", "id_switch": e["switches"], "fail": e["fails"],
                     "memo": "; ".join(e["memo"]) or "이상 없음"})
    return rows


# ---------------------------------------------------------------- 배경 모델 (전경 마스크)

def mask_scores(pred, truth):
    """전경 마스크의 정밀도·재현율·F1 (A5-1의 분류 지표를 픽셀에 적용)."""
    p = pred > 0
    tp = int(np.count_nonzero(p & truth))
    fp = int(np.count_nonzero(p & ~truth))
    fn = int(np.count_nonzero(~p & truth))
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1}


# ---------------------------------------------------------------- 침입 구역 (보너스 2)

def zone_ground_truth(gt, rect, obj="A"):
    """정답 박스 중심이 구역에 들어가는 프레임 구간 [(들어간 프레임, 나온 프레임)]."""
    x, y, w, h = rect
    inside_prev, start, spans = False, None, []
    for i, objs in enumerate(gt["gt"]):
        o = next((o for o in objs if o["id"] == obj and o.get("bbox")), None)
        inside = False
        if o is not None:
            bx, by, bw, bh = o["bbox"]
            cx, cy = bx + bw / 2, by + bh / 2
            inside = x <= cx <= x + w and y <= cy <= y + h
        if inside and not inside_prev:
            start = i
        if not inside and inside_prev:
            spans.append((start, i - 1))
        inside_prev = inside
    if inside_prev:
        spans.append((start, len(gt["gt"]) - 1))
    return spans
