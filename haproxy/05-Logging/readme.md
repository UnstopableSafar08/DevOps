# HAProxy Logging Configuration Guide

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7 / 9.8
**rsyslog:** 8.2510.0
**logrotate:** 3.18.0
**Date:** June 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Logging Methods Comparison](#logging-methods-comparison)
3. [Unix Socket (Recommended)](#unix-socket-recommended)
4. [TCP Logging](#tcp-logging)
5. [UDP Logging](#udp-logging)
6. [Chroot — Why, Pros & Cons](#chroot--why-pros--cons)
7. [Full HAProxy Configuration](#full-haproxy-configuration)
8. [rsyslog Configuration](#rsyslog-configuration)
9. [Logrotate](#logrotate)
10. [Hourly Rotation — Cron vs systemd Timer](#hourly-rotation--cron-vs-systemd-timer)
11. [Chroot Socket Persistence](#chroot-socket-persistence)
12. [Disk Space Management](#disk-space-management)
13. [Timeout Inheritance](#timeout-inheritance)
14. [Verification](#verification)
15. [Troubleshooting](#troubleshooting)

---

## Overview

HAProxy does not write logs directly to disk. It forwards log entries to a syslog-compatible daemon (rsyslog) via one of three transports:

- Unix socket (`/dev/log`) — recommended for local logging
- UDP (`127.0.0.1:514`) — remote syslog, simple
- TCP (`tcp@127.0.0.1:514`) — remote syslog, guaranteed delivery

rsyslog then writes to disk. On Oracle Linux 9 (RHEL-family), rsyslog is the default syslog daemon and is fully integrated with systemd.

---

## Logging Methods Comparison

| Feature | Unix Socket `/dev/log` | UDP `127.0.0.1:514` | TCP `tcp@127.0.0.1:514` |
|---|---|---|---|
| Transport overhead | None | Minimal | Low |
| Message loss risk | None | Possible under burst | None (connection-based) |
| Remote logging support | No | Yes | Yes |
| Connection resilience | N/A — socket file | Fire-and-forget | Reconnect on failure |
| HAProxy chroot impact | Requires socket inside chroot | Not affected | Not affected |
| Config complexity | Low | Low | Low |
| Best for | Local logging | Remote/central syslog | Remote with delivery guarantee |
| HAProxy directive syntax | `log /dev/log local0` | `log 127.0.0.1:514 local0` | `log tcp@127.0.0.1:514 local0` |

### Recommendation

| Use case | Recommended method |
|---|---|
| Logs stay on same server | Unix socket (`/dev/log`) |
| Send to remote syslog (Graylog, ELK, etc.) | UDP (simple) or TCP (reliable) |
| Remote + guaranteed delivery | TCP |

---

## Unix Socket (Recommended)

Unix socket is the most efficient method for local logging. No network stack involved — HAProxy writes directly to a socket file managed by rsyslog. Zero packet loss risk and lowest possible overhead.

### HAProxy global section

```haproxy
global
    log /dev/log local0
    log /dev/log local1 notice
```

### Syslog facility levels

| Facility | Purpose |
|---|---|
| `local0` | All HAProxy traffic logs (access logs) |
| `local1 notice` | Notices and above only (warnings, errors) |

### Chroot caveat

When `chroot` is enabled, HAProxy drops into `/var/empty` after startup and can no longer see `/dev/log`. A second socket must be created inside the chroot directory:

```
/var/empty/dev/log   ← HAProxy sees this after chroot
/dev/log             ← System processes use this
```

Both are configured in rsyslog. See [rsyslog Configuration](#rsyslog-configuration) and [Chroot Socket Persistence](#chroot-socket-persistence).

---

## TCP Logging

TCP syslog uses a persistent connection between HAProxy and rsyslog. Unlike UDP, TCP is connection-based — lost connections are detected and retried, making it suitable when log delivery guarantee matters.

### HAProxy global section

```haproxy
global
    log tcp@127.0.0.1:514 local0
    log tcp@127.0.0.1:514 local1 notice
```

The `tcp@` prefix is required — without it HAProxy defaults to UDP.

### rsyslog — imtcp module

```
module(load="imtcp")
input(type="imtcp" port="514")

local0.*    /var/log/haproxy/access.log
& stop
local1.*    /var/log/haproxy/notice.log
& stop
```

### TCP caveat

If rsyslog restarts, HAProxy log entries are lost until reconnection. For local logging, Unix socket is more resilient. TCP shines for remote central logging.

---

## UDP Logging

UDP is the traditional syslog transport — fire-and-forget with no delivery guarantee. Simple to configure, low overhead, but messages can be silently dropped under high burst load.

### HAProxy global section

```haproxy
global
    log 127.0.0.1:514 local0
    log 127.0.0.1:514 local1 notice
```

### rsyslog — imudp module

```
module(load="imudp")
input(type="imudp" port="514")

local0.*    /var/log/haproxy/access.log
& stop
local1.*    /var/log/haproxy/notice.log
& stop
```

---

## Chroot — Why, Pros & Cons

### What is chroot?

`chroot` changes the apparent root directory for a process. After HAProxy starts and binds its ports, it calls `chroot()` to drop into `/var/empty`. From that point, the process sees `/var/empty` as its `/` — it cannot navigate to or read anything outside it.

```
Without chroot:                  With chroot /var/empty:
/                                /var/empty/  ← HAProxy sees this as /
├── etc/passwd   ← readable      (empty — nothing here by default)
├── etc/shadow   ← readable      cannot escape
├── var/log/     ← writable      no binaries, no config files
└── bin/bash     ← executable    no /etc, no /var
```

HAProxy binds ports and opens file descriptors **before** calling chroot, so listener sockets, the stats socket, and log sockets set up at startup continue to work inside the jail.

### Why use it?

If an attacker exploits a vulnerability in HAProxy (buffer overflow, RCE, etc.), the chroot jail limits the blast radius. The attacker is trapped in an empty directory with no files, no binaries, and no path to the real filesystem.

### Pros

| Pro | Detail |
|---|---|
| Limits filesystem exposure | Attacker cannot read `/etc/passwd`, `/etc/shadow`, config files, or other sensitive data |
| Prevents binary execution | No binaries inside `/var/empty` to pivot with |
| Defense in depth | Works alongside `user haproxy` and `group haproxy` drops — multiple layers |
| Industry standard | Recommended in HAProxy documentation and security hardening guides |
| Zero performance cost | One-time syscall at startup — no runtime overhead |

### Cons

| Con | Detail |
|---|---|
| Socket path complexity | Syslog socket (`/dev/log`) must be replicated inside chroot — requires extra rsyslog config |
| Resolvers limited | DNS resolution after start can fail; use IP-based resolvers or pre-resolve at start |
| Debugging harder | `strace`, `/proc` access limited inside jail |
| Runtime file access blocked | Any file HAProxy needs post-startup must be pre-opened before chroot or placed inside jail |

### Best practice config

```haproxy
global
    chroot          /var/empty
    user            haproxy
    group           haproxy
    daemon
```

Combined, these three directives (chroot + user/group drop + daemon) are the standard HAProxy security hardening baseline.

---

## Full HAProxy Configuration

### `/etc/haproxy/haproxy.cfg`

```haproxy
global
    maxconn         100000
    stats socket    /var/run/haproxy.stat mode 600 level admin
    log             /dev/log local0
    log             /dev/log local1 notice
    chroot          /var/empty
    pidfile         /var/run/haproxy.pid
    user            haproxy
    group           haproxy
    daemon
    nbthread        4

defaults
    mode            http
    log             global
    option          httplog
    option          dontlognull
    timeout connect 5s
    timeout client  30s
    timeout server  30s
```

---

## rsyslog Configuration

### `/etc/rsyslog.d/haproxy.conf`

`& stop` must appear after **each** rule to prevent HAProxy logs from leaking into `/var/log/messages`. A single `& stop` at the end only stops the last matched facility.

```
$AddUnixListenSocket /dev/log
$AddUnixListenSocket /var/empty/dev/log

local0.*    /var/log/haproxy/access.log
& stop
local1.*    /var/log/haproxy/notice.log
& stop
```

`$AddUnixListenSocket /dev/log` — system-wide socket for all other processes.
`$AddUnixListenSocket /var/empty/dev/log` — socket visible to HAProxy inside chroot.
`& stop` after each rule — fully prevents log bleed into `/var/log/messages`.

### Apply

```bash
mkdir -p /var/empty/dev
mkdir -p /var/log/haproxy

systemctl restart rsyslog
systemctl reload haproxy
```

---

## Logrotate

### `/etc/logrotate.d/haproxy`

```
/var/log/haproxy/*.log {
    daily
    maxsize 1G
    missingok
    rotate 20
    maxage 3
    compress
    notifempty
    create 0640 root root
    sharedscripts
    dateext
    dateformat -%Y%m%d-%H%M%S
    postrotate
        /usr/bin/systemctl reload rsyslog >/dev/null 2>&1 || true
    endscript
}
```

### Directive reference

| Directive | Value | Purpose |
|---|---|---|
| `daily` | — | Rotate daily at minimum |
| `maxsize 1G` | 1GB | Also rotate if file exceeds 1GB before daily trigger |
| `rotate 20` | 20 | Keep max 20 archived files |
| `maxage 3` | 3 days | Delete archives older than 3 days regardless of count |
| `compress` | — | Compress rotated files with gzip → `.gz` |
| `notifempty` | — | Skip rotation if log file is empty |
| `create 0640 root root` | — | Create fresh log file after rotation with correct permissions |
| `sharedscripts` | — | Run postrotate once for all `*.log` files, not once per file |
| `dateext` | — | Append date/time to rotated filename |
| `dateformat -%Y%m%d-%H%M%S` | — | Format: `access.log-20260623-153748.gz` |
| `postrotate reload` | — | Send HUP to rsyslog — reopens file handles without dropping log pipeline |

### Why `reload` not `restart` in postrotate

On Oracle Linux 9, `rsyslog.service` defines `ExecReload=/bin/kill -HUP $MAINPID`. Running `reload` sends HUP — rsyslog simply reopens its log file handles without terminating the processing pipeline. Using `restart` would briefly interrupt the daemon and risk dropping log messages from HAProxy during that window.

### Why `daily` + `maxsize` not `size` alone

| Directive | Behavior |
|---|---|
| `size 1G` | Rotate ONLY when size exceeded — ignores daily schedule |
| `maxsize 1G` | Rotate when size exceeded OR daily — whichever comes first |
| `daily` alone | Rotate every day regardless of size |

`daily` + `maxsize 1G` ensures daily rotation even on low-traffic days, and immediate size-triggered rotation during traffic spikes.

### Expected output after rotation

```
access.log                          ← live (fresh empty file)
access.log-20260624-010001.gz  ✅   ← latest rotation, compressed
access.log-20260623-010001.gz       ← previous rotation
error.log                           ← live
error.log-20260624-010001.gz        ← rotated
```

---

## Hourly Rotation — Cron vs systemd Timer

### Do NOT change `logrotate.timer` to hourly

`logrotate.timer` runs ALL configs in `/etc/logrotate.d/` — that includes `btmp`, `chrony`, `dnf`, `falcon-sensor`, `nginx`, `rsyslog`, `salt`, and others. Changing the timer to hourly breaks all of them.

### Correct approach — cron for haproxy only

Create `/etc/cron.d/haproxy-logrotate` (system cron, not user crontab):

```bash
cat > /etc/cron.d/haproxy-logrotate << 'EOF'
# Run haproxy logrotate hourly — size/schedule enforced by config
0 * * * * root /usr/sbin/logrotate /etc/logrotate.d/haproxy
EOF
```

### `logrotate` vs `logrotate -f`

| Command | Behavior |
|---|---|
| `logrotate /etc/logrotate.d/haproxy` | Respects `maxsize` and `daily` — only rotates when threshold exceeded |
| `logrotate -f /etc/logrotate.d/haproxy` | Forces rotation every run — ignores size/schedule thresholds |

Never use `-f` in production cron. It forces rotation every hour regardless of file size, exhausting `rotate 20` slots in 20 hours.

### Crontab format

```
# /etc/cron.d/ — username field required
0 * * * * root /usr/sbin/logrotate /etc/logrotate.d/haproxy

# crontab -e — NO username field
0 * * * * /usr/sbin/logrotate /etc/logrotate.d/haproxy
```

---

## Chroot Socket Persistence

`/var/empty/dev/` can be lost on OS update or reboot. rsyslog cannot create `/var/empty/dev/log` if the directory does not exist.

Use `systemd-tmpfiles` to ensure the directory is always recreated at boot before rsyslog starts:

```bash
cat > /etc/tmpfiles.d/haproxy-chroot.conf << 'EOF'
d /var/empty/dev 0755 root root -
EOF
```

Apply immediately:

```bash
systemd-tmpfiles --create /etc/tmpfiles.d/haproxy-chroot.conf
ls -la /var/empty/dev/
```

Boot sequence with this in place:

```
boot
 └── systemd-tmpfiles  → creates /var/empty/dev/
 └── rsyslog starts    → creates /var/empty/dev/log socket
 └── haproxy starts    → connects to socket
 └── logs flow ✅
```

---

## Disk Space Management

### Check disk usage

```bash
du -sh /var/log/haproxy/*
df -h /var/log/haproxy/
```

### Manually compress old uncompressed files

HAProxy text logs compress approximately 10:1 with gzip. A 1.8G file compresses to ~180M.

```bash
gzip /var/log/haproxy/access.log-<date>
gzip /var/log/haproxy/access-1.log-<date>
gzip /var/log/haproxy/error.log-<date>
```

### Emergency — free disk when /var is full

```bash
# Remove old rotated logs, keep latest 20
find /var/log/haproxy/ -name "*.gz" | sort -r | tail -n +21 | xargs rm -f

# Truncate live log only if critically full — do NOT delete
truncate -s 0 /var/log/haproxy/access.log

# Verify disk freed
df -h /var
```

### Prevent `/var/log/messages` disk fill

If `& stop` is missing after each rsyslog rule, HAProxy logs duplicate into `/var/log/messages`. A single `& stop` at the end only stops the last matched facility — local0 still leaks. Always use `& stop` after each rule:

```
local0.*    /var/log/haproxy/access.log
& stop
local1.*    /var/log/haproxy/notice.log
& stop
```

---

## Timeout Inheritance

Timeouts defined in `defaults` are inherited by all frontends and backends unless explicitly overridden.

```
defaults
└── timeout connect 5s    ← base value
└── timeout client  30s   ← base value
└── timeout server  30s   ← base value

frontend web
└── timeout client  60s   ← overrides defaults (60s used)

backend api
└── timeout server  120s  ← overrides defaults (120s used)
└── timeout connect       ← NOT set → inherits 5s from defaults

backend static
└── (nothing set)         ← inherits all timeouts from defaults
```

Override only where a specific service needs a different value (e.g., WebSocket backends, file upload backends).

---

## Verification

```bash
# Sockets exist
ls -la /dev/log
ls -la /var/empty/dev/log

# HAProxy config valid
haproxy -c -f /etc/haproxy/haproxy.cfg

# rsyslog receiving local0
logger -p local0.info "haproxy log test"
tail -f /var/log/haproxy/access.log

# HAProxy log counter — must be > 0 after traffic
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs

# Cron installed correctly
cat /etc/cron.d/haproxy-logrotate

# Logrotate dry-run
logrotate -d /etc/logrotate.d/haproxy

# Check rotation state
cat /var/lib/logrotate/logrotate.status
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `access.log` empty / 0 bytes after rotation | rsyslog not reopening file handle | `systemctl reload rsyslog` |
| `CumRecvLogs: 0` after traffic | Chroot blocking `/dev/log` access | Verify `/var/empty/dev/log` socket exists |
| `/var/empty/dev/log` missing after reboot | `/var/empty/dev/` directory lost | Add `tmpfiles.d` entry |
| `/var/log/messages` filling disk | `& stop` only at end of rsyslog config | Add `& stop` after each rule |
| No `.gz` on rotated files | `delaycompress` present | Remove `delaycompress` for immediate compression |
| Rotation not happening hourly | Using `logrotate.timer` instead of cron | Use `/etc/cron.d/haproxy-logrotate` |
| All system logs rotating hourly | `logrotate.timer` changed to hourly | Revert timer, use cron for haproxy only |
| Rotate runs but file unchanged | `-f` flag missing or size not exceeded | Remove `-f`, check file size vs `maxsize` |
| rsyslog not starting | Syntax error in haproxy.conf | Run `rsyslogd -N1 -f /etc/rsyslog.conf` |
| HAProxy config invalid | Timeout or mode missing | Run `haproxy -c -f /etc/haproxy/haproxy.cfg` |

---

*HAProxy 2.8.14 — Oracle Linux 9.7/9.8 — rsyslog 8.2510.0 — logrotate 3.18.0*
