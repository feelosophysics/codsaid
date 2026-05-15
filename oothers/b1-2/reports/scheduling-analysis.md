# [Analysis] 로그 패턴 분석을 통한 스케줄링 알고리즘 추론

## 1. 로그 관찰 개요
`MULTI_THREAD_ENABLE=false`, `CPU_MAX_OCCUPY=10`, `MEMORY_LIMIT=512` 조건에서 앱은 `Healthy System Monitoring` 시나리오를 선택했다. 이때 `Scheduler`가 `Thread-A`, `Thread-B`, `Thread-C`를 등록하고 작업을 교대로 진행했다.

## 2. Evidence & Logs
`evidence/raw/deadlock-off.app.log`와 `evidence/raw/cpu-low.app.log`에서 같은 스케줄링 패턴이 관측됐다.

```text
2026-05-16 00:34:02,276 [INFO] [Thread-A] Task Started. Calculating... (20%)
2026-05-16 00:34:02,326 [INFO] [Thread-A] Calculating... (40%)
2026-05-16 00:34:02,377 [INFO] [Thread-A] Preempted. Progress saved at (40%)
2026-05-16 00:34:02,429 [INFO] [Thread-B] Task Started. Calculating... (20%)
2026-05-16 00:34:02,481 [INFO] [Thread-B] Calculating... (40%)
2026-05-16 00:34:02,531 [INFO] [Thread-B] Preempted. Progress saved at (40%)
2026-05-16 00:34:02,583 [INFO] [Thread-C] Task Started. Calculating... (20%)
2026-05-16 00:34:02,635 [INFO] [Thread-C] Calculating... (40%)
2026-05-16 00:34:02,687 [INFO] [Thread-C] Preempted. Progress saved at (40%)
2026-05-16 00:34:02,738 [INFO] [Thread-A] Resumed. Calculating... (60%)
```

## 3. Pattern Analysis
FCFS라면 Thread-A가 100% 완료된 뒤 Thread-B가 시작되어야 한다. 하지만 Thread-A는 40%에서 preempted 되었고, Thread-B와 Thread-C가 끼어들었다.

Priority scheduling이라면 특정 우선순위 작업이 반복적으로 먼저 선택되거나 오래 실행되는 편향이 보여야 한다. 그러나 로그에서는 A → B → C → A → B → C 순서가 균등하게 반복된다.

Round-Robin이라면 각 작업이 일정 시간 또는 일정 진행량만큼 실행된 뒤 다음 작업으로 넘어가고, 완료되지 않은 작업은 나중에 재개된다. 로그의 `Preempted`, `Progress saved`, `Resumed`가 이 패턴과 가장 잘 맞는다.

## 4. Conclusion
이 앱의 미션용 작업 스케줄러는 Round-Robin 방식으로 추론된다.

장점은 작업 간 공정성이 높고, 하나의 작업이 전체 실행 흐름을 독점하지 않는다는 점이다. 웹 요청 처리처럼 여러 사용자 요청에 응답성을 나눠 줘야 하는 구조에 적합하다.

단점은 컨텍스트 전환 비용이 생기고, 처리량만 중요한 배치 작업에서는 FCFS 또는 우선순위 기반 처리보다 비효율적일 수 있다는 점이다. 실시간성이 매우 강한 시스템에서는 단순 Round-Robin만으로는 마감 시간 보장이 어렵기 때문에 priority나 deadline 기반 정책이 필요할 수 있다.
