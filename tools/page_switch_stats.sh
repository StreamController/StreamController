#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${1:-$HOME/.local/share/streamcontroller-git/data/logs/logs.log}"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "Log file not found: $LOG_FILE" >&2
  exit 1
fi

tmp_total="$(mktemp)"
tmp_wait="$(mktemp)"
trap 'rm -f "$tmp_total" "$tmp_wait"' EXIT

rg -N "\\[page-switch\\].*total_ms=" "$LOG_FILE" | sed -E 's/.*total_ms=([0-9.]+).*/\1/' > "$tmp_total" || true
rg -N "\\[page-switch\\].*wait_for_tick_ms=" "$LOG_FILE" | sed -E 's/.*wait_for_tick_ms=([0-9.]+).*/\1/' > "$tmp_wait" || true

count="$(awk 'NF{c++} END{print c+0}' "$tmp_total")"
if [[ "$count" -eq 0 ]]; then
  echo "No [page-switch] metrics found in $LOG_FILE"
  exit 0
fi

avg_total="$(awk 'NF{s+=$1;c++} END{if(c) printf "%.1f", s/c; else print "0.0"}' "$tmp_total")"
max_total="$(awk 'NF{if($1>m)m=$1} END{printf "%.1f", m+0}' "$tmp_total")"
avg_wait="$(awk 'NF{s+=$1;c++} END{if(c) printf "%.1f", s/c; else print "0.0"}' "$tmp_wait")"
max_wait="$(awk 'NF{if($1>m)m=$1} END{printf "%.1f", m+0}' "$tmp_wait")"

total_sorted="$(mktemp)"
trap 'rm -f "$tmp_total" "$tmp_wait" "$total_sorted"' EXIT
sort -n "$tmp_total" > "$total_sorted"

p50_total="$(awk 'NF{a[++n]=$1} END{if(n){idx=int((n+1)*0.50); if(idx<1) idx=1; if(idx>n) idx=n; printf "%.1f", a[idx]} else print "0.0"}' "$total_sorted")"
p95_total="$(awk 'NF{a[++n]=$1} END{if(n){idx=int((n+1)*0.95); if(idx<1) idx=1; if(idx>n) idx=n; printf "%.1f", a[idx]} else print "0.0"}' "$total_sorted")"

echo "Page Switch Metrics ($LOG_FILE)"
echo "count=$count avg_total_ms=$avg_total p50_total_ms=$p50_total p95_total_ms=$p95_total max_total_ms=$max_total avg_wait_ms=$avg_wait max_wait_ms=$max_wait"
echo
echo "Recent samples:"
rg -N "\\[page-switch\\].*total_ms=" "$LOG_FILE" | tail -n 10

echo
echo "Recent phase samples:"
rg -N "\\[page-switch-phase\\].*(initialize_actions_ms|brightness_ms|screensaver_ms|phase=background|phase=screensaver|phase=gc)" "$LOG_FILE" | tail -n 15
