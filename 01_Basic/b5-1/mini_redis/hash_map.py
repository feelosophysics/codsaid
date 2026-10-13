"""
[HashMap: 다항식 롤링 해시 & 체이닝 기반 커스텀 해시맵 구현 모듈]

1. 어떤 로직인가:
   - 문자열 키를 숫자 해시로 변환하고, 그 해시값을 버킷 인덱스로 삼아 데이터를 저장/조회하는 해시맵 클래스입니다.
   - 해시 충돌은 체이닝(Chaining, 이중 연결 리스트 연동) 방식으로 해결하고, 버킷 채움 비율이 75%를 넘으면 버킷을 2배로 확장(Rehashing)합니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 파이썬 내장 `dict` 사용이 엄격히 금지된 환경에서, 키 기반 데이터 접근 및 LRU 노드 위치 조회를 O(1) 시간에 지원하기 위해 필수적입니다.

3. 수학 알고리즘 및 복잡도:
   - 다항식 롤링 해시: H(s) = (sum(s[i] * p^i)) mod m (p=31, m=10^9+9) -> 아나그램 충돌 방지
   - 조회/수정/삭제: 평균 O(1) (Rehash 시 단일 O(N), 분할상환 O(1))
"""

from typing import Any, Optional, List
from .dynamic_array import DynamicArray
from .doubly_linked_list import DoublyLinkedList, Node
from .constants import ConfigDefaults


class HashMap:
    """
    DynamicArray(버킷 버퍼)와 DoublyLinkedList(체이닝 리스트) 기반 커스텀 해시맵 클래스입니다.
    """

    def __init__(self, initial_capacity: int = ConfigDefaults.INITIAL_CAPACITY) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if initial_capacity <= 0:
            raise ValueError("Initial capacity must be greater than 0")

        self._capacity: int = initial_capacity  # 전체 버킷 용량 (기본 8개)
        self._size: int = 0                     # 저장된 총 (키, 값) 쌍 개수
        self._buckets: DynamicArray = DynamicArray(self._capacity)

        # 8개 버킷 방에 각각 이중 연결 리스트(DoublyLinkedList)를 사전 할당
        for _ in range(self._capacity):
            self._buckets.append(DoublyLinkedList())

    @property
    def capacity(self) -> int:
        """무엇: capacity 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._capacity

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

    def _hash(self, key: str) -> int:
        """무엇: _hash 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        hash_val: int = 0
        p: int = 31             # 알파벳 소문자 분포에 최적인 소수
        m: int = 10**9 + 9      # 정수 오버플로우 방지용 거대 소수
        p_pow: int = 1

        for char in key:
            hash_val = (hash_val + ord(char) * p_pow) % m
            p_pow = (p_pow * p) % m

        return hash_val

    def _get_bucket_index(self, key: str) -> int:
        """무엇: _get_bucket_index 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self._hash(key) % self._capacity

    def put(self, key: str, value: Any) -> None:
        """무엇: 키-값을 버킷 체인에 저장하거나 기존 값을 교체합니다.
        상태: 새 키만 size를 늘리고 충돌 키는 같은 체인에서 구분됩니다.
        이유: 해시 충돌은 허용하되 키 동등성 비교로 정확성을 보장합니다.
        복잡도: 평균 O(1), 최악 O(N)."""
        if not isinstance(key, str):
            raise TypeError("HashMap key must be a string")

        # 임계점(0.75) 도달 시 버킷을 2배로 확장하여 충돌 리스트 길이를 짧게 유지
        if self._size / self._capacity >= ConfigDefaults.DEFAULT_LOAD_FACTOR:
            self._resize()

        bucket_idx: int = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)

        # 버킷 내 체이닝 리스트를 순회하며 이미 있는 키인지 검사
        curr: Optional[Node] = chain.head.next
        while curr is not None and curr != chain.tail:
            if curr.key == key:
                curr.value = value  # 덮어쓰기
                return
            curr = curr.next

        # 없으면 맨 앞에 새 노드 삽입 (O(1))
        new_node: Node = Node(key=key, value=value)
        chain.insert_front(new_node)
        self._size += 1

    def get(self, key: str) -> Any:
        """무엇: get 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if not isinstance(key, str):
            return None

        bucket_idx: int = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)

        curr: Optional[Node] = chain.head.next
        while curr is not None and curr != chain.tail:
            if curr.key == key:
                return curr.value
            curr = curr.next

        return None

    def remove(self, key: str) -> bool:
        """무엇: remove 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if not isinstance(key, str):
            return False

        bucket_idx: int = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)

        curr: Optional[Node] = chain.head.next
        while curr is not None and curr != chain.tail:
            if curr.key == key:
                chain.remove_node(curr)  # DoublyLinkedList의 O(1) 노드 고립 삭제
                self._size -= 1
                return True
            curr = curr.next

        return False

    def contains_key(self, key: str) -> bool:
        """무엇: contains_key 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if not isinstance(key, str):
            return False

        bucket_idx: int = self._get_bucket_index(key)
        chain: DoublyLinkedList = self._buckets.get(bucket_idx)

        curr: Optional[Node] = chain.head.next
        while curr is not None and curr != chain.tail:
            if curr.key == key:
                return True
            curr = curr.next

        return False

    def contains(self, key: str) -> bool:
        """무엇: contains 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return self.contains_key(key)

    def keys(self) -> List[str]:
        """무엇: keys 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        result_keys: List[str] = []
        for i in range(self._capacity):
            chain: DoublyLinkedList = self._buckets.get(i)
            curr: Optional[Node] = chain.head.next
            while curr is not None and curr != chain.tail:
                if curr.key is not None:
                    result_keys.append(curr.key)
                curr = curr.next
        return result_keys

    def _resize(self) -> None:
        """무엇: 버킷 수를 늘리고 모든 키를 새 버킷으로 리해싱합니다.
        상태: capacity는 커지고 key-value 관계와 size는 유지됩니다.
        이유: capacity가 바뀌면 해시 modulo 결과도 바뀌므로 단순 복사로는 조회가 깨집니다.
        복잡도: O(N), 삽입 기준 상각 O(1)."""
        old_capacity: int = self._capacity
        old_buckets: DynamicArray = self._buckets

        self._capacity *= 2
        self._size = 0
        self._buckets = DynamicArray(self._capacity)

        for _ in range(self._capacity):
            self._buckets.append(DoublyLinkedList())

        for i in range(old_capacity):
            chain: DoublyLinkedList = old_buckets.get(i)
            curr: Optional[Node] = chain.head.next
            while curr is not None and curr != chain.tail:
                if curr.key is not None:
                    self.put(curr.key, curr.value)
                curr = curr.next
