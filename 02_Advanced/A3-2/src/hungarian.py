"""Hungarian Algorithm (보너스 1) — NumPy만으로 구현한 최소 비용 할당.

n×m 비용 행렬에서 행마다 서로 다른 열을 하나씩 골라 비용 합을 최소로 만든다(n ≤ m, 아니면 전치해서 푼다).
쿤–먼크레스의 포텐셜 방식(최단 증가 경로)을 쓴다. 행을 하나씩 추가하며, 지금까지의 할당을 유지한 채
'줄인 비용' c[i, j] − u[i] − v[j] 가 0인 간선만으로 새 행을 잇는 경로를 찾는다. 경로가 없으면 포텐셜을
가장 작은 줄인 비용 δ만큼 옮겨 새 0 간선을 만든다. 행 하나에 O(n·m), 전체 O(n²·m).

비교용으로 같은 파일에 탐욕(Greedy) 할당과 완전 탐색(작은 행렬 검증용)도 둔다.
"""
from itertools import permutations

import numpy as np


def hungarian(cost):
    """최소 비용 할당. (행 인덱스 배열, 열 인덱스 배열)을 행 순서로 돌려준다."""
    cost = np.asarray(cost, dtype=float)
    if cost.ndim != 2:
        raise ValueError("비용 행렬은 2차원이어야 한다")
    if cost.size == 0:
        return np.empty(0, int), np.empty(0, int)
    if not np.all(np.isfinite(cost)):
        raise ValueError("비용에 inf/NaN이 있으면 안 된다 (게이트는 큰 유한값으로 표현)")
    transposed = cost.shape[0] > cost.shape[1]
    if transposed:
        cost = cost.T
    n, m = cost.shape
    u = np.zeros(n + 1)            # 행 포텐셜 (1부터)
    v = np.zeros(m + 1)            # 열 포텐셜, v[0]은 가상 열
    p = np.zeros(m + 1, int)       # p[j] = 열 j에 할당된 행 (0이면 비어 있음)
    way = np.zeros(m + 1, int)     # 증가 경로 역추적용: 열 j 직전에 지난 열
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(m + 1, np.inf)
        used = np.zeros(m + 1, bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            free = ~used[1:]
            cur = cost[i0 - 1] - u[i0] - v[1:]          # 행 i0에서 각 열로 가는 줄인 비용
            better = free & (cur < minv[1:])
            minv[1:][better] = cur[better]
            way[1:][better] = j0
            cand = np.where(free, minv[1:], np.inf)
            j1 = int(np.argmin(cand)) + 1
            delta = cand[j1 - 1]
            u[p[used]] += delta                          # 트리에 든 행·열의 포텐셜 이동
            v[used] -= delta
            minv[1:][free] -= delta
            j0 = j1
            if p[j0] == 0:                               # 빈 열에 닿으면 증가 경로 완성
                break
        while j0:                                        # 경로를 따라 할당을 한 칸씩 민다
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    cols = np.nonzero(p[1:])[0]
    rows = p[1:][cols] - 1
    if transposed:
        rows, cols = cols, rows
    order = np.argsort(rows)
    return rows[order], cols[order]


def greedy(cost):
    """탐욕 할당: 전체 쌍을 비용 오름차순으로 보며, 행과 열이 둘 다 비어 있으면 짝짓는다."""
    cost = np.asarray(cost, dtype=float)
    if cost.size == 0:
        return np.empty(0, int), np.empty(0, int)
    order = np.argsort(cost, axis=None, kind="stable")
    used_r, used_c = set(), set()
    rows, cols = [], []
    for flat in order:
        r, c = divmod(int(flat), cost.shape[1])
        if r in used_r or c in used_c:
            continue
        used_r.add(r)
        used_c.add(c)
        rows.append(r)
        cols.append(c)
        if len(rows) == min(cost.shape):
            break
    rows, cols = np.array(rows, int), np.array(cols, int)
    order = np.argsort(rows)
    return rows[order], cols[order]


def brute_force(cost):
    """작은 행렬의 정답 (검증용). 최소 비용 합을 돌려준다."""
    cost = np.asarray(cost, dtype=float)
    if cost.shape[0] > cost.shape[1]:
        cost = cost.T
    n, m = cost.shape
    return min(cost[np.arange(n), list(perm)].sum() for perm in permutations(range(m), n))


def gated_assignment(cost, gate, method="hungarian"):
    """게이트(허용 최대 비용)를 넘는 쌍은 짝짓지 않는다. (짝 목록, 남은 행, 남은 열) 반환.

    헝가리안은 게이트 밖 쌍을 '아주 비싼' 유한값으로 바꿔 풀고, 결과에서 그런 쌍을 버린다.
    """
    cost = np.asarray(cost, dtype=float)
    n, m = cost.shape
    if n == 0 or m == 0:
        return [], list(range(n)), list(range(m))
    valid = cost <= gate
    if method == "hungarian":
        big = (np.abs(cost[valid]).sum() + 1.0) * 10 if valid.any() else 1.0
        rows, cols = hungarian(np.where(valid, cost, big))
    elif method == "greedy":
        rows, cols = greedy(np.where(valid, cost, np.inf))
    else:
        raise ValueError(f"알 수 없는 할당 방식: {method}")
    pairs = [(int(r), int(c)) for r, c in zip(rows, cols) if valid[r, c]]
    mr = {r for r, _ in pairs}
    mc = {c for _, c in pairs}
    return pairs, [r for r in range(n) if r not in mr], [c for c in range(m) if c not in mc]
