# [Bug] Deadlock - 두 Worker 스레드가 서로의 락을 기다리며 프로세스가 무응답 상태로 정체

## 1. Description (현상 설명)
`MULTI_THREAD_ENABLE=true`로 실행하면 앱은 concurrent transaction processor를 시작한 뒤 두 Worker 스레드가 각각 다른 자원을 먼저 획득한다. 이후 서로 상대방이 가진 자원을 요청하면서 `WAITING ... BLOCKED` 로그를 마지막으로 더 이상 진행하지 않는다.

프로세스 PID는 유지되지만 CPU 사용률은 거의 0에 가까워지고, 메모리 사용량도 변하지 않으며, 애플리케이션 로그가 멈춘다. 이는 crash가 아니라 살아 있는 무응답 상태다.

## 2. Evidence & Logs (증거 자료)

### 실행 조건
| 구분 | MEMORY_LIMIT | CPU_MAX_OCCUPY | MULTI_THREAD_ENABLE | 결과 |
| :--- | :--- | :--- | :--- | :--- |
| Before | 512MB | 10% | true | Deadlock 재현 |
| After | 512MB | 10% | false | 정상 스케줄러/워커 흐름, Deadlock 미발생 |

### PID 존재 및 스레드 정체
`evidence/raw/deadlock-on.monitor.log`:

```text
2026-05-16 00:33:19,12995,SNl,3,1.1,0.1,21696,180188,00:07,agent-app-leak
2026-05-16 00:33:21,12995,SNl,3,0.8,0.1,21696,180188,00:09,agent-app-leak
2026-05-16 00:33:28,12995,SNl,3,0.5,0.1,21696,180188,00:15,agent-app-leak
2026-05-16 00:33:38,12995,SNl,3,0.3,0.1,21696,180188,00:25,agent-app-leak
```

스레드 스냅샷:

```text
# thread snapshot 2026-05-16 00:33:38 pids=12993,12995
    PID     TID STAT %CPU %MEM COMMAND
  12993   12993 S     0.5  0.0 agent-app-leak
  12995   12995 SNl   0.3  0.1 agent-app-leak
  12995   13122 SNl   0.0  0.1 agent-app-leak
  12995   13123 SNl   0.0  0.1 agent-app-leak
```

PID `12995`는 살아 있고 스레드도 3개 존재하지만, Worker 스레드 `13122`, `13123`의 CPU는 0.0으로 정체되어 있다.

### 마지막 애플리케이션 로그
`evidence/raw/deadlock-on.app.log`:

```text
2026-05-16 00:33:19,708 [INFO] [AgentWorker][Worker-Thread-1] LOCK ACQUIRED: [Shared_Memory_A]. (Holding...)
2026-05-16 00:33:19,708 [INFO] [AgentWorker][Worker-Thread-2] LOCK ACQUIRED: [Socket_Pool_B]. (Holding...)
2026-05-16 00:33:21,712 [INFO] [AgentWorker][Worker-Thread-1] Need resource [Socket_Pool_B] to finish job.
2026-05-16 00:33:21,712 [INFO] [AgentWorker][Worker-Thread-2] Need resource [Shared_Memory_A] to write logs.
2026-05-16 00:33:21,713 [INFO] [AgentWorker][Worker-Thread-2] WAITING for [Shared_Memory_A]... (Status: BLOCKED)
2026-05-16 00:33:21,713 [INFO] [AgentWorker][Worker-Thread-1] WAITING for [Socket_Pool_B]... (Status: BLOCKED)
```

### 회피 케이스
`evidence/raw/deadlock-off.app.log`:

```text
2026-05-16 00:34:02,275 [INFO] [Scheduler] Registered Tasks: ['Thread-A', 'Thread-B', 'Thread-C']
2026-05-16 00:34:02,276 [INFO] [Thread-A] Task Started. Calculating... (20%)
2026-05-16 00:34:02,429 [INFO] [Thread-B] Task Started. Calculating... (20%)
2026-05-16 00:34:02,583 [INFO] [Thread-C] Task Started. Calculating... (20%)
2026-05-16 00:34:03,359 [INFO] [Scheduler] All tasks completed.
```

`MULTI_THREAD_ENABLE=false`에서는 strict locking 기반 concurrent transaction processor가 아니라 정상 스케줄러 흐름이 실행되어 Deadlock 로그가 발생하지 않았다.

## 3. Root Cause Analysis (원인 분석)
* **순환 의존의 도식화**:
  본 장애는 두 스레드가 각자 하나의 자원을 이미 쥐어 점유(Hold)한 상태에서, 상대방이 쥐고 있는 다른 자원을 얻기 위해 무한히 락 해제를 대기(Wait)하는 **순환 의존성 고리**가 만들어지며 발생합니다.
  ```text
  [ Worker-Thread-1 ] ──(점유)──> [ Shared_Memory_A ] ──(대기)──> [ Worker-Thread-2 ]
          ▲                                                               │
          │                                                               │
        (대기)                                                          (점유)
          │                                                               ▼
  [ Socket_Pool_B ] <─────────────────────────────────────────────────────┘
  ```
  이를 락 자원 관점에서 매핑하면 단방향 순환 그래프(Closed Loop)가 완성됩니다.
  `Worker-Thread-1` ➔ `Socket_Pool_B` 대기 ➔ `Worker-Thread-2` ➔ `Shared_Memory_A` 대기 ➔ `Worker-Thread-1`
* **교착상태 4대 조건과의 대조**:
  1. **상호 배제 (Mutual Exclusion)**: 메모리 블록 `Shared_Memory_A`와 네트워크 자원 `Socket_Pool_B`는 다중 스레드가 동시에 소유할 수 없는 상호 배제적 자원(Mutex/Lock)입니다.
  2. **점유 대기 (Hold and Wait)**: `Worker-Thread-1`은 자신이 이미 획득한 `Shared_Memory_A`를 손에 쥔 상태로 `Socket_Pool_B`를 요청하며 대기합니다.
  3. **비선점 (No Preemption)**: 다른 스레드가 쥐고 있는 자원을 운영체제 수준이나 강제 호출로 중도 탈취(Preempt)할 수 없습니다.
  4. **순환 대기 (Circular Wait)**: 자원을 양보하지 않는 두 스레드 간 대기 경로가 하나의 닫힌 고리(Closed Loop)인 원을 그립니다.
  네 가지 조건이 동시에 충족됨으로써 스레드가 꼼짝 못 하고 굳어버리는 전형적인 Deadlock 상태가 영구 고착화되었습니다.

## 4. Workaround & Verification (조치 및 검증)
임시 조치로 멀티스레드 경합 시나리오를 차단하기 위해 `MULTI_THREAD_ENABLE` 환경변수를 `false`로 변환했다.

### Before & After 대조 검증 표
| 항목 | Before (멀티스레드 활성화) | After (싱글스레드/스케줄러 모드) |
| :--- | :--- | :--- |
| 제어 변수 설정 | `MULTI_THREAD_ENABLE=true` | `MULTI_THREAD_ENABLE=false` |
| 감시 대상 PID | 12995 | 13210 (테스트 예시) |
| 프로세스 CPU 수렴 | **0.3%** 바닥 수준으로 고착 수렴 | 작업 완료 후 기동 시 정상적인 CPU 연산 진행 |
| RSS 물리 메모리 | **21,696 KB**에 고정되어 단 1B도 움직이지 않음 | 작업 기동 시 메모리 맵 변화 및 정상 완료 |
| 워커 스레드 상태 | `TID 13122, 13123` 스레드 CPU **0.0%** 동결 | 워커/스케줄러 순차적 정상 진행 |
| 최종 애플리케이션 로그 | `WAITING ... BLOCKED` 상태에서 영구 Hang | `All tasks completed` 성공적으로 찍으며 정상 가동 |

* **근본 대책 (Code-level Remedy)**: 환경변수 비활성화 방식은 동시성 대용량 처리를 포기하는 임시방편입니다. 소스 코드를 근본적으로 교정하려면, 두 스레드가 자원을 획득하는 전역 순서를 **동일하게 일치(Lock Ordering)**시켜야 합니다. 즉, 두 스레드 모두 항상 `Shared_Memory_A`를 먼저 쥐고 난 뒤에만 `Socket_Pool_B`를 획득할 수 있게 통일하면 순환 고리가 절대 생성되지 않습니다. 또는 락 획득 시 **`try_lock(timeout=N)`** 과 같은 타임아웃 기법을 구현하여, 일정 시간 내에 락을 잡지 못하면 이미 자기가 쥐고 있던 모든 락을 즉각 릴리즈(Release)하고 무작위 시간 동안 대기(Jitter Backoff) 후 다시 재시도하도록 롤백 설계를 해야 합니다.

