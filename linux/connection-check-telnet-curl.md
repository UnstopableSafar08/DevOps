# Net Check Tool — Overview

A bash menu script for testing connectivity to a domain via **telnet** (raw port check) or **curl** (HTTPS request), with repeat-count batching, color-coded output, auto-logging, and a success/fail summary per batch.

**Core features:**
- Interactive menu: `1` telnet, `2` curl, `3` exit
- After picking 1 or 2, prompts for a repeat count (positive integer only, re-prompts on bad input)
- Runs that action N times, tagging each attempt `run i/N`
- Prints a batch summary at the end — success count, fail count, and per-failure cause/status detail
- Logs everything (plain text, no color codes) to `/tmp/<domain>-<timestamp>.txt`
- Flags: `-h`/`--help` (usage), `--dry-run` (preview commands without making real connections)
- Accepts `domain` and `port` as optional positional args (defaults: `example.com` 80)

---

Create a new file `net_check.sh` (update as per yours) and paste the below contents on it. 

```bash
#!/usr/bin/env bash
# Author : Sagar Malla
# Updated on : 19th-Jun-2026
# Net check tool: telnet or curl a domain, colored msgs, logs to /tmp

set -uo pipefail

# ---- colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # reset

DOMAIN="example.com"
PORT=80
LOGDIR="/tmp"
DRY_RUN=0

usage() {
    cat <<EOF
Net Check Tool — telnet or curl a domain, color output, auto-logged.
After picking telnet (1) or curl (2), you'll be asked how many times
to repeat that action before returning to the menu.

Usage: $(basename "$0") [OPTIONS] [DOMAIN] [PORT]

Options:
  -h, --help     Show this help, exit
  --dry-run      Show commands that would run, skip actual network calls
                 (still writes a log file)

Arguments:
  DOMAIN         Target domain (default: example.com)
  PORT           Port for telnet check (default: 80)

Examples:
  $(basename "$0")                      # menu, default domain/port
  $(basename "$0") example.com 443       # menu, custom domain/port
  $(basename "$0") --dry-run example.com # preview commands, no real calls
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            if [ "$DOMAIN" = "example.com" ] && [ -z "${_domain_set:-}" ]; then
                DOMAIN="$1"
                _domain_set=1
            else
                PORT="$1"
            fi
            shift
            ;;
    esac
done

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOGFILE="${LOGDIR}/${DOMAIN}-${TIMESTAMP}.txt"

log() {
    # write to logfile, plain (no color codes)
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" >> "$LOGFILE"
}

msg_info()  { echo -e "${BLUE}[INFO]${NC} $1";  log "INFO: $1"; }
msg_ok()    { echo -e "${GREEN}[OK]${NC} $1";   log "OK: $1"; }
msg_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; log "WARN: $1"; }
msg_err()   { echo -e "${RED}[ERR]${NC} $1";    log "ERR: $1"; }

check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# set by run_telnet/run_curl after each attempt, read by batch loop
LAST_STATUS=""      # "ok" or "fail"
LAST_REASON=""       # human cause string, only meaningful on fail
LAST_HTTP_CODE=""    # curl only, blank for telnet

prompt_repeat_count() {
    local count
    while true; do
        echo -n "How many times to run this? (integer): " >&2
        read -r count
        if [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -ge 1 ]; then
            echo "$count"
            return 0
        fi
        echo -e "${YELLOW}[WARN]${NC} Bad value '${count}'. Enter a positive integer." >&2
        log "WARN: Bad repeat-count input '${count}'"
    done
}

print_batch_summary() {
    local action="$1"
    local success_count="$2"
    local fail_count="$3"
    local fail_details="$4"   # newline-separated detail lines, may be empty

    echo ""
    echo -e "${CYAN}--- ${action} batch summary ---${NC}"
    echo -e "${GREEN}Success: ${success_count}${NC}"
    echo -e "${RED}Failed:  ${fail_count}${NC}"
    log "SUMMARY: ${action} success=${success_count} fail=${fail_count}"

    if [ "$fail_count" -gt 0 ] && [ -n "$fail_details" ]; then
        echo -e "${RED}Failure details:${NC}"
        while IFS= read -r detail; do
            [ -z "$detail" ] && continue
            echo -e "  ${RED}•${NC} ${detail}"
            log "SUMMARY-DETAIL: ${detail}"
        done <<< "$fail_details"
    fi
    echo ""
}

run_telnet() {
    if ! check_cmd telnet; then
        msg_err "telnet not installed. Install: apt-get install telnet / yum install telnet"
        LAST_STATUS="fail"
        LAST_REASON="telnet binary not installed"
        return 1
    fi
    msg_info "Telnet → ${DOMAIN}:${PORT} ..."
    log "CMD: telnet ${DOMAIN} ${PORT}"

    if [ "$DRY_RUN" -eq 1 ]; then
        msg_warn "[DRY-RUN] Would run: timeout 8 telnet ${DOMAIN} ${PORT}"
        LAST_STATUS="ok"
        LAST_REASON="dry-run, no real attempt"
        return 0
    fi

    # telnet is interactive and won't exit on its own after connecting,
    # so: (1) feed it closed stdin so it exits right after connect instead
    # of idling until the timeout, and (2) trust "Connected to" in the
    # output over the exit code, since timeout killing an idle-but-open
    # session still reports rc=124 even though the connection succeeded.
    if output=$(timeout 8 telnet "$DOMAIN" "$PORT" </dev/null 2>&1); then
        rc=0
    else
        rc=$?
    fi
    echo "$output" | tee -a "$LOGFILE"

    if echo "$output" | grep -qi "Connected to"; then
        msg_ok "Telnet connected to ${DOMAIN}:${PORT}"
        LAST_STATUS="ok"
        LAST_REASON=""
    elif [ "$rc" -eq 124 ]; then
        msg_err "Telnet timed out (8s), no connection confirmed to ${DOMAIN}:${PORT}"
        LAST_STATUS="fail"
        LAST_REASON="timed out after 8s with no 'Connected to' (port likely filtered/firewalled, or host unreachable)"
        return 1
    else
        msg_err "Telnet failed, exit code ${rc}. See ${LOGFILE}"
        LAST_STATUS="fail"
        LAST_REASON="telnet exit code ${rc} (connection refused or DNS/host error — see log)"
        return 1
    fi
}

run_curl() {
    if ! check_cmd curl; then
        msg_err "curl not installed. Install: apt-get install curl / yum install curl"
        LAST_STATUS="fail"
        LAST_REASON="curl binary not installed"
        return 1
    fi
    msg_info "Curl → https://${DOMAIN} ..."
    log "CMD: curl -v --max-time 10 https://${DOMAIN}"

    if [ "$DRY_RUN" -eq 1 ]; then
        msg_warn "[DRY-RUN] Would run: curl -v --max-time 10 https://${DOMAIN}"
        LAST_STATUS="ok"
        LAST_REASON="dry-run, no real attempt"
        return 0
    fi

    if output=$(curl -v --max-time 10 "https://${DOMAIN}" 2>&1); then
        echo "$output" >> "$LOGFILE"
        http_code=$(echo "$output" | grep -E '^< HTTP/' | tail -1 | sed -E 's/^< HTTP\/[^ ]+ ([0-9]+).*/\1/')
        LAST_HTTP_CODE="${http_code:-unknown}"

        if [[ "$http_code" =~ ^[23][0-9][0-9]$ ]]; then
            msg_ok "Curl done. HTTP code: ${http_code}. Full output → ${LOGFILE}"
            LAST_STATUS="ok"
            LAST_REASON=""
        else
            deny_reason=$(echo "$output" | grep -i 'x-deny-reason' | sed -E 's/.*x-deny-reason:[[:space:]]*//I' | tr -d '\r')
            if [ -n "$deny_reason" ]; then
                cause="HTTP ${LAST_HTTP_CODE}, denied: ${deny_reason}"
            elif [ -z "$http_code" ]; then
                cause="no HTTP status line in response (connection may have dropped mid-handshake)"
            else
                cause="server returned non-success HTTP ${LAST_HTTP_CODE}"
            fi
            msg_warn "Curl completed but got HTTP ${LAST_HTTP_CODE}: ${cause}"
            LAST_STATUS="fail"
            LAST_REASON="$cause"
            return 1
        fi
    else
        rc=$?
        echo "$output" >> "$LOGFILE"
        msg_err "Curl failed, exit code ${rc}. See ${LOGFILE}"
        LAST_HTTP_CODE="none"
        case "$rc" in
            6)  LAST_REASON="exit ${rc} — could not resolve host (DNS failure)" ;;
            7)  LAST_REASON="exit ${rc} — could not connect (refused or host unreachable)" ;;
            28) LAST_REASON="exit ${rc} — operation timed out (10s)" ;;
            35) LAST_REASON="exit ${rc} — SSL/TLS handshake failed" ;;
            60) LAST_REASON="exit ${rc} — SSL certificate problem (untrusted/expired)" ;;
            *)  LAST_REASON="exit ${rc} — see curl manpage EXIT CODES section" ;;
        esac
        LAST_STATUS="fail"
        return 1
    fi
}

show_menu() {
    echo -e "${CYAN}=========================================${NC}"
    echo -e "${CYAN}  Net Check Tool — target: ${DOMAIN}${NC}"
    echo -e "${CYAN}=========================================${NC}"
    echo "1. telnet"
    echo "2. curl"
    echo "3. exit"
    echo -n "Choose [1-3]: "
}

main() {
    log "=== Session start, domain=${DOMAIN} ==="
    msg_info "Logging to ${LOGFILE}"

    while true; do
        show_menu
        read -r choice
        case "$choice" in
            1)
                n=$(prompt_repeat_count)
                success_count=0
                fail_count=0
                fail_details=""
                for ((i = 1; i <= n; i++)); do
                    msg_info "--- telnet run ${i}/${n} ---"
                    run_telnet
                    if [ "$LAST_STATUS" = "ok" ]; then
                        success_count=$((success_count + 1))
                    else
                        fail_count=$((fail_count + 1))
                        fail_details="${fail_details}run ${i}/${n}: ${LAST_REASON}
"
                    fi
                done
                print_batch_summary "telnet" "$success_count" "$fail_count" "$fail_details"
                ;;
            2)
                n=$(prompt_repeat_count)
                success_count=0
                fail_count=0
                fail_details=""
                for ((i = 1; i <= n; i++)); do
                    msg_info "--- curl run ${i}/${n} ---"
                    run_curl
                    if [ "$LAST_STATUS" = "ok" ]; then
                        success_count=$((success_count + 1))
                    else
                        fail_count=$((fail_count + 1))
                        fail_details="${fail_details}run ${i}/${n}: ${LAST_REASON}
"
                    fi
                done
                print_batch_summary "curl" "$success_count" "$fail_count" "$fail_details"
                ;;
            3)
                msg_info "Exit. Log saved: ${LOGFILE}"
                log "=== Session end ==="
                exit 0
                ;;
            *)
                msg_warn "Bad choice '${choice}'. Pick 1, 2, or 3."
                ;;
        esac
        echo ""
    done
}

main
```


## Dummy output — `--help`

```
$ ./net_check.sh --help
Net Check Tool — telnet or curl a domain, color output, auto-logged.
After picking telnet (1) or curl (2), you'll be asked how many times
to repeat that action before returning to the menu.

Usage: net_check.sh [OPTIONS] [DOMAIN] [PORT]

Options:
  -h, --help     Show this help, exit
  --dry-run      Show commands that would run, skip actual network calls
                 (still writes a log file)

Arguments:
  DOMAIN         Target domain (default: example.com)
  PORT           Port for telnet check (default: 80)

Examples:
  net_check.sh                          # menu, default domain/port
  net_check.sh example.com 443          # menu, custom domain/port
  net_check.sh --dry-run example.com    # preview commands, no real calls
```

---

## Dummy output — curl, all success

```
$ ./net_check.sh example.com 443
[INFO] Logging to /tmp/example.com-20260619-101500.txt
=========================================
  Net Check Tool — target: example.com
=========================================
1. telnet
2. curl
3. exit
Choose [1-3]: 2
How many times to run this? (integer): 5
[INFO] --- curl run 1/5 ---
[INFO] Curl → https://example.com ...
[OK] Curl done. HTTP code: 200. Full output → /tmp/example.com-20260619-101500.txt
[INFO] --- curl run 2/5 ---
[OK] Curl done. HTTP code: 200. Full output → /tmp/example.com-20260619-101500.txt
[INFO] --- curl run 3/5 ---
[OK] Curl done. HTTP code: 200. Full output → /tmp/example.com-20260619-101500.txt
[INFO] --- curl run 4/5 ---
[OK] Curl done. HTTP code: 200. Full output → /tmp/example.com-20260619-101500.txt
[INFO] --- curl run 5/5 ---
[OK] Curl done. HTTP code: 200. Full output → /tmp/example.com-20260619-101500.txt

--- curl batch summary ---
Success: 5
Failed:  0

=========================================
  Net Check Tool — target: example.com
=========================================
1. telnet
2. curl
3. exit
Choose [1-3]: 3
[INFO] Exit. Log saved: /tmp/example.com-20260619-101500.txt
```

---

## Dummy output — telnet, mixed result (with failure detail)

```
Choose [1-3]: 1
How many times to run this? (integer): 4
[INFO] --- telnet run 1/4 ---
Trying xxx.xxx.xxx.xxx...
Connected to example.com.
Escape character is '^]'.
[OK] Telnet connected to example.com:443
[INFO] --- telnet run 2/4 ---
Trying xxx.xxx.xxx.xxx...
Connected to example.com.
Escape character is '^]'.
[OK] Telnet connected to example.com:443
[INFO] --- telnet run 3/4 ---
Trying xxx.xxx.xxx.xxx...
[ERR] Telnet timed out (8s), no connection confirmed to example.com:443
[INFO] --- telnet run 4/4 ---
Trying xxx.xxx.xxx.xxx...
Connected to example.com.
Escape character is '^]'.
[OK] Telnet connected to example.com:443

--- telnet batch summary ---
Success: 3
Failed:  1
Failure details:
  • run 3/4: timed out after 8s with no 'Connected to' (port likely filtered/firewalled, or host unreachable)
```

---

## Dummy output — `--dry-run`

```
$ ./net_check.sh --dry-run example.com 443
Choose [1-3]: 2
How many times to run this? (integer): 2
[INFO] --- curl run 1/2 ---
[WARN] [DRY-RUN] Would run: curl -v --max-time 10 https://example.com
[INFO] --- curl run 2/2 ---
[WARN] [DRY-RUN] Would run: curl -v --max-time 10 https://example.com

--- curl batch summary ---
Success: 2
Failed:  0
```
