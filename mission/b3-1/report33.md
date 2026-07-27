# 📄 doubly_linked_list.py 및 dynamic_array.py 사용 현황과 필요성 종합 분석 리포트 (report33.md)

---

## 1. 개요 (Executive Summary)

본 리포트는 Mini Redis 프로젝트(`b3-1` 미션)의 `doubly_linked_list.py`에 정의된 **`remove_front()` / `remove_back()`** 함수와, `dynamic_array.py`에 정의된 **`DynamicArray`** 클래스의 actual usage(실제 코드베이스 내 사용 현황) 및 학습 미션 설계 의도(Pedagogical Intent)를 종합 분석하여 필요성 여부를 판정합니다.

### 📌 핵심 결론
> 1. **`remove_front()` / `remove_back()`**: `mini_redis_core.py`(LRU Eviction)와 `pub_sub.py`(메시지 큐 Poll)의 **핵심 직접 연산자**로서 필수적입니다.
> 2. **`DynamicArray`**: `mini_redis_core.py` 최상단에 직접 import되지 않아 "안 쓰인다"고 오해하기 쉬우나, **`HashMap`의 버킷 배열과 `MinHeap`의 트리 배열을 받쳐주는 최하위 핵심 기저(Storage Substrate) 자료구조**로서 절대 삭제할 수 없는 **필수 클래스**입니다.

---

## 2. DoublyLinkedList 메서드 사용 현황 분석 (`remove_front` / `remove_back`)

프로젝트 코드 전체를 정밀 검색(Grep Inspection)한 결과, 두 함수는 다음과 같이 핵심 서비스 로직에 직접 사용되고 있습니다.

```
[Search Results]
1. remove_back():
   - mini_redis_core.py (Line 40): lru_node = self.lru_list.remove_back()
   - doubly_linked_list.py (Line 106): def remove_back(self) -> Node:

2. remove_front():
   - pub_sub.py (Line 63): node = message_queue.remove_front()
   - doubly_linked_list.py (Line 121): def remove_front(self) -> Node:
```

---

### 2.1 `remove_back()` 사용처: Mini Redis LRU 캐시 Eviction

* **사용 모듈**: [`mini_redis_core.py`](file:///Users/f22losophysics1091/Desktop/codsaid/mission/b3-1/mini_redis_core.py#L40) -> `MiniRedis._evict_lru()`
* **코드 조각**:
  ```python
  def _evict_lru(self) -> None:
      """메모리 초과 시 LRU(가장 오래 사용되지 않은) 키를 찾아 제거합니다."""
      lru_node = self.lru_list.remove_back()  # <--- remove_back() 호출
      if lru_node is not None:
          key = lru_node.key
          value = lru_node.value
          self.store.remove(key)
          self.ttl_map.remove(key)
          ...
  ```
* **구동 메커니즘**:
  - `MiniRedis`는 새로운 데이터 삽입(`SET`) 또는 조회(`GET`) 시 해당 노드를 이중 연결 리스트의 맨 앞(`insert_front`, `move_to_front`)으로 보냅니다.
  - 이에 따라 **리스트의 맨 뒤(`tail.prev`)에 위치한 노드가 가장 오래전에 사용된 데이터(Least Recently Used)**가 됩니다.
  - 메모리 용량 제한(`maxmemory`)을 초과하면 가장 오랫동안 사용되지 않은 노드를 $O(1)$ 시간에 꺼내어 메모리를 해제해야 하므로, `remove_back()` 메서드가 필수적으로 사용됩니다.

---

### 2.2 `remove_front()` 사용처: Pub/Sub 메시지 큐 인출 (FIFO Poll)

* **사용 모듈**: [`pub_sub.py`](file:///Users/f22losophysics1091/Desktop/codsaid/mission/b3-1/pub_sub.py#L63) -> `PubSub.poll()`
* **코드 조각**:
  ```python
  def poll(self, channel: str) -> list:
      """특정 채널의 큐에 쌓인 모든 메시지를 꺼내옵니다(dequeue)."""
      ...
      message_queue: DoublyLinkedList = self._channels.get(channel)
      messages = []
      
      while not message_queue.is_empty():
          node = message_queue.remove_front()  # <--- remove_front() 호출
          messages.append(node.value)
          
      return messages
  ```
* **구동 메커니즘**:
  - Pub/Sub 모듈은 메시지를 발행(`publish`)할 때 메시지 큐의 맨 뒤에 노드를 추가(`insert_back`)합니다 (Enqueue 연산).
  - 구독자가 메시지를 수신(`poll`)할 때는 **가장 먼저 발행된 메시지부터 순서대로 추출(FIFO, First-In First-Out)**해야 하므로 큐의 맨 앞 노드를 꺼내는 `remove_front()`가 필수적으로 사용됩니다 (Dequeue 연산).

---

## 3. DynamicArray 사용 현황 및 오해 원인 분석 (`dynamic_array.py`)

### 3.1 "DynamicArray를 안 쓴다"는 오해가 생기는 원인 분석
동료나 지인이 "DynamicArray는 안 쓰인다"고 오해하는 이유는 **최상위 실행 파일(`mini_redis_core.py`, `cli.py`)의 `import` 구문만 확인했기 때문**입니다.

- `mini_redis_core.py` 상단: `from hash_map import HashMap`, `from min_heap import MinHeap`
- 외부에서는 `HashMap`과 `MinHeap`을 불러와 사용하므로, 겉으로는 `DynamicArray`가 보이지 않습니다 (Encapsulation).
- 그러나 `HashMap`과 `MinHeap` 내부를 들여다보면 **`DynamicArray` 없이는 단 1줄도 구동될 수 없는 강한 의존 구조(Indirect Dependency)**를 가지고 있습니다.

---

### 3.2 코드베이스 내 `DynamicArray` 의존성 추적 (Dependency Trace)

```
[DynamicArray 의존성 구조도]

  MiniRedis Engine (mini_redis_core.py)
   ├── HashMap (hash_map.py)
   │    └── self._buckets = DynamicArray(self._capacity)  <-- [DynamicArray 필수!]
   └── MinHeap (min_heap.py)
        └── self._data = DynamicArray()                 <-- [DynamicArray 필수!]
```

1. **`HashMap` 버킷 배열의 기저 저장소**:
   - 위치: [`hash_map.py:L1, L15`](file:///Users/f22losophysics1091/Desktop/codsaid/mission/b3-1/hash_map.py#L15)
   - 코드: `self._buckets = DynamicArray(self._capacity)`
   - 이유: 해시 충돌(Chaining)을 해결하기 위한 버킷 공간으로 고정 배열을 할당하고, Rehash 발생 시 버킷 크기를 확장하는 데 `DynamicArray`를 사용합니다.

2. **`MinHeap` 완전 이진 트리 배열의 기저 저장소**:
   - 위치: [`min_heap.py:L1, L17`](file:///Users/f22losophysics1091/Desktop/codsaid/mission/b3-1/min_heap.py#L17)
   - 코드: `self._data = DynamicArray()`
   - 이유: TTL 관리용 최소 힙은 1차원 배열 기반 완전 이진 트리입니다. 힙 요소의 `push`/`pop` 및 `_swap` 연산이 모두 `DynamicArray` 위에서 수행됩니다.

---

## 4. 필요성 및 학습 미션 설계 의도 (Pedagogical Intent)

### 4.1 파이썬 내장 자료형 배제 원칙 준수
- 미션 `b3-1`의 핵심 제약 조건: **"파이썬 내장 `list`의 동적 크기 조절 기능(`append`, `pop`, 동적 할당)과 `dict` 사용을 엄격히 배제할 것"**
- `DynamicArray`는 오직 `[None] * capacity` 형태의 원시 고정 크기 메모리 공간만 할당받은 뒤, 용량이 차면 2배로 공간을 늘리는 `_resize()` 연산과 분할 상환 복잡도(Amortized $O(1)$)를 **수동으로 직접 구현**한 클래스입니다.
- 파이썬 내장 `list` 대신 원시 메모리 배열을 흉내 내어 동적 배열의 원리를 배우는 것이 이 학습 미션의 뿌리입니다.

---

## 5. 종합 요약표 (Summary Matrix)

| 대상 | 위치 / 주요 사용처 | 의존 형태 | 자료구조적 / 기능적 역할 | 결론 및 판정 |
| :--- | :--- | :--- | :--- | :--- |
| **`remove_back()`** | `mini_redis_core.py` (`_evict_lru`) | Direct | LRU 캐시 메모리 초과 시 $O(1)$ 꼬리 노드 제거 | **필수 (Directly Used)** |
| **`remove_front()`** | `pub_sub.py` (`poll`) | Direct | Pub/Sub 메시지 큐 FIFO 순서 인출 | **필수 (Directly Used)** |
| **`DynamicArray`** | `hash_map.py`, `min_heap.py` | Indirect (Substrate) | HashMap 버킷 배열 및 MinHeap 트리 배열의 하부 저장소 | **필수 (Foundation Storage)** |

---

## 6. 결론

1. `doubly_linked_list.py`의 `remove_front()`와 `remove_back()`은 Mini Redis의 **LRU Eviction** 및 **Pub/Sub Queue Poll**에 직접 사용되는 핵심 함수입니다.
2. `dynamic_array.py`의 `DynamicArray`는 최상위 파일에서 직접 호출되지는 않지만, **`HashMap`과 `MinHeap`이 내부적으로 사용하는 원시 배열 엔진**입니다.
3. 따라서 `remove_front`, `remove_back`, `DynamicArray` **모두 삭제해서는 안 되며 프로젝트 구동 및 자료구조 밑바닥 구현 학습에 완전히 필수적인 요소**입니다.
