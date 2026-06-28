# HAProxy Logging — UDP

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7 / 9.8
**Transport:** UDP (`127.0.0.1:514`)
**Recommended for:** Remote central syslog where simplicity is preferred over delivery guarantee

---

## Overview

UDP is the traditional syslog transport and the default HAProxy logging method when no `tcp@` prefix is used. It is fire-and-forget — HAProxy sends log datagrams to rsyslog on UDP port 514 with no acknowledgment or retry. Simple to configure, low overhead, but messages can be silently dropped under high burst load.

When `chroot` is enabled, HAProxy sends outbound UDP datagrams to `127.0.0.1:514` via the network stack. Since UDP uses the network stack (not a socket file), chroot does **not** block UDP datagrams — no extra socket configuration needed inside the jail.

---

## How It Works

```
HAProxy (inside chroot /var/empty)
    └── UDP datagram → 127.0.0.1:514

rsyslog
    └── listens on UDP :514 (imudp module)
    └── writes to /var/log/haproxy/access.log

Remote syslog (optional)
    └── rsyslog can forward to remote:514 via UDP
```

---

## Step 1 — Prepare Directories

```bash
mkdir -p /var/log/haproxy
```

No chroot socket setup required — UDP uses the network stack, accessible from inside the jail.

---

## Step 2 — HAProxy Configuration

Edit `/etc/haproxy/haproxy.cfg`:

```haproxy
global
    maxconn         100000
    stats socket    /var/run/haproxy.stat mode 600 level admin
    log             127.0.0.1:514 local0
    log             127.0.0.1:514 local1 notice
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

No prefix needed — `127.0.0.1:514` without `tcp@` defaults to UDP.

---

## Step 3 — rsyslog Configuration

Create `/etc/rsyslog.d/haproxy.conf`:

```bash
cat > /etc/rsyslog.d/haproxy.conf << 'EOF'
module(load="imudp")
input(type="imudp" port="514")

local0.*    /var/log/haproxy/access.log
& stop
local1.*    /var/log/haproxy/notice.log
& stop
EOF
```

`module(load="imudp")` — loads UDP input module (not loaded by default on OL9).
`input(type="imudp" port="514")` — binds rsyslog to UDP port 514.
`& stop` after each rule — prevents log bleed into `/var/log/messages`. A single `& stop` at the end only stops the last matched facility — `local0` would still leak without its own stop.

---

## Step 4 — Apply Changes

```bash
systemctl restart rsyslog
systemctl reload haproxy
```

---

## Step 5 — Logrotate

Create `/etc/logrotate.d/haproxy`:

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

| Directive | Purpose |
|---|---|
| `daily` + `maxsize 1G` | Rotate daily, or immediately if file exceeds 1GB |
| `rotate 20` | Keep max 20 archived files |
| `maxage 3` | Delete archives older than 3 days |
| `compress` | gzip rotated files → `.gz` (immediate, no delaycompress) |
| `sharedscripts` | Run postrotate once for all `*.log` files |
| `dateext` + `dateformat` | Filename: `access.log-20260623-153748.gz` |
| `reload rsyslog` | HUP rsyslog — reopens file handles without dropping log pipeline |

---

## Step 6 — Hourly Cron

`logrotate.timer` runs daily and covers ALL configs in `/etc/logrotate.d/`. Do NOT change it to hourly — it would affect `btmp`, `dnf`, `nginx`, `rsyslog`, and other system logs.

Instead, add a dedicated cron for HAProxy only:

```bash
cat > /etc/cron.d/haproxy-logrotate << 'EOF'
# Run haproxy logrotate hourly — size/schedule enforced by config
0 * * * * root /usr/sbin/logrotate /etc/logrotate.d/haproxy
EOF
```

Do not use `-f` flag — it forces rotation every hour regardless of file size, bypassing `maxsize` and `daily` thresholds.

---

## Step 7 — Verify

```bash
# Confirm rsyslog listening on UDP 514
ss -ulnp | grep 514

# Validate HAProxy config
haproxy -c -f /etc/haproxy/haproxy.cfg

# Test rsyslog receiving local0
logger -p local0.info -d -n 127.0.0.1 -P 514 "haproxy udp test"
tail -f /var/log/haproxy/access.log

# HAProxy log counter — must be > 0 after traffic
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs

# Logrotate dry-run
logrotate -d /etc/logrotate.d/haproxy
```

Expected `ss` output:
```
UNCONN  0  0  0.0.0.0:514  0.0.0.0:*  users:(("rsyslogd",...))
```

---

## Optional — Forward to Remote Syslog Server

```
local0.*    /var/log/haproxy/access.log
& stop
local0.*    @remote-syslog.example.com:514     # @ = UDP forwarding
local1.*    /var/log/haproxy/notice.log
& stop
```

Single `@` = UDP forward. Double `@@` = TCP forward.

---

## Pros & Cons

| | Detail |
|---|---|
| **Pro** — Simple config | No module complexity, traditional syslog default |
| **Pro** — Low overhead | Stateless datagrams, no connection management |
| **Pro** — Remote capable | Easy forwarding to Graylog, ELK, remote syslog |
| **Pro** — Chroot friendly | UDP network stack accessible from inside jail — no extra socket setup |
| **Con** — No delivery guarantee | Fire-and-forget — messages silently dropped under burst load |
| **Con** — No error detection | HAProxy never knows if rsyslog received the datagram |
| **Con** — Port binding required | rsyslog must listen on UDP 514; check firewall if remote |

---

## UDP vs TCP — When to choose UDP

| Situation | Use UDP |
|---|---|
| Low-to-medium traffic volume | Yes — buffer overflow unlikely |
| Logs are supplementary, not critical | Yes |
| Remote syslog aggregation, simple setup | Yes |
| High burst traffic with zero log loss tolerance | No — use TCP or Unix socket instead |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `CumRecvLogs: 0` | rsyslog not on UDP 514 | Run `ss -ulnp \| grep 514` to confirm listener |
| `access.log` 0 bytes after rotation | rsyslog not reopening file handle | `systemctl reload rsyslog` |
| `/var/log/messages` filling disk | `& stop` missing per rule | Add `& stop` after each rsyslog facility rule |
| No `.gz` on rotated files | `delaycompress` present | Remove `delaycompress` |
| Logs missing under high load | UDP buffer overflow | Increase rsyslog `imudp` buffer or switch to Unix socket/TCP |
| Log file not created | imudp module not loaded | Check rsyslog.conf syntax with `rsyslogd -N1` |
| rsyslog not starting | imudp config syntax error | Run `rsyslogd -N1 -f /etc/rsyslog.conf` |

---

*HAProxy 2.8.14 — Oracle Linux 9.7/9.8 — UDP via rsyslog 8.2510.0*
