# Nightly Security Database Update — Trivy, OWASP Dependency-Check & Grype

**Author:** Sagar Malla

---

## Why This Is Required

Trivy, OWASP Dependency-Check, and Grype all rely on local vulnerability
databases to scan images and dependencies. If those databases go stale,
scan results become unreliable — new CVEs won't be detected, and some
tools (Grype in particular) will outright refuse to scan once the DB
exceeds a maximum allowed age.

Previously, each of these tools refreshed its own database **inline,
inside every Jenkins pipeline run** — meaning every build paid the cost
of a DB download, even during working hours when pipelines run most
frequently. This added unnecessary time to every build and put avoidable
load on external endpoints (NVD, Maven Central, npm registry, etc.)
throughout the day.

This script centralizes all three DB refreshes into a **single nightly
job**, so:

- Databases are refreshed once, at a fixed off-hours time
- Application pipelines just consume an already-warm DB and skip
  re-downloading (via `--skip-db-update` / `--noupdate` flags on the
  scan side)
- Nightly runs don't collide with daytime pipeline activity or scanner
  load

---

## Why Run It This Way (Pros)

- **Faster pipelines** — DB downloads no longer add minutes to every
  build; scans run against an already-current local DB.
- **Predictable load** — all external DB-source traffic happens once,
  at a known time, instead of scattered across every pipeline run.
- **Self-healing** — before each run, the script kills any leftover
  process from a previous run (via a PID file), so a hung or crashed
  run never blocks the next scheduled one.
- **Fails fast, not silently hung** — each DB source is checked for
  reachability (5 retries, 30s timeout each) before attempting a
  download. If an endpoint is down, the script logs it clearly and
  exits instead of hanging indefinitely.
- **Self-contained** — the script sets its own `PATH` and `JAVA_HOME`
  explicitly, so it runs correctly under cron's minimal environment
  without depending on shell profile files being sourced.
- **Secrets kept out of source** — the NVD API key is loaded from a
  separate `.env` file (owner-only permissions), never hardcoded in
  the script itself.
- **Bounded log growth** — only the latest 5 run logs are kept; older
  logs are automatically pruned after each run.
- **Clear, colorized logging** — every stage (Trivy / OWASP / Grype)
  logs its own status, so failures are easy to spot at a glance, both
  live in the terminal and in the saved log file.

---

## What It Updates

| Tool  | Database Location                         |
|-------|---------------------------------------------|
| Trivy | `/var/lib/trivy/db`                          |
| OWASP Dependency-Check | `/opt/owasp/dependency-check/data` |
| Grype | Managed internally by `grype` (`~/.cache/grype/db`) |

---

## How It Works

1. **Fresh start** — on launch, the script checks a PID file for a
   leftover process from a previous run. If one is still alive, it's
   force-killed before proceeding. This guarantees each run starts
   clean, with no stacked/orphaned processes from prior runs.

2. **Secret loading** — the NVD API key is loaded from:
   ```
   <working-dir>/.env
   ```
   containing a single line:
   ```
   NVD_API_KEY=your-actual-key-here
   ```
   If this file is missing, Dependency-Check still runs — just slower
   and more rate-limited without a key.

3. **Reachability check** — before each download, the relevant source
   is checked with `curl --max-time 30`, retried up to 5 times. If all
   attempts fail, that stage is marked failed and the script moves on
   without hanging.

4. **DB downloads**, run in sequence:
   - `trivy image --download-db-only --cache-dir <trivy-cache-dir>`
   - `dependency-check.sh --updateonly --data <owasp-data-dir> --nvdApiKey <key>`
   - `grype db update`

5. **Logging** — every run writes a timestamped, colorized log under
   `<working-dir>/logs/`, plus a `latest.log` symlink pointing at the
   most recent run. Only the 5 most recent log files are kept — older
   ones are automatically deleted at the end of each run.

6. **Scheduling** — runs via cron at 04:00 daily, well outside typical
   working hours.

---

## Setup Steps

### 1. Place the script


Create a bash script file as `update-security-dbs.sh`

```bash
#!/usr/bin/env bash
#
# update-security-dbs.sh
# Nightly refresh of Trivy, OWASP Dependency-Check, and Grype vulnerability DBs.
# Run via cron at 04:00 to avoid daytime scan/API load.
#
# Author  : Sagar Malla
# Team    : DevOps / Infrastructure Engineer.
# Created : 2026-07-30
#
# Paths:
#   Trivy : /var/lib/trivy/db
#   OWASP : /opt/owasp/dependency-check/data
#   Grype : ~/.cache/grype/db (managed internally by grype)

# ── Environment (cron runs with a minimal PATH — set explicitly) ──────────
export JAVA_HOME="/home/jenkin/java21"
export PATH="${JAVA_HOME}/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin:${PATH}"

# ── Config ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/update-security-dbs.pid"

TRIVY_CACHE_DIR="/var/lib/trivy"
OWASP_DATA_DIR="/opt/owasp/dependency-check/data"
DC_HOME="/opt/owasp/dependency-check/bin/dependency-check.sh"

WORKING_DIR="/home/jenkin/.security-db-update"
LOGS_DIR="${WORKING_DIR}/logs"
LOG_FILE="${LOGS_DIR}/update-$(date '+%Y%m%d-%H%M%S').log"
LATEST_LINK="${LOGS_DIR}/latest.log"

CHECK_TRIES=5
CHECK_TIMEOUT=30

# ── Colors ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

mkdir -p "$LOGS_DIR" "$TRIVY_CACHE_DIR/db" "$OWASP_DATA_DIR"
ln -sf "$LOG_FILE" "$LATEST_LINK"

# Load NVD_API_KEY from .env if present
ENV_FILE="${WORKING_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi
NVD_API_KEY="${NVD_API_KEY:-}"

log() {
    local level="$1"; shift
    local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local color
    case "$level" in
        INFO)  color="$BLUE" ;;
        OK)    color="$GREEN" ;;
        WARN)  color="$YELLOW" ;;
        ERROR) color="$RED" ;;
        STAGE) color="${BOLD}${CYAN}" ;;
        *)     color="$NC" ;;
    esac
    echo -e "${color}[${ts}] [${level}]${NC} $*"
    echo "[${ts}] [${level}] $*" >> "$LOG_FILE"
}

hr() { echo "────────────────────────────────────────────────" | tee -a "$LOG_FILE"; }

# ── Fresh start: kill any leftover run from before, then claim our own PID ──
if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null)"
    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        log WARN "Previous run still active (PID ${OLD_PID}) — killing it"
        kill -9 "$OLD_PID" 2>/dev/null
    fi
    rm -f "$PID_FILE"
fi
echo "$$" > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

# ── Reachability check ───────────────────────────────────────────────────
check_reachable() {
    local name="$1" url="$2"
    for ((i=1; i<=CHECK_TRIES; i++)); do
        log INFO "Checking ${name} (attempt ${i}/${CHECK_TRIES})..."
        if curl -sS --max-time "$CHECK_TIMEOUT" --head "$url" >/dev/null 2>&1; then
            log OK "${name} reachable"
            return 0
        fi
        log WARN "${name} unreachable (attempt ${i}/${CHECK_TRIES})"
        sleep 2
    done
    log ERROR "${name} unreachable after ${CHECK_TRIES} attempts"
    return 1
}

# ── Start ─────────────────────────────────────────────────────────────────
FAILED=0
hr
log STAGE "Security DB nightly update starting (PID $$)"
log INFO  "Log file: ${LOG_FILE}"
hr

# ── Trivy ─────────────────────────────────────────────────────────────────
log STAGE "Updating Trivy DB → ${TRIVY_CACHE_DIR}/db"
if ! command -v trivy &>/dev/null; then
    log ERROR "trivy not found on PATH"
    FAILED=1
elif check_reachable "Trivy DB source (ghcr.io)" "https://ghcr.io/v2/"; then
    if trivy image --download-db-only --cache-dir "$TRIVY_CACHE_DIR" >>"$LOG_FILE" 2>&1; then
        log OK "Trivy DB updated"
    else
        log ERROR "Trivy DB update failed"
        FAILED=1
    fi
else
    FAILED=1
fi

hr

# ── OWASP Dependency-Check ───────────────────────────────────────────────
log STAGE "Updating OWASP DB → ${OWASP_DATA_DIR}"
if [[ ! -x "$DC_HOME" ]]; then
    log ERROR "dependency-check.sh not found at ${DC_HOME}"
    FAILED=1
elif check_reachable "NVD API" "https://services.nvd.nist.gov/rest/json/cves/2.0"; then
    if [[ -z "$NVD_API_KEY" ]]; then
        log WARN "NVD_API_KEY not set — update will be slow/rate-limited"
        DC_CMD=("$DC_HOME" --updateonly --data "$OWASP_DATA_DIR")
    else
        DC_CMD=("$DC_HOME" --updateonly --data "$OWASP_DATA_DIR" --nvdApiKey "$NVD_API_KEY")
    fi
    if "${DC_CMD[@]}" >>"$LOG_FILE" 2>&1; then
        log OK "OWASP DB updated"
    else
        log ERROR "OWASP DB update failed"
        FAILED=1
    fi
else
    FAILED=1
fi

hr

# ── Grype ─────────────────────────────────────────────────────────────────
log STAGE "Updating Grype vulnerability DB"
if ! command -v grype &>/dev/null; then
    log ERROR "grype not found on PATH"
    FAILED=1
elif check_reachable "Grype DB source (anchore toolbox-data)" "https://toolbox-data.anchore.io/grype/databases/listing.json"; then
    if grype db update >>"$LOG_FILE" 2>&1; then
        log OK "Grype DB updated"
    else
        log ERROR "Grype DB update failed"
        FAILED=1
    fi
else
    FAILED=1
fi

hr

# ── Rotate logs: keep only the latest N, delete older ────────────────────
rotate_logs() {
    local keep=5
    find "$LOGS_DIR" -maxdepth 1 -name 'update-*.log' -type f -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn \
        | tail -n +"$((keep + 1))" \
        | cut -d' ' -f2- \
        | xargs -r rm -f
}
rotate_logs

# ── Summary ───────────────────────────────────────────────────────────────
if [[ "$FAILED" -eq 0 ]]; then
    log OK "All DB updates completed successfully"
    exit 0
else
    log ERROR "One or more DB updates FAILED — review ${LOG_FILE}"
    exit 1
fi
```



```bash
mkdir -p <install-dir>
cp update-security-dbs.sh <install-dir>/
chmod 700 <install-dir>/update-security-dbs.sh
```

### 2. Create the `.env` file with your NVD API key

```bash
mkdir -p <working-dir>
cat > <working-dir>/.env << 'EOF'
NVD_API_KEY=your-actual-key-here
EOF
chmod 600 <working-dir>/.env
```

`chmod 600` restricts the file to owner-only read/write, since it
holds a secret.

Get a free NVD API key (raises the rate limit from 5/30s to 50/30s):
https://nvd.nist.gov/developers/request-an-api-key

### 3. Verify tool paths

Confirm these match your actual install (adjust the script's `Config`
section if different):

```bash
which trivy
which grype
find /opt -iname 'dependency-check.sh'
```

Also confirm `JAVA_HOME` matches your environment:

```bash
echo $JAVA_HOME
which java
```

### 4. Test manually first

```bash
<install-dir>/update-security-dbs.sh
```

Check the log:

```bash
cat <working-dir>/logs/latest.log
```

### 5. Schedule via cron

```bash
crontab -e
```

Add:

```
0 4 * * * <install-dir>/update-security-dbs.sh
```

No environment variables need to be set in the crontab — the script
sets its own `PATH`/`JAVA_HOME`, and the `.env` file handles the
secret.

### 6. Update scan pipelines to skip inline DB downloads

Since DB refresh is now centralized, scan steps elsewhere should
**not** re-download the DB on every run:

- **Trivy:** add `--skip-db-update`
- **Dependency-Check:** add `--noupdate`
- **Grype:** add `--skip-db-update`

This is what actually removes the DB-download cost from every
pipeline run — the nightly script keeps the databases warm, and
scan steps just consume them.

---

## Files

- `update-security-dbs.sh` — the automation script
- `<working-dir>/.env` — NVD API key (owner-only permissions, not
  committed to version control)
- `<working-dir>/logs/update-<timestamp>.log` — per-run log (latest 5 kept)
- `<working-dir>/logs/latest.log` — symlink to the most recent log
- `<install-dir>/update-security-dbs.pid` — PID file used for
  stale-run detection
