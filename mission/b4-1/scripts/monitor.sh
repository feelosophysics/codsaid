#!/bin/bash
# =============================================================================
# monitor.sh - 시스템 상태 수집 및 로깅 스크립트 (초정밀 주석 개선판)
# 물리적 위치: $AGENT_HOME/bin/monitor.sh
# 소유 권한 구조: 소유자: agent-dev / 소유 그룹: agent-core / 허용 권한: 750 (rwxr-x---)
# 실행 배치 크론: agent-admin 계정의 crontab을 통해 매분(1분 주기) 자동으로 실행
# =============================================================================

# ── [설정 변수 정의] ──────────────────────────────────────────────────────────
APP_PROCESS="agent-app"           # 모니터링할 목표 백그라운드 프로세스 이름 패턴
APP_PORT=15034                    # 서비스 활성화 여부를 판단할 TCP 포트 번호
# 멱등 환경변수 셋업: AGENT_LOG_DIR이 선언되어 있으면 그 경로를 쓰고, 없으면 기본값 /var/log/agent-app 사용
LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
LOG_FILE="$LOG_DIR/monitor.log"   # 관제 데이터가 영구 적재될 시계열 로그 파일 경로
MAX_LOG_SIZE_MB=10                # 로그 파일이 로테이션을 시작할 용량 기준 임계점 (10MB)
MAX_LOG_FILES=10                  # 시스템에 보존할 백업 로그 파일 최대 개수 (.1 ~ .10)

# 리소스 경고 기준치 설정 (임계값)
CPU_THRESHOLD=20                  # CPU 사용률 20% 초과 시 경고 발생
MEM_THRESHOLD=10                  # 메모리 사용률 10% 초과 시 경고 발생
DISK_THRESHOLD=80                 # 루트 디스크 사용률 80% 초과 시 경고 발생

# ── [함수 정의 정의] ──────────────────────────────────────────────────────────

# timestamp: 로그 행 앞에 주입할 고정식 날짜 및 시간 문자열을 균일하게 출력하는 함수
timestamp() {
    # date 뒤의 포맷 인자는 연(Y)-월(m)-일(d) 시(H):분(M):초(S) 순서로 국제 표준 타임스탬프를 반환합니다.
    date "+%Y-%m-%d %H:%M:%S"
}

# rotate_log: 용량 기반 로그 파일 회전(Log Rotation)을 독자적 쉘 알고리즘으로 수행하는 함수
rotate_log() {
    # 대상 로그 파일이 물리적으로 아예 존재하지 않는 초기 기동 시점이라면 함수를 즉시 탈출(return)
    if [ ! -f "$LOG_FILE" ]; then
        return
    fi

    local size_bytes
    # stat 명령어의 -c%s 옵션은 파일의 순수 물리 바이트(Byte) 크기만을 정수값으로 빠르게 리턴합니다.
    # 2>/dev/null 처리를 통해 만에 하나 생길 오류 출력 메시지를 전면 소거하고 실패 시 0을 기본 출력합니다.
    size_bytes=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    
    # 쉘 내부 산술 연산 문법 $(( ... ))을 사용하여 10MB 기준치를 바이트 단위로 계산해 메모리에 올립니다.
    # 10 * 1024 (KB) * 1024 (Byte) = 10,485,760 Bytes
    local max_bytes=$((MAX_LOG_SIZE_MB * 1024 * 1024))

    # stat으로 측정한 현재 로그 용량이 10MB 크기 이상인지 비교 연산자 -ge(Greater than or Equal)로 스캔합니다.
    if [ "$size_bytes" -ge "$max_bytes" ]; then
        # ⚠️ [역순 백업 시프트 알고리즘 적용]
        # 작은 번호부터 덮어쓰기 시작하면 기존 데이터가 파괴됩니다.
        # 따라서 보존 한계 꼬리 부분인 9번 파일부터 순차적으로 뒤로 1칸씩 밀어냅니다.
        # seq 명령어의 인자: ((최대 보존 개수 - 1))부터 시작해 -1씩 감소하면서 1까지 숫자를 생성합니다. (예: 9 8 7 ... 1)
        for i in $(seq $((MAX_LOG_FILES - 1)) -1 1); do
            # 해당 백업 번호의 파일이 존재하는지 검증 (-f)
            if [ -f "${LOG_FILE}.$i" ]; then
                # 존재한다면 기존 번호에서 하나 큰 번호의 파일로 안전하게 이동(이름 변경)
                # 예: monitor.log.9 -> monitor.log.10
                mv "${LOG_FILE}.$i" "${LOG_FILE}.$((i + 1))"
            fi
        done
        
        # 루프가 끝나 1번 자리(monitor.log.1)가 안전하게 비워지면,
        # 현재까지 실시간 기록 중이던 원본 monitor.log 파일을 monitor.log.1로 완전 이동 백업합니다.
        mv "$LOG_FILE" "${LOG_FILE}.1"
        
        # 최대 한계 파일 개수를 초과하게 되는 가장 오래된 11번째 파일(monitor.log.11)을 특정합니다.
        local oldest="${LOG_FILE}.$((MAX_LOG_FILES + 1))"
        # 존재 여부를 검증하고, 참이라면 파일 삭제(rm -f)를 단행하여 저장 장치 고갈을 방지합니다.
        [ -f "$oldest" ] && rm -f "$oldest"
    fi
}

# ── [출력 헤더 디스플레이] ────────────────────────────────────────────────────
echo ""
echo "====== SYSTEM MONITOR RESULT ======"
echo ""

# ── [1단계] 서비스 및 포트 생존성 체크 (Health Check - 실패 시 종료) ───────────
echo "[HEALTH CHECK]"

# 1. 프로세스 기동 체크
# pgrep 명령어의 -f 옵션은 실행 파일명뿐 아니라 전체 명령행 인자(Full command line)를 대상으로 검색합니다.
# 파이프라인 head -1을 통해 혹시 멀티 프로세스가 매칭되더라도 가장 상단의 부모 PID 하나만 안전하게 캡처합니다.
APP_PID=$(pgrep -f "$APP_PROCESS" | head -1)

# -z 옵션은 변수의 문자열 길이가 0(즉, 비어 있는 무(無)의 상태)인지 검사합니다.
if [ -z "$APP_PID" ]; then
    # 프로세스가 감지되지 않으면 FAIL 경고를 화면에 즉시 띄웁니다.
    echo "Checking process '$APP_PROCESS'... [FAIL] (Process not running)"
    # 장애 사후 추적을 위해 시계열 타임스탬프와 함께 크리티컬 에러 로그를 파일에 추가(>> 리다이렉션)합니다.
    echo "[$(timestamp)] HEALTH CHECK FAILED: process '$APP_PROCESS' not found" >> "$LOG_FILE"
    # 프로세스 무(無) 상태는 서비스 전면 중단을 의미하므로, 스크립트 실행을 즉시 강제 중단하며 'exit 1(실패)'을 외부로 반환합니다.
    exit 1
else
    # 살아 있다면 획득한 PID 번호와 함께 OK 승인을 콘솔에 기록합니다.
    echo "Checking process '$APP_PROCESS'... [OK] (PID: $APP_PID)"
fi

# 2. 네트워크 포트 LISTEN 검출
# ss -tulnp 명령어: 리눅스 커널의 실시간 소켓 상태 진단
#   -t: TCP / -u: UDP / -l: Listen 중인 대기 포트만 필터 / -n: 도메인 해석 없이 포트를 기계적 숫자로 표기 / -p: 연결을 소유한 프로세스 정보 강제 출력
# 2>/dev/null 은 권한 없는 사용자가 실행 시 생기는 커널 경고를 소거합니다.
# grep ":15034 " 을 거쳐 해당 서비스 포트 할당 행을 분리한 뒤,
# grep -c LISTEN 을 통해 실시간으로 LISTEN 마크가 떠 있는 행의 개수(-c)를 세어 정수로 리턴합니다.
PORT_LISTEN=$(ss -tulnp 2>/dev/null | grep ":${APP_PORT} " | grep -c LISTEN)

if [ "$PORT_LISTEN" -eq 0 ]; then
    # 리슨 중인 포트 개수가 0개라면 서비스 불가 상황으로 판단하여 FAIL 처리
    echo "Checking port $APP_PORT... [FAIL] (Port not listening)"
    echo "[$(timestamp)] HEALTH CHECK FAILED: port $APP_PORT not listening" >> "$LOG_FILE"
    # 네트워크 마비 상황 역시 치명적 장애로 간주하여 즉각 비정상 종료 (exit 1) 처리
    exit 1
else
    echo "Checking port $APP_PORT... [OK]"
fi

echo ""

# ── [2단계] 보안 방화벽 기동 검증 (경고 표시하되 스크립트는 중단 없음) ─────────
echo "[FIREWALL CHECK]"

# 방화벽 합격 플래그 변수 초기화
FIREWALL_OK=false

# 1. 시스템 내에 UFW 방화벽 도구가 활성화되어 있는지 자동 검사
# command -v [명령어]는 쉘 환경 내에 해당 바이너리가 등록되어 있는지 판별하는 POSIX 표준 방식입니다.
if command -v ufw &>/dev/null; then
    # ufw status 결과를 파싱하여 'Status: active' 부분만 awk로 추출 ($2 즉 status 문자열 추출)
    UFW_STATUS=$(sudo ufw status 2>/dev/null | grep -i "Status:" | awk '{print $2}')
    if [ "$UFW_STATUS" = "active" ]; then
        echo "Firewall (UFW)... [OK] (active)"
        FIREWALL_OK=true
    fi
fi

# 2. UFW가 비활성이거나 동작 안 할 경우, RHEL/CentOS 계열 백업 방화벽인 firewalld의 구동 상태 체크
# && 뒤의 조건은 UFW가 실패 상태로 남아있을 때만 진입하게 만드는 스마트 단락 평가(Short-circuit evaluation)입니다.
if [ "$FIREWALL_OK" = false ] && command -v firewall-cmd &>/dev/null; then
    # firewall-cmd --state 는 정상 작동 중일 때 영문 소문자 'running'을 반환합니다.
    FWD_STATUS=$(sudo firewall-cmd --state 2>/dev/null)
    if [ "$FWD_STATUS" = "running" ]; then
        echo "Firewall (firewalld)... [OK] (running)"
        FIREWALL_OK=true
    fi
fi

# 3. 두 가지 범용 방화벽 프레임워크가 전부 활성화 상태가 아니라고 판정되었을 때
if [ "$FIREWALL_OK" = false ]; then
    # 서비스 전체가 내려앉은 극단 장애는 아니므로 exit 1을 치지 않고, 콘솔에 경고[WARNING] 환기 메시지만 남겨 조치 유도
    echo "[WARNING] Firewall is not active! System may be exposed."
fi

echo ""

# ── [3단계] 실시간 시스템 리소스 계측 (CPU / MEM / DISK) ────────────────────────
echo "[RESOURCE MONITORING]"

# 1. CPU 사용률 정밀 파싱 알고리즘
# top -bn1: top 배치(-b) 모드로 동작시켜 깜빡임 없이 정적인 텍스트로 딱 1회(-n1)만 출력 유도
# sed 정규식 기법: 'Cpu(s)'가 포함된 열에서 유휴 비율을 지칭하는 '... [값] id' 값을 역산 추출합니다.
# \([0-9.]*\) 그룹 캡처 메커니즘을 통해 영문자 사이에 끼어 있는 순수 숫자와 소수점만 잘라내어 매칭시킵니다 (\1로 매핑 출력).
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed -n 's/.*, *\([0-9.]*\) *id.*/\1/p')

# top의 출력 컬럼이나 언어셋 포맷이 특이하여 값이 매치되지 않았을 때를 위한 이중 안전장치(Fallback) sed 작동
if [ -z "$CPU_IDLE" ]; then
    CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed 's/.*,\s*\([0-9.]*\)\s*id.*/\1/')
fi

# awk 실수 계산기 가동: CPU 사용률 = 100% - 유휴율(CPU_IDLE)
# BEGIN 절을 열어 터미널 환경에 상관없이 부동 소수점(%.1f 포맷) 계산을 정밀 수행합니다.
# 만에 하나 CPU_IDLE가 빈 변수일 경우를 대비해 쉘 매개변수 대체 기본값 문법인 ${CPU_IDLE:-0} 를 적용해 크래시를 원천 차단합니다.
CPU_USAGE=$(awk "BEGIN {printf \"%.1f\", 100 - ${CPU_IDLE:-0}}")

# 2. 메모리 사용률 계산
# free 명세를 grep Mem으로 뽑아 awk로 2번째 컬럼(전체 용량, Total)과 3번째 컬럼(실제 사용량, Used)을 변수로 지정합니다.
MEM_INFO=$(free | grep Mem)
MEM_TOTAL=$(echo "$MEM_INFO" | awk '{print $2}')
MEM_USED=$(echo "$MEM_INFO"  | awk '{print $3}')
# 소수점 한 자리 정밀 백분율 산출: (Used / Total) * 100
MEM_USAGE=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED / $MEM_TOTAL) * 100}")

# 3. 루트 파티션 디스크 사용률 수집
# df / 명령어는 루트('/') 파일 시스템 장치 잔여량을 출력합니다.
# tail -1로 헤더 라인을 제외한 알짜 데이터 행을 선택한 뒤, 5번째 컬럼(Used %)의 퍼센트(%) 기호를 tr -d로 완전 삭제하여 정수만 획득합니다.
DISK_USED=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

# 수집된 3대 물리 정보 실시간 콘솔 출력
echo "CPU Usage  : ${CPU_USAGE}%"
echo "MEM Usage  : ${MEM_USAGE}%"
echo "DISK Used  : ${DISK_USED}%"
echo ""

# ── [4단계] 하드웨어 자원 임계치 위반 감사 및 주의 경고 ────────────────────────
WARN_CPU=false
WARN_MEM=false
WARN_DISK=false

# 1. CPU 경고 판정
# 부동 소수점을 정수형으로 전환하기 위해 printf %.0f 포맷을 수행합니다. (예: 25.3 -> 25)
CPU_INT=$(printf "%.0f" "$CPU_USAGE")
# -gt(Greater than) 연산자로 사전 설정한 threshold(20%)를 넘어섰는지 감별합니다.
if [ "$CPU_INT" -gt "$CPU_THRESHOLD" ]; then
    echo "[WARNING] CPU threshold exceeded (${CPU_USAGE}% > ${CPU_THRESHOLD}%)"
    WARN_CPU=true
fi

# 2. 메모리 경고 판정
MEM_INT=$(printf "%.0f" "$MEM_USAGE")
if [ "$MEM_INT" -gt "$MEM_THRESHOLD" ]; then
    echo "[WARNING] MEM threshold exceeded (${MEM_USAGE}% > ${MEM_THRESHOLD}%)"
    WARN_MEM=true
fi

# 3. 디스크 경고 판정
if [ "$DISK_USED" -gt "$DISK_THRESHOLD" ]; then
    echo "[WARNING] DISK threshold exceeded (${DISK_USED}% > ${DISK_THRESHOLD}%)"
    WARN_DISK=true
fi

# ── [5단계] 시계열 로깅 적재 및 파일 관리 실행 ──────────────────────────────────

# 1. 로그 보존용 폴더 존재 체크 및 자동 권한 복구 생성
if [ ! -d "$LOG_DIR" ]; then
    # mkdir에 -p(parent) 옵션을 동반하여 부모 디렉토리가 없더라도 경로 전반을 순차 생성시킵니다.
    mkdir -p "$LOG_DIR" 2>/dev/null || {
        echo "[ERROR] Cannot create log directory: $LOG_DIR (permission denied?)"
        exit 1
    }
fi

# 2. 로그 누적으로 파일 크기가 과도하게 팽창하기 전에 크기 검사 및 회전(Rotation)을 실시간 집행
rotate_log

# 3. 시계열 관제 데이터 한 행으로 압축 정의
# 포맷 무결성 준증: [YYYY-MM-DD HH:MM:SS] PID:... CPU:..% MEM:..% DISK_USED:..%
LOG_LINE="[$(timestamp)] PID:${APP_PID} CPU:${CPU_USAGE}% MEM:${MEM_USAGE}% DISK_USED:${DISK_USED}%"

# ⚠️ [역사적 누적 보존의 핵]
# 반드시 단일 '>' 덮어쓰기가 아닌 이중 '>>' 어펜드(추가) 연산자를 사용하여 시계열을 유지시킵니다.
echo "$LOG_LINE" >> "$LOG_FILE"

echo ""
echo "[INFO] Log appended: $LOG_FILE"
echo ""
echo "===================================="
