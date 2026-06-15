#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT_DIR/evidence/run_workspace/agent-app-leak"
RAW_DIR="$ROOT_DIR/evidence/raw"
WORK_DIR="$ROOT_DIR/evidence/run_workspace"

mkdir -p "$RAW_DIR" "$WORK_DIR/agent_home/upload_files" "$WORK_DIR/agent_home/api_keys" "$WORK_DIR/agent_home/logs"
printf 'agent_api_key_test' > "$WORK_DIR/agent_home/api_keys/secret.key"

export AGENT_HOME="$WORK_DIR/agent_home"
export AGENT_PORT=15034
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys"
export AGENT_LOG_DIR="$AGENT_HOME/logs"
export MEMORY_LIMIT=512
export CPU_MAX_OCCUPY=100
export MULTI_THREAD_ENABLE=false

"$APP" > "$RAW_DIR/cpu-high-late.app.log" 2>&1 &
parent=$!

sleep 27
pids="$(pgrep -f "$APP" | paste -sd, -)"

{
  echo "# late ps $(date '+%Y-%m-%d %H:%M:%S %z')"
  ps -ef | grep agent-app-leak | grep -v grep || true
  echo "pids=$pids"
  if [[ -n "$pids" ]]; then
    ps -p "$pids" -o pid,stat,nlwp,pcpu,pmem,rss,vsz,etime,comm || true
  fi
} > "$RAW_DIR/cpu-high-late.ps.log"

{
  echo "# late top $(date '+%Y-%m-%d %H:%M:%S %z')"
  if [[ -n "$pids" ]]; then
    top -b -n 1 -p "$pids" || true
  fi
} > "$RAW_DIR/cpu-high-late.top.log"

wait "$parent" 2>/dev/null
echo "exit_code=$?" > "$RAW_DIR/cpu-high-late.exit.txt"
