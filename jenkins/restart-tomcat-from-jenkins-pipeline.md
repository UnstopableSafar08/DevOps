# Jenkins Tomcat Restart — Reference Guide

Restart Tomcat post-WAR-deployment via Jenkins pipeline, using `restart-tomcat.sh` placed on the destination server.

**Author:** Sagar Malla, DevOps Engineer

---

## Table of Contents

1. [Script Syntax](#1-script-syntax)
2. [restart-tomcat.sh (full script — root/sudo)](#2-restart-usersh-full-script--rootsudo)
3. [Direct Bash Usage](#3-direct-bash-usage)
4. [Jenkins Pipeline — Basic](#4-jenkins-pipeline--basic)
5. [Jenkins Pipeline — Exit Code Handling](#5-jenkins-pipeline--exit-code-handling)
6. [Jenkins Pipeline — Rolling Restart (Multi-Node)](#6-jenkins-pipeline--rolling-restart-multi-node)
7. [Argument / Command Syntax Breakdown](#7-argument--command-syntax-breakdown)
8. [Exit Codes](#8-exit-codes)
9. [Fixes vs Original Draft](#9-fixes-vs-original-draft)
10. [Non-Root Variant — restart-user-nonroot.sh](#10-non-root-variant--restart-user-nonrootsh)
11. [Non-Root Jenkins Pipeline](#11-non-root-jenkins-pipeline)
12. [Root vs Non-Root — What Changes](#12-root-vs-non-root--what-changes)
13. [Next Tasks](#13-next-tasks)

---

## 1. Script Syntax

```
restart-tomcat.sh <tomcat_user> [port]
```

| Argument | Required | Default | Notes |
|---|---|---|---|
| `tomcat_user` | Yes | — | OS user Tomcat runs/owns process as. Also derives `CATALINA_HOME` as `/home/<tomcat_user>/<tomcat_user>` |
| `port` | No | `8080` | Used only for post-start `ss` listening check |

---

## 2. restart-tomcat.sh (full script — root/sudo)

```bash
#!/bin/bash
#
# restart-tomcat.sh
# Restart Tomcat for a given OS user.
#
# Author: Sagar Malla
# Title:  DevOps Engineer
#
# Usage: ./restart-tomcat.sh <tomcat_user> [port]
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[FAIL]${NC} $1" >&2; }

USER="$1"
PORT="${2:-8080}"
TOMCAT_HOME="/home/${USER}/${USER}"

if [[ -z "$USER" ]]; then
    log_err "Usage: $0 <tomcat_user> [port]"
    exit 1
fi

if ! id "$USER" &>/dev/null; then
    log_err "User does not exist: $USER"
    exit 1
fi

# correct PID lookup — scoped to this user's tomcat/catalina process
get_pid() {
    pgrep -u "$USER" -f "catalina.base=${TOMCAT_HOME}" 2>/dev/null || \
    pgrep -u "$USER" -f "org.apache.catalina.startup.Bootstrap" 2>/dev/null
}

PID=$(get_pid)

if [[ -n "$PID" ]]; then
    log_info "Process for $USER running with PID $PID"
    log_warn "Killing PID $PID"
    kill -9 $PID
    sleep 2

    if kill -0 $PID 2>/dev/null; then
        log_err "PID $PID still alive after kill -9. Aborting."
        exit 3
    fi
    log_ok "Process stopped"
else
    log_warn "No running process found for $USER — proceeding to start"
fi

log_info "Starting Tomcat for $USER"
su - "$USER" -c "${TOMCAT_HOME}/bin/startup.sh"
sleep 3

NEW_PID=$(get_pid)
if [[ -z "$NEW_PID" ]]; then
    log_err "Tomcat failed to start for $USER"
    exit 4
fi
log_ok "Tomcat started. PID: $NEW_PID"

if command -v ss &>/dev/null; then
    if ss -tulnp 2>/dev/null | grep -q ":${PORT} "; then
        log_ok "Port ${PORT} is listening"
    else
        log_warn "Port ${PORT} not listening yet — may still be initializing"
    fi
fi

log_ok "Restart complete for $USER"
exit 0
```

---

## 3. Direct Bash Usage

Run manually on the destination server to test before wiring into Jenkins:

```bash
chmod +x restart-tomcat.sh

# default port 8080
./restart-tomcat.sh tomcatapp

# explicit port
./restart-tomcat.sh tomcatapp 8443
```

---

## 4. Jenkins Pipeline — Basic

```groovy
stage("Restart Tomcat") {
    steps {
        script {
            withCredentials([usernamePassword(credentialsId: 'root-rc-server', passwordVariable: 'pass', usernameVariable: 'user')]) {
                remote.name = "${env.server_name}"
                remote.host = "${env.server_url}"
                remote.user = user
                remote.password = pass
                remote.timeoutSec = 60
                remote.allowAnyHosts = true

                sshCommand remote: remote, command: "sh /root/restart-tomcat.sh ${env.server_username} 8080", sudo: true
            }
        }
    }
}
```

---

## 5. Jenkins Pipeline — Exit Code Handling

`sshCommand` returns stdout, not the remote exit code — append `; echo EXIT:$?` and parse it to detect failure.

```groovy
stage("Restart Tomcat") {
    steps {
        script {
            withCredentials([usernamePassword(credentialsId: 'root-rc-server', passwordVariable: 'pass', usernameVariable: 'user')]) {
                remote.name = "${env.server_name}"
                remote.host = "${env.server_url}"
                remote.user = user
                remote.password = pass
                remote.timeoutSec = 60
                remote.allowAnyHosts = true

                def output = sshCommand remote: remote, command: "sh /root/restart-tomcat.sh ${env.server_username} 8080; echo EXIT:\$?", sudo: true
                def exitCode = (output =~ /EXIT:(\d+)/)[0][1] as Integer
                echo "${output}"

                if (exitCode != 0) {
                    error "Tomcat restart failed with exit code ${exitCode} on ${env.server_name}"
                }
            }
        }
    }
}
```

---

## 6. Jenkins Pipeline — Rolling Restart (Multi-Node)

```groovy
stage("Rolling Restart") {
    steps {
        script {
            def nodes = ['tomcat-node1', 'tomcat-node2']

            withCredentials([usernamePassword(credentialsId: 'root-rc-server', passwordVariable: 'pass', usernameVariable: 'user')]) {
                nodes.each { node ->
                    remote.name = node
                    remote.host = node
                    remote.user = user
                    remote.password = pass
                    remote.timeoutSec = 60
                    remote.allowAnyHosts = true

                    def output = sshCommand remote: remote, command: "sh /root/restart-tomcat.sh ${env.server_username} 8080; echo EXIT:\$?", sudo: true
                    def exitCode = (output =~ /EXIT:(\d+)/)[0][1] as Integer
                    echo "${node}: ${output}"

                    if (exitCode != 0) {
                        error "Tomcat restart failed on ${node} (exit ${exitCode}) — aborting rolling restart"
                    }
                }
            }
        }
    }
}
```
Restarts one node at a time, aborts remaining nodes on first failure — avoids dropping all backends behind the LB simultaneously.

---

## 7. Argument / Command Syntax Breakdown

```
sh /root/restart-tomcat.sh  ${env.server_username}  8080
│         │                       │                 │
│         │                       │                 └─ arg2: port (optional, default 8080)
│         │                       └─ arg1: tomcat_user (required)
│         └─ script path on remote server
└─ shell invocation (script has #!/bin/bash shebang; sh works since script avoids bashisms incompatible with POSIX sh — bash-specific syntax like [[ ]] still runs fine under bash even when called via `sh` IF /bin/sh is symlinked to bash, as on most RHEL/OL9 systems)
```

Derived internally by the script:
```
TOMCAT_HOME = /home/${tomcat_user}/${tomcat_user}
```

---

## 8. Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Bad arguments / user does not exist |
| 3 | Process still alive after `kill -9` (force-kill failed) |
| 4 | Tomcat failed to start (no PID found post-startup) |

---

## 9. Fixes vs Original Draft

| Issue in original | Fix applied |
|---|---|
| `PID=$(ps --user $1 f \| tail -n 1 ...)` — grabbed last line of `ps` output, not tomcat's actual PID | `pgrep -u $USER -f "catalina.base=..."` — scoped, reliable lookup |
| `pgrep -f -x $PID` — invalid usage (passing a PID as a name pattern) | `kill -0 $PID` — correct way to check if a PID is alive |
| Killed PID before checking if it was running | Check first (`get_pid`), then kill only if found |
| `su - $1 -c pkill -9 java` — killed **all** java processes for that user | Removed; only the specific tomcat PID is killed |
| `else` branch called `shutdown.sh` on an already-stopped process (dead logic) | Removed; not-running case just proceeds straight to startup |
| No exit codes — Jenkins couldn't detect failure | Added exit codes 1/3/4, plus post-start PID confirmation |

---

## 10. Non-Root Variant — restart-user-nonroot.sh

Runs entirely as the tomcat OS user — no `sudo`, no `su -`. Requires Jenkins to SSH into the server **directly as the tomcat user** (separate SSH credential per app user, or a shared deploy key added to each tomcat user's `~/.ssh/authorized_keys`).

`kill -9` on your own process works without root — that's the only permission this script relies on. No sudoers entry needed at all.

```bash
#!/bin/bash
#
# restart-user-nonroot.sh
# Restart Tomcat WITHOUT root/sudo/su. Intended to be run as the tomcat
# user itself (e.g. Jenkins connects via SSH directly as the tomcat user,
# or as a deploy user with matching UID/permissions on the process).
#
# Author: Sagar Malla
# Title:  DevOps Engineer
#
# Usage: ./restart-user-nonroot.sh [port]
#
# Note: no <tomcat_user> arg needed — script uses `whoami`, since it must
# already be running as that user (kill only works on your own processes
# without root anyway).
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[FAIL]${NC} $1" >&2; }

USER="$(whoami)"
PORT="${1:-8080}"
TOMCAT_HOME="/home/${USER}/${USER}"

if [[ "$USER" == "root" ]]; then
    log_err "This script must NOT be run as root. Connect via SSH as the tomcat user directly."
    exit 1
fi

if [[ ! -d "$TOMCAT_HOME" ]]; then
    log_err "Tomcat home not found: $TOMCAT_HOME"
    exit 2
fi

get_pid() {
    pgrep -u "$USER" -f "catalina.base=${TOMCAT_HOME}" 2>/dev/null || \
    pgrep -u "$USER" -f "org.apache.catalina.startup.Bootstrap" 2>/dev/null
}

PID=$(get_pid)

if [[ -n "$PID" ]]; then
    log_info "Process for $USER running with PID $PID"
    log_warn "Killing PID $PID"
    kill -9 $PID   # works without root — you own this process
    sleep 2

    if kill -0 $PID 2>/dev/null; then
        log_err "PID $PID still alive after kill -9. Aborting."
        exit 3
    fi
    log_ok "Process stopped"
else
    log_warn "No running process found for $USER — proceeding to start"
fi

log_info "Starting Tomcat"
"${TOMCAT_HOME}/bin/startup.sh"
sleep 3

NEW_PID=$(get_pid)
if [[ -z "$NEW_PID" ]]; then
    log_err "Tomcat failed to start"
    exit 4
fi
log_ok "Tomcat started. PID: $NEW_PID"

# port check without root — ss/netstat work fine unprivileged for TCP listening state
if command -v ss &>/dev/null; then
    if ss -tuln 2>/dev/null | grep -q ":${PORT} "; then
        log_ok "Port ${PORT} is listening"
    else
        log_warn "Port ${PORT} not listening yet — may still be initializing"
    fi
fi

log_ok "Restart complete for $USER"
exit 0
```

**Direct bash usage (already logged in as tomcat user):**
```bash
chmod +x restart-user-nonroot.sh
./restart-user-nonroot.sh          # default port 8080
./restart-user-nonroot.sh 8443     # custom port
```

---

## 11. Non-Root Jenkins Pipeline

Credential must be an SSH key or password **for the tomcat user itself**, not root. No `sudo: true` needed — nothing in the script requires elevated privileges.

```groovy
stage("Restart Tomcat (non-root)") {
    steps {
        script {
            withCredentials([usernamePassword(credentialsId: 'tomcat-user-server', passwordVariable: 'pass', usernameVariable: 'user')]) {
                remote.name = "${env.server_name}"
                remote.host = "${env.server_url}"
                remote.user = "${env.server_username}"   // connects AS the tomcat user directly
                remote.password = pass
                remote.timeoutSec = 60
                remote.allowAnyHosts = true

                sshCommand remote: remote, command: "sh /home/${env.server_username}/scripts/restart-user-nonroot.sh 8080"
            }
        }
    }
}
```

**With exit code handling:**
```groovy
stage("Restart Tomcat (non-root)") {
    steps {
        script {
            withCredentials([usernamePassword(credentialsId: 'tomcat-user-server', passwordVariable: 'pass', usernameVariable: 'user')]) {
                remote.name = "${env.server_name}"
                remote.host = "${env.server_url}"
                remote.user = "${env.server_username}"
                remote.password = pass
                remote.timeoutSec = 60
                remote.allowAnyHosts = true

                def output = sshCommand remote: remote, command: "sh /home/${env.server_username}/scripts/restart-user-nonroot.sh 8080; echo EXIT:\$?"
                def exitCode = (output =~ /EXIT:(\d+)/)[0][1] as Integer
                echo "${output}"

                if (exitCode != 0) {
                    error "Tomcat restart failed with exit code ${exitCode} on ${env.server_name}"
                }
            }
        }
    }
}
```

**Rolling restart, non-root:**
```groovy
stage("Rolling Restart (non-root)") {
    steps {
        script {
            def nodes = ['tomcat-node1', 'tomcat-node2']

            withCredentials([usernamePassword(credentialsId: 'tomcat-user-server', passwordVariable: 'pass', usernameVariable: 'user')]) {
                nodes.each { node ->
                    remote.name = node
                    remote.host = node
                    remote.user = "${env.server_username}"
                    remote.password = pass
                    remote.timeoutSec = 60
                    remote.allowAnyHosts = true

                    def output = sshCommand remote: remote, command: "sh /home/${env.server_username}/scripts/restart-user-nonroot.sh 8080; echo EXIT:\$?"
                    def exitCode = (output =~ /EXIT:(\d+)/)[0][1] as Integer
                    echo "${node}: ${output}"

                    if (exitCode != 0) {
                        error "Tomcat restart failed on ${node} (exit ${exitCode}) — aborting rolling restart"
                    }
                }
            }
        }
    }
}
```

---

## 12. Root vs Non-Root — What Changes

| Aspect | Root/Sudo Variant | Non-Root Variant |
|---|---|---|
| Script | `restart-tomcat.sh` | `restart-user-nonroot.sh` |
| SSH connects as | root (or user with sudoers rule) | tomcat user directly |
| Process start/stop | `su - $USER -c ...` | run directly, no wrapper |
| `kill -9` permission | root can kill any PID | works because you own the process (same UID) |
| Jenkins credential | root/admin SSH cred | per-app tomcat-user SSH cred |
| `sudo: true` in sshCommand | required | not needed |
| Sudoers config needed on server | yes, or full root SSH | none |
| Blast radius if credential leaks | full root on that host | limited to that one tomcat user's files/process |
| Script arg for user | `restart-tomcat.sh <user> [port]` | `restart-user-nonroot.sh [port]` (uses `whoami`) |

Non-root is the safer long-term posture — a compromised Jenkins credential only affects one app's user, not the whole box. Tradeoff: need a separate SSH credential per tomcat user in Jenkins credential store, and each tomcat user's `authorized_keys` needs the deploy key added — more setup work upfront.

---

## 13. Next Tasks

- [ ] Provision SSH access for Jenkins as each tomcat user directly (add deploy public key to `/home/<user>/.ssh/authorized_keys` per app user)
- [ ] Create per-app Jenkins credentials (`tomcat-user-<appname>`) instead of one shared root credential
- [ ] Migrate existing pipelines from `restart-tomcat.sh` (root/sudo) to `restart-user-nonroot.sh` (non-root) one app at a time — verify each before moving to the next
- [ ] Remove/narrow the root SSH credential once all apps are migrated, or restrict it to break-glass use only
- [ ] Audit sudoers entries on each server — remove any broad `NOPASSWD: ALL` rules once non-root path is confirmed working
- [ ] Add health-check URL support to `restart-user-nonroot.sh` (mirrors the optional health check in the earlier `restart-tomcat.sh` draft), if app-level `/health` endpoints exist
- [ ] Standardize script location across servers (e.g. always `/home/<user>/scripts/restart-user-nonroot.sh`) so Jenkins pipeline paths don't vary per node
- [ ] Document rollback procedure if a restart fails mid-deployment (previous WAR backup, redeploy steps)
