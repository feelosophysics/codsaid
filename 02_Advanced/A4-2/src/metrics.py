"""평가 지표. 수식을 그대로 보이려고 직접 계산하고, 테스트에서 scikit-learn 결과와 대조한다."""
from __future__ import annotations

import math
import random
from collections import Counter


def prf(tp: int, fp: int, fn: int) -> dict:
    """정밀도 = TP/(TP+FP): 뽑은 것 중 맞은 비율. 재현율 = TP/(TP+FN): 정답 중 뽑은 비율.
    분모가 0이면 정의되지 않는다. 뽑은 게 없으면 정밀도 1.0(틀린 게 없음), 정답이 없으면 재현율 1.0으로 둔다."""
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def classification_report(y_true, y_pred) -> dict:
    """이진 분류(0=부정, 1=긍정). 정확도, 클래스별 P/R/F1, macro F1, 혼동 행렬."""
    cm = Counter(zip(y_true, y_pred))
    out = {"n": len(y_true), "accuracy": sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)}
    per = {}
    for c in (0, 1):
        tp = cm[(c, c)]
        fp = cm[(1 - c, c)]
        fn = cm[(c, 1 - c)]
        per[c] = prf(tp, fp, fn)
    out["negative"] = per[0]
    out["positive"] = per[1]
    out["macro_f1"] = (per[0]["f1"] + per[1]["f1"]) / 2
    out["confusion"] = [[cm[(0, 0)], cm[(0, 1)]], [cm[(1, 0)], cm[(1, 1)]]]  # 행=정답, 열=예측
    return out


def bootstrap_ci(y_true, y_pred, stat=lambda t, p: sum(a == b for a, b in zip(t, p)) / len(t),
                 n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """표본을 복원 추출로 다시 뽑아 지표의 95% 구간을 구한다. 1,000건 정확도는 대략 ±3%p 흔들린다."""
    rng = random.Random(seed)
    n = len(y_true)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        vals.append(stat([y_true[i] for i in idx], [y_pred[i] for i in idx]))
    vals.sort()
    return vals[int(n_boot * alpha / 2)], vals[int(n_boot * (1 - alpha / 2)) - 1]


def mcnemar_exact(y_true, pred_a, pred_b) -> dict:
    """같은 문장에 대한 두 분류기의 차이 검정. 한쪽만 맞힌 문장 수 b, c만 본다.
    차이가 없다면 b와 c는 반반이어야 하므로 이항분포 B(b+c, 0.5)에서 양측 p값을 구한다."""
    b = sum(a == t and p != t for t, a, p in zip(y_true, pred_a, pred_b))  # A만 맞음
    c = sum(a != t and p == t for t, a, p in zip(y_true, pred_a, pred_b))  # B만 맞음
    n = b + c
    if n == 0:
        return {"a_only": 0, "b_only": 0, "p_value": 1.0}
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return {"a_only": b, "b_only": c, "p_value": min(1.0, 2 * tail)}
