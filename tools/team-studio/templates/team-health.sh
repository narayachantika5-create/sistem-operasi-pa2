#!/usr/bin/env bash
# Baca source ini. Ubah prasyarat produk, bukan angka pengukuran.
set -euo pipefail
cpu="$(LC_ALL=C awk '{print $1}' /proc/loadavg)"
memory="$(LC_ALL=C awk '/MemTotal:/ {total=$2} /MemAvailable:/ {avail=$2} END {printf "%.1f%%",100*(total-avail)/total}' /proc/meminfo)"
disk="$(LC_ALL=C df -P / | awk 'NR==2 {print $5}')"
uptime="$(LC_ALL=C awk '{printf "%.0f seconds",$1}' /proc/uptime)"
printf 'CPU_LOAD_1M=%s\nMEMORY_USED=%s\nDISK_USED=%s\nUPTIME=%s\n' \
  "$cpu" "$memory" "$disk" "$uptime"
if command -v cc >/dev/null 2>&1; then
  printf 'COMPILER=available\n'
else
  printf 'COMPILER=missing\n'
fi
printf '%s\n' @HEALTH_MARKER@
