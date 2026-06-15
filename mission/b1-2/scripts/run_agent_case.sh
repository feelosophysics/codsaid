#!/usr/bin/env bash
set -u

CASE_NAME="${1:?case name required}"
MEMORY_LIMIT_VALUE="${2:?memory limit required}"
CPU_MAX_OCCUPY_VALUE="${3:?cpu max occupy required}"
MULTI_THREAD_VALUE="${4:?multi thread flag required}"
SAMPLES="${5:-20}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$ROOT_DIR/evidence/run_workspace"
RAW_DIR="$ROOT_DIR/evidence/raw"
APP="$WORK_DIR/agent-app-leak"

mkdir -p "$RAW_DIR" "$WORK_DIR/agent_home/upload_files" "$WORK_DIR/agent_home/api_keys" "$WORK_DIR/agent_home/logs"
printf 'agent_api_key_test' > "$WORK_DIR/agent_home/api_keys/secret.key"

export AGENT_HOME="$WORK_DIR/agent_home"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys"
export AGENT_LOG_DIR="$AGENT_HOME/logs"
export MEMORY_LIMIT="$MEMORY_LIMIT_VALUE"
export CPU_MAX_OCCUPY="$CPU_MAX_OCCUPY_VALUE"
export MULTI_THREAD_ENABLE="$MULTI_THREAD_VALUE"

APP_LOG="$RAW_DIR/${CASE_NAME}.app.log"
MONITOR_LOG="$RAW_DIR/${CASE_NAME}.monitor.log"
PS_LOG="$RAW_DIR/${CASE_NAME}.ps.log"
TOP_LOG="$RAW_DIR/${CASE_NAME}.top.log"
THREAD_LOG="$RAW_DIR/${CASE_NAME}.threads.log"
EXIT_LOG="$RAW_DIR/${CASE_NAME}.exit.txt"

: > "$APP_LOG"
: > "$MONITOR_LOG"
: > "$PS_LOG"
: > "$TOP_LOG"
: > "$THREAD_LOG"
: > "$EXIT_LOG"

echo "# case=${CASE_NAME} started_at=$(date '+%Y-%m-%d %H:%M:%S %z')" >> "$EXIT_LOG"
echo "# MEMORY_LIMIT=${MEMORY_LIMIT} CPU_MAX_OCCUPY=${CPU_MAX_OCCUPY} MULTI_THREAD_ENABLE=${MULTI_THREAD_ENABLE}" >> "$EXIT_LOG"

"$APP" > "$APP_LOG" 2>&1 &
app_pid=$!

echo "pid=${app_pid}" >> "$EXIT_LOG"
sleep 1

{
  echo "# ps snapshot $(date '+%Y-%m-%d %H:%M:%S %z')"
  ps -ef | grep -E "PID|agent-app-leak" | grep -v grep || true
} >> "$PS_LOG"

{
  echo "# top snapshot $(date '+%Y-%m-%d %H:%M:%S %z')"
  top -b -n 1 -p "$app_pid" || true
} >> "$TOP_LOG"

{
  echo "# ps -L snapshot $(date '+%Y-%m-%d %H:%M:%S %z')"
  ps -L -p "$app_pid" -o pid,tid,stat,pcpu,pmem,rss,vsz,comm || true
} >> "$THREAD_LOG"

PROCESS_NAME="$APP" OUT="$MONITOR_LOG" INTERVAL=1 SAMPLES="$SAMPLES" "$ROOT_DIR/scripts/monitor.sh"

if pgrep -f "$APP" >/dev/null 2>&1; then
  echo "cleanup=SIGTERM" >> "$EXIT_LOG"
  pgrep -f "$APP" | xargs -r kill 2>/dev/null || true
  sleep 1
fi

if pgrep -f "$APP" >/dev/null 2>&1; then
  echo "cleanup=SIGKILL" >> "$EXIT_LOG"
  pgrep -f "$APP" | xargs -r kill -9 2>/dev/null || true
fi

wait "$app_pid" 2>/dev/null
exit_code=$?
echo "exit_code=${exit_code}" >> "$EXIT_LOG"
echo "# case=${CASE_NAME} finished_at=$(date '+%Y-%m-%d %H:%M:%S %z')" >> "$EXIT_LOG"
