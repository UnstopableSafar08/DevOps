# HAProxy Installation Guide (Oracle Linux 9)

**Target OS:** Oracle Linux 9 (EL9)
**HAProxy Version:** 3.4.3 (latest stable LTS)
**Install Method:** Build from source
**LB Algorithm:** Round-robin

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Final Configuration File](#3-final-configuration-file)
4. [Final Systemd Service Unit](#4-final-systemd-service-unit)
5. [Resource Allocation Profiles](#5-resource-allocation-profiles)
6. [Linux Kernel & Limit Tuning](#6-linux-kernel--limit-tuning)
7. [Deploy and Verify](#7-deploy-and-verify)
8. [Why Each Setting Is There](#8-why-each-setting-is-there)
9. [Prometheus Metrics Exporter](#9-prometheus-metrics-exporter)
10. [Complete Uninstall Process](#10-complete-uninstall-process)

---

## 1. Prerequisites

```bash
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y gcc make wget tar \
    openssl-devel pcre2-devel systemd-devel zlib-devel
```

---

## 2. Installation

```bash
cd /usr/local/src
sudo wget https://www.haproxy.org/download/3.4/src/haproxy-3.4.3.tar.gz
sudo tar xzf haproxy-3.4.3.tar.gz
cd haproxy-3.4.3

sudo make -j$(nproc) TARGET=linux-glibc \
    USE_OPENSSL=1 \
    USE_PCRE2=1 \
    USE_PCRE2_JIT=1 \
    USE_ZLIB=1 \
    USE_SYSTEMD=1 \
    USE_PROMEX=1

sudo make install PREFIX=/usr/local
sudo ln -sf /usr/local/sbin/haproxy /usr/sbin/haproxy

haproxy -v
```

`USE_PROMEX=1` builds in the native Prometheus metrics exporter module. Confirm it's present in this build:
```bash
haproxy -vv | grep -i promex
```
Should show `+PROMEX`. If it shows `-PROMEX`, the module wasn't compiled in — see [Section 9](#9-prometheus-metrics-exporter) for how to add it without a full rebuild.

Create the service account and config directory:

```bash
sudo useradd -r -M -s /sbin/nologin haproxy 2>/dev/null || true
sudo mkdir -p /etc/haproxy
```

---

## 3. Final Configuration File

```bash
sudo tee /etc/haproxy/haproxy.cfg > /dev/null << 'EOF'
#---------------------------------------------------------------------
# HAProxy — round-robin load balancer
#---------------------------------------------------------------------
global
    default-path config
    log /dev/log local0 info
    maxconn 8000
    nbthread 2
    cpu-map auto:1/1-2 0-1
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    retries 3

frontend fe_main
    bind *:80
    default_backend be_app

backend be_app
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    default-server check inter 3s fall 3 rise 2 fastinter 1s maxconn 500
    server app1 <BACKEND_1_IP>:8080
    server app2 <BACKEND_2_IP>:8080
EOF
```

Replace `<BACKEND_1_IP>` / `<BACKEND_2_IP>` with real backend addresses, and confirm `/health` matches a real endpoint on your backend that returns HTTP 200.

`maxconn 8000`, `nbthread 2`, and `default-server maxconn 500` above match the **2 vCPU / 4GB** profile — see [Section 5](#5-resource-allocation-profiles) to swap in the 4 vCPU / 8GB values instead.

Validate:
```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
```

---

## 4. Final Systemd Service Unit

```bash
sudo tee /etc/systemd/system/haproxy.service > /dev/null << 'EOF'
[Unit]
Description=HAProxy Load Balancer
After=network.target syslog.service
Wants=syslog.service

[Service]
Type=notify
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
RuntimeDirectory=haproxy
RuntimeDirectoryMode=0755
WorkingDirectory=/etc/haproxy
LimitNOFILE=65536
ExecStartPre=/usr/sbin/haproxy -f /etc/haproxy/haproxy.cfg -c -q
ExecStart=/usr/sbin/haproxy -Ws -f /etc/haproxy/haproxy.cfg -p /run/haproxy/haproxy.pid
ExecReload=/bin/kill -USR2 $MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=2
User=haproxy
Group=haproxy

[Install]
WantedBy=multi-user.target
EOF
```

`LimitNOFILE=65536` above matches the 2 vCPU / 4GB profile — use `131072` for the 4 vCPU / 8GB profile.

---

## 5. Resource Allocation Profiles

### Profile A — 2 vCPU / 4 GB RAM

| Setting | Value |
|---|---|
| `nbthread` | `2` |
| `cpu-map` | `auto:1/1-2 0-1` |
| `global maxconn` | `8000` |
| `default-server maxconn` | `500` |
| `LimitNOFILE` (systemd) | `65536` |
| `net.core.somaxconn` | `8192` |
| `net.ipv4.tcp_max_syn_backlog` | `8192` |

Estimated HAProxy footprint: ~100–300MB RAM under sustained load.

### Profile B — 4 vCPU / 8 GB RAM

| Setting | Value |
|---|---|
| `nbthread` | `4` |
| `cpu-map` | `auto:1/1-4 0-3` |
| `global maxconn` | `16000` |
| `default-server maxconn` | `1000` |
| `LimitNOFILE` (systemd) | `131072` |
| `net.core.somaxconn` | `16384` |
| `net.ipv4.tcp_max_syn_backlog` | `16384` |

Estimated HAProxy footprint: ~300–600MB RAM under sustained heavy load.

To apply Profile B, update `haproxy.cfg`:
```haproxy
global
    ...
    maxconn 16000
    nbthread 4
    cpu-map auto:1/1-4 0-3
```
```haproxy
backend be_app
    ...
    default-server check inter 3s fall 3 rise 2 fastinter 1s maxconn 1000
```

And the systemd unit:
```ini
[Service]
LimitNOFILE=131072
```

> Match `nbthread` exactly to core count on either profile — more threads than cores adds context-switch overhead with no throughput gain.

---

## 6. Linux Kernel & Limit Tuning

Values below match **Profile A (2 vCPU/4GB)** — swap the two `somaxconn`/`backlog` lines for Profile B values if using the 4 vCPU/8GB tier.

```bash
sudo tee /etc/sysctl.d/99-haproxy.conf > /dev/null << 'EOF'
# Max total open file handles system-wide
fs.file-max = 200000

# Expanded ephemeral port range for outbound connections to backends
net.ipv4.ip_local_port_range = 1024 65535

# Reuse TIME_WAIT sockets faster under high connection churn
net.ipv4.tcp_tw_reuse = 1

# Backlog queue sizing — Profile A values (2 vCPU/4GB)
net.core.somaxconn = 8192
net.ipv4.tcp_max_syn_backlog = 8192

# TCP keepalive — detect dead backend connections faster
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 5
EOF

sudo sysctl --system
```

PAM limits (backstop for interactive/manual shell testing only — has no effect on the systemd-managed daemon itself, which is governed by `LimitNOFILE=` in the unit file):

```bash
sudo tee /etc/security/limits.d/haproxy.conf > /dev/null << 'EOF'
haproxy soft nofile 65536
haproxy hard nofile 65536
root    soft nofile 65536
root    hard nofile 65536
EOF
```

---

## 7. Deploy and Verify

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now haproxy
sudo systemctl status haproxy --no-pager
sudo ss -tlnp | grep haproxy
```

Expected:
```
● haproxy.service - HAProxy Load Balancer
     Active: active (running)
     Status: "Ready."
```
```
LISTEN 0 8000 0.0.0.0:80 0.0.0.0:* users:(("haproxy",pid=XXXX,fd=X))
```

Confirm the file descriptor limit landed on the running process:
```bash
sudo cat /proc/$(pgrep -o haproxy)/limits | grep "open files"
```

---

## 8. Why Each Setting Is There

Every non-obvious line in the final config and unit file above exists to resolve a specific real startup failure. Kept brief — for the full failure logs and diagnosis steps, ask for the troubleshooting appendix separately.

| Setting | Fixes |
|---|---|
| `default-path config` (haproxy.cfg, `global`) | Prevents a startup failure where HAProxy tries to `chdir` back to the directory it was launched from (often `/root`), which the unprivileged `haproxy` user cannot access. |
| `WorkingDirectory=/etc/haproxy` (systemd) | Second layer of defense for the same issue — pins the process's working directory explicitly rather than relying on the launching shell's `$PWD`. |
| `AmbientCapabilities=CAP_NET_BIND_SERVICE` + `CapabilityBoundingSet=CAP_NET_BIND_SERVICE` (systemd) | Without this, binding to port 80 (a privileged port) as the unprivileged `haproxy` user fails with `Permission denied`. |
| `RuntimeDirectory=haproxy` + pidfile path `/run/haproxy/haproxy.pid` | `/run/` itself is root-owned and not writable by the `haproxy` user, causing a `Cannot create pidfile` failure. `RuntimeDirectory=` auto-creates `/run/haproxy` on every boot, owned by the service user. |
| `LimitNOFILE=65536` (systemd) | Must be set here, not in `limits.conf` — PAM-based limits don't apply to systemd-managed daemons. |
| `user haproxy` / `group haproxy` (haproxy.cfg, `global`) | Both must be set together — using only `group` without `user` triggers a (harmless but avoidable) warning at startup. |

---

## 9. Complete Uninstall Process

```bash
# Stop and disable the service
sudo systemctl stop haproxy
sudo systemctl disable haproxy
sudo systemctl reset-failed haproxy

# Remove systemd unit
sudo rm -f /etc/systemd/system/haproxy.service
sudo rm -rf /etc/systemd/system/haproxy.service.d
sudo systemctl daemon-reload
sudo systemctl reset-failed

# Remove binaries
sudo rm -f /usr/sbin/haproxy
sudo rm -f /usr/local/sbin/haproxy

# Remove config and runtime files
sudo rm -rf /etc/haproxy
sudo rm -rf /run/haproxy

# Remove source/build directory
sudo rm -rf /usr/local/src/haproxy-3.4.3
sudo rm -f /usr/local/src/haproxy-3.4.3.tar.gz

# Remove service account
sudo userdel haproxy

# Remove limits and sysctl tuning
sudo rm -f /etc/security/limits.d/haproxy.conf
sudo rm -f /etc/sysctl.d/99-haproxy.conf
sudo sysctl --system

# Remove logging config, if any was added
sudo rm -f /etc/rsyslog.d/haproxy.conf
sudo rm -f /etc/logrotate.d/haproxy
sudo systemctl restart rsyslog
```

Final verification:
```bash
# Confirm no process is running
pgrep -a haproxy
# should return nothing

# Confirm no port 80 listener remains
sudo ss -tlnp | grep :80

# Confirm no leftover files anywhere on the filesystem
sudo find / -iname "*haproxy*" -not -path "*/proc/*" 2>/dev/null
```

Review the last command's output — it surfaces anything not covered above (custom scripts, cron jobs, or monitoring configs referencing HAProxy).

If SELinux was changed from `enforcing` at any point during setup, restore it now:
```bash
sudo sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config
sudo reboot
```
