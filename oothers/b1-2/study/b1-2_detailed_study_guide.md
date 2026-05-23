# B1-2 리눅스 프로세스 및 시스템 리소스 트러블슈팅 초상세 학습 가이드

이 문서는 `mission_b1-2.md` 미션을 처음 공부하는 비기너가 “무슨 일이 일어났는지”, “왜 그런 판단을 했는지”, “어떤 명령어를 어떤 순서로 썼는지”, “리포트에는 무엇을 증거로 써야 하는지”를 끝까지 따라갈 수 있도록 작성한 학습 가이드다.

이번 미션의 핵심은 단순히 앱을 실행하는 것이 아니다. 앱이 비정상적으로 종료되거나, 느려지거나, 멈췄을 때 운영자/개발자처럼 증거를 수집하고 원인을 추론한 뒤 GitHub Issue 형식으로 소통 가능한 보고서를 만드는 것이다.

## 1. 최종 산출물 구조

이번 작업에서 만든 주요 파일은 다음과 같다.

```text
.
├── agent-app-leak
├── mission_b1-2.md
├── b1-2_detailed_study_guide.md
├── monitor.sh
├── scripts/
│   ├── monitor.sh
│   ├── run_agent_case.sh
│   └── capture_cpu_late.sh
├── reports/
│   ├── oom-crash.md
│   ├── cpu-latency.md
│   ├── deadlock.md
│   └── scheduling-analysis.md
└── evidence/
    ├── run_workspace/
    └── raw/
```

각 파일의 역할은 다음과 같다.

| 파일/디렉터리 | 역할 |
| :--- | :--- |
| `monitor.sh` | 루트에서 바로 실행할 수 있는 wrapper |
| `scripts/monitor.sh` | 실제 관제 스크립트. PID, CPU, MEM, RSS, VSZ, 스레드 상태를 기록한다. |
| `scripts/run_agent_case.sh` | 장애 케이스를 반복 실행하기 위한 보조 스크립트 |
| `scripts/capture_cpu_late.sh` | CPU 케이스의 종료 직전 `top`/`ps` 캡처를 보강하기 위한 스크립트 |
| `evidence/raw/*.log` | 실제 OrbStack Ubuntu에서 수집한 원본 증거 |
| `reports/*.md` | 제출 가능한 GitHub Issue 스타일 장애 리포트 |
| `reports/scheduling-analysis.md` | 보너스 과제인 스케줄링 알고리즘 추론 리포트 |

## 2. 이 미션의 큰 그림

운영 환경에서 장애가 발생하면 가장 위험한 습관은 “일단 재부팅”이다. 재부팅은 현상을 없앨 수 있지만 원인도 함께 지워 버린다. 같은 문제가 다시 발생했을 때 무엇을 봐야 하는지 알 수 없다.

이 미션은 세 가지 장애를 다룬다.

| 장애 | 겉으로 보이는 현상 | 실제로 봐야 하는 것 |
| :--- | :--- | :--- |
| OOM / Memory Leak | 프로세스가 갑자기 종료됨 | 메모리가 시간에 따라 증가했는가, 종료 직전 MemoryGuard 로그가 있는가 |
| CPU Spike / Latency | 응답이 느려지거나 프로세스가 종료됨 | 특정 프로세스의 CPU 부하가 임계치를 넘었는가 |
| Deadlock | 프로세스가 살아 있는데 아무 일도 안 함 | PID는 존재하지만 CPU/MEM/로그가 멈췄는가, 스레드가 서로의 락을 기다리는가 |

실무에서는 이 세 장애를 구분하는 능력이 매우 중요하다.

프로세스가 종료됐다면 OOM, crash, signal, watchdog 등을 의심한다. 프로세스가 살아 있는데 응답이 없으면 CPU 과점유, I/O 대기, deadlock, livelock 등을 의심한다. 메모리와 CPU 수치가 계속 변하면 “일하고 있는 상태”일 수 있고, 둘 다 정체되어 있으며 로그도 멈추면 “대기 상태”일 가능성이 크다.

## 3. 실행 환경 이해

사용자 PC는 iMac Intel이고, 실습은 OrbStack의 Ubuntu 가상환경에서 수행한다. 제공된 `agent-app-leak`는 macOS 실행 파일이 아니라 Linux x86-64 ELF 바이너리다.

확인한 파일 정보:

```text
agent-app-leak: ELF 64-bit LSB executable, x86-64, dynamically linked, for GNU/Linux
```

따라서 macOS 터미널에서 직접 실행하는 것이 아니라 OrbStack Ubuntu 안에서 실행해야 한다.

실제 실행 계정 확인:

```text
uid=1267600514(f22losophysics1091) gid=1267600514(...)
```

미션 조건 중 “root가 아닌 일반 사용자” 조건을 만족한다.

## 4. 부트 조건 이해

앱은 시작할 때 6단계 부트 체크를 수행한다.

```text
[1/6] Checking User Account
[2/6] Verifying Environment Variables
[3/6] Checking Required Files
[4/6] Checking Port Availability
[5/6] Verifying Log Permission
[6/6] Verifying Mission Environment
```

여기서 하나라도 실패하면 장애 분석을 시작하기 전에 앱이 종료된다. 그러면 그것은 OOM/CPU/Deadlock 장애가 아니라 “실행 환경 구성 실패”다.

필수 환경변수는 다음과 같다.

```bash
export AGENT_HOME="$PWD/evidence/run_workspace/agent_home"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys"
export AGENT_LOG_DIR="$AGENT_HOME/logs"
export MEMORY_LIMIT=50
export CPU_MAX_OCCUPY=100
export MULTI_THREAD_ENABLE=false
```

주의할 점이 있다. 쉘에서 같은 `export` 한 줄에 `AGENT_HOME=... AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"`처럼 쓰면, 환경에 따라 `AGENT_UPLOAD_DIR`가 새로 지정한 `AGENT_HOME`이 아니라 이전 값 또는 빈 값으로 확장될 수 있다. 그래서 이번 작업에서는 `scripts/run_agent_case.sh`에서 각 변수를 한 줄씩 순서대로 설정했다.

`secret.key`도 필수다.

```bash
mkdir -p "$AGENT_HOME/api_keys"
printf 'agent_api_key_test' > "$AGENT_HOME/api_keys/secret.key"
```

## 5. monitor.sh 설계와 명령어 의미

미션은 `monitor.sh`를 활용하라고 요구한다. 이번에 만든 `scripts/monitor.sh`는 다음 데이터를 수집한다.

```text
timestamp,pid,state,threads,cpu_percent,mem_percent,rss_kb,vsz_kb,etime,command
```

각 컬럼의 의미는 다음과 같다.

| 컬럼 | 의미 |
| :--- | :--- |
| `timestamp` | 관측 시각 |
| `pid` | 프로세스 ID |
| `state` | 프로세스 상태. `S`는 sleeping, `R`은 running, `l`은 multi-threaded를 뜻할 수 있다. |
| `threads` | 프로세스의 스레드 수 |
| `cpu_percent` | `ps` 기준 CPU 사용률 |
| `mem_percent` | 시스템 메모리 대비 사용 비율 |
| `rss_kb` | 실제 물리 메모리에 올라간 Resident Set Size |
| `vsz_kb` | 가상 메모리 크기 |
| `etime` | 프로세스 경과 시간 |
| `command` | 명령 이름 |

중요한 메모리 지표는 `RSS`다. `VSZ`는 가상 주소 공간이라 실제 RAM 사용량과 다를 수 있다. OOM 분석에서는 `RSS`가 더 직접적인 증거다.

사용한 핵심 명령어:

```bash
pgrep -f "$PROCESS_NAME"
ps -p "$pids" -o pid=,stat=,nlwp=,pcpu=,pmem=,rss=,vsz=,etime=,comm=
ps -L -p "$pids" -o pid,tid,stat,pcpu,pmem,comm
top -b -n 1 -p "$pids"
```

`pgrep -f`는 프로세스 이름뿐 아니라 전체 command line에서 패턴을 찾는다. PyInstaller로 패키징된 앱은 부모 프로세스와 실제 Python 자식 프로세스가 함께 뜰 수 있다. 처음에는 부모 PID만 보다가 실제 메모리 증가 자식을 놓쳤다. 그래서 `monitor.sh`는 특정 PID 하나가 아니라 `agent-app-leak` 전체 프로세스군을 추적하도록 보강했다.

`ps -L`은 스레드 단위 관찰에 중요하다. Deadlock에서는 프로세스가 하나만 있는 것처럼 보여도 내부 스레드가 서로 기다리는 상태일 수 있다.

## 6. OOM / Memory Leak 분석

### 6.1 관측 결과

Before 조건:

```text
MEMORY_LIMIT=50
CPU_MAX_OCCUPY=100
MULTI_THREAD_ENABLE=false
```

앱 로그:

```text
2026-05-16 00:28:59,292 [INFO] [MemoryWorker] Current Heap: 25MB
2026-05-16 00:29:02,321 [INFO] [MemoryWorker] Current Heap: 50MB
2026-05-16 00:29:02,321 [CRITICAL] [MemoryGuard] Memory limit exceeded (50MB >= 50MB)
2026-05-16 00:29:02,321 [CRITICAL] [MemoryGuard] Self-terminating process 11207 to prevent system instability.
```

monitor 로그:

```text
2026-05-16 00:28:58,11207,SN,1,8.0,0.1,21544,32692,00:01,agent-app-leak
2026-05-16 00:28:59,11207,SN,1,6.0,0.2,47148,58296,00:02,agent-app-leak
```

RSS가 약 21MB에서 약 47MB로 증가했다.

After 조건:

```text
MEMORY_LIMIT=100
CPU_MAX_OCCUPY=100
MULTI_THREAD_ENABLE=false
```

앱 로그:

```text
Current Heap: 25MB
Current Heap: 50MB
Current Heap: 75MB
Current Heap: 100MB
Memory limit exceeded (100MB >= 100MB)
```

monitor 로그:

```text
2026-05-16 00:29:18,11359,SN,1,7.2,0.1,21588,32692,00:01,agent-app-leak
2026-05-16 00:29:22,11359,SN,1,3.0,0.4,72796,83900,00:05,agent-app-leak
2026-05-16 00:29:25,11359,SN,1,2.2,0.5,98400,109504,00:08,agent-app-leak
```

### 6.2 판단 흐름

첫째, 부트 체크가 모두 통과했으므로 실행 환경 문제는 아니다.

둘째, 앱 로그의 `MemoryWorker Current Heap`이 25MB 단위로 증가한다.

셋째, monitor의 `rss_kb`도 함께 증가한다.

넷째, `Memory limit exceeded`와 `Self-terminating process`가 남는다.

다섯째, `MEMORY_LIMIT`를 50에서 100으로 올리면 생존 시간이 늘어난다.

이 다섯 가지가 합쳐져 “메모리 누수성 증가를 MemoryGuard가 감지해 종료했다”고 판단할 수 있다.

### 6.3 OS 관점 설명

프로세스는 가상 메모리 공간을 가진다. 하지만 실제로 RAM에 올라간 부분은 RSS로 관찰된다. 누수가 발생하면 사용이 끝난 객체를 해제하지 않아 참조가 계속 남고, GC나 메모리 해제가 일어나지 않으며 RSS가 증가한다.

메모리 누수가 심해지면 다음 문제가 생긴다.

1. 프로세스 자체가 느려진다.
2. 시스템 전체 free memory가 줄어든다.
3. swap이 늘어날 수 있다.
4. 커널 OOM Killer가 다른 중요한 프로세스를 죽일 수도 있다.
5. 장애 원인이 앱 하나였는데 서버 전체 장애로 번질 수 있다.

그래서 MemoryGuard는 해당 프로세스를 먼저 종료해 더 큰 장애를 막는다.

## 7. CPU Spike / Latency 분석

### 7.1 관측 결과

Before 조건:

```text
MEMORY_LIMIT=512
CPU_MAX_OCCUPY=100
MULTI_THREAD_ENABLE=false
```

앱 로그:

```text
2026-05-16 00:30:46,958 [INFO] [CpuWorker] Started. Maximum CPU Limit: 100%
2026-05-16 00:30:59,370 [INFO] [CpuWorker] Current Load: 27.05%
2026-05-16 00:31:05,580 [INFO] [CpuWorker] Current Load: 37.78%
2026-05-16 00:31:11,788 [INFO] [CpuWorker] Current Load: 48.05%
2026-05-16 00:31:14,893 [INFO] [CpuWorker] Current Load: 55.67%
2026-05-16 00:31:14,995 [CRITICAL] [CpuWorker] CPU Threshold Violated! (55.669999999999995%).
```

종료 코드:

```text
exit_code=143
```

`143 = 128 + 15`이므로 SIGTERM 종료로 볼 수 있다.

After 조건:

```text
MEMORY_LIMIT=512
CPU_MAX_OCCUPY=10
MULTI_THREAD_ENABLE=false
```

앱은 `Peak reached (10.00%). Starting cooldown...`과 `Cooldown complete`를 반복했고, 자체 종료는 일어나지 않았다. 실습 스크립트가 관찰 종료 후 정리했기 때문에 `cleanup=SIGTERM`이 남았다.

### 7.2 CPU_MAX_OCCUPY 해석

처음에는 `CPU_MAX_OCCUPY=10`이 낮은 임계치라서 더 쉽게 죽을 것처럼 보일 수 있다. 하지만 이 앱에서는 낮은 값이 “부하를 낮게 제한하는 안전 설정”으로 동작했다. 반대로 `CPU_MAX_OCCUPY=100`은 부하를 크게 허용하는 위험 설정이었고, 앱 내부 부하가 50%를 넘자 보호 정책이 종료를 수행했다.

이 지점이 이 미션에서 중요한 학습 포인트다. 환경변수 이름만 보고 의미를 단정하지 말고, 실제 로그를 보며 그 앱에서 어떻게 해석되는지 확인해야 한다.

### 7.3 OS 도구와 앱 내부 지표의 차이

`top`과 `ps`는 OS가 보는 순간 또는 누적 평균 CPU 사용률을 보여준다. 반면 앱 로그의 `Current Load`는 앱이 내부적으로 계산한 부하 지표일 수 있다.

이번 케이스에서는 `top`의 순간 `%CPU`가 낮게 잡혔다. 이유는 다음과 같이 추정할 수 있다.

1. 앱이 `nice=10`으로 우선순위를 낮췄다.
2. `top -n 1`은 순간 샘플이라 CPU peak를 놓칠 수 있다.
3. 앱의 `Current Load`는 실제 OS `%CPU`와 1:1 대응하지 않는 시뮬레이션 지표일 수 있다.

그래서 CPU 리포트에서는 앱 로그의 `Current Load` 증가, `CPU Threshold Violated`, 종료 코드, monitor의 PID 소멸을 함께 증거로 제시했다.

### 7.4 운영체제 관점 설명

CPU는 한정된 실행 자원이다. 프로세스가 CPU를 오래 점유하면 다른 프로세스가 실행될 기회를 늦게 얻는다. Linux 스케줄러가 공정성을 제공하더라도, CPU-bound 작업이 많으면 run queue가 길어지고 응답 시간이 늘어난다.

웹 서버라면 다음 문제가 생긴다.

1. 요청 처리 지연
2. 타임아웃 증가
3. 큐 적체
4. health check 실패
5. 오토스케일링 오판

그래서 Watchdog이 단일 프로세스를 종료하는 것은 “그 프로세스 하나를 살리는 것”보다 “서버 전체를 살리는 것”을 우선하는 정책이다.

## 8. Deadlock 분석

### 8.1 관측 결과

Before 조건:

```text
MEMORY_LIMIT=512
CPU_MAX_OCCUPY=10
MULTI_THREAD_ENABLE=true
```

앱 로그:

```text
Worker-Thread-1 LOCK ACQUIRED: [Shared_Memory_A]
Worker-Thread-2 LOCK ACQUIRED: [Socket_Pool_B]
Worker-Thread-1 Need resource [Socket_Pool_B] to finish job.
Worker-Thread-2 Need resource [Shared_Memory_A] to write logs.
Worker-Thread-2 WAITING for [Shared_Memory_A]... (Status: BLOCKED)
Worker-Thread-1 WAITING for [Socket_Pool_B]... (Status: BLOCKED)
```

monitor 로그:

```text
2026-05-16 00:33:21,12995,SNl,3,0.8,0.1,21696,180188,00:09,agent-app-leak
2026-05-16 00:33:28,12995,SNl,3,0.5,0.1,21696,180188,00:15,agent-app-leak
2026-05-16 00:33:38,12995,SNl,3,0.3,0.1,21696,180188,00:25,agent-app-leak
```

스레드 스냅샷:

```text
PID     TID STAT %CPU %MEM COMMAND
12995 13122 SNl   0.0  0.1 agent-app-leak
12995 13123 SNl   0.0  0.1 agent-app-leak
```

### 8.2 판단 흐름

Deadlock은 “프로세스가 죽은 것”이 아니다. 살아 있지만 진행하지 못하는 상태다.

판단 순서는 다음과 같다.

1. `ps -ef` 또는 monitor로 PID가 존재하는지 확인한다.
2. `ps -L`로 스레드가 존재하는지 확인한다.
3. CPU가 0.0에 가깝게 정체되어 있는지 확인한다.
4. RSS/VSZ가 거의 변하지 않는지 확인한다.
5. 앱 로그가 특정 지점 이후 멈췄는지 확인한다.
6. 마지막 로그가 `WAITING`, `BLOCKED`, `LOCK ACQUIRED`, `Need resource` 같은 락 대기 문맥인지 확인한다.
7. 두 스레드가 서로의 자원을 기다리는 순환 구조인지 그린다.

이번 케이스의 순환 구조:

```text
Worker-Thread-1
  holds Shared_Memory_A
  waits for Socket_Pool_B

Worker-Thread-2
  holds Socket_Pool_B
  waits for Shared_Memory_A
```

화살표로 쓰면 다음과 같다.

```text
Thread-1 -> Socket_Pool_B -> Thread-2 -> Shared_Memory_A -> Thread-1
```

### 8.3 교착상태 4대 조건

Deadlock은 보통 다음 네 조건이 동시에 만족될 때 발생한다.

| 조건 | 이번 미션에서의 의미 |
| :--- | :--- |
| 상호 배제 | `Shared_Memory_A`, `Socket_Pool_B`는 동시에 여러 스레드가 사용할 수 없다. |
| 점유 대기 | 각 스레드는 하나의 락을 잡은 채 다른 락을 기다린다. |
| 비선점 | 한 스레드가 가진 락을 다른 스레드가 강제로 빼앗지 못한다. |
| 순환 대기 | Thread-1과 Thread-2가 서로 상대방의 자원을 기다린다. |

### 8.4 회피 방법

임시 조치는 `MULTI_THREAD_ENABLE=false`다. 이 설정에서는 concurrent locking 시나리오가 실행되지 않고 정상 스케줄러가 실행된다.

근본 해결 방법은 다음과 같다.

1. 모든 스레드가 같은 순서로 락을 획득한다.
2. 락 획득에 timeout을 둔다.
3. timeout 발생 시 이미 잡은 락을 풀고 재시도한다.
4. 두 자원을 동시에 다뤄야 한다면 상위 단일 락을 둔다.
5. 락을 잡은 상태에서 네트워크, 파일 I/O, 로그 기록 같은 느린 작업을 하지 않는다.

## 9. 보너스: 스케줄링 알고리즘 추론

정상 실행 로그에서 다음 패턴이 보였다.

```text
Thread-A 20%
Thread-A 40%
Thread-A Preempted
Thread-B 20%
Thread-B 40%
Thread-B Preempted
Thread-C 20%
Thread-C 40%
Thread-C Preempted
Thread-A Resumed 60%
```

이 패턴은 FCFS가 아니다. FCFS라면 A가 100% 끝난 뒤 B가 시작해야 한다.

Priority도 아니다. 특정 스레드가 계속 우선 실행되는 편향이 없다.

가장 타당한 추론은 Round-Robin이다. 각 작업이 일정량 진행된 뒤 preempted 되고, 다음 작업으로 넘어가며, 나중에 saved progress에서 resumed 된다.

Round-Robin은 여러 작업에 공평한 응답 기회를 준다. 웹 서버처럼 응답성이 중요한 시스템에 어울린다. 단, 컨텍스트 전환 비용이 있고, 순수 처리량이 중요한 배치 작업에서는 최적이 아닐 수 있다.

## 10. 평가 문항 답변 가이드

이 섹션은 `mission_b1-2.md`에 추가된 평가 문항에 직접 답할 수 있도록 정리한 것이다.

### 항목 1: 필수 결과물 체크

#### OOM: 메모리 사용량이 선형적으로 증가하다가 프로세스가 강제 종료되는 패턴이 로그에 기록되어 있는가?

그렇다. `oom-high.app.log`에는 Heap이 25MB, 50MB, 75MB, 100MB로 증가한 뒤 `Memory limit exceeded`가 기록되어 있다. `oom-high.monitor.log`에는 PID `11359`의 RSS가 21588KB에서 72796KB, 98400KB로 증가했다.

#### OOM: MEMORY_LIMIT 조정 후 생존 시간이 늘어난 Before & After가 있는가?

그렇다. `MEMORY_LIMIT=50`에서는 약 5초 후 종료됐고, `MEMORY_LIMIT=100`에서는 약 11초 후 종료됐다. 상향 조정은 근본 해결은 아니지만 생존 시간을 늘리는 임시 조치임을 보여준다.

#### CPU: CPU 사용률이 임계치를 초과하여 프로세스가 종료되는 패턴이 로그에 기록되어 있는가?

그렇다. `cpu-high.app.log`에는 `Current Load`가 55.67%까지 상승한 뒤 `CPU Threshold Violated`가 기록되어 있다. 종료 코드는 `143`으로 SIGTERM 계열이다.

#### CPU: CPU_MAX_OCCUPY 조정 후 종료 여부/생존 시간이 변화했는가?

그렇다. `CPU_MAX_OCCUPY=100`에서는 앱 자체가 임계치 위반으로 종료됐다. `CPU_MAX_OCCUPY=10`에서는 cooldown을 반복하며 자체 종료가 발생하지 않았고, 실습 스크립트가 관찰 종료 후 정리했다.

#### Deadlock: PID는 살아 있으나 CPU/메모리 변화 없이 로그가 멈춘 상태를 식별했는가?

그렇다. `deadlock-on.monitor.log`에서 PID `12995`가 계속 존재하고, 스레드 CPU가 0.0에 가깝게 정체된다. 앱 로그는 `WAITING ... BLOCKED` 이후 진행되지 않는다.

#### Deadlock: MULTI_THREAD_ENABLE 조정 후 재현/회피 비교가 있는가?

그렇다. `true`에서는 Deadlock이 재현되고, `false`에서는 `Scheduler All tasks completed`가 나타나는 정상 흐름이 관측됐다.

#### Format: 3건의 리포트가 GitHub 구조를 갖추었는가?

그렇다. `reports/oom-crash.md`, `reports/cpu-latency.md`, `reports/deadlock.md`는 모두 Description, Evidence & Logs, Root Cause Analysis, Workaround & Verification 구조를 따른다.

#### Evidence: PID, 로그 타임스탬프, 핵심 로그 메시지가 포함되어 있는가?

그렇다. 각 리포트는 PID, 타임스탬프, 핵심 메시지인 `Memory limit exceeded`, `CPU Threshold Violated`, `WAITING ... BLOCKED`를 포함한다.

### 항목 2: 사용 도구와 판단 흐름

#### monitor.sh에서 메모리 증가 패턴을 추적하기 위해 사용한 명령어와 데이터 추출 방법은?

핵심 명령은 다음이다.

```bash
pgrep -f "$PROCESS_NAME"
ps -p "$pids" -o pid=,stat=,nlwp=,pcpu=,pmem=,rss=,vsz=,etime=,comm=
```

`pgrep -f`로 `agent-app-leak` 관련 부모/자식 PID를 모두 찾고, `ps`로 각 PID의 `rss`를 추출했다. RSS는 실제 물리 메모리 사용량에 가까운 지표라 메모리 누수 관찰에 적합하다.

#### CPU 사용률 확인을 위해 선택한 도구와 옵션의 의미는?

사용 도구는 `ps`, `top`, 앱 로그다.

`ps -p <pid> -o pcpu`는 프로세스 CPU 사용률을 보여준다. `top -b -n 1 -p <pid>`는 배치 모드로 한 번 샘플링하여 CPU/MEM을 보여준다. 앱 로그의 `Current Load`는 앱 내부 부하 지표다.

이번 케이스에서는 OS 샘플링 수치보다 앱 내부 `Current Load`가 장애 판단에 더 직접적이었다. 그래서 `CPU Threshold Violated` 로그와 종료 코드 `143`을 핵심 증거로 삼고, `top`/`ps`는 보조 증거로 사용했다.

#### 살아있지만 멈춰있는 상태를 진단하기 위해 어떤 도구를 어떤 순서로 사용했는가?

순서는 다음과 같다.

1. `ps -ef` 또는 monitor로 PID 존재 확인
2. `ps -L -p <pid>`로 스레드 존재 확인
3. monitor로 CPU/MEM 정체 확인
4. 앱 로그의 마지막 지점 확인
5. 마지막 로그의 락 획득/대기 관계를 표로 정리
6. 순환 대기 구조가 있는지 판단

이 순서가 중요한 이유는 Deadlock은 crash가 아니기 때문이다. 먼저 프로세스가 살아 있는지 확인하고, 살아 있는데 진행이 없는 이유를 스레드/락 관점에서 좁혀야 한다.

### 항목 3: 원리 설명

#### 메모리 누수가 발생했을 때 MemoryGuard가 프로세스를 종료하는 이유는?

메모리 누수는 시간이 지날수록 프로세스가 더 많은 RAM을 붙잡는 문제다. 방치하면 서버 전체 free memory가 줄고, swap이 늘고, 커널 OOM Killer가 발동할 수 있다. MemoryGuard는 장애 범위를 해당 프로세스로 제한하기 위해 미리 종료한다.

#### CPU 과점유 시 단일 프로세스를 종료하는 것이 시스템 보호에 왜 필요한가?

CPU를 과점유하는 프로세스는 다른 프로세스의 실행 기회를 빼앗는다. 웹 서버에서는 응답 지연과 타임아웃으로 이어진다. 단일 문제 프로세스를 종료하면 나머지 서비스의 CPU 시간을 확보할 수 있다.

#### Deadlock 원리를 상호 배제와 순환 대기로 설명하면?

상호 배제는 한 자원을 동시에 여러 스레드가 사용할 수 없다는 뜻이다. 순환 대기는 A가 B의 자원을 기다리고, B가 A의 자원을 기다리는 닫힌 고리다. 이번 미션에서는 Thread-1이 `Shared_Memory_A`를 잡고 `Socket_Pool_B`를 기다리며, Thread-2가 `Socket_Pool_B`를 잡고 `Shared_Memory_A`를 기다린다.

#### 로그에서 A->B, B->A 순환 의존 관계를 어떻게 파악했는가?

로그를 다음 두 질문으로 읽었다.

1. 각 스레드가 이미 잡은 자원은 무엇인가?
2. 각 스레드가 추가로 기다리는 자원은 무엇인가?

그 결과 Thread-1은 A를 보유하고 B를 요청하며, Thread-2는 B를 보유하고 A를 요청한다. 따라서 `Thread-1 -> B -> Thread-2 -> A -> Thread-1`의 순환이 만들어진다.

### 항목 4: 확장 사고 질문

#### 운영 서버에서 메모리 누수를 장애 전에 탐지하려면 monitor.sh를 어떻게 개선할 것인가?

다음 개선이 필요하다.

1. RSS 절대값뿐 아니라 증가율을 계산한다.
2. 최근 N분 동안 RSS가 계속 증가하면 경고한다.
3. 임계치 도달 전 70%, 85%, 95% 단계별 알림을 둔다.
4. 로그를 CSV나 JSON으로 저장해 Prometheus, Grafana, CloudWatch 같은 관제 시스템과 연동한다.
5. 프로세스 재시작 횟수와 종료 코드를 함께 기록한다.
6. PID가 바뀌어도 같은 서비스 이름 기준으로 추적한다.
7. `pmap`, `/proc/<pid>/smaps`, heap profiler와 연결해 어떤 영역이 커지는지 본다.

#### 세 장애 중 실제 서비스에서 가장 치명적인 것은 무엇인가?

상황에 따라 다르지만, 나는 Deadlock을 가장 치명적으로 본다. OOM과 CPU Spike는 종료나 경보로 드러나는 경우가 많다. Deadlock은 프로세스가 살아 있으므로 단순 health check가 “프로세스 존재”만 보면 정상으로 오판할 수 있다. 사용자는 응답을 못 받는데 운영자는 프로세스가 살아 있다고 착각할 수 있다.

예방 방법은 락 순서 규칙, timeout, deadlock detection, thread dump 수집, 요청 단위 timeout, synthetic transaction 기반 health check다.

#### OOM과 Deadlock이 동시에 발생했다면 어떤 순서로 트러블슈팅할 것인가?

먼저 시스템 안정성을 확인한다. free memory가 급격히 줄고 있다면 OOM 확산을 막기 위해 메모리 사용량이 큰 프로세스부터 격리하거나 재시작한다. 그 다음 Deadlock 여부를 본다.

하지만 이미 서비스 요청이 멈춰 있고 메모리는 안정적이라면 Deadlock을 먼저 본다. 판단 기준은 “지금 서버 전체를 죽일 위험이 큰가”와 “사용자 영향이 즉시 발생하는가”다.

실전 순서:

1. `free`, `top`, `ps aux --sort=-rss`로 시스템 메모리 압박 확인
2. 문제 PID 식별
3. 앱 로그에서 OOM/MemoryGuard 확인
4. PID가 살아 있다면 `ps -L`, thread dump, 마지막 로그 확인
5. 증거 저장 후 임시 조치
6. 코드 레벨 원인 분석

#### 환경변수 조정이 아니라 코드 수정이 가능하다면 어떻게 개선할 것인가?

OOM:

1. 누수되는 리스트, 딕셔너리, 캐시의 참조를 제거한다.
2. 캐시에 max size와 TTL을 둔다.
3. 큰 파일/데이터는 한 번에 메모리에 올리지 않고 streaming 처리한다.
4. 메모리 프로파일링을 CI나 부하 테스트에 포함한다.

CPU:

1. busy loop를 제거하고 sleep/backoff를 둔다.
2. CPU-heavy 작업을 큐와 worker pool로 분리한다.
3. 요청당 작업량과 실행 시간을 제한한다.
4. 알고리즘 복잡도를 개선한다.
5. 프로파일러로 hot path를 찾아 최적화한다.

Deadlock:

1. 락 획득 순서를 전역 규칙으로 통일한다.
2. lock timeout을 도입한다.
3. timeout 시 rollback하고 재시도한다.
4. 락을 잡은 상태로 외부 I/O를 하지 않는다.
5. thread dump와 lock graph를 관측 가능하게 만든다.

#### 다시 미션을 처음부터 수행한다면 무엇을 다르게 접근할 것인가?

처음부터 부모/자식 PID 구조를 의심하고 `pgrep -f`로 관련 프로세스를 모두 추적하겠다. PyInstaller 앱은 부트로더 부모와 Python 자식으로 나뉠 수 있기 때문이다.

또한 CPU 케이스에서는 `top -n 1` 한 번만 찍지 않고, `pidstat 1`, `top -d 1`, `/proc/<pid>/stat` 반복 샘플을 써서 peak를 놓치지 않도록 하겠다.

Deadlock 케이스에서는 로그가 멈춘 시점 직후에 `ps -L`을 더 명확히 저장하고, 가능하다면 Python thread dump 또는 `strace -p` 같은 도구로 futex 대기 여부까지 확인하겠다.

## 11. 제출 전 체크리스트

제출 전에 다음을 확인한다.

```text
[x] OOM 리포트에 메모리 증가 수치가 있는가
[x] OOM 리포트에 MemoryGuard 로그가 있는가
[x] OOM 리포트에 MEMORY_LIMIT Before & After가 있는가
[x] CPU 리포트에 CpuWorker 부하 증가와 임계치 위반 로그가 있는가
[x] CPU 리포트에 CPU_MAX_OCCUPY Before & After가 있는가
[x] Deadlock 리포트에 PID 존재와 스레드 정체 증거가 있는가
[x] Deadlock 리포트에 WAITING/BLOCKED 마지막 로그가 있는가
[x] Deadlock 리포트에 MULTI_THREAD_ENABLE 비교가 있는가
[x] 보너스 스케줄링 분석이 있는가
[x] 평가 문항 답변이 학습 가이드에 포함되어 있는가
```

## 12. 이번 미션을 통해 익혀야 할 핵심 감각

장애 분석은 정답 문장을 외우는 일이 아니다. 관측값을 모아 가능한 원인을 좁히는 일이다.

좋은 분석은 다음 형태를 가진다.

```text
현상: 무엇이 보였는가
증거: 어떤 로그/명령어 출력이 있는가
해석: 그 증거가 왜 그 원인을 가리키는가
조치: 무엇을 바꿨는가
검증: 바꾼 뒤 무엇이 달라졌는가
한계: 임시 조치와 근본 해결은 어떻게 다른가
```

이번 미션에서 가장 중요한 배움은 “프로세스가 종료됐다”, “CPU가 높다”, “멈췄다” 같은 말만으로는 충분하지 않다는 점이다. PID, 타임스탬프, 로그 메시지, 수치 변화, Before & After가 함께 있어야 동료가 재현하고 검증할 수 있는 리포트가 된다.