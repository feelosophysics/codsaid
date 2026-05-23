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
* **메모리 누수(Memory Leak) 결함**: `MemoryWorker` 모듈이 특정 트랜잭션을 시뮬레이션하면서 힙(Heap) 영역에 지속해서 25MB 단위의 메모리를 할당하지만, 할당 완료된 메모리 객체의 전역 참조 관계(Reference Link)를 해제하지 않는 결함이 존재합니다. 이로 인해 Python 런타임의 가비지 컬렉터(GC)가 해당 메모리를 회수(Reclaim)하지 못하고 가용 실제 RAM이 지속해서 잠식되는 현상이 발생합니다.
* **자가 보호 장치의 작동 이유**: 물리 메모리 점유량(RSS)이 환경변수로 입력된 `MEMORY_LIMIT`에 도달하면 애플리케이션의 내부 감시 정책인 **`MemoryGuard`**가 이를 감지합니다. 만약 이 프로세스가 계속 방치되어 OS의 전체 가용 메모리를 고갈시킨다면, 리눅스 커널의 **`OOM Killer`**가 활성화되어 엉뚱한 핵심 서비스 데몬(예: 데이터베이스, SSH 등)을 무차별 강제 종료시켜 전체 서버 가동성을 마비시킵니다. 따라서 `MemoryGuard`는 장애 범위를 해당 어플리케이션 내부로 완전히 차단 및 격리(Fault Isolation)하기 위해 스스로 `SIGKILL`을 호출하여 선제 자폭한 것입니다.

## 4. Workaround & Verification (조치 및 검증)
임시 조치로 `MEMORY_LIMIT`를 50MB에서 100MB로 상향했다.

### Before & After 대조 검증 표
| 항목 | Before | After |
| :--- | :--- | :--- |
| 설정 변수 | `MEMORY_LIMIT=50` | `MEMORY_LIMIT=100` |
| Heap 로그 추이 | 25MB ➔ 50MB (자폭) | 25MB ➔ 50MB ➔ 75MB ➔ 100MB (자폭) |
| 감시 대상 PID | 11207 | 11359 |
| 생존 지속 시간 | 약 5초 | 약 11초 (수명 약 2.2배 선형 연장) |
| 종료 신호 및 exit_code | `exit_code=137` (SIGKILL 자폭) | `exit_code=137` (SIGKILL 자폭) |

* **물리 메모리(RSS) 선형적 우상향 검증**:
  - `low` 케이스: RSS가 21,544 KB (가동 1초) ➔ 47,148 KB (가동 2초)로 1초 만에 약 25.6MB 급증하는 메모리 누설 속도 관측.
  - `high` 케이스: RSS가 21,588 KB (가동 1초) ➔ 72,796 KB (가동 5초) ➔ 98,400 KB (가동 8초)로 선형적으로 꾸준히 증가하다가 100MB 임계값에 상응하는 시점에 정확히 소멸.
* **근본 대책 (Code-level Remedy)**: 환경변수 조정을 통한 임시방편은 메모리 누수 속도를 늦출 뿐 근본 해결책이 아닙니다. 소스 코드 상에서 미사용 메모리 객체의 전역 참조를 명시적으로 파괴(파이썬의 `del` 처리 혹은 컬렉션의 `clear()` / `pop()` 유도)하여 GC가 메모리를 제때 수집할 수 있도록 리팩토링해야 합니다.

