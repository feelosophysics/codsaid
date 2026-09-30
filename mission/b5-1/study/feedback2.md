AI 사전평가 결과
평가 시각: 2026-07-28 19:02:01

82%
(14 / 17 항목 통과)
종합 평가
핵심 요구사항(문자열 명령, LRU/TTL 구조, 해시맵/리스트/힙 직접구현, 메모리/TTL 동작)은 코드에 충실히 구현되어 있음. 다만 LFU 전환 설계, 대규모(10만) 병목 분석, used_memory 모델 변경 영향에 대한 설계/문서가 누락되어 보완 필요.

항목별 평가 (17개)

PASS
평가 항목 #1
근거
mini_redis_core.py > 'def set(self, key: str, value: str) -> str:'
잘한 점
SET/GET/DEL 및 DBSIZE/KEYS가 구현되고 CLI에 연동됨
부족한 점
특별한 기능 누락 없음
보완
명령별 인자/타입 검사 메시지를 통일해 테스트 케이스에 명시적으로 대응

PASS
평가 항목 #2
근거
mini_redis_core.py > 'while self.maxmemory > 0 and self.used_memory > self.maxmemory:'
잘한 점
maxmemory 설정과 초과 시 LRU 제거 루프가 구현됨
부족한 점
LRU 제거가 올드키(리스트 꼬리)를 사용함을 문서로 명시하면 좋음
보완
CONFIG 변경 시 발생 가능한 즉시 Eviction 흐름을 README에 한 문장으로 추가

PASS
평가 항목 #3
근거
mini_redis_core.py > 'used_memory:{self.used_memory}\n'
잘한 점
INFO memory가 used_memory/maxmemory/evicted_keys를 출력함
부족한 점
출력 포맷 확장(예: 단위) 필요성 없음
보완
INFO 출력 예시를 README에 하나 추가하여 기대값 명확화

PASS
평가 항목 #4
근거
mini_redis_core.py > 'def expire(self, key: str, seconds: int) -> int:'
잘한 점
EXPIRE/TTL 구현과 _cleanup_expired 통한 만료 제거가 존재함
부족한 점
TTL 경계(초단위 반올림 등) 설명이 문서에 없음
보완
TTL 반환 방식(음수/0처리) 구현 의도를 README에 간단히 기술

PASS
평가 항목 #5
근거
mini_redis_core.py > "raise MemoryError(\"OOM command not allowed when used_memory > 'maxmemory'\")"
잘한 점
인자/정수 파싱 오류와 OOM을 적절히 처리하고 메시지로 노출함
부족한 점
CLI 출력 포맷 일관성(예: 모든 내부 예외에 '(error)' 프리픽스)이 일부 누락됨
보완
MemoryError 발생 시 CLI에서 '(error)' 접두를 붙여 출력하도록 조정 고려

PASS
평가 항목 #6
근거
doubly_linked_list.py > 'self.prev = None'
잘한 점
Node에 prev/next/key/value가 있고 insert/remove/move 메서드들이 O(1)로 구현됨
부족한 점
Node 필드명이 'data' 요구와 다르게 key/value로 분리되어 있음
보완
문서에서 Node 구조(key/value 사용)를 명시하여 평가 항목과 용어 차이를 설명

PASS
평가 항목 #7
근거
hash_map.py > 'p = 31 # 영어 알파벳 소문자를 커버하기에 적합한 소수'
잘한 점
다항식 롤링 해시를 직접 구현하고 과정 주석을 제공함
부족한 점
해시의 시간복잡도/분포 특성에 대한 간단한 분석은 없음
보완
간단한 해시 분포(충돌) 실험 결과를 README에 추가 고려

PASS
평가 항목 #8
근거
hash_map.py > 'self._buckets.append(DoublyLinkedList())'
잘한 점
체이닝 방식으로 버킷마다 DoublyLinkedList를 사용해 충돌을 해결함
부족한 점
버킷 내 노드 재사용 정책에 대한 명시적 언급은 없음
보완
체이닝 노드 재사용(예: 객체 재활용) 전략을 설계 메모에 추가하면 좋음

PASS
평가 항목 #9
근거
hash_map.py > 'if self._size / self._capacity >= 0.75:'
잘한 점
로드팩터 0.75 조건과 버킷 2배 확장이 구현되어 있음
부족한 점
리해시 중 복사 비용에 대한 영향 분석 문서는 없음
보완
리해시 시점과 비용에 대한 간단한 설명을 코드 주석에 추가

PASS
평가 항목 #10
근거
mini_redis_core.py > 'self.store = HashMap()'
잘한 점
HashMap과 DoublyLinkedList를 분리하여 조회·순서 역할을 명확히 구현함
부족한 점
두 구조의 상호작용(참조 흐름)을 한 그림으로 정리하면 더 명확함
보완
아키텍처 다이어그램 한 장을 README에 포함시키기

PASS
평가 항목 #11
근거
mini_redis_core.py > 'self.lru_list.move_to_front(node)'
잘한 점
조회시 해시로 노드 찾고 리스트 이동으로 갱신해 O(1) 원리를 코드로 증명함
부족한 점
평균/최악 복잡도에 대한 간단한 주석은 더해질 수 있음
보완
핵심 연산들에 대한 시간복잡도 표기를 메서드 docstring에 추가

PASS
평가 항목 #12
근거
mini_redis_core.py > 'expire_at, key = self.ttl_heap.peek()'
잘한 점
TTL 관리를 위해 최소힙(peek/pop)을 사용해 빠른 만료 검색을 구현함
부족한 점
힙과 ttl_map의 lazy deletion 상호작용을 문서화하면 좋음
보완
lazy deletion 시나리오(예: 중복 엔트리 처리)를 README에 사례로 추가

PASS
평가 항목 #13
근거
mini_redis_core.py > 'self.used_memory -= mem_freed'
잘한 점
Eviction 시 used_memory 갱신과 evicted_keys 증가가 구현되어 있음
부족한 점
단일 엔트리 OOM 거부 메시지 외의 통계(어느 키가 제거됐는지)는 없음
보완
eviction 발생 시 제거된 키 로그(디버그 레벨)를 옵션으로 남겨두기

PASS
평가 항목 #14
근거
mini_redis_core.py > 'self._cleanup_expired()'
잘한 점
GET에서 만료 확인 후 삭제/반환 및 LRU 갱신 흐름을 올바르게 구현함
부족한 점
만료로 삭제된 경우의 정확한 출력 포맷 예시가 문서에 부족함
보완
GET 만료 케이스의 출력 예시를 README 사용 예시에 추가

FAIL
평가 항목 #15
부족한 점
LFU 전환에 필요한 빈도 카운트·자료구조 변경·정책 재설계 논의/코드가 없음
보완
빈도 카운트와 우선순위 구조를 추가하는 설계 노트를 작성하고 영향 범위를 정의하세요

FAIL
평가 항목 #16
부족한 점
대규모(10만) 처리시 병목 식별(락/싱글스레드/단일 해시 버킷 등) 및 샤딩/병렬화 대책 문서가 없음
보완
핫스팟 프로파일러 결과 기반 병목 목록과 샤딩/병렬화 옵션을 설계 문서로 추가하세요

FAIL
평가 항목 #17
부족한 점
used_memory 모델 변경(오버헤드 포함 등)이 채점·비교에 미칠 영향에 대한 분석/보정 방안이 없음
보완
used_memory 측정 변경 시 보정 방법과 채점 영향(예: 기준 표준화)을 문서화하세요