---
title: "Codyssey B5-1 Mini Redis 초상세 학습 가이드"
tags: ["#project/codyssey", "#mission/b5-1", "#cs/data-structures", "#cs/cache", "#prog/python", "#education/study-guide"]
created: 2026-09-20
updated: 2026-09-20
status: draft
type: draft
source: "ready/mini_redis 및 ready/tests 실제 구현과 01_Buffer/_Drafts/b5-1_mission.md"
semantic_compression:
  invariants:
    - "store는 키에서 LRU Node를 찾고, lru_list는 최근성 순서를 보존하며, ttl_map과 ttl_heap은 최신 만료 시각을 검증한다."
    - "used_memory는 자료구조 오버헤드를 제외한 UTF-8 키·값 payload 바이트 합이다."
    - "명령 전에 만료를 지연 정리하고, SET 이후 초과하면 tail의 LRU부터 제거한다."
  boundaries:
    - "네트워크·영속성·동시성·복잡 자료형은 구현하지 않는다."
    - "Pub/Sub와 BST는 핵심 String/LRU/TTL 경로가 아니라 보너스 학습 범위다."
  core_thesis: "Mini Redis는 HashMap의 즉시 조회, DoublyLinkedList의 즉시 순서 갱신, MinHeap의 가장 이른 만료 탐색을 하나의 상태 불변식으로 결합한 학습용 인메모리 엔진이다."
---

# Codyssey B5-1 Mini Redis 초상세 학습 가이드

이 문서는 ready 레포의 실제 구현을 읽고, 동료에게 코드를 열어 놓은 채 방어할 수 있도록 만든 학습 문서다. 목표는 명령어 목록을 외우는 것이 아니라 다음 질문에 코드로 답하는 것이다.

> 키 하나가 들어왔을 때, 어떤 자료구조에 어떤 노드가 생기고, 최근성·만료·메모리 카운터가 어떻게 동시에 움직이는가?

이 가이드는 미션 명세의 이상적인 설계와 현재 코드의 실제 동작을 구분한다. 특히 코드가 명세를 완전히 만족한다고 가정하지 않고, 검토자가 물을 수 있는 차이도 함께 기록한다.

## 0. 먼저 잡을 전체 멘탈 모델

    사용자 입력
      ↓
    cli.py: shlex.split → 명령 분기 → Redis 스타일 출력
      ↓
    MiniRedis 명령 메서드
      ├─ store: HashMap[key → LRU Node 참조]
      ├─ lru_list: Head(MRU) ↔ ... ↔ Tail(LRU)
      ├─ ttl_map: HashMap[key → 최신 expire_at]
      ├─ ttl_heap: MinHeap[(expire_at, key)]
      └─ used_memory / maxmemory / evicted_keys
      ↓
    결과: OK / 값 / (nil) / (integer) N / (error) ...

핵심은 store, lru_list, ttl_map, ttl_heap가 서로 중복된 저장소라는 뜻이 아니다. 각각 다른 질문에 답한다.

| 질문 | 담당 구조 | 필요한 이유 |
| --- | --- | --- |
| 이 키의 값을 어디서 즉시 찾는가? | store | 평균 O(1) 키 조회 |
| 어떤 키가 가장 오래되었는가? | lru_list | Head는 MRU, Tail은 LRU |
| 이 키의 최신 만료 시각은 언제인가? | ttl_map | 오래된 힙 항목을 판정 |
| 전체 키 중 무엇이 가장 먼저 만료되는가? | ttl_heap | 최소 만료 시각을 루트에서 확인 |
| 현재 payload가 몇 바이트인가? | used_memory | maxmemory와 비교 |

이 네 구조의 상태가 서로 어긋나면 Mini Redis는 “값은 있는데 LRU에는 없는 키”, “TTL은 만료됐는데 메모리 카운터에는 남은 키” 같은 유령 상태를 만든다. 따라서 모든 단계에서 자료구조 하나의 동작보다 교차 구조 불변식을 먼저 확인한다.

---

# 1단계. 미션의 본질: Redis를 왜 밑바닥부터 만드는가

## 왜 필요한가

Redis를 단순히 “빠른 DB”라고 외우면 SET 한 번이 왜 빠른지, 메모리가 차면 무엇을 버리는지, TTL이 많은 키를 어떻게 감시하는지 설명할 수 없다. 이 미션은 네트워크 서버를 만드는 과제가 아니라, 인메모리 key-value 엔진의 핵심 물리 구조를 작은 규모로 재현하는 과제다.

Redis는 데이터를 RAM에 두므로 디스크 기반 DB보다 접근 경로가 짧다. 하지만 RAM에 둔다는 사실만으로 LRU, TTL, 충돌 처리, 메모리 제한이 자동 해결되지는 않는다. 빠른 조회와 정리 정책을 함께 설계해야 한다.

## 초보자용 비유

디스크 DB는 지하 창고에서 물건을 찾아오는 가게이고, Redis는 계산대 바로 뒤의 작은 선반이다. 선반은 빠르지만 공간이 작다. 그래서 자주 쓰는 물건은 앞에 두고, 오래 안 쓴 물건은 버리며, 유통기한이 지난 물건은 손님이 오기 전에 치워야 한다.

## 선수 개념

- RAM과 디스크의 접근 경로 차이
- key-value 자료 모델
- 캐시와 영속 DB의 역할 차이
- 평균 O(1), O(log N), O(N)의 의미
- UTF-8에서 문자의 바이트 길이가 항상 1은 아니라는 사실

## 실제 읽을 파일

- 미션 요구사항: mission.md
- 프로젝트 개요: README.md
- 코어 엔진: mini_redis/mini_redis_core.py
- 실행 진입점: mini_redis/__main__.py, mini_redis/cli.py

## 코드 현미경

MiniRedis.__init__()는 단순히 빈 변수 몇 개를 만드는 생성자가 아니다. store, lru_list, ttl_heap, ttl_map 네 개의 인덱스를 동시에 초기화한다. 이 순간부터 엔진은 “값 저장”, “최근성”, “만료”, “메모리 제한”을 서로 다른 축으로 추적할 준비를 한다.

메모리 공식은 다음과 같다.

    used_memory = Σ(len(key.encode("utf-8")) + len(str(value).encode("utf-8")))

현재 구현은 Node, 포인터, 빈 버킷, 힙 배열 같은 Python 객체 오버헤드를 포함하지 않는다. 그러므로 used_memory는 실제 프로세스 RSS가 아니라 미션 채점용 payload 모델이다.

## 전체 도식

    영속성 없음 ──┐
    네트워크 없음 ─┼─> 작은 단일 프로세스 메모리 엔진
    동시성 없음 ──┘             │
                                ├─ 빠른 키 조회: HashMap
                                ├─ 공간 압박: LRU eviction
                                └─ 시간 압박: TTL + MinHeap

## 복잡도

| 관점 | 현재 설계 |
| --- | --- |
| 키 조회 | HashMap 평균 O(1), 충돌 체인 최악 O(K) |
| LRU tail 제거 | O(1) |
| TTL 삽입 | MinHeap push O(log N) |
| 가장 빠른 TTL 확인 | MinHeap peek O(1) |
| 전체 키 출력 | O(N) |
| 저장성 | 프로세스 종료 시 소실 |

## 정상·실패·경계 사례

- 정상: SET user:1 Alice 후 GET user:1은 값을 돌려준다.
- 캐시 한계: maxmemory를 작게 설정하면 새 키를 넣을 때 기존 LRU가 제거된다.
- 시간 경계: TTL이 지나도 별도 타이머가 아니라 다음 명령이 들어올 때 lazy cleanup이 실행된다.
- 비목표: 파일 저장, 네트워크 프로토콜, Redis List/Set/Sorted Set, 멀티스레딩은 구현하지 않는다.

## 관련 테스트

- tests/test_mini_redis.py::test_mini_redis_basic_set_get_del
- tests/test_mini_redis.py::test_mini_redis_lru_eviction
- tests/test_mini_redis.py::test_mini_redis_ttl_expiration

## 손으로 추적하는 연습

CONFIG SET maxmemory 10 뒤 SET k1 v1, SET k2 v2, GET k1, SET k3 v3를 실행하라. 각 키의 payload는 4바이트다. 세 개를 넣는 순간 12바이트가 되므로, GET k1로 최신화된 k1을 보존하고 k2를 제거해야 한다.

## 동료에게 설명하는 한 문장

> 이 미션은 Redis의 네 가지 질문—찾기, 오래됨, 만료, 공간—을 서로 다른 자료구조로 분리한 뒤 하나의 메모리 엔진으로 조립하는 과제다.

## 피어리뷰 질문과 방어 포인트

질문: RAM에 있으면 왜 무조건 빠른가요?

방어: RAM 접근 자체보다 중요한 것은 자료구조다. 전체 키를 순회하면 RAM이어도 O(N)이므로, HashMap과 LRU/TTL 인덱스로 필요한 후보를 좁혀야 한다.

## 단계 완료 기준

- Redis가 인메모리라는 말과 캐시라는 말의 차이를 설명한다.
- payload 메모리 공식과 오버헤드 제외 규칙을 말한다.
- 핵심 범위와 보너스 범위를 구분한다.

---

# 2단계. 실행 진입점과 전체 데이터 흐름

## 왜 필요한가

자료구조부터 읽으면 전체 맥락을 잃기 쉽다. 먼저 사용자의 한 줄 입력이 어떤 함수들을 통과하는지 보면 각 자료구조가 어디에 끼어드는지 선명해진다.

## 초보자용 비유

공항의 흐름과 같다. __main__.py는 공항 입구, cli.py는 체크인 창구, MiniRedis는 관제실, HashMap·리스트·힙은 관제실 안의 전문 장비다.

## 선수 개념

- Python package와 python -m mini_redis
- if __name__ == "__main__"
- 함수 호출과 반환값
- 파서와 실행기의 책임 분리

## 실제 읽을 파일과 함수

- mini_redis/__init__.py: 공개 API와 __all__
- mini_redis/__main__.py: main() 호출
- mini_redis/cli.py: main(), handle_command(), print_error()
- mini_redis/mini_redis_core.py: MiniRedis.set(), get(), delete() 등
- mini_redis/constants.py: 명령어와 응답 상수

## 코드 현미경: SET 한 줄

    main()
      └─ input("mini-redis> ")
          └─ handle_command(line, db, pubsub)
              ├─ shlex.split(line)
              ├─ args 개수 확인
              ├─ db.set(args[1], args[2])
              └─ print("OK")

shlex.split('SET user:1 "Alice Kim"')은 ['SET', 'user:1', 'Alice Kim']을 만든다. 단순 str.split()이었다면 값이 두 토큰으로 쪼개져 인자 개수 오류가 난다.

cli.py는 값을 저장하지 않는다. 명령어의 텍스트를 해석하고 코어 메서드를 호출한 뒤 출력 형식을 입힌다. 실제 상태 변경은 MiniRedis의 책임이다.

## 상태 변화 도식

    "SET user:1 \"Alice Kim\""
          ↓ shlex.split
    [SET, user:1, Alice Kim]
          ↓ 분기
    MiniRedis.set("user:1", "Alice Kim")
          ↓
    OK

## 정상·실패·경계 사례

- SET k v: OK
- GET k: 코어는 v, CLI는 "v"로 출력
- GET: 인자 개수 오류
- HELLO: (error) ERR unknown command 'HELLO'
- SET k "unclosed: shlex.split의 ValueError를 잡아 unbalanced quotes 오류 출력
- exit, quit: handle_command()가 False를 반환하여 REPL 종료

## 복잡도

- shlex.split: 입력 길이를 M이라 할 때 O(M)
- 명령 분기: 명령 종류 수가 고정이므로 O(1)
- 실제 명령 비용은 호출한 코어 메서드 비용을 따른다.

## 관련 테스트

- tests/test_mini_redis.py::test_cli_unbalanced_quotes
- tests/test_mini_redis.py의 handle_command import 부분과 미션의 CLI 요구사항

## 손으로 추적하는 연습

다음 입력 세 개의 args와 출력 책임자를 적어라.

    SET greeting "hello world"
    GET greeting
    CONFIG SET maxmemory abc

첫 번째는 shlex가 값 하나를 보존하고, 두 번째는 코어의 문자열에 CLI가 따옴표를 붙이며, 세 번째는 int() 실패를 CLI가 표준 에러로 변환한다.

## 동료에게 설명하는 한 문장

> CLI는 문자열을 토큰으로 바꾸고 출력 포맷을 책임지며, 데이터 구조와 정책의 진짜 소유자는 MiniRedis 코어다.

## 피어리뷰 질문과 방어 포인트

질문: 왜 cli.py에서 바로 Python dict에 저장하지 않았나요?

방어: CLI는 입출력 계층이고, 저장·LRU·TTL 불변식은 코어 계층이 맡아야 한다. 내장 dict를 쓰면 미션의 자료구조 학습 목적도 우회한다.

## 단계 완료 기준

- python -m mini_redis가 __main__.py를 통해 cli.main()으로 연결됨을 설명한다.
- shlex.split이 따옴표 값과 오류를 어떻게 처리하는지 말한다.
- CLI와 코어의 책임을 섞지 않는다.

---

# 3단계. DynamicArray: 모든 구조의 바닥 저장소

## 왜 필요한가

HashMap의 버킷 테이블과 MinHeap의 트리 저장소는 연속적인 인덱스 공간이 필요하다. Python list의 자동 확장을 그대로 믿지 않고 [None] * capacity 버퍼와 크기 변수를 직접 관리하면 동적 배열의 원리를 볼 수 있다.

## 초보자용 비유

8칸짜리 사물함이 꽉 차면 16칸짜리 새 사물함을 만들고 물건을 옮긴다. 평소에는 바로 빈 칸에 넣지만, 가끔 전체 이사가 발생한다.

## 선수 개념

- 배열의 연속 인덱스
- capacity와 현재 size의 차이
- 얕은 참조 복사
- 분할상환(amortized) 분석

## 실제 파일과 메서드

mini_redis/dynamic_array.py의 DynamicArray.__init__, capacity, size, append, _resize, _check_bounds, get, set, remove_at, pop을 순서대로 읽는다.

## 코드 현미경

    self._capacity = capacity
    self._size = 0
    self._data = [None] * self._capacity

capacity는 방의 총수, size는 실제 물건 수다. append()는 size == capacity일 때 먼저 _resize()를 호출하고, data[size]에 넣은 뒤 size를 하나 증가시킨다.

    capacity=2, size=2: [A][B]
    append(C)
      ↓ resize
    capacity=4: [A][B][None][None]
      ↓ append
    size=3:     [A][B][C][None]

remove_at(index)는 중간을 지운 뒤 오른쪽 원소를 한 칸씩 당기므로 O(N)이다. 반면 pop()은 마지막 원소만 빼므로 O(1)이다. MinHeap이 마지막 원소를 루트로 옮길 때 pop()을 사용한다.

## 정상·실패·경계 사례

- capacity가 0 이하이면 생성자에서 ValueError
- get(-1), get(size)는 _check_bounds()에서 IndexError
- 빈 배열 pop()은 IndexError
- 중간 삭제는 데이터를 잃지 않도록 shift해야 한다.
- remove_at() 후 마지막 슬롯을 None으로 비워 참조를 놓는다.

## 복잡도

| 연산 | 복잡도 | 이유 |
| --- | --- | --- |
| get, set | O(1) | 인덱스 직접 접근 |
| append 평상시 | O(1) | 빈 슬롯 한 칸 사용 |
| _resize | O(N) | 기존 원소 복사 |
| append 분할상환 | O(1) | 용량을 두 배로 늘림 |
| remove_at | O(N) | 뒤 원소 shift |
| pop | O(1) | 끝 원소 제거 |

## 관련 테스트

tests/test_custom_ds.py::test_dynamic_array는 초기 capacity 2, 두 번의 append, 세 번째 append에서 2배 확장, 인덱스 조회·대입을 확인한다.

## 손으로 추적하는 연습

capacity 4 배열에 A, B, C를 넣고 remove_at(1)을 하라. 최종 버퍼는 [A, C, None, None], size는 2여야 한다. pop()은 C를 반환하고 [A, None, None, None]을 만든다.

## 동료에게 설명하는 한 문장

> DynamicArray는 자동으로 커지는 Python list를 흉내 내되, 버퍼·size·resize를 눈앞에 드러내 HashMap과 Heap의 기초를 제공한다.

## 피어리뷰 질문과 방어 포인트

질문: 왜 매번 capacity를 한 칸만 늘리지 않고 두 배로 늘리나요?

방어: 한 칸씩 늘리면 N번 삽입 동안 복사가 O(N²)가 된다. 두 배 확장은 총 복사량이 기하급수적으로 제한되어 append 분할상환 비용이 O(1)이 된다.

## 단계 완료 기준

- size와 capacity를 혼동하지 않는다.
- remove_at이 O(N), pop이 O(1)인 이유를 설명한다.
- DynamicArray가 HashMap과 MinHeap의 하부 저장소임을 추적한다.

---

# 4단계. DoublyLinkedList: 포인터로 최근성을 표현하기

## 왜 필요한가

LRU는 “가장 최근 사용된 것부터 가장 오래된 것까지”의 순서를 유지해야 한다. 배열이나 단일 연결 리스트에서 중간 노드를 이동하려면 탐색이 필요하지만, 이중 연결 리스트는 대상 노드가 prev와 next를 이미 가지고 있어 양옆만 다시 연결하면 된다.

## 초보자용 비유

사람들이 양손으로 앞사람과 뒷사람의 손을 잡고 서 있는 줄이다. 한 사람을 줄에서 빼려면 앞사람과 뒷사람의 손만 서로 잡게 하면 된다.

## 선수 개념

- 노드와 포인터 참조
- 연결 리스트의 삽입·삭제
- sentinel/dummy node
- MRU와 LRU의 방향

## 실제 파일과 메서드

mini_redis/doubly_linked_list.py의 Node, DoublyLinkedList.__init__, insert_front, insert_back, remove_node, move_to_front, remove_back, remove_front, values를 읽는다.

## 실제 구현과 명세의 차이

미션은 노드에 prev, next, data 필드를 요구하지만, 이 레포의 실제 Node는 key, value, prev, next를 가진다. LRU eviction 때 tail 노드만 보고도 삭제할 키와 값을 알아야 하므로 key와 value를 직접 보관한 설계다. “data 하나”라는 추상 요구를 실제 엔진에 필요한 필드로 구체화한 것이다.

## 코드 현미경: sentinel 두 개

    head(dummy) ↔ tail(dummy)

빈 리스트에서도 head.next와 tail.prev가 존재한다. 실제 원소가 하나 들어오면 다음이 된다.

    head ↔ node ↔ tail

insert_front(node)의 핵심은 네 연결을 설정하는 것이다.

    node.prev = head
    node.next = first_node
    head.next = node
    first_node.prev = node

remove_node(node)은 반대로 다음 두 연결을 바꾼다.

    node.prev.next = node.next
    node.next.prev = node.prev
    node.prev = None
    node.next = None

move_to_front가 O(1)인 이유는 노드를 찾는 일이 이미 끝났다는 전제 때문이다. 코어는 store.get(key)로 LRU Node를 먼저 얻는다.

## 상태 변화 도식

    처음: head ↔ A ↔ B ↔ tail
    move_to_front(B)
    1) B 양옆 연결 복구: head ↔ A ↔ tail, B 고립
    2) B를 head 뒤에 삽입: head ↔ B ↔ A ↔ tail

## 정상·실패·경계 사례

- 빈 리스트에서 remove_front/remove_back은 None
- insert_front(None)은 ValueError
- remove_node는 이미 고립된 노드에 대해 조용히 반환
- move_to_front는 None이면 반환
- 같은 노드를 리스트에 중복 삽입하면 size 불변식이 깨질 수 있으므로 호출자는 먼저 제거해야 한다. 코어의 overwrite 경로가 그 순서를 지킨다.

## 복잡도

insert_front, insert_back, remove_node, remove_front, remove_back, move_to_front는 모두 O(1)이다. values처럼 전체를 순회하는 메서드는 O(N)이다.

## 관련 테스트

tests/test_custom_ds.py::test_doubly_linked_list는 두 노드를 넣고 하나를 앞으로 이동한 뒤 tail을 제거하여 LRU 방향과 size를 검증한다.

## 손으로 추적하는 연습

add_front(k1,v1), add_front(k2,v2), move_to_front(n1), remove_back()의 결과를 적어라. 순서는 k1, k2가 되고, 제거되는 것은 k2다.

## 동료에게 설명하는 한 문장

> 이중 연결 리스트는 노드의 양옆 포인터만 재연결해 이미 알고 있는 노드를 O(1)에 이동·삭제하고, head와 tail을 MRU/LRU 경계로 사용한다.

## 피어리뷰 질문과 방어 포인트

질문: 단일 연결 리스트면 안 되나요?

방어: 단일 연결 리스트는 대상의 앞 노드를 찾기 위해 머리부터 순회해야 한다. LRU의 GET마다 이 비용을 내면 O(1) 목표가 무너진다.

## 단계 완료 기준

- prev와 next를 이용해 네 포인터 변경을 그릴 수 있다.
- sentinel이 빈 리스트와 단일 원소 경계를 어떻게 단순화하는지 설명한다.
- move_to_front가 “탐색”이 아니라 “이미 받은 Node 참조의 재배치”임을 안다.

---

# 5단계. HashMap: 키를 버킷과 체인으로 바꾸기

## 왜 필요한가

LRU와 TTL 모두 키를 빠르게 찾아야 한다. Python dict 대신 문자열 키를 숫자 해시로 바꾸고, 버킷 안에서 충돌을 체이닝으로 해결한다.

## 초보자용 비유

도서관 사서가 책 제목을 그대로 모든 책장에 붙이지 않고, 제목을 계산해 책장 번호를 정한다. 같은 책장 번호가 나온 책은 그 책장 안의 작은 줄에 함께 세운다.

## 선수 개념

- 해시 함수와 버킷
- 충돌(collision)
- separate chaining
- load factor
- rehash

## 실제 파일과 메서드

mini_redis/hash_map.py의 __init__, _hash, _get_bucket_index, put, get, remove, contains_key, keys, _resize를 읽는다. 버킷 저장에는 DynamicArray, 버킷 내부 체인에는 DoublyLinkedList를 사용한다.

## 코드 현미경: 해시와 인덱스

실제 해시는 다음 누적식이다.

    hash_val = 0
    p = 31
    m = 1_000_000_009
    p_pow = 1
    각 char에 대해:
      hash_val = (hash_val + ord(char) * p_pow) % m
      p_pow = (p_pow * p) % m
    bucket_index = hash_val % capacity

입력은 문자열 key다. ord(char)로 각 문자의 코드 포인트를 받고, 위치에 따라 31의 거듭제곱 가중치를 붙인다. 마지막으로 큰 소수 m으로 줄이고, 현재 버킷 수로 한 번 더 나눠 실제 배열 범위에 맞춘다.

이 함수가 충돌을 절대 없애는 것은 아니다. abc와 cba처럼 순서가 다른 문자열을 다른 값으로 만들 가능성을 높일 뿐이며, 최종 버킷 인덱스가 같아지는 충돌은 언제든 가능하다.

## 충돌 체이닝

    bucket[3]
      └─ chain: head ↔ (keyA,valueA) ↔ (keyB,valueB) ↔ tail

put은 먼저 체인을 순회해 같은 키가 있는지 확인한다. 있으면 값을 덮어쓰고, 없으면 새 Node를 체인 앞에 삽입한다. 이 체인의 Node와 LRU 리스트의 Node는 역할이 다르다. store에서는 체인 Node의 value가 LRU Node 참조가 된다.

## load factor와 rehash

현재 구현의 조건은 미션 문장의 “0.75 초과”보다 한 단계 이른 size / capacity >= 0.75다. 즉 8개 버킷에서 size가 6일 때 put 시작 전에 확장될 수 있다. 동료에게는 명세와 구현을 모두 말해야 한다.

확장 절차는 다음과 같다.

    old_buckets 보관
    capacity *= 2
    새 DynamicArray(capacity) 생성
    각 버킷에 빈 DoublyLinkedList 생성
    old_buckets의 모든 체인을 순회
      각 (key,value)에 대해 새 capacity로 put

capacity가 바뀌면 hash % capacity 결과도 바뀔 수 있으므로 원소를 단순 복사할 수 없다. 모든 원소를 새 위치로 재해싱해야 한다.

## 정상·실패·경계 사례

- 같은 키 put: size를 늘리지 않고 값만 갱신
- 다른 키가 같은 bucket: 체인에 함께 저장
- None value: get은 None을 반환할 수 있으므로 존재 판정은 contains_key로 해야 한다.
- 문자열이 아닌 key: put은 TypeError, 조회 계열은 안전하게 실패
- keys는 모든 버킷과 체인을 순회하므로 O(N)

## 복잡도

평균 put/get/remove/contains는 O(1), 충돌 체인 길이를 K라 하면 최악 O(K)다. _resize는 O(N), 재해싱이 섞인 삽입은 분할상환 관점에서 평균 O(1)로 본다. keys는 O(N)이다.

## 관련 테스트

tests/test_custom_ds.py::test_hash_map은 put/get/remove/contains, 없는 키, None 값, 기본 동작을 확인한다. 테스트 이름만으로는 특정 충돌 키와 rehash를 직접 증명하지 않으므로, 학습자는 _hash 또는 작은 초기 capacity를 이용한 추가 손추적을 해야 한다.

## 손으로 추적하는 연습

capacity 4인 HashMap에 a, b, c를 넣는다고 하자. 각 key의 hash와 hash % 4를 계산하고, 동일 인덱스가 있다면 체인 순서를 그린다. 이어 capacity 8로 확장했을 때 각 key가 어느 bucket으로 이동하는지 다시 계산한다.

## 동료에게 설명하는 한 문장

> 해시는 키를 버킷 번호로 압축하고, 충돌은 버킷 내부 이중 연결 리스트로 보존하며, load factor가 높아지면 전체 키를 새 용량 기준으로 재배치한다.

## 피어리뷰 질문과 방어 포인트

질문: 해시가 같으면 데이터가 덮어써지지 않나요?

방어: 해시 자체를 키로 쓰지 않고 bucket 안에서 원래 문자열 key를 다시 비교한다. 같은 bucket에 다른 key가 들어와도 체인으로 공존한다.

질문: 왜 0.75 초과가 아니라 >= 인가요?

방어: 현재 코드의 실제 조건은 >=다. 미션의 엄밀한 문장과 구현의 경계를 정확히 지적하고, 평가 기준이 어느 쪽인지 확인해야 한다.

## 단계 완료 기준

- ord → polynomial accumulation → modulo capacity를 설명한다.
- 체이닝의 버킷 내부 자료구조와 같은 키 덮어쓰기 흐름을 설명한다.
- rehash가 “버킷 배열만 복사”가 아니라 “새 인덱스로 재삽입”임을 안다.

---

# 6단계. MinHeap: 가장 빠른 TTL을 먼저 찾기

## 왜 필요한가

TTL이 있는 키가 N개일 때 모든 키를 매번 검사하면 O(N)이다. 만료 시각이 가장 작은 항목을 루트에 유지하면 현재 정리해야 할 후보를 빠르게 확인할 수 있다.

## 초보자용 비유

유통기한이 가장 빠른 식품을 맨 위에 놓는 냉장고다. 맨 위 식품이 아직 안 상했다면 아래 식품은 더 늦게 상하므로 지금 검사할 필요가 없다.

## 선수 개념

- 완전 이진 트리
- 우선순위 큐
- 배열 기반 트리
- tuple의 사전식 비교
- heapify up/down

## 실제 파일과 메서드

mini_redis/min_heap.py의 _swap, _heapify_up, _heapify_down, push, pop, peek, size와 dynamic_array.py의 append, pop, get, set을 함께 읽는다.

## 배열 인덱스 공식

0-based 배열에서 index i의 관계는 다음과 같다.

    parent = (i - 1) // 2
    left   = 2*i + 1
    right  = 2*i + 2

push(expire_at, key)는 실제로 (expire_at, key) tuple을 저장한다. Python tuple 비교는 첫 번째 값인 expire_at를 먼저 비교하고, 시간이 같으면 key를 비교하므로 최소 만료 시각이 먼저 나온다.

## 코드 현미경

    push:
      DynamicArray 맨 끝에 item 추가
      부모보다 작으면 swap하며 위로

    pop:
      루트 백업
      마지막 원소를 pop하여 0번으로 이동
      더 작은 자식과 swap하며 아래로

peek는 원소를 빼지 않고 0번만 읽으므로 O(1)이다. pop은 루트 복구에 트리 높이만큼 이동하므로 O(log N)이다.

## 정상·실패·경계 사례

- 빈 힙 peek은 None
- 빈 힙 pop은 IndexError
- 요소 하나 pop은 배열 pop만 수행
- 같은 expire_at이면 key가 tie-breaker가 된다.
- TTL 갱신 시 새 tuple을 push하고 이전 tuple은 힙에 남을 수 있다. 코어가 ttl_map으로 최신성을 검증한다.

## 상태 변화 도식

    push(10,A), push(5,B), push(15,C)
    배열의 힙 루트: (5,B)
    pop()
      root=(5,B) 반환
      last=(15,C)를 0번으로 이동
      children과 비교해 (10,A)가 루트가 됨

## 복잡도

peek O(1), push O(log N), pop O(log N), size O(1)이다. _cleanup_expired()는 만료된 K개를 제거하면 대략 O(K log N)이고, 아무것도 만료되지 않았으면 루트 한 번 확인하고 O(1)에 끝난다.

## 관련 테스트

tests/test_custom_ds.py::test_min_heap은 10.5, 5.0, 15.2를 넣고 5.0이 peek/pop되는지 확인한다. tests/test_mini_redis.py::test_mini_redis_ttl_expiration은 실제 시간 경과 후 코어와 결합된 lazy deletion을 검증한다.

## 손으로 추적하는 연습

(12,A), (4,B), (8,C), (2,D)를 순서대로 push하고 매번 배열을 적어라. 각 push 뒤 부모보다 작은 값이 위로 이동하여 2가 루트가 되는 과정을 표시한다.

## 동료에게 설명하는 한 문장

> MinHeap은 전체 TTL을 매초 순회하지 않고, 가장 빠른 만료 후보 하나를 루트에 고정해 확인 비용을 줄인다.

## 피어리뷰 질문과 방어 포인트

질문: TTL을 HashMap만으로 관리하면 안 되나요?

방어: HashMap은 특정 key의 TTL 조회에는 좋지만 가장 빠른 만료 key를 알려주지 못한다. 전체 key를 훑어야 하므로 MinHeap을 추가한다.

## 단계 완료 기준

- 배열 인덱스 공식으로 부모·자식을 계산한다.
- peek와 pop의 복잡도 차이를 설명한다.
- stale heap entry를 ttl_map과 함께 해석한다.

---

# 7단계. MiniRedis 상태 모델과 교차 구조 불변식

## 왜 필요한가

개별 자료구조를 이해해도 코어의 상태가 어떻게 겹치는지 모르면 SET, DEL, EXPIRE, eviction에서 버그를 만든다. 하나의 논리적 키가 여러 물리 구조에 표현된다.

## 초보자용 비유

한 손님에 대해 매장에는 상품 본체, 대기 줄의 위치표, 유통기한 알림표, 유통기한 우선순위 보드가 따로 있다. 손님이 떠나면 네 기록을 모두 정리해야 한다.

## 선수 개념

- 인덱스와 본체의 분리
- 객체 참조
- 상태 불변식
- 삭제의 원자적 의미

## 실제 상태 필드

mini_redis/mini_redis_core.py의 생성자를 기준으로 다음을 그린다.

    store:    HashMap[key → LRU Node]
    lru_list: DoublyLinkedList[LRU Node]
    ttl_map:  HashMap[key → expire_at]
    ttl_heap: MinHeap[(expire_at, key)]

여기서 store의 HashMap 체인 Node와 lru_list의 LRU Node는 별개 객체일 수 있다. store의 값이 LRU Node 참조를 들고 있으므로 key로 LRU 노드를 찾아 즉시 이동할 수 있다.

## 핵심 불변식

1. store.contains(key)가 참이면 해당 key의 LRU Node가 lru_list에 연결되어 있어야 한다.
2. used_memory는 store에 살아 있는 각 key/value payload의 합이어야 한다.
3. ttl_map에 현재 만료 시각이 있으면 해당 key는 store에도 있어야 한다.
4. ttl_heap에는 과거 TTL entry가 남을 수 있지만, 삭제·갱신된 entry는 ttl_map 비교에서 무효로 판정되어야 한다.
5. lru_list.head.next는 MRU, lru_list.tail.prev는 LRU다.

## 코드 현미경: 삭제 경로

_raw_delete(key)는 store.get(key)로 LRU Node를 얻고, 메모리를 계산해 빼고, lru_list.remove_node(node), store.remove(key), ttl_map.remove(key)를 순서대로 호출한다. ttl_heap에서 과거 entry를 직접 찾아 지우지 않는 대신, 나중에 cleanup이 ttl_map을 확인해 무시한다.

## 정상·실패·경계 사례

- 정상 SET: store·LRU·memory가 함께 증가
- 기존 key SET: 이전 LRU Node를 제거하고 이전 payload를 먼저 반환하며 TTL을 지운다.
- DEL: 값이 없으면 (integer) 0
- TTL 만료: store·LRU·ttl_map·memory가 정리되고, stale heap tuple은 나중에 무시된다.
- LRU eviction: evicted_keys는 증가하지만 TTL 만료 삭제에는 증가하지 않는다.

## 복잡도

정상 key를 store에서 찾고 LRU Node를 조작하는 핵심 경로는 평균 O(1)이다. TTL cleanup이 한 번에 여러 키를 지우면 O(K log N)이다. keys는 전체 순회 O(N)이다.

## 관련 테스트

- tests/test_mini_redis.py::test_mini_redis_basic_set_get_del
- tests/test_mini_redis.py::test_mini_redis_lru_eviction
- tests/test_mini_redis.py::test_mini_redis_ttl_expiration

## 손으로 추적하는 연습

SET a 1, EXPIRE a 5, SET b 2 뒤 네 구조를 표로 적어라. a는 ttl_map과 ttl_heap에 있고, b는 TTL 구조에 없다. 이후 SET a 9를 하면 old TTL map은 제거되고 새 heap tuple은 아직 생기지 않는다.

## 동료에게 설명하는 한 문장

> MiniRedis의 핵심은 한 키를 네 번 저장하는 것이 아니라, 조회·순서·만료·메모리라는 서로 다른 질의를 각각 가장 잘하는 인덱스를 동기화하는 것이다.

## 피어리뷰 질문과 방어 포인트

질문: TTL heap에 키가 남아 있는데 삭제가 덜 된 것 아닌가요?

방어: heap은 append-only에 가까운 후보 큐이고 ttl_map이 최신성의 권위다. 갱신된 과거 tuple은 cleanup 시 current TTL과 불일치하여 버려진다.

## 단계 완료 기준

- 하나의 키가 네 구조에 어떤 형태로 나타나는지 그린다.
- 삭제 시 어느 구조를 반드시 정리해야 하는지 말한다.
- eviction과 expiration의 카운터 의미를 구분한다.

---

# 8단계. HashMap + DoublyLinkedList로 O(1) LRU 만들기

## 왜 필요한가

LRU는 두 가지 일을 동시에 해야 한다. 첫째 key를 주면 해당 데이터의 현재 위치를 빨리 찾고, 둘째 그 데이터를 최신 위치로 옮기거나 가장 오래된 tail을 제거해야 한다.

HashMap만으로는 순서를 모른다. LinkedList만으로는 key를 찾는 데 O(N)이 걸린다. 둘을 결합해야 한다.

## 초보자용 비유

HashMap은 도서관 색인 카드이고, DoublyLinkedList는 실제 대기 줄이다. 색인 카드가 줄에 선 사람의 손을 직접 가리키므로, 사람을 찾고 줄 앞으로 보내는 두 작업이 모두 빠르다.

## 실제 코드 흐름

MiniRedis.set()에서 새 LRU Node(key, value)를 만들어 lru_list.insert_front()한다. 그 다음 store.put(key, new_node)로 key에서 그 Node를 찾을 수 있게 한다.

MiniRedis.get()은 store.get(key)로 Node를 받은 뒤 lru_list.move_to_front(node)를 호출한다. HashMap 조회와 리스트 포인터 조작이 각각 평균 O(1)이므로 GET의 핵심 LRU 갱신도 평균 O(1)이다.

## GET 성공의 순서

    GET key
      ↓
    _cleanup_expired()
      ↓
    store.get(key)
      ├─ None → (nil), LRU 이동 없음
      └─ Node → move_to_front(Node) → value 반환

만료로 삭제된 키는 store.get에 도달했을 때 없어야 하므로 LRU를 갱신하지 않는다. 이것이 “없는 키를 읽었다고 최신 데이터로 만들지 않는다”는 의미다.

## eviction 전체 흐름

    SET new_key new_value
      ↓ used_memory += payload
    used_memory > maxmemory?
      ↓ yes
    lru_list.remove_back()
      ↓ key/value 확보
    store.remove(key)
    ttl_map.remove(key)
    used_memory -= old payload
    evicted_keys += 1
      ↓
    used_memory <= maxmemory까지 반복

## 정상·실패·경계 사례

- GET 성공은 MRU로 이동한다.
- SET도 새 값이므로 MRU로 들어간다.
- 새 entry 자체가 maxmemory보다 크면 저장하지 않고 OOM을 발생시킨다.
- 기존 key를 덮어쓸 때는 기존 Node를 리스트에서 먼저 제거한다.
- LRU가 없는 상태에서 _evict_lru가 호출되면 조용히 반환한다. 일반적인 초과 상태에서는 store가 비어 있지 않으므로 이 경로는 방어 코드다.

## 복잡도

HashMap 평균 조회 O(1) + DLL 이동 O(1) = 평균 O(1)이다. eviction 한 건도 tail 제거와 두 HashMap 제거가 평균 O(1)이다. 여러 건을 연속 제거하면 제거 건수 K에 비례한다.

## 관련 테스트

tests/test_mini_redis.py::test_mini_redis_lru_eviction은 k1·k2를 넣고 k1을 읽어 순서를 뒤집은 뒤 k3로 초과시켜 k2가 사라지는지 확인한다.

## 손으로 추적하는 연습

다음 순서를 적고 매 단계의 head→tail을 써라.

    SET A 1
    SET B 2
    GET A
    SET C 3

세 키가 같은 payload이고 한도 때문에 하나를 제거해야 한다면 A가 MRU, C가 새 MRU, B가 LRU다.

## 동료에게 설명하는 한 문장

> HashMap은 key에서 노드까지 순간 이동시키고, 이중 연결 리스트는 그 노드를 순서상 앞으로 옮기므로 LRU를 평균 O(1)에 유지한다.

## 피어리뷰 질문과 방어 포인트

질문: 리스트만 순회해서 tail을 찾으면 안 되나요?

방어: tail sentinel이 이미 tail 직전 노드를 가리키므로 tail 찾기는 O(1)이다. 문제는 GET 때 임의 key의 노드를 찾아 이동하는 일인데, 그 부분을 HashMap이 해결한다.

## 단계 완료 기준

- HashMap과 DLL 각각의 역할을 섞지 않고 설명한다.
- GET의 TTL 확인→조회→이동 조건을 순서대로 말한다.
- eviction에서 used_memory와 evicted_keys가 왜 함께 갱신되는지 안다.

---

# 9단계. TTL, lazy deletion, stale heap entry

## 왜 필요한가

만료 시각을 저장하는 것과 만료된 키를 제거하는 것은 다른 문제다. 이 구현은 타이머 스레드로 모든 키를 즉시 지우지 않고, 명령이 들어올 때 가장 빠른 만료 후보부터 청소한다.

## 초보자용 비유

가게가 매초 모든 상품의 유통기한을 검사하지 않고, 손님이 들어올 때 유통기한 임박 선반부터 확인하는 방식이다. 다만 유통기한을 연장한 상품의 예전 알림표가 게시판에 남을 수 있으므로 최신 장부와 대조한다.

## 선수 개념

- Unix timestamp
- priority queue
- lazy deletion
- stale entry
- 현재 시각과 남은 시간

## EXPIRE 흐름

    EXPIRE key seconds
      ↓ cleanup
    store에 key 없음 → (integer) 0
    seconds <= 0 → _raw_delete(key), (integer) 1
    정상 seconds
      expire_at = time.time() + seconds
      ttl_map.put(key, expire_at)
      ttl_heap.push(expire_at, key)
      → (integer) 1

## TTL 흐름

    TTL key
      ↓ cleanup
    key 없음 → -2
    ttl_map에 없음 → -1
    있음 → int(expire_at - time.time()), 최소 0

## TTL 갱신과 stale entry

EXPIRE a 10 후 EXPIRE a 100을 호출하면 heap에는 (t+10,a)와 (t+100,a)가 모두 있을 수 있다. ttl_map[a]는 두 번째 값이다. 10초 항목이 root로 나와도 현재 TTL이 100초라면 _cleanup_expired()는 _raw_delete하지 않고 그 heap 항목만 버린다.

    heap:   (t+10, a) → (t+100, a)
    map:    a → t+100
    시간 t+10
      old heap entry pop
      current_ttl == t+100, now보다 미래
      → 삭제하지 않음

반대로 LRU eviction이나 DEL로 ttl_map 자체가 없어졌다면 stale heap entry는 current_ttl is None이 되어 무시된다.

## _cleanup_expired() 현미경

1. now = time.time()을 한 번 읽는다.
2. heap이 빌 때까지 peek()한다.
3. root의 expire_at > now면 뒤 항목도 더 늦으므로 즉시 중단한다.
4. 만료 root를 pop()한다.
5. ttl_map.get(key)로 최신 만료 시각을 얻는다.
6. 최신 값이 존재하고 현재 시각보다 과거이면 _raw_delete(key)한다.

## 정상·실패·경계 사례

- 없는 key에 EXPIRE: 0
- seconds <= 0: 존재하면 즉시 삭제 후 1
- TTL 없는 key: -1
- 만료된 key: cleanup 후 -2
- TTL이 1초여도 실제 반환은 int 내림이므로 0이 먼저 나올 수 있다.
- 별도 백그라운드 타이머가 없으므로 명령이 전혀 없으면 메모리에서 즉시 제거되지 않는다.

## 복잡도

EXPIRE는 HashMap put O(1) + Heap push O(log N)이다. TTL 조회는 cleanup이 없다면 O(1)이지만, 실제 ttl()은 먼저 cleanup을 하므로 만료된 K개가 있으면 O(K log N)까지 걸릴 수 있다.

## 관련 테스트

tests/test_mini_redis.py::test_mini_redis_ttl_expiration은 1초 TTL을 설정하고 1.1초 대기한 뒤 GET이 (nil), TTL이 -2인지 확인한다.

## 손으로 추적하는 연습

a에 TTL 5를 주고 즉시 TTL 100으로 갱신한 다음 t+5에 cleanup을 실행한다고 가정하라. heap root와 ttl_map을 각각 적고, 왜 a가 삭제되지 않는지 설명하라.

## 동료에게 설명하는 한 문장

> MinHeap은 가장 빠른 만료 후보를 고르고, ttl_map은 그 후보가 아직 최신 약속인지 확인해 stale entry 오삭제를 막는다.

## 피어리뷰 질문과 방어 포인트

질문: 왜 TTL을 갱신할 때 heap의 예전 항목을 바로 찾아 지우지 않나요?

방어: 임의 항목 삭제를 지원하는 비용과 구현 복잡도를 피하고, 최신 map 비교로 무효 항목을 늦게 버리는 lazy deletion을 택했다. 대신 heap이 일시적으로 커질 수 있다.

## 단계 완료 기준

- EXPIRE/TTL의 -2, -1, 0 이상 의미를 구분한다.
- stale heap entry가 왜 생기고 어떻게 무시되는지 설명한다.
- “만료 즉시 삭제”와 “다음 명령에서 관측되는 lazy 삭제”를 구분한다.

---

# 10단계. 메모리 제한과 명령 의미론

## 왜 필요한가

LRU는 자료구조 문제가 아니라 정책 문제다. 값을 저장하는 순간 payload 메모리를 계산하고, 한도를 넘으면 오래된 순서대로 제거해야 한다. 기존 키 덮어쓰기, 단일 entry OOM, CONFIG 축소까지 함께 봐야 한다.

## 초보자용 비유

10kg만 실을 수 있는 트럭에 화물을 싣는 상황이다. 새 화물이 너무 무거우면 애초에 싣지 못하고, 기존 화물과 합쳐 한도를 넘으면 가장 오래 방치된 화물부터 내린다.

## 실제 파일과 함수

- MiniRedis._calc_memory
- MiniRedis.set
- MiniRedis._evict_lru
- MiniRedis.config_set_maxmemory
- MiniRedis.info_memory
- MiniRedis._raw_delete

## SET의 세 구간

    1. 정제
       refined_key = key.strip()
       refined_val = str(value)
       mem_cost 계산

    2. 검증
       _cleanup_expired()
       mem_cost > maxmemory면 MemoryError

    3. 실행
       기존 key면 old memory 반환, old LRU 제거, TTL 삭제
       새 LRU Node를 head에 삽입
       store.put(key, new_node)
       used_memory += mem_cost
       초과하는 동안 tail eviction 반복
       새 key가 살아 있지 않으면 OOM

## 기존 키 덮어쓰기

SET a old 후 EXPIRE a 100, 다시 SET a new를 하면 old Node가 LRU에서 빠지고 old payload만큼 used_memory가 먼저 감소한다. ttl_map.remove(a)로 TTL도 초기화한다. 예전 heap tuple은 stale entry가 되어 훗날 map 부재로 무시된다.

## 단일 entry OOM

maxmemory=10, SET long very-long-value의 key+value payload가 10보다 크면 기존 LRU를 아무리 제거해도 새 entry 자체가 들어갈 수 없다. 현재 구현은 저장 전에 MemoryError를 발생시킨다.

## CONFIG와 INFO

config_set_maxmemory(bytes_limit)은 음수를 거부하고, limit을 설정한 뒤 cleanup과 LRU 반복 제거를 실행한다. 0은 무제한이다.

info_memory()는 다음 세 줄을 반환한다.

    used_memory:<number>
    maxmemory:<number>
    evicted_keys:<number>

주의할 실제 구현 포인트: info_memory() 자체는 _cleanup_expired()를 호출하지 않는다. 따라서 TTL이 지났지만 아직 다른 명령이 cleanup을 촉발하지 않았다면, INFO 직전 수치가 lazy cleanup 전 상태일 수 있다. 이것은 코드 리뷰에서 반드시 확인할 경계다.

## DEL·DBSIZE·KEYS·EXISTS

- delete()는 _raw_delete()로 store·LRU·ttl_map·memory를 정리한다.
- dbsize()는 cleanup 후 store.size()를 반환한다.
- keys()는 cleanup 후 HashMap 전체 키를 순회한다.
- exists()는 cleanup 후 store.contains()를 확인한다.

주의할 실제 구현 포인트: 현재 delete()는 직접 _cleanup_expired()를 호출하지 않고 _raw_delete()로 들어간다. 엄격한 미션 문장처럼 모든 key 명령 전에 만료를 보려면 cleanup이 필요하므로, 만료된 키에 대한 DEL의 의미는 보강 테스트 또는 코드 리뷰 대상이다. 이 가이드는 구현이 이미 완벽하다고 숨기지 않는다.

## 복잡도

SET은 평균 O(1) + 필요 시 rehash O(N) + eviction K건이다. config_set_maxmemory 축소도 현재 초과 키 수만큼 eviction한다. INFO는 O(1), DBSIZE는 HashMap size O(1)이나 사전 cleanup이 만료 K개를 처리할 수 있다. KEYS는 O(N)이다.

## 관련 테스트

test_mini_redis_lru_eviction은 used memory를 직접 assert하지는 않지만 LRU 생존·제거 결과를 검증한다. test_mini_redis_basic_set_get_del은 DEL 결과 형식을 검증한다. INFO, CONFIG 축소, 단일 OOM, 다국어 UTF-8은 현재 통합 테스트에서 직접 충분히 고정되어 있지 않으므로 손으로 실행할 범위다.

## 손으로 추적하는 연습

maxmemory=10에서 다음을 계산하라.

    SET k1 v1  → 4
    SET k2 v2  → 8
    GET k1     → 순서 k1, k2
    SET k3 v3  → 12, k2 제거, used_memory 8

SET k1 huge의 overwrite OOM도 별도로 생각하라. 새 entry 자체가 limit을 넘으면 기존 k1을 지우고 시도하는 것이 아니라 사전 검증에서 실패한다.

## 동료에게 설명하는 한 문장

> 메모리 정책은 payload를 UTF-8 바이트로 계산하고, 새 entry 자체의 OOM은 거부하며, 합계 초과는 LRU tail을 반복 제거해 해결한다.

## 피어리뷰 질문과 방어 포인트

질문: 실제 Python 프로세스 메모리와 used_memory가 왜 다르죠?

방어: 미션 공식이 key/value UTF-8 payload만 세고 노드·포인터·버킷 오버헤드는 제외한다. 채점 결정론을 위해 의도적으로 단순화한 모델이다.

## 단계 완료 기준

- SET 신규·overwrite·OOM 세 흐름을 구분한다.
- eviction과 expiration이 evicted_keys를 다르게 다룬다는 점을 안다.
- INFO의 lazy cleanup 한계와 DEL의 실제 cleanup 누락 가능성을 말할 수 있다.

---

# 11단계. CLI와 오류 처리

## 왜 필요한가

코어가 올바른 값을 내도 CLI가 인자 수, 따옴표, 정수 변환, 오류 포맷을 잘못 처리하면 사용자는 Redis처럼 사용할 수 없다. 파싱 오류와 도메인 오류의 책임을 구분해야 한다.

## 초보자용 비유

식당 주문서 접수 창구다. 창구는 주문 문장을 읽어 주방에 전달하고, 주문서 형식이 잘못되면 손님에게 표준 문구로 다시 요청한다. 재료 저장과 조리 정책은 주방(MiniRedis)의 일이다.

## 실제 파일과 함수

mini_redis/cli.py의 print_error, handle_command, main, 그리고 constants.py의 RedisCommands, RedisResponses, ErrorMessages를 읽는다.

## 표준 출력 분류

| 상황 | 예시 |
| --- | --- |
| 성공 문자열 | OK |
| 값 없음 | (nil) |
| 정수 | (integer) 1 |
| 알 수 없는 명령 | (error) ERR unknown command 'HELLO' |
| 인자 수 오류 | (error) ERR wrong number of arguments for 'GET' command |
| 정수 오류 | (error) ERR value is not an integer or out of range |
| OOM | (error) OOM command not allowed when used memory > 'maxmemory' |

## 코드 현미경

handle_command()는 빈 줄을 무시하고 shlex.split을 실행한다. command token은 대문자로 정규화하지만 key/value는 그대로 둔다. 각 명령 branch는 먼저 인자 수를 확인한 후 코어 메서드를 호출한다.

EXPIRE, CONFIG의 정수 변환은 branch 안에서 try/except ValueError로 처리한다. shlex.split의 unbalanced quote도 ValueError이므로 바깥 catch에서 syntax error를 출력한다. MemoryError는 별도 catch에서 메시지를 감싸 출력한다.

## 정상·실패·경계 사례

- GET "my key"는 key 자체에 공백이 있어도 하나의 인자로 파싱된다.
- CONFIG SET maxmemory abc는 int 변환 실패다.
- CONFIG SET maxmemory -1은 int 변환은 성공하지만 core가 음수를 거부한다.
- INFO memory extra는 malformed INFO 오류다.
- KEYS pattern은 현재 요구하지 않는 패턴 인자로 wrong arguments가 된다.
- GET은 wrong arguments이고, HELLO는 unknown command다.

## 복잡도

파싱은 입력 길이에 비례한다. 명령 분기와 상수 조회는 O(1)이고, 나머지는 core 비용이다.

## 관련 테스트

현재 tests/test_mini_redis.py는 unbalanced quote를 직접 검증한다. 나머지 표준 응답은 코어 테스트와 미션 예시를 결합해 수동으로 확인해야 한다.

## 손으로 추적하는 연습

다음 입력의 args, branch, 예외, 최종 출력 줄을 각각 적어라.

    SET note "hello world"
    GET
    EXPIRE note ten
    CONFIG SET maxmemory abc
    PING

PING은 RedisCommands에 있지만 현재 handle_command에 별도 branch가 없으므로 unknown command가 된다. 상수에 존재한다고 기능이 구현된 것은 아니다.

## 동료에게 설명하는 한 문장

> CLI는 입력을 안전하게 토큰화하고 형식 오류를 표준 응답으로 바꾸지만, 데이터 정책과 상태 변경은 코어에 위임한다.

## 피어리뷰 질문과 방어 포인트

질문: except Exception은 너무 넓지 않나요?

방어: 현재 코드에는 마지막에 내부 오류를 표시하는 포괄 catch가 있다. 운영 코드라면 예상 가능한 예외를 더 구체화하는 개선점이며, 학습자는 이 사실을 숨기지 말아야 한다.

## 단계 완료 기준

- 따옴표 값이 shlex.split에서 어떻게 보존되는지 설명한다.
- unknown command, wrong arguments, integer error, OOM을 구분한다.
- 상수 선언과 실제 branch 구현의 차이를 확인한다.

---

# 12단계. 테스트·복잡도·피어리뷰 방어

## 왜 필요한가

구현을 읽었다고 이해가 완성되는 것은 아니다. 테스트는 상태 전이의 증거이고, 피어리뷰 방어는 “왜 이 자료구조인가”를 다시 말하게 하는 검증이다.

## 초보자용 비유

자동차를 만들었다면 엔진을 한 번 켜 보는 것으로 끝나지 않는다. 부품 단위 시험, 실제 주행, 고장 상황, 정비사 질문까지 모두 통과해야 한다.

## 테스트 파일별 역할

### tests/test_custom_ds.py

- test_dynamic_array: capacity와 resize
- test_doubly_linked_list: sentinel, add_front, move_to_front, remove_back
- test_hash_map: put/get/remove/contains와 None value
- test_min_heap: heap order, peek/pop, size

### tests/test_mini_redis.py

- test_mini_redis_basic_set_get_del: String CRUD와 응답
- test_mini_redis_lru_eviction: GET으로 MRU를 바꾼 뒤 eviction
- test_mini_redis_ttl_expiration: 시간 경과와 lazy deletion
- test_cli_unbalanced_quotes: CLI 파싱 오류 격리

## 테스트가 증명하는 것과 증명하지 않는 것

현재 테스트는 핵심 골격을 증명하지만 모든 미션 문장을 고정하지는 않는다.

직접 보강해 손으로 확인할 항목:

- EXISTS, DBSIZE, KEYS
- INFO memory의 세 필드
- UTF-8 한글 key/value 메모리 계산
- 단일 entry OOM
- 기존 key overwrite 시 TTL 초기화
- TTL 갱신 stale heap
- CONFIG SET maxmemory 축소
- HashMap의 실제 충돌과 rehash
- CLI의 각 오류 표준

## 전체 복잡도 표

| 기능 | 평균/일반 | 최악 또는 조건부 |
| --- | --- | --- |
| HashMap get/put/remove | O(1) | O(K), rehash 시 O(N) |
| DLL 삽입/삭제/이동 | O(1) | O(1) |
| MinHeap peek | O(1) | O(1) |
| MinHeap push/pop | O(log N) | O(log N) |
| GET | 평균 O(1) | cleanup K개 시 O(K log N) |
| SET | 평균 O(1) | rehash + eviction K개 |
| DEL | 평균 O(1) | 현재 구현의 stale TTL 상태에 따라 후속 cleanup 비용 |
| EXPIRE | O(log N) | heap 크기 기준 |
| TTL | 보통 O(1) | cleanup K개 시 O(K log N) |
| KEYS | O(N) | 항상 전체 순회 |

## 30초 설명 연습

> Mini Redis는 key를 HashMap으로 찾고, 같은 key의 LRU Node를 이중 연결 리스트로 관리한다. GET/SET 성공은 Node를 head로 옮기고, 메모리가 한도를 넘으면 tail을 제거한다. TTL은 만료 시각을 MinHeap에 넣고 ttl_map으로 갱신 여부를 검증한다.

## 3분 설명 연습

1. CLI가 shlex.split으로 입력을 토큰화한다.
2. 코어가 명령 전에 lazy expiration을 수행한다.
3. store에서 key→LRU Node를 찾는다.
4. 새 값은 head, 오래된 값은 tail에 위치한다.
5. payload UTF-8 바이트 합으로 메모리를 계산한다.
6. 초과 시 tail eviction을 반복한다.
7. TTL heap은 후보 순서를, ttl_map은 최신성을 책임진다.

## 10분 설명 연습

위 설명에 더해 DynamicArray의 resize, HashMap의 polynomial rolling hash와 chaining, MinHeap의 배열 공식, overwrite TTL 초기화, stale heap 처리, 명세-구현 차이(>=, DEL/INFO cleanup)를 코드 위치와 함께 말한다.

## BST와 Pub/Sub의 핵심·보너스 구분

bst.py와 pub_sub.py는 실제 레포에 있지만 미션의 핵심 평가 축은 String 명령어, LRU, TTL, 메모리, CLI다. BST는 정렬·범위 조회로 확장될 때 유용한 보너스이고, Pub/Sub는 HashMap[channel → DoublyLinkedList queue]로 메시지 FIFO를 연습하는 보너스다. 핵심 엔진의 store, lru_list, ttl_map, ttl_heap 설명에 이들을 섞어 “반드시 필요한 구조”라고 말하면 안 된다.

## 관련 테스트

먼저 tests/test_custom_ds.py와 tests/test_mini_redis.py를 각각 실행하고, 이후 CLI 수동 시나리오를 실행한다.

## 손으로 추적하는 종합 연습

다음 명령을 실행하기 전에 모든 구조의 상태를 예측하라.

    CONFIG SET maxmemory 12
    SET a 1
    SET b 2
    EXPIRE a 1
    GET b
    SET c 3
    TTL a
    DEL b
    INFO memory
    KEYS
    DBSIZE
    EXISTS a

a, b, c의 payload는 각각 2바이트다. GET b가 b를 MRU로 만들고, SET c가 들어와도 6바이트이므로 eviction은 없다. 1초가 지나 cleanup이 실행되면 a가 사라지고, DEL b 이후에는 c만 남는다. 실제 시계 경계는 sleep 시점에 따라 달라질 수 있으므로 테스트에서는 충분한 여유를 둔다.

## 동료에게 설명하는 한 문장

> 좋은 방어는 테스트가 통과했다는 말이 아니라, 각 테스트가 어느 불변식을 증명하고 어떤 빈틈은 아직 남기는지 말하는 것이다.

## 피어리뷰 공격 질문과 방어 포인트

질문: 이 테스트만으로 모든 명세를 만족한다고 할 수 있나요?

방어: 아니다. 현재 테스트는 핵심 happy path와 한 가지 LRU/TTL/CLI 오류를 고정한다. INFO·OOM·overwrite TTL·실제 collision·rehash 등은 추가 검증 범위로 명시해야 한다.

## 단계 완료 기준

- 각 테스트가 어느 함수와 불변식을 겨냥하는지 설명한다.
- 30초·3분·10분 설명을 모두 할 수 있다.
- 핵심과 보너스, 구현 사실과 개선 제안을 분리한다.

---

# 부록 A. 필수 시나리오를 한 번에 추적하기

## A-1. SET

    입력: SET user:1 "Alice"
    args: [SET, user:1, Alice]
    mem = len(6 UTF-8 bytes) + len(5 UTF-8 bytes) = 11
    cleanup
    single-entry OOM 검사
    새 LRU Node 생성 → lru head
    store.put(user:1 → Node)
    used_memory += 11
    초과하면 tail eviction
    출력: OK

## A-2. GET 성공과 LRU head 이동

    store.get(key) → Node
    lru_list.move_to_front(Node)
    Node.value 반환

없는 key나 cleanup으로 만료된 key는 (nil)이며 move_to_front를 하지 않는다.

## A-3. 메모리 초과와 tail eviction

    새 entry를 먼저 저장
    used_memory > maxmemory
    tail.prev를 remove_back
      ↓ key/value 확보
    store와 ttl_map에서 같은 key 제거
    payload만큼 used_memory 감소
    evicted_keys 증가
    한도 이하가 될 때까지 반복

단일 entry가 한도보다 큰 경우에는 기존 LRU를 쫓아내는 경로가 아니라 사전 OOM이다.

## A-4. 기존 키 덮어쓰기와 TTL 초기화

    old_node = store.get(key)
    used_memory -= old payload
    lru_list.remove_node(old_node)
    ttl_map.remove(key)
    새 Node를 head에 삽입
    store.put(key, 새 Node)
    used_memory += new payload

old heap tuple은 남아도 현재 map이 없거나 새 TTL과 다르므로 삭제를 일으키지 않는다.

## A-5. EXPIRE와 TTL

EXPIRE key seconds는 ttl_map과 ttl_heap에 같은 expire_at을 기록한다. TTL은 cleanup 뒤 map을 읽어 -2/-1/남은 초를 결정한다.

## A-6. TTL 재설정과 stale heap entry

    첫 expire: heap[(t1,key)], map[key]=t1
    두 번째 expire: heap[(t1,key),(t2,key)], map[key]=t2
    cleanup at t1:
      pop t1
      map[key]=t2 > now
      key 보존

## A-7. _cleanup_expired()

루트가 아직 미래이면 중단한다. 루트가 과거이면 pop하고 최신 map을 확인한다. 이 때문에 힙의 나머지를 매번 전수 검사하지 않는다.

## A-8. DEL의 세 구조 동시 정리

정상 key의 delete()는 _raw_delete()를 통해 LRU Node, store mapping, ttl_map, used_memory를 정리한다. TTL heap의 과거 entry는 직접 제거하지 않고 stale로 남긴다. 단, 현재 delete()가 명령 시작 전에 _cleanup_expired()를 호출하지 않는다는 구현상 주의점을 함께 기억한다.

## A-9. 단일 엔트리 OOM

    mem_cost > maxmemory
      → MemoryError(ErrorMessages.ERR_MEMORY_LIMIT)
      → CLI가 (error)로 출력
      → 새 key는 store/LRU에 들어가지 않음

## A-10. HashMap 충돌

두 key의 hash % capacity가 같으면 같은 bucket의 chain을 순회한다. 실제 key를 비교하므로 value가 덮어써지지 않는다.

## A-11. HashMap rehash

현재 put()은 size / capacity >= 0.75이면 먼저 _resize()한다. 새 DynamicArray와 새 체인을 만들고 old chain 전체를 새 capacity로 재삽입한다.

## A-12. 따옴표가 있는 CLI 값

shlex.split이 "Alice Kim"을 하나의 값으로 만든다. 코어는 따옴표를 보지 못하고 순수 값만 받으며, GET 출력에만 CLI가 따옴표를 입힌다.

## A-13. CONFIG

CONFIG SET maxmemory bytes만 허용한다. bytes는 CLI에서 int로 변환하고 core에서 음수를 거부한다. limit을 줄였는데 현재 사용량이 크면 즉시 LRU를 제거한다.

## A-14. INFO

세 필드 used_memory, maxmemory, evicted_keys를 줄바꿈으로 반환한다. INFO 자체의 cleanup 미호출은 현재 코드의 관찰 포인트다.

## A-15. KEYS, DBSIZE, EXISTS

세 명령 모두 core에서 cleanup 후 실행한다. KEYS는 전체 키를 리스트로 만들어 CLI가 번호와 따옴표를 출력하고, DBSIZE는 HashMap의 size, EXISTS는 contains 결과를 Redis integer로 변환한다.

## A-16. Pub/Sub과 BST

Pub/Sub은 PubSub._channels라는 HashMap과 채널별 DoublyLinkedList 메시지 큐를 사용한다. publish는 back 삽입, poll은 front 제거로 FIFO를 만든다. BST는 bst.py의 보너스 자료구조로 핵심 Redis String 저장 경로에는 참여하지 않는다.

---

# 부록 B. 평가 항목별 최종 방어 답안

아래는 학습 가이드의 마지막에 붙이는 구술 평가 대비 섹션이다. “동작한다”고만 말하지 말고 실제 함수, 상태 변화, 경계 조건을 함께 말한다.

## 항목 1. 기능·출력·정책

### String 타입 기본 동작

SET, GET, DEL, EXISTS, DBSIZE, KEYS는 MiniRedis의 각각 set, get, delete, exists, dbsize, keys와 cli.py의 branch가 담당한다.

- SET: 새 LRU Node를 head에 넣고 store에 연결한 뒤 OK를 반환한다.
- GET: cleanup 후 store에서 Node를 찾고, 성공할 때만 LRU head로 이동한다. 없으면 (nil)이다.
- DEL: _raw_delete로 Node, store, TTL map, payload 메모리를 정리하고 1 또는 0을 반환한다.
- EXISTS: cleanup 후 store.contains 결과를 (integer) 1/0으로 반환한다.
- DBSIZE: cleanup 후 HashMap size를 반환한다.
- KEYS: cleanup 후 모든 bucket을 순회해 key 목록을 출력한다. 패턴 매칭은 구현하지 않는다.

검증 답변은 “기본 테스트가 SET/GET/DEL을 고정하고, EXISTS/DBSIZE/KEYS는 현재 코드와 수동 시나리오로 확인하며, key 명령의 공통 만료 규칙은 delete()가 별도 cleanup을 호출하지 않는다는 실제 차이까지 점검한다”가 정확하다.

### LRU 자동 제거

CONFIG SET maxmemory N은 maxmemory를 설정한다. 이후 SET이 payload를 더해 used_memory > maxmemory가 되면 lru_list.remove_back()으로 tail의 LRU Node를 떼고, store.remove, ttl_map.remove, used_memory 감소, evicted_keys 증가를 실행한다. 한도 이하가 될 때까지 반복한다. GET과 SET 성공은 head 이동 또는 head 삽입으로 최근성을 갱신한다.

### 메모리 정보

INFO memory는 최소한 다음을 출력한다.

    used_memory:<payload UTF-8 byte sum>
    maxmemory:<configured limit, 0 means unlimited>
    evicted_keys:<LRU eviction count>

만료 삭제는 evicted_keys를 증가시키지 않는다. 현재 구현은 info_memory() 내부에서 cleanup하지 않으므로, 평가 시 INFO 직전 다른 명령을 한 번 실행했는지 또는 이 경계를 별도 테스트했는지 명확히 한다.

### TTL 관리

EXPIRE는 존재하지 않는 key에 0, 0 이하 seconds에는 즉시 삭제 후 1, 정상 값에는 ttl_map 기록과 ttl_heap.push 후 1을 반환한다. TTL은 없는 key -2, TTL 없는 살아 있는 key -1, 만료 시각이 있으면 남은 정수를 반환한다. 만료된 key는 cleanup에서 store/LRU/map/memory가 제거되어 없는 key처럼 보인다.

### 에러 처리

- unknown command: ERR_UNKNOWN_COMMAND와 원래 command
- wrong number: 명령별 인자 수 branch
- integer: int() 실패를 ERR_VALUE_NOT_INT
- OOM: core의 MemoryError를 CLI가 (error)로 포장
- unbalanced quotes: shlex.split의 ValueError를 syntax error

“모든 오류가 완벽히 같은 Redis 구현과 같다”고 과장하지 말고, CONFIG/INFO malformed branch의 메시지와 마지막 except Exception이 실제 코드의 확장 포인트임을 지적한다.

## 항목 2. 기본 자료구조 구현

### 이중 연결 리스트 노드와 O(1)

실제 Node는 미션의 data 하나 대신 key, value, prev, next를 가진다. head와 tail sentinel 사이에 실제 Node를 연결한다. insert_front와 insert_back은 주변 네 포인터를 설정하고, remove_node는 앞·뒤 Node를 직접 연결한 뒤 대상 포인터를 끊는다. move_to_front는 remove 후 insert이므로 모두 O(1)이다. 탐색을 포함하지 않는다는 전제가 중요하다.

### 직접 설계한 해시 함수

입력은 문자열 key다. 각 문자의 ord에 위치별 31의 거듭제곱을 곱하고 누적 mod 1_000_000_009를 취한다. 이후 해시값을 현재 capacity로 mod해 버킷 인덱스를 만든다. 순서 정보를 반영하므로 단순 문자 합보다 분포가 좋지만 충돌을 완전히 제거하지는 않는다.

### 체이닝

버킷 배열의 각 칸은 DoublyLinkedList다. 같은 bucket index가 나온 key는 해당 chain에 함께 들어가고, put/get/remove/contains가 원래 문자열 key를 비교해 정확한 대상을 찾는다. 버킷 내부 구조까지 직접 만든 DLL이므로 내장 dict로 충돌을 숨기지 않는다.

### 0.75 초과 시 2배 확장

의도는 load factor가 높아질 때 bucket을 두 배로 늘리는 것이다. 절차는 old bucket 보관 → capacity 두 배 → 빈 새 DynamicArray와 chain 생성 → 모든 old chain 원소를 새 capacity로 재해싱해 put하는 순서다. 다만 실제 코드의 조건은 “초과”가 아니라 >= 0.75다. 이 구현 사실은 평가 때 정확히 밝힌다.

## 항목 3. 통합 알고리즘

### LRU에서 HashMap과 DLL의 역할

HashMap은 key → LRU Node를 평균 O(1)에 찾는다. DLL은 그 Node의 순서를 head(MRU)부터 tail(LRU)까지 보존하고, Node를 이동·제거한다. HashMap만 있으면 최근성 순서가 없고, DLL만 있으면 key를 찾는 데 O(N)이므로 둘 다 필요하다.

### O(1) LRU 원리

조회: store.get(key)로 Node 참조를 얻는다. 갱신: lru_list.move_to_front(node)가 포인터 네 개 수준의 재연결을 한다. 두 단계가 평균 O(1)이다. HashMap 충돌이 심하면 worst case는 O(K)라는 단서도 함께 말한다.

### TTL에 힙을 쓰는 이유

ttl_map은 특정 key의 최신 만료 시각을 빠르게 찾지만, 가장 빨리 만료될 key를 알려면 전체를 비교해야 한다. MinHeap은 최소 expire_at을 root에 두므로 peek O(1), 만료 항목 제거 O(log N)이다.

### 메모리 초과 eviction

1. key/value의 UTF-8 payload를 계산한다.
2. used_memory에 새 payload를 더한다.
3. maxmemory가 0이 아니고 초과하면 tail LRU를 꺼낸다.
4. store와 ttl_map에서 제거한다.
5. 제거한 payload를 used_memory에서 뺀다.
6. evicted_keys를 1 증가시킨다.
7. 한도 이하가 될 때까지 반복한다.

entry 하나 자체가 maxmemory보다 크면 2번 전에 OOM이므로 다른 키를 희생하지 않는다.

### GET 전체 흐름

get(key)는 key를 strip하고 _cleanup_expired()를 호출한다. 이후 store.get(key)가 None이면 (nil)이다. Node가 있으면 move_to_front하고 값을 반환한다. 따라서 만료로 이미 삭제된 key는 LRU 갱신을 받지 않는다.

## 항목 4. 확장 설계와 트레이드오프

### LRU를 LFU로 바꾼다면

각 Node에 frequency를 추가하고 GET/SET 성공 때 증가시킨다. 단순한 HashMap + 하나의 DLL만으로는 “가장 적게 사용된 frequency”를 즉시 찾기 어렵다. 현재 레포의 DLL을 재사용해 frequency → DLL 버킷을 만들고, key → DataNode HashMap과 min_freq 변수를 유지하는 방식이 합리적이다.

접근 시 Node를 freq 버킷에서 제거해 freq+1 버킷의 head로 옮긴다. eviction은 min_freq 버킷의 tail에서 한다. 이렇게 하면 조회·빈도 증가·eviction을 평균 O(1)에 가깝게 만들 수 있지만, 빈 버킷 제거와 min_freq 갱신이라는 상태가 늘어난다. MinHeap에 (frequency, last_access, key)를 넣는 더 단순한 설계는 가능하지만 frequency 증가마다 O(log N) 비용을 낸다.

### 데이터 10만 건의 병목과 개선

현재 구조에서 병목 후보는 다음과 같다.

1. load factor마다 전체 rehash가 발생해 지연 spike가 생긴다.
2. 해시 충돌이 특정 bucket에 몰리면 chain 탐색이 O(K)로 퇴화한다.
3. TTL 갱신이 많으면 stale heap entry가 누적되어 heap이 실제 key 수보다 커질 수 있다.
4. KEYS는 전체 순회라 데이터가 커질수록 선형 시간이 든다.
5. Python 객체와 포인터의 메모리 오버헤드는 payload 모델에서 보이지 않는다.

개선안은 점진적으로 선택한다.

- 점진적 rehash로 한 번의 O(N) 정지 시간을 나눈다.
- 해시 분포를 측정하고 적절한 capacity/해시 함수를 선택한다.
- TTL 갱신 빈도가 높으면 indexed heap 또는 주기적 heap compaction을 도입한다.
- 전체 KEYS 대신 cursor 기반 scan을 제공한다.
- CPU 확장은 단일 프로세스만 키우기보다 key hash 기반 shard 여러 개로 분할한다.
- 다만 이 미션은 단일 스레드 CLI 학습용이므로, 개선안을 현재 코드에 무단 구현하지 않고 별도 설계로 분리한다.

### 자료구조 오버헤드를 used_memory에 포함한다면

현재 공식은 payload-only라서 동일한 key/value 입력은 환경과 무관하게 같은 값이다. 오버헤드를 포함하면 Node 객체, prev/next 참조, store chain Node, bucket 배열의 빈 슬롯, DynamicArray capacity, ttl_map entry, ttl_heap tuple까지 계산해야 한다. 그러면 maxmemory에 도달하는 시점이 빨라지고 LRU eviction 결과가 Python 버전·객체 구현·capacity에 민감해진다.

공정한 비교를 위해서는 다음이 필요하다.

- payload와 metadata를 별도 필드로 공개한다.
- 어떤 객체와 capacity를 세는지 명세한다.
- sys.getsizeof의 얕은 크기인지 참조가 가리키는 객체를 재귀적으로 세는지 고정한다.
- Python 버전, allocator, 문자열 intern 여부를 통제하거나 채점에서 제외한다.
- 기존 payload-only 테스트와 새 overhead-aware 테스트를 분리한다.
- 정답 판정은 가능하면 논리 payload 모델로 유지하고, overhead 모델은 관측·성능 평가로 사용한다.

예시 모델은 다음처럼 분리하는 편이 낫다.

    payload_memory = Σ key/value UTF-8 bytes
    metadata_memory = node + pointer + bucket slots + TTL index entries
    reported_memory = payload_memory + metadata_memory

alpha, beta, gamma 같은 경험 계수 하나로 보정하면 설명은 쉽지만 데이터 분포와 Python 런타임에 따라 오차가 커진다. 채점 기준으로 쓸 때는 계수보다 구성요소별 고정 모델과 교정 fixture가 낫다.

---

# 부록 C. 최종 자가 점검표

## 코드 읽기

- [ ] __main__.py → cli.main → handle_command → MiniRedis 흐름을 그렸다.
- [ ] store의 값이 LRU Node 참조라는 점을 확인했다.
- [ ] HashMap chain Node와 LRU Node를 구분했다.
- [ ] DynamicArray가 HashMap bucket과 MinHeap storage에 간접 사용됨을 확인했다.
- [ ] MinHeap tuple 비교가 (expire_at, key) 순서임을 확인했다.

## 상태 전이

- [ ] SET 신규에서 store/LRU/memory가 함께 변한다.
- [ ] SET overwrite에서 old memory와 TTL이 반환된다.
- [ ] GET 성공에서만 LRU head 이동이 일어난다.
- [ ] DEL과 expiration이 evicted_keys를 증가시키지 않는다는 점을 구분한다.
- [ ] TTL 갱신 stale entry가 map 비교로 무효화된다.
- [ ] LRU eviction이 tail에서 시작한다.

## 명세-구현 경계

- [ ] HashMap load factor 조건은 실제로 >= 0.75임을 기록했다.
- [ ] delete()가 _cleanup_expired()를 직접 호출하지 않음을 기록했다.
- [ ] info_memory()가 cleanup을 직접 호출하지 않음을 기록했다.
- [ ] PING 상수는 있지만 CLI branch는 없음을 확인했다.
- [ ] Pub/Sub과 BST를 핵심 범위가 아닌 보너스로 분류했다.

## 구술 방어

- [ ] 30초 설명을 할 수 있다.
- [ ] “왜 HashMap + DLL인가?”에 O(1) 조회와 O(1) 이동으로 답한다.
- [ ] “왜 TTL에 heap인가?”에 earliest expiration root로 답한다.
- [ ] “10만 건에서 어디가 느려지는가?”에 rehash·collision·stale heap·KEYS를 말한다.
- [ ] “오버헤드를 포함하면?”에 결정론적 채점과 런타임 의존성의 충돌을 말한다.

이 체크리스트까지 통과하면 코드를 단순히 실행한 상태가 아니라, 자료구조 선택·상태 불변식·실제 구현의 한계까지 방어할 수 있는 상태다.
