# [Bug] OOM Crash - MemoryGuard가 메모리 누수 증가를 감지하고 프로세스를 강제 종료

## 1. Description (현상 설명)
`agent-app-leak`를 `MEMORY_LIMIT=50`으로 실행하면 프로세스가 약 5초 뒤 종료된다. 앱 로그에는 `MemoryWorker`의 Heap 사용량이 25MB에서 50MB로 증가한 뒤, `MemoryGuard`가 임계치 초과를 감지하고 self-termination을 수행한 기록이 남았다.

비교 실행에서 `MEMORY_LIMIT=100`으로 상향하자 종료 시점이 약 11초 뒤로 늦춰졌다. 따라서 종료 원인은 실행 실패나 포트 문제라기보다, 시간 경과에 따라 누적되는 메모리 사용량이 앱 내부 보호 한계에 도달한 것이다.

## 2. Evidence & Logs (증거 자료)

### 실행 조건
| 구분 | MEMORY_LIMIT | CPU_MAX_OCCUPY | MULTI_THREAD_ENABLE | 결과 |
| :--- | :--- | :--- | :--- | :--- |
| Before | 50MB | 100% | false | 약 5초 후 MemoryGuard 종료 |
| After | 100MB | 100% | false | 약 11초 후 MemoryGuard 종료 |

### monitor.sh 관제 로그
`evidence/raw/oom-low.monitor.log`에서 실제 Python 자식 프로세스 PID `11207`의 RSS가 증가했다.

```text
2026-05-16 00:28:58,11207,SN,1,8.0,0.1,21544,32692,00:01,agent-app-leak
2026-05-16 00:28:59,11207,SN,1,6.0,0.2,47148,58296,00:02,agent-app-leak
2026-05-16 00:29:00,11207,SN,1,4.1,0.2,47148,58296,00:03,agent-app-leak
2026-05-16 00:29:02,PID_NOT_FOUND,process=/Users/.../evidence/run_workspace/agent-app-leak
```

`evidence/raw/oom-high.monitor.log`에서는 PID `11359`의 RSS가 더 오래 증가했다.

```text
2026-05-16 00:29:18,11359,SN,1,7.2,0.1,21588,32692,00:01,agent-app-leak
2026-05-16 00:29:22,11359,SN,1,3.0,0.4,72796,83900,00:05,agent-app-leak
2026-05-16 00:29:25,11359,SN,1,2.2,0.5,98400,109504,00:08,agent-app-leak
2026-05-16 00:29:28,PID_NOT_FOUND,process=/Users/.../evidence/run_workspace/agent-app-leak
```

### 애플리케이션 로그
Before 로그:

```text
2026-05-16 00:28:59,292 [INFO] [MemoryWorker] Current Heap: 25MB
2026-05-16 00:29:02,321 [INFO] [MemoryWorker] Current Heap: 50MB
2026-05-16 00:29:02,321 [CRITICAL] [MemoryGuard] Memory limit exceeded (50MB >= 50MB) / (Recommend Over 256MB)
2026-05-16 00:29:02,321 [CRITICAL] [MemoryGuard] Self-terminating process 11207 to prevent system instability.
```

After 로그:

```text
2026-05-16 00:29:19,720 [INFO] [MemoryWorker] Current Heap: 25MB
2026-05-16 00:29:22,757 [INFO] [MemoryWorker] Current Heap: 50MB
2026-05-16 00:29:25,795 [INFO] [MemoryWorker] Current Heap: 75MB
2026-05-16 00:29:28,832 [INFO] [MemoryWorker] Current Heap: 100MB
2026-05-16 00:29:28,832 [CRITICAL] [MemoryGuard] Memory limit exceeded (100MB >= 100MB) / (Recommend Over 256MB)
2026-05-16 00:29:28,833 [CRITICAL] [MemoryGuard] Self-terminating process 11359 to prevent system instability.
```

### 종료 코드
```text
oom-low:  exit_code=137
oom-high: exit_code=137
```

`137`은 일반적으로 `128 + 9`, 즉 SIGKILL 계열 종료로 해석한다. 앱 로그의 `Self-terminating process`와 함께 보면 MemoryGuard가 보호 목적의 강제 종료를 수행한 것으로 볼 수 있다.

## 3. Root Cause Analysis (원인 분석)
관측된 핵심 패턴은 “Heap 증가 → RSS 증가 → MEMORY_LIMIT 도달 → MemoryGuard 종료”이다.

앱 내부의 `MemoryWorker`는 약 3초 간격으로 Heap을 25MB씩 증가시키는 동작을 보였다. 정상적인 프로그램이라면 사용이 끝난 객체를 해제하거나 재사용해야 하지만, 이 앱은 미션용으로 메모리를 계속 보유한다. 그 결과 프로세스의 물리 메모리 사용량인 RSS가 증가한다.

MemoryGuard는 프로세스가 설정된 `MEMORY_LIMIT` 이상으로 커지면 시스템 전체 불안정을 막기 위해 해당 프로세스를 종료한다. 운영 서버에서 이런 보호 장치가 없다면 프로세스가 계속 메모리를 점유해 스왑 증가, 응답 지연, 커널 OOM Killer 발동으로 이어질 수 있다.

## 4. Workaround & Verification (조치 및 검증)
임시 조치로 `MEMORY_LIMIT`를 50MB에서 100MB로 상향했다.

| 항목 | Before | After |
| :--- | :--- | :--- |
| 설정 | `MEMORY_LIMIT=50` | `MEMORY_LIMIT=100` |
| Heap 로그 | 25MB, 50MB | 25MB, 50MB, 75MB, 100MB |
| 주요 PID | 11207 | 11359 |
| 종료 시점 | 약 5초 | 약 11초 |
| 종료 사유 | MemoryGuard | MemoryGuard |

검증 결과 생존 시간은 늘었지만, 근본 원인은 사라지지 않았다. 운영 코드라면 누수 객체의 참조를 제거하고, 캐시 상한을 두고, 큰 버퍼를 스트리밍 방식으로 처리하며, 장기 실행 시 RSS 증가율을 경보로 감시해야 한다.
