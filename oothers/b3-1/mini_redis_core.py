import time
from hash_map import HashMap
from doubly_linked_list import DoublyLinkedList, Node
from min_heap import MinHeap

class MiniRedis:
    """
    Mini Redis 엔진의 핵심 로직을 담당하는 클래스입니다.
    데이터 저장(HashMap), LRU 추적(DoublyLinkedList), TTL 관리(MinHeap)가 이곳에서 통합됩니다.
    """
    def __init__(self):
        # 데이터 저장소: Key -> LRU Node 매핑
        # O(1) 시간에 LRU 리스트의 노드에 직접 접근하기 위함
        self.store = HashMap()
        
        # LRU 리스트: 최근 사용된 노드를 맨 앞(head)으로, 오래된 노드를 맨 뒤(tail)로 관리
        self.lru_list = DoublyLinkedList()
        
        # TTL 관리용 최소 힙: (만료 시간 Timestamp, Key) 저장
        self.ttl_heap = MinHeap()
        
        # 만료 시간 빠른 조회를 위한 보조 저장소: Key -> Expire Timestamp 매핑
        # 힙은 임의 검색이 O(N)이므로, 개별 키의 만료 여부를 O(1)에 확인하기 위해 사용
        self.ttl_map = HashMap()
        
        # 메모리 설정 및 통계
        self.maxmemory = 0 # 0은 무제한
        self.used_memory = 0
        self.evicted_keys = 0

    def _calc_memory(self, key: str, value: str) -> int:
        """키와 값의 메모리 사용량(바이트)을 계산합니다."""
        return len(key.encode('utf-8')) + len(str(value).encode('utf-8'))

    def _evict_lru(self) -> None:
        """
        메모리 초과 시 LRU(가장 오래 사용되지 않은) 키를 찾아 제거합니다.
        제거될 때 데이터, LRU 리스트, TTL 맵의 모든 연결을 끊어줍니다.
        """
        lru_node = self.lru_list.remove_back()
        if lru_node is not None:
            key = lru_node.key
            value = lru_node.value
            
            # 저장소 및 TTL에서 삭제
            self.store.remove(key)
            self.ttl_map.remove(key)
            
            # 메모리 반환 및 통계 갱신
            mem_freed = self._calc_memory(key, value)
            self.used_memory -= mem_freed
            self.evicted_keys += 1

    def _cleanup_expired(self) -> None:
        """
        지연 삭제(Lazy Deletion) 로직.
        힙을 확인하여 만료 시간이 지난 키들을 일괄 제거합니다.
        명령어 실행 전 항상 호출되어 일관성을 유지합니다.
        """
        now = time.time()
        while not self.ttl_heap.is_empty():
            expire_at, key = self.ttl_heap.peek()
            
            # 가장 빨리 만료되는 아이템이 아직 만료 전이라면 반복문 종료
            if expire_at > now:
                break
                
            # 만료되었다면 힙에서 제거하고 실제 데이터도 삭제
            self.ttl_heap.pop()
            
            # ttl_map에 기록된 최신 만료 시간과 일치할 때만 삭제 진행
            # (기존 키를 SET으로 덮어썼거나 EXPIRE를 새로 갱신한 경우 과거 데이터가 힙에 남아있을 수 있음)
            current_ttl = self.ttl_map.get(key)
            if current_ttl is not None and current_ttl <= now:
                self.delete(key) # 내부 delete를 호출하여 모든 맵에서 깔끔하게 정리

    def config_set_maxmemory(self, bytes_limit: int) -> str:
        """최대 메모리 제한을 설정합니다."""
        if bytes_limit < 0:
            raise ValueError("ERR value is not an integer or out of range")
        self.maxmemory = bytes_limit
        
        # 메모리 제한을 줄였을 경우 즉시 Eviction 발생 가능
        self._cleanup_expired()
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            if self.lru_list.is_empty():
                break # 더 이상 지울 게 없는 경우
            self._evict_lru()
            
        return "OK"

    def info_memory(self) -> str:
        """메모리 사용 현황을 반환합니다."""
        return (f"used_memory:{self.used_memory}\n"
                f"maxmemory:{self.maxmemory}\n"
                f"evicted_keys:{self.evicted_keys}")

    def set(self, key: str, value: str) -> str:
        """
        데이터를 저장합니다.
        성공 시 LRU를 갱신하며, 덮어쓸 경우 기존 TTL은 초기화(삭제) 됩니다.
        """
        self._cleanup_expired()
        
        mem_cost = self._calc_memory(key, value)
        
        # 단일 엔트리가 제한을 초과하는지 검사
        if self.maxmemory > 0 and mem_cost > self.maxmemory:
            raise MemoryError("OOM command not allowed when used_memory > 'maxmemory'")
            
        # 기존 데이터가 있으면 교체 및 메모리 반환
        if self.store.contains(key):
            old_node = self.store.get(key)
            old_mem = self._calc_memory(key, old_node.value)
            self.used_memory -= old_mem
            self.lru_list.remove_node(old_node)
            # 덮어쓰기 시 TTL 삭제
            self.ttl_map.remove(key)
            
        # 새 데이터 생성 및 삽입
        new_node = Node(key=key, value=value)
        self.lru_list.insert_front(new_node)
        self.store.put(key, new_node)
        self.used_memory += mem_cost
        
        # maxmemory를 초과하면 사용량이 제한 이하로 떨어질 때까지 LRU 제거
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            self._evict_lru()
            
        # 만약 방금 넣은 데이터가 바로 Evict 되었다면 (예외적인 상황)
        if not self.store.contains(key):
             raise MemoryError("OOM command not allowed when used_memory > 'maxmemory'")
             
        return "OK"

    def get(self, key: str):
        """
        데이터를 조회합니다. 존재하면 값 반환, 없으면 None 반환.
        성공 시 LRU가 갱신됩니다.
        """
        self._cleanup_expired()
        
        node = self.store.get(key)
        if node is None:
            return None
            
        # LRU 갱신 (가장 앞으로 이동)
        self.lru_list.move_to_front(node)
        return node.value

    def delete(self, key: str) -> int:
        """데이터를 삭제합니다. 성공 시 1, 실패 시 0 반환"""
        # _cleanup_expired에서 호출될 수 있으므로, 재귀 호출 방지를 위해 _cleanup_expired 미호출
        node = self.store.get(key)
        if node is None:
            return 0
            
        # 메모리 반환
        mem_cost = self._calc_memory(key, node.value)
        self.used_memory -= mem_cost
        
        # 각 구조에서 완전히 삭제
        self.lru_list.remove_node(node)
        self.store.remove(key)
        self.ttl_map.remove(key)
        
        return 1

    def exists(self, key: str) -> int:
        """키 존재 여부 반환 (만료 체크 포함)"""
        self._cleanup_expired()
        return 1 if self.store.contains(key) else 0

    def dbsize(self) -> int:
        """현재 저장된 키의 개수 반환"""
        self._cleanup_expired()
        return self.store.size()

    def keys(self) -> list:
        """전체 키 목록 반환"""
        self._cleanup_expired()
        return self.store.keys()

    def expire(self, key: str, seconds: int) -> int:
        """
        키의 만료 시간을 설정합니다.
        초가 0 이하면 즉시 만료(삭제) 처리합니다.
        """
        self._cleanup_expired()
        
        if not self.store.contains(key):
            return 0
            
        if seconds <= 0:
            self.delete(key)
            return 1
            
        expire_at = time.time() + seconds
        
        # TTL 맵 갱신 및 힙에 푸시 (기존에 있던 예전 만료시간은 _cleanup_expired에서 지연 삭제됨)
        self.ttl_map.put(key, expire_at)
        self.ttl_heap.push((expire_at, key))
        return 1

    def ttl(self, key: str) -> int:
        """
        키의 남은 만료 시간(초)을 반환합니다.
        -2: 키 없음, -1: 만료 시간 설정 안 됨
        """
        self._cleanup_expired()
        
        if not self.store.contains(key):
            return -2
            
        expire_at = self.ttl_map.get(key)
        if expire_at is None:
            return -1
            
        remains = int(expire_at - time.time())
        return remains if remains > 0 else 0
