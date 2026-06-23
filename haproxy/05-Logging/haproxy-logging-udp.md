# HAProxy Logging — UDP

**Environment:** HAProxy 2.8.14 on Oracle Linux 9.7  
**Transport:** UDP (`127.0.0.1:514`)  
**Recommended for:** Remote central syslog where simplicity is preferred over delivery guarantee

---

## Overview

UDP is the traditional syslog transport and the default HAProxy logging method when no `tcp@` prefix is used. It is fire-and-forget — HAProxy sends log datagrams to rsyslog on UDP port 514 with no acknowledgment or retry. Simple to configure, low overhead, but messages can be silently dropped under high burst load.

When `chroot` is enabled, HAProxy sends outbound UDP datagrams to `127.0.0.1:514` via the network stack. Since UDP uses the network stack (not a socket file), chroot does **not** block UDP datagrams — no extra configuration needed inside the jail for transport.

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
# Create log output directory
mkdir -p /var/log/haproxy
```

No chroot socket setup required for UDP — network stack is accessible from inside the jail.

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
local1.*    /var/log/haproxy/notice.log

& stop
EOF
```

`module(load="imudp")` — loads UDP input module (not loaded by default on OL9).  
`input(type="imudp" port="514")` — binds rsyslog to UDP port 514.  
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
# Confirm rsyslog is listening on UDP 514
ss -ulnp | grep 514

# Validate HAProxy config
haproxy -c -f /etc/haproxy/haproxy.cfg

# Test rsyslog receiving local0 via UDP
logger -p local0.info -d -n 127.0.0.1 -P 514 "haproxy udp test"
tail -f /var/log/haproxy/access.log

# Check HAProxy log counter (must be > 0 after traffic)
echo "show info" | socat stdio /var/run/haproxy.stat | grep CumRecvLogs
```

Expected output of `ss -ulnp | grep 514`:
```
UNCONN  0  0  0.0.0.0:514  0.0.0.0:*  users:(("rsyslogd",...))
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
local0.*    @remote-syslog.example.com:514     # @ = UDP forwarding
local1.*    /var/log/haproxy/notice.log
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
| Logs are supplementary (not critical) | Yes |
| Remote syslog aggregation, simple setup | Yes |
| High burst traffic with zero log loss tolerance | No — use TCP or Unix socket instead |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `CumRecvLogs: 0` | rsyslog not on UDP 514 | Run `ss -ulnp \| grep 514` to confirm listener |
| Log file not created | imudp module not loaded | Check rsyslog.conf syntax with `rsyslogd -N1` |
| Logs missing under load | UDP buffer overflow | Increase rsyslog `imudp` buffer or switch to Unix socket/TCP |
| Connection refused | UDP 514 blocked by firewall | Check `firewalld` or `iptables` rules |
| rsyslog not starting | imudp config syntax error | Run `rsyslogd -N1 -f /etc/rsyslog.conf` |

---

*HAProxy 2.8.14 — Oracle Linux 9.7 — UDP via rsyslog*
