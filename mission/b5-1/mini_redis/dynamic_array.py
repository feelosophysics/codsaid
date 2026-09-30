"""
[DynamicArray: 밑바닥 동적 배열 구현 모듈]

1. 어떤 로직인가:
   - 파이썬 내장 `list`의 자동 확장 기능을 사용하지 않고, 고정 크기 배열 `[None] * capacity`만을 할당받아
     내부 요소 수(`_size`)를 직접 관리하고 용량 초과 시 2배 크기로 확장(Resize)하는 커스텀 동적 배열 클래스입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 미션 제약조건(내장 컬렉션 배제)을 만족하면서, 뒤이어 구현할 HashMap 버킷 테이블 및 MinHeap 트리를 
     원시적인 고정 배열 메모리 구조 위에서 작동시키기 위한 '기초 저장소 부품'으로 존재합니다.

3. 알고리즘 및 시간 복잡도:
   - 인덱스 접근(`get`/`set`): O(1)
   - 요소 추가(`append`): Amortized O(1) (2배 확장 재배치 비용은 occasional 함)
   - 특정 위치 삭제(`remove_at`): O(N) (요소 시프트 필요)
"""

from typing import Any, Optional, List


class DynamicArray:
    """
    고정 크기 상자([None] * capacity)를 기반으로 작동하는 커스텀 동적 배열 클래스입니다.
    """

    def __init__(self, capacity: int = 8) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if capacity <= 0:
            # 0 이하의 크기는 물리적으로 배열을 생성할 수 없으므로 사전 Guard Clause로 예외 발생
            raise ValueError("Capacity must be greater than 0")

        self._capacity: int = capacity  # 현재 배열이 담을 수 있는 최대 요소 개수
        self._size: int = 0             # 실제 현재 저장된 데이터 개수
        
        # 고정 크기 레퍼런스 배열 할당 (추가/삭제 시 자동으로 크기가 변하지 않는 고정 버퍼)
        self._data: List[Any] = [None] * self._capacity

    @property
    def capacity(self) -> int:
        """무엇: capacity 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._capacity

    @property
    def size(self) -> int:
        """무엇: size 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._size

    def __len__(self) -> int:
        """무엇: __len__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._size

    def is_empty(self) -> bool:
        """무엇: is_empty 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._size == 0

    def _resize(self) -> None:
        """무엇: 더 큰 버퍼를 할당하고 유효 원소를 순서대로 복사합니다.
        상태: capacity만 커지고 size와 원소 순서는 보존됩니다.
        이유: 2배 확장은 삽입을 계속 허용하면서 append의 상각 비용을 O(1)로 만듭니다.
        복잡도: O(N), append 기준 상각 O(1)."""
        new_capacity: int = self._capacity * 2
        new_data: list[Any] = [None] * new_capacity  # 2배 큰 고정 버퍼 재할당

        # 기존 낡은 버퍼에서 데이터를 하나씩 새 버퍼로 얕은 복사
        for i in range(self._size):
            new_data[i] = self._data[i]

        # 낡은 버퍼 대신 새 버퍼를 내 가리키는 내부 변수로 교체
        self._data = new_data
        self._capacity = new_capacity

    def append(self, value: Any) -> None:
        """무엇: append 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        # 버퍼가 꽉 찼다면 append 전에 2배 확장을 먼저 실행
        if self._size == self._capacity:
            self._resize()

        self._data[self._size] = value
        self._size += 1

    def _check_bounds(self, index: int) -> None:
        """무엇: _check_bounds 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of bounds for size {self._size}")

    def get(self, index: int) -> Any:
        """무엇: get 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self._check_bounds(index)
        return self._data[index]

    def set(self, index: int, value: Any) -> None:
        """무엇: set 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self._check_bounds(index)
        self._data[index] = value

    def __getitem__(self, index: int) -> Any:
        """무엇: __getitem__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self.get(index)

    def __setitem__(self, index: int, value: Any) -> None:
        """무엇: __setitem__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self.set(index, value)

    def remove_at(self, index: int) -> None:
        """무엇: 지정 원소를 삭제하고 오른쪽 원소를 왼쪽으로 당깁니다.
        상태: 빈 구멍 없이 밀집 상태가 되고 size가 하나 줄어듭니다.
        이유: 유효 구간에 빈 칸이 남으면 순회와 다음 append의 규약이 깨집니다.
        복잡도: O(N)."""
        self._check_bounds(index)

        for i in range(index, self._size - 1):
            self._data[i] = self._data[i + 1]

        # 마지막 방 레퍼런스를 None으로 지워 파이썬 가비지 컬렉터가 메모리를 해제하도록 조치
        self._data[self._size - 1] = None
        self._size -= 1

    def pop(self) -> Any:
        """무엇: pop 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if self.is_empty():
            raise IndexError("pop from empty DynamicArray")

        value: Any = self._data[self._size - 1]
        self._data[self._size - 1] = None  # 메모리 해제
        self._size -= 1
        return value
