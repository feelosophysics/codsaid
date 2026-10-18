"""정량 평가: 정답 꼭짓점과 비교해 성공·부분 성공·실패를 판정하고, 파라미터·규칙 실험을 한다.

판정 기준 (정답 사각형의 긴 대각선 길이 D 기준, 네 꼭짓점 중 가장 큰 오차 e):
  성공       e ≤ 2% D   네 꼭짓점이 문서 모서리에 맞아 반듯하게 펴짐
  부분 성공  e ≤ 5% D   펴지긴 했으나 가장자리가 잘리거나 남음
  실패       e > 5% D 또는 사각형을 찾지 못함
결과가 90° 단위로 돌아간 것(시작 꼭짓점 차이)은 오차에 넣지 않고 따로 기록한다.

labels.json이 없는 폴더(정답 꼭짓점 없는 실제 사진)는 검출 여부만 기록한다.
tools/annotate_corners.py로 꼭짓점을 찍으면 같은 기준으로 평가된다.

E01 실행 결과: e = 1.98px, D = 1045.6px → 0.19% → 성공. 대각선으로 나누는 이유는 명함(작음)과 A4(큼)를
같은 기준으로 판정하기 위해서다. 같은 3px 오차라도 명함에서는 더 큰 실패다.
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
    """OpenCV 내부 병렬 스레드 수를 제한한다 (다른 작업과 CPU를 나눠 쓸 때).

    Args:
        n: 스레드 수. 0이나 None이면 제한하지 않는다.
    """
    if n and n > 0:  # n이 None이면 "n and ..."에서 바로 거짓이 되어 뒤의 비교를 하지 않는다
        cv2.setNumThreads(int(n))


def load_dataset(folder):
    """이미지와 라벨 목록. labels.json이 없으면 파일 이름만으로 만든다.

    Args:
        folder: 이미지 폴더. data/synthetic이면 labels.json의 정답 꼭짓점을 함께 읽는다.

    Returns:
        list: (label dict, BGR 이미지) 튜플의 목록. 합성 데이터는 20개.
        label에는 id, file, condition, condition_name, corners 등이 있다.
    """
    folder = Path(folder)
    label_file = folder / "labels.json"
    if label_file.is_file():
        # json.loads는 JSON 글자를 dict·list로 바꾼다. doc["images"]는 이미지마다 dict 한 개인 리스트다.
        doc = json.loads(label_file.read_text(encoding="utf-8"))
        labels = doc["images"]
    else:
        labels = [{"id": p.stem, "file": p.name, "condition": "unknown", "condition_name": "미분류", "corners": None}
                  for p in list_images(folder)]
    return [(lab, imread(folder / lab["file"])) for lab in labels]


def diagonal(quad):
    """사각형의 두 대각선 중 긴 쪽의 길이.

    Args:
        quad: TL, TR, BR, BL 순서의 네 점.

    Returns:
        numpy.float64: 긴 대각선 길이(픽셀). E01 정답은 1045.6.
    """
    q = geometry.as_points(quad)
    return max(np.linalg.norm(q[0] - q[2]), np.linalg.norm(q[1] - q[3]))  # TL–BR, TR–BL


def judge(result, label):
    """ScanResult 하나를 정답과 비교한 평가 행.

    Args:
        result: scan()의 ScanResult.
        label: 그 이미지의 라벨 dict. corners가 None이면 검출 여부만 기록한다.

    Returns:
        dict: id, condition, found, status 등. 검출하고 정답이 있으면 max_error_px, error_ratio,
        rotation_shift가, 정답 종횡비가 있으면 aspect_error도 들어간다.
        status는 "success", "partial", "fail", "unknown" 중 하나.
    """
    # label.get("condition", "unknown")은 키가 없으면 오류 대신 기본값을 준다. label["condition"]은 키가 없으면 오류다.
    row = {"id": label["id"], "condition": label.get("condition", "unknown"),
           "condition_name": label.get("condition_name", ""), "found": result.found, "reason": result.reason,
           "n_contours": len(result.contours), "n_candidates": len(result.candidates),
           "candidate_vertices": [len(c) for c in result.candidates[:5]]}  # 큰 후보 5개의 꼭짓점 수(실패 분석용)
    truth = label.get("corners")
    if result.found:
        row["quad"] = result.quad.round(2).tolist()  # tolist()는 배열을 JSON에 넣을 수 있는 파이썬 리스트로 바꾼다
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
    # update(이름=값, ...)는 여러 키를 한 번에 추가한다.
    row.update(max_error_px=max_err, mean_error_px=mean_err, error_ratio=ratio, rotation_shift=shift)
    # 조건식을 이어 쓴 형태: ratio ≤ 0.02면 "success", 아니고 ≤ 0.05면 "partial", 둘 다 아니면 "fail".
    row["status"] = "success" if ratio <= SUCCESS_RATIO else "partial" if ratio <= PARTIAL_RATIO else "fail"
    if "true_aspect" in label:
        # 시작점이 홀수 칸 돌았으면(90°, 270°) 결과의 가로·세로가 바뀐 것이라 정답 비율도 뒤집어 비교한다.
        true = label["true_aspect"] if shift % 2 == 0 else 1 / label["true_aspect"]
        row["aspect_true"] = true
        row["aspect_error"] = abs(row["aspect_estimated"] - true) / true  # 상대 오차. 0.05면 5%
        row["distance_aspect_error"] = abs(row["distance_aspect"] - true) / true
    return row


def _distance_aspect(quad):
    """변 길이 방법(보너스 2 기본형)으로 낸 가로/세로 비율.

    이름 앞의 _는 "이 파일 안에서만 쓰는 보조 함수"라는 관례다.

    Args:
        quad: TL, TR, BR, BL 순서의 원본 좌표.

    Returns:
        float: width / height.
    """
    w, h = geometry.output_size_by_distance(quad)
    return w / h


def evaluate(dataset, params=None, warp=False):
    """데이터셋 전체를 같은 파라미터로 평가한다. warp=True면 ScanResult도 함께 돌려준다.

    Args:
        dataset: load_dataset()의 결과.
        params: ScanParams. None이면 기본값.
        warp: True면 투시 변환까지 하고 ScanResult 목록도 돌려준다.

    Returns:
        list 또는 tuple: warp=False면 평가 행 목록, True면 (평가 행 목록, ScanResult 목록).
    """
    rows, results = [], []
    for label, image in dataset:  # 튜플 (label, image)를 두 변수로 나눠 받는다
        result = scan(image, params, warp=warp)
        rows.append(judge(result, label))
        if warp:
            results.append(result)
    return (rows, results) if warp else rows


def summarize(rows):
    """조건별 성공·부분 성공·실패 수와 성공률.

    Args:
        rows: judge()가 만든 평가 행 목록.

    Returns:
        list: 조건마다 dict 한 개, 마지막은 "all"(전체). 실행 결과 전체는 성공 12, 부분 2, 실패 6 → 60%.
    """
    # 처음 나온 순서를 지키며 조건 이름을 모은다(set은 순서를 보장하지 않으므로 리스트로).
    order = []
    for r in rows:
        if r["condition"] not in order:
            order.append(r["condition"])
    table = []
    for cond in order + ["all"]:  # 리스트 + 리스트는 이어 붙인 새 리스트
        sel = rows if cond == "all" else [r for r in rows if r["condition"] == cond]
        n = len(sel)
        # True는 1, False는 0으로 더해진다. sum(조건 for r in sel)은 조건을 만족하는 행의 수다.
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
    """탐색할 (블러, low, high) 조합 목록.

    Returns:
        list: low < high인 조합만 남긴 튜플 목록. 7 × 7 × 7 = 343개 중 266개.
    """
    # itertools.product는 세 목록의 모든 조합을 만든다: (1, 10, 50), (1, 10, 100), ...
    return [(b, lo, hi) for b, lo, hi in itertools.product(SWEEP_BLUR, SWEEP_LOW, SWEEP_HIGH) if lo < hi]


def parameter_sweep(dataset, base=None, progress=None):
    """(블러, Canny low, high) 조합마다 이미지별 판정을 기록한다.

    반환: configs 목록, status 행렬 (이미지 × 조합, 2=성공 1=부분 0=실패), 이미지 id 목록

    20장 × 266조합 = 5,320번 검출한다. warp=False로 꼭짓점까지만 찾아 시간을 줄인다.

    Args:
        dataset: load_dataset()의 결과.
        base: 블러·Canny 외의 값을 가져올 ScanParams.
        progress: 20조합마다 부를 함수 progress(완료 수, 전체 수). None이면 부르지 않는다.

    Returns:
        tuple: (configs, matrix, ids). matrix는 (20, 266) int8. matrix[i, j]는 i번 이미지를 j번 조합으로 판정한 값.
    """
    base = base or ScanParams()
    configs = sweep_configs()
    ids = [lab["id"] for lab, _ in dataset]
    code = {"success": 2, "partial": 1, "fail": 0, "unknown": 1}
    matrix = np.zeros((len(dataset), len(configs)), np.int8)  # (이미지 수, 조합 수). int8은 −128~127 정수
    for j, (b, lo, hi) in enumerate(configs):
        params = replace(base, blur=b, canny_low=lo, canny_high=hi)
        for i, (label, image) in enumerate(dataset):
            matrix[i, j] = code[judge(scan(image, params, warp=False), label)["status"]]  # 한 칸을 제자리에서 채운다
        if progress and (j + 1) % 20 == 0:
            progress(j + 1, len(configs))
    return configs, matrix, ids


def sweep_summary(configs, matrix, ids, default=(5, 50, 150)):
    """파라미터 딜레마를 숫자로 요약한다.

    실행 결과: 기본 조합 12/20, 최고 단일 조합 14/20, 이미지마다 최적 조합을 따로 골라도(oracle) 16/20.
    E03·S05·C03·C04는 어떤 조합으로도 성공하지 못했다. S04와 C02는 성공 조합이 하나도 겹치지 않는다.

    Args:
        configs: sweep_configs()의 목록.
        matrix: parameter_sweep()의 (이미지, 조합) 판정 행렬.
        ids: 이미지 id 목록. matrix의 행 순서와 같다.
        default: 기본 파라미터 조합.

    Returns:
        dict: n_configs, default, best, oracle_success, never_success, per_image_success_rate,
        disjoint_pairs, per_config_success.
    """
    success = matrix == 2  # (20, 266) True/False
    per_config = success.sum(axis=0)  # 열마다(조합마다) 성공한 이미지 수 → (266,)
    best = int(per_config.max())
    best_idx = [j for j in range(len(configs)) if per_config[j] == best]
    per_image_any = success.any(axis=1)  # 행마다(이미지마다) "한 조합이라도 성공했는가" → (20,)
    per_image_rate = success.mean(axis=1)  # 이미지마다 성공한 조합의 비율 → (20,)
    default_idx = configs.index(tuple(default))  # list.index(값)은 그 값이 처음 나오는 위치
    # 이미지 A의 최적 조합이 이미지 B에서 실패하는 예: 성공 조합이 서로 겹치지 않는 쌍
    disjoint = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):  # a보다 뒤의 b만 봐서 같은 쌍을 두 번 세지 않는다
            # success[a] & success[b]는 두 이미지가 함께 성공한 조합. .any()가 거짓이면 공통 성공 조합이 없다.
            if success[a].any() and success[b].any() and not (success[a] & success[b]).any():
                disjoint.append((ids[a], ids[b]))
    return {
        "n_configs": len(configs),
        "default": {"config": list(default), "success": int(per_config[default_idx])},
        "best": {"success": best, "configs": [list(configs[j]) for j in best_idx]},
        "oracle_success": int(per_image_any.sum()),
        "never_success": [ids[i] for i in range(len(ids)) if not per_image_any[i]],
        # {키식: 값식 for ...}는 dict 컴프리헨션이다.
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
    """규칙을 하나씩 더하거나 뺐을 때 이미지별 판정이 어떻게 바뀌는지 기록한다.

    실행 결과: V0 12/20 → V2(색 채널별 엣지) 15/20(E03·S04·T04 고침) → V6(모두) 15/20.
    규칙을 모두 더해도 C02·C03·C04·C05·S05는 남는다.

    Args:
        dataset: load_dataset()의 결과.
        base: 바꾸기 전의 ScanParams.

    Returns:
        list: 규칙마다 dict. name, change, status(이미지 id → 판정), success, 그리고 V0과 비교한 fixed·broken.
    """
    base = base or ScanParams()
    out = []
    baseline = None
    for name, change in RULE_VARIANTS:
        # **change는 dict를 이름=값 인자로 풀어 넣는다: replace(base, **{"clahe": True}) = replace(base, clahe=True).
        rows = evaluate(dataset, replace(base, **change))
        status = {r["id"]: r["status"] for r in rows}
        entry = {"name": name, "change": change, "status": status,
                 "success": sum(v == "success" for v in status.values())}
        if baseline is None:  # 첫 번째(V0)를 비교 기준으로 저장한다
            baseline = status
        else:
            entry["fixed"] = [k for k in status if status[k] == "success" and baseline[k] != "success"]
            entry["broken"] = [k for k in status if status[k] != "success" and baseline[k] == "success"]
        out.append(entry)
    return out
