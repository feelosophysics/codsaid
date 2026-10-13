# Mini-Redis 마스터 가이드: 탑다운(Top-Down) 스토리텔링 학습 로드맵

> **"Redis의 내부 메커니즘과 커스텀 자료구조 동작 원리"**

본 문서는 `@mission.md` 미션 요구사항을 바탕으로 작성된 Mini-Redis의 동작 원리 및 학습 가이드라인입니다. 
단순히 "Redis는 In-Memory DB다"라는 모호한 이해를 넘어, 사용자가 CLI에 명령어를 입력했을 때 컴퓨터 내부(RAM, 메모리 포인터, 자료구조)에서 어떤 일들이 일어나는지 **위에서 아래로(Top-Down)** 단계적으로 파헤칩니다.

---

## 🗺️ 전체 학습 커리큘럼 한눈에 보기

```text
[ 1단계: 숲 보기 ] In-Memory DB란 무엇인가? 왜 Redis는 극도로 빠른가?
        │
[ 2단계: 요청의 여정 ] CLI 입력을 받았을 때 시스템 내부의 3단계 파이프라인 흐름
        │
[ 3단계: 지휘관 분석 ] MiniRedis 코어 엔진과 오케스트레이션 (LRU + TTL)
        │
[ 4단계: 밑바닥 부품 ] 직접 만든 4대 자료구조 (HashMap, DoublyLinkedList, MinHeap, DynamicArray)
        │
[ 5단계: 미션 정합성 ] @mission.md 요구사항 100% 대응표 및 핵심 Q&A 10선
```

---

# 1단계. In-Memory DB란 무엇인가? 왜 Redis는 극도로 빠른가?

### 1.1 RAM vs Disk (도서관 책상과 지하 창고의 비유)
우리가 흔히 쓰는 데이터베이스(MySQL, PostgreSQL 등)는 **HDD나 SSD 같은 디스크(Storage)**에 데이터를 영구 보관합니다. 
반면 **Redis는 오직 컴퓨터의 메인 메모리(RAM)**에만 데이터를 두고 읽고 씁니다.

- **디스크 접근 속도**: 대략 **10ms (10,000,000ns)** -> *지하 3층 창고에 가서 책을 찾아오는 속도*
- **RAM 접근 속도**: 대략 **100ns** -> *지금 내 바로 앞에 있는 책상 위 책을 펼치는 속도*
- **속도 차이**: RAM은 디스크보다 **약 10만 배** 빠릅니다. 이것이 Redis가 초당 수십만 건의 요청을 처리할 수 있는 본질적인 이유입니다.

### 1.2 왜 파이썬 내장 `dict`나 `list`를 쓰지 않고 밑바닥부터 만드는가?
파이썬의 내장 `dict`나 `list`는 내부적으로 C언어로 정교하게 만들어져 있습니다. 하지만 이를 그냥 가져다 쓰면 **"메모리가 가득 찼을 때 어떤 순서로 데이터를 쫓아내는지(LRU)"**, **"초 단위 만료 시간을 어떻게 탐지해서 지우는지(TTL)"**를 내 손으로 제어할 수 없게 됩니다.

본 프로젝트에서는 파이썬 기본 기능(`[None] * N` 고정 배열)만 사용하고, 그 위에 자료구조를 직접 얹음으로써 **Redis의 내부 톱니바퀴**를 직관적으로 이해할 수 있게 제작되었습니다.

---

# 2단계. CLI 명령어의 여정 (3단계 파이프라인)

사용자가 터미널에서 `mini-redis> SET user:1 "Alice"`를 입력하고 엔터를 치는 순간, 시스템은 다음 **3단계 파이프라인**을 거칩니다.

```text
  [ 사용자 입력 ] -> mini-redis> SET user:1 "Alice"
        │
        ▼
[ 1. Data Refinement ]  "  user:1  " -> 공백 제거 "user:1", 바이트 수 계산 (6B + 5B = 11B)
        │
        ▼
[ 2. Validation ]       (1) 만료된 키 힙에서 정리 (_cleanup_expired)
                        (2) maxmemory 초과 여부 검사 (OOM 에러 사전 방지)
        │
        ▼
[ 3. Logic Execution ]  (1) HashMap 버킷에 저장
                        (2) DoublyLinkedList 맨 앞으로 이동 (LRU 최신화)
                        (3) 메모리 초과 시 LRU 제거 (_evict_lru)
        │
        ▼
  [ 결과 반환 ]        OK
```

1. **Data Refinement (데이터 정제)**: 입력받은 문자열의 양 끝 공백을 떼어내고(`strip()`), `len(key.encode('utf-8')) + len(value.encode('utf-8'))` 공식을 통해 몇 바이트의 메모리를 먹을지 미리 정밀 계산합니다.
2. **Validation (유효성 검사)**: 로직을 수행하기 직전에 만료 시간이 지난 키들을 힙에서 청소하고, 방금 들어온 데이터가 `maxmemory` 제한보다 커서 아예 못 들어가는 상황이 아닌지 체크합니다.
3. **Logic Execution (비즈니스 로직 실행)**: 검증을 통과하면 실제 해시맵에 데이터를 넣고, LRU 이중 연결 리스트의 맨 앞으로 노드를 보낸 뒤, 결과를 `OK`로 리턴합니다.

---

# 3단계. 지휘관 분석: `MiniRedis` 코어 엔진과 오케스트레이션

`MiniRedis` 클래스(`mini_redis/mini_redis_core.py`)는 마치 오케스트라의 지휘자처럼 4가지 자료구조를 조화롭게 조종합니다.

### 3.1 LRU (Least Recently Used) 캐시 제거의 미학: $O(1)$의 비밀
메모리가 꽉 찼을 때 "가장 오래전에 읽거나 쓴 데이터"를 찾아내서 지워야 합니다.
- **배열이나 리스트만 쓴다면?**: "누가 가장 오래되었지?"를 찾기 위해 전체 $N$개 데이터를 뒤져야 함 ($O(N)$ 시간 - 매우 느림!)
- **HashMap + DoublyLinkedList의 조합**:
  - `HashMap`: 키를 주면 노드의 위치(메모리 주소)를 **$O(1)$**에 즉시 찾음.
  - `DoublyLinkedList`: 찾은 노드를 맨 앞으로 옮기거나(`move_to_front`), 맨 뒤 노드를 지우는 것(`remove_back`)을 포인터 2개 변경으로 **$O(1)$**에 수행.
  - **결과**: 아무리 데이터가 100만 개 쌓여도 **단 0.0001초만에** LRU 노드를 찾아내어 제거!

```text
[Head 더미 (가장 최근 - MRU)] <-> [Node: user:3] <-> [Node: user:2] <-> [Node: user:1] <-> [Tail 더미 (가장 오래됨 - LRU)]
```

### 3.2 TTL (Time-To-Live) 만료와 지연 삭제(Lazy Deletion) 전략
"3초 뒤에 만료되는 키"를 1초마다 모든 키를 돌면서 타이머로 감시하면 CPU가 터집니다. Redis는 이를 **MinHeap + Lazy Deletion**으로 스마트하게 해결합니다.

1. **MinHeap (최소 힙)**: `(만료 타임스탬프, 키)`를 저장합니다. 힙의 맨 꼭대기(루트, 인덱스 0)에는 **"가장 먼저 만료될 녀석"**이 항상 $O(1)$에 위치합니다.
2. **지연 삭제 (Lazy Deletion)**: 초 단위 시계를 따로 돌리지 않고, **사용자가 명령어를 보낼 때마다** `_cleanup_expired()`를 호출합니다.
   - 힙의 꼭대기 `peek()`를 봅니다.
   - "어? 꼭대기에 있는 놈의 만료시간이 지금 시각보다 옛날이네?" -> 힙에서 `pop()`하고 실제 `HashMap`, `LRUList`에서 제거합니다.
   - 아직 만료 시간이 안 된 녀석이 꼭대기에 나오면 **즉시 반복문을 중단**합니다! (뒤쪽은 볼 필요도 없음)

---

# 4단계. 밑바닥 부품: 4대 커스텀 자료구조 완전 해부

### 4.1 DynamicArray (`mini_redis/dynamic_array.py`)
- **개념**: 파이썬 내장 `list` 대신 `[None] * capacity` 고정 크기 상자를 만들고 크기를 직접 관리합니다.
- **2배 리사이징 (Resize)**: 상자가 꽉 찰 때마다 용량을 2배($8 \to 16 \to 32 \dots$)로 늘리고 기존 요소를 복사합니다.
- **시간 복잡도**: $N$번 넣을 때 리사이징은 아주 가끔 일어나므로 평균 **$O(1)$ (Amortized $O(1)$)**의 삽입 속도를 자랑합니다.

### 4.2 DoublyLinkedList (`mini_redis/doubly_linked_list.py`)
- **개념**: 각 노드가 이전(`prev`)과 다음(`next`) 노드의 주소를 손에 손잡고 있는 형태입니다.
- **Head & Tail 더미 노드 (Sentinel Node)**: 맨 앞과 맨 뒤에 빈 노드를 하나씩 박아둠으로써, "리스트가 비어있을 때", "첫 번째 요소를 지울 때" 같은 **번거로운 예외 조건(`if node.prev is None`)을 코딩에서 완전히 제거**했습니다.

### 4.3 HashMap (`mini_redis/hash_map.py`)
- **개념**: 문자열 키를 숫자로 바꾸어 배열의 인덱스로 변환하는 장치입니다.
- **다항식 롤링 해시 (Polynomial Rolling Hash)**:
  $$\text{hash}(s) = \left( \sum_{i=0}^{n-1} s[i] \cdot p^i \right) \pmod m$$
  문자열의 각 철자 아스키 코드에 소수 $p=31$의 거듭제곱을 곱해 더함으로써 `"ab"`와 `"ba"`가 다른 해시값을 갖도록 충돌을 극소화합니다.
- **체이닝 (Chaining)**: 만약 해시 결과가 같은 버킷 인덱스로 충돌하면, 그 버킷 안에 `DoublyLinkedList`를 달아서 연결합니다.
- **재해싱 (Rehashing)**: 저장된 요소 개수 / 버킷 수(Load Factor)가 0.75에 도달하면 버킷을 2배로 늘려 검색 성능 $O(1)$을 유지합니다.

### 4.4 MinHeap (`mini_redis/min_heap.py`)
- **개념**: 완전 이진 트리(Complete Binary Tree)를 1차원 배열(`DynamicArray`) 위에 겹쳐서 구현한 자료구조입니다.
- **인덱스 계산 공식**:
  - 부모 노드 인덱스: `(i - 1) // 2`
  - 왼쪽 자식 인덱스: `2 * i + 1`
  - 오른쪽 자식 인덱스: `2 * i + 2`
- **`_heapify_up` & `_heapify_down`**: 새로 들어오면 아래에서 위로 삼촌/부모와 비교해 솟구치고($O(\log N)$), 최솟값이 나가면 맨 밑바닥 요소를 위에 올린 뒤 아래로 자식들과 비교하며 내려갑니다($O(\log N)$).

---

# 5단계. Mission 요구사항 대조 및 핵심 Q&A 10선

## 5.1 `@mission.md` 요구사항 100% 이행 대조표

| 요구사항 분류 | 상세 명세 | 구현 모듈 & 함수 | 이행 여부 |
| :--- | :--- | :--- | :---: |
| **기본 자료구조 배제** | `dict`, `set` 내장 모듈 사용 전면 금지 | `HashMap`, `DoublyLinkedList`, `MinHeap`, `DynamicArray` 직접 구현 | ✅ 100% |
| **String 명령어 6종** | `SET`, `GET`, `DEL`, `EXISTS`, `DBSIZE`, `KEYS` | `mini_redis/mini_redis_core.py` | ✅ 100% |
| **메모리 관리 2종** | `CONFIG SET maxmemory`, `INFO memory` | `mini_redis/mini_redis_core.py` | ✅ 100% |
| **TTL 관리 2종** | `EXPIRE`, `TTL` | `mini_redis/mini_redis_core.py` (MinHeap 연동) | ✅ 100% |
| **LRU 자동 제거** | `maxmemory` 초과 시 LRU 노드 자동 삭제 | `MiniRedis._evict_lru()` | ✅ 100% |
| **CLI & 파싱** | `mini-redis>` REPL, shlex 인자 파싱 | `mini_redis/cli.py` & `mini_redis/__main__.py` | ✅ 100% |
| **보너스 과제** | 동적 배열, BST, Pub/Sub 지원 | `dynamic_array.py`, `bst.py`, `pub_sub.py` | ✅ 100% |

---

## 5.2 핵심 Q&A 10선 (면접 & 개념 정리용)

**Q1. Redis는 왜 Single Thread(단일 스레드) 기반인데도 빠른가요?**
> **A1.** 데이터가 메모리(RAM)에 있어서 I/O 대기 시간이 없기 때문입니다. 스레드가 여러 개면 스레드끼리 줄 서는 '컨텍스트 스위칭(Context Switching)' 비용과 동기화 락(Lock) 오버헤드가 발생하는데, 단일 스레드는 이를 완전히 회피해 오직 메모리 연산에만 전념할 수 있습니다.

**Q2. HashMap에서 해시 충돌(Hash Collision)이란 무엇이고 어떻게 해결했나요?**
> **A2.** 다른 두 키(예: `"apple"`과 `"orange"`)가 해시 함수를 거쳐 나온 버킷 인덱스가 같아지는 현상입니다. 본 프로젝트는 해당 버킷 위치에 `DoublyLinkedList`를 달아 줄을 세우는 **체이닝(Chaining)** 방식으로 해결했습니다.

**Q3. 왜 LRU 구현에 단일 LinkedList가 아닌 DoublyLinkedList(이중 연결 리스트)를 썼나요?**
> **A3.** 단일 연결 리스트는 중간 노드를 지우려면 "내 앞 노드"가 누구인지 알기 위해 처음부터 찾아가는 $O(N)$ 조회가 필요합니다. 하지만 이중 연결 리스트는 노드가 자기 이전(`prev`) 주소를 직접 쥐고 있으므로, 앞뒤 포인터만 쓱 재연결하면 즉시 **$O(1)$**에 노드를 떼어낼 수 있습니다.

**Q4. 만료된 TTL 키를 주기적으로 지우지 않고 명령어가 올 때 지우는 이유(Lazy Deletion)는?**
> **A4.** 백그라운드에서 매밀리초마다 전체 키를 검사하면 무의미한 CPU 사용량이 발생합니다. 사용자가 키를 조회하거나 입력할 때만 최우선 만료 힙(`MinHeap`) 꼭대기 몇 개만 쓱 검사하는 지연 삭제 방식을 통해 CPU 자원을 극도로 아낄 수 있습니다.

**Q5. LRU 캐시에서 Head와 Tail에 더미 노드(Sentinel Node)를 두는 이유는?**
> **A5.** 노드를 맨 앞에 넣거나 뺄 때 리스트가 완전히 비어있는 상황(`head is None`)이 발생하면 매번 `if` 문 예외 처리를 해야 합니다. Head와 Tail 더미 노드를 고정해두면 예외 없이 항상 `head.next`와 `tail.prev` 포인터 조작 2줄만으로 모든 처리가 끝나 코드가 매우 단단해집니다.

**Q6. `used_memory` 계산 시 키와 값 문자열만 바이트로 세는 이유는?**
> **A6.** 파이썬 파이토치/C 내부 객체 포인터나 클래스 메타데이터 크기는 OS나 파이썬 버전마다 다릅니다. 순수 데이터 문자열의 UTF-8 바이트 합($\text{len}(\text{key}) + \text{len}(\text{val})$)을 세는 것이 Redis의 실제 메모리 산정 기준과 가장 부합하기 때문입니다.

**Q7. MinHeap에서 왜 부모 인덱스가 `(i - 1) // 2` 인가요?**
> **A7.** 완전 이진 트리를 1차원 배열로 펼치면 레벨마다 요소 개수가 1, 2, 4, 8개로 2배씩 늘어납니다. 자식 인덱스가 $2i+1, 2i+2$가 되므로, 그 역연산을 수식으로 정리하면 정확히 `(i - 1) // 2`가 됩니다.

**Q8. HashMap의 Load Factor가 0.75를 넘으면 왜 2배로 확장(Rehashing)하나요?**
> **A8.** 버킷 수에 비해 데이터가 너무 많아지면 체이닝 리스트가 길어져 검색 속도가 $O(1)$에서 $O(N)$으로 떨어집니다. 로드 팩터 0.75 시점에 버킷을 2배로 늘려 노드들을 재배치함으로써 constant time 검색 속도를 보장합니다.

**Q9. CLI 인터랙티브 모드에서 `python3 -m mini_redis`로 실행하는 이유는?**
> **A9.** 독립된 낱개 스크립트 실행 대신 패키지(`mini_redis/`) 이름공간과 `__main__.py` 진입점을 활용하여, 타 모듈 파일명 충돌을 방지하고 깔끔한 파이썬 모듈 실행 표준을 준수하기 위함입니다.

**Q10. 만약 싱글 엔트리 키-값 크기 자체가 `maxmemory`보다 크면 어떻게 되나요?**
> **A10.** LRU로 기존 데이터를 다 지워도 그 1개조차 담을 수 없으므로, 아무 데이터도 지우거나 넣지 않고 즉시 `OOM command not allowed` 에러를 반환하여 기존 저장 데이터를 보호합니다.

---

# 6단계. 브라우저 시각화 시뮬레이터 및 코드 주석 안내

- **인터랙티브 웹 대시보드**: [visualizer.html](file:///Users/f22losophysics1091/Desktop/ready/study/visualizer.html) 파일에서 브라우저를 통해 실시간 HashMap 버킷, LRU 노드 체인, MinHeap 트리의 애니메이션 동작을 확인하실 수 있습니다.
- **소스코드 상세 주석**: [mini_redis/](file:///Users/f22losophysics1091/Desktop/ready/mini_redis) 패키지 내 모든 소스 파일에 라인별 기술 설명이 추가되어 있습니다.
