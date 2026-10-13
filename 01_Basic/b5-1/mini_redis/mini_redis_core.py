"""
[MiniRedis: 메인 코어 엔진 및 오케스트레이션 모듈]

1. 어떤 로직인가:
   - HashMap(데이터 저장소), DoublyLinkedList(LRU 캐시 순서), MinHeap(TTL 만료 시간), HashMap(TTL 최신값)
     4개 자료구조를 결합하여 Redis 핵심 명령어를 총괄 제어하는 코어 엔진 클래스입니다.

2. 왜 존재하는가 (존재 이유 및 목적):
   - 단품 자료구조들을 묶어 실제 In-Memory 데이터 저장소 동작(LRU 캐시 교체, 지연 삭제, 메모리 한도 관리)을
     오케스트레이션(통합 제어)하기 위해 존재합니다.

3. 3단계 파이프라인 디자인:
   - 모든 명령어 수행 시 [1. Data Refinement] -> [2. Validation] -> [3. Logic Execution] 표준 흐름을 엄격히 준수합니다.
"""

import time
from typing import List, Optional, Tuple

from .hash_map import HashMap
from .doubly_linked_list import DoublyLinkedList, Node
from .min_heap import MinHeap
from .constants import RedisCommands, RedisResponses, ErrorMessages, ConfigDefaults


class MiniRedis:
    """
    Mini-Redis 메인 코어 엔진 클래스입니다.
    """

    def __init__(self) -> None:
        """무엇: __init__ 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self.store: HashMap = HashMap()                 # Key -> Node(Key, Value) 매핑 (O(1))
        self.lru_list: DoublyLinkedList = DoublyLinkedList() # LRU 최근성 관리 (Head=MRU, Tail=LRU)
        self.ttl_heap: MinHeap = MinHeap()             # (expire_at, key) 만료시간 최소 힙 (O(log N))
        self.ttl_map: HashMap = HashMap()               # Key -> expire_at 매핑 (O(1))

        self.maxmemory: int = ConfigDefaults.DEFAULT_MAX_MEMORY # 최대 메모리 한도 (0=무제한)
        self.used_memory: int = 0                       # 현재 사용 중인 바이트 수
        self.evicted_keys: int = 0                      # LRU로 제거된 총 키 수

    def _calc_memory(self, key: str, value: str) -> int:
        """무엇: _calc_memory 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return len(key.encode("utf-8")) + len(str(value).encode("utf-8"))

    def _evict_lru(self) -> None:
        """무엇: _evict_lru 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        lru_node: Optional[Node] = self.lru_list.remove_back()
        if lru_node is None or lru_node.key is None:
            return

        key: str = lru_node.key
        value: str = lru_node.value

        # 연관된 모든 자료구조에서 데이터 연쇄 제거
        self.store.remove(key)
        self.ttl_map.remove(key)

        mem_freed: int = self._calc_memory(key, value)
        self.used_memory -= mem_freed
        self.evicted_keys += 1

    def _cleanup_expired(self) -> None:
        """무엇: 최소 힙의 가장 이른 후보부터 만료 키를 정리합니다.
        상태: 최신 TTL이 만료된 키만 store, LRU, TTL 맵에서 함께 제거됩니다.
        이유: 같은 키의 과거 힙 항목은 ttl_map 최신값과 비교해 무효화해야 갱신된 키를 잘못 삭제하지 않습니다.
        복잡도: 만료 없음 O(1), K개 처리 시 O(K log N)."""
        now: float = time.time()
        while not self.ttl_heap.is_empty():
            peek_item = self.ttl_heap.peek()
            if peek_item is None:
                break

            expire_at, key = peek_item
            # 힙 상단의 가장 빠른 만료 키가 아직 안 지났다면 뒤쪽은 볼 필요도 없으므로 즉시 종료!
            if expire_at > now:
                break

            self.ttl_heap.pop()
            # ttl_map에 기록된 최신 만료 시간과 일치하는 경우에만 삭제 (SET/EXPIRE로 갱신된 과거 힙 항목 무시)
            current_ttl: Optional[float] = self.ttl_map.get(key)
            if current_ttl is not None and current_ttl <= now:
                self._raw_delete(key)

    def _raw_delete(self, key: str) -> int:
        """무엇: 한 키를 모든 관련 인덱스에서 원자적으로 삭제합니다.
        상태: LRU 노드, store, ttl_map, used_memory가 함께 갱신됩니다.
        이유: DEL, 즉시 EXPIRE, 지연 만료가 같은 삭제 규칙을 공유해 부분 삭제를 막습니다.
        복잡도: 평균 O(1)."""
        node: Optional[Node] = self.store.get(key)
        if node is None:
            return 0

        mem_cost: int = self._calc_memory(key, node.value)
        self.used_memory -= mem_cost

        self.lru_list.remove_node(node)
        self.store.remove(key)
        self.ttl_map.remove(key)

        return 1

    def config_set_maxmemory(self, bytes_limit: int) -> str:
        """무엇: config_set_maxmemory 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        if bytes_limit < 0:
            raise ValueError(ErrorMessages.ERR_VALUE_NOT_INT)

        self.maxmemory = bytes_limit
        self._cleanup_expired()

        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            if self.lru_list.is_empty():
                break
            self._evict_lru()

        return RedisResponses.OK

    def info_memory(self) -> str:
        """무엇: info_memory 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        return (
            f"used_memory:{self.used_memory}\n"
            f"maxmemory:{self.maxmemory}\n"
            f"evicted_keys:{self.evicted_keys}"
        )

    def set(self, key: str, value: str) -> str:
        """무엇: SET 명령으로 키와 값을 저장하고 최신 사용(MRU) 위치로 갱신합니다.
        상태: store, LRU 리스트, TTL 맵, used_memory가 함께 갱신됩니다. 기존 키의 TTL은 취소됩니다.
        이유: 네 인덱스가 같은 키 집합을 가리켜야 만료와 LRU 퇴거가 서로 모순되지 않습니다.
        복잡도: 평균 O(1), 퇴거한 키 수를 K라 하면 O(K)."""
        # 1. Data Refinement
        refined_key: str = key.strip()
        refined_val: str = str(value)
        mem_cost: int = self._calc_memory(refined_key, refined_val)

        # 2. Validation: 먼저 만료 키를 청소한다. 죽은 키가 남아 있으면 실제로 쓸 수 있는
        # 메모리를 과소평가하므로, 한도 검사보다 앞서야 한다.
        self._cleanup_expired()
        # 이 항목 하나가 한도보다 크면 모든 LRU 키를 지워도 저장할 수 없다.
        # 따라서 기존 데이터를 지우는 부작용 없이 즉시 OOM으로 실패한다.
        if self.maxmemory > 0 and mem_cost > self.maxmemory:
            raise MemoryError(ErrorMessages.ERR_MEMORY_LIMIT)

        # 3. Logic Execution
        # SET은 값을 덮어쓸 뿐 아니라 기존 TTL도 취소한다. 이전 노드, 메모리 계수,
        # ttl_map을 함께 정리해 store, LRU, TTL 인덱스가 같은 키 집합을 보게 한다.
        if self.store.contains(refined_key):
            old_node: Node = self.store.get(refined_key)
            old_mem: int = self._calc_memory(refined_key, old_node.value)
            self.used_memory -= old_mem
            self.lru_list.remove_node(old_node)
            self.ttl_map.remove(refined_key)

        new_node: Node = Node(key=refined_key, value=refined_val)
        self.lru_list.insert_front(new_node) # 맨 앞에 꼽아서 최신화 (MRU)
        self.store.put(refined_key, new_node)
        self.used_memory += mem_cost

        # 새 값을 반영한 뒤 초과량이 확정된다. Tail의 LRU부터 제거해 최근 사용 키를 보존한다.
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            self._evict_lru()

        if not self.store.contains(refined_key):
            raise MemoryError(ErrorMessages.ERR_MEMORY_LIMIT)

        return RedisResponses.OK

    def get(self, key: str) -> str:
        """무엇: GET 명령으로 값을 읽고 성공한 키를 MRU 위치로 승격합니다.
        상태: 값은 유지되고 LRU 순서만 바뀝니다.
        이유: 읽기도 사용으로 기록해야 다음 메모리 압박에서 오래 미사용한 키부터 제거합니다.
        복잡도: 평균 O(1)."""
        refined_key: str = key.strip()
        self._cleanup_expired()

        node: Optional[Node] = self.store.get(refined_key)
        if node is None:
            return RedisResponses.NIL

        self.lru_list.move_to_front(node) # LRU 갱신
        return str(node.value)

    def get_with_status(self, key: str) -> Tuple[bool, Optional[str]]:
        """무엇: get_with_status 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        refined_key: str = key.strip()
        self._cleanup_expired()
        node: Optional[Node] = self.store.get(refined_key)
        if node is None:
            return False, None
        self.lru_list.move_to_front(node)
        return True, str(node.value)

    def delete(self, key: str) -> str:
        """무엇: delete 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        refined_key: str = key.strip()
        deleted_count: int = self._raw_delete(refined_key)
        return RedisResponses.format_integer(deleted_count)

    def exists(self, key: str) -> str:
        """무엇: exists 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        refined_key: str = key.strip()
        self._cleanup_expired()
        is_exists: int = 1 if self.store.contains(refined_key) else 0
        return RedisResponses.format_integer(is_exists)

    def dbsize(self) -> str:
        """무엇: dbsize 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self._cleanup_expired()
        return RedisResponses.format_integer(self.store.size())

    def keys(self) -> List[str]:
        """무엇: keys 연산을 수행합니다.
        상태: 필요한 값, 연결, 또는 크기만 갱신하고 자료구조 불변식을 유지합니다.
        이유: 상위 Redis 명령이 예측 가능한 결과와 일관된 상태를 전제로 이 연산을 조합합니다.
        복잡도: 직접 접근은 O(1), 순회나 재배치가 있으면 O(N)."""
        self._cleanup_expired()
        return self.store.keys()

    def expire(self, key: str, seconds: int) -> str:
        """무엇: EXPIRE 명령으로 키의 최신 절대 만료 시각을 등록합니다.
        상태: ttl_map에는 최신 시각, ttl_heap에는 만료 후보가 기록됩니다.
        이유: 맵은 최신 진실값을, 힙은 가장 이른 만료 후보를 빠르게 찾는 역할로 분리합니다.
        복잡도: O(log N)."""
        refined_key: str = key.strip()
        self._cleanup_expired()

        if not self.store.contains(refined_key):
            return RedisResponses.format_integer(0)

        if seconds <= 0:
            self._raw_delete(refined_key)
            return RedisResponses.format_integer(1)

        expire_at: float = time.time() + seconds
        # ttl_map은 최신 만료 시각의 진실값이고, heap은 가장 이른 만료 후보를 찾는 큐다.
        self.ttl_map.put(refined_key, expire_at)
        # 같은 키의 과거 heap 항목은 남겨 둔다. cleanup이 ttl_map 최신값과 비교해 무시한다.
        self.ttl_heap.push(expire_at, refined_key)

        return RedisResponses.format_integer(1)

    def ttl(self, key: str) -> str:
        """무엇: TTL 명령으로 남은 만료 시간을 Redis 정수 응답으로 반환합니다.
        상태: 만료 키를 먼저 정리하며 -2는 키 없음, -1은 TTL 없음, 0 이상은 남은 초입니다.
        이유: 만료를 청소한 뒤 답해야 죽은 키를 살아 있다고 반환하지 않습니다.
        복잡도: 평균 O(1)."""
        refined_key: str = key.strip()
        self._cleanup_expired()

        if not self.store.contains(refined_key):
            return RedisResponses.format_integer(-2)

        expire_at: Optional[float] = self.ttl_map.get(refined_key)
        if expire_at is None:
            return RedisResponses.format_integer(-1)

        remains: int = int(expire_at - time.time())
        result_seconds: int = remains if remains > 0 else 0
        return RedisResponses.format_integer(result_seconds)
