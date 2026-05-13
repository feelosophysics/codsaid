#!/bin/bash
# =============================================================================
# report.sh - monitor.log 통계 분석 리포트 (보너스 1)
# 사용법: ./report.sh [시작시간] [종료시간]
#   예시: ./report.sh "2026-02-25 13:00:00" "2026-02-25 14:00:00"
#         ./report.sh   (시간 미지정 시 전체 로그 분석)
# =============================================================================

LOG_FILE="${AGENT_LOG_DIR:-/var/log/agent-app}/monitor.log"

# ── 인자 처리 ──────────────────────────────────────────────────────────────────
START_TIME="$1"
END_TIME="$2"

if [ ! -f "$LOG_FILE" ]; then
    echo "[ERROR] Log file not found: $LOG_FILE"
    exit 1
fi

# ── 분석 대상 라인 필터링 ──────────────────────────────────────────────────────
if [ -n "$START_TIME" ] && [ -n "$END_TIME" ]; then
    echo "[INFO] Analyzing logs from '$START_TIME' to '$END_TIME'"
    # 시간 범위 필터 (awk로 문자열 비교)
    FILTERED=$(awk -v s="$START_TIME" -v e="$END_TIME" '{
        # 라인에서 타임스탬프 추출: [YYYY-MM-DD HH:MM:SS]
        match($0, /\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\]/, arr)
        if (arr[1] >= s && arr[1] <= e) print
    }' "$LOG_FILE")
else
    echo "[INFO] Analyzing all log entries"
    FILTERED=$(cat "$LOG_FILE")
fi

# 유효한 로그 라인만 필터 (형식: [DATE] PID:... CPU:...% MEM:...% DISK_USED:...%)
VALID=$(echo "$FILTERED" | grep -E '\[.*\] PID:[0-9]+ CPU:[0-9.]+% MEM:[0-9.]+% DISK_USED:[0-9]+%')

SAMPLE_COUNT=$(echo "$VALID" | grep -v "^$" | wc -l)

if [ "$SAMPLE_COUNT" -eq 0 ]; then
    echo "[WARNING] No valid log entries found for analysis."
    exit 0
fi

# ── 통계 계산 함수 ─────────────────────────────────────────────────────────────
# 인자: 필드명(CPU/MEM/DISK_USED), 단위(% 포함)
calc_stats() {
    local field="$1"   # 예: CPU
    local unit="$2"    # 예: %

    # 각 줄에서 값 추출 (예: CPU:25.3%)
    local values
    values=$(echo "$VALID" | grep -oP "${field}:\K[0-9.]+")

    if [ -z "$values" ]; then
        echo "    Average : N/A"
        echo "    Maximum : N/A"
        echo "    Minimum : N/A"
        return
    fi

    # awk로 통계 계산
    echo "$values" | awk -v unit="$unit" '
    BEGIN { max=-1; min=999999; sum=0; count=0 }
    {
        val = $1 + 0
        sum += val
        count++
        if (val > max) { max = val }
        if (val < min) { min = val }
    }
    END {
        printf "    Average : %.1f%s\n", sum/count, unit
        printf "    Maximum : %.1f%s\n", max, unit
        printf "    Minimum : %.1f%s\n", min, unit
    }'
}

# 최댓값/최솟값 발생 시각 계산
calc_max_time() {
    local field="$1"
    echo "$VALID" | awk -v f="$field" '
    BEGIN { max=-1; maxline="" }
    {
        match($0, /\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\]/, ts)
        match($0, f ":" "([0-9.]+)", val)
        if (val[1]+0 > max) { max = val[1]+0; maxline = ts[1] }
    }
    END { printf "    Maximum at : %s\n", maxline }'
}

calc_min_time() {
    local field="$1"
    echo "$VALID" | awk -v f="$field" '
    BEGIN { min=999999; minline="" }
    {
        match($0, /\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\]/, ts)
        match($0, f ":" "([0-9.]+)", val)
        if (val[1]+0 < min) { min = val[1]+0; minline = ts[1] }
    }
    END { printf "    Minimum at : %s\n", minline }'
}

# ── 리포트 출력 ────────────────────────────────────────────────────────────────
echo ""
echo "====== STATISTICS REPORT ======"
echo ""

echo "[CPU]"
calc_stats "CPU" "%"
calc_max_time "CPU"
calc_min_time "CPU"
echo ""

echo "[Memory]"
calc_stats "MEM" "%"
calc_max_time "MEM"
calc_min_time "MEM"
echo ""

echo "[Disk]"
calc_stats "DISK_USED" "%"
echo ""

echo "[Samples]"
echo "    Data Points: $SAMPLE_COUNT samples"
echo ""
echo "================================"
