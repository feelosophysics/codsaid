#!/bin/bash
# =============================================================================
# setup.sh - 미션 전체 환경 자동 구성 및 프로비저닝 스크립트 (초정밀 주석 개선판)
# 실행 주체: VM 내부에서 시스템 관리를 위해 'sudo' 권한(Root)으로 직접 구동
# =============================================================================

# ── [Rich Aesthetics] 터미널 시각 효과를 극대화하는 ANSI 컬러 및 스타일 정의 ────
# \e[ 또는 \033[ 은 이스케이프 시퀀스의 시작을 뜻하며, 뒤의 숫자는 스타일과 전경색을 지정합니다.
RED='\e[1;31m'     # 1: 굵게(Bold), 31: 빨간색 (에러 출력용)
GREEN='\e[1;32m'   # 1: 굵게(Bold), 32: 초록색 (성공 출력용)
YELLOW='\e[1;33m'  # 1: 굵게(Bold), 33: 노란색 (경고 출력용)
BLUE='\e[1;34m'    # 1: 굵게(Bold), 34: 파란색 (주요 진행 단계 표시용)
MAGENTA='\e[1;35m' # 1: 굵게(Bold), 35: 자줏빛 (헤더 배너 장식용)
CYAN='\e[1;36m'    # 1: 굵게(Bold), 36: 청록색 (상세 수동 가이드 정보용)
NC='\e[0m'         # No Color: 폰트 스타일 및 색상 초기화 (터미널 기본 상태 복구)
BOLD='\e[1m'       # 폰트 두께만 굵게 지정

# ── 시각적 가독성 극대화를 위한 로깅 헬퍼 함수 정의 ───────────────────────────
# 함수 내부에서 echo -e 옵션을 사용해 ANSI 이스케이프 문자를 쉘이 해석하여 색상으로 출력하게 합니다.

# 주요 메이저 단계 진척 사항 표시
log_step() {
    echo -e "\n${BOLD}${BLUE}▶ $1${NC}"
}

# 하위 작업 성공 승인 완료 표시
log_success() {
    echo -e "   ${GREEN}✅ $1${NC}"
}

# 크리티컬 실패 및 프로그램 중단 오류 알림
log_error() {
    echo -e "   ${RED}❌ [ERROR] $1${NC}"
}

# 경고 사항 표시 (동작에는 무관하나 확인이 필요한 주의)
log_warn() {
    echo -e "   ${YELLOW}⚠️  [WARNING] $1${NC}"
}

# 상세 설정값 또는 상태 리포팅 정보 표시
log_info() {
    echo -e "   ${CYAN}ℹ️  $1${NC}"
}

# 메인 인트로 배너 장식 출력
echo -e "${BOLD}${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${MAGENTA}║      Agent Mission - Premium Auto Setup Script       ║${NC}"
echo -e "${BOLD}${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"

# ── [보안 검증] 최상위 관리자 권한(Root) 체크 ─────────────────────────────────
# $EUID 환경변수는 현재 실행 중인 사용자의 유효 UID(Effective User ID)를 반환합니다.
# 유닉스 계열에서 Root의 UID는 항상 0입니다. 0이 아닐 경우 권한 상승 실패로 보고 즉시 종료합니다.
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 시스템 설정을 위해 반드시 sudo 권한으로 실행되어야 합니다."
    log_info "실행 예: sudo bash setup.sh"
    exit 1
fi

# ── 핵심 상수 정의 ─────────────────────────────────────────────────────────────
# 애플리케이션이 구동 및 관리될 논리적 홈 디렉토리
AGENT_HOME=/home/agent-admin/agent-app
# 스크립트 실행 파일이 위치한 물리적 디렉토리 경로 자동 파싱
# dirname "${BASH_SOURCE[0]}"는 현재 스크립트 파일의 상대 경로를 검출하고, cd 후 pwd를 통해 절대 경로로 정규화합니다.
CURRENT_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ──────────────────────────────────────────────────────────────────────────────
log_step "[1단계] 시스템 의존성 자동 확인 및 설치"

# 패키지 존재 확인 및 자동 설치 헬퍼 함수
# 인자: $1 -> 검증 및 설치할 패키지 명칭
ensure_package() {
    local pkg_name="$1"
    # dpkg -l 명령으로 시스템 설치 패키지 명세를 조회한 뒤, grep으로 정상 설치 상태를 나타내는 '^ii  [패키지명] ' 패턴을 검색합니다.
    # -q 옵션은 화면 출력을 전면 차단하고 성공/실패 코드(Exit Code)만 반환하게 만듭니다.
    if ! dpkg -l | grep -q "^ii  $pkg_name "; then
        log_warn "'$pkg_name' 패키지가 감지되지 않았습니다. 설치를 진행합니다..."
        # apt-get의 출력을 표준출력/에러 모두 디바이스 널 블랙홀(&>/dev/null)로 폐기하여 사용자 터미널 콘솔을 깨끗하게 유지합니다.
        apt-get update -y &>/dev/null
        apt-get install -y "$pkg_name" &>/dev/null
        
        # 직전 명령어(apt-get install)의 성공 여부 ($? == 0) 확인
        if [ $? -eq 0 ]; then
            log_success "'$pkg_name' 패키지 설치 완료!"
        else
            log_error "'$pkg_name' 패키지 설치 실패. 인터넷 연결이나 apt 저장소(Sources.list)를 확인해 주세요."
            exit 1
        fi
    else
        log_success "'$pkg_name' 이(가) 이미 시스템에 존재합니다."
    fi
}

# 관제 및 하드닝에 반드시 필요한 4대 유틸리티 설치 검증
ensure_package "openssh-server" # SSH 서버 데몬
ensure_package "ufw"            # 우분투 표준 방화벽
ensure_package "acl"            # 확장 접근 제어 관리 도구 (setfacl 등 제공)
ensure_package "file"           # 바이너리 파일 형식 식별기

# ──────────────────────────────────────────────────────────────────────────────
log_step "[2단계] SSH 보안 하드닝 및 설정..."

SSHD_CONFIG="/etc/ssh/sshd_config"

if [ -f "$SSHD_CONFIG" ]; then
    # sed의 -i 옵션은 파일의 내용을 임시 복사 없이 제자리에서 직접 수정(In-place edit)합니다.
    # 정규식 패턴 분석:
    # '^#\?\s*Port .*': 행의 시작 부분에 주석기호(#)가 있거나 없으며(\?), 임의의 공백(\s*)이 존재하고, 'Port'와 임의의 값(.*)이 나오는 패턴 매칭
    # 'Port 20022'로 강제 치환
    sudo sed -i 's/^#\?\s*Port .*/Port 20022/' "$SSHD_CONFIG"
    
    # '^#\?\s*PermitRootLogin .*': root의 원격 직접 접근 정책 행을 탐색하여, 'PermitRootLogin no'로 완벽 격리 치환
    sudo sed -i 's/^#\?\s*PermitRootLogin .*/PermitRootLogin no/' "$SSHD_CONFIG"
    
    log_info "SSH 설정 파일 반영 확인:"
    grep -E "^Port|^PermitRootLogin" "$SSHD_CONFIG"
    
    # ── [지능형 SSH 소켓 활성화 트러블슈팅 엔진] ──────────────────────────────
    # 최신 Ubuntu에서는 ssh.socket이 포트 22를 미리 선점하여 관리하므로, 
    # sshd_config 수정을 제대로 먹이려면 ssh.socket을 내리고 서비스 상주 모드로 강제 개편해야 합니다.
    # systemctl is-active --quiet 는 해당 유닛이 현재 'active(정상 동작)' 상태인지를 결과 코드로만 조용히 검출합니다.
    if systemctl is-active --quiet ssh.socket 2>/dev/null; then
        log_warn "systemd 소켓 활성화(ssh.socket) 구조가 시스템에 켜져 있는 상태입니다."
        log_info "포트 20022 변경 반영을 위해 소켓 유닛을 정지하고, 전통적인 서비스 상주형 모드로 전환합니다."
        
        # ssh.socket 정지 및 부팅 시 자동 시작 해제
        sudo systemctl stop ssh.socket 2>/dev/null || true
        sudo systemctl disable ssh.socket 2>/dev/null || true
        
        # systemd의 설정 파일 변화(소켓 비활성화)를 적용하기 위해 데몬 설정 갱신
        sudo systemctl daemon-reload 2>/dev/null || true
        
        # 배포판 버전에 맞게 ssh.service 또는 sshd.service를 구동하여 20022 포트 상시 리슨 모드로 작동
        sudo systemctl enable --now ssh.service 2>/dev/null || sudo systemctl enable --now sshd.service 2>/dev/null || true
    else
        # 소켓 활성화가 활성화되어 있지 않다면, 전통적인 방식으로 서비스 유닛만 완전 재시작
        log_info "전통적인 SSH 데몬 환경입니다. 서비스를 재시작합니다."
        sudo systemctl restart ssh 2>/dev/null || sudo systemctl restart sshd 2>/dev/null || true
    fi
    
    log_info "SSH 실시간 커널 포트 리슨 상태 확인:"
    ss -tulnp | grep -E "sshd|ssh" || true
    log_success "SSH 설정 및 보안 정책 반영 완료"
else
    log_error "$SSHD_CONFIG 파일을 시스템에서 발견하지 못했습니다."
fi

# ──────────────────────────────────────────────────────────────────────────────
log_step "[2단계] 방화벽(UFW) 화이트리스트 구성..."

if command -v ufw &>/dev/null; then
    # 방화벽 기존에 주입된 모든 룰셋을 완전 삭제 초기화 (--force 옵션으로 대화형 확인 메시지 생략)
    sudo ufw --force reset >/dev/null
    
    # 기본 접근 제어 원칙 수립: 외부에서 들어오는 트래픽(Incoming)은 전체 전면 거부(deny)
    sudo ufw default deny incoming >/dev/null
    # 내부에서 나가는 트래픽(Outgoing)은 유연하게 전체 허용(allow)
    sudo ufw default allow outgoing >/dev/null
    
    # 화이트리스트 개방 포트 등록 (20022/tcp: SSH 관리자 통로, 15034/tcp: 앱 서비스용)
    sudo ufw allow 20022/tcp comment 'SSH' >/dev/null
    sudo ufw allow 15034/tcp comment 'APP' >/dev/null
    
    # UFW 방화벽 필터링 모듈 엔진을 실시간 커널에 반영하여 가동
    sudo ufw --force enable >/dev/null
    
    log_info "UFW 활성화 상태 및 개방 룰 목록:"
    sudo ufw status verbose
    log_success "방화벽(UFW) 화이트리스트 최소 허용 정책 수립 완료"
else
    log_error "UFW 커맨드가 존재하지 않거나 사용할 수 없습니다."
fi

# ──────────────────────────────────────────────────────────────────────────────
log_step "[3단계] 역할 기반 보안 그룹 생성..."

# groupadd의 -f(force) 옵션은 생성하려는 그룹이 이미 있는 경우에도 에러 코드를 뿜지 않고 0을 반환하며 안전하게 넘어갑니다.
sudo groupadd -f agent-common  # 세 사용자 공통 협업 그룹
sudo groupadd -f agent-core    # 관리자 및 개발자만 포함되는 보안 핵심 그룹

log_info "생성된 에이전트 전용 그룹 명부 확인:"
grep -E "^agent-" /etc/group
log_success "보안 그룹 생성 및 격리 완료"

log_step "[3단계] 역할별 계정 생성 및 그룹 구성 매핑..."

# 사용자 생성 헬퍼 함수
# 인자: $1 -> 계정명, $2 -> 패스워드 문자열
create_agent_user() {
    local username="$1"
    local password="$2"
    # id 명령어를 통해 해당 이름의 사용자가 기존 시스템 데이터베이스(/etc/passwd)에 정의되어 있는지 사전 검사
    if ! id "$username" &>/dev/null; then
        # -m 옵션: 사용자의 홈 디렉토리를 /home/하위에 강제 매핑하여 자동 생성
        # -s /bin/bash: 로그인 시 부여할 기본 쉘을 bash로 설정
        sudo useradd -m -s /bin/bash "$username"
        # echo 형식을 chpasswd에 파이프라인으로 전달하여 비밀번호를 비대화형(non-interactive)으로 즉시 주입
        echo "$username:$password" | sudo chpasswd
        log_success "신규 계정 생성 완료: $username"
    else
        log_info "계정 '$username'이 이미 존재합니다. 충돌 방지를 위해 생성을 건너뜁니다."
    fi
}

# 3대 핵심 사용자 생성
create_agent_user "agent-admin" "agent-admin123!" # 운영 관리자
create_agent_user "agent-dev" "agent-dev123!"     # 개발자
create_agent_user "agent-test" "agent-test123!"   # 품질 검수 테스터

# ── 역할별 그룹 할당 설계 ────────────────────────────────────────────────────
# usermod의 -aG 옵션은 기존에 소속된 그룹 정보를 잃어버리지 않고, 새 그룹을 보조 그룹(Append Group)으로 추가합니다.

# agent-common 그룹에는 모든 협업을 수행할 3개 계정을 전부 배정합니다.
sudo usermod -aG agent-common agent-admin
sudo usermod -aG agent-common agent-dev
sudo usermod -aG agent-common agent-test

# agent-core 보안 권한 그룹에는 오직 'admin'과 'dev' 단 둘만 배정하여 'test'를 철저히 물리적으로 격리합니다.
sudo usermod -aG agent-core agent-admin
sudo usermod -aG agent-core agent-dev

log_info "계정별 소속 그룹 무결성 검증:"
id agent-admin
id agent-dev
id agent-test
log_success "역할 기반 계정 및 보조 보안 그룹 구성 완료"

# ──────────────────────────────────────────────────────────────────────────────
log_step "[3단계] 디렉토리 보존 구조 수립 및 권한/SetGID/ACL 적용..."

# 관제 프로세스가 돌아갈 물리적 폴더 및 아카이브 공간 생성
sudo mkdir -p $AGENT_HOME/upload_files
sudo mkdir -p $AGENT_HOME/api_keys
sudo mkdir -p $AGENT_HOME/bin
sudo mkdir -p /var/log/agent-app
sudo mkdir -p /var/log/monitor/agent-app/archive

# 소유권 및 접근 권한 분할 설정
# 1. 에이전트 홈은 admin이 소유하되 dev(core 그룹)도 탐색(x) 및 열람(r)만 가능하게 750(rwxr-x---) 설정
sudo chown agent-admin:agent-core  $AGENT_HOME
sudo chmod 750                     $AGENT_HOME

# 2. 업로드 공유 폴더는 공동(agent-common) 작업 구역
# 권한 '2770' 중 '2'는 특수 권한인 **SetGID (Set Group ID)** 비트입니다.
# 이 디렉토리 아래에서 세 사용자가 제각기 파일을 새로 생성하더라도, 새로 태어난 파일들의 소유 그룹은 생성자 본인이 아닌
# 부모 폴더의 소유 그룹인 'agent-common'으로 강제 귀속됩니다. 따라서 상호 수정 및 공유 협업 권한이 깨지지 않습니다.
sudo chown agent-admin:agent-common $AGENT_HOME/upload_files
sudo chmod 2770                     $AGENT_HOME/upload_files

# 3. 비밀키 api_keys 폴더는 오직 코어 멤버만 읽고 써야 하므로 그룹을 agent-core로 두고 2770 적용
sudo chown agent-admin:agent-core  $AGENT_HOME/api_keys
sudo chmod 2770                    $AGENT_HOME/api_keys

# 4. 관제 로그 디렉토리도 역시 코어 멤버 전용이므로 2770 적용
sudo chown agent-admin:agent-core  /var/log/agent-app
sudo chmod 2770                    /var/log/agent-app

# 5. 보너스 아카이브 및 모니터링 수집 통계 디렉토리 소유권 전이
sudo chown -R agent-admin:agent-core /var/log/monitor

# ── [ACL & Default ACL (액세스 제어 상속성) 정밀 주입] ───────────────────────
# setfacl의 -m(modify) 옵션은 개별 그룹의 접근 룰을 파일 시스템 메타데이터에 등록합니다.
# setfacl의 -d(default) 옵션은 디렉토리에만 설정 가능한 특수 마커로,
# 이 폴더 하위에 앞으로 생성될 미래의 모든 하위 파일들과 폴더들이 부모와 완전히 똑같은 ACL 규칙(rwx)을 상속받도록 강제합니다.

# upload_files: agent-common 그룹에 완벽한 rwx 통제권 설정 및 기본 권한 상속 규칙 적용
sudo setfacl -m  g:agent-common:rwx $AGENT_HOME/upload_files
sudo setfacl -d  -m g:agent-common:rwx $AGENT_HOME/upload_files

# api_keys: 코어 보안 자원 보호
sudo setfacl -m  g:agent-core:rwx  $AGENT_HOME/api_keys
sudo setfacl -d  -m g:agent-core:rwx  $AGENT_HOME/api_keys

# /var/log/agent-app: 관제 로그 훼손 방지
sudo setfacl -m  g:agent-core:rwx  /var/log/agent-app
sudo setfacl -d  -m g:agent-core:rwx  /var/log/agent-app

# archive: 아카이브 보너스 로그 보호
sudo setfacl -m  g:agent-core:rwx  /var/log/monitor/agent-app/archive
sudo setfacl -d  -m g:agent-core:rwx  /var/log/monitor/agent-app/archive

log_info "에이전트 홈 하위의 전체 물리 객체 권한 및 소유 상태 검증:"
sudo ls -la $AGENT_HOME
log_success "디렉토리 구조, 특수 권한(SetGID) 및 ACL 보안 규칙 주입 완료"

# ──────────────────────────────────────────────────────────────────────────────
log_step "[4단계] 쉘 환경 변수 주입..."

# .bashrc 멱등성 주입 함수
# 사용자가 로그인할 때(대화형 쉘) 동작할 환경 변수 매핑
inject_bashrc() {
    local target_file="/home/agent-admin/.bashrc"
    # grep -q 옵션으로 기존 .bashrc 파일 내부에 AGENT_HOME이라는 환경변수 문자열이 이미 상주해 있는지 스캔
    if ! grep -q "AGENT_HOME=" "$target_file" 2>/dev/null; then
        # 멱등성 보장: 중복 주입을 방지하여 파일 크기가 무한히 증가하는 버그 차단
        sudo bash -c "cat >> $target_file << 'ENVEOF'

# ===== Agent App Environment =====
export AGENT_HOME=/home/agent-admin/agent-app
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR=\$AGENT_HOME/upload_files
export AGENT_KEY_PATH=\$AGENT_HOME/api_keys/t_secret.key
export AGENT_LOG_DIR=/var/log/agent-app
# =================================
ENVEOF"
        log_success "agent-admin .bashrc에 로컬 환경 변수 추가 성공"
    else
        log_info "agent-admin .bashrc에 이미 환경 변수가 셋업되어 있어 건너뜁니다."
    fi
}

# /etc/environment 멱등성 주입 함수
# cron과 같이 사용자의 로그인 세션을 거치지 않는 비대화형(non-interactive) 스케줄러 배치 프로세스에서도
# 시스템 전체 수준(System-wide)에서 해당 경로 환경변수들을 완벽하게 획득하도록 적재하는 핵심 메커니즘입니다.
inject_etc_environment() {
    local target_file="/etc/environment"
    if ! grep -q "AGENT_HOME=" "$target_file" 2>/dev/null; then
        sudo bash -c "cat >> $target_file << 'ENVEOF'
AGENT_HOME=/home/agent-admin/agent-app
AGENT_PORT=15034
AGENT_UPLOAD_DIR=/home/agent-admin/agent-app/upload_files
AGENT_KEY_PATH=/home/agent-admin/agent-app/api_keys/t_secret.key
AGENT_LOG_DIR=/var/log/agent-app
ENVEOF"
        log_success "/etc/environment 시스템 전체 환경 변수 추가 성공"
    else
        log_info "/etc/environment에 이미 환경 변수가 매핑되어 있어 건너뜁니다."
    fi
}

inject_bashrc
inject_etc_environment

log_info "시스템 환경 파일(/etc/environment) 내 에이전트 속성 스캔:"
grep AGENT /etc/environment
log_success "환경 변수 시스템 셋업 완료"

# ──────────────────────────────────────────────────────────────────────────────
log_step "[4단계] 비밀 관리용 마스터 키 파일 생성..."

# 마스터 비밀 키 등록
echo "agent_api_key_test" | sudo tee $AGENT_HOME/api_keys/t_secret.key > /dev/null
# 소유자는 관리자로 설정하되 코어 그룹에 읽기 권한을 인계
sudo chown agent-admin:agent-core  $AGENT_HOME/api_keys/t_secret.key
# 권한 640 (rw-r-----): 소유자(admin)는 읽고 쓸 수 있고, 그룹(core) 멤버들은 읽기만 가능하며, 제3자(test 등)는 일체 읽거나 쓸 수 없게 격리
sudo chmod 640                     $AGENT_HOME/api_keys/t_secret.key

log_info "마스터 키 보안 파일 정보 검증:"
sudo ls -la $AGENT_HOME/api_keys/
log_info "키 내용 정합성 검증 (보안 출력):"
sudo cat $AGENT_HOME/api_keys/t_secret.key
log_success "비밀 보안 키 생성 완료"

# ──────────────────────────────────────────────────────────────────────────────
log_step "[4단계] 메인 애플리케이션(agent-app) 바이너리 탐색 및 배치..."

# 개발/VM 환경의 상이함에 대응하기 위해 유연한 멀티 스폿 바이너리 스캔 알고리즘 적용
SRC_APP=""
if [ -f "/tmp/agent-app" ]; then
    SRC_APP="/tmp/agent-app"
elif [ -f "$CURRENT_SCRIPT_DIR/../agent-app" ]; then
    SRC_APP="$CURRENT_SCRIPT_DIR/../agent-app"
elif [ -f "$CURRENT_SCRIPT_DIR/agent-app" ]; then
    SRC_APP="$CURRENT_SCRIPT_DIR/agent-app"
fi

if [ -n "$SRC_APP" ]; then
    # 탐색된 원본 실행 바이너리를 에이전트 홈으로 정밀 복사
    sudo cp "$SRC_APP" $AGENT_HOME/agent-app
    # 소유자와 권한 분할 지정
    sudo chown agent-admin:agent-core $AGENT_HOME/agent-app
    # 권한 750 (rwxr-x---): 실행 가능성 부여 및 외부인 사용 제한
    sudo chmod 750                    $AGENT_HOME/agent-app
    log_info "바이너리 배치 완료 ($SRC_APP -> $AGENT_HOME/agent-app)"
    
    if command -v file &>/dev/null; then
        log_info "파일 시스템 정밀 아키텍처 식별 결과:"
        file $AGENT_HOME/agent-app
    fi
    log_success "애플리케이션 구동 실행 바이너리 배치 완료"
else
    log_warn "복사할 소스 agent-app 바이너리를 워크스페이스 상에서 찾을 수 없습니다."
    log_info "(/tmp/agent-app 또는 로컬 리포지토리 루트 경로를 사후에 확인바랍니다)"
fi

# ──────────────────────────────────────────────────────────────────────────────
log_step "[5단계] 관제 및 유틸리티 쉘 스크립트 삼총사 일괄 배치..."

# 배치할 자동화 스크립트 목록을 배열화하여 반복 루프 구동
for script_file in "monitor.sh" "report.sh" "archive.sh"; do
    if [ -f "$CURRENT_SCRIPT_DIR/$script_file" ]; then
        # 원본 코드를 빈 디렉토리로 안전하게 복사
        sudo cp "$CURRENT_SCRIPT_DIR/$script_file" "$AGENT_HOME/bin/$script_file"
        
        # ⚠️ [보안 핵심 정책 만족]
        # 스크립트의 소유자는 개발 담당 역할인 'agent-dev'로 귀속시켜 유지보수 권한을 넘기고,
        # 소유 그룹은 'agent-core'로 지정합니다.
        sudo chown agent-dev:agent-core "$AGENT_HOME/bin/$script_file"
        
        # 권한 750 (rwxr-x---):
        # 소유자(agent-dev)는 자유로운 읽기/쓰기/실행 권한(rwx)을 가집니다.
        # 소유 그룹(agent-core)에 포함된 관리자(agent-admin)는 읽기 및 실행 권한(r-x)을 가지므로 cron 배치를 자유롭게 동작시킬 수 있습니다.
        # 그 외 테스터(agent-test)는 파일에 노출되지 않고 내용을 변조할 수도 없도록 차단됩니다.
        sudo chmod 750 "$AGENT_HOME/bin/$script_file"
        log_success "[배포 완료] $script_file -> $AGENT_HOME/bin/ (소유자: agent-dev, 그룹: agent-core, 권한: 750)"
    else
        log_warn "$script_file 스크립트 파일을 현재 소스 경로 ($CURRENT_SCRIPT_DIR) 에서 스캔할 수 없습니다."
    fi
done

log_info "배치된 관제 빈(bin) 디렉토리 상세 명세:"
sudo ls -la $AGENT_HOME/bin/
log_success "관제 시스템 패키징 스크립트 일괄 배치 성공"

# ──────────────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║       ✅ 자동 환경 구성이 완벽히 끝났습니다!       ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BOLD}【수동 검증 및 후속 조치 방법】${NC}"
echo -e "1. agent-app 실행 (백그라운드/로그인 쉘):"
echo -e "   ${CYAN}sudo -u agent-admin bash -l -c 'cd \$AGENT_HOME && ./agent-app'${NC}"
echo ""
echo -e "2. monitor.sh 수동 진단 (애플리케이션 작동 확인):"
echo -e "   ${CYAN}sudo -u agent-admin bash -l -c '\$AGENT_HOME/bin/monitor.sh'${NC}"
echo ""
echo -e "3. crontab 스케줄러 자동 실행 등록 (매분 배치):"
echo -e "   ${CYAN}sudo -u agent-admin crontab -e${NC}"
echo -e "   ※ 아래 내용을 편집기에 추가해 주세요:"
echo -e "   ${YELLOW}* * * * * . /etc/environment; $AGENT_HOME/bin/monitor.sh >> /tmp/cron.log 2>&1${NC}"
echo ""