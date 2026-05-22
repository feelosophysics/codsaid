# 🚀 시스템 관제 자동화 스크립트 개발 프로젝트 (Agent Mission)

> 본 문서는 다중 사용자 환경에서의 정밀한 권한 제어, 네트워크 보안 강화, 백그라운드 애플리케이션의 안정적 구동, 그리고 시스템 리소스 관제 및 로그 수집/보존 정책 자동화를 다루는 리눅스 시스템 엔지니어링 프로젝트에 대한 종합 안내서입니다.

---

## 1. 프로젝트 개요(미션 목표 요약)

본 프로젝트는 현업에서 발생할 수 있는 서버 장애 상황에 대비하여, 시스템 상태를 실시간으로 모니터링하고 기록하여 문제를 신속하게 추적할 수 있도록 지원하는 **'시스템 관제 자동화 솔루션'** 개발을 목표로 합니다.

### 🎯 핵심 미션 목표
* **다중 사용자 권한 체계 구축**: 역할 기반 계정(`agent-admin`, `agent-dev`, `agent-test`)과 협업 그룹(`agent-common`, `agent-core`)을 생성하고, 공유/보안 디렉토리를 분리하여 최소 권한 원칙을 실현합니다.
* **네트워크 보안 강화**: SSH 접속 포트 변경(22 → 20022), Root 원격 접속 차단, UFW 방화벽 설정을 통해 필요한 외부 포트(`20022`, `15034`)만 허용하는 화이트리스트 기반 네트워크 보안을 구축합니다.
* **실행 환경 격리 및 표준화**: 일반 서비스 계정(`agent-admin`)으로 애플리케이션을 안전하게 구동하고, 환경 변수를 표준화하여 다중 환경에서의 일관성을 확보합니다.
* **관제 자동화 및 로그 라이프사이클 관리**:
  * `monitor.sh`: 프로세스/포트 Health Check, 리소스 사용량(CPU/MEM/DISK) 수집 및 자체 로그 롤오버(10MB * 10개 파일)를 수행하는 Bash 스크립트 구현.
  * `report.sh` (보너스 1): 로그 데이터를 분석하여 통계(평균/최대/최소) 및 특정 구간 분석 기능 구현.
  * `archive.sh` (보너스 2): 7일 경과 로그 압축 보존 및 30일 경과 아카이브 자동 삭제 기능 구현.

---

## 2. 실행 환경(OS/쉘/터미널, Git 버전)

본 프로젝트는 다음의 시스템 및 개발 환경에서 검증 및 운영되었습니다.

* **대상 운영체제 (OS)**: Ubuntu 24.04 LTS
* **사용 쉘 (Shell)**: Bash (`/bin/bash`)
* **터미널 환경**: 표준 Unix Terminal (zsh, bash 호환)
* **Git 버전**: `git version 2.53.0`
* **시스템 계정 및 그룹 구성**:
  | 구분 | 계정/그룹명 | 역할 및 권한 범위 | 소속 멤버 |
  | :--- | :--- | :--- | :--- |
  | **계정** | `agent-admin` | 시스템 운영 및 관리자 (cron 배치 실행자) | - |
  | | `agent-dev` | 개발자 (관제 스크립트 `monitor.sh` 작성자) | - |
  | | `agent-test` | QA 및 테스터 | - |
  | **그룹** | `agent-common` | 공용 파일 영역 접근 그룹 | `agent-admin`, `agent-dev`, `agent-test` |
  | | `agent-core` | 핵심 시스템/로그 및 비밀키 접근 그룹 | `agent-admin`, `agent-dev` |

---

## 3. 수행 항목 체크리스트

| 수행 대분류 | 세부 수행 요구사항 | 구현 상태 | 확인 방법 및 증거 자료 |
| :--- | :--- | :---: | :--- |
| **0. 시스템 의존성 패키지** | `openssh-server`, `ufw`, `acl`, `file` 자동 설치 | `완료 (OK)` | `setup.sh` 실행 시 `dpkg` 및 `command -v`로 검사 후 자동 설치 |
| **1. 기본 보안 & 네트워크** | SSH 접속 포트를 `20022`로 변경 | `완료 (OK)` | `/etc/ssh/sshd_config` 내 `Port 20022` 설정 및 데몬 리슨 확인 |
| | Root 계정의 원격 로그인 차단 | `완료 (OK)` | `/etc/ssh/sshd_config` 내 `PermitRootLogin no` 설정 확인 |
| | UFW 방화벽 활성화 및 인바운드 기본 차단 | `완료 (OK)` | `sudo ufw status verbose` (Status: active, Default: deny incoming) |
| | 허용 포트 제한 (`20022/tcp`, `15034/tcp`만) | `완료 (OK)` | `scrs/ufw_status.png` 증거 확인 |
| **2. 계정/그룹/권한 체계** | 3개 역할 기반 계정 및 2개 보안 그룹 생성 | `완료 (OK)` | `id` 명령어를 통한 그룹 소속 관계 매핑 검증 |
| | `$AGENT_HOME` 및 하위 디렉토리 구조 설계 | `완료 (OK)` | `/home/agent-admin/agent-app` 디렉토리 구성 완료 |
| | `upload_files` 공용 R/W 권한 부여 | `완료 (OK)` | SetGID (`2770`) 및 `agent-common` ACL 대물림 설정 (`getfacl`로 확인) |
| | `api_keys` 및 로그 디렉토리 R/W 제한 | `완료 (OK)` | SetGID (`2770`) 및 `agent-core` 전용 권한/ACL 설정 (`test` 계정 차단) |
| **3. 앱 실행 환경 구성** | 핵심 실행 환경 변수 5종 정의 및 배포 | `완료 (OK)` | `.bashrc` 및 `/etc/environment` 등록 확인 |
| | API 키 파일 (`t_secret.key`) 보안 생성 | `완료 (OK)` | `640` 권한 부여 및 `agent_api_key_test` 문자열 기록 검증 |
| | 일반 계정(`agent-admin`) 구동 및 부팅 검증 | `완료 (OK)` | Boot Sequence 5단계 `[OK]` 완료 및 `Agent READY` 콘솔 출력 검증 |
| | 애플리케이션 `15034/tcp` 포트 리슨 검증 | `완료 (OK)` | `ss -tulnp \| grep 15034` 실행 시 프로세스 매핑 확인 |
| **4. 시스템 관제 자동화** | `monitor.sh` 경로 및 실행 권한 적용 | `완료 (OK)` | 소유자 `agent-dev`, 그룹 `agent-core`, 권한 `750` 적용 완료 |
| | 프로세스 & 포트 Health Check 기능 구현 | `완료 (OK)` | 정상 작동 시 `[OK]` 출력, 비정상 상태 감지 시 `exit 1` 및 에러 로깅 |
| | 방화벽 활성화 상태 상시 체크 | `완료 (OK)` | UFW/firewalld 미작동 시 스크립트는 지속하되 `[WARNING]` 출력 |
| | CPU/MEM/DISK 리소스 실시간 수집 | `완료 (OK)` | `top`, `free`, `df` 명령 기반 정확한 소수점 파싱 및 백분율 수집 |
| | 임계치 경고 (CPU>20%, MEM>10%, DISK>80%) | `완료 (OK)` | 임계치 초과 시 `[WARNING]`을 콘솔 및 로그에 기록 |
| | 로그 포맷 정규화 및 자체 용량 관리 (롤오버) | `완료 (OK)` | 표준 포맷 로깅 및 10MB 크기 기준 최대 10개 파일 백업 기능 (`rotate_log`) |
| **5. 자동 실행 및 배치** | crontab 매분 주기 실행 등록 및 동작 확인 | `완료 (OK)` | `scrs/monitor_log.png`를 통한 매분 단위 타임스탬프 적재 완료 증빙 |
| **6. 보너스 수행 (선택)** | `report.sh`: 로그 통계 및 구간 분석 리포트 | `완료 (OK)` | 평균/최대/최소 자원 사용량 분석 및 `scrs/statistics_report.png` 증빙 |
| | `archive.sh`: 시간 기반 로그 압축/삭제 정책 | `완료 (OK)` | 7일 경과 로그 gzip 압축 후 아카이브 이동, 30일 경과 아카이브 자동 삭제 |

---

## 4. 검증 방법

구축된 시스템 보안 및 모니터링 환경의 무결성을 검증하기 위한 상세 가이드는 다음과 같습니다.

### 4.1 시스템 환경 설정 검증
1. **SSH 보안 설정 검증**:
   ```bash
   # 포트 변경 및 Root 로그인 제한 여부 확인
   grep -E "^Port|^PermitRootLogin" /etc/ssh/sshd_config
   # [출력 기준] Port 20022 및 PermitRootLogin no가 보여야 합니다.
   
   # SSH 서비스가 20022 포트에서 리슨 중인지 확인
   ss -tulnp | grep -E "sshd|ssh"
   ```
2. **방화벽(UFW) 정책 검증**:
   ```bash
   # ufw 활성화 및 포트 규칙 세부 사항 확인
   sudo ufw status verbose
   # [검증 기준] Status: active, 20022/tcp 및 15034/tcp ALLOW Anywhere가 확인되어야 함 (scrs/ufw_status.png)
   ```
3. **계정 권한 및 ACL 대물림 검증**:
   ```bash
   # 계정별 그룹 소속 상태 확인
   id agent-admin  # (agent-common, agent-core 모두 소속)
   id agent-dev    # (agent-common, agent-core 모두 소속)
   id agent-test   # (agent-common만 소속, agent-core 배제)
   
   # 디렉토리 권한 및 ACL 규칙 확인
   getfacl /home/agent-admin/agent-app/upload_files
   # [검증 기준] group:agent-common:rwx 및 default:group:agent-common:rwx가 포함되어야 함
   
   getfacl /home/agent-admin/agent-app/api_keys
   # [검증 기준] group:agent-core:rwx 및 default:group:agent-core:rwx가 포함되어야 함 (test 계정 접근 차단)
   ```

### 4.2 애플리케이션 및 모니터링 동작 검증
1. **애플리케이션 구동 검증**:
   ```bash
   # 일반 운영 계정으로 안전하게 구동
   sudo -u agent-admin bash -l -c 'cd /home/agent-admin/agent-app && ./agent-app'
   # [검증 기준] Boot Sequence 5단계 [OK] 및 'Agent READY' 문구가 정상 출력되는지 확인
   ```
2. **모니터링 스크립트(monitor.sh) 수동 실행**:
   ```bash
   # 운영 계정 권한으로 수동 실행하여 관제 상태 진단
   sudo -u agent-admin bash -l -c '/home/agent-admin/agent-app/bin/monitor.sh'
   # [검증 기준] HEALTH CHECK 및 RESOURCE MONITORING 정보가 정해진 템플릿 형태로 출력되는지 확인
   ```
3. **자동 실행 배치(cron) 검증**:
   ```bash
   # crontab 등록 내용 확인
   sudo -u agent-admin crontab -l
   # [검증 기준] "* * * * * . /etc/environment; /home/agent-admin/agent-app/bin/monitor.sh >> /tmp/cron.log 2>&1" 확인
   
   # 로그 파일이 실시간으로 증가하는지 확인
   tail -f /var/log/agent-app/monitor.log
   # [검증 기준] 매 1분마다 타임스탬프가 갱신되며 리소스 한 줄 일지가 계속 적재되는지 확인 (scrs/monitor_log.png)
   ```

### 4.3 보너스 스크립트 검증
1. **통계 분석 리포트(report.sh) 실행**:
   ```bash
   # 전체 로그 통계 분석
   /home/agent-admin/agent-app/bin/report.sh
   
   # 특정 일시 구간(시작~종료) 지정 분석
   /home/agent-admin/agent-app/bin/report.sh "2026-05-13 17:00:00" "2026-05-13 18:00:00"
   # [검증 기준] CPU, Memory, Disk의 평균/최대/최소값과 수집된 샘플 수가 포맷에 맞추어 콘솔에 예쁘게 출력되어야 함
   ```
2. **로그 보존/아카이빙(archive.sh) 실행**:
   ```bash
   # 아카이빙 정책 수동 호출 테스트
   /home/agent-admin/agent-app/bin/archive.sh
   # [검증 기준] 7일 초과 로그가 gzip(.gz)으로 자동 압축된 후 archive 폴더로 이동되고, 30일 경과 아카이브가 자동 영구 삭제되는지 터미널 메시지로 확인
   ```

---

## 5. 트러블슈팅

본 시스템을 개발하고 모니터링 환경을 튜닝하는 과정에서 발생한 핵심 이슈들과 해결 기법입니다.

### 📌 ISSUE 1: OS 환경에 따른 CPU Idle 값 파싱 에러 (정규식 고도화)
* **문제 상황**: 모니터링 스크립트 `monitor.sh`에서 CPU 사용량을 얻기 위해 `top` 명령어와 `awk`를 사용하였으나, 테스트 환경과 운영 VM의 `top` 출력 포맷(콤마 위치 및 공백 수) 차이로 인해 CPU 사용률이 비어 있거나 `100%`로 잘못 오인되는 버그가 발생했습니다.
* **해결 방안**: 정규표현식 파서 도구인 `sed`를 적용하여 `Cpu(s)` 행에서 문자 패턴과 상관없이 오직 `id` 문자 앞에 붙어 있는 순수 부동소수점 값을 고도로 발췌해 내는 정규식을 설계했습니다.
  ```bash
  # 고도화된 2중 sed 파싱 로직 적용
  CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed -n 's/.*, *\([0-9.]*\) *id.*/\1/p')
  if [ -z "$CPU_IDLE" ]; then
      CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed 's/.*,\s*\([0-9.]*\)\s*id.*/\1/')
  fi
  ```
  이 방식을 적용하여 어떤 OS 배포판에서도 흔들림 없이 소수점 단위의 CPU 사용률을 정확하게 역산(`100 - CPU_IDLE`)할 수 있도록 튜닝을 완료했습니다.

### 📌 ISSUE 2: setup.sh의 선행 의존성 패키지 부재 및 멱등성 결여 이슈
* **문제 상황**: `setup.sh`를 실행할 때, `openssh-server`, `ufw`, `acl`, `file` 등 필수 리눅스 패키지가 서버에 사전에 깔려있지 않아 여러 단계에서 `command not found` 오류가 발생하고 파일 미존재 오류가 발생했습니다. 또한, 스크립트를 여러 번 연속 실행 시 `.bashrc`와 `/etc/environment` 파일 하단에 중복 환경 변수가 지저분하게 계속 덧붙는 멱등성 결여 문제와 주석 실수 버그로 `crontab: invalid option`이 터지는 아키텍처적 불안정성이 드러났습니다.
* **해결 방안**:
  * **[1단계] 시스템 의존성 자동 확인 및 설치** 루틴을 맨 앞에 전격 탑재했습니다. `dpkg` 및 `command -v`를 이용하여 필수 패키지가 없을 시 `apt-get`으로 자동 확인 및 선행 설치하게 구현했습니다.
  * **환경 변수 주입 멱등성 보장**: `grep` 사전 필터링 로직을 장착하여 이미 환경 변수 블록이 적혀있다면 중복 삽입하지 않고 안전하게 스킵되도록 조치했습니다.
  * **바이너리 유연 탐색 및 버그 척결**: `/tmp/`에 한정되어 있던 바이너리 탐색 위치를 실행 경로 및 부모 디렉토리까지 자동으로 뒤져 안전하게 배치하도록 하고, 설명 문법 버그(`crontab -e:`)를 전원 제거하여 완벽한 안정성을 달성했습니다.

### 📌 ISSUE 3: Ubuntu 22.10+ / 24.04 LTS의 systemd 소켓 활성화(Socket Activation)로 인한 SSH 포트 고정 현상
* **문제 상황**: `/etc/ssh/sshd_config` 내에 `Port 20022`를 정상적으로 세팅하고 SSH 데몬 서비스를 재시작했음에도 불구하고, `ss -tlnp`로 열려 있는 포트를 조회하면 기존의 `22` 포트가 완강하게 유지되는 현상이 발생했습니다. 소켓 상태 분석 시 프로세스 란에 `sshd`뿐 아니라 마스터 프로세스인 `systemd (PID 1)`가 해당 포트의 파일 디스크립터를 공유 점유하고 있음이 기술적으로 포착되었습니다.
* **해결 방안**: 최신 Ubuntu 배포판이 지원하는 systemd 소켓 활성화(`ssh.socket`) 유닛이 `22` 포트를 커널 수준에서 선점 관리하여 생기는 현상임을 확인했습니다. `setup.sh` 내에 `ssh.socket`의 활성화 여부를 스스로 감지(`systemctl is-active --quiet ssh.socket`)하는 엔진을 구현하여, 감지 시 `ssh.socket`을 정지 및 영구 비활성화 처리하고 `ssh.service` 독립 상주형 서비스로 멱등하게 자동 리다이렉트 기동함으로써 20022 포트 전환의 자동화를 완벽히 성취했습니다.

### 📌 ISSUE 4: 시연 및 검증 시 실 운영 데이터 소실 방지 조치 (Non-destructive Testbed)
* **문제 상황**: 보너스 미션(`archive.sh`, `report.sh`)의 동작을 시연하기 위해 가상 테스트 데이터를 빌드하는 과정에서, 기존 관제 디렉토리를 함부로 강제 재생성(포맷)하거나 원본 실시간 로그 파일(`monitor.log`)을 덮어쓰게 될 경우, 기존에 장기간 정상적으로 쌓아 올린 시계열 실 운영 로그 이력이 영구 소실되어 버릴 보안상의 심각한 위협이 존재했습니다.
* **해결 방안**: 시연용 제너레이터 룰에서 비파괴적(Non-destructive) 검증 메커니즘을 전격 채택하였습니다.
  * 디렉토리 생성 단계에서는 기존에 축적된 디렉토리를 전면 포맷(rm -rf 등)하지 않고 안전하게 보존하기 위해 `mkdir -p`로만 안전 구조를 다듬습니다.
  * 7일 경과 압축 시연에서는 실 운영 로그 파일인 `monitor.log`를 임의로 훼손하지 않기 위해, 오직 시연 목적으로 탄생한 **가상의 단독 타겟 파일(`test_history.log`)**을 독립 `touch` 생성하여 실 운영 이력에 전혀 영향을 미치지 않고도 아카이빙 시나리오를 깨끗하게 검증할 수 있도록 설계했습니다.
  * 3분 자원 스파이크 분석 시연 시에도 기존 로그를 삭제하지 않고, 기 구축된 `monitor.log` 파일의 맨 마지막 오프셋 꼬리에 추가 누적 어펜드(`>>`)하는 방식으로 더미를 삽입하여 기존 관제 데이터의 무결성을 영구 보존하며 안전하게 통계 마이닝을 검증하도록 보강했습니다.