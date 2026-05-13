#!/bin/bash
# =============================================================================
# archive.sh - 시간 기반 로그 보존 정책 (보너스 2)
# - 7일 경과 로그 → gzip 압축
# - 압축 파일 → /var/log/monitor/agent-app/archive/ 이동
# - 30일 경과 아카이브 → 삭제
# =============================================================================

LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
ARCHIVE_DIR="/var/log/monitor/agent-app/archive"
COMPRESS_DAYS=7
DELETE_DAYS=30

echo "[$(date '+%Y-%m-%d %H:%M:%S')] archive.sh started"

# ── 아카이브 디렉토리 확인/생성 ────────────────────────────────────────────────
if [ ! -d "$ARCHIVE_DIR" ]; then
    mkdir -p "$ARCHIVE_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[ERROR] Cannot create archive directory: $ARCHIVE_DIR (permission denied?)"
        exit 1
    fi
    echo "[INFO] Created archive directory: $ARCHIVE_DIR"
fi

# ── 로그 디렉토리 확인 ─────────────────────────────────────────────────────────
if [ ! -d "$LOG_DIR" ]; then
    echo "[WARNING] Log directory not found: $LOG_DIR — nothing to archive."
    exit 0
fi

# ── 1단계: 7일 경과 *.log 파일 압축 ───────────────────────────────────────────
echo ""
echo "[STEP 1] Compressing log files older than ${COMPRESS_DAYS} days..."

COMPRESS_TARGETS=$(find "$LOG_DIR" -maxdepth 1 -name "*.log" -mtime "+${COMPRESS_DAYS}" 2>/dev/null)

if [ -z "$COMPRESS_TARGETS" ]; then
    echo "[INFO] No log files older than ${COMPRESS_DAYS} days. Skipping compression."
else
    COMPRESS_COUNT=0
    while IFS= read -r logfile; do
        if [ ! -r "$logfile" ]; then
            echo "[WARNING] Cannot read '$logfile' — skipping (permission denied?)"
            continue
        fi
        echo "  Compressing: $logfile"
        gzip "$logfile" 2>/dev/null
        if [ $? -eq 0 ]; then
            COMPRESS_COUNT=$((COMPRESS_COUNT + 1))
        else
            echo "[WARNING] Failed to compress: $logfile"
        fi
    done <<< "$COMPRESS_TARGETS"
    echo "[INFO] Compressed ${COMPRESS_COUNT} file(s)."
fi

# ── 2단계: 압축 파일을 아카이브 디렉토리로 이동 ────────────────────────────────
echo ""
echo "[STEP 2] Moving compressed files to archive: $ARCHIVE_DIR"

MOVE_TARGETS=$(find "$LOG_DIR" -maxdepth 1 -name "*.log.gz" 2>/dev/null)

if [ -z "$MOVE_TARGETS" ]; then
    echo "[INFO] No compressed files to move. Skipping."
else
    MOVE_COUNT=0
    while IFS= read -r gzfile; do
        echo "  Moving: $gzfile → $ARCHIVE_DIR/"
        mv "$gzfile" "$ARCHIVE_DIR/" 2>/dev/null
        if [ $? -eq 0 ]; then
            MOVE_COUNT=$((MOVE_COUNT + 1))
        else
            echo "[WARNING] Failed to move: $gzfile (permission denied?)"
        fi
    done <<< "$MOVE_TARGETS"
    echo "[INFO] Moved ${MOVE_COUNT} file(s) to archive."
fi

# ── 3단계: 30일 경과 아카이브 삭제 ────────────────────────────────────────────
echo ""
echo "[STEP 3] Deleting archive files older than ${DELETE_DAYS} days..."

DELETE_TARGETS=$(find "$ARCHIVE_DIR" -maxdepth 1 -name "*.gz" -mtime "+${DELETE_DAYS}" 2>/dev/null)

if [ -z "$DELETE_TARGETS" ]; then
    echo "[INFO] No archive files older than ${DELETE_DAYS} days. Skipping deletion."
else
    DELETE_COUNT=0
    while IFS= read -r gzfile; do
        echo "  Deleting: $gzfile"
        rm -f "$gzfile" 2>/dev/null
        if [ $? -eq 0 ]; then
            DELETE_COUNT=$((DELETE_COUNT + 1))
        else
            echo "[WARNING] Failed to delete: $gzfile (permission denied?)"
        fi
    done <<< "$DELETE_TARGETS"
    echo "[INFO] Deleted ${DELETE_COUNT} archive file(s)."
fi

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] archive.sh completed."
