# OpenVPN + TOTP Automated Login Script

A cross-platform bash script to automate OpenVPN authentication with
Time-based One-Time Password (TOTP). Supports macOS, Linux, and Windows WSL.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
  - [macOS](#macos)
  - [Linux](#linux)
  - [Windows WSL](#windows-wsl)
- [Configuration](#configuration)
- [Usage](#usage)
- [Environment Variable Overrides](#environment-variable-overrides)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)

---

## How It Works

```
vpn.sh connect
      |
      |-- Detects platform (macOS / Linux / WSL)
      |-- Checks dependencies (openvpn, oathtool)
      |-- Validates config values
      |
      |-- oathtool reads TOTP_SECRET
      |       generates a 6-digit OTP code
      |
      |-- Writes /tmp/.vpn_auth_<pid>   [chmod 600]
      |       Line 1: username
      |       Line 2: password + OTP
      |
      |-- sudo openvpn --daemon
      |       starts OpenVPN in background
      |
      |-- Polls for tun/utun interface
      |       confirms tunnel is up
      |       prints assigned VPN IP
      |
      |-- trap EXIT
              deletes temp auth file
```

---

## Requirements

| Tool        | macOS                        | Linux                              | WSL                                |
|-------------|------------------------------|------------------------------------|------------------------------------|
| `openvpn`   | `brew install openvpn`       | `sudo apt install openvpn`         | `sudo apt install openvpn`         |
| `oathtool`  | `brew install oath-toolkit`  | `sudo apt install oathtool`        | `sudo apt install oathtool`        |
| `ip`        | Not required (uses ifconfig) | `sudo apt install iproute2`        | `sudo apt install iproute2`        |
| `bash`      | Built-in (v3.2+)             | Built-in                           | Built-in                           |
| `.ovpn`     | From your VPN provider       | From your VPN provider             | From your VPN provider             |

---

## Installation

### macOS

**Step 1 — Install Homebrew**

If you do not have Homebrew installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Verify it installed correctly:

```bash
brew --version
```

---

**Step 2 — Install OpenVPN and oathtool**

```bash
brew install openvpn oath-toolkit
```

Verify both are installed:

```bash
openvpn --version
oathtool --version
```

---

**Step 3 — Place your .ovpn config file**

Copy the `.ovpn` file provided by your VPN administrator to a known path:

```bash
mkdir -p ~/vpn
cp ~/Downloads/your_config.ovpn ~/vpn/client.ovpn
```

---

**Step 4 — Download the script**

```bash
#!/usr/bin/env bash
# ============================================================
# Author: Sagar Malla
# Date: 2024-06-20
# openvpn-otp-connect.sh
# Automated OpenVPN login with TOTP/OTP — macOS + Linux
# Dependencies: openvpn, oathtool
# ============================================================

set -euo pipefail

# ── Detect Platform ──────────────────────────────────────────
detect_platform() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        PLATFORM="macos"
    elif grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
        PLATFORM="wsl"
    elif [[ "$(uname -s)" == "Linux" ]]; then
        PLATFORM="linux"
    else
        PLATFORM="unknown"
    fi
}

detect_platform

# ── Static Defaults (override via env vars) ──────────────────
VPN_CONFIG="${OPENVPN_CONFIG:-/Users/sagarmalla/sagar.malla__ssl_vpn_config.ovpn}"
VPN_USER="${OPENVPN_USER:-your_VPN_user_name_here}"
VPN_PASS="${OPENVPN_PASS:-your_VPN_user_password_here}"
TOTP_SECRET="${TOTP_SECRET:-your_VPN_TOTP_secret_here}" # e.g JBxxxxxxxxPXP
AUTH_FILE="/tmp/.vpn_auth_$$"
LOG_FILE="/tmp/openvpn.log"
MAX_RETRIES="${OPENVPN_RETRIES:-3}"
RETRY_DELAY="${OPENVPN_RETRY_DELAY:-5}"

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Logging helpers ───────────────────────────────────────────
info()    { echo -e "${GREEN}  [OK]   ${NC}${BOLD}$*${NC}"; }
warn()    { echo -e "${YELLOW}  [WARN] ${NC}${YELLOW}$*${NC}"; }
error()   { echo -e "${RED}  [ERR]  ${NC}${RED}${BOLD}$*${NC}" >&2; }
step()    { echo -e "${CYAN}  [....] ${NC}${BOLD}$*${NC}"; }
dim()     { echo -e "${DIM}         $*${NC}"; }
section() {
    echo ""
    echo -e "${BLUE}${BOLD}  ════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}    $*${NC}"
    echo -e "${BLUE}${BOLD}  ════════════════════════════════${NC}"
}

# ── Cleanup ───────────────────────────────────────────────────
cleanup() {
    rm -f "$AUTH_FILE"
    dim "Temp auth file removed."
}
trap cleanup EXIT INT TERM

# ── Dependency check ──────────────────────────────────────────
check_deps() {
    section "Checking Dependencies  [platform: $PLATFORM]"
    local missing=()

    for cmd in openvpn oathtool; do
        if command -v "$cmd" &>/dev/null; then
            info "$cmd is installed"
            dim "$(command -v "$cmd")"
        else
            error "$cmd is not installed"
            missing+=("$cmd")
        fi
    done

    # Check network tool per platform
    if [[ "$PLATFORM" == "macos" ]]; then
        if command -v ifconfig &>/dev/null; then
            info "ifconfig is available"
        else
            error "ifconfig not found"
            missing+=("ifconfig")
        fi
    else
        # Linux / WSL — prefer ip, fallback to ifconfig
        if command -v ip &>/dev/null; then
            info "ip is available"
        elif command -v ifconfig &>/dev/null; then
            info "ifconfig is available (fallback)"
        else
            error "No network tool found (ip or ifconfig)"
            missing+=("iproute2 or net-tools")
        fi
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        warn "Install missing dependencies:"
        if [[ "$PLATFORM" == "macos" ]]; then
            dim "brew install openvpn oath-toolkit"
        elif [[ "$PLATFORM" == "wsl" ]]; then
            dim "sudo apt install openvpn oathtool iproute2"
            dim "Note: WSL may need extra steps — see WSL notes below"
        else
            dim "sudo apt install openvpn oathtool iproute2    # Debian/Ubuntu"
            dim "sudo dnf install openvpn oathtool iproute     # Fedora/RHEL"
        fi
        exit 1
    fi
}

# ── Validate config ───────────────────────────────────────────
validate_config() {
    section "Validating Configuration"
    local errors=0

    if [[ -n "$VPN_USER" ]]; then
        info "Username     : $VPN_USER"
    else
        error "VPN_USER is empty"
        (( errors++ ))
    fi

    if [[ -n "$VPN_PASS" ]]; then
        info "Password     : ${VPN_PASS:0:2}$(printf '*%.0s' {1..5})  (masked)"
    else
        error "VPN_PASS is empty"
        (( errors++ ))
    fi

    if [[ -z "$TOTP_SECRET" ]]; then
        error "TOTP_SECRET is empty"
        (( errors++ ))
    elif [[ ${#TOTP_SECRET} -lt 16 ]]; then
        error "TOTP_SECRET looks too short — check your Base32 secret"
        (( errors++ ))
    else
        info "TOTP Secret  : ${TOTP_SECRET:0:4}$(printf '*%.0s' {1..10})  (masked)"
    fi

    if [[ -f "$VPN_CONFIG" ]]; then
        info "VPN Config   : $VPN_CONFIG"
    else
        error "VPN config not found: $VPN_CONFIG"
        dim "Set OPENVPN_CONFIG=/path/to/your.ovpn"
        (( errors++ ))
    fi

    info "Platform     : $PLATFORM"
    dim "Log File     : $LOG_FILE"
    dim "Max Retries  : $MAX_RETRIES"

    if [[ $errors -gt 0 ]]; then
        echo ""
        error "Found $errors error(s). Fix them and retry."
        exit 1
    fi
}

# ── Generate OTP ──────────────────────────────────────────────
generate_otp() {
    local otp
    if ! otp=$(oathtool --base32 --totp "$TOTP_SECRET" 2>/dev/null); then
        error "Failed to generate OTP — check your TOTP_SECRET is valid Base32"
        exit 1
    fi
    echo "$otp"
}

# ── Write auth file ───────────────────────────────────────────
write_auth_file() {
    local otp="$1"
    install -m 600 /dev/null "$AUTH_FILE"
    printf '%s\n%s%s\n' "$VPN_USER" "$VPN_PASS" "$otp" > "$AUTH_FILE"
    dim "Auth file -> $AUTH_FILE  [chmod 600]"
}

# ── Tunnel detection (cross-platform) ────────────────────────
tunnel_is_up() {
    if [[ "$PLATFORM" == "macos" ]]; then
        # macOS uses utun0, utun1, utun2 ...
        ifconfig 2>/dev/null | grep -q "^utun\|^tun"
    elif command -v ip &>/dev/null; then
        # Linux / WSL with iproute2
        ip link show 2>/dev/null | grep -q "^[0-9]*: tun"
    else
        # Linux fallback using ifconfig
        ifconfig 2>/dev/null | grep -q "^tun"
    fi
}

# ── Get tunnel interface name and IP ─────────────────────────
get_tunnel_info() {
    local iface vpn_ip

    if [[ "$PLATFORM" == "macos" ]]; then
        iface=$(ifconfig 2>/dev/null | grep -o "^utun[0-9]*\|^tun[0-9]*" | head -1)
        vpn_ip=$(ifconfig "$iface" 2>/dev/null | awk '/inet /{print $2}')
    elif command -v ip &>/dev/null; then
        iface=$(ip link show 2>/dev/null | awk -F': ' '/tun/{print $2; exit}')
        vpn_ip=$(ip addr show "$iface" 2>/dev/null | awk '/inet /{gsub(/\/.*/, "", $2); print $2}')
    else
        iface=$(ifconfig 2>/dev/null | grep -o "^tun[0-9]*" | head -1)
        vpn_ip=$(ifconfig "$iface" 2>/dev/null | awk '/inet /{print $2}')
    fi

    echo "$iface $vpn_ip"
}

# ── Wait for tunnel ───────────────────────────────────────────
wait_for_tunnel() {
    local timeout=30 elapsed=0
    step "Waiting for tunnel interface..."

    while [[ $elapsed -lt $timeout ]]; do
        if tunnel_is_up; then
            echo ""
            read -r iface vpn_ip <<< "$(get_tunnel_info)"
            info "Tunnel is UP  ->  ${BOLD}$iface${NC}  ${GREEN}($vpn_ip)${NC}"
            return 0
        fi
        printf "\r${CYAN}  [....]${NC}${DIM}  Waiting... ${elapsed}s${NC}"
        sleep 1
        (( elapsed++ ))
    done

    echo ""
    warn "Tunnel did not appear within ${timeout}s — check $LOG_FILE"
    return 1
}

# ── Connect ───────────────────────────────────────────────────
connect() {
    section "Connecting to VPN"

    # WSL warning
    if [[ "$PLATFORM" == "wsl" ]]; then
        warn "WSL detected — OpenVPN may require additional WSL2 kernel support."
        dim "If connection fails, consider running the script natively on Linux."
        echo ""
    fi

    local attempt=1
    while [[ $attempt -le $MAX_RETRIES ]]; do
        step "Attempt $attempt / $MAX_RETRIES"

        local otp
        otp=$(generate_otp)
        info "OTP generated -> ${otp:0:2}****  (masked)"

        write_auth_file "$otp"

        if sudo openvpn \
            --config         "$VPN_CONFIG" \
            --auth-user-pass "$AUTH_FILE" \
            --log            "$LOG_FILE" \
            --daemon 2>/dev/null; then

            if wait_for_tunnel; then
                section "VPN Connected"
                info "Status   : Connected"
                info "Platform : $PLATFORM"
                info "Log      : $LOG_FILE"
                echo ""
                dim "To disconnect run:  sudo pkill -f openvpn"
                echo ""
                return 0
            fi
        fi

        if [[ $attempt -lt $MAX_RETRIES ]]; then
            warn "Attempt $attempt failed — retrying in ${RETRY_DELAY}s..."
            sleep "$RETRY_DELAY"
        fi
        (( attempt++ ))
    done

    section "Connection Failed"
    error "All $MAX_RETRIES attempts failed."
    dim "Check logs: cat $LOG_FILE"
    exit 1
}

# ── Disconnect ────────────────────────────────────────────────
disconnect() {
    section "Disconnecting VPN"
    if pgrep -f "openvpn" &>/dev/null; then
        step "Sending SIGTERM to OpenVPN..."
        sudo pkill -SIGTERM -f "openvpn"
        sleep 1
        if ! pgrep -f "openvpn" &>/dev/null; then
            info "VPN disconnected successfully."
        else
            warn "Process still running — force killing..."
            sudo pkill -9 -f "openvpn" || true
        fi
    else
        warn "No OpenVPN process found — already disconnected."
    fi
}

# ── Status ────────────────────────────────────────────────────
status() {
    section "VPN Status  [platform: $PLATFORM]"
    if pgrep -f "openvpn" &>/dev/null; then
        local pid
        pid=$(pgrep -f openvpn | head -1)
        info "OpenVPN is running  (PID: $pid)"
        if tunnel_is_up; then
            read -r iface vpn_ip <<< "$(get_tunnel_info)"
            info "Tunnel Interface : ${BOLD}$iface${NC}"
            info "VPN IP Address   : ${BOLD}${GREEN}$vpn_ip${NC}"
        else
            warn "No tunnel interface found."
        fi
    else
        warn "OpenVPN is NOT running."
    fi
    echo ""
}

# ── Usage ─────────────────────────────────────────────────────
usage() {
    echo ""
    echo -e "${BOLD}  Usage:${NC}  $(basename "$0")  ${CYAN}[connect|disconnect|status|help]${NC}"
    echo ""
    echo -e "${BOLD}  Override defaults via environment variables:${NC}"
    echo -e "  ${DIM}OPENVPN_CONFIG${NC}       Path to .ovpn file"
    echo -e "  ${DIM}OPENVPN_USER${NC}         VPN username"
    echo -e "  ${DIM}OPENVPN_PASS${NC}         VPN password"
    echo -e "  ${DIM}TOTP_SECRET${NC}          Base32 TOTP secret (min 16 chars)"
    echo -e "  ${DIM}OPENVPN_RETRIES${NC}      Max retries              (default: 3)"
    echo -e "  ${DIM}OPENVPN_RETRY_DELAY${NC}  Delay between retries in seconds (default: 5)"
    echo ""
    echo -e "${BOLD}  Examples:${NC}"
    echo -e "  $(basename "$0") connect"
    echo -e "  $(basename "$0") disconnect"
    echo -e "  $(basename "$0") status"
    echo -e "  TOTP_SECRET=NEWKEY $(basename "$0") connect"
    echo ""
    echo -e "${BOLD}  Platform install guides:${NC}"
    echo -e "  ${DIM}macOS  :${NC}  brew install openvpn oath-toolkit"
    echo -e "  ${DIM}Ubuntu :${NC}  sudo apt install openvpn oathtool iproute2"
    echo -e "  ${DIM}Fedora :${NC}  sudo dnf install openvpn oathtool iproute"
    echo -e "  ${DIM}WSL    :${NC}  sudo apt install openvpn oathtool iproute2"
    echo ""
}

# ── Entry point ───────────────────────────────────────────────
main() {
    local cmd="${1:-connect}"
    case "$cmd" in
        connect)
            check_deps
            validate_config
            connect
            ;;
        disconnect) disconnect ;;
        status)     status ;;
        help|--help|-h) usage ;;
        *)
            error "Unknown command: '$cmd'"
            usage
            exit 1
            ;;
    esac
}

main "$@"
```

Or create it manually:

```bash
vi ~/vpn/vpn.sh
# paste the script content and save
```

---

**Step 5 — Make the script executable**

```bash
chmod +x ~/vpn/vpn.sh
```

---

**Step 6 — Edit the script defaults**

Open the script and update the static defaults at the top:

```bash
vi ~/vpn/vpn.sh
```

Update these lines with your real values:

```bash
VPN_CONFIG="${OPENVPN_CONFIG:-/Users/yourname/vpn/client.ovpn}"
VPN_USER="${OPENVPN_USER:-your.username}"
VPN_PASS="${OPENVPN_PASS:-YourPassword}"
TOTP_SECRET="${TOTP_SECRET:-YOUR_BASE32_SECRET}"
```

---

**Step 7 — Run the script**

```bash
cd ~/vpn
./vpn.sh connect
```

Expected output:

```
  ════════════════════════════════
    Checking Dependencies  [platform: macos]
  ════════════════════════════════
  [OK]   openvpn is installed
         /opt/homebrew/sbin/openvpn
  [OK]   oathtool is installed
         /opt/homebrew/bin/oathtool
  [OK]   ifconfig is available

  ════════════════════════════════
    Validating Configuration
  ════════════════════════════════
  [OK]   Username     : sagar.malla
  [OK]   Password     : Sa*****  (masked)
  [OK]   TOTP Secret  : JBSW**********  (masked)
  [OK]   VPN Config   : /Users/sagarmalla/vpn/client.ovpn
  [OK]   Platform     : macos

  ════════════════════════════════
    Connecting to VPN
  ════════════════════════════════
  [....]  Attempt 1 / 3
  [OK]   OTP generated -> 48****  (masked)
         Auth file -> /tmp/.vpn_auth_12345  [chmod 600]
  [....]  Waiting for tunnel interface...
  [OK]   Tunnel is UP  ->  utun4  (10.8.0.2)

  ════════════════════════════════
    VPN Connected
  ════════════════════════════════
  [OK]   Status   : Connected
  [OK]   Platform : macos
  [OK]   Log      : /tmp/openvpn.log

         To disconnect run:  sudo pkill -f openvpn
```

---

### Linux

Tested on Ubuntu 20.04, 22.04, Debian 11, Fedora 38.

---

**Step 1 — Update your package list**

```bash
# Debian / Ubuntu
sudo apt update

# Fedora / RHEL
sudo dnf check-update
```

---

**Step 2 — Install dependencies**

```bash
# Debian / Ubuntu
sudo apt install -y openvpn oathtool iproute2

# Fedora / RHEL
sudo dnf install -y openvpn oathtool iproute
```

Verify installations:

```bash
openvpn --version
oathtool --version
ip --version
```

---

**Step 3 — Place your .ovpn config file**

```bash
mkdir -p ~/vpn
cp ~/Downloads/your_config.ovpn ~/vpn/client.ovpn
```

Alternatively, if your admin placed it in `/etc/openvpn/`:

```bash
sudo cp ~/Downloads/your_config.ovpn /etc/openvpn/client.ovpn
```

---

**Step 4 — Download the script**

```bash
curl -O https://raw.githubusercontent.com/yourusername/openvpn-otp/main/vpn.sh
chmod +x vpn.sh
```

---

**Step 5 — Edit the script defaults**

```bash
vi vpn.sh
```

Update these lines:

```bash
VPN_CONFIG="${OPENVPN_CONFIG:-/home/yourname/vpn/client.ovpn}"
VPN_USER="${OPENVPN_USER:-your.username}"
VPN_PASS="${OPENVPN_PASS:-YourPassword}"
TOTP_SECRET="${TOTP_SECRET:-YOUR_BASE32_SECRET}"
```

---

**Step 6 — Run the script**

```bash
./vpn.sh connect
```

---

**Step 7 — (Optional) Allow openvpn without sudo password prompt**

If you want to run without being prompted for a sudo password each time,
add an exception in sudoers:

```bash
sudo visudo
```

Add this line at the bottom (replace `yourname` with your Linux username):

```
yourname ALL=(ALL) NOPASSWD: /usr/sbin/openvpn
```

---

### Windows WSL

WSL2 is required. WSL1 does not support TUN/TAP devices needed by OpenVPN.

---

**Step 1 — Enable WSL2 on Windows**

Open PowerShell as Administrator and run:

```powershell
wsl --install
```

If WSL is already installed, make sure you are on WSL2:

```powershell
wsl --list --verbose
wsl --set-version Ubuntu 2
```

Restart your machine after enabling WSL2.

---

**Step 2 — Open WSL terminal**

Press `Win + S`, search for `Ubuntu` (or your WSL distro) and open it.

---

**Step 3 — Update packages**

```bash
sudo apt update && sudo apt upgrade -y
```

---

**Step 4 — Install dependencies**

```bash
sudo apt install -y openvpn oathtool iproute2
```

---

**Step 5 — Enable TUN/TAP kernel module**

WSL2 requires the TUN module to be loaded before OpenVPN can create a tunnel:

```bash
# Check if tun module is already loaded
lsmod | grep tun

# If nothing is returned, load it manually
sudo modprobe tun

# Verify it loaded
lsmod | grep tun
```

To make it load automatically on every WSL startup, add it to your shell profile:

```bash
echo "sudo modprobe tun 2>/dev/null" >> ~/.bashrc
source ~/.bashrc
```

---

**Step 6 — Place your .ovpn config file**

Copy from Windows filesystem into WSL. Windows drives are mounted at `/mnt/c`,
`/mnt/d`, etc:

```bash
mkdir -p ~/vpn
cp /mnt/c/Users/YourWindowsName/Downloads/your_config.ovpn ~/vpn/client.ovpn
```

---

**Step 7 — Download and set up the script**

```bash
cd ~/vpn
curl -O https://raw.githubusercontent.com/yourusername/openvpn-otp/main/vpn.sh
chmod +x vpn.sh
```

---

**Step 8 — Edit the script defaults**

```bash
vi vpn.sh
```

Update these lines:

```bash
VPN_CONFIG="${OPENVPN_CONFIG:-/home/yourname/vpn/client.ovpn}"
VPN_USER="${OPENVPN_USER:-your.username}"
VPN_PASS="${OPENVPN_PASS:-YourPassword}"
TOTP_SECRET="${TOTP_SECRET:-YOUR_BASE32_SECRET}"
```

---

**Step 9 — Run the script**

```bash
./vpn.sh connect
```

The script will detect WSL automatically and print a warning if TUN support
is missing. If the tunnel does not come up, refer to the Troubleshooting
section below.

---

## Configuration

All values at the top of the script can be set as static defaults or
overridden at runtime using environment variables.

```bash
# ── Static Defaults (override via env vars) ──────────────────
VPN_CONFIG="${OPENVPN_CONFIG:-/path/to/client.ovpn}"
VPN_USER="${OPENVPN_USER:-your.username}"
VPN_PASS="${OPENVPN_PASS:-YourPassword}"
TOTP_SECRET="${TOTP_SECRET:-YOUR_BASE32_SECRET}"
MAX_RETRIES="${OPENVPN_RETRIES:-3}"
RETRY_DELAY="${OPENVPN_RETRY_DELAY:-5}"
```

### Where to find your TOTP Base32 secret

When your VPN administrator sets up two-factor authentication, they provide
either a QR code or a plain-text Base32 secret key. The secret looks like:

```
JBSWY3DPEHPK3PXP
```

| Source                  | How to get the secret                                                   |
|-------------------------|-------------------------------------------------------------------------|
| VPN portal setup page   | Shown below the QR code during 2FA enrollment as a plain-text key       |
| Google Authenticator    | Export account, the Base32 key is inside the otpauth URI                |
| Microsoft Authenticator | Re-enroll and copy the secret key shown during setup                    |
| QR code only            | Scan with a QR decoder app, copy the value after `secret=` in the URI  |

---

## Usage

```bash
# Connect to VPN
./vpn.sh connect

# Check connection status
./vpn.sh status

# Disconnect from VPN
./vpn.sh disconnect

# Show help and available options
./vpn.sh help
```

---

## Environment Variable Overrides

You can override any default value at runtime without editing the script.
This is useful for CI/CD pipelines, multiple VPN profiles, or shared scripts.

```bash
# Override a single value
TOTP_SECRET=NEWKEY ./vpn.sh connect

# Override multiple values
OPENVPN_USER=john.doe \
OPENVPN_PASS=newpassword \
TOTP_SECRET=JBSWY3DPEHPK3PXP \
./vpn.sh connect

# Use a different config file
OPENVPN_CONFIG=~/vpn/office.ovpn ./vpn.sh connect

# Increase retries and delay for slow networks
OPENVPN_RETRIES=5 OPENVPN_RETRY_DELAY=10 ./vpn.sh connect
```

| Variable               | Description                        | Default             |
|------------------------|------------------------------------|---------------------|
| `OPENVPN_CONFIG`       | Path to your `.ovpn` file          | Hardcoded in script |
| `OPENVPN_USER`         | VPN username                       | Hardcoded in script |
| `OPENVPN_PASS`         | VPN base password                  | Hardcoded in script |
| `TOTP_SECRET`          | Base32 TOTP secret (min 16 chars)  | Hardcoded in script |
| `OPENVPN_RETRIES`      | Max connection attempts            | `3`                 |
| `OPENVPN_RETRY_DELAY`  | Seconds to wait between retries    | `5`                 |

---

## Troubleshooting

### Deprecation warnings on connect

```
DEPRECATED OPTION: --persist-key option ignored.
WARNING: Compression for receiving enabled.
```

These are harmless warnings from your `.ovpn` config file.
To silence them, open your `.ovpn` file in a text editor and:

- Remove or comment out the line `persist-key`
- Add the line `compress no`

---

### TOTP_SECRET too short error

```
[ERR]  TOTP_SECRET looks too short — check your Base32 secret
```

Your secret must be at least 16 characters. Make sure you copied the full
Base32 key and did not accidentally include spaces or truncate it.

---

### VPN config file not found

```
[ERR]  VPN config not found: /path/to/client.ovpn
```

Double-check the path. On macOS the file might still be in Downloads:

```bash
ls ~/Downloads/*.ovpn
```

Then update `VPN_CONFIG` in the script or pass it as an env var:

```bash
OPENVPN_CONFIG=~/Downloads/your_config.ovpn ./vpn.sh connect
```

---

### Tunnel never comes up

```
[WARN] Tunnel did not appear within 30s — check /tmp/openvpn.log
```

Check the full OpenVPN log for the real error:

```bash
cat /tmp/openvpn.log
```

Common causes and fixes:

| Cause                         | Fix                                                          |
|-------------------------------|--------------------------------------------------------------|
| Wrong username or password    | Double-check `VPN_USER` and `VPN_PASS` in the script        |
| Wrong TOTP secret             | Re-copy the Base32 key from your VPN portal                  |
| VPN server unreachable        | Check your internet connection and firewall rules            |
| Expired `.ovpn` config        | Request a new config file from your VPN administrator        |
| TUN module not loaded (WSL)   | Run `sudo modprobe tun` and try again                        |

---

### oathtool command not found

```bash
# macOS
brew install oath-toolkit

# Linux / WSL
sudo apt install oathtool
```

---

### openvpn command not found

```bash
# macOS
brew install openvpn

# Linux / WSL
sudo apt install openvpn
```

---

### Permission denied running the script

```bash
chmod +x vpn.sh
```

---

### WSL — TUN device not available

```bash
# Load the TUN module
sudo modprobe tun

# Verify it loaded
lsmod | grep tun

# Then retry
./vpn.sh connect
```

If `modprobe tun` fails with a module not found error, your WSL2 kernel may
not support TUN/TAP. In that case, run OpenVPN natively on Windows using the
official OpenVPN GUI installer from https://openvpn.net/community-downloads

---

### sudo password prompt blocks automation

Add a sudoers exception (replace `yourname` with your actual username):

```bash
sudo visudo
```

Add at the bottom:

```bash
# macOS
yourname ALL=(ALL) NOPASSWD: /opt/homebrew/sbin/openvpn

# Linux / WSL
yourname ALL=(ALL) NOPASSWD: /usr/sbin/openvpn
```

---

## Security Notes

| Practice                     | How this script handles it                                       |
|------------------------------|------------------------------------------------------------------|
| Temp credentials file        | Written to `/tmp` with `chmod 600` — owner read/write only       |
| Auto cleanup                 | `trap EXIT` deletes the auth file even if the script crashes     |
| Secrets never logged         | Password and OTP only appear masked in terminal output           |
| OTP regenerated per retry    | TOTP codes expire every 30s — each retry generates a fresh code  |
| No secrets in process list   | Credentials passed via file, not as command-line arguments       |

For team or production use, store secrets in a dedicated secrets manager
instead of hardcoding them in the script:

- macOS Keychain via `security add-generic-password`
- Linux `secret-tool` from the `libsecret-tools` package
- HashiCorp Vault at https://www.vaultproject.io
- AWS Secrets Manager at https://aws.amazon.com/secrets-manager

---

## Platform Support Summary

| Feature                  | macOS    | Linux  | WSL2   |
|--------------------------|----------|--------|--------|
| Auto platform detection  | Yes      | Yes    | Yes    |
| OpenVPN daemon mode      | Yes      | Yes    | Yes    |
| Tunnel interface name    | utun*    | tun*   | tun*   |
| Network tool used        | ifconfig | ip     | ip     |
| OTP auto-generation      | Yes      | Yes    | Yes    |
| Retry on failure         | Yes      | Yes    | Yes    |
| Temp file auto cleanup   | Yes      | Yes    | Yes    |
| TUN module required      | No       | No     | Yes    |

---

## Project Structure

```
openvpn-otp/
├── vpn.sh        Main automation script
└── README.md     This file
```

---

## License

MIT — free to use, modify, and distribute.
