# batch-cmd-run.sh

Run any shell command, push a file, or pull a file across a list of Linux servers — one by one, over SSH, using `sshpass` for password auth.

Built for managing a fleet of servers (e.g. hostmap updates, config pushes, service restarts) without typing SSH passwords manually or writing a new script for every task.

**Author:** Sagar Malla — DevOps Engineer, 

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
  - [`--exec` — run any command](#--exec--run-any-command)
  - [`--hostmap` — add a `/etc/hosts` entry](#--hostmap--add-a-etchosts-entry)
  - [`--push` — copy a local file to every server](#--push--copy-a-local-file-to-every-server)
  - [`--pull` — copy a file from every server to your machine](#--pull--copy-a-file-from-every-server-to-your-machine)
- [Output](#output)
- [Troubleshooting](#troubleshooting)
- [Script source: `batch-cmd-run.sh`](#script-source-multi-runsh)

---

## Features

- **`--exec`** — run any arbitrary command on every server (`systemctl restart X`, `df -h`, `yum install -y htop`, etc.)
- **`--hostmap`** — shortcut to append an `/etc/hosts` entry on every server, idempotent (skips if the line already exists)
- **`--push`** — `scp` a local file/dir to the same path on every server
- **`--pull`** — `scp` a remote file/dir from every server back to your machine, saved with an IP-prefixed filename so nothing collides
- **`--help`** — full usage reference
- Clean **Ctrl+C** handling — kills the in-flight `ssh`/`scp` process group immediately, no orphaned/zombie processes
- Auto-accepts host key prompts (`StrictHostKeyChecking=no`) — no manual "yes" needed, nothing written to `known_hosts`
- Reads the server list safely via a dedicated file descriptor so `ssh`/`scp` can never "steal" stdin and silently skip remaining hosts
- Per-host pass/fail summary at the end, with a list of failed hosts

---

## Requirements

- `bash`
- `sshpass` installed (`apt install sshpass` / `yum install sshpass` / `brew install hudochenkov/sshpass/sshpass`)
- SSH access (password auth) to every target server

---

## Setup

1. Save the script as `batch-cmd-run.sh` (source below) and make it executable:

   ```bash
   chmod +x batch-cmd-run.sh
   ```

2. Create `server-ips.txt` in the same directory — one IP or hostname per line. Blank lines and `#` comments are ignored, and inline `# comment` after an IP is stripped too:

   ```
   10.10.10.132
   10.10.10.163
   # 10.10.10.200   (temporarily excluded)
   10.10.10.100
   ```

3. Edit the config block at the top of the script for your environment:

   ```bash
   SSH_USER="root"
   SSH_PORT="22"
   SSH_PASS="passwordHere"
   ```

   > All servers in the list must share this same user/password. If your servers use different credentials, you'll need to extend the script to read per-host credentials instead of one global password.

---

## Usage

```bash
./batch-cmd-run.sh --exec    "<remote_command>"                [server-ips.txt]
./batch-cmd-run.sh --hostmap <ip_to_map> <hostname_to_map>      [server-ips.txt]
./batch-cmd-run.sh --push    <local_file> <remote_dest_path>    [server-ips.txt]
./batch-cmd-run.sh --pull    <remote_file> <local_dest_dir>     [server-ips.txt]
./batch-cmd-run.sh --help
```

`server-ips.txt` is optional in every mode — defaults to `server-ips.txt` in the current directory if omitted.

### `--exec` — run any command

Quote the whole command as a single argument. It runs via `bash -c "<command>"` on the remote end, so pipes, redirects, and `&&` all work normally.

```bash
./batch-cmd-run.sh --exec 'echo "10.10.10.5 example.com.np" >> /etc/hosts'
./batch-cmd-run.sh --exec 'systemctl restart kafka'
./batch-cmd-run.sh --exec 'df -h'
./batch-cmd-run.sh --exec 'yum install -y htop' my-servers.txt
```

> `--exec` runs whatever you give it, with no dry-run or confirmation step. Test destructive commands (`rm`, `systemctl stop`, package removals) against a single-IP test list before pointing it at the full fleet.

### `--hostmap` — add a `/etc/hosts` entry

Shortcut for the common case above — appends `"<ip> <hostname>"` to `/etc/hosts` on every server, skipping hosts where that exact line already exists.

```bash
./batch-cmd-run.sh --hostmap 10.10.10.100 dc-transfer.sagar.com.np
```

Equivalent to:

```bash
--exec 'grep -qF "10.10.10.100 dc-transfer.sagar.com.np" /etc/hosts || echo "10.10.10.100 dc-transfer.sagar.com.np" >> /etc/hosts'
```

### `--push` — copy a local file to every server

```bash
./batch-cmd-run.sh --push ./resolv.conf /etc/resolv.conf
```

### `--pull` — copy a file from every server to your machine

Saved as `<local_dest_dir>/<server-ip>_<basename>` so files from different servers don't overwrite each other.

```bash
./batch-cmd-run.sh --pull /var/log/app.log ./logs/
# -> ./logs/10.10.10.132_app.log
# -> ./logs/10.10.10.163_app.log
```

---

## Output

```
Will run on each server: echo "10.10.10.100 dc-transfer.sagar.com.np" >> /etc/hosts
Target server list  : server-ips.txt
----------------------------------------
[*] Connecting to 10.10.10.132 .sagar..
[OK]   10.10.10.132: command succeeded
----------------------------------------
[*] Connecting to 10.10.10.163 .sagar..
[OK]   10.10.10.163: command succeeded
----------------------------------------

Done. Success: 2  Failed: 0
```

On failure, a summary of failed hosts is printed and the script exits with code `1`:

```
Done. Success: 8  Failed: 2
Failed hosts:
  - 10.10.10.163
  - 10.10.10.100
```

Exits `130` on Ctrl+C.

---

## Troubleshooting

**`Permission denied, please try again.`**
Most common causes, in order of likelihood:
1. Wrong password in `SSH_PASS` for that particular server (servers don't share the same password)
2. `PasswordAuthentication no` in that server's `sshd_config` — key-based auth only
3. `PermitRootLogin no` / `PermitRootLogin prohibit-password` — root login over password disabled
4. Special characters in the password breaking word-splitting somewhere

Debug a single host manually with verbose SSH:

```bash
sshpass -p 'passwordHere' ssh -v -p 22 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@<ip> "echo test"
```

**Script only seems to run on the first server in the list.**
Fixed as of this version — the loop now reads `server-ips.txt` via a dedicated file descriptor (`3<`) instead of stdin, and every `ssh`/`scp` call is redirected from `/dev/null`. Previously, `ssh` inherited the loop's stdin and silently drained the rest of the server list on the first connection.

---

## Script source: `batch-cmd-run.sh`

```bash
#!/usr/bin/env bash
#
# batch-cmd-run.sh
# Run any command / scp push / scp pull across a list of servers,
# one by one, over SSH using sshpass.
#
# Author : Sagar Malla
# Role   : DevOps Engineer, 
# Date   : 2026-07-17
#
# Usage:
#   ./batch-cmd-run.sh --exec    "<remote_command>"                [server-ips.txt]
#   ./batch-cmd-run.sh --hostmap <ip_to_map> <hostname_to_map>      [server-ips.txt]
#   ./batch-cmd-run.sh --push    <local_file> <remote_dest_path>    [server-ips.txt]
#   ./batch-cmd-run.sh --pull    <remote_file> <local_dest_dir>     [server-ips.txt]
#   ./batch-cmd-run.sh --help
#
# Examples:
#   ./batch-cmd-run.sh --exec 'echo "10.10.10.5 example.com.np" >> /etc/hosts'
#   ./batch-cmd-run.sh --exec 'systemctl restart kafka'
#   ./batch-cmd-run.sh --exec 'df -h'
#   ./batch-cmd-run.sh --hostmap 10.10.10.5 example.com.np server-ips.txt
#   ./batch-cmd-run.sh --push ./resolv.conf /etc/resolv.conf server-ips.txt
#   ./batch-cmd-run.sh --pull /var/log/app.log ./logs/ server-ips.txt
#
set -uo pipefail

# ---- clean ctrl+c handling ----
CHILD_PID=""

cleanup_and_exit() {
    echo ""
    echo "[!] Interrupted. Terminating.sagar.."
    if [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; then
        # kill the whole process group of the child (ssh/scp + sshpass)
        kill -TERM -"$CHILD_PID" 2>/dev/null
        sleep 0.3
        kill -KILL -"$CHILD_PID" 2>/dev/null
    fi
    exit 130
}
trap cleanup_and_exit SIGINT SIGTERM

# run a command in its own process group, in background, wait on it,
# so ctrl+c can kill the whole group instead of leaving orphans behind
run_tracked() {
    setsid "$@" &
    CHILD_PID=$!
    wait "$CHILD_PID"
    local rc=$?
    CHILD_PID=""
    return $rc
}

# ---- config ----
SSH_USER="root"
SSH_PORT="22"
SSH_PASS="passwordHere"          # consider exporting SSHPASS instead of hardcoding
# StrictHostKeyChecking=no -> auto-accepts host key (answers "yes" to the
#   "Are you sure you want to continue connecting" prompt) without asking.
# UserKnownHostsFile=/dev/null -> don't save/check against known_hosts.
# LogLevel=ERROR -> suppress SSH banners/warnings cluttering output.
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=8"

show_help() {
    cat <<'EOF'
batch-cmd-run.sh — run a command / scp push / scp pull across a list of servers

USAGE:
  ./batch-cmd-run.sh --exec    "<remote_command>"             [server-ips.txt]
  ./batch-cmd-run.sh --hostmap <ip_to_map> <hostname_to_map>   [server-ips.txt]
  ./batch-cmd-run.sh --push    <local_file> <remote_dest_path> [server-ips.txt]
  ./batch-cmd-run.sh --pull    <remote_file> <local_dest_dir>  [server-ips.txt]
  ./batch-cmd-run.sh --help

MODES:
  --exec      Run ANY shell command on every server, e.g.:
                --exec 'echo "10.10.10.5 example.com.np" >> /etc/hosts'
                --exec 'systemctl restart kafka'
                --exec 'df -h'
                --exec 'yum install -y htop'
              Quote the whole command as one argument. Runs via
              `bash -c "<command>"` on the remote end, so pipes,
              redirects, &&, etc. all work normally.

  --hostmap   Shortcut for appending "<ip> <hostname>" to /etc/hosts
              on every server (skipped if the exact line already
              exists). Equivalent to:
                --exec 'grep -qF "<ip> <hostname>" /etc/hosts || echo "<ip> <hostname>" >> /etc/hosts'

  --push      scp a local file/dir to the same destination path on
              every server.

  --pull      scp a remote file/dir from every server back to your
              machine, saved as <local_dest_dir>/<server-ip>_<basename>.

ARGS:
  server-ips.txt   Optional, defaults to "server-ips.txt" in cwd.
                   One IP/hostname per line. Blank lines and lines
                   starting with # are ignored; inline "# comment"
                   after an IP is also stripped.

EXAMPLES:
  ./batch-cmd-run.sh --exec 'echo "10.10.10.5 example.com.np" >> /etc/hosts'
  ./batch-cmd-run.sh --exec 'systemctl status haproxy' my-servers.txt
  ./batch-cmd-run.sh --hostmap 10.10.10.5 example.com.np
  ./batch-cmd-run.sh --push ./resolv.conf /etc/resolv.conf
  ./batch-cmd-run.sh --pull /var/log/app.log ./logs/

CONFIG (edit script header):
  SSH_USER, SSH_PORT, SSH_PASS   — connection credentials
                                    (used via sshpass)

NOTES:
  - Requires sshpass installed.
  - Host-key prompts ("Are you sure you want to continue connecting
    (yes/no/[fingerprint])?") are auto-accepted via
    StrictHostKeyChecking=no — no manual "yes" needed, and nothing
    is written to known_hosts.
  - Ctrl+C aborts immediately and kills the in-flight ssh/scp
    process, no leftover/zombie processes.
  - --exec runs the command as-is on the remote shell. Be careful
    with anything destructive; test on one server first.

AUTHOR:
  Sagar Malla — DevOps Engineer
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || $# -eq 0 ]]; then
    show_help
    exit 0
fi

if ! command -v sshpass >/dev/null 2>&1; then
    echo "ERROR: sshpass not installed. Install it first (e.g. apt install sshpass / brew install hudochenkov/sshpass/sshpass)."
    exit 1
fi

# ---- args ----
MODE="${1:-}"
case "$MODE" in
    --exec)
        REMOTE_CMD="${2:-}"
        SERVER_LIST="${3:-server-ips.txt}"
        if [[ -z "$REMOTE_CMD" ]]; then
            echo "Usage: $0 --exec \"<remote_command>\" [server-ips.txt]"
            exit 1
        fi
        ;;
    --hostmap)
        HOST_IP="${2:-}"
        HOST_NAME="${3:-}"
        SERVER_LIST="${4:-server-ips.txt}"
        if [[ -z "$HOST_IP" || -z "$HOST_NAME" ]]; then
            echo "Usage: $0 --hostmap <ip_to_map> <hostname_to_map> [server-ips.txt]"
            exit 1
        fi
        HOSTMAP_LINE="${HOST_IP} ${HOST_NAME}"
        REMOTE_CMD="grep -qF '${HOSTMAP_LINE}' /etc/hosts || echo '${HOSTMAP_LINE}' >> /etc/hosts"
        ;;
    --push)
        LOCAL_FILE="${2:-}"
        REMOTE_DEST="${3:-}"
        SERVER_LIST="${4:-server-ips.txt}"
        if [[ -z "$LOCAL_FILE" || -z "$REMOTE_DEST" ]]; then
            echo "Usage: $0 --push <local_file> <remote_dest_path> [server-ips.txt]"
            exit 1
        fi
        if [[ ! -e "$LOCAL_FILE" ]]; then
            echo "ERROR: local file/dir '$LOCAL_FILE' not found."
            exit 1
        fi
        ;;
    --pull)
        REMOTE_FILE="${2:-}"
        LOCAL_DEST="${3:-}"
        SERVER_LIST="${4:-server-ips.txt}"
        if [[ -z "$REMOTE_FILE" || -z "$LOCAL_DEST" ]]; then
            echo "Usage: $0 --pull <remote_file> <local_dest_dir> [server-ips.txt]"
            exit 1
        fi
        ;;
    *)
        echo "ERROR: unknown mode '$MODE'"
        echo "Run '$0 --help' for usage."
        exit 1
        ;;
esac

if [[ ! -f "$SERVER_LIST" ]]; then
    echo "ERROR: server list '$SERVER_LIST' not found."
    exit 1
fi

SCP_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=8 -P ${SSH_PORT}"

case "$MODE" in
    --exec)
        echo "Will run on each server: ${REMOTE_CMD}"
        ;;
    --hostmap)
        echo "Will add hosts entry: '${HOSTMAP_LINE}'"
        ;;
    --push)
        echo "Will scp push: '${LOCAL_FILE}' -> '${REMOTE_DEST}' on each server"
        ;;
    --pull)
        echo "Will scp pull: '${REMOTE_FILE}' -> '${LOCAL_DEST}/<server>_<basename>' from each server"
        mkdir -p "$LOCAL_DEST"
        ;;
esac
echo "Target server list  : ${SERVER_LIST}"
echo "----------------------------------------"

success=0
fail=0
failed_hosts=()

while IFS= read -r line <&3 || [[ -n "$line" ]]; do
    # skip blank lines and comments
    line="$(echo "$line" | sed 's/#.*//' | xargs)"
    [[ -z "$line" ]] && continue

    target="$line"
    echo "[*] Connecting to ${target} .sagar.."

    case "$MODE" in
        --exec|--hostmap)
            if run_tracked sshpass -p "$SSH_PASS" ssh -p "$SSH_PORT" $SSH_OPTS "${SSH_USER}@${target}" "bash -c \"${REMOTE_CMD//\"/\\\"}\"" </dev/null; then
                echo "[OK]   ${target}: command succeeded"
                ((success++))
            else
                echo "[FAIL] ${target}: command failed"
                ((fail++))
                failed_hosts+=("$target")
            fi
            ;;
        --push)
            if run_tracked sshpass -p "$SSH_PASS" scp $SCP_OPTS -r "$LOCAL_FILE" "${SSH_USER}@${target}:${REMOTE_DEST}" </dev/null; then
                echo "[OK]   ${target}: file pushed to ${REMOTE_DEST}"
                ((success++))
            else
                echo "[FAIL] ${target}: scp push failed"
                ((fail++))
                failed_hosts+=("$target")
            fi
            ;;
        --pull)
            out_name="${target//[:\/]/_}_$(basename "$REMOTE_FILE")"
            if run_tracked sshpass -p "$SSH_PASS" scp $SCP_OPTS -r "${SSH_USER}@${target}:${REMOTE_FILE}" "${LOCAL_DEST}/${out_name}" </dev/null; then
                echo "[OK]   ${target}: file pulled to ${LOCAL_DEST}/${out_name}"
                ((success++))
            else
                echo "[FAIL] ${target}: scp pull failed"
                ((fail++))
                failed_hosts+=("$target")
            fi
            ;;
    esac
    echo "----------------------------------------"
done 3< "$SERVER_LIST"

echo ""
echo "Done. Success: ${success}  Failed: ${fail}"
if (( fail > 0 )); then
    echo "Failed hosts:"
    printf '  - %s\n' "${failed_hosts[@]}"
    exit 1
fi
```
