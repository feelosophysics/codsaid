# [Bug] CPU Latency - CPU_MAX_OCCUPY 과대 설정으로 CpuWorker가 임계치를 초과하고 SIGTERM 종료

## 1. Description (현상 설명)
`agent-app-leak`를 `CPU_MAX_OCCUPY=100`으로 실행하면 `CpuWorker`의 내부 부하가 점진적으로 상승하다가 50%를 넘는 순간 `CPU Threshold Violated` 로그를 남기고 프로세스가 종료된다.

비교 실행에서 `CPU_MAX_OCCUPY=10`으로 낮추면 앱은 부하를 10% 안팎에서 올렸다 내리는 cooldown 흐름으로 유지되며, 제한 시간 동안 자체 종료되지 않았다.

## 2. Evidence & Logs (증거 자료)

### 실행 조건
| 구분 | MEMORY_LIMIT | CPU_MAX_OCCUPY | MULTI_THREAD_ENABLE | 결과 |
| :--- | :--- | :--- | :--- | :--- |
| Before | 512MB | 100% | false | 약 31초 후 CPU 임계치 위반 종료 |
| After | 512MB | 10% | false | 35초 관찰 동안 자체 종료 없음 |

### 애플리케이션 로그
`evidence/raw/cpu-high.app.log`:

```text
2026-05-16 00:30:46,958 [INFO] [CpuWorker] Started. Maximum CPU Limit: 100%
2026-05-16 00:30:59,370 [INFO] [CpuWorker] Current Load: 27.05%
2026-05-16 00:31:05,580 [INFO] [CpuWorker] Current Load: 37.78%
2026-05-16 00:31:11,788 [INFO] [CpuWorker] Current Load: 48.05%
2026-05-16 00:31:14,893 [INFO] [CpuWorker] Current Load: 55.67%
2026-05-16 00:31:14,995 [CRITICAL] [CpuWorker] CPU Threshold Violated! (55.669999999999995%).
```

`evidence/raw/cpu-high.exit.txt`:

```text
# MEMORY_LIMIT=512 CPU_MAX_OCCUPY=100 MULTI_THREAD_ENABLE=false
pid=12321
exit_code=143
```

`143`은 일반적으로 `128 + 15`, 즉 SIGTERM 계열 종료로 해석한다. 앱 로그의 임계치 위반 직후 종료된 흐름과 일치한다.

### monitor.sh 및 시스템 도구
`evidence/raw/cpu-high.monitor.log`는 대상 PID가 종료 직전까지 살아 있다가 사라진 사실을 보여준다.

```text
2026-05-16 00:31:13,12323,SN,1,1.1,0.1,21692,32692,00:28,agent-app-leak
2026-05-16 00:31:14,12323,SN,1,1.1,0.1,21692,32692,00:29,agent-app-leak
2026-05-16 00:31:15,PID_NOT_FOUND,process=/Users/.../evidence/run_workspace/agent-app-leak
```

`evidence/raw/cpu-high-late.top.log`에서 OS 관점의 샘플도 저장했다.

```text
top - 00:32:31 up  8:03,  0 user,  load average: 0.00, 0.01, 0.00
%Cpu(s):  0.0 us,  0.0 sy,  6.6 ni, 93.4 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
  12964 f22loso+  30  10   32692  21656  11840 S   0.0   0.1   0:00.31 agent-a+
```

이번 앱은 `nice=10`으로 우선순위를 낮추고 내부적으로 부하를 시뮬레이션하기 때문에, OS의 1회성 `top` 샘플이 앱 내부 `Current Load` 수치와 완전히 같지는 않았다. 그래서 판단 근거는 앱 로그의 `Current Load` 증가와 종료 코드, monitor의 PID 소멸을 함께 묶어 해석했다.

### 비교 로그
`evidence/raw/cpu-low.app.log`:

```text
2026-05-16 00:29:52,019 [INFO] [CpuWorker] Started. Maximum CPU Limit: 10%
2026-05-16 00:29:54,121 [INFO] [CpuWorker] Peak reached (10.00%). Starting cooldown...
2026-05-16 00:29:57,226 [INFO] [CpuWorker] Cooldown complete (5.00%). Resuming load increase...
2026-05-16 00:30:19,958 [INFO] [CpuWorker] Current Load: 10.00%
```

`evidence/raw/cpu-low.exit.txt`:

```text
cleanup=SIGTERM
exit_code=143
```

`cpu-low`의 종료는 앱 자체 종료가 아니라 실습 스크립트가 관찰 종료 후 정리한 것이다. `cleanup=SIGTERM`이 그 차이를 보여준다.

## 3. Root Cause Analysis (원인 분석)
* **환경변수 `CPU_MAX_OCCUPY` 설정의 진실**: 
  - `CPU_MAX_OCCUPY=100`은 부하 발생 상한선을 최대로 개방하는 위험 설정입니다. 이에 따라 `CpuWorker` 내부 루프가 연산 간격을 좁혀 계산 밀도를 올리고 부하를 100%까지 지속해서 증폭시킵니다. 내부 부하가 감시 한계값인 약 50%를 넘자, 어플리케이션 내부 Watchdog이 임계치 파괴로 단정하고 시스템을 비상 종료시켰습니다.
  - 반면 `CPU_MAX_OCCUPY=10`은 내부 부하가 10%를 넘지 않도록 제한하는 안전 장치로 작동합니다. 부하가 10%에 도달하는 피크 시점마다 sleep 및 backoff 제어가 활성화되어 부하를 쿨다운(5%대) 시킵니다.
* **단일 프로세스 강제 종료(Watchdog)의 당위성**:
  CPU 자원은 한정되어 있으므로, 단일 프로세스가 CPU를 100%에 가깝게 점유하고 코어를 독점하면 OS의 **실행 큐(Run Queue)에 스케줄링 대기 상태의 다른 프로세스들이 극심하게 밀리게 됩니다.** 특히 실시간으로 가동되는 웹 서버 환경이라면, 이 시간 동안 쌓이는 웹 클라이언트의 TCP 요청들이 OS 소켓 백로그 큐나 WAS의 이벤트 처리 스레드 큐에 적체되는 **대기 큐 지연(Queueing Delay)**을 유발합니다. 이는 응답성 붕괴인 **테일 레이턴시(Tail Latency)의 폭증**으로 이어져 결국 커넥션 타임아웃 장애로 확산됩니다. 따라서 시스템 전반의 공멸을 막기 위해 폭주하는 단일 프로세스를 Watchdog이 선제 차단(Emergency Abort)하는 조치는 OS 스케줄링 및 가용성 관점에서 절대적으로 필요합니다.

## 4. Workaround & Verification (조치 및 검증)
임시 조치로 `CPU_MAX_OCCUPY`를 100에서 10으로 낮췄다.

### Before & After 대조 검증 표
| 항목 | Before (폭주 모드) | After (안전 모드) |
| :--- | :--- | :--- |
| 제어 변수 설정 | `CPU_MAX_OCCUPY=100` | `CPU_MAX_OCCUPY=10` |
| 감시 대상 PID | 12321 | 12340 (테스트 예시) |
| 내부 부하 변화 | 5% ➔ 55.67% 상승 후 즉시 임계치 위반 | 10% Peak 도달 시 즉시 Cooldown(5% 평탄화) 반복 |
| 프로세스 생사 여부 | 내부 감시견(Watchdog)에 의한 강제 소멸 | 35초 이상의 관찰 기간 동안 죽지 않고 정상 생존 |
| 종료 신호 및 exit_code | `exit_code=143` (SIGTERM 안전 차단) | `exit_code=143` (관찰 완료 후 스크립트 정리) |

* **근본 대책 (Code-level Remedy)**: CPU 집약적 연산을 처리하는 루프 내부에 명시적인 Backoff 주기와 `sleep`을 삽입하여 연산 속도를 물리적으로 제한해야 합니다. 나아가 실시간 요청을 응답해야 하는 주 스레드 루프 내에서 무거운 연산을 돌리지 말고, **메시지 큐(Celery, RabbitMQ 등)를 활용한 외부 연산 워커 노드 위임(Offloading) 아키텍처**로 전환하여 비블로킹(Non-blocking) I/O 구조를 완성해야 합니다.

