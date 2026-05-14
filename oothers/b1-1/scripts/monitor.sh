#!/bin/bash
# =============================================================================
# monitor.sh - 시스템 관제 자동화 스크립트
# 위치: $AGENT_HOME/bin/monitor.sh
# 소유자: agent-dev / 그룹: agent-core / 권한: 750
# =============================================================================

# ── 설정 변수 ──────────────────────────────────────────────────────────────────
APP_PROCESS="agent-app"           # 감시할 프로세스명
APP_PORT=15034                    # 감시할 포트
LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
LOG_FILE="$LOG_DIR/monitor.log"
MAX_LOG_SIZE_MB=10                # 로그 최대 크기 (MB)
MAX_LOG_FILES=10                  # 최대 보관 파일 수

# 임계값
CPU_THRESHOLD=20
MEM_THRESHOLD=10
DISK_THRESHOLD=80

# ── 함수 정의 ──────────────────────────────────────────────────────────────────

# 현재 타임스탬프
timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

# 로그 파일 용량 관리 (10MB 초과 시 로테이션)
rotate_log() {
    if [ ! -f "$LOG_FILE" ]; then
        return
    fi

    local size_bytes
    size_bytes=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    local max_bytes=$((MAX_LOG_SIZE_MB * 1024 * 1024))

    if [ "$size_bytes" -ge "$max_bytes" ]; then
        # 기존 백업 파일들을 한 단계씩 밀어냄
        for i in $(seq $((MAX_LOG_FILES - 1)) -1 1); do
            if [ -f "${LOG_FILE}.$i" ]; then
                mv "${LOG_FILE}.$i" "${LOG_FILE}.$((i + 1))"
            fi
        done
        # 현재 로그를 .1로 백업
        mv "$LOG_FILE" "${LOG_FILE}.1"
        # 최대 개수 초과 파일 삭제
        local oldest="${LOG_FILE}.$((MAX_LOG_FILES + 1))"
        [ -f "$oldest" ] && rm -f "$oldest"
    fi
}

# ── 출력 헤더 ──────────────────────────────────────────────────────────────────
echo ""
echo "====== SYSTEM MONITOR RESULT ======"
echo ""

# ── [1] Health Check ───────────────────────────────────────────────────────────
echo "[HEALTH CHECK]"

# 프로세스 확인
APP_PID=$(pgrep -f "$APP_PROCESS" | head -1)
if [ -z "$APP_PID" ]; then
    echo "Checking process '$APP_PROCESS'... [FAIL] (Process not running)"
    echo "[$(timestamp)] HEALTH CHECK FAILED: process '$APP_PROCESS' not found" >> "$LOG_FILE"
    exit 1
else
    echo "Checking process '$APP_PROCESS'... [OK] (PID: $APP_PID)"
fi

# 포트 확인
PORT_LISTEN=$(ss -tulnp 2>/dev/null | grep ":${APP_PORT} " | grep -c LISTEN)
if [ "$PORT_LISTEN" -eq 0 ]; then
    echo "Checking port $APP_PORT... [FAIL] (Port not listening)"
    echo "[$(timestamp)] HEALTH CHECK FAILED: port $APP_PORT not listening" >> "$LOG_FILE"
    exit 1
else
    echo "Checking port $APP_PORT... [OK]"
fi

echo ""

# ── [2] 방화벽 상태 점검 ───────────────────────────────────────────────────────
echo "[FIREWALL CHECK]"

FIREWALL_OK=false

# UFW 확인
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | grep -i "Status:" | awk '{print $2}')
    if [ "$UFW_STATUS" = "active" ]; then
        echo "Firewall (UFW)... [OK] (active)"
        FIREWALL_OK=true
    fi
fi

# firewalld 확인 (UFW가 없거나 비활성인 경우)
if [ "$FIREWALL_OK" = false ] && command -v firewall-cmd &>/dev/null; then
    FWD_STATUS=$(sudo firewall-cmd --state 2>/dev/null)
    if [ "$FWD_STATUS" = "running" ]; then
        echo "Firewall (firewalld)... [OK] (running)"
        FIREWALL_OK=true
    fi
fi

if [ "$FIREWALL_OK" = false ]; then
    echo "[WARNING] Firewall is not active! System may be exposed."
fi

echo ""

# ── [3] 리소스 수집 ────────────────────────────────────────────────────────────
echo "[RESOURCE MONITORING]"

# CPU 사용률 (idle을 뺀 값)
# CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | tr -d '%')
# 이 줄로 교체하세요 (숫자와 소수점만 순수하게 뽑아내는 코드)
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed -n 's/.*, *\([0-9.]*\) *id.*/\1/p')
# top 출력 포맷이 환경마다 다를 수 있어 fallback 처리
if [ -z "$CPU_IDLE" ]; then
    CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed 's/.*,\s*\([0-9.]*\)\s*id.*/\1/')
fi
CPU_USAGE=$(awk "BEGIN {printf \"%.1f\", 100 - ${CPU_IDLE:-0}}")

# 메모리 사용률
MEM_INFO=$(free | grep Mem)
MEM_TOTAL=$(echo "$MEM_INFO" | awk '{print $2}')
MEM_USED=$(echo "$MEM_INFO"  | awk '{print $3}')
MEM_USAGE=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED / $MEM_TOTAL) * 100}")

# 디스크 사용률 (루트 파티션)
DISK_USED=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

echo "CPU Usage  : ${CPU_USAGE}%"
echo "MEM Usage  : ${MEM_USAGE}%"
echo "DISK Used  : ${DISK_USED}%"
echo ""

# ── [4] 임계값 경고 ────────────────────────────────────────────────────────────
WARN_CPU=false
WARN_MEM=false
WARN_DISK=false

# CPU 경고
CPU_INT=$(printf "%.0f" "$CPU_USAGE")
if [ "$CPU_INT" -gt "$CPU_THRESHOLD" ]; then
    echo "[WARNING] CPU threshold exceeded (${CPU_USAGE}% > ${CPU_THRESHOLD}%)"
    WARN_CPU=true
fi

# MEM 경고
MEM_INT=$(printf "%.0f" "$MEM_USAGE")
if [ "$MEM_INT" -gt "$MEM_THRESHOLD" ]; then
    echo "[WARNING] MEM threshold exceeded (${MEM_USAGE}% > ${MEM_THRESHOLD}%)"
    WARN_MEM=true
fi

# DISK 경고
if [ "$DISK_USED" -gt "$DISK_THRESHOLD" ]; then
    echo "[WARNING] DISK threshold exceeded (${DISK_USED}% > ${DISK_THRESHOLD}%)"
    WARN_DISK=true
fi

# ── [5] 로그 기록 ──────────────────────────────────────────────────────────────
# 로그 디렉토리 없으면 생성 시도
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR" 2>/dev/null || {
        echo "[ERROR] Cannot create log directory: $LOG_DIR"
        exit 1
    }
fi

# 로테이션 실행
rotate_log

# 로그 한 줄 기록
LOG_LINE="[$(timestamp)] PID:${APP_PID} CPU:${CPU_USAGE}% MEM:${MEM_USAGE}% DISK_USED:${DISK_USED}%"
echo "$LOG_LINE" >> "$LOG_FILE"

echo ""
echo "[INFO] Log appended: $LOG_FILE"
echo ""
echo "===================================="
