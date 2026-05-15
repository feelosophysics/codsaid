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
문제 조건은 `CPU_MAX_OCCUPY=100`이다. 앱은 부트 시 이 값을 “권장 50% 미만”보다 큰 위험 설정으로 판단했고, `CpuWorker`를 통해 부하를 계속 증가시켰다. 내부 부하가 약 55.67%까지 올라가자 앱의 보호 정책이 임계치 위반으로 판단하고 SIGTERM 계열 종료를 수행했다.

CPU 과점유는 시스템 전체 장애로 번질 수 있다. CPU를 많이 쓰는 단일 프로세스가 코어 시간을 독점하면 같은 서버의 다른 프로세스가 스케줄링될 기회를 늦게 얻고, 웹 서버에서는 요청 지연, 큐 적체, 타임아웃이 발생한다. 따라서 Watchdog이 단일 프로세스를 종료하는 것은 전체 시스템을 살리기 위한 보호 조치다.

## 4. Workaround & Verification (조치 및 검증)
임시 조치로 `CPU_MAX_OCCUPY`를 100에서 10으로 낮췄다.

| 항목 | Before | After |
| :--- | :--- | :--- |
| 설정 | `CPU_MAX_OCCUPY=100` | `CPU_MAX_OCCUPY=10` |
| 로그 패턴 | 5% → 55.67% 상승 후 임계치 위반 | 10% 도달 후 cooldown 반복 |
| 종료 여부 | 앱 자체 SIGTERM 계열 종료 | 관찰 종료 후 스크립트가 정리 |
| 핵심 로그 | `CPU Threshold Violated!` | `Peak reached`, `Cooldown complete` |

근본 해결은 CPU 집약 루프에 backoff, sleep, 작업량 제한, 큐 처리량 제한, 타임아웃, 비동기 작업 분리, 프로파일링 기반 알고리즘 개선을 적용하는 것이다.
