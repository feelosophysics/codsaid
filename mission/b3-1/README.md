# Mini Redis from Scratch

이 프로젝트는 세계에서 가장 널리 사용되는 인메모리 데이터 저장소인 **Redis**의 핵심 메커니즘을 파이썬으로 **밑바닥부터 직접 구현(From Scratch)** 해본 학습용 프로젝트입니다. 

파이썬이 제공하는 강력한 내장 자료형인 `dict`, `set`, `collections` 모듈의 사용을 **엄격하게 배제**하고, 원시 배열 수준에서부터 자료구조를 층층이 쌓아올려 데이터 저장과 관리의 본질을 깊이 있게 학습하는 데 목적을 두었습니다.

## 🚀 주요 특징 (Core Features)

1. **Custom Data Structures (내장 자료형 배제)**
   - **`DynamicArray`**: `[None] * capacity` 형태의 고정 버퍼를 기반으로 용량이 초과되면 2배씩 확장(Resize)하는 로직을 직접 구현.
   - **`DoublyLinkedList`**: O(1) 삽입/삭제를 보장하는 이중 연결 리스트.
   - **`HashMap`**: 다항식 롤링 해시(Polynomial Rolling Hash) 함수를 직접 작성하고, 체이닝(Chaining) 기법을 이용해 해시 충돌을 해결.
   - **`MinHeap`**: 1차원 배열(DynamicArray)을 기반으로 한 완전 이진 트리 구조의 최소 힙 구현.
   - **`BST`**: 보너스 과제용 이진 탐색 트리와 전위/중위/후위/레벨 순회.

2. **LRU Cache Eviction**
   - 메모리가 가득 찼을 때 사용량이 가장 적은(Least Recently Used) 데이터를 O(1)에 찾아 삭제합니다.
   - `HashMap`과 `DoublyLinkedList`의 조합이 어떻게 O(1) 캐시 교체 알고리즘을 달성하는지 코드로 증명합니다.

3. **TTL (Time-To-Live) Management**
   - 데이터에 만료 시간을 설정하고, 지연 삭제(Lazy Deletion) 전략을 사용합니다.
   - O(log N) 성능을 자랑하는 `MinHeap`을 이용해, 다음에 만료될 아이템을 가장 빠르게 추적합니다.

4. **단일 스레드 기반 Pub/Sub**
   - 터미널 환경을 위한 수동 `POLL` 방식의 독자적인 발행-구독 시스템.

## 🛠 실행 방법 (How to Run)

Python 3.8 이상 환경에서 외부 의존성 없이 실행 가능합니다.

```bash
python3 cli.py
```

## 💻 사용 예시 (Usage Example)

```sh
Welcome to Mini Redis CLI.
Type 'exit' or 'quit' to terminate.
mini-redis> CONFIG SET maxmemory 30
OK

# 데이터 삽입
mini-redis> SET user:1 "Alice"
OK
mini-redis> SET user:2 "Bob"
OK
mini-redis> SET user:3 "Charlie"
OK

# maxmemory 초과 시 오래된 데이터(user:1)가 자동 삭제됨 (LRU)
mini-redis> GET user:1
(nil)

mini-redis> INFO memory
used_memory:22
maxmemory:30
evicted_keys:1

# TTL 만료 설정 (초 단위)
mini-redis> EXPIRE user:2 5
(integer) 1

# 5초 경과 후 조회 시 만료되어 삭제됨
mini-redis> GET user:2
(nil)

# 전체 키 조회
mini-redis> KEYS
1. "user:3"
```

## 🗂 파일 구조

- `cli.py`: REPL 명령어 입력 및 파싱 
- `mini_redis_core.py`: 엔진 본체 (저장, LRU, TTL, 메모리 계산 통합)
- `hash_map.py`: 커스텀 해시맵 알고리즘
- `doubly_linked_list.py`: 이중 연결 리스트
- `min_heap.py`: 최소 힙
- `dynamic_array.py`: 동적 배열
- `pub_sub.py`: Pub/Sub 기능
- `bst.py`: 이진 탐색 트리 및 순회
- `STACK_QUEUE_DEQUE.md`: 선형 자료구조 분석 문서
- `study_guide.md`: 인지과학적 초상세 학습 가이드 (필독!)
