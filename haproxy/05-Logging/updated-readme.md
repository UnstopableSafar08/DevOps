# HAProxy Logging Configuration Guide

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7  
**Date:** June 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Logging Methods Comparison](#logging-methods-comparison)
3. [Unix Socket (Recommended)](#unix-socket-recommended)
4. [TCP Logging](#tcp-logging)
5. [UDP Logging](#udp-logging)
6. [Chroot — Why, Pros & Cons](#chroot--why-pros--cons)
7. [Full Configuration](#full-configuration)
8. [rsyslog Configuration](#rsyslog-configuration)
9. [Logrotate](#logrotate)
10. [Timeout Inheritance](#timeout-inheritance)
11. [Verification](#verification)
12. [Troubleshooting](#troubleshooting)

---

## Overview

HAProxy does not write logs directly to disk. It forwards log entries to a syslog-compatible daemon (rsyslog, syslog-ng, etc.) via one of three transports:

- Unix socket (`/dev/log`)
- UDP (`127.0.0.1:514`)
- TCP (`tcp@127.0.0.1:514`)

rsyslog then writes to disk. On Oracle Linux 9 (RHEL-family), rsyslog is the default syslog daemon.

---

## Logging Methods Comparison

| Feature | Unix Socket `/dev/log` | UDP `127.0.0.1:514` | TCP `tcp@127.0.0.1:514` |
|---|---|---|---|
| Transport overhead | None | Minimal | Low |
| Message loss risk | None | Possible under burst | None (connection-based) |
| Remote logging support | No | Yes | Yes |
| Connection resilience | N/A — socketfile | Fire-and-forget | Reconnect on failure |
| HAProxy chroot impact | Requires socket inside chroot | Not affected | Not affected |
| Config complexity | Low | Low | Low |
| Best for | Local logging | Remote/central syslog | Remote with delivery guarantee |
| HAProxy directive syntax | `log /dev/log local0` | `log 127.0.0.1:514 local0` | `log tcp@127.0.0.1:514 local0` |

### Recommendation

| Use case | Recommended method |
|---|---|
| Logs stay on same server | **Unix socket** (`/dev/log`) |
| Send to remote syslog (Graylog, ELK, etc.) | **UDP** (simple) or **TCP** (reliable delivery) |
| Remote + guaranteed delivery | **TCP** |

---

## Unix Socket (Recommended)

Unix socket is the most efficient method for local logging. No network stack involved — HAProxy writes directly to a socket file managed by rsyslog.

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

When `chroot` is enabled (e.g., `chroot /var/empty`), HAProxy can no longer see `/dev/log` after dropping into the jail. The socket must also be created inside the chroot directory:

```
/var/empty/dev/log   ← HAProxy sees this after chroot
/dev/log             ← System processes use this
```

Both are configured in rsyslog (see [rsyslog Configuration](#rsyslog-configuration)).

---

## TCP Logging

TCP syslog provides connection-based delivery with reconnect support. Preferred over UDP when sending to a remote syslog server and message loss is unacceptable.

### HAProxy global section

```haproxy
global
    log tcp@127.0.0.1:514 local0
    log tcp@127.0.0.1:514 local1 notice
```

### rsyslog — imtcp module

```
module(load="imtcp")
input(type="imtcp" port="514")

local0.*    /var/log/haproxy/access.log
local1.*    /var/log/haproxy/notice.log

& stop
```

### TCP caveat

If rsyslog restarts or the TCP connection drops, HAProxy log entries are lost until reconnection. For local logging, Unix socket is more resilient. TCP shines for remote central logging where the remote server is always available.

---

## UDP Logging

UDP is the traditional syslog transport. Simple, low overhead, but fire-and-forget — no delivery guarantee.

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
local1.*    /var/log/haproxy/notice.log

& stop
```

### UDP caveat

Under high load, the UDP socket buffer can overflow and silently drop log messages. Acceptable for non-critical environments or where log completeness is not required. For production traffic logging, Unix socket or TCP is preferred.

---

## Chroot — Why, Pros & Cons

### What is chroot?

`chroot` changes the apparent root directory for a process. After HAProxy starts and binds its ports, it calls `chroot()` to drop into a restricted directory (e.g., `/var/empty`). From that point, the process sees `/var/empty` as its `/` — it cannot navigate to or read anything outside it.

```
Without chroot:                  With chroot /var/empty:
/                                /var/empty/  ← HAProxy sees this as /
├── etc/passwd   ← readable      (empty — nothing here by default)
├── etc/shadow   ← readable      cannot escape
├── var/log/     ← writable      no binaries, no config files
└── bin/bash     ← executable    no /etc, no /var
```

HAProxy binds ports and opens file descriptors **before** calling chroot, so listener sockets, the stats socket, and log sockets that are set up at startup continue to work inside the jail.

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
| Resolvers limited | DNS resolution after start can fail; use `resolvers` directive with IP or pre-resolve at start |
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

Combined, these three directives (chroot + user/group drop + daemon) represent the standard HAProxy security hardening baseline.

### Chroot + logging fix

```bash
# Create dev dir inside chroot
mkdir -p /var/empty/dev

# rsyslog creates sockets at both paths
$AddUnixListenSocket /dev/log
$AddUnixListenSocket /var/empty/dev/log
```

---

## Full Configuration

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

### Timeout inheritance

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

Override only where a specific service needs a different value (e.g., WebSocket backends, large file uploads).

---

## rsyslog Configuration

### `/etc/rsyslog.d/haproxy.conf`

```
$AddUnixListenSocket /dev/log
$AddUnixListenSocket /var/empty/dev/log

local0.*    /var/log/haproxy/access.log
local1.*    /var/log/haproxy/notice.log

& stop
```

`& stop` — prevents HAProxy log entries from also appearing in `/var/log/messages`.

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
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
```

---

## Verification

### Check socket exists

```bash
ls -la /dev/log
ls -la /var/empty/dev/log
```

### Validate HAProxy config

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

### Test rsyslog is receiving local0

```bash
logger -p local0.info "haproxy log test"
tail -f /var/log/haproxy/access.log
```

### Check HAProxy received log count

```bash
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs
```

`CumRecvLogs` should increment with traffic. If stuck at `0`, HAProxy is not reaching the syslog socket — check chroot path.

### Live traffic logs

```bash
tail -f /var/log/haproxy/access.log
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/var/log/haproxy/access.log` not created | No traffic yet, or rsyslog not receiving | Run `logger -p local0.info test` to verify rsyslog |
| `CumRecvLogs: 0` after traffic | Chroot blocking `/dev/log` access | Add `$AddUnixListenSocket /var/empty/dev/log` to rsyslog |
| Log file created but empty | `option dontlognull` dropping empty requests | Send real HTTP request to test |
| rsyslog not starting | Syntax error in haproxy.conf | Run `rsyslogd -N1 -f /etc/rsyslog.conf` to validate |
| HAProxy config invalid | Timeout or mode missing in defaults | Run `haproxy -c -f /etc/haproxy/haproxy.cfg` |

---

*HAProxy 2.8.14 — Oracle Linux 9.7 — rsyslog*
