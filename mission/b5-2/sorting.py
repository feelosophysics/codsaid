"""
sorting.py — 정렬 알고리즘 모듈
=================================

이 모듈은 두 가지 정렬 알고리즘을 직접 구현합니다:

1. 머지 정렬 (Merge Sort)  — 안정 정렬, O(n log n) 보장
2. 퀵 정렬 (Quick Sort)    — 불안정 정렬, 평균 O(n log n), 최악 O(n²)

그리고 보너스 과제 5.3을 위한 성능 비교 함수도 포함합니다.

════════════════════════════════════════════
★ 미션 제약: sorted()와 list.sort() 사용 금지 ★
════════════════════════════════════════════

────────────────────────────────────────────
정렬 알고리즘의 핵심 개념들
────────────────────────────────────────────

■ 안정 정렬(Stable Sort)이란?
  같은 키(key)를 가진 원소들의 상대적 순서가 정렬 후에도 유지되는 정렬입니다.
  예: [(Alice, 3), (Bob, 1), (Charlie, 3)]을 숫자 기준으로 정렬하면
  - 안정 정렬: [(Bob, 1), (Alice, 3), (Charlie, 3)]  ← Alice가 Charlie보다 먼저 (원래 순서 유지)
  - 불안정 정렬: [(Bob, 1), (Charlie, 3), (Alice, 3)]  ← 순서가 바뀔 수 있음

■ 시간복잡도(Time Complexity):
  - 머지 정렬: 항상 O(n log n) — 최선, 평균, 최악 모두 동일
  - 퀵 정렬:   평균 O(n log n), 최악 O(n²)
    최악의 경우: 피벗이 항상 최솟값/최댓값일 때 (이미 정렬된 배열에서 첫/마지막 원소를 피벗으로 선택)

■ 공간복잡도(Space Complexity):
  - 머지 정렬: O(n) — 병합 시 임시 배열이 필요
  - 퀵 정렬:   O(log n) 평균 (재귀 스택) — in-place 정렬이므로 추가 배열 불필요

■ 비교 기반 정렬의 하한:
  비교 기반 정렬은 이론적으로 Ω(n log n)보다 빠를 수 없습니다.
  머지 정렬과 퀵 정렬(평균)은 모두 이 하한에 도달하는 최적 알고리즘입니다.

────────────────────────────────────────────
key_func 패턴 (비교 기준 주입)
────────────────────────────────────────────
정렬 알고리즘에 key_func을 전달하면,
같은 알고리즘으로 다양한 기준으로 정렬할 수 있습니다.

예:
  merge_sort(commits, key_func=lambda c: c.timestamp)  → 시간순 정렬
  merge_sort(commits, key_func=lambda c: c.author)     → 작성자순 정렬

이것은 "전략 패턴(Strategy Pattern)"의 간단한 형태입니다.
Python의 sorted(key=...) 도 같은 원리입니다.
"""

import time  # 보너스 과제: 성능 벤치마크에 사용
import hashlib  # 보너스 과제: 더미 커밋 생성에 사용


def merge_sort(arr, key_func=None):
    """
    머지 정렬(Merge Sort)을 수행합니다.

    ── 알고리즘 개요 ──
    "분할 정복(Divide and Conquer)" 전략을 사용합니다:
    1. 분할(Divide):  배열을 절반으로 나눕니다.
    2. 정복(Conquer): 각 절반을 재귀적으로 정렬합니다.
    3. 결합(Combine): 두 정렬된 절반을 병합(merge)합니다.

    ── 동작 예시 ──
    [38, 27, 43, 3, 9, 82, 10]
       분할 →
    [38, 27, 43, 3]    [9, 82, 10]
       분할 →
    [38, 27] [43, 3]   [9, 82] [10]
       분할 →
    [38] [27] [43] [3] [9] [82] [10]
       병합 →
    [27, 38] [3, 43]   [9, 82] [10]
       병합 →
    [3, 27, 38, 43]    [9, 10, 82]
       병합 →
    [3, 9, 10, 27, 38, 43, 82]

    ── 안정 정렬인 이유 ──
    병합(merge) 단계에서 두 원소의 키가 같을 때,
    왼쪽 배열의 원소를 먼저 선택합니다.
    왼쪽 배열은 원래 배열에서 더 앞에 있었으므로,
    상대적 순서가 유지됩니다.

    ── 시간복잡도 분석 ──
    - 분할: 매번 배열을 절반으로 나누므로, log n 단계가 있습니다.
    - 각 단계: 모든 원소를 한 번씩 비교하므로, O(n)입니다.
    - 총: O(n log n) — 최선, 평균, 최악 모두 동일!

    ── 공간복잡도 ──
    O(n): 병합 시 임시 배열(left, right)이 필요합니다.

    Args:
        arr (list): 정렬할 리스트
        key_func (callable, optional): 비교 기준 함수
            예: lambda x: x.timestamp → 타임스탬프 기준 정렬
            None이면 원소 자체를 기준으로 비교합니다.

    Returns:
        list: 정렬된 새 리스트 (원본은 변경되지 않음)
    """
    # ── key_func이 None이면 항등 함수를 사용 ──
    # 항등 함수: 입력을 그대로 반환하는 함수
    # 이렇게 하면 아래 코드에서 key_func(x)를 항상 사용할 수 있습니다.
    if key_func is None:
        key_func = lambda x: x

    # ── 기저 조건(Base Case) ──
    # 원소가 0개 또는 1개이면 이미 정렬된 것입니다.
    # 재귀를 멈추는 조건입니다.
    if len(arr) <= 1:
        return arr[:]  # 복사본을 반환 (원본 보호)

    # ── 분할(Divide) ──
    # 배열을 절반으로 나눕니다.
    mid = len(arr) // 2         # 중간 인덱스 (정수 나눗셈)
    left = merge_sort(arr[:mid], key_func)   # 왼쪽 절반 재귀 정렬
    right = merge_sort(arr[mid:], key_func)  # 오른쪽 절반 재귀 정렬

    # ── 결합(Combine): 두 정렬된 배열을 병합 ──
    return _merge(left, right, key_func)


def _merge(left, right, key_func):
    """
    두 정렬된 배열을 하나의 정렬된 배열로 병합합니다.

    ── 병합의 핵심 원리 ──
    두 배열의 "맨 앞 원소"를 비교하여, 더 작은 것을 결과에 추가합니다.
    두 배열 모두 이미 정렬되어 있으므로, 맨 앞이 항상 해당 배열의 최솟값입니다.

    ── 안정성 보장 ──
    left[i]의 키와 right[j]의 키가 같으면, left[i]를 먼저 선택합니다.
    (left는 원래 배열에서 더 앞에 있었으므로)
    조건문에서 <= 을 사용하는 것이 핵심입니다.

    Args:
        left (list): 정렬된 왼쪽 배열
        right (list): 정렬된 오른쪽 배열
        key_func (callable): 비교 기준 함수

    Returns:
        list: 병합된 정렬 배열
    """
    result = []  # 병합 결과를 저장할 배열
    i = 0  # left 배열의 현재 인덱스
    j = 0  # right 배열의 현재 인덱스

    # ── 두 배열 모두 원소가 남아있는 동안 비교하며 병합 ──
    while i < len(left) and j < len(right):
        # key_func으로 비교 기준값을 추출합니다.
        left_key = key_func(left[i])
        right_key = key_func(right[j])

        # <= 을 사용하여 안정성을 보장합니다.
        # 같은 키면 왼쪽(원래 앞에 있던 것)을 먼저 선택합니다.
        if left_key <= right_key:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # ── 남은 원소를 모두 추가 ──
    # 한쪽 배열이 먼저 소진되면, 다른 배열의 나머지를 모두 추가합니다.
    while i < len(left):
        result.append(left[i])
        i += 1

    while j < len(right):
        result.append(right[j])
        j += 1

    return result


def quick_sort(arr, key_func=None):
    """
    퀵 정렬(Quick Sort)을 수행합니다.

    ── 알고리즘 개요 ──
    "분할 정복" 전략을 사용하지만, 머지 정렬과 방식이 다릅니다:
    1. 피벗(Pivot) 선택: 배열에서 기준 원소를 하나 선택합니다.
    2. 분할(Partition):   피벗보다 작은 원소는 왼쪽, 큰 원소는 오른쪽으로 나눕니다.
    3. 재귀(Recurse):     왼쪽과 오른쪽을 각각 재귀적으로 정렬합니다.
    4. 결합: 이미 정렬되어 있으므로 추가 결합이 불필요합니다!

    ── 머지 정렬과의 차이 ──
    - 머지 정렬: "먼저 나누고, 나중에 합침" → 결합 비용이 큼
    - 퀵 정렬:   "나누면서 정렬" → 결합 비용이 없음

    ── 피벗 선택 전략: Median-of-Three ──
    피벗을 첫 번째, 중간, 마지막 원소 중 중앙값으로 선택합니다.
    이미 정렬된 배열에서 최악의 경우를 방지하기 위함입니다.

    이미 정렬된 배열 [1, 2, 3, 4, 5]에서:
    - 첫 번째 원소(1)를 피벗으로 선택하면: 분할이 극도로 불균형 → O(n²)
    - Median-of-Three(1, 3, 5 중 3)를 선택하면: 비교적 균형 → O(n log n)에 가까움

    ── 불안정 정렬인 이유 ──
    분할(partition) 과정에서 같은 키를 가진 원소들의 상대적 순서가
    보존되지 않을 수 있습니다.

    ── 시간복잡도 분석 ──
    - 평균: O(n log n) — 피벗이 대략 중앙값일 때
    - 최악: O(n²) — 피벗이 항상 최솟값/최댓값일 때 (극히 불균형 분할)
    - 최선: O(n log n) — 피벗이 정확히 중앙값일 때

    ── 공간복잡도 ──
    O(n): 이 구현에서는 새 리스트를 만들어 반환합니다.
    (In-place 구현은 O(log n)이지만, 코드가 복잡해집니다.)

    Args:
        arr (list): 정렬할 리스트
        key_func (callable, optional): 비교 기준 함수

    Returns:
        list: 정렬된 새 리스트 (원본은 변경되지 않음)
    """
    # ── key_func이 None이면 항등 함수를 사용 ──
    if key_func is None:
        key_func = lambda x: x

    # ── 기저 조건 ──
    if len(arr) <= 1:
        return arr[:]

    # ── 피벗 선택: Median-of-Three ──
    pivot = _select_pivot(arr, key_func)

    # ── 분할(Partition) ──
    # 피벗을 기준으로 세 그룹으로 나눕니다:
    # - less:    피벗보다 작은 원소들
    # - equal:   피벗과 같은 원소들 (3-way partition)
    # - greater: 피벗보다 큰 원소들
    # 3-way partition을 사용하면 중복 원소가 많을 때 효율적입니다.
    pivot_key = key_func(pivot)
    less = []     # 피벗보다 작은 원소들
    equal = []    # 피벗과 같은 원소들
    greater = []  # 피벗보다 큰 원소들

    for item in arr:
        item_key = key_func(item)
        if item_key < pivot_key:
            less.append(item)
        elif item_key > pivot_key:
            greater.append(item)
        else:
            equal.append(item)

    # ── 재귀 정렬 후 결합 ──
    # less와 greater만 재귀적으로 정렬합니다.
    # equal은 이미 "올바른 위치"에 있으므로 정렬할 필요 없습니다.
    return quick_sort(less, key_func) + equal + quick_sort(greater, key_func)


def _select_pivot(arr, key_func):
    """
    Median-of-Three 전략으로 피벗을 선택합니다.

    ── Median-of-Three란? ──
    배열의 첫 번째, 중간, 마지막 원소 중 중앙값(median)을 피벗으로 선택합니다.

    예: 배열 [7, 3, 9, ...] 에서 첫(7), 중(5), 끝(9)이면
    → 중앙값 = 7 → 7을 피벗으로 선택

    ── 왜 이 전략을 사용하는가? ──
    1. 첫 번째 원소를 항상 피벗으로 선택하면,
       이미 정렬된 배열에서 최악의 경우 O(n²)가 발생합니다.
    2. 랜덤 선택은 비결정적(non-deterministic)이라 테스트가 어렵습니다.
    3. Median-of-Three는 결정적이면서도 최악의 경우를 줄여줍니다.

    Args:
        arr (list): 피벗을 선택할 배열
        key_func (callable): 비교 기준 함수

    Returns:
        원소: 선택된 피벗 원소
    """
    # 원소가 2개 이하이면 그냥 첫 번째 원소를 반환합니다.
    if len(arr) <= 2:
        return arr[0]

    # 첫 번째, 중간, 마지막 원소를 후보로 선택합니다.
    first = arr[0]
    mid = arr[len(arr) // 2]
    last = arr[-1]

    # 세 후보의 키 값을 추출합니다.
    f_key = key_func(first)
    m_key = key_func(mid)
    l_key = key_func(last)

    # ── 세 값 중 중앙값(median) 찾기 ──
    # 세 값을 비교하여 중앙값을 결정합니다.
    # 중앙값 = 최대도 아니고 최소도 아닌 값
    if f_key <= m_key <= l_key or l_key <= m_key <= f_key:
        return mid   # mid가 중앙값
    elif m_key <= f_key <= l_key or l_key <= f_key <= m_key:
        return first  # first가 중앙값
    else:
        return last   # last가 중앙값


def benchmark_sorts(n_sizes=None):
    """
    [보너스 5.3] 두 정렬 알고리즘의 성능을 비교합니다.

    다양한 입력 크기에 대해 Merge Sort와 Quick Sort의 실행 시간을 측정하고,
    결과를 표 형태로 출력합니다.

    ── 벤치마크 방법론 ──
    1. 각 크기에 대해 동일한 무작위 데이터를 생성합니다.
    2. 같은 데이터에 대해 두 알고리즘을 각각 실행합니다.
    3. time.perf_counter()로 실행 시간을 측정합니다.
       (time.time()보다 더 정밀합니다.)

    ── 예상 결과 ──
    - 작은 입력: 두 알고리즘의 차이가 거의 없습니다.
    - 큰 입력:   Quick Sort가 약간 더 빠를 수 있습니다.
      (상수 인자가 작고, 캐시 효율이 좋으므로)
    - 이미 정렬된 입력: Quick Sort(Median-of-Three)도
      잘 작동하지만, 순수 첫번째 원소 피벗 선택 시 O(n²).

    Args:
        n_sizes (list, optional): 벤치마크할 입력 크기 목록.
            기본값: [10, 50, 100, 500, 1000, 3000, 5000]

    Returns:
        str: 벤치마크 결과 문자열 (표 형태)
    """
    # ── 기본 입력 크기 설정 ──
    if n_sizes is None:
        n_sizes = [10, 50, 100, 500, 1000, 3000, 5000]

    # ── 결과 문자열 구성 ──
    lines = []
    lines.append("=" * 65)
    lines.append("  Sorting Algorithm Benchmark: Merge Sort vs Quick Sort")
    lines.append("=" * 65)
    lines.append(f"{'Size':>8} | {'Merge Sort (s)':>16} | {'Quick Sort (s)':>16} | {'Winner':>8}")
    lines.append("-" * 65)

    for n in n_sizes:
        # ── 테스트 데이터 생성 ──
        # hashlib을 사용하여 결정적(deterministic) 무작위 데이터를 생성합니다.
        # 이렇게 하면 매번 같은 데이터로 테스트할 수 있어 재현 가능합니다.
        data = _generate_test_data(n)

        # ── Merge Sort 벤치마크 ──
        # 같은 데이터의 복사본으로 테스트합니다.
        data_copy1 = data[:]
        start = time.perf_counter()
        merge_sort(data_copy1)
        merge_time = time.perf_counter() - start

        # ── Quick Sort 벤치마크 ──
        data_copy2 = data[:]
        start = time.perf_counter()
        quick_sort(data_copy2)
        quick_time = time.perf_counter() - start

        # ── 승자 결정 ──
        if merge_time < quick_time:
            winner = "Merge"
        elif quick_time < merge_time:
            winner = "Quick"
        else:
            winner = "Tie"

        lines.append(
            f"{n:>8} | {merge_time:>16.6f} | {quick_time:>16.6f} | {winner:>8}"
        )

    lines.append("-" * 65)
    lines.append("")
    lines.append("Notes:")
    lines.append("  - Merge Sort: Stable, O(n log n) guaranteed")
    lines.append("  - Quick Sort: Unstable, O(n log n) avg, O(n^2) worst")
    lines.append("  - Merge Sort uses O(n) extra space")
    lines.append("  - Quick Sort (this impl) also uses O(n) extra space")
    lines.append("    (due to list creation; in-place version uses O(log n))")
    lines.append("=" * 65)

    return "\n".join(lines)


def _generate_test_data(n):
    """
    벤치마크용 결정적 테스트 데이터를 생성합니다.

    hashlib을 사용하여 인덱스를 해싱하고, 그 값을 정수로 변환합니다.
    이렇게 하면:
    - random 모듈 없이 "무작위처럼 보이는" 데이터를 생성할 수 있습니다.
    - 매번 실행할 때 같은 데이터가 생성되어 결과를 재현할 수 있습니다.

    Args:
        n (int): 생성할 데이터 크기

    Returns:
        list: n개의 정수 리스트
    """
    data = []
    for i in range(n):
        # 인덱스를 문자열로 변환하고 SHA-1 해싱합니다.
        hash_val = hashlib.sha1(str(i).encode()).hexdigest()
        # hex 문자열의 앞 8자리를 정수로 변환합니다.
        # int(hash_val[:8], 16): 16진수 문자열을 10진수 정수로 변환
        data.append(int(hash_val[:8], 16))
    return data
