# curl_hop_check.sh | [Link](https://github.com/UnstopableSafar08/DevOps/blob/main/linux/connection_curl_tls_check.sh)

A bash script that repeatedly hits an HTTPS endpoint N times (default 100) and records **TLS handshake timing**, **HTTP status codes**, **connection errors**, and **per-hop timestamps** — all written to a timestamped output directory with a raw log and CSV file.

Built for diagnosing intermittent TLS flaps, connection timeouts, and latency spikes on production endpoints.


```bash
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
```

---

## Requirements

| Tool | Notes |
|------|-------|
| `bash` 4.0+ | Associative arrays required |
| `curl` | Any recent version |
| `awk` | Standard gawk/mawk |
| `date` | GNU coreutils (`date +%s%3N` for ms precision) |

> On CentOS/Oracle Linux: all present by default.  
> On macOS: install GNU coreutils via `brew install coreutils` and use `gdate`.

---

## Usage

```bash
chmod +x curl_hop_check.sh

# Default: 100 hops to the built-in URL
./curl_hop_check.sh

# Custom URL, 100 hops
./curl_hop_check.sh "https://your-endpoint.example.com/api/path"

# Custom URL + hop count
./curl_hop_check.sh "https://your-endpoint.example.com/api/path" 50

# With Bearer token auth
./curl_hop_check.sh "https://your-endpoint.example.com/api/path" 100 "eyJhbGci..."
```

### Arguments

| Position | Variable | Default | Description |
|----------|----------|---------|-------------|
| `$1` | `URL` | Built-in default URL | Target HTTPS endpoint |
| `$2` | `HOPS` | `100` | Number of curl requests to fire |
| `$3` | `AUTH_TOKEN` | _(empty)_ | Bearer token — injected as `Authorization: Bearer <token>` |

---

## What It Measures Per Hop

Each curl request captures the following via `-w` write-out format:

| Field | curl variable | Description |
|-------|--------------|-------------|
| `HTTP` | `%{http_code}` | HTTP response status code (`200`, `403`, `000` on failure) |
| `TCP` | `%{time_connect}` | Time to complete TCP 3-way handshake |
| `TLS` | `%{time_appconnect}` | Time until TLS handshake completed (includes TCP) |
| `TTFB` | `%{time_starttransfer}` | Time to first byte — server processing time visible here |
| `Total` | `%{time_total}` | Full round-trip time |
| `SSL verify` | `%{ssl_verify_result}` | `0` = cert OK, `19` = self-signed/untrusted CA, other = error code |
| `start` | `date` before curl | Wall clock timestamp when request was fired |
| `end` | `date` after curl | Wall clock timestamp when curl returned |
| `wall` | epoch ms diff | Actual elapsed ms including curl process overhead |

> **Why `wall` matters on failures:** when curl times out, `Total=0.000000s` — but `wall=15013ms` reveals the full 15-second blocking wait that the script experienced.

---

## Error Classification

When curl exits non-zero, the connection never completed. The script maps the exit code to a human-readable label:

| curl exit | Label | Meaning |
|-----------|-------|---------|
| `6` | `DNS_RESOLVE_FAIL` | Could not resolve hostname |
| `7` | `CONN_REFUSED` | Server actively refused TCP connection |
| `28` | `TIMEOUT` | Hit `--max-time` / `--connect-timeout` limit |
| `35` | `TLS_HANDSHAKE_ERROR` | SSL/TLS negotiation failed |
| `51` | `TLS_CERT_MISMATCH` | Cert hostname does not match |
| `52` | `EMPTY_RESPONSE` | Server closed connection with no response |
| `56` | `RECV_ERROR` | Failure receiving network data |
| `60` | `TLS_CERT_VERIFY_FAIL` | CA cert verification failed (`-s` skips this; use without `-s` to catch) |
| other | `CURL_ERR_N` | Unknown curl error N |

Failed hops are recorded as `HTTP=000` and are **excluded from timing averages** so they do not skew your min/max/avg stats.

---

## Output

### Terminal (live, color-coded)

```
╔══════════════════════════════════════════════════════╗
║           curl TLS + Status Hop Checker             ║
╚══════════════════════════════════════════════════════╝

  URL    : https://resources.geniustv.geniussystems.com.np
  Hops   : 100
  Timeout: 15s per hop
  Auth   :
  Output : ./curl_results_20260625_152230

Hop   1 | HTTP=200 | TCP= 0.016613s | TLS= 0.466508s | TTFB= 0.469260s | Total= 0.469299s | TLS_OK                | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=492ms
Hop   2 | HTTP=200 | TCP= 0.017179s | TLS= 0.021412s | TTFB= 0.024013s | Total= 0.024042s | TLS_OK                | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=32ms
Hop   3 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | TIMEOUT               | start=2026-06-25 15:22:30  end=2026-06-25 15:22:45  wall=15013ms
Hop   4 | HTTP=000 | TCP= 0.019800s | TLS= 0.000000s | TTFB= 0.000000s | Total= 15.001s   | TLS_HANDSHAKE_ERROR   | start=2026-06-25 15:22:45  end=2026-06-25 15:23:00  wall=15021ms
Hop   5 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | DNS_RESOLVE_FAIL      | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=9ms
Hop   6 | HTTP=000 | TCP= 0.003100s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.031200s | TLS_CERT_VERIFY_FAIL  | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=34ms
Hop   7 | HTTP=200 | TCP= 0.002900s | TLS= 0.007100s | TTFB= 0.009700s | Total= 0.009800s | TLS_WARN(19)          | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=18ms
Hop   8 | HTTP=403 | TCP= 0.003200s | TLS= 0.007600s | TTFB= 0.010300s | Total= 0.010400s | TLS_OK                | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=19ms
Hop   9 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | CONN_REFUSED          | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=5ms
Hop  10 | HTTP=200 | TCP= 0.003000s | TLS= 0.006900s | TTFB= 0.009300s | Total= 0.009400s | TLS_OK                | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=17ms
...
```

**Color coding:**

| Color | Meaning |
|-------|---------|
| 🟢 Green | `2xx` — success |
| 🟡 Yellow | `3xx` — redirect |
| 🔴 Red | `4xx` / `5xx` — client/server error |
| 🟣 Magenta | `000` — connection or TLS failure (never reached server) |

### Summary Block

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Successful hops:       95 / 100
  Failed hops:           5 / 100

  HTTP Status Distribution:
    HTTP 200     : 94 / 100
    HTTP 403     : 1  / 100
    HTTP 000     : 5  / 100

  Connection / TLS Error Breakdown:
    TIMEOUT                    : 2 times
    TLS_HANDSHAKE_ERROR        : 1 times
    DNS_RESOLVE_FAIL           : 1 times
    CONN_REFUSED               : 1 times

  Timing (successful hops only):
    TCP Connect:     avg= 0.0072s   min= 0.0050s   max= 0.0620s
    TLS Handshake:   avg= 0.0905s   min= 0.0760s   max= 0.3710s
    TTFB:            avg= 0.1028s
    Total:           avg= 0.1028s

  Output files:
    Raw log : ./curl_results_20260625_152230/raw.log
    CSV     : ./curl_results_20260625_152230/summary.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> The error breakdown section only appears when at least one hop fails — on a clean run it is omitted.

---

## Output Files

Every run creates a timestamped directory: `./curl_results_YYYYMMDD_HHMMSS/`

```
curl_results_20260625_152230/
├── raw.log        # Human-readable log of every hop + summary
└── summary.csv    # Machine-readable CSV for import into Excel / Grafana / etc.
```

### raw.log

```
=== curl TLS + Status Hop Checker ===
URL    : https://resources.geniustv.geniussystems.com.np
Hops   : 100
Started: Wed Jun 25 15:22:30 +0545 2026

Hop   1 | HTTP=200 | TCP=0.016613s | TLS=0.466508s | TTFB=0.469260s | Total=0.469299s | TLS_OK                | reason=-                    | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=492ms
Hop   2 | HTTP=200 | TCP=0.017179s | TLS=0.021412s | TTFB=0.024013s | Total=0.024042s | TLS_OK                | reason=-                    | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=32ms
Hop   3 | HTTP=000 | TCP=0.000000s | TLS=0.000000s | TTFB=0.000000s | Total=0.000000s | TIMEOUT               | reason=TIMEOUT              | start=2026-06-25 15:22:30  end=2026-06-25 15:22:45  wall=15013ms
...

=== SUMMARY ===
Completed : Wed Jun 25 15:24:01 +0545 2026
Successful: 95 / 100
Failed    : 5 / 100

HTTP Status Distribution:
  HTTP 200  : 94 / 100
  HTTP 403  : 1  / 100
  HTTP 000  : 5  / 100

Error Breakdown:
  TIMEOUT                       : 2
  TLS_HANDSHAKE_ERROR           : 1
  DNS_RESOLVE_FAIL              : 1
  CONN_REFUSED                  : 1

Timing (successful hops only):
  TCP Connect  : avg=0.0072s  min=0.0050s  max=0.0620s
  TLS Handshake: avg=0.0905s  min=0.0760s  max=0.3710s
  TTFB         : avg=0.1028s
  Total        : avg=0.1028s
```

### summary.csv

```csv
hop,status_code,error_reason,tcp_connect_s,tls_handshake_s,ttfb_s,total_s,ssl_verify_result,start_time,end_time,wall_time
1,200,-,0.016613,0.466508,0.469260,0.469299,0,2026-06-25 15:22:30,2026-06-25 15:22:30,492ms
2,200,-,0.017179,0.021412,0.024013,0.024042,0,2026-06-25 15:22:30,2026-06-25 15:22:30,32ms
3,000,TIMEOUT,0.000000,0.000000,0.000000,0.000000,28,2026-06-25 15:22:30,2026-06-25 15:22:45,15013ms
4,000,TLS_HANDSHAKE_ERROR,0.019800,0.000000,0.000000,15.001300,35,2026-06-25 15:22:45,2026-06-25 15:23:00,15021ms
5,000,DNS_RESOLVE_FAIL,0.000000,0.000000,0.000000,0.000000,6,2026-06-25 15:23:00,2026-06-25 15:23:00,9ms
6,403,-,0.003200,0.007600,0.010300,0.010400,0,2026-06-25 15:23:00,2026-06-25 15:23:00,19ms
```

CSV columns:

| Column | Description |
|--------|-------------|
| `hop` | Sequence number (1 to N) |
| `status_code` | HTTP status, or `000` for connection failures |
| `error_reason` | `-` on success, or the error label (e.g. `TIMEOUT`) |
| `tcp_connect_s` | TCP connect time in seconds |
| `tls_handshake_s` | TLS handshake completion time in seconds |
| `ttfb_s` | Time to first byte in seconds |
| `total_s` | Total curl time in seconds |
| `ssl_verify_result` | `0` = OK, other = OpenSSL/NSS error code |
| `start_time` | Wall clock timestamp before curl fired |
| `end_time` | Wall clock timestamp after curl returned |
| `wall_time` | Actual elapsed time in ms (reliable even on timeout) |

---

## Reading the Results

### Healthy endpoint (all 200, stable TLS)

```
Hop   1 | HTTP=200 | TCP= 0.003100s | TLS= 0.007400s | TTFB= 0.009800s | Total= 0.009900s | TLS_OK   | start=... wall=17ms
Hop   2 | HTTP=200 | TCP= 0.002900s | TLS= 0.006900s | TTFB= 0.009200s | Total= 0.009300s | TLS_OK   | start=... wall=16ms
```

TCP ~3ms, TLS ~7ms, steady — everything nominal.

### TLS resumption visible on hop 1

The first hop often shows a much higher TLS time (e.g. `0.4665s`) because it performs a **full TLS handshake**. Subsequent hops reuse the session via TLS session tickets, dropping to `~7ms`. If hop 1 is always slow and the rest are fast, this is expected behaviour — not a problem.

### Intermittent timeout

```
Hop  47 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | TIMEOUT  | start=2026-06-25 15:22:47  end=2026-06-25 15:23:02  wall=15013ms
```

TCP never connected — possible upstream load balancer dropping connections, firewall conntrack table full, or server overloaded. The `start`/`end` timestamps let you correlate with server logs.

### TLS handshake failure (TCP OK, TLS failed)

```
Hop  83 | HTTP=000 | TCP= 0.019800s | TLS= 0.000000s | TTFB= 0.000000s | Total= 15.001s   | TLS_HANDSHAKE_ERROR | start=... wall=15021ms
```

TCP connected (`TCP=0.0198s`) but TLS negotiation failed and hit the timeout. Common causes: cipher mismatch, expired cert, SNI misconfiguration, or HAProxy SSL offload issue.

### Self-signed / internal CA cert (`TLS_WARN(19)`)

```
Hop   7 | HTTP=200 | TCP= 0.002900s | TLS= 0.007100s | TTFB= 0.009700s | Total= 0.009800s | TLS_WARN(19) | ...
```

The request succeeded (`HTTP=200`) but the cert could not be verified against the system CA bundle. Script uses `-sk` (skip verify) so it continues. This is normal when hitting endpoints signed by an internal CA (e.g. F1Soft Root CA) from a machine that does not have the internal CA installed in its trust store.

---

## Timeouts Configuration

Two timeout values are hard-coded at the top of the script:

```bash
TIMEOUT=15          # --max-time: total curl operation limit
CONNECT_TIMEOUT=10  # --connect-timeout: TCP connect limit
```

Adjust these for faster or slower networks before running.

---

## Tips

**Run in background for long hop counts:**
```bash
nohup ./curl_hop_check.sh "https://your-url.com" 500 > run.log 2>&1 &
```

**Watch live while logging:**
```bash
./curl_hop_check.sh "https://your-url.com" 100 | tee live_output.txt
```

**Import CSV into quick analysis:**
```bash
# Average TLS handshake across successful hops
awk -F',' 'NR>1 && $2 != "000" {sum+=$5; n++} END{printf "avg TLS: %.4fs\n", sum/n}' summary.csv

# Count timeouts
grep -c "TIMEOUT" summary.csv
```

---

## Author

Ocean (Sagar Malla) — DevOps / Infrastructure Engineer  
GitHub: [UnstopableSafar08](https://github.com/UnstopableSafar08)  
Blog: [blogs.sagarmalla.info.np](https://blogs.sagarmalla.info.np)
