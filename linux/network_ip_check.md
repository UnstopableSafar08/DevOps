The script scans a network range (e.g. 10.13.134.0/24) and does two things for every IP address in that range:

- Pings it — to check if the host is alive and reachable.
- Connects to port 22 (you can change) via telnet — to check if SSH is open on that host.

At the end, it saves the results into two files — one for hosts that passed both checks, and one for hosts that failed — plus a full timestamped log of everything.

```bash
#!/usr/bin/env bash
# =============================================================================
# subnet_scan.sh
# Description : Ping all hosts in a given subnet and test port 22 via telnet
# Usage       : ./subnet_scan.sh <subnet/cidr>  e.g.  ./subnet_scan.sh 10.10.10.0/24
# =============================================================================

# ── Colour definitions ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
RESET='\033[0m'
BOLD='\033[1m'

# ── Configuration ─────────────────────────────────────────────────────────────
TARGET_PORT=22
PING_COUNT=1
PING_TIMEOUT=1        # seconds per ping attempt
TELNET_TIMEOUT=3      # seconds for port-connect attempt
LOG_FILE="subnet_scan_$(date +%Y%m%d).log"
PING_TELNET_OK_FILE="ping_telnet_ok.txt"
UNREACHABLE_FILE="unreachable_ip_port.txt"

# ── Helper: print a banner line ───────────────────────────────────────────────
banner() {
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo -e "${BOLD}${WHITE}  Subnet Scanner  |  Port: ${TARGET_PORT}  |  $(date '+%Y-%m-%d %H:%M:%S')${RESET}"
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
}

# ── Helper: timestamped log ───────────────────────────────────────────────────
log() {
    # Strip ANSI colour codes before writing to the log file
    local clean
    clean=$(echo -e "$*" | sed 's/\x1B\[[0-9;]*[mK]//g')
    echo "$(date '+%Y-%m-%d %H:%M:%S')  $clean" > "$LOG_FILE"
}

# ── Helper: print + log ───────────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${RESET}  $*";    log "[INFO]  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*";   log "[OK]    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*";  log "[WARN]  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*";     log "[ERROR] $*"; }
result()  { echo -e "${MAGENTA}[STAT]${RESET} $*";  log "[STAT]  $*"; }

# ── Dependency check ──────────────────────────────────────────────────────────
check_dependencies() {
    local missing=0
    for cmd in ping telnet timeout awk; do
        if ! command -v "$cmd" &>/dev/null; then
            error "Required command not found: ${BOLD}${cmd}${RESET}"
            missing=1
        fi
    done
    [[ $missing -ne 0 ]] && exit 1
}

# ── Validate CIDR input ───────────────────────────────────────────────────────
validate_cidr() {
    local cidr="$1"
    if [[ ! "$cidr" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        error "Invalid CIDR format: '${cidr}'. Expected format: X.X.X.X/N"
        exit 1
    fi

    local ip prefix
    ip="${cidr%/*}"
    prefix="${cidr#*/}"

    # Validate each octet
    IFS='.' read -r -a octets <<< "$ip"
    for octet in "${octets[@]}"; do
        if (( octet < 0 || octet > 255 )); then
            error "IP address octet out of range: ${octet}"
            exit 1
        fi
    done

    # Validate prefix length
    if (( prefix < 0 || prefix > 32 )); then
        error "CIDR prefix out of range: /${prefix}  (must be 0-32)"
        exit 1
    fi
}

# ── Convert IP string to integer ──────────────────────────────────────────────
ip_to_int() {
    local ip="$1"
    local a b c d
    IFS='.' read -r a b c d <<< "$ip"
    echo $(( (a << 24) + (b << 16) + (c << 8) + d ))
}

# ── Convert integer to IP string ──────────────────────────────────────────────
int_to_ip() {
    local int="$1"
    echo "$(( (int >> 24) & 255 )).$(( (int >> 16) & 255 )).$(( (int >> 8) & 255 )).$(( int & 255 ))"
}

# ── Generate all host IPs from CIDR (excludes network & broadcast) ────────────
generate_hosts() {
    local cidr="$1"
    local ip prefix mask host_count net_int first last i

    ip="${cidr%/*}"
    prefix="${cidr#*/}"

    # /32 edge case – single host
    if (( prefix == 32 )); then
        echo "$ip"
        return
    fi

    mask=$(( 0xFFFFFFFF << (32 - prefix) & 0xFFFFFFFF ))
    net_int=$(( $(ip_to_int "$ip") & mask ))
    host_count=$(( (1 << (32 - prefix)) - 2 ))   # exclude network & broadcast

    if (( host_count <= 0 )); then
        error "Subnet /${prefix} has no usable host addresses."
        exit 1
    fi

    first=$(( net_int + 1 ))
    last=$(( net_int + host_count ))

    for (( i = first; i <= last; i++ )); do
        int_to_ip "$i"
    done
}

# ── Ping a single host ────────────────────────────────────────────────────────
ping_host() {
    local ip="$1"
    if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$ip" &>/dev/null; then
        return 0   # reachable
    fi
    return 1       # unreachable
}

# ── Test TCP port using telnet ────────────────────────────────────────────────
# telnet is interactive and does not have a built-in connect-only mode, so we:
#   1. Feed it an immediate EOF via </dev/null so it exits right after connecting
#   2. Wrap it in 'timeout' to enforce a hard deadline
#   3. Capture stderr+stdout and look for the "Connected" banner that telnet
#      prints when the TCP handshake succeeds
#   4. Treat "Connection refused" or a timeout as a closed/filtered port
test_port() {
    local ip="$1"
    local port="$2"
    local output

    # Run telnet with a forced EOF; capture all output (telnet writes to stderr)
    output=$(timeout "$TELNET_TIMEOUT" telnet "$ip" "$port" </dev/null 2>&1)
    local exit_code=$?

    # timeout exits with 124 when the deadline is exceeded
    if [[ $exit_code -eq 124 ]]; then
        warn "${BOLD}${BLUE}${ip}${RESET} -- Port ${port} timed out after ${TELNET_TIMEOUT}s (filtered?)"
        return 1
    fi

    # A successful TCP connection always produces "Connected to <host>" in the output
    if echo "$output" | grep -qi "^Connected"; then
        return 0   # port open
    fi

    # Common failure strings from telnet
    if echo "$output" | grep -qi "Connection refused"; then
        return 1   # port actively refused
    fi

    # Any other outcome (no route, host unreachable, etc.) is treated as closed
    return 1
}

# ── Scan a single IP ──────────────────────────────────────────────────────────
scan_ip() {
    local ip="$1"
    local pad="${BOLD}${BLUE}${ip}${RESET}"

    # ---- Ping ----------------------------------------------------------------
    if ping_host "$ip"; then
        success "${pad} -- Ping OK"

        # ---- Port test -------------------------------------------------------
        if test_port "$ip" "$TARGET_PORT"; then
            success "${pad} -- Port ${TARGET_PORT} OPEN"
        else
            warn    "${pad} -- Port ${TARGET_PORT} CLOSED, REFUSED, or FILTERED"
        fi

    else
        error "${pad} -- Host UNREACHABLE (no ping response)"
    fi
}

# ── Print summary ─────────────────────────────────────────────────────────────
print_summary() {
    local total="$1" up="$2" down="$3" open="$4" closed="$5"
    echo ""
    echo -e "${BOLD}${CYAN}------------------------------------------------------------${RESET}"
    echo -e "${BOLD}${WHITE}  Scan Summary${RESET}"
    echo -e "${BOLD}${CYAN}------------------------------------------------------------${RESET}"
    result "Total hosts scanned : ${BOLD}${total}${RESET}"
    result "Hosts up (ping OK)  : ${BOLD}${GREEN}${up}${RESET}"
    result "Hosts down          : ${BOLD}${RED}${down}${RESET}"
    result "Port ${TARGET_PORT} open        : ${BOLD}${GREEN}${open}${RESET}"
    result "Port ${TARGET_PORT} closed/filt : ${BOLD}${YELLOW}${closed}${RESET}"
    result "Log file saved to   : ${BOLD}${MAGENTA}${LOG_FILE}${RESET}"
    result "Reachable hosts     : ${BOLD}${MAGENTA}${PING_TELNET_OK_FILE}${RESET}"
    result "Unreachable hosts   : ${BOLD}${MAGENTA}${UNREACHABLE_FILE}${RESET}"
    echo -e "${BOLD}${CYAN}------------------------------------------------------------${RESET}"
}

# ── Graceful interrupt handler ────────────────────────────────────────────────
trap_ctrl_c() {
    echo ""
    warn "Scan interrupted by user (SIGINT). Partial results may be logged."
    print_summary "$total_hosts" "$hosts_up" "$hosts_down" "$port_open" "$port_closed"
    exit 130
}

# =============================================================================
# Main
# =============================================================================
main() {
    # ---- Argument check -------------------------------------------------------
    if [[ $# -ne 1 ]]; then
        echo -e "${RED}${BOLD}Usage:${RESET} $0 <subnet/cidr>"
        echo -e "  Example: $0 10.10.10.0/24"
        exit 1
    fi

    local subnet="$1"

    # ---- Pre-flight checks ----------------------------------------------------
    check_dependencies
    validate_cidr "$subnet"

    # ---- Collect host list ----------------------------------------------------
    mapfile -t hosts < <(generate_hosts "$subnet")
    total_hosts=${#hosts[@]}

    if [[ $total_hosts -eq 0 ]]; then
        error "No hosts generated from subnet: ${subnet}"
        exit 1
    fi

    # ---- Initialise counters --------------------------------------------------
    hosts_up=0
    hosts_down=0
    port_open=0
    port_closed=0

    # ---- Initialise result files ----------------------------------------------
    {
        echo "# ============================================================"
        echo "# Ping OK + Port ${TARGET_PORT} Open"
        echo "# Subnet  : ${subnet}"
        echo "# Scanned : $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# ============================================================"
        echo "# IP Address"
        echo "# ------------------------------------------------------------"
    } > "$PING_TELNET_OK_FILE"

    {
        echo "# ============================================================"
        echo "# Unreachable Hosts / Port ${TARGET_PORT} Closed or Filtered"
        echo "# Subnet  : ${subnet}"
        echo "# Scanned : $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# ============================================================"
        echo "# IP Address          | Reason"
        echo "# ------------------------------------------------------------"
    } > "$UNREACHABLE_FILE"


    trap trap_ctrl_c SIGINT

    # ---- Banner ---------------------------------------------------------------
    banner
    info "Target subnet : ${BOLD}${subnet}${RESET}"
    info "Usable hosts  : ${BOLD}${total_hosts}${RESET}"
    info "Target port   : ${BOLD}${TARGET_PORT}${RESET}"
    info "Log file      : ${BOLD}${LOG_FILE}${RESET}"
    info "OK output     : ${BOLD}${PING_TELNET_OK_FILE}${RESET}"
    info "Fail output   : ${BOLD}${UNREACHABLE_FILE}${RESET}"
    echo ""

    # ---- Main scan loop -------------------------------------------------------
    for ip in "${hosts[@]}"; do
        # Ping
        if ping_host "$ip"; then
            (( hosts_up++ ))
            success "${BOLD}${BLUE}${ip}${RESET} -- Ping OK"

            # Port test
            if test_port "$ip" "$TARGET_PORT"; then
                (( port_open++ ))
                success "${BOLD}${BLUE}${ip}${RESET} -- Port ${TARGET_PORT} OPEN"
                # Record as fully reachable
                printf "%-20s\n" "$ip" >> "$PING_TELNET_OK_FILE"
            else
                (( port_closed++ ))
                warn    "${BOLD}${BLUE}${ip}${RESET} -- Port ${TARGET_PORT} CLOSED, REFUSED, or FILTERED"
                # Ping OK but port failed
                printf "%-20s | Port %s closed/refused/filtered\n" "$ip" "$TARGET_PORT" >> "$UNREACHABLE_FILE"
            fi
        else
            (( hosts_down++ ))
            error "${BOLD}${BLUE}${ip}${RESET} -- Host UNREACHABLE"
            # Host did not respond to ping at all
            printf "%-20s | Host unreachable (no ping response)\n" "$ip" >> "$UNREACHABLE_FILE"
        fi

        # Log each result
        log "Host: ${ip} | Ping: $([ $((hosts_up + hosts_down)) -gt 0 ] && \
            ping_host "$ip" &>/dev/null && echo UP || echo DOWN) | Port ${TARGET_PORT}: $(test_port "$ip" "$TARGET_PORT" &>/dev/null && echo OPEN || echo CLOSED)"
    done

    # ---- Summary --------------------------------------------------------------
    print_summary "$total_hosts" "$hosts_up" "$hosts_down" "$port_open" "$port_closed"
}

main "$@"
```

```bash
chmod +x subnet_scan.sh
./subnet_scan.sh 10.13.134.0/24
```


E.g. OUTPUT:
```bash
./subnet_scan.sh 10.13.134.0/24
============================================================
  Subnet Scanner  |  Port: 22  |  2026-02-18 13:25:09
============================================================
[INFO]  Target subnet : 10.13.134.0/24
[INFO]  Usable hosts  : 254
[INFO]  Target port   : 22
[INFO]  Log file      : subnet_scan_20260218_132509.log

[OK]    10.13.134.1 -- Ping OK
[WARN]  10.13.134.1 -- Port 22 timed out after 3s (filtered?)
[WARN]  10.13.134.1 -- Port 22 CLOSED, REFUSED, or FILTERED
[OK]    10.13.134.2 -- Ping OK
[OK]    10.13.134.2 -- Port 22 OPEN
[ERROR] 10.13.134.3 -- Host UNREACHABLE
[ERROR] 10.13.134.4 -- Host UNREACHABLE
[ERROR] 10.13.134.5 -- Host UNREACHABLE
[ERROR] 10.13.134.6 -- Host UNREACHABLE
[ERROR] 10.13.134.7 -- Host UNREACHABLE
[ERROR] 10.13.134.8 -- Host UNREACHABLE
[ERROR] 10.13.134.9 -- Host UNREACHABLE
[OK]    10.13.134.10 -- Ping OK
[OK]    10.13.134.10 -- Port 22 OPEN
[OK]    10.13.134.11 -- Ping OK
[OK]    10.13.134.11 -- Port 22 OPEN
[OK]    10.13.134.12 -- Ping OK
```

LOGS_file:
```bash
total 130260
-rw-------. 1 root root      1352 Jan 26 10:30 anaconda-ks.cfg
-rwxr-xr-x  1 root root     13851 Feb 18 13:30 subnet_scan.sh
-rw-r--r--  1 root root        67 Feb 18 13:31 subnet_scan_20260218.log
-rw-r--r--  1 root root       973 Feb 18 13:31 unreachable_ip_port.txt
```



Ping and Telnet Fine log:
```bash
cat ping_telnet_ok.txt 
# ============================================================
# Ping OK + Port 22 Open
# Subnet  : 10.13.134.0/24
# Scanned : 2026-02-18 13:30:40
# ============================================================
# IP Address
# ------------------------------------------------------------
10.13.134.2         
10.13.134.10        
10.13.134.11        
10.13.134.12        
10.13.134.13        
10.13.134.14        
10.13.134.15        
10.13.134.16        
10.13.134.20        
10.13.134.21        
```

Unreachable and telnet failed log;
```bash
cat unreachable_ip_port.txt 
# ============================================================
# Unreachable Hosts / Port 22 Closed or Filtered
# Subnet  : 10.13.134.0/24
# Scanned : 2026-02-18 13:30:40
# ============================================================
# IP Address          | Reason
# ------------------------------------------------------------
10.13.134.1          | Port 22 closed/refused/filtered
10.13.134.3          | Host unreachable (no ping response)
10.13.134.4          | Host unreachable (no ping response)
10.13.134.5          | Host unreachable (no ping response)
10.13.134.6          | Host unreachable (no ping response)
10.13.134.7          | Host unreachable (no ping response)
10.13.134.8          | Host unreachable (no ping response)
10.13.134.9          | Host unreachable (no ping response)
10.13.134.17         | Host unreachable (no ping response)
10.13.134.18         | Host unreachable (no ping response)
10.13.134.19         | Host unreachable (no ping response)
10.13.134.29         | Host unreachable (no ping response)
```
