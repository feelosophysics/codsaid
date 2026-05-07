# **시스템 관제 자동화 스크립트 개발**
1. 다중 사용자 환경에서의 권한 관리
2. 네트워크 보안 설정
3. 실제 서비스를 배포하고 운영할 때 필수적인 시스템 리소스 관제와 로그 관리를 자동화하는 쉘 스크립트 개발 수행

### [산출물]
1. 요구사항 수행 내역서(문서 1개)
    - 수행 내역 : 설정/명령어 기록(SSH 포트, 방화벽 규칙, 계정/그룹/ACL, 디렉토리/권한, 환경 변수, cron 등록 등)
    - 필수 증거 자료 체크리스트
        - SSH 포트 변경(20022) 및 Root 원격 접속 차단 설정 확인 내역
        - 방화벽(UFW 또는 firewalld) 활성화 및 20022/tcp, 15034/tcp만 허용 내역
        - 계정/그룹(agent-admin/dev/test, agent-common/core) 생성 확인 내역
        - 디렉토리 구조 및 권한(ACL 포함) 확인 내역
        - 앱 Boot Sequence 5단계 [OK] 및 "Agent READY" 확인 내역
        - monitor.sh 실행 결과(프로세스/포트/리소스/경고) 내역
        - /var/log/agent-app/monitor.log 누적 기록 확인(최근 라인) 내역
        - crontab 매분 실행 등록 및 자동 실행 확인(1분 후 로그 증가) 내역
2. 자동화 스크립트 소스코드 : monitor.sh : 시스템 상태 수집 및 로깅 스크립트

### [과제 목표]
- SSH 포트 변경과 Root 원격 접속 차단이 왜 기본 보안에 해당하는지 설명할 수 있다.
- UFW 또는 firewalld 중 하나를 선택해 “필요 포트만 허용”하는 방화벽 정책을 구성하고 검증할 수 있다.
- 역할 기반 계정/그룹과 ACL을 통해 “공유 디렉토리”와 “보안 디렉토리”를 분리하는 이유를 설명할 수 있다.
- 환경 변수(AGENT_HOME 등)로 실행 환경을 고정하는 이유와 검증 방법을 설명할 수 있다.
- 쉘 스크립트로 프로세스/포트/리소스 상태를 수집하고, 로그로 남겨 운영 문제를 추적하는 흐름을 설명할 수 있다.
- crontab으로 모니터링을 주기 실행시키고, 로그 보존 정책(압축/삭제)이 왜 필요한지 설명할 수 있다.

### 기능 요구 사항
1. 기본 보안 및 네트워크 설정
    - SSH 설정
        - SSH 접속 포트를 20022로 변경한다.
        - Root 원격 로그인을 차단한다.
        - 확인 방법(예시)
            - sshd 설정 파일에서 포트/PermitRootLogin 확인
            - 포트 리슨 상태 확인: ss -tulnp 후 sshd 관련 라인 확인
        - 방화벽 설정(택1)
            - UFW 또는 firewalld 중 하나를 선택해 활성화한다.
            - 인바운드 허용 포트는 TCP 20022(SSH), TCP 15034(APP)만 허용한다.
            - 확인 방법(예시)
                - UFW 선택 시: ufw status
                - firewalld 선택 시: firewall-cmd --list-all
2. 계정/그룹/권한 체계(협업 + 최소 권한)
    - 생성 계정
        - agent-admin (운영/관리, cron 실행자)
        - agent-dev (개발/운영, monitor.sh 작성자)
        - agent-test (QA/테스트)
    - 생성 그룹
        - agent-common: admin, dev, test
        - agent-core: admin, dev
    - 디렉토리 구조(AGENT_HOME 기준)
        - $AGENT_HOME
        - $AGENT_HOME/upload_files
        - $AGENT_HOME/api_keys
        - /var/log/agent-app
    - 접근 권한(핵심 정책)
        - upload_files: group=agent-common, R/W 가능
        - api_keys 및 /var/log/agent-app: group=agent-core ONLY, R/W 가능
        - 확인 방법(예시)
            - id agent-admin / id agent-dev / id agent-test
            - ls -l 및 getfacl(사용 시)로 소유/권한 확인
3. 애플리케이션 실행 환경 구성(제공 Python 앱)
    - 환경 변수
        - AGENT_HOME: 예) /home/agent-admin/agent-app
        - AGENT_PORT: 15034
        - AGENT_UPLOAD_DIR: $AGENT_HOME/upload_files
        - AGENT_KEY_PATH: $AGENT_HOME/api_keys/t_secret.key
        - AGENT_LOG_DIR: /var/log/agent-app (미지정 시 기본값이므로 지정 권장)
    - 키 파일 생성
        - 경로: $AGENT_HOME/api_keys/t_secret.key
        - 내용: agent_api_key_test (1줄)
    - 앱 실행 및 성공 기준
        - 일반 계정으로 실행(루트 실행 금지)
        - Boot Sequence 5단계가 모두 [OK]로 출력되고, 마지막에 “Agent READY”가 출력되어야 한다.
        - 앱이 0.0.0.0:15034로 LISTEN 상태가 되어야 한다.
        - 참고: 앱 종료는 Ctrl+C로 수행한다.
4. 시스템 관제 자동화 스크립트(monitor.sh) 구현
    - 파일 위치/권한 정책
        - 경로: $AGENT_HOME/bin/monitor.sh
        - 소유자: agent-dev
        - 그룹: agent-core
        - 권한: 750 (rwxr-x---)
        - cron 실행 계정: agent-admin (agent-admin은 agent-core에 포함되어 실행 가능해야 함)
    - Health Check(실패 시 종료)
        - 프로세스: agent_app.py(또는 제공 앱 파일명) 실행 상태를 확인하고, 비정상 시 exit 1
        - 포트: TCP 15034 LISTEN 상태 확인, 비정상 시 exit 1
    - 상태 점검(경고만 출력)
        - 방화벽(UFW 또는 firewalld) 활성화 상태를 점검한다.
        - 비활성 상태면 [WARNING]을 출력하되, 스크립트는 종료하지 않는다.
    - 자원 수집
        - CPU 사용률(%)
        - 메모리 사용률(%)
        - 디스크 사용률(Root partition, Used %)
    - 임계값 경고(경고만 출력)
        - CPU > 20%: [WARNING]
        - MEM > 10%: [WARNING]
        - DISK_USED > 80%: [WARNING]
    - 로그 기록
        - 로그 파일: /var/log/agent-app/monitor.log
        - 로그 포맷
            - [YYYY-MM-DD HH:MM:SS] PID:... CPU:..% MEM:..% DISK_USED:..%
    - 로그 파일 용량 관리
        - monitor.log가 커지면 최대 10MB/10개 파일 유지(방법 자유: logrotate 사용 또는 스크립트 로직 구현)
    - 자동 실행(cron) 설정
        - agent-admin 계정의 crontab으로 monitor.sh를 매분 실행되도록 등록한다.
        - 등록 후 1~2분 내 monitor.log에 새 라인이 자동으로 누적되는 것을 확인한다.
