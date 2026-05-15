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
Deadlock의 원인은 락 획득 순서가 서로 반대인 두 스레드다.

| 스레드 | 먼저 획득한 자원 | 나중에 요청한 자원 |
| :--- | :--- | :--- |
| Worker-Thread-1 | `Shared_Memory_A` | `Socket_Pool_B` |
| Worker-Thread-2 | `Socket_Pool_B` | `Shared_Memory_A` |

이 상황은 교착상태 4대 조건 중 특히 `상호 배제`, `점유 대기`, `비선점`, `순환 대기`를 만족한다. `Shared_Memory_A`와 `Socket_Pool_B`는 동시에 여러 스레드가 마음대로 사용할 수 없는 자원이다. 각 스레드는 이미 하나의 자원을 잡은 상태로 다른 자원을 기다린다. 락은 강제로 빼앗기지 않는다. 그리고 Thread-1 → Socket_Pool_B → Thread-2 → Shared_Memory_A → Thread-1의 순환 대기가 완성된다.

## 4. Workaround & Verification (조치 및 검증)
임시 조치로 `MULTI_THREAD_ENABLE=true`를 `false`로 바꿨다.

| 항목 | Before | After |
| :--- | :--- | :--- |
| 설정 | `MULTI_THREAD_ENABLE=true` | `MULTI_THREAD_ENABLE=false` |
| 마지막 로그 | `WAITING ... BLOCKED` | `Scheduler All tasks completed` 후 정상 모니터링 |
| PID 상태 | 살아 있으나 정체 | 살아 있으며 계속 작업 진행 |
| 스레드 상태 | Worker 스레드 CPU 0.0 | 워커/스케줄러 로그 진행 |

근본 해결은 모든 스레드가 같은 순서로 락을 잡게 만들거나, 락 획득 timeout을 두거나, 두 자원을 하나의 상위 락으로 보호하거나, 락을 오래 잡은 채 외부 자원을 기다리지 않도록 코드를 재설계하는 것이다.
