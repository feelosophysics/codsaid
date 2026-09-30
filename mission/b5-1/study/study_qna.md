# Mini Redis 학습 Q&A 노트

---

## Q1. `maxmemory 0` (무제한) 설정 시 물리 메모리 초과 및 OS 동작 원리

### ❓ 질문
`config set maxmemory 0`으로 설정하면 메모리 제한을 무제한으로 간주하는데, 실제 iMac 물리 메모리 용량보다 많은 데이터를 저장하면 어떻게 되는가? Ubuntu의 OOM Killer가 동작하는가? 실질적으로 사용 가능한 메모리 한계는 어느 정도인가?

### 💡 핵심 요약
1. **`maxmemory 0`의 의미**: Mini Redis 애플리케이션 차원의 LRU Eviction(자동 제거) 및 소프트웨어 제한을 끌 뿐, 하드웨어 메모리가 무한해지는 것은 아닙니다.
2. **OS 레벨의 메모리 관리**:
   - **macOS (현재 iMac 환경)**: Linux의 OOM Killer 대신 **Memory Pressure Subsystem**이 작동합니다. 메모리가 부족해지면 먼저 메모리 압축(Memory Compression)과 스왑(Swap)을 사용하며, 이로 인해 급격한 성능 저하(Thrashing)가 발생합니다. 가상 메모리까지 고갈되면 OS가 Python 프로세스에 `SIGKILL`을 보내 강제 종료(`Killed: 9`)시킵니다.
   - **Linux (Ubuntu 환경)**: Kernel의 **OOM Killer (Out-Of-Memory Killer)**가 동작하여 메모리를 과다하게 사용하는 Python 프로세스에 `SIGKILL`을 보냅니다.
   - **Python 레벨**: OS가 메모리 할당(`malloc`)을 거부할 경우 Python 인터프리터에서 `MemoryError` 예외가 발생합니다.
3. **실질적 메모리 한계**:
   - `(물리 RAM + OS Swap 용량) - (OS 및 타 프로세스 사용량)`이 한계선입니다.
   - Python의 커스텀 객체(`Node`, 리스트, 해시맵 버킷 등) 자체 오버헤드(노드당 수십~수백 바이트) 때문에 저장하는 순수 데이터(Key/Value 문자열) 크기보다 훨씬 빠르게 메모리가 고갈됩니다.

---

## Q2. `EXPIRE` (TTL) 기능의 존재 이유와 LRU의 차이점

### ❓ 질문
`EXPIRE key seconds`는 데이터의 만료 시간을 설정하는 기능인데, 이미 오래된 데이터를 제거해주는 LRU 기능이 있음에도 TTL/EXPIRE 기능이 별도로 존재하는 이유와 실제 활용 상황은 무엇인가?

### 💡 핵심 요약
1. **목적과 기준의 차이**:
   - **`EXPIRE` (TTL)**: **비즈니스적 요구(절대적 시간)**에 의해 삭제. 자주 조회되더라도 설정된 시간이 지나면 무조건 무효화 처리되어 삭제되어야 하는 데이터 관리.
   - **`LRU Eviction`**: **메모리 용량 한도(상대적 사용 빈도)**에 의해 삭제. 메모리가 부족할 때 가장 안 쓰인(Cold) 데이터부터 삭제하여 공간 확보.
2. **대표적인 EXPIRE (TTL) 유즈케이스**:
   - **인증번호 (OTP)**: 3분 뒤 무조건 만료. (자주 조회된다고 삭제 안 되면 보안 사고)
   - **로그인 세션 / JWT 토큰**: 지정된 시간(예: 30분) 후 자동 만료.
   - **API Rate Limit 카운터**: 1분당 요청 횟수 제한 카운터.
   - **일일 쿠폰/이벤트 키**: 자정(24시간) 기준 자동 무효화.
3. **핵심 비교**:
   - LRU는 메모리가 넉넉하면 1년이 지나도 안 지워지지만, TTL은 메모리 여유와 상관없이 약속된 시간이 되면 정확히 삭제됩니다.

---

## Q3. JWT 토큰의 개념과 Redis의 실무 활용 진위 여부

### ❓ 질문
JWT 토큰이 무엇이며, 앞에서 언급된 인증번호/Rate Limit/이벤트 쿠폰 등의 예시가 실제로 Redis로 구현되는 표준 패턴인가? 아니면 단순히 든 예시인가?

### 💡 핵심 요약
1. **JWT (JSON Web Token)란?**:
   - 회원 인증 정보 등을 안전하게 전달하기 위해 `Header.Payload.Signature` 3가지 파트를 인코딩한 문자열 토큰.
   - 서버가 세션 상태를 저장하지 않는 무상태(Stateless) 방식이지만, **로그아웃 블랙리스트(Blacklist)**나 **Refresh Token 관리** 시 만료(TTL) 기능이 뛰어난 Redis를 필수적으로 조합하여 사용함.
2. **실무에서 Redis를 쓰는가? (100% 실무 표준)**:
   - **인증번호 (OTP)**: RDBMS는 배치 삭제 쿼리가 필요하여 무겁지만, Redis는 `EXPIRE` 설정 하나로 자동 삭제되므로 1순위 표준.
   - **API Rate Limit (요청 제한)**: 초당 수만 건의 카운트 연산(`INCR`)을 RDBMS로 처리하면 DB가 뻗음. In-Memory 단일 스레드 구조인 Redis가 필수적.
   - **선착순 쿠폰 / 분산 락**: 동시성 이슈와 초고속 I/O 처리를 위해 RDBMS 대신 Redis의 Atomic 연산을 사용.

---

## Q4. Redis 등장 역사(2009년)와 In-Memory 데이터 소실(Persistence) 대처법

### ❓ 질문
1. Redis는 몇 년도에 등장했는가? 등장 전에는 이 문제를 어떻게 대처했는가?
2. In-Memory DB인 Redis가 장애로 다운되면 데이터가 소실되는데, 실무에서 인증번호/Rate Limit/세션 등에 문제가 생기지 않는 이유는 무엇인가?

### 💡 핵심 요약
1. **Redis의 역사 (2009년 등장)**:
   - 살바토레 산필리포(antirez)가 이탈리아의 실시간 웹 로그 분석 서비스 성능 개선을 위해 2009년 최초 개발.
   - **등장 이전 (2009년 전)**: RDBMS 직접 조회, 단순 Key-Value 캐시인 **Memcached(2003년)**, 파일/공유메모리 세션 등을 사용함.
   - **Redis의 혁신**: 단순 Key-Value를 넘어 다양하고 강력한 **자료구조(List, Hash, Set, Sorted Set)**와 **Pub/Sub, Atomic 연산, 백그라운드 영속성(RDB/AOF)**을 제공하며 캐시 시장을 평정함.
2. **In-Memory 소실 위험과 실무 대처법**:
   - **RDB & AOF 영속성 (Persistence)**: Redis는 메모리 전용이지만 디스크에 백그라운드 스냅샷(RDB)을 남기거나 매 쿼리 로그(AOF)를 디스크에 기록해 재부팅 시 데이터를 100% 복구 가능.
   - **고가용성 (High Availability - Sentinel / Cluster)**: Master-Replica(복제본) 노드를 여러 대 두고, 메인 노드가 죽으면 1초 이내 서브 노드가 승격(Failover)되어 서비스 중단 방지.
   - **데이터 성격별 소실 영향도**:
     - *인증번호 (OTP)*: 소실되어도 사용자가 "재발송" 누르면 됨. (충격 적음)
     - *Rate Limit*: 소실되어도 카운터 0 초기화로 기능 지속.
     - *세션/토큰*: AOF 복구 및 클러스터 복제로 보호되며, 최악의 경우 재로그인 유도.

---

## Q5. Redis의 병목과 한계, 오픈소스/PR 개념, 그리고 차세대 대체 기술

### ❓ 질문
1. Redis의 주요 문제점이나 병목 현상은 무엇인가?
2. 오픈소스와 PR(Pull Request)이란 무엇인가?
3. Redis를 대처하거나 개선하는 혁신 프로젝트가 존재하는가?

### 💡 핵심 요약
1. **Redis의 주요 병목 및 한계**:
   - **싱글 스레드 블로킹 (Blocking)**: 이벤트 루프가 단일 스레드로 동작하므로 `KEYS *` 같은 무거운 쿼리가 실행되면 뒤따르는 모든 요청이 대기(병목) 상태에 빠짐.
   - **RAM 비용 부담**: 모든 데이터가 RAM에 저장되므로 대용량 데이터 적재 시 서버 비용이 매우 비쌈.
   - **Fork 시 메모리 급증**: RDB 스냅샷 백업 시 `fork()`로 인해 메모리가 순간적으로 2배 필요(Copy-On-Write).
2. **오픈소스 & PR (Pull Request) 개념**:
   - **오픈소스**: 소스코드가 누구나 볼 수 있게 GitHub 등에 공개된 소프트웨어.
   - **PR (Pull Request)**: 전 세계 개발자가 "내가 버그를 고쳤거나 기능을 개선했으니 프로젝트에 병합(Pull)해주세요"라고 기여(Contribution)를 요청하는 프로세스.
3. **Redis 라이선스 파동과 차세대 혁신 (Valkey / Dragonfly)**:
   - **2024년 라이선스 변경**: Redis 개발사가 오픈소스 라이선스(BSD)를 중단하고 비오픈소스 조항을 도입하여 커뮤니티 반발 발생.
   - **Valkey (발키)**: Linux 재단, AWS, Google 등이 기존 오픈소스 정신을 지키기 위해 Redis를 포크(Fork)하여 만든 진짜 오픈소스 대체제.
   - **Dragonfly (드래곤플라이)**: C++ 기반 완벽한 다중 스레드(Multi-threaded) 아키텍처로 재설계하여 Redis 대비 25배 뛰어난 성능과 메모리 효율을 제공하는 차세대 인메모리 DB.

---

## Q6. Valkey vs Dragonfly 기술적 차이, 병합 불가능 이유 및 상위호환 여부

### ❓ 질문
1. Valkey와 Dragonfly는 어떤 차이가 있으며, 왜 하나로 병합되지 않는가?
2. Dragonfly는 Redis/Valkey의 완벽한 상위 호환인가? 아니면 장단점이 갈리는가?

### 💡 핵심 요약
1. **Valkey vs Dragonfly 비교**:
   - **Valkey**: 기존 C언어 기반 Redis 코드베이스를 승계하여 100% 호환성과 안정성 및 순수 오픈소스(BSD)를 지키는 리눅스 재단 주도 프로젝트.
   - **Dragonfly**: C++20 기반으로 엔진을 밑바닥부터 새로 작성한 멀티스레드 인메모리 DB (스타트업 주도 프로젝트).
2. **하나로 병합(Merge)될 수 없는 이유**:
   - C vs C++20, Single-Thread vs Multi-Thread 등 **설계 엔진과 소스코드 아키텍처 자체가 완전히 다름**.
   - BSD(비영리재단) vs BSL(스타트업 상용) 라이선스 및 지배구조(Governance)가 다름.
3. **Dragonfly가 완벽한 상위 호환이 아닌 이유 (장단점)**:
   - **장점**: 압도적 초고성능(25배), 멀티코어 활용, `KEYS *` 실행 시 블로킹 없음, 메모리 절감.
   - **단점/한계**: 15년 이상 검증된 Redis/Valkey의 무결한 프로덕션 안정성(Battle-tested) 미흡, 소형 1Core 서버에서의 자원 소모 부담, 클러스터링 및 백엔드 스크립팅/모듈 생태계 호환성 한계.

---

## Q7. 동적 배열, Pub/Sub, 그리고 보너스 과제(이진 트리/BST)의 필요성 유무

### ❓ 질문
1. 동적 배열이란 무엇인가?
2. 보너스 미션 Pub/Sub이란 무엇이며 어떤 기능인가?
3. 이진 트리와 이진 탐색 트리(BST)를 구현하지 않아도 Mini Redis 미션 실행에 문제가 없는가? 왜 필수 대신 보너스로 제공되었는가?

### 💡 핵심 요약
1. **동적 배열 (Dynamic Array)**:
   - 처음에는 고정된 크기로 시작하지만, 요소가 가득 차면 용량(Capacity)을 2배로 자동 확장(Resizing)하여 무한히 요소를 추가할 수 있는 리스트 자료구조 (Python의 `list`, Java의 `ArrayList`).
2. **Pub/Sub (Publish / Subscribe)**:
   - 메시지 발행자(Publisher)가 특정 채널에 메시지를 송신하면, 그 채널을 구독(Subscribe)하고 있는 수신자들에게 메시지를 실시간으로 방송(Broadcast)해 주는 1:N 메시징 패턴 (실시간 채팅, 알림 시스템).
3. **이진 트리 / BST가 보너스인 이유**:
   - **미션 영향 없음**: 트리를 구현하지 않아도 Mini Redis의 핵심 10개 명령어(SET, GET, EXISTS, TTL, LRU 등) 동작 및 요구사항 검증에는 **아무런 문제가 없음 (100% 정상 동작)**.
   - **보너스로 둔 이유**: 필수 미션인 `MinHeap`이 "완전 이진 트리" 형태를 배열로 나타낸 것이고, 실제 Redis의 `Sorted Set` 기능이 트리의 범위 탐색과 연관되어 있으므로 자료구조적 깊이를 더하고 싶을 때 도전하는 **선택적 심화 학습(Bonus)**임.

---

## Q8. Redis와 Pub/Sub의 실무적 관계 및 유즈케이스 작동 원리

### ❓ 질문
실시간 채팅, 알림 서비스 등의 유즈케이스에서 실제로 Redis의 Pub/Sub을 사용하는가? 구체적으로 어떤 구조로 활용되는가?

### 💡 핵심 요약
1. **실제 Redis의 내장 기능**:
   - Redis는 단순 K-V 저장소일 뿐만 아니라, 자체적으로 `PUBLISH`, `SUBSCRIBE` 명령어를 완벽히 지원하는 **메시지 브로커(Message Broker)** 역할을 내장하고 있음.
2. **다중 웹 서버 환경에서의 실시간 채팅 유즈케이스**:
   - 사용자가 늘어나 서버를 여러 대(서버 A, 서버 B) 분산 배치했을 때, 서버 A에 접속한 사용자 1의 채팅 메시지를 서버 B에 접속한 사용자 2에게 전달해야 함.
   - 이때 모든 웹 서버가 중앙의 Redis Pub/Sub 채널을 구독하게 하면, 사용자 1이 보낸 메시지가 Redis를 거쳐 서버 B로 방송(Broadcast)되고, 서버 B가 사용자 2에게 최종 전달할 수 있게 됨.
3. **특징 및 한계 (Fire and Forget)**:
   - **장점**: 인메모리 기반이라 지연 시간(Latency)이 거의 없고 극도로 빠름.
   - **단점/한계**: 메시지를 따로 보관(큐잉)해 주지 않아 구독자가 잠시 접속 종료 상태였다면 그 사이 보낸 메시지는 날아감. (메시지 보관이 필요하다면 Redis Streams나 Kafka를 함께 사용)

---

## Q9. 로그인 30분 자동 만료 메커니즘과 Apache Kafka의 개념

### ❓ 질문
1. 30분 정도 아무 활동이 없으면 로그인이 저절로 풀리는 홈페이지는 거의 100% Redis를 사용하는 것인가? JWT TTL과 연관이 있는가?
2. Apache Kafka란 무엇이고 왜 사용하는가?

### 💡 핵심 요약
1. **로그인 30분 자동 만료의 세 가지 구현 가능성**:
   - **서버 자체 메모리 세션**: 서버가 1대뿐인 소규모 서비스의 경우 Redis 없이 서버 메모리 자체 세션 만료 기능 사용.
   - **Redis 기반 공유 세션**: 서버가 여러 대인 다중 서버 환경일 경우, 공통 세션 보관용으로 Redis(TTL)를 사용.
   - **JWT 자체 만료 (Access Token)**: Redis 없이 토큰 데이터 구조 자체에 기록된 만료 시간(`exp`) 스펙만으로 동작.
   - **결론**: 100% Redis는 아니지만, 최신 대규모 모던 서비스라면 Redis 세션 저장소나 JWT 만료 방식을 채택했을 가능성이 큼.
2. **Apache Kafka (아파치 카프카)**:
   - LinkedIn에서 개발한 대량의 실시간 데이터를 유실 없이 처리하기 위한 **분산 이벤트 스트리밍 플랫폼**.
   - **라디오 방송(Redis Pub/Sub)**과 달리, Kafka는 메시지를 디스크에 **영구 보관(유튜브 다시보기)**하므로 수신 서버가 죽어 있더라도 나중에 살아나서 처음부터 혹은 끊긴 지점(Offset)부터 유실 없이 안전하게 메시지를 읽어갈 수 있음.

---

## Q10. `python3 -m unittest discover -s tests` 명령어 분석 및 단위 테스트 실행 방식의 특징

### ❓ 질문
리드미에 적혀 있는 `python3 -m unittest discover -s tests` 코드의 뜻은 무엇인가요? `unittest`, `discover`, `-s`와 같은 명령어와 옵션들의 역할이 궁금합니다. 또한 이 방식이 `tests` 폴더 내부의 테스트 코드를 실행시키는 것 같은데, 일반적인 파이썬 코드 실행과 어떤 차이가 있나요?

### 💡 핵심 요약
1. **명령어 및 옵션 상세 설명**:
   - **`python3 -m unittest`**: 파이썬 표준 라이브러리에 내장된 단위 테스트 프레임워크인 `unittest` 모듈을 스크립트(모듈) 형태로 실행합니다.
   - **`discover`**: `unittest`의 하위 명령어로, **테스트 자동 발견(Test Discovery)**을 지시합니다. 특정 규칙(기본값은 `test*.py` 형식의 파일명)에 맞는 파일들을 디렉토리 내에서 자동으로 검색해 줍니다.
   - **`-s tests`** (또는 `--start-directory tests`): 자동 발견을 시작할 **출발지 디렉토리**를 지정합니다. 이 경우 워크스페이스 내의 `tests` 디렉토리 하위에서 테스트 파일을 찾습니다.
2. **일반 코드 실행과의 차이점**:
   - **실행 대상**: 일반 실행(`python3 main.py`)은 단일 스크립트 파일의 진입점(`if __name__ == '__main__':`)을 실행하는 반면, 이 명령어는 `tests` 디렉토리 내 모든 테스트 파일([test_custom_ds.py](file:///Users/f22losophysics1091/Desktop/ready/tests/test_custom_ds.py), [test_mini_redis.py](file:///Users/f22losophysics1091/Desktop/ready/tests/test_mini_redis.py))을 찾아 내부의 모든 테스트 케이스를 모아서 일괄 실행합니다.
   - **자동 테스트 로드**: 개발자가 직접 각 테스트 파일이나 함수를 임포트해서 호출하는 코드를 작성할 필요 없이, `unittest.TestCase`를 상속받고 `test_`로 시작하는 메서드를 자동으로 찾아 실행해 줍니다.
   - **테스트 결과 리포팅**: 성공/실패 여부를 수집하여 실행 시간, 통과 개수 등을 터미널에 요약 출력(`Ran X tests in Ys`, `OK` 또는 `FAILED`)해주며, 테스트 실패 시 비정상 종료 코드(non-zero exit code)를 반환하여 CI/CD 파이프라인 연동에 용이합니다.

---

## Q11. LRU Eviction 시 꼬리 노드(tail.prev)의 Key를 O(1) 시간 내에 조회하여 삭제하는 원리

### ❓ 질문
리드미의 '꼬리 노드(tail.prev)를 에빅션(remove_back())할 때 해당 노드의 key를 O(1) 시간 내에 알아내어 store와 ttl_map에서 즉시 제거하기 위해서입니다.'라는 설명이 잘 이해되지 않습니다. `store`가 정확히 무엇이고, 어떻게 꼬리 노드에서 key를 O(1) 시간에 알아내어 삭제할 수 있는지 그 구조와 원리를 설명해주세요.

### 💡 핵심 요약
1. **각 데이터 구조의 역할 (`store`의 정의)**:
   - **`self.store`**: [mini_redis_core.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/mini_redis_core.py)에 정의된 **커스텀 해시맵(HashMap)**으로, 외부에서 들어온 키(Key, 예: `"user:1"`)에서 연결 리스트의 **노드 객체 참조(Node)**로 가는 매핑을 갖고 있습니다 (`Key -> Node(Key, Value)`).
   - **`self.lru_list`**: 데이터들의 최신 사용 순서를 기록하는 **이중 연결 리스트(DoublyLinkedList)**입니다. 가장 최근에 조회/수정된 노드는 Head 바로 뒤(`head.next`)로 가고, 가장 오랫동안 쓰이지 않은 노드는 Tail 바로 앞(`tail.prev`)에 위치하게 됩니다.
2. **O(1) 시간에 Key를 알아내는 원리 (Node 설계)**:
   - 만약 노드 객체([Node](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/doubly_linked_list.py#L23-L34))에 `value`만 저장하고 `key` 정보를 가지고 있지 않다면, `lru_list.remove_back()`을 통해 쫓겨날 꼬리 노드(`tail.prev`)를 꺼냈을 때 이 노드가 어떤 키(Key)였는지 바로 알 수 없습니다.
   - 이 경우, `store`(해시맵) 전체를 순회하면서 해당 노드 객체를 값으로 가지고 있는 키가 무엇인지 선형 검색(Linear Search)해야 하므로 **$O(N)$ 시간**이 걸리게 됩니다.
   - 이를 방지하기 위해 `Node` 객체 내부에 값뿐만 아니라 **자신의 키(Key) 정보도 함께 저장**합니다 (`self.key = key`).
   - 따라서 `lru_node = self.lru_list.remove_back()`을 실행하면 반환된 노드 객체에서 즉시 `lru_node.key`를 통해 **$O(1)$의 비용으로 키 문자열을 확보**할 수 있습니다.
3. **store와 ttl_map에서의 즉각적인 O(1) 제거**:
   - 노드에서 알아낸 `key`를 사용하여 해시맵인 `self.store.remove(key)`와 `self.ttl_map.remove(key)`를 호출합니다.
   - 해시맵의 삭제 연산은 평균 **$O(1)$**의 시간 복잡도를 가지므로, 최종적으로 LRU Eviction 전체 과정(이중 연결 리스트 노드 제거 및 두 해시맵에서의 삭제)이 모두 **$O(1)$ 시간** 내에 완료됩니다.

---

## Q12. 다항식 롤링 해시(Polynomial Rolling Hash)와 체이닝(Chaining) 기반 커스텀 해시맵의 충돌 해결 및 리사이징(Rehashing) 원리

### ❓ 질문
1. 파이썬 내장 `dict` 없이 구현한 커스텀 해시맵([hash_map.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/hash_map.py))은 해시 충돌을 어떻게 해결하나요?
2. "abc"와 "cba"처럼 철자는 같고 순서만 다른 아나그램(Anagram) 문자열이 동일한 버킷 인덱스를 갖는 문제를 다항식 롤링 해시(Polynomial Rolling Hash)는 어떻게 해결하나요?
3. 데이터가 계속 늘어날 때 평균 $O(1)$ 조회 성능을 유지해 주는 Load Factor ($0.75$)와 버킷 2배 확장(Rehashing) 메커니즘을 상세히 설명해주세요.

### 💡 핵심 요약
1. **다항식 롤링 해시 (Polynomial Rolling Hash) 원리**:
   - 단순히 각 문자의 ASCII 코드를 더하는 방식($\sum \text{ord}(c)$)은 `"abc"` ($\text{97+98+99}=294$)와 `"cba"` ($\text{99+98+97}=294$)가 100% 동일한 해시값을 가져 대량의 해시 충돌을 유발합니다.
   - 이를 방지하기 위해 각 문자의 위치(인덱스 $i$)에 따라 소수 $p=31$의 거듭제곱($p^i$)을 곱해주는 다항식 해시 공식을 적용합니다:
     $$H(s) = \left( \sum_{i=0}^{n-1} \text{ord}(s[i]) \times p^i \right) \pmod m \quad (p=31, \; m=10^9+9)$$
   - 위치에 따른 가중치가 부여되므로 `"abc"`와 `"cba"`는 서로 완전히 다른 해시 정수를 가지게 되어 해시 충돌 위험이 극적으로 낮아집니다.

2. **체이닝 (Chaining) 충돌 해결 메커니즘**:
   - 계산된 해시 정수를 현재 버킷 배열 크기(`_capacity`)로 나눈 나머지(`hash % capacity`)를 버킷 인덱스로 사용합니다.
   - 만약 서로 다른 키가 동일한 버킷 인덱스에 할당되는 해시 충돌이 발생하면, 해당 버킷 방에 할당된 **이중 연결 리스트(DoublyLinkedList)**의 노드로 연쇄 연결하여 저장합니다.
```text
[Bucket Index 2] -> Head -> [Node: key="user:1", val=Node1] <-> [Node: key="cat", val=Node2] -> Tail
```

3. **Load Factor 0.75와 버킷 2배 재해싱 (Rehashing)**:
   - 데이터 개수(`_size`)가 늘어나면 한 버킷 리스트의 길이가 길어져 탐색 시간이 $O(N)$으로 변질될 수 있습니다.
   - **Load Factor = $\frac{\text{_size}}{\text{_capacity}}$**가 **$0.75$** 이상이 되면 버킷 배열 크기를 2배(`_capacity * 2`)로 늘리는 `_resize()`를 실행합니다.
   - 버킷 용량이 변하면 기존 해시값의 나머지 연산(`hash % new_capacity`) 결과가 바뀌므로, 모든 기존 데이터의 버킷 위치를 새로 계산하여 재배치(Rehashing)합니다. 이로 인해 체이닝 리스트 길이를 항상 평균 1 이하로 유지하여 **분할상환 평균 $O(1)$** 조회 성능을 보장합니다.

---

## Q13. 최소 힙(MinHeap) 기반 TTL 만료 관리와 지연 삭제(Lazy Deletion) 메커니즘

### ❓ 질문
1. Redis의 키 만료 시간(TTL) 관리에 최소 힙([min_heap.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/min_heap.py))이 가장 적합한 이유는 무엇인가요?
2. 별도의 백그라운드 타이머 스레드를 돌리지 않고 만료된 키를 청소하는 지연 삭제(Lazy Deletion)는 어떤 원리로 동작하나요?
3. 이미 힙에 들어가 있는 키에 대해 `SET`으로 값을 덮어쓰거나 `EXPIRE`를 다시 설정했을 때 발생할 수 있는 힙 내부의 낡은 엔트리(Stale Entry) 문제는 어떻게 해결하나요?

### 💡 핵심 요약
1. **최소 힙(MinHeap)의 적합성**:
   - 일반 리스트나 해시맵을 쓰면 "가장 먼저 만료될 키"를 찾기 위해 전체 키 $N$개를 매번 순회해야 하므로 **$O(N)$**의 시간이 걸립니다.
   - 최소 힙에 만료 시각 타임스탬프 튜플 `(expire_at, key)` 형태로 저장하면, 가장 만료 시각이 이른(작은) 항목이 항상 최상단 루트(인덱스 `0`)에 위치합니다.
   - 따라서 $O(1)$ 시간에 `peek()`로 최상단 항목의 만료 여부를 검사하고, 만료된 경우 $O(\log N)$의 최단 시간에 `pop()` 및 재정렬(`_heapify_down`)을 수행할 수 있습니다.

2. **지연 삭제 (Lazy Deletion) 전략**:
   - 백그라운드에서 끊임없이 1초마다 루프를 돌며 검사하는 타이머 스레드는 CPU 자원을 낭비하고 동시성 락(Lock) 복잡성을 유발합니다.
   - Mini Redis는 클라이언트가 명령어를 실행할 때마다 직전에 `_cleanup_expired()`를 호출하는 **지연 삭제(Lazy Deletion)** 방식을 사용합니다.
```text
[명령어 호출 (GET/SET/EXPIRE 등)]
       │
       ▼
_cleanup_expired() 실행
       │
       ├──> MinHeap.peek() 검사 (O(1))
       │      │
       │      ├──> expire_at > now? ---> [종료! 뒤쪽 항목은 볼 필요도 없음]
       │      │
       │      └──> expire_at <= now? --> MinHeap.pop() (O(log N)) 및 삭제 수행
```

3. **Stale Entry (낡은 힙 항목) 처리원리**:
   - 기존 키에 대해 `SET`으로 덮어쓰면 TTL은 제거되고, `EXPIRE`를 재호출하면 새로운 `expire_at`이 힙에 또 추가됩니다. 힙 중간의 낡은 항목을 일일이 찾아 지우는 것은 $O(N)$으로 비효율적입니다.
   - 따라서 `ttl_map`(해시맵, `key -> 최신 expire_at`)을 보조 데이터 구조로 유지합니다.
   - `_cleanup_expired()`에서 힙 상단 항목을 `pop()`할 때, `ttl_map.get(key)`의 **최신 만료 시각과 힙의 expire_at을 대조**합니다. `ttl_map`에 키가 없거나 만료 시각이 일치하지 않으면 "이미 갱신되거나 삭제된 낡은 힙 데이터"로 판단하여 무시(Skip)합니다.

---

## Q14. 메모리 제한(maxmemory) 환경에서의 used_memory 바이트 추적 및 LRU Eviction 전체 파이프라인

### ❓ 질문
1. `mini_redis` 코어 엔진([mini_redis_core.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/mini_redis_core.py))은 메모리 사용량(`used_memory`)을 어떤 공식을 통해 실시간으로 추적하나요?
2. `CONFIG SET maxmemory`로 용량을 제한했을 때, `SET` 명령어가 실행되며 메모리 한도를 넘어서면 LRU 데이터가 제거(Eviction)되는 전체 흐름을 시각적으로 설명해주세요.

### 💡 핵심 요약
1. **used_memory 실시간 추적 공식**:
   - 미션 요구사항 4.3조항에 따라 데이터 구조 오버헤드는 제외하고 오직 저장된 문자열의 바이트 크기만 계산합니다:
     $$\text{used\_memory} = \sum \Big( \text{len}(\text{utf8}(key)) + \text{len}(\text{utf8}(value)) \Big)$$
   - `SET`으로 새 키-값이 들어오면 해당 바이트를 `+` 가산하고, `DEL`, 만료, 또는 `SET` 덮어쓰기 발생 시 기존 바이트를 `-` 감산하여 $O(1)$ 시간에 exact 메모리 사용량을 유지합니다.

2. **`SET` 명령어 수행 및 LRU Eviction 4단계 파이프라인**:
```text
[입력: SET user:1 "Alice"]
       │
       ▼
1. Data Refinement & Validation
   - key/value 공백 정제 (strip)
   - mem_cost = len("user:1") + len("Alice") 계산
   - _cleanup_expired() 호출로 만료 키 선제 청소
   - 단일 데이터 mem_cost > maxmemory 인 경우 OOM 예외 발생
       │
       ▼
2. Existing Key Overwrite Handling
   - 기존 user:1이 존재하면 이전 memory 차감 및 lru_list, ttl_map 노드 제거
       │
       ▼
3. Node Insertion & Memory Charge
   - Node(key="user:1", value="Alice") 생성
   - lru_list.insert_front() -> Head 직후(MRU) 위치에 꼽기
   - store.put("user:1", node) 및 used_memory += mem_cost
       │
       ▼
4. LRU Eviction Loop (maxmemory > 0 및 used_memory > maxmemory 인 동안)
   - lru_list.remove_back() 호출로 Tail 직전(가장 안 쓰인 LRU 노드) 떼어내기
   - store와 ttl_map에서 해당 key $O(1)$ 삭제
   - used_memory -= freed_memory 및 evicted_keys += 1
```

---

## Q15. 힙(Heap)과 이진 트리(Binary Tree)의 개념, 차이점, 및 BST와의 비교

### ❓ 질문
1. 힙(Heap)이란 무엇이고, 이진 트리(Binary Tree)와의 차이점은 무엇인가요?
2. 힙은 이진 트리의 한 종류(하위 개념)인가요?
3. 힙(Heap)과 이진 탐색 트리(BST, Binary Search Tree)는 어떻게 다르며, 왜 힙은 포인터 대신 1차원 배열로 구현하나요?

### 💡 핵심 요약
1. **힙(Heap)의 정의와 포함 관계**:
   - **개념**: 최댓값이나 최솟값을 빠르게($O(1)$) 찾아내기 위해 만들어진 **완전 이진 트리(Complete Binary Tree)** 기반의 데이터 구조입니다.
   - **포함 관계**: 힙은 이진 트리의 한 종류입니다.
     $$\text{이진 트리 (Binary Tree)} \supset \text{완전 이진 트리 (Complete Binary Tree)} \supset \text{힙 (Heap)}$$
     - *이진 트리*: 각 노드가 최대 2개의 자식을 가지는 트리.
     - *완전 이진 트리*: 마지막 레벨을 제외하고 모든 노드가 채워져 있고, 마지막 레벨은 왼쪽부터 차곡차곡 채워진 트리.
     - *힙*: 완전 이진 트리 형태 위에 **"부모 노드와 자식 노드 간의 대소 관계"(Heap Property)**라는 조건이 추가된 트리. (최소 힙: $\text{부모} \le \text{자식}$, 최대 힙: $\text{부모} \ge \text{자식}$)

2. **힙(Heap) vs 이진 탐색 트리(BST)의 핵심 차이점**:
   - **정렬 규칙의 방향**:
     - **BST**: **좌우 대소 관계** ($\text{왼쪽 자식} < \text{부모} < \text{오른쪽 자식}$). 모든 요소가 좌우로 정렬되어 탐색($O(\log N)$)에 최적화됨.
     - **Heap**: **상하(부모-자식) 대소 관계만 존재** ($\text{부모} \le \text{자식}$). 형제 노드나 좌우 노드 간에는 대소 관계 규칙이 없음 (반정렬/부분정렬 상태).
   - **목적의 차이**: BST는 "임의의 데이터 탐색($O(\log N)$)"이 목적이고, Heap은 "최상단 루트(최솟값/최댓값) 빠르게 확인($O(1)$) 및 추출($O(\log N)$)"이 목적입니다.

3. **힙을 1차원 배열(Dynamic Array)로 구현하는 이유**:
   - 일반 이진 트리는 모양이 불균형할 수 있어 포인터 객체(`Node.left`, `Node.right`) 연결 방식을 쓰지만, 힙은 항상 빈 구멍 없이 채워지는 **완전 이진 트리**이므로 **1차원 배열**에 차례대로 담을 수 있습니다.
   - 포인터 메모리 오버헤드가 없고, 산술 연산만으로 부모/자식 인덱스를 $O(1)$에 직접 계산합니다:
     - 부모 인덱스 = `(i - 1) // 2`
     - 왼쪽 자식 인덱스 = `2 * i + 1`
     - 오른쪽 자식 인덱스 = `2 * i + 2`

4. **Mini Redis에서의 실제 구현 및 활용 ([min_heap.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/min_heap.py))**:
   - 본 프로젝트의 [min_heap.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/min_heap.py)는 `DynamicArray` 1차원 배열 위에 최소 힙 속성을 적용해 구현되었습니다.
   - `(expire_at, key)` 튜플을 힙에 저장하여, 전체 키 $N$개를 순회하는 $O(N)$ 대신 최상단 루트(`0`번 인덱스) 확인을 통해 $O(1)$ 시간 내에 TTL 만료 여부를 검사(`peek()`)하고 $O(\log N)$에 제거(`pop()`)합니다.

---

## Q16. Mini-Redis 코어의 `store` 메인 저장소 개념과 커스텀 `DynamicArray` 클래스의 정체

### ❓ 질문
1. [mini_redis_core.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/mini_redis_core.py)에 등장하는 `self.store`란 무엇인가요? Data Pool이나 DB의 메인 저장 공간을 뜻하는 건가요?
2. [dynamic_array.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/dynamic_array.py)의 `class DynamicArray`는 파이썬 내장 기능인가요, 아니면 사용자 정의 클래스인가요?

### 💡 핵심 요약
1. **`self.store`의 개념과 역할 (메인 데이터 저장 공간)**:
   - **맞습니다.** `self.store`는 Mini-Redis 데이터베이스의 **실제 데이터(Key-Value)를 저장하는 핵심 저장 공간 (Main Data Storage / Data Pool)**입니다.
   - [mini_redis_core.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/mini_redis_core.py#L35)에서 `self.store: HashMap = HashMap()`으로 선언되어 있습니다.
   - 외부에서 `SET user:1 "Alice"` 명령어가 들어오면, 키(`"user:1"`)에서 노드 객체(`Node(key="user:1", value="Alice")`)로 향하는 매핑을 평균 $O(1)$ 시간 내에 조회/저장할 수 있도록 관리하는 메인 해시맵 테이블입니다.
   - **Mini-Redis 내부 4대 서브시스템 중 하나**:
     - `self.store` (HashMap): 메인 데이터 저장소 (Key $\rightarrow$ Node)
     - `self.lru_list` (DoublyLinkedList): LRU 캐시 최근 사용 순서 관리
     - `self.ttl_heap` (MinHeap): 만료 시각(TTL) 관리 최소 힙
     - `self.ttl_map` (HashMap): Key별 최신 만료 시각 매핑

2. **`DynamicArray` 클래스의 정체 (사용자 정의 커스텀 클래스)**:
   - **파이썬 내장 기능이 아니며, 본 프로젝트에서 직접 작성한 사용자 정의 클래스(Custom Class)**입니다.
   - 파이썬의 내장 `list`는 CPython 내부(C언어)에서 자동으로 크기가 늘어나는 동적 배열이지만, 본 프로젝트는 **"파이썬 내장 고급 컬렉션 배제 및 밑바닥 구현"**이라는 미션 제약조건을 가지고 있습니다.
   - 따라서 [dynamic_array.py](file:///Users/f22losophysics1091/Desktop/ready/mini_redis/dynamic_array.py#L21-L39)에서는 원시적인 고정 크기 리스트(`[None] * capacity`)만을 할당받은 후, 요소 수(`_size`)를 직접 추적하고 공간이 부족할 때 2배 크기로 새로 할당하여 기존 요소를 복사하는 **동적 배열(Dynamic Array) 리사이징 알고리즘을 밑바닥부터 직접 구현**했습니다.

---

## Q17. RAM에서 CPU 레지스터로 데이터 로드 시 캐시 메모리(Cache)의 거쳐가는 순서 및 원리

### ❓ 질문
RAM(주기억장치)에서 CPU가 연산할 데이터를 레지스터로 보낼 때, 보통 캐시(Cache)를 거쳐서 레지스터로 가나요? 아니면 레지스터로 직행한 다음에 캐시로 이동하나요?

### 💡 핵심 요약
1. **무조건 캐시(Cache)를 거쳐서 레지스터(Register)로 이동합니다**:
   - **데이터 이동 경로**: $\text{RAM (DRAM)} \longrightarrow \text{L3 Cache} \longrightarrow \text{L2 Cache} \longrightarrow \text{L1 Cache} \longrightarrow \text{CPU Register}$
   - 레지스터로 데이터가 직행한 후 역으로 캐시에 채워지는 구조는 하드웨어 아키텍처상 불가능하며 존재하지 않습니다.

2. **구체적인 데이터 로드 흐름 (Memory Read Pipeline)**:
   - **1단계 (Cache Lookup)**: CPU 제어장치가 필요한 메모리 주소를 **L1 $\rightarrow$ L2 $\rightarrow$ L3 캐시** 순서로 탐색합니다.
   - **2단계 (Cache Miss 발생)**: 캐시에 데이터가 없으면(**Cache Miss**) CPU 통신 버스를 통해 **RAM(DRAM)**으로 데이터 읽기 요청을 전송합니다.
   - **3단계 (Cache Line 채우기)**: RAM에서 데이터를 읽어올 때 단일 바이트/word만 가져오는 것이 아니라, **64 바이트 단위 블록(Cache Line)** 전체를 읽어와 **L3 $\rightarrow$ L2 $\rightarrow$ L1 캐시** 순서로 차례대로 복사해 넣습니다 (공간 국소성 활용).
   - **4단계 (Register Load)**: 최종적으로 **L1 캐시**에 올라온 64바이트 블록 중 CPU 연산에 필요한 데이터(4~8바이트)를 **레지스터(Register)**로 가져와 ALU 연산을 실행합니다.

3. **왜 레지스터 직행이 불가능하고 캐시를 거쳐야 하는가?**:
   - **하드웨어 물리 아키텍처 제약**: CPU 코어 내 레지스터 연산 파이프라인은 **L1 캐시 컨트롤러**와 직접 하드웨어 버스로 연결되어 있어, 캐시를 우회하고 RAM과 직접 통신하는 별도 통로가 없습니다.
   - **국소성(Locality) 원리를 통한 병목 방지**:
     - RAM 접근은 약 $100 \sim 200$ 클럭 사이클이 소요되는 심각한 병목 구간입니다.
     - RAM 데이터를 캐시 메모리에 64바이트 단위(Cache Line)로 먼저 복사해 두어야, 바로 다음 명령어 연산 시 캐시 히트(Cache Hit, $1 \sim 4$ 사이클)가 발생하여 CPU가 대기(Stall)하는 것을 막을 수 있습니다.



