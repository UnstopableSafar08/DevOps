# HAProxy Logging — TCP

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7  
**Transport:** TCP (`tcp@127.0.0.1:514`)  
**Recommended for:** Remote central syslog with guaranteed delivery

---

## Overview

TCP syslog uses a persistent connection between HAProxy and rsyslog. Unlike UDP, TCP is connection-based — lost connections are detected and retried, making it suitable when log delivery guarantee matters. Most commonly used when shipping logs to a remote syslog server (Graylog, ELK, Loki, etc.).

When `chroot` is enabled, HAProxy connects outbound to `127.0.0.1:514` via TCP. Since TCP uses the network stack (not a socket file), chroot does **not** block TCP connections — no extra configuration needed inside the jail for transport. However, rsyslog still runs outside the jail and writes logs to disk normally.

---

## How It Works

```
HAProxy (inside chroot /var/empty)
    └── TCP connect → 127.0.0.1:514

rsyslog
    └── listens on TCP :514 (imtcp module)
    └── writes to /var/log/haproxy/access.log

Remote syslog (optional)
    └── rsyslog can forward to remote:514 via TCP
```

---

## Step 1 — Prepare Directories

```bash
# Create log output directory
mkdir -p /var/log/haproxy
```

No chroot socket setup required for TCP — network stack is accessible from inside the jail.

---

## Step 2 — HAProxy Configuration

Edit `/etc/haproxy/haproxy.cfg`:

```haproxy
global
    maxconn         100000
    stats socket    /var/run/haproxy.stat mode 600 level admin
    log             tcp@127.0.0.1:514 local0
    log             tcp@127.0.0.1:514 local1 notice
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

The `tcp@` prefix is required — without it HAProxy defaults to UDP.

---

## Step 3 — rsyslog Configuration

Create `/etc/rsyslog.d/haproxy.conf`:

```bash
cat > /etc/rsyslog.d/haproxy.conf << 'EOF'
module(load="imtcp")
input(type="imtcp" port="514")

local0.*    /var/log/haproxy/access.log
local1.*    /var/log/haproxy/notice.log

& stop
EOF
```

`module(load="imtcp")` — loads TCP input module (not loaded by default).  
`input(type="imtcp" port="514")` — binds rsyslog to TCP port 514.  
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
# Confirm rsyslog is listening on TCP 514
ss -tlnp | grep 514

# Validate HAProxy config
haproxy -c -f /etc/haproxy/haproxy.cfg

# Test rsyslog receiving local0 via TCP
logger -p local0.info -T -n 127.0.0.1 -P 514 "haproxy tcp test"
tail -f /var/log/haproxy/access.log

# Check HAProxy log counter (must be > 0 after traffic)
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs
```

Expected output of `ss -tlnp | grep 514`:
```
LISTEN  0  128  0.0.0.0:514  0.0.0.0:*  users:(("rsyslogd",...))
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

## Optional — Forward to Remote Syslog Server

To relay HAProxy logs to a remote central syslog server, append to `/etc/rsyslog.d/haproxy.conf`:

```
local0.*    /var/log/haproxy/access.log
local0.*    @@remote-syslog.example.com:514    # @@ = TCP forwarding
local1.*    /var/log/haproxy/notice.log
```

Single `@` = UDP forward. Double `@@` = TCP forward.

---

## Pros & Cons

| | Detail |
|---|---|
| **Pro** — Reliable delivery | Connection-based; detects and retries on failure |
| **Pro** — Remote capable | Send to Graylog, ELK, Loki, Splunk, etc. |
| **Pro** — Chroot friendly | TCP network stack accessible from inside jail — no extra socket setup |
| **Con** — Connection dependency | If rsyslog restarts, logs lost until HAProxy reconnects |
| **Con** — Port binding required | rsyslog must listen on TCP 514; check firewall if remote |
| **Con** — Slightly more overhead | TCP handshake vs direct socket write |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `CumRecvLogs: 0` | rsyslog not on TCP 514 | Run `ss -tlnp \| grep 514` to confirm listener |
| Log file not created | imtcp module not loaded | Check rsyslog.conf syntax with `rsyslogd -N1` |
| Connection refused | Port 514 blocked | Check `firewalld` or `iptables` rules |
| Logs stop after rsyslog restart | TCP connection dropped | HAProxy will reconnect automatically on next log event |
| rsyslog not starting | imtcp config syntax error | Run `rsyslogd -N1 -f /etc/rsyslog.conf` |

---

*HAProxy 2.8.14 — Oracle Linux 9.7 — TCP via rsyslog*
