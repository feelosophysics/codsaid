# 🎓 리눅스 서버 운영 미션: 완전 학습 가이드

이 문서는 `mission.md`의 요구사항을 바탕으로 우리가 구축한 시스템의 **'왜(Why)'**와 **'어떻게(How)'**를 설명합니다. 이 가이드를 통해 서버 엔지니어의 핵심 역량을 학습해 보세요.

---

## 🗺️ 전체 구축 로드맵 (Roadmap)

우리는 아래의 5단계를 거쳐 현업 수준의 서버 환경을 완성했습니다.

1.  **Infrastructure**: OrbStack을 이용한 Ubuntu 24.04 환경 준비
2.  **Hardening (보안 강화)**: SSH 포트 변경 및 방화벽 설정
3.  **IAM (계정 및 권한)**: 역할 기반 그룹(RBAC) 및 ACL 설정
4.  **Deployment (앱 배포)**: 환경 변수 설정 및 바이너리 실행
5.  **Observability (관제 자동화)**: 쉘 스크립트와 cron을 이용한 자동 감시

---

## 🔍 주요 단계별 상세 설명

### 1. 보안 설정 (Server Hardening)

#### **왜 SSH 포트를 22에서 20022로 바꿨나요?**
*   **이유**: 인터넷상의 수많은 해킹 봇들은 기본 포트인 22번을 끊임없이 공격(Brute Force)합니다. 포트 번호만 바꿔도 이런 자동화 공격의 99%를 피할 수 있습니다. (Security by Obscurity)
*   **Root 접속 차단**: root 계정은 전지전능한 권한을 가집니다. 해커가 root 비번을 알아내면 끝입니다. 따라서 일반 계정으로 접속한 뒤 `sudo`를 통해서만 권한을 얻도록 하는 것이 표준입니다.

> **💡 학습 명령어**: `ss -tulnp | grep ssh` (현재 어떤 포트가 열려있는지 확인)

#### **방화벽 (UFW)**
*   **원칙**: "필요한 것 외에는 모두 닫는다."
*   **적용**: SSH(20022)와 앱 서비스(15034) 포트만 열어두고 나머지는 모두 차단했습니다.

---

### 2. 계정 및 권한 관리 (IAM)

우리는 사용자별로 권한을 다르게 부여했습니다.

| 계정 | 소속 그룹 | 역할 |
| :--- | :--- | :--- |
| `agent-admin` | `agent-core`, `agent-common` | 전체 운영 및 자동화(cron) 실행 |
| `agent-dev` | `agent-core`, `agent-common` | 모니터링 스크립트 작성 및 수정 |
| `agent-test` | `agent-common` | 단순 테스트 (보안 디렉토리 접근 불가) |

#### **ACL (Access Control List)이란?**
기본 리눅스 권한(`rwxrwxrwx`)은 '소유자-그룹-기타'로만 나뉩니다. 하지만 **ACL**을 사용하면 "A 그룹에게는 읽기 권한을, B 그룹에게는 쓰기 권한을"과 같이 훨씬 세밀하게 설정할 수 있습니다.

> **💡 학습 명령어**: `getfacl /home/agent-admin/agent-app/upload_files`

---

### 3. 애플리케이션 실행 환경

*   **환경 변수**: `AGENT_HOME`, `AGENT_PORT` 등을 사용하여 앱이 실행될 때 필요한 설정값을 하드코딩하지 않고 외부에서 주입합니다.
*   **바이너리 실행**: 우리가 실행한 `agent-app`은 Python 코드를 실행 파일로 빌드한 것입니다. 리눅스 라이브러리 버전(GLIBC)이 맞아야 실행된다는 것을 이번에 경험했습니다.

---

### 4. 모니터링 자동화 (monitor.sh)

`monitor.sh`는 서버의 심장박동을 체크하는 의사 역할을 합니다.

1.  **Health Check**: 앱 프로세스가 떠 있는가? ( `pgrep` )
2.  **Port Check**: 서비스 포트가 응답하는가? ( `ss` )
3.  **Resource Check**: CPU, 메모리, 디스크가 가득 차지 않았는가? ( `top`, `free`, `df` )
4.  **Logging**: 결과를 `/var/log/agent-app/monitor.log`에 기록합니다.

#### **Cron (크론)**
이 스크립트를 우리가 매분 직접 실행할 순 없습니다. `cron`이라는 예약 시스템을 통해 1분마다 자동으로 실행되게 만들었습니다.

> **💡 학습 명령어**: `sudo -u agent-admin crontab -l`

---

## 🛠️ 직접 확인해보기 (Self-Check)

학습을 위해 VM 접속 후 아래 명령어들을 직접 입력해 보세요.

1.  **서버 접속**: `orb shell ubuntu-agent`
2.  **로그 실시간 감시**: `sudo tail -f /var/log/agent-app/monitor.log` (1분마다 로그가 올라오는 것을 구경하세요!)
3.  **리포트 생성**: `sudo -u agent-admin /home/agent-admin/agent-app/bin/report.sh` (지금까지 쌓인 로그의 통계를 보여줍니다.)
4.  **보안 점검**: `sudo ufw status`

---

## 📁 워크스페이스 파일 구조 가이드

*   `scripts/setup.sh`: 전체 환경을 한 번에 구축한 마법 같은 스크립트입니다. 내용을 뜯어보며 공부하기 좋습니다.
*   `scripts/monitor.sh`: 리눅스 상태를 어떻게 수집하는지 Bash 문법이 담겨 있습니다.
*   `scripts/report.sh`: 수집된 로그 데이터를 어떻게 분석(awk 활용)하는지 보여줍니다.
*   `walkthrough.md`: 상세한 작업 기록이 담긴 기술 문서입니다.

이제 이 가이드를 옆에 띄워두고, 하나씩 명령어를 입력하며 서버의 동작 원리를 익혀보세요!
