# HAProxy Logging — Unix Socket

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7  
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

HAProxy resolves `/dev/log` relative to chroot root at runtime — it will look for `/var/empty/dev/log` internally.

---

## Step 3 — rsyslog Configuration

Create `/etc/rsyslog.d/haproxy.conf`:

```bash
cat > /etc/rsyslog.d/haproxy.conf << 'EOF'
$AddUnixListenSocket /dev/log
$AddUnixListenSocket /var/empty/dev/log

local0.*    /var/log/haproxy/access.log
local1.*    /var/log/haproxy/notice.log

& stop
EOF
```

`$AddUnixListenSocket /dev/log` — system-wide socket for all other processes.  
`$AddUnixListenSocket /var/empty/dev/log` — socket visible to HAProxy inside chroot.  
`& stop` — prevents HAProxy logs from also polluting `/var/log/messages`.

---

## Step 4 — Apply Changes

```bash
systemctl restart rsyslog
systemctl reload haproxy
```

---

## Step 5 — Verify

```bash
# Both sockets must exist
ls -la /dev/log
ls -la /var/empty/dev/log

# Validate HAProxy config
haproxy -c -f /etc/haproxy/haproxy.cfg

# Test rsyslog receiving local0
logger -p local0.info "haproxy unix socket test"
tail -f /var/log/haproxy/access.log

# Check HAProxy log counter (must be > 0 after traffic)
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs
```

---

## Step 6 — Logrotate

Create `/etc/logrotate.d/haproxy`:

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

## Pros & Cons

| | Detail |
|---|---|
| **Pro** — Zero overhead | No network stack, direct socket write |
| **Pro** — No packet loss | Socket-based, no UDP drop risk |
| **Pro** — Simple config | No port binding, no firewall rules |
| **Con** — Local only | Cannot send to remote syslog server |
| **Con** — Chroot complexity | Extra socket required inside `/var/empty/dev/` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `CumRecvLogs: 0` | Chroot blocking `/dev/log` | Verify `/var/empty/dev/log` socket exists |
| Log file not created | No traffic or rsyslog not receiving | Run `logger -p local0.info test` to confirm rsyslog |
| rsyslog won't start | Config syntax error | Run `rsyslogd -N1 -f /etc/rsyslog.conf` |
| `/var/empty/dev/log` missing after rsyslog restart | rsyslog re-creates on start | Ensure `mkdir -p /var/empty/dev` was done |

---

*HAProxy 2.8.14 — Oracle Linux 9.7 — Unix Socket via rsyslog*
