"""
[MinHeap: 1차원 완전 이진 트리 최소 힙 구현 모듈]

1. 어떤 로직인가:
   - 1차원 배열(`DynamicArray`) 위에 완전 이진 트리(Complete Binary Tree) 구조를 오버레이하여,
     가장 작은 값(루트 노드, 0번 인덱스)을 항상 O(1) 시간에 꺼내볼 수 있게 유지하는 최소 힙 모듈입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - Redis의 TTL(Time-To-Live) 만료 시간 관리를 위해 존재합니다.
   - `(만료 타임스탬프, 키)` 형태의 튜플을 저장해두면, 가장 먼저 만료될 항목이 항상 최상단(루트)에 배치되므로
     전체 키를 순회하지 않고도 단 O(1) 만에 만료 여부를 검사하고 O(log N)으로 삭제할 수 있습니다.

3. 지수 인덱싱 공식:
   - 부모 인덱스 = (index - 1) // 2
   - 왼쪽 자식 인덱스 = 2 * index + 1
   - 오른쪽 자식 인덱스 = 2 * index + 2
"""

from typing import Any, Optional
from .dynamic_array import DynamicArray


class MinHeap:
    """
    DynamicArray 기반 최소 힙 클래스입니다.
    """

    def __init__(self) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self._data: DynamicArray = DynamicArray()

    def __len__(self) -> int:
        """무엇: __len__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return len(self._data)

    def size(self) -> int:
        """무엇: size 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return len(self._data)

    def is_empty(self) -> bool:
        """무엇: is_empty 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._data.is_empty()

    def _swap(self, i: int, j: int) -> None:
        """무엇: _swap 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        temp: Any = self._data.get(i)
        self._data.set(i, self._data.get(j))
        self._data.set(j, temp)

    def _heapify_up(self, index: int) -> None:
        """무엇: 새 항목을 부모와 비교하며 위로 올립니다.
        상태: 삽입 경로의 최소 힙 불변식이 복구됩니다.
        이유: 끝 삽입 뒤 순서를 깰 수 있는 곳은 조상 경로뿐입니다.
        복잡도: O(log N)."""
        parent_idx: int = (index - 1) // 2

        # 내가 부모보다 작다면 부모와 자리를 바꿈
        while index > 0 and self._data.get(index) < self._data.get(parent_idx):
            self._swap(index, parent_idx)
            index = parent_idx
            parent_idx = (index - 1) // 2

    def _heapify_down(self, index: int) -> None:
        """무엇: 루트 항목을 더 작은 자식과 교환하며 아래로 내립니다.
        상태: pop 뒤 루트 경로의 최소 힙 불변식이 복구됩니다.
        이유: 마지막 항목이 루트로 온 경로만 재정렬하면 됩니다.
        복잡도: O(log N)."""
        size: int = len(self._data)
        while True:
            smallest: int = index
            left_child_idx: int = 2 * index + 1
            right_child_idx: int = 2 * index + 2

            # 왼쪽 자식이 존재하고 현재 최솟값보다 작으면 smallest 갱신
            if left_child_idx < size and self._data.get(left_child_idx) < self._data.get(smallest):
                smallest = left_child_idx

            # 오른쪽 자식이 존재하고 현재 최솟값보다 작으면 smallest 갱신
            if right_child_idx < size and self._data.get(right_child_idx) < self._data.get(smallest):
                smallest = right_child_idx

            # 자식들 중 더 작은 값이 없으면 정렬 완료이므로 루프 중단
            if smallest == index:
                break

            self._swap(index, smallest)
            index = smallest

    def push(self, *args: Any) -> None:
        """무엇: push 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if len(args) == 1:
            item: Any = args[0]
        elif len(args) == 2:
            item = (args[0], args[1])
        else:
            raise ValueError("push requires 1 tuple argument or 2 positional arguments")

        self._data.append(item)
        self._heapify_up(len(self._data) - 1)

    def pop(self) -> Any:
        """무엇: pop 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if self.is_empty():
            raise IndexError("pop from empty MinHeap")

        size: int = len(self._data)
        if size == 1:
            return self._data.pop()

        root: Any = self._data.get(0)          # 최솟값 백업
        last_item: Any = self._data.pop()     # 맨 뒤 항목을 떼어냄
        self._data.set(0, last_item)           # 0번에 임시로 배치

        self._heapify_down(0)                  # 루트부터 하향 재배열

        return root

    def peek(self) -> Optional[Any]:
        """무엇: peek 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if self.is_empty():
            return None
        return self._data.get(0)
