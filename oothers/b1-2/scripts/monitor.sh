#!/usr/bin/env bash
set -u

PROCESS_NAME="${PROCESS_NAME:-agent-app-leak}"
PID="${PID:-}"
OUT="${OUT:-monitor.log}"
INTERVAL="${INTERVAL:-1}"
SAMPLES="${SAMPLES:-0}"

usage() {
  cat <<'USAGE'
Usage:
  PROCESS_NAME=agent-app-leak OUT=evidence/raw/oom.monitor.log ./scripts/monitor.sh
  PID=12345 OUT=evidence/raw/deadlock.monitor.log INTERVAL=1 SAMPLES=30 ./scripts/monitor.sh

Environment:
  PROCESS_NAME  Process name or command pattern to find when PID is not set.
  PID           Exact process id to monitor.
  OUT           Output log path. Default: monitor.log
  INTERVAL      Seconds between samples. Default: 1
  SAMPLES       Number of samples. 0 means run until the process disappears.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "$(dirname "$OUT")"

find_pids() {
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    printf '%s\n' "$PID"
    return 0
  fi

  pgrep -f "$PROCESS_NAME" | while read -r candidate; do
    if [[ "$candidate" != "$$" && "$candidate" != "$PPID" ]]; then
      printf '%s\n' "$candidate"
    fi
  done
}

{
  echo "# monitor.sh started_at=$(date '+%Y-%m-%d %H:%M:%S %z') process=${PROCESS_NAME} pid=${PID:-auto} interval=${INTERVAL}s samples=${SAMPLES}"
  echo "# timestamp,pid,state,threads,cpu_percent,mem_percent,rss_kb,vsz_kb,etime,command"
} >> "$OUT"

count=0
while true; do
  target_pids="$(find_pids || true)"

  if [[ -z "$target_pids" ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'),PID_NOT_FOUND,process=${PROCESS_NAME}" >> "$OUT"
    break
  fi

  ps_lines="$(ps -p "$(echo "$target_pids" | paste -sd, -)" -o pid=,stat=,nlwp=,pcpu=,pmem=,rss=,vsz=,etime=,comm= 2>/dev/null || true)"
  if [[ -z "$ps_lines" ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'),PID_GONE,pids=$(echo "$target_pids" | paste -sd, -)" >> "$OUT"
    break
  fi

  while read -r ps_line; do
    [[ -z "$ps_line" ]] && continue
    read -r pid state threads cpu mem rss vsz etime command <<< "$ps_line"
    echo "$(date '+%Y-%m-%d %H:%M:%S'),${pid},${state},${threads},${cpu},${mem},${rss},${vsz},${etime},${command}" >> "$OUT"
  done <<< "$ps_lines"

  if command -v ps >/dev/null 2>&1; then
    {
      echo "# thread snapshot $(date '+%Y-%m-%d %H:%M:%S') pids=$(echo "$target_pids" | paste -sd, -)"
      ps -L -p "$(echo "$target_pids" | paste -sd, -)" -o pid,tid,stat,pcpu,pmem,comm 2>/dev/null || true
    } >> "$OUT"
  fi

  count=$((count + 1))
  if [[ "$SAMPLES" -gt 0 && "$count" -ge "$SAMPLES" ]]; then
    echo "# monitor.sh reached sample limit at $(date '+%Y-%m-%d %H:%M:%S %z')" >> "$OUT"
    break
  fi

  sleep "$INTERVAL"
done
