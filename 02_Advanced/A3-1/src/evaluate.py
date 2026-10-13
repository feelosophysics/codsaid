"""정량 평가: 정답 꼭짓점과 비교해 성공·부분 성공·실패를 판정하고, 파라미터·규칙 실험을 한다.

판정 기준 (정답 사각형의 긴 대각선 길이 D 기준, 네 꼭짓점 중 가장 큰 오차 e):
  성공       e ≤ 2% D   네 꼭짓점이 문서 모서리에 맞아 반듯하게 펴짐
  부분 성공  e ≤ 5% D   펴지긴 했으나 가장자리가 잘리거나 남음
  실패       e > 5% D 또는 사각형을 찾지 못함
결과가 90° 단위로 돌아간 것(시작 꼭짓점 차이)은 오차에 넣지 않고 따로 기록한다.

labels.json이 없는 폴더(정답 꼭짓점 없는 실제 사진)는 검출 여부만 기록한다.
tools/annotate_corners.py로 꼭짓점을 찍으면 같은 기준으로 평가된다.
"""
import itertools
import json
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from . import geometry
from .image_io import imread, list_images
from .scanner import ScanParams, scan

SUCCESS_RATIO = 0.02
PARTIAL_RATIO = 0.05
STATUS_KO = {"success": "성공", "partial": "부분 성공", "fail": "실패", "unknown": "정답 없음"}


def limit_threads(n):
    """OpenCV 내부 병렬 스레드 수를 제한한다 (다른 작업과 CPU를 나눠 쓸 때)."""
    if n and n > 0:
        cv2.setNumThreads(int(n))


def load_dataset(folder):
    """이미지와 라벨 목록. labels.json이 없으면 파일 이름만으로 만든다."""
    folder = Path(folder)
    label_file = folder / "labels.json"
    if label_file.is_file():
        doc = json.loads(label_file.read_text(encoding="utf-8"))
        labels = doc["images"]
    else:
        labels = [{"id": p.stem, "file": p.name, "condition": "unknown", "condition_name": "미분류", "corners": None}
                  for p in list_images(folder)]
    return [(lab, imread(folder / lab["file"])) for lab in labels]


def diagonal(quad):
    q = geometry.as_points(quad)
    return max(np.linalg.norm(q[0] - q[2]), np.linalg.norm(q[1] - q[3]))


def judge(result, label):
    """ScanResult 하나를 정답과 비교한 평가 행."""
    row = {"id": label["id"], "condition": label.get("condition", "unknown"),
           "condition_name": label.get("condition_name", ""), "found": result.found, "reason": result.reason,
           "n_contours": len(result.contours), "n_candidates": len(result.candidates),
           "candidate_vertices": [len(c) for c in result.candidates[:5]]}
    truth = label.get("corners")
    if result.found:
        row["quad"] = result.quad.round(2).tolist()
        row["aspect_method"] = result.aspect["method"]
        row["aspect_estimated"] = result.aspect["estimated"]
        row["distance_aspect"] = _distance_aspect(result.quad)
    if truth is None:
        row["status"] = "unknown" if result.found else "fail"
        return row
    if not result.found:
        row["status"] = "fail"
        return row
    max_err, mean_err, shift = geometry.corner_error(result.quad, truth)
    ratio = max_err / diagonal(truth)
    row.update(max_error_px=max_err, mean_error_px=mean_err, error_ratio=ratio, rotation_shift=shift)
    row["status"] = "success" if ratio <= SUCCESS_RATIO else "partial" if ratio <= PARTIAL_RATIO else "fail"
    if "true_aspect" in label:
        true = label["true_aspect"] if shift % 2 == 0 else 1 / label["true_aspect"]
        row["aspect_true"] = true
        row["aspect_error"] = abs(row["aspect_estimated"] - true) / true
        row["distance_aspect_error"] = abs(row["distance_aspect"] - true) / true
    return row


def _distance_aspect(quad):
    w, h = geometry.output_size_by_distance(quad)
    return w / h


def evaluate(dataset, params=None, warp=False):
    """데이터셋 전체를 같은 파라미터로 평가한다. warp=True면 ScanResult도 함께 돌려준다."""
    rows, results = [], []
    for label, image in dataset:
        result = scan(image, params, warp=warp)
        rows.append(judge(result, label))
        if warp:
            results.append(result)
    return (rows, results) if warp else rows


def summarize(rows):
    """조건별 성공·부분 성공·실패 수와 성공률."""
    order = []
    for r in rows:
        if r["condition"] not in order:
            order.append(r["condition"])
    table = []
    for cond in order + ["all"]:
        sel = rows if cond == "all" else [r for r in rows if r["condition"] == cond]
        n = len(sel)
        s = sum(r["status"] == "success" for r in sel)
        p = sum(r["status"] == "partial" for r in sel)
        name = "전체" if cond == "all" else sel[0].get("condition_name") or cond
        table.append({"condition": cond, "name": name, "n": n, "success": s, "partial": p,
                      "fail": n - s - p, "success_rate": s / n if n else 0.0})
    return table


# ───────────────────────── 파라미터 탐색 ─────────────────────────

SWEEP_BLUR = (1, 3, 5, 7, 9, 11, 13)
SWEEP_LOW = (10, 25, 50, 75, 100, 150, 200)
SWEEP_HIGH = (50, 100, 150, 200, 250, 300, 400)


def sweep_configs():
    return [(b, lo, hi) for b, lo, hi in itertools.product(SWEEP_BLUR, SWEEP_LOW, SWEEP_HIGH) if lo < hi]


def parameter_sweep(dataset, base=None, progress=None):
    """(블러, Canny low, high) 조합마다 이미지별 판정을 기록한다.

    반환: configs 목록, status 행렬 (이미지 × 조합, 2=성공 1=부분 0=실패), 이미지 id 목록
    """
    base = base or ScanParams()
    configs = sweep_configs()
    ids = [lab["id"] for lab, _ in dataset]
    code = {"success": 2, "partial": 1, "fail": 0, "unknown": 1}
    matrix = np.zeros((len(dataset), len(configs)), np.int8)
    for j, (b, lo, hi) in enumerate(configs):
        params = replace(base, blur=b, canny_low=lo, canny_high=hi)
        for i, (label, image) in enumerate(dataset):
            matrix[i, j] = code[judge(scan(image, params, warp=False), label)["status"]]
        if progress and (j + 1) % 20 == 0:
            progress(j + 1, len(configs))
    return configs, matrix, ids


def sweep_summary(configs, matrix, ids, default=(5, 50, 150)):
    """파라미터 딜레마를 숫자로 요약한다."""
    success = matrix == 2
    per_config = success.sum(axis=0)
    best = int(per_config.max())
    best_idx = [j for j in range(len(configs)) if per_config[j] == best]
    per_image_any = success.any(axis=1)
    per_image_rate = success.mean(axis=1)
    default_idx = configs.index(tuple(default))
    # 이미지 A의 최적 조합이 이미지 B에서 실패하는 예: 성공 조합이 서로 겹치지 않는 쌍
    disjoint = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            if success[a].any() and success[b].any() and not (success[a] & success[b]).any():
                disjoint.append((ids[a], ids[b]))
    return {
        "n_configs": len(configs),
        "default": {"config": list(default), "success": int(per_config[default_idx])},
        "best": {"success": best, "configs": [list(configs[j]) for j in best_idx]},
        "oracle_success": int(per_image_any.sum()),
        "never_success": [ids[i] for i in range(len(ids)) if not per_image_any[i]],
        "per_image_success_rate": {ids[i]: float(per_image_rate[i]) for i in range(len(ids))},
        "disjoint_pairs": disjoint,
        "per_config_success": per_config.tolist(),
    }


# ───────────────────────── 규칙 추가 실험 ─────────────────────────

RULE_VARIANTS = [
    ("V0 기본 규칙", {}),
    ("V1 닫힘 연산 제거", {"close_kernel": 0}),
    ("V2 + 색 채널별 엣지", {"color_edges": True}),
    ("V3 + 자동 Canny 임계값", {"auto_canny": True}),
    ("V4 + CLAHE 대비 향상", {"clahe": True}),
    ("V5 + 근사 허용 오차 2배", {"approx_epsilon": 0.04}),
    ("V6 V2~V5 모두", {"color_edges": True, "auto_canny": True, "clahe": True, "approx_epsilon": 0.04}),
]


def rule_experiment(dataset, base=None):
    """규칙을 하나씩 더하거나 뺐을 때 이미지별 판정이 어떻게 바뀌는지 기록한다."""
    base = base or ScanParams()
    out = []
    baseline = None
    for name, change in RULE_VARIANTS:
        rows = evaluate(dataset, replace(base, **change))
        status = {r["id"]: r["status"] for r in rows}
        entry = {"name": name, "change": change, "status": status,
                 "success": sum(v == "success" for v in status.values())}
        if baseline is None:
            baseline = status
        else:
            entry["fixed"] = [k for k in status if status[k] == "success" and baseline[k] != "success"]
            entry["broken"] = [k for k in status if status[k] != "success" and baseline[k] == "success"]
        out.append(entry)
    return out
