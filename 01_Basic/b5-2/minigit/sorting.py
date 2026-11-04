"""직접 구현한 정렬 두 가지. Python의 표준 정렬 함수는 사용하지 않는다."""

from __future__ import annotations

import random
import time
from typing import Any, Callable


def _identity(value: Any) -> Any:
    """정렬 기준을 주지 않으면 원소 자체를 비교한다."""
    return value


def merge_sort(
    items: list[Any], key_func: Callable[[Any], Any] | None = None
) -> list[Any]:
    """머지 정렬. 새 리스트를 돌려주며, O(n log n) 시간·O(n) 추가 공간.

    같은 키에서는 왼쪽 원소를 먼저 뽑으므로 원래 상대 순서가 유지된다(안정 정렬).
    """
    if key_func is None:
        # 비교 기준을 생략하면 숫자나 문자열 원소 자체를 비교한다.
        key_func = _identity
    if len(items) <= 1:
        # [:]는 전체를 복사한다. 원본 리스트를 바꾸지 않는 정렬이다.
        return items[:]

    # //는 소수점 아래를 버리는 나눗셈. 길이 5라면 왼쪽 2개, 오른쪽 3개.
    middle = len(items) // 2
    # 함수가 자기 자신을 다시 부르는 재귀. 조각이 길이 1이 되면 위에서 멈춘다.
    left = merge_sort(items[:middle], key_func)
    right = merge_sort(items[middle:], key_func)
    return _merge(left, right, key_func)


def _merge(
    left: list[Any], right: list[Any], key_func: Callable[[Any], Any]
) -> list[Any]:
    """이미 정렬된 두 조각의 앞에서부터 작은 쪽을 결과에 넣는다."""
    result: list[Any] = []
    left_index = 0
    right_index = 0
    # 두 조각의 현재 맨 앞 값을 비교하고, 선택한 쪽의 위치만 1 증가시킨다.
    while left_index < len(left) and right_index < len(right):
        if key_func(left[left_index]) <= key_func(right[right_index]):
            # 키가 같으면 왼쪽을 먼저 넣어 동률 원소의 원래 순서를 보존한다.
            result.append(left[left_index])
            left_index += 1
        else:
            result.append(right[right_index])
            right_index += 1
    # 한 조각을 다 썼다면 다른 조각의 남은 원소는 이미 정렬되어 있다.
    result.extend(left[left_index:])
    result.extend(right[right_index:])
    return result


def quick_sort(
    items: list[Any], key_func: Callable[[Any], Any] | None = None
) -> list[Any]:
    """세 그룹으로 나누는 퀵 정렬. 평균 O(n log n), 최악 O(n²).

    이 구현은 세 그룹에 원래 순서대로 넣는다. 따라서 같은 키의 상대 순서가
    유지되는 안정 정렬이다. 일반적인 제자리 퀵 정렬과 공간 사용도 다르다.
    평균 추가 공간은 O(n), 최악의 편향 분할에서는 O(n²)까지 쓸 수 있다.
    """
    if key_func is None:
        key_func = _identity
    if len(items) <= 1:
        return items[:]

    # 가운데 위치의 값을 '기준(피벗)'으로 삼는다. 위치가 중간이라는 뜻이지
    # 크기의 중앙값이라는 뜻은 아니다.
    pivot_key = key_func(items[len(items) // 2])
    smaller: list[Any] = []
    equal: list[Any] = []
    larger: list[Any] = []
    # 원래 순서대로 세 그룹에 넣으므로 각 그룹의 동률 순서는 유지된다.
    for item in items:
        item_key = key_func(item)
        if item_key < pivot_key:
            smaller.append(item)
        elif item_key > pivot_key:
            larger.append(item)
        else:
            equal.append(item)
    return quick_sort(smaller, key_func) + equal + quick_sort(larger, key_func)


def benchmark_sorts(sizes: list[int] | None = None) -> str:
    """같은 입력을 두 정렬에 주어 실행 시간을 비교한다(선택 과제).

    시간은 환경에 따라 달라진다. Python 함수 호출과 리스트 복사 비용도 포함된다.
    """
    if sizes is None:
        sizes = [10, 50, 100, 500, 1000, 3000, 5000]
    if not sizes or any(size < 0 for size in sizes):
        return "Error: Invalid benchmark sizes."

    lines = [
        "Sorting benchmark (seconds; smaller is faster)",
        "    size |    merge |    quick | winner",
    ]
    for size in sizes:
        data = list(range(size))
        random.Random(size).shuffle(data)  # 같은 크기는 매번 같은 입력을 만든다.
        # perf_counter는 성능 측정용 시계다. 종료값 - 시작값 = 걸린 초.
        start = time.perf_counter()
        merge_sort(data)
        merge_seconds = time.perf_counter() - start
        start = time.perf_counter()
        quick_sort(data)
        quick_seconds = time.perf_counter() - start
        if merge_seconds < quick_seconds:
            winner = "Merge"
        else:
            winner = "Quick"
        lines.append(
            f"{size:>8} | {merge_seconds:>8.6f} | {quick_seconds:>8.6f} | {winner}"
        )
    lines.append("Both implementations are stable; times vary by machine and run.")
    return "\n".join(lines)
