# HAProxy Logging — Unix Socket

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7 / 9.8
**Transport:** Unix Socket (`/dev/log`)
**Recommended for:** Local logging on same server

---

## Overview

Unix socket is the most efficient logging method for HAProxy when rsyslog runs on the same machine. No network stack involved — HAProxy writes log entries directly to a socket file managed by rsyslog. Zero packet loss risk and lowest possible overhead.

When `chroot` is enabled, HAProxy drops into a jail directory after startup and can no longer see `/dev/log`. A second socket must be created inside the chroot directory so HAProxy can still reach rsyslog.

---

## How It Works

```
HAProxy (inside chroot /var/empty)
    └── writes to /var/empty/dev/log  ← socket inside jail

rsyslog
    └── listens on /dev/log           ← system socket
    └── listens on /var/empty/dev/log ← socket for chrooted HAProxy
    └── writes to /var/log/haproxy/access.log
```

---

## Step 1 — Prepare Directories

```bash
# Create dev dir inside chroot jail
mkdir -p /var/empty/dev

# Create log output directory
mkdir -p /var/log/haproxy
```

---

## Step 2 — HAProxy Configuration

Edit `/etc/haproxy/haproxy.cfg`:

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

HAProxy resolves `/dev/log` relative to the chroot root at runtime — it looks for `/var/empty/dev/log` internally.

---

## Step 3 — rsyslog Configuration

Create `/etc/rsyslog.d/haproxy.conf`:

```bash
cat > /etc/rsyslog.d/haproxy.conf << 'EOF'
$AddUnixListenSocket /dev/log
$AddUnixListenSocket /var/empty/dev/log

local0.*    /var/log/haproxy/access.log
& stop
local1.*    /var/log/haproxy/notice.log
& stop
EOF
```

`$AddUnixListenSocket /dev/log` — system-wide socket for all other processes.
`$AddUnixListenSocket /var/empty/dev/log` — socket visible to HAProxy inside chroot.
`& stop` after each rule — prevents log bleed into `/var/log/messages`. A single `& stop` at the end only stops the last matched facility — `local0` would still leak without its own stop.

---

## Step 4 — Chroot Socket Persistence

`/var/empty/dev/` can be lost on reboot or OS update. Use `systemd-tmpfiles` to ensure the directory is always recreated at boot before rsyslog starts:

```bash
cat > /etc/tmpfiles.d/haproxy-chroot.conf << 'EOF'
d /var/empty/dev 0755 root root -
EOF

systemd-tmpfiles --create /etc/tmpfiles.d/haproxy-chroot.conf
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

## Step 5 — Apply Changes

```bash
systemctl restart rsyslog
systemctl reload haproxy
```

---

## Step 6 — Logrotate

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

## Step 7 — Hourly Cron

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

## Step 8 — Verify

```bash
# Both sockets must exist
ls -la /dev/log
ls -la /var/empty/dev/log

# tmpfiles.d entry in place
cat /etc/tmpfiles.d/haproxy-chroot.conf

# Validate HAProxy config
haproxy -c -f /etc/haproxy/haproxy.cfg

# Test rsyslog receiving local0
logger -p local0.info "haproxy unix socket test"
tail -f /var/log/haproxy/access.log

# HAProxy log counter — must be > 0 after traffic
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs

# Logrotate dry-run
logrotate -d /etc/logrotate.d/haproxy
```

---

## Pros & Cons

| | Detail |
|---|---|
| **Pro** — Zero overhead | No network stack, direct socket write |
| **Pro** — No packet loss | Socket-based, no UDP drop risk |
| **Pro** — Simple config | No port binding, no firewall rules |
| **Con** — Local only | Cannot send to remote syslog server |
| **Con** — Chroot complexity | Extra socket required inside `/var/empty/dev/` + tmpfiles.d for persistence |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `CumRecvLogs: 0` | Chroot blocking `/dev/log` | Verify `/var/empty/dev/log` socket exists |
| `/var/empty/dev/log` missing after reboot | `/var/empty/dev/` directory lost | Add `tmpfiles.d` entry |
| `access.log` 0 bytes after rotation | rsyslog not reopening file handle | `systemctl reload rsyslog` |
| `/var/log/messages` filling disk | `& stop` missing per rule | Add `& stop` after each rsyslog facility rule |
| No `.gz` on rotated files | `delaycompress` present | Remove `delaycompress` |
| Log file not created | No traffic or rsyslog not receiving | Run `logger -p local0.info test` |
| rsyslog won't start | Config syntax error | Run `rsyslogd -N1 -f /etc/rsyslog.conf` |

---

*HAProxy 2.8.14 — Oracle Linux 9.7/9.8 — Unix Socket via rsyslog 8.2510.0*
