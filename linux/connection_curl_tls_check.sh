#!/usr/bin/env bash
# ============================================================
# curl_hop_check.sh
# Hits a URL N times and records TLS handshake + HTTP status
# Usage: ./curl_hop_check.sh [URL] [HOPS] [AUTH_TOKEN]
# ============================================================

set -uo pipefail

# ---------- defaults ----------
DEFAULT_URL="https://example.com"
DEFAULT_HOPS=100
TIMEOUT=15

# ---------- args ----------
URL="${1:-$DEFAULT_URL}"
HOPS="${2:-$DEFAULT_HOPS}"
AUTH_TOKEN="${3:-}"

# ---------- output files ----------
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="./curl_results_${TIMESTAMP}"
RAW_LOG="${OUTPUT_DIR}/raw.log"
CSV_FILE="${OUTPUT_DIR}/summary.csv"

mkdir -p "$OUTPUT_DIR"

# ---------- colors ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
RESET='\033[0m'

# ---------- curl exit code → reason ----------
curl_error_reason() {
  case "$1" in
    6)  echo "DNS_RESOLVE_FAIL" ;;
    7)  echo "CONN_REFUSED" ;;
    28) echo "TIMEOUT" ;;
    35) echo "TLS_HANDSHAKE_ERROR" ;;
    51) echo "TLS_CERT_MISMATCH" ;;
    52) echo "EMPTY_RESPONSE" ;;
    56) echo "RECV_ERROR" ;;
    60) echo "TLS_CERT_VERIFY_FAIL" ;;
    *)  echo "CURL_ERR_$1" ;;
  esac
}

# ---------- auth header ----------
CURL_AUTH=()
if [[ -n "$AUTH_TOKEN" ]]; then
  CURL_AUTH=(-H "Authorization: Bearer ${AUTH_TOKEN}")
fi

# ---------- banner ----------
echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║           curl TLS + Status Hop Checker             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  ${BOLD}URL    :${RESET} $URL"
echo -e "  ${BOLD}Hops   :${RESET} $HOPS"
echo -e "  ${BOLD}Timeout:${RESET} ${TIMEOUT}s per hop"
echo -e "  ${BOLD}Auth   :${RESET} ${AUTH_TOKEN:+(Bearer token provided)}"
echo -e "  ${BOLD}Output :${RESET} $OUTPUT_DIR"
echo ""

# ---------- CSV header ----------
echo "hop,status_code,error_reason,tcp_connect_s,tls_handshake_s,ttfb_s,total_s,ssl_verify_result,start_time,end_time,wall_time" > "$CSV_FILE"

# ---------- raw log header ----------
{
  echo "=== curl TLS + Status Hop Checker ==="
  echo "URL    : $URL"
  echo "Hops   : $HOPS"
  echo "Started: $(date)"
  echo ""
} > "$RAW_LOG"

# ---------- tracking vars ----------
declare -A STATUS_COUNT
declare -A ERROR_COUNT
TOTAL_TCP=0; TOTAL_TLS=0; TOTAL_TTFB=0; TOTAL_TOTAL=0
MIN_TLS=999; MAX_TLS=0; MIN_TCP=999; MAX_TCP=0
FAIL_COUNT=0

# ---------- main loop ----------
for i in $(seq 1 "$HOPS"); do

  HOP_START=$(date '+%Y-%m-%d %H:%M:%S')
  HOP_START_EPOCH=$(date +%s%3N)

  CURL_OUT=$(curl -sk \
    --max-time "$TIMEOUT" \
    --connect-timeout 10 \
    "${CURL_AUTH[@]+"${CURL_AUTH[@]}"}" \
    -o /dev/null \
    -w "%{http_code}|%{time_connect}|%{time_appconnect}|%{time_starttransfer}|%{time_total}|%{ssl_verify_result}" \
    "$URL" 2>/dev/null)
  CURL_EXIT=$?

  HOP_END=$(date '+%Y-%m-%d %H:%M:%S')
  HOP_WALL_MS=$(( $(date +%s%3N) - HOP_START_EPOCH ))

  if [[ $CURL_EXIT -ne 0 ]]; then
    REASON=$(curl_error_reason "$CURL_EXIT")
    HTTP="000"
    T_TCP="0.000000"; T_TLS="0.000000"; T_TTFB="0.000000"; T_TOT="0.000000"
    SSL_V="$CURL_EXIT"; SSL_LABEL="$REASON"
    COLOR=$MAGENTA
    ((FAIL_COUNT++)) || true
    ERROR_COUNT["$REASON"]=$(( ${ERROR_COUNT["$REASON"]:-0} + 1 ))
  else
    HTTP=$(echo "$CURL_OUT"   | cut -d'|' -f1)
    T_TCP=$(echo "$CURL_OUT"  | cut -d'|' -f2)
    T_TLS=$(echo "$CURL_OUT"  | cut -d'|' -f3)
    T_TTFB=$(echo "$CURL_OUT" | cut -d'|' -f4)
    T_TOT=$(echo "$CURL_OUT"  | cut -d'|' -f5)
    SSL_V=$(echo "$CURL_OUT"  | cut -d'|' -f6)
    REASON="-"
    SSL_LABEL=$([[ "$SSL_V" == "0" ]] && echo "TLS_OK" || echo "TLS_WARN($SSL_V)")

    if   [[ "$HTTP" == 2* ]]; then COLOR=$GREEN
    elif [[ "$HTTP" == 3* ]]; then COLOR=$YELLOW
    else                            COLOR=$RED; fi

    # accumulate timing (only successful hops)
    TOTAL_TCP=$(awk   "BEGIN{print $TOTAL_TCP   + $T_TCP}")
    TOTAL_TLS=$(awk   "BEGIN{print $TOTAL_TLS   + $T_TLS}")
    TOTAL_TTFB=$(awk  "BEGIN{print $TOTAL_TTFB  + $T_TTFB}")
    TOTAL_TOTAL=$(awk "BEGIN{print $TOTAL_TOTAL + $T_TOT}")
    MIN_TCP=$(awk "BEGIN{print ($T_TCP < $MIN_TCP && $T_TCP > 0) ? $T_TCP : $MIN_TCP}")
    MAX_TCP=$(awk "BEGIN{print ($T_TCP > $MAX_TCP) ? $T_TCP : $MAX_TCP}")
    MIN_TLS=$(awk "BEGIN{print ($T_TLS < $MIN_TLS && $T_TLS > 0) ? $T_TLS : $MIN_TLS}")
    MAX_TLS=$(awk "BEGIN{print ($T_TLS > $MAX_TLS) ? $T_TLS : $MAX_TLS}")
  fi

  STATUS_COUNT["$HTTP"]=$(( ${STATUS_COUNT["$HTTP"]:-0} + 1 ))

  # terminal output
  printf "Hop %3d | HTTP=%b%-3s%b | TCP=%9ss | TLS=%9ss | TTFB=%9ss | Total=%9ss | %-22s | start=%s  end=%s  wall=%dms\n" \
    "$i" "$COLOR" "$HTTP" "$RESET" "$T_TCP" "$T_TLS" "$T_TTFB" "$T_TOT" "$SSL_LABEL" "$HOP_START" "$HOP_END" "$HOP_WALL_MS"

  # raw log
  printf "Hop %3d | HTTP=%-3s | TCP=%ss | TLS=%ss | TTFB=%ss | Total=%ss | %-22s | reason=%-20s | start=%s  end=%s  wall=%dms\n" \
    "$i" "$HTTP" "$T_TCP" "$T_TLS" "$T_TTFB" "$T_TOT" "$SSL_LABEL" "$REASON" "$HOP_START" "$HOP_END" "$HOP_WALL_MS" >> "$RAW_LOG"

  echo "$i,$HTTP,$REASON,$T_TCP,$T_TLS,$T_TTFB,$T_TOT,$SSL_V,$HOP_START,$HOP_END,${HOP_WALL_MS}ms" >> "$CSV_FILE"

done

# ---------- summary (terminal only, then write to log separately) ----------
GOOD_COUNT=$(( HOPS - FAIL_COUNT ))
[[ $GOOD_COUNT -le 0 ]] && GOOD_COUNT=1

echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}                        SUMMARY${RESET}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# hop counts
echo ""
printf "  %-22s %d / %d\n" "Successful hops:" "$GOOD_COUNT" "$HOPS"
printf "  %-22s %d / %d\n" "Failed hops:"     "$FAIL_COUNT" "$HOPS"

# HTTP status distribution
echo ""
echo -e "  ${BOLD}HTTP Status Distribution:${RESET}"
for code in $(echo "${!STATUS_COUNT[@]}" | tr ' ' '\n' | sort); do
  if   [[ "$code" == 2*  ]]; then C=$GREEN
  elif [[ "$code" == 3*  ]]; then C=$YELLOW
  elif [[ "$code" == 000 ]]; then C=$MAGENTA
  else C=$RED; fi
  printf "    %b%-8s%b : %d / %d\n" "$C" "HTTP $code" "$RESET" "${STATUS_COUNT[$code]}" "$HOPS"
done

# error breakdown (only if any failures)
if [[ $FAIL_COUNT -gt 0 ]]; then
  echo ""
  echo -e "  ${BOLD}${MAGENTA}Connection / TLS Error Breakdown:${RESET}"
  for err in "${!ERROR_COUNT[@]}"; do
    printf "    ${MAGENTA}%-26s${RESET} : %d times\n" "$err" "${ERROR_COUNT[$err]}"
  done
fi

# timing stats
echo ""
echo -e "  ${BOLD}Timing (successful hops only):${RESET}"
awk -v tcp="$TOTAL_TCP" -v tls="$TOTAL_TLS" -v ttfb="$TOTAL_TTFB" \
    -v tot="$TOTAL_TOTAL" -v n="$GOOD_COUNT" \
    -v min_tcp="$MIN_TCP" -v max_tcp="$MAX_TCP" \
    -v min_tls="$MIN_TLS" -v max_tls="$MAX_TLS" \
  'BEGIN{
    printf "    %-16s avg=%7.4fs   min=%7.4fs   max=%7.4fs\n", "TCP Connect:",   tcp/n, min_tcp, max_tcp
    printf "    %-16s avg=%7.4fs   min=%7.4fs   max=%7.4fs\n", "TLS Handshake:", tls/n, min_tls, max_tls
    printf "    %-16s avg=%7.4fs\n",                           "TTFB:",          ttfb/n
    printf "    %-16s avg=%7.4fs\n",                           "Total:",         tot/n
  }'

echo ""
echo -e "  ${BOLD}Output files:${RESET}"
echo -e "    Raw log : $RAW_LOG"
echo -e "    CSV     : $CSV_FILE"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# write clean summary to log
{
  echo ""
  echo "=== SUMMARY ==="
  echo "Completed : $(date)"
  echo "Successful: $GOOD_COUNT / $HOPS"
  echo "Failed    : $FAIL_COUNT / $HOPS"
  echo ""
  echo "HTTP Status Distribution:"
  for code in $(echo "${!STATUS_COUNT[@]}" | tr ' ' '\n' | sort); do
    printf "  HTTP %-5s: %d / %d\n" "$code" "${STATUS_COUNT[$code]}" "$HOPS"
  done
  if [[ $FAIL_COUNT -gt 0 ]]; then
    echo ""
    echo "Error Breakdown:"
    for err in "${!ERROR_COUNT[@]}"; do
      printf "  %-28s: %d\n" "$err" "${ERROR_COUNT[$err]}"
    done
  fi
  echo ""
  awk -v tcp="$TOTAL_TCP" -v tls="$TOTAL_TLS" -v ttfb="$TOTAL_TTFB" \
      -v tot="$TOTAL_TOTAL" -v n="$GOOD_COUNT" \
      -v min_tcp="$MIN_TCP" -v max_tcp="$MAX_TCP" \
      -v min_tls="$MIN_TLS" -v max_tls="$MAX_TLS" \
    'BEGIN{
      print "Timing (successful hops only):"
      printf "  TCP Connect  : avg=%.4fs  min=%.4fs  max=%.4fs\n", tcp/n, min_tcp, max_tcp
      printf "  TLS Handshake: avg=%.4fs  min=%.4fs  max=%.4fs\n", tls/n, min_tls, max_tls
      printf "  TTFB         : avg=%.4fs\n", ttfb/n
      printf "  Total        : avg=%.4fs\n", tot/n
    }'
} >> "$RAW_LOG"
