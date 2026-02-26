# Production System Configuration Guide
## EL9 · Nginx + PHP-FPM (7.2 / 8.1 / 8.2 / 8.3)

> **Target OS:** RHEL 9 / AlmaLinux 9 / Rocky Linux 9 (EL9)  
> **Stack:** Nginx → PHP-FPM (multi-version, Unix socket)  
> **Scope:** OS-level tuning — kernel, limits, sysctl, systemd, Nginx, PHP-FPM

---

## Table of Contents

1. [System Limits — `/etc/security/limits.conf`](#1-system-limits)
2. [PAM Limits — ensure limits apply](#2-pam-limits)
3. [Systemd Unit Overrides — Nginx & PHP-FPM](#3-systemd-unit-overrides)
4. [Kernel Parameters — `/etc/sysctl.d/99-production.conf`](#4-kernel-parameters)
5. [File Descriptor Limits — system-wide](#5-file-descriptor-limits)
6. [CPU Scheduler & IRQ Affinity](#6-cpu-scheduler--irq-affinity)
7. [Transparent Huge Pages & Memory](#7-transparent-huge-pages--memory)
8. [Nginx — Production Configuration](#8-nginx-production-configuration)
9. [PHP-FPM Pool Configs per Version](#9-php-fpm-pool-configs-per-version)
10. [OPcache Tuning per Version](#10-opcache-tuning-per-version)
11. [Logrotate for Nginx & PHP-FPM](#11-logrotate)
12. [SELinux — Allow Nginx + FPM Sockets](#12-selinux)
13. [systemd tmpfiles — Ensure socket dirs](#13-systemd-tmpfiles)
14. [Verification & Health Checks](#14-verification--health-checks)

---

## 1. System Limits

**`/etc/security/limits.conf`** — or drop in `/etc/security/limits.d/99-production.conf`

```ini
# /etc/security/limits.d/99-production.conf
# ============================================================
# Production limits for Nginx + PHP-FPM on EL9
# ============================================================

# --- Nginx worker process ---
nginx           soft    nofile          65535
nginx           hard    nofile          65535
nginx           soft    nproc           65535
nginx           hard    nproc           65535
nginx           soft    core            unlimited
nginx           hard    core            unlimited

# --- PHP-FPM workers (each version runs as dedicated user) ---
# Applies to: php-fpm, www-data, or whatever user FPM pools run as
# Remi default: the pool user defined in www.conf (commonly nginx or php-fpm)

php-fpm         soft    nofile          65535
php-fpm         hard    nofile          65535
php-fpm         soft    nproc           65535
php-fpm         hard    nproc           65535
php-fpm         soft    core            unlimited
php-fpm         hard    core            unlimited

# If FPM pool runs as 'nginx' user (common when Nginx serves static files too)
# The nginx entries above already cover this — no duplication needed.

# --- General system / root ---
root            soft    nofile          unlimited
root            hard    nofile          unlimited
root            soft    nproc           unlimited
root            hard    nproc           unlimited

# --- All other users ---
*               soft    nofile          65535
*               hard    nofile          65535
*               soft    nproc           65535
*               hard    nproc           65535
*               soft    stack           8192
*               hard    stack           unlimited
*               soft    memlock         unlimited
*               hard    memlock         unlimited
```

> **Apply without reboot:**
> ```bash
> sysctl -p
> # For limit changes on running services — restart via systemd (see §3)
> ```

---

## 2. PAM Limits

Ensure PAM loads the limits for login sessions AND system services.

```bash
# Verify these lines exist in /etc/pam.d/system-auth and /etc/pam.d/password-auth
grep 'pam_limits' /etc/pam.d/system-auth
grep 'pam_limits' /etc/pam.d/password-auth
```

They should contain:
```
session     required      pam_limits.so
```

If missing:
```bash
echo "session     required      pam_limits.so" >> /etc/pam.d/system-auth
echo "session     required      pam_limits.so" >> /etc/pam.d/password-auth
```

Also ensure `/etc/security/limits.d/` overrides are loaded:
```bash
# /etc/pam.d/common-session (if present on your distro)
grep 'pam_limits' /etc/pam.d/common-session || \
  echo "session required pam_limits.so" >> /etc/pam.d/common-session
```

---

## 3. Systemd Unit Overrides

PAM limits do **not** apply to systemd services by default. You must set limits in the unit drop-in. This is the **authoritative** method for services managed by systemd.

### 3a. Nginx

```bash
sudo mkdir -p /etc/systemd/system/nginx.service.d/
sudo tee /etc/systemd/system/nginx.service.d/override.conf > /dev/null <<'EOF'
[Service]
# File descriptors
LimitNOFILE=65535
LimitNPROC=65535

# Disable core dumps in production (set to infinity for debugging)
LimitCORE=0

# Memory lock (needed if using huge pages or pinned memory)
LimitMEMLOCK=infinity

# Restart policy
Restart=on-failure
RestartSec=3s
StartLimitIntervalSec=60
StartLimitBurst=5

# Process/security hardening
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true

# IO scheduling — best-effort, high priority
IOSchedulingClass=best-effort
IOSchedulingPriority=0

# CPU scheduling
CPUSchedulingPolicy=other
CPUSchedulingPriority=0

# Nice value — Nginx gets priority
Nice=-5
EOF
```

### 3b. PHP-FPM (repeat for 72, 81, 82, 83)

```bash
for VER in 72 81 82 83; do
  SERVICE="php${VER}-php-fpm"
  DIR="/etc/systemd/system/${SERVICE}.service.d"
  sudo mkdir -p "$DIR"
  sudo tee "${DIR}/override.conf" > /dev/null <<EOF
[Service]
# File descriptors — must match or exceed pm.max_children * 10
LimitNOFILE=65535
LimitNPROC=65535

# No core dumps in production
LimitCORE=0

# Memory lock
LimitMEMLOCK=infinity

# Restart policy
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=120
StartLimitBurst=5

# Security
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true

# Runtime directory for Unix sockets
RuntimeDirectory=php${VER}-fpm
RuntimeDirectoryMode=0750

# IO
IOSchedulingClass=best-effort
IOSchedulingPriority=0
EOF
  echo "Written: ${DIR}/override.conf"
done
```

```bash
# Reload systemd and restart all
sudo systemctl daemon-reload
sudo systemctl restart nginx
for VER in 72 81 82 83; do
  sudo systemctl restart php${VER}-php-fpm
done
```

### Verify limits applied to running processes

```bash
# Get Nginx worker PID
NGINX_PID=$(pgrep -o nginx)
cat /proc/${NGINX_PID}/limits

# Get PHP-FPM worker PID
FPM_PID=$(pgrep -o php-fpm)
cat /proc/${FPM_PID}/limits
```

---

## 4. Kernel Parameters

**`/etc/sysctl.d/99-production.conf`**

```bash
sudo tee /etc/sysctl.d/99-production.conf > /dev/null <<'EOF'
# ============================================================
# Production Kernel Parameters — EL9 Nginx + PHP-FPM
# ============================================================

# -------- FILE SYSTEM ----------------------------------------
# Maximum number of open file descriptors system-wide
fs.file-max = 2097152

# Maximum number of inotify watches per user (for log watchers, etc.)
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
fs.inotify.max_queued_events = 32768

# Allow a large number of memory-mapped files (needed by JVM, Redis, etc.)
vm.max_map_count = 262144

# -------- NETWORK — CORE -------------------------------------
# Increase socket receive/send buffer maximums
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 31457280
net.core.wmem_default = 31457280

# Backlog queue — Nginx: worker_connections * # of workers
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535

# Busy poll (reduces latency on high-throughput systems)
net.core.busy_poll = 50
net.core.busy_read = 50

# -------- NETWORK — TCP --------------------------------------
# TCP read/write buffer sizes [min, default, max]
net.ipv4.tcp_rmem = 4096 131072 134217728
net.ipv4.tcp_wmem = 4096 16384  134217728

# Enable window scaling
net.ipv4.tcp_window_scaling = 1

# Reuse TIME_WAIT sockets — important for high-connection-rate HTTP
net.ipv4.tcp_tw_reuse = 1

# SYN backlog — protect against SYN flood
net.ipv4.tcp_max_syn_backlog = 65535

# Keep fewer FIN_WAIT2 sockets
net.ipv4.tcp_fin_timeout = 15

# TCP keepalive — detect dead connections faster
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 10

# Maximum number of TIME_WAIT sockets
net.ipv4.tcp_max_tw_buckets = 2000000

# Enable TCP Fast Open (TFO) — reduces latency by 1 RTT on reconnects
net.ipv4.tcp_fastopen = 3

# Increase local port range for outgoing connections
net.ipv4.ip_local_port_range = 1024 65535

# Congestion control — BBR if available (best for modern networks)
net.ipv4.tcp_congestion_control = bbr

# Enable TCP selective acknowledgements
net.ipv4.tcp_sack = 1

# Disable slow start after idle
net.ipv4.tcp_slow_start_after_idle = 0

# Reduce TCP retransmission (fail faster on dead connections)
net.ipv4.tcp_retries2 = 8

# -------- UNIX DOMAIN SOCKETS (Nginx ↔ PHP-FPM) -------------
# Buffer sizes for Unix sockets — critical for FPM performance
net.unix.max_dgram_qlen = 512

# -------- VIRTUAL MEMORY -------------------------------------
# Prefer swap less aggressively (keep app data in RAM)
vm.swappiness = 10

# Dirty page write-back tuning
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.dirty_expire_centisecs = 3000
vm.dirty_writeback_centisecs = 500

# Disable overcommit accounting — prevent OOM surprises
# 0 = heuristic, 1 = always allow, 2 = never overcommit beyond swap+RAM
vm.overcommit_memory = 0
vm.overcommit_ratio = 50

# -------- SECURITY -------------------------------------------
# Protect against ICMP-based attacks
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Disable IP source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Enable reverse path filtering
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# SYN cookie protection
net.ipv4.tcp_syncookies = 1

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
EOF

# Apply immediately
sudo sysctl -p /etc/sysctl.d/99-production.conf
```

### Enable TCP BBR (if not already loaded)

```bash
# Load BBR module
sudo modprobe tcp_bbr
echo 'tcp_bbr' | sudo tee /etc/modules-load.d/tcp_bbr.conf

# Verify
sysctl net.ipv4.tcp_congestion_control
# Expected: net.ipv4.tcp_congestion_control = bbr
```

---

## 5. File Descriptor Limits — System-Wide

```bash
# /etc/systemd/system.conf — global systemd limits
sudo sed -i 's/^#DefaultLimitNOFILE=.*/DefaultLimitNOFILE=65535/' /etc/systemd/system.conf
sudo sed -i 's/^#DefaultLimitNPROC=.*/DefaultLimitNPROC=65535/'   /etc/systemd/system.conf
sudo sed -i 's/^#DefaultLimitCORE=.*/DefaultLimitCORE=0/'          /etc/systemd/system.conf

# /etc/systemd/user.conf — for user-level services
sudo sed -i 's/^#DefaultLimitNOFILE=.*/DefaultLimitNOFILE=65535/' /etc/systemd/user.conf

# Verify the hard OS limit allows this
sudo cat /proc/sys/fs/file-max
# Should be >= 2097152 (set by sysctl above)

# Check current open files across all processes
sudo lsof | wc -l

# Show system-wide fd usage
cat /proc/sys/fs/file-nr
# Output: [allocated]  [freed]  [max]
```

---

## 6. CPU Scheduler & IRQ Affinity

```bash
# Check CPU count
nproc --all

# Set CPU governor to performance mode (disable power-saving frequency scaling)
sudo dnf install -y kernel-tools
sudo cpupower frequency-set -g performance

# Persist across reboots
sudo tee /etc/systemd/system/cpupower.service > /dev/null <<'EOF'
[Unit]
Description=Set CPU governor to performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/cpupower frequency-set -g performance
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now cpupower.service

# IRQ balance — distribute interrupts evenly across CPUs
sudo dnf install -y irqbalance
sudo systemctl enable --now irqbalance
```

---

## 7. Transparent Huge Pages & Memory

```bash
# Disable Transparent Huge Pages — reduces latency jitter for PHP/web workloads
sudo tee /etc/systemd/system/disable-thp.service > /dev/null <<'EOF'
[Unit]
Description=Disable Transparent Huge Pages
DefaultDependencies=false
After=sysinit.target local-fs.target
Before=basic.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/defrag'
RemainAfterExit=yes

[Install]
WantedBy=basic.target
EOF
sudo systemctl enable --now disable-thp.service

# Verify
cat /sys/kernel/mm/transparent_hugepage/enabled
# Should show: always madvise [never]

# Set up NUMA interleaving if server is multi-socket
# sudo dnf install -y numactl
# sudo numactl --interleave=all <process>  — set in FPM unit ExecStart if needed
```

---

## 8. Nginx Production Configuration

### `/etc/nginx/nginx.conf`

```nginx
# /etc/nginx/nginx.conf
# Production configuration for PHP-FPM backend

user  nginx;

# Set to number of CPU cores (or 'auto')
worker_processes  auto;

# Maximum open file descriptors per worker — must match LimitNOFILE
worker_rlimit_nofile  65535;

# Error log — warn level in production (use 'info' for debugging)
error_log  /var/log/nginx/error.log warn;
pid        /run/nginx.pid;

# Load dynamic modules
include /usr/share/nginx/modules/*.conf;

events {
    # Max simultaneous connections per worker
    # Total = worker_processes * worker_connections
    worker_connections  10240;

    # Accept multiple connections per epoll event
    multi_accept  on;

    # Use epoll on Linux (most efficient)
    use  epoll;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # ---- Logging ----
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for" '
                      'rt=$request_time uct=$upstream_connect_time '
                      'uht=$upstream_header_time urt=$upstream_response_time';

    access_log  /var/log/nginx/access.log  main buffer=64k flush=5s;

    # ---- Performance ----
    sendfile            on;
    tcp_nopush          on;     # Batch response headers + body
    tcp_nodelay         on;     # Flush small packets immediately
    keepalive_timeout   65;
    keepalive_requests  10000;  # Requests per keep-alive connection

    # File handle caching — avoid repeated open()/stat() syscalls
    open_file_cache            max=50000 inactive=60s;
    open_file_cache_valid      80s;
    open_file_cache_min_uses   2;
    open_file_cache_errors     on;

    # ---- Buffers ----
    client_body_buffer_size       16k;
    client_header_buffer_size     1k;
    client_max_body_size          64m;
    large_client_header_buffers   4 8k;

    # ---- Timeouts ----
    client_body_timeout     12s;
    client_header_timeout   12s;
    send_timeout            10s;
    reset_timedout_connection on;

    # ---- Gzip ----
    gzip               on;
    gzip_vary          on;
    gzip_proxied       any;
    gzip_comp_level    4;         # 1-9; 4-6 is sweet spot
    gzip_buffers       16 8k;
    gzip_http_version  1.1;
    gzip_min_length    1024;      # Don't compress tiny responses
    gzip_types
        text/plain text/css text/xml text/javascript
        application/json application/javascript application/xml
        application/rss+xml application/atom+xml
        image/svg+xml font/truetype font/opentype
        application/vnd.ms-fontobject;

    # ---- Security headers (global) ----
    server_tokens  off;          # Hide Nginx version
    more_clear_headers Server;   # Requires ngx_headers_more module

    # ---- Rate limiting zones ----
    limit_req_zone  $binary_remote_addr  zone=req_limit:10m  rate=100r/s;
    limit_conn_zone $binary_remote_addr  zone=conn_limit:10m;

    # ---- Upstream PHP-FPM pools (one per PHP version) ----
    upstream php72_fpm {
        server  unix:/run/php72-fpm/www.sock;
        keepalive 32;
    }
    upstream php81_fpm {
        server  unix:/run/php81-fpm/www.sock;
        keepalive 32;
    }
    upstream php82_fpm {
        server  unix:/run/php82-fpm/www.sock;
        keepalive 32;
    }
    upstream php83_fpm {
        server  unix:/run/php83-fpm/www.sock;
        keepalive 32;
    }

    # ---- Include virtual hosts ----
    include /etc/nginx/conf.d/*.conf;
}
```

### `/etc/nginx/conf.d/app-php83.conf` — Example vhost

```nginx
# /etc/nginx/conf.d/app-php83.conf
# Example: PHP 8.3 application

server {
    listen       80;
    listen       [::]:80;
    server_name  example.com www.example.com;

    # Redirect HTTP → HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen       443 ssl http2;
    listen       [::]:443 ssl http2;
    server_name  example.com www.example.com;

    root   /var/www/example.com/public;
    index  index.php index.html;

    # ---- SSL ----
    ssl_certificate      /etc/ssl/certs/example.com.crt;
    ssl_certificate_key  /etc/ssl/private/example.com.key;
    ssl_session_timeout  1d;
    ssl_session_cache    shared:SSL:50m;
    ssl_session_tickets  off;
    ssl_protocols        TLSv1.2 TLSv1.3;
    ssl_ciphers          ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # ---- Security headers ----
    add_header X-Frame-Options           "SAMEORIGIN"  always;
    add_header X-Content-Type-Options    "nosniff"     always;
    add_header X-XSS-Protection          "1; mode=block" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy        "geolocation=(), microphone=(), camera=()" always;

    # ---- Rate limiting ----
    limit_req   zone=req_limit  burst=200  nodelay;
    limit_conn  conn_limit      100;

    # ---- Logging ----
    access_log  /var/log/nginx/example.com-access.log  main;
    error_log   /var/log/nginx/example.com-error.log   warn;

    # ---- Static files ----
    location ~* \.(jpg|jpeg|gif|png|ico|css|js|woff2|woff|ttf|svg|eot|webp|avif)$ {
        expires     30d;
        add_header  Cache-Control "public, immutable";
        access_log  off;
        log_not_found off;
        try_files   $uri =404;
    }

    # ---- PHP handling ----
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        # Prevent executing uploaded PHP
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;

        # Route to PHP 8.3 FPM upstream
        fastcgi_pass   php83_fpm;
        fastcgi_index  index.php;

        include fastcgi_params;
        fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
        fastcgi_param  PATH_INFO        $fastcgi_path_info;
        fastcgi_param  SERVER_NAME      $host;

        # ---- FastCGI buffer tuning ----
        fastcgi_buffers          16 16k;
        fastcgi_buffer_size      32k;
        fastcgi_busy_buffers_size 32k;
        fastcgi_temp_file_write_size 256k;

        # ---- FastCGI timeouts ----
        fastcgi_connect_timeout  5s;
        fastcgi_send_timeout     60s;
        fastcgi_read_timeout     60s;

        # ---- Keep-alive to FPM ----
        fastcgi_keep_conn on;

        # ---- Cache FastCGI responses (optional) ----
        # fastcgi_cache_bypass $http_pragma;
        # fastcgi_cache FASTCGI_CACHE;
        # fastcgi_cache_valid 200 1m;
    }

    # ---- Block sensitive files ----
    location ~ /\.(ht|git|env|svn) { deny all; }
    location ~ /\.user\.ini               { deny all; }
    location ~* wp-config\.php            { deny all; }
}
```

---

## 9. PHP-FPM Pool Configs per Version

Place each file at `/etc/opt/remi/php{ver}/php-fpm.d/www.conf`.

> **Sizing formula:**
> - `pm.max_children` = Available RAM for FPM ÷ Average worker memory  
>   Example: 4 GB ÷ 50 MB/worker = ~80 children
> - `pm.start_servers` = 25% of max_children
> - `pm.min_spare_servers` = 10% of max_children
> - `pm.max_spare_servers` = 30–40% of max_children

### PHP 7.2 Pool — `/etc/opt/remi/php72/php-fpm.d/www.conf`

```ini
[www]
; Run as nginx user so it can read web root files
user  = nginx
group = nginx

; Unix socket — faster than TCP for local Nginx↔FPM
listen = /run/php72-fpm/www.sock
listen.owner = nginx
listen.group = nginx
listen.mode  = 0660
listen.backlog = 65535

; Process manager: dynamic = adjust workers based on load
pm = dynamic
pm.max_children      = 80
pm.start_servers     = 20
pm.min_spare_servers = 10
pm.max_spare_servers = 30

; Recycle workers to prevent memory leaks (PHP 7.x especially)
pm.max_requests = 1000

; Status and ping endpoints for monitoring
pm.status_path  = /fpm-status
ping.path       = /fpm-ping
ping.response   = pong

; Timeouts
request_terminate_timeout = 60s
request_slowlog_timeout   = 5s
slowlog = /var/log/php72-fpm-slow.log

; Environment variables passed to PHP workers
env[HOSTNAME]     = $HOSTNAME
env[PATH]         = /usr/local/bin:/usr/bin:/bin
env[TMP]          = /tmp
env[TMPDIR]       = /tmp
env[TEMP]         = /tmp

; PHP overrides for this pool
php_admin_value[error_log]           = /var/log/php72-fpm-error.log
php_admin_flag[log_errors]           = on
php_admin_value[memory_limit]        = 256M
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size]       = 64M
php_admin_value[max_execution_time]  = 60
php_admin_value[max_input_time]      = 60
php_admin_value[open_basedir]        = /var/www:/tmp:/usr/share/php
php_admin_flag[expose_php]           = off
php_admin_flag[display_errors]       = off
php_flag[display_errors]             = off

; Catch workers output in error log
catch_workers_output = yes
decorate_workers_output = no

; Security: clear environment to avoid leaking host vars
clear_env = yes
```

### PHP 8.1 Pool — `/etc/opt/remi/php81/php-fpm.d/www.conf`

```ini
[www]
user  = nginx
group = nginx

listen = /run/php81-fpm/www.sock
listen.owner = nginx
listen.group = nginx
listen.mode  = 0660
listen.backlog = 65535

pm = dynamic
pm.max_children      = 80
pm.start_servers     = 20
pm.min_spare_servers = 10
pm.max_spare_servers = 30
pm.max_requests      = 2000

pm.status_path  = /fpm-status
ping.path       = /fpm-ping
ping.response   = pong

request_terminate_timeout = 60s
request_slowlog_timeout   = 5s
slowlog = /var/log/php81-fpm-slow.log

env[HOSTNAME] = $HOSTNAME
env[PATH]     = /usr/local/bin:/usr/bin:/bin
env[TMP]      = /tmp
env[TMPDIR]   = /tmp
env[TEMP]     = /tmp

php_admin_value[error_log]           = /var/log/php81-fpm-error.log
php_admin_flag[log_errors]           = on
php_admin_value[memory_limit]        = 256M
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size]       = 64M
php_admin_value[max_execution_time]  = 60
php_admin_value[max_input_time]      = 60
php_admin_value[open_basedir]        = /var/www:/tmp:/usr/share/php
php_admin_flag[expose_php]           = off
php_admin_flag[display_errors]       = off
php_flag[display_errors]             = off

catch_workers_output    = yes
decorate_workers_output = no
clear_env               = yes
```

### PHP 8.2 Pool — `/etc/opt/remi/php82/php-fpm.d/www.conf`

```ini
[www]
user  = nginx
group = nginx

listen = /run/php82-fpm/www.sock
listen.owner = nginx
listen.group = nginx
listen.mode  = 0660
listen.backlog = 65535

pm = dynamic
pm.max_children      = 80
pm.start_servers     = 20
pm.min_spare_servers = 10
pm.max_spare_servers = 30
pm.max_requests      = 2000

pm.status_path  = /fpm-status
ping.path       = /fpm-ping
ping.response   = pong

request_terminate_timeout = 60s
request_slowlog_timeout   = 5s
slowlog = /var/log/php82-fpm-slow.log

env[HOSTNAME] = $HOSTNAME
env[PATH]     = /usr/local/bin:/usr/bin:/bin
env[TMP]      = /tmp
env[TMPDIR]   = /tmp
env[TEMP]     = /tmp

php_admin_value[error_log]           = /var/log/php82-fpm-error.log
php_admin_flag[log_errors]           = on
php_admin_value[memory_limit]        = 256M
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size]       = 64M
php_admin_value[max_execution_time]  = 60
php_admin_value[max_input_time]      = 60
php_admin_value[open_basedir]        = /var/www:/tmp:/usr/share/php
php_admin_flag[expose_php]           = off
php_admin_flag[display_errors]       = off
php_flag[display_errors]             = off

catch_workers_output    = yes
decorate_workers_output = no
clear_env               = yes
```

### PHP 8.3 Pool — `/etc/opt/remi/php83/php-fpm.d/www.conf`

```ini
[www]
user  = nginx
group = nginx

listen = /run/php83-fpm/www.sock
listen.owner = nginx
listen.group = nginx
listen.mode  = 0660
listen.backlog = 65535

pm = dynamic
pm.max_children      = 80
pm.start_servers     = 20
pm.min_spare_servers = 10
pm.max_spare_servers = 30
pm.max_requests      = 2000

pm.status_path  = /fpm-status
ping.path       = /fpm-ping
ping.response   = pong

request_terminate_timeout = 60s
request_slowlog_timeout   = 5s
slowlog = /var/log/php83-fpm-slow.log

env[HOSTNAME] = $HOSTNAME
env[PATH]     = /usr/local/bin:/usr/bin:/bin
env[TMP]      = /tmp
env[TMPDIR]   = /tmp
env[TEMP]     = /tmp

php_admin_value[error_log]           = /var/log/php83-fpm-error.log
php_admin_flag[log_errors]           = on
php_admin_value[memory_limit]        = 256M
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size]       = 64M
php_admin_value[max_execution_time]  = 60
php_admin_value[max_input_time]      = 60
php_admin_value[open_basedir]        = /var/www:/tmp:/usr/share/php
php_admin_flag[expose_php]           = off
php_admin_flag[display_errors]       = off
php_flag[display_errors]             = off

catch_workers_output    = yes
decorate_workers_output = no
clear_env               = yes
```

---

## 10. OPcache Tuning per Version

Drop in `/etc/opt/remi/php{ver}/php.d/10-opcache.ini`

> OPcache settings vary slightly by PHP version — PHP 8.x supports `opcache.jit`.

### PHP 7.2 — `/etc/opt/remi/php72/php.d/10-opcache.ini`

```ini
; OPcache — PHP 7.2 Production
zend_extension = opcache.so

opcache.enable            = 1
opcache.enable_cli        = 0       ; Disable on CLI (unnecessary)
opcache.memory_consumption = 256    ; MB — increase for large codebases
opcache.interned_strings_buffer = 32; MB — pool for interned strings
opcache.max_accelerated_files = 30000 ; # of PHP files to cache
opcache.max_wasted_percentage = 5
opcache.revalidate_freq   = 60      ; Seconds between mtime checks (0=never)
opcache.validate_timestamps = 0     ; DISABLE in production for max speed
                                    ; Set to 1 during deploy, then back to 0
opcache.save_comments     = 1       ; Required by Doctrine, Laravel, etc.
opcache.fast_shutdown     = 1
opcache.file_cache        = /tmp/opcache-php72   ; Secondary file cache
opcache.file_cache_only   = 0
```

```bash
sudo mkdir -p /tmp/opcache-php72
sudo chown nginx:nginx /tmp/opcache-php72
```

### PHP 8.1 — `/etc/opt/remi/php81/php.d/10-opcache.ini`

```ini
; OPcache — PHP 8.1 Production (with JIT)
zend_extension = opcache.so

opcache.enable            = 1
opcache.enable_cli        = 0
opcache.memory_consumption = 256
opcache.interned_strings_buffer = 32
opcache.max_accelerated_files = 30000
opcache.max_wasted_percentage = 5
opcache.revalidate_freq   = 60
opcache.validate_timestamps = 0
opcache.save_comments     = 1
opcache.fast_shutdown     = 1
opcache.file_cache        = /tmp/opcache-php81
opcache.file_cache_only   = 0

; JIT — PHP 8.0+ (set to 0 to disable)
; tracing = best for long-running scripts/workers
; function = best for typical web requests
opcache.jit               = tracing
opcache.jit_buffer_size   = 128M
```

```bash
sudo mkdir -p /tmp/opcache-php81
sudo chown nginx:nginx /tmp/opcache-php81
```

### PHP 8.2 — `/etc/opt/remi/php82/php.d/10-opcache.ini`

```ini
; OPcache — PHP 8.2 Production (with JIT)
zend_extension = opcache.so

opcache.enable            = 1
opcache.enable_cli        = 0
opcache.memory_consumption = 256
opcache.interned_strings_buffer = 32
opcache.max_accelerated_files = 30000
opcache.max_wasted_percentage = 5
opcache.revalidate_freq   = 60
opcache.validate_timestamps = 0
opcache.save_comments     = 1
opcache.fast_shutdown     = 1
opcache.file_cache        = /tmp/opcache-php82
opcache.file_cache_only   = 0

opcache.jit               = tracing
opcache.jit_buffer_size   = 128M
```

```bash
sudo mkdir -p /tmp/opcache-php82
sudo chown nginx:nginx /tmp/opcache-php82
```

### PHP 8.3 — `/etc/opt/remi/php83/php.d/10-opcache.ini`

```ini
; OPcache — PHP 8.3 Production (with JIT)
zend_extension = opcache.so

opcache.enable            = 1
opcache.enable_cli        = 0
opcache.memory_consumption = 256
opcache.interned_strings_buffer = 32
opcache.max_accelerated_files = 30000
opcache.max_wasted_percentage = 5
opcache.revalidate_freq   = 60
opcache.validate_timestamps = 0
opcache.save_comments     = 1
opcache.fast_shutdown     = 1
opcache.file_cache        = /tmp/opcache-php83
opcache.file_cache_only   = 0

opcache.jit               = tracing
opcache.jit_buffer_size   = 128M
```

```bash
sudo mkdir -p /tmp/opcache-php83
sudo chown nginx:nginx /tmp/opcache-php83
```

---

## 11. Logrotate

### Nginx — `/etc/logrotate.d/nginx`

```
/var/log/nginx/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    postrotate
        /bin/kill -USR1 $(cat /run/nginx.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
```

### PHP-FPM — `/etc/logrotate.d/php-fpm-all`

```
/var/log/php72-fpm*.log
/var/log/php81-fpm*.log
/var/log/php82-fpm*.log
/var/log/php83-fpm*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    postrotate
        /bin/kill -USR1 $(cat /run/php72-fpm.pid 2>/dev/null) 2>/dev/null || true
        /bin/kill -USR1 $(cat /run/php81-fpm.pid 2>/dev/null) 2>/dev/null || true
        /bin/kill -USR1 $(cat /run/php82-fpm.pid 2>/dev/null) 2>/dev/null || true
        /bin/kill -USR1 $(cat /run/php83-fpm.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
```

---

## 12. SELinux

EL9 runs SELinux enforcing by default. Nginx + PHP-FPM Unix sockets require proper context.

```bash
# Install SELinux tools
sudo dnf install -y policycoreutils-python-utils setroubleshoot-server

# Allow Nginx to connect to PHP-FPM Unix sockets
sudo setsebool -P httpd_can_network_connect 1

# If FPM sockets live in /run/php*-fpm/ (non-default path)
sudo semanage fcontext -a -t httpd_var_run_t "/run/php[0-9]*-fpm(/.*)?"
sudo restorecon -Rv /run/

# Allow Nginx to read web root files
sudo chcon -R -t httpd_sys_content_t /var/www/

# Allow PHP-FPM workers to write to storage/cache dirs
sudo chcon -R -t httpd_sys_rw_content_t /var/www/example.com/storage/
sudo chcon -R -t httpd_sys_rw_content_t /var/www/example.com/bootstrap/cache/

# Check for SELinux denials related to Nginx/PHP
sudo ausearch -c 'nginx' --raw | audit2allow -M nginx-php
sudo ausearch -c 'php-fpm' --raw | audit2allow -M php-fpm-custom
# sudo semodule -i nginx-php.pp   # Apply if needed

# Monitor SELinux denials in real time
sudo journalctl -f | grep -i avc
```

---

## 13. systemd tmpfiles — Ensure Socket Dirs

Socket directories in `/run/` are cleared on reboot. Use `tmpfiles.d` to auto-recreate them.

```bash
sudo tee /etc/tmpfiles.d/php-fpm-sockets.conf > /dev/null <<'EOF'
# Type  Path                  Mode  User   Group  Age  Argument
d  /run/php72-fpm   0750  nginx  nginx   -
d  /run/php81-fpm   0750  nginx  nginx   -
d  /run/php82-fpm   0750  nginx  nginx   -
d  /run/php83-fpm   0750  nginx  nginx   -
EOF

# Apply now (also runs automatically at boot)
sudo systemd-tmpfiles --create /etc/tmpfiles.d/php-fpm-sockets.conf
```

---

## 14. Verification & Health Checks

### Quick system check

```bash
echo "=== File Descriptors ===" && cat /proc/sys/fs/file-nr
echo "=== Open FDs (nginx) ===" && ls /proc/$(pgrep -o nginx)/fd 2>/dev/null | wc -l
echo "=== Open FDs (fpm83) ===" && ls /proc/$(pgrep -o php-fpm 2>/dev/null)/fd 2>/dev/null | wc -l
echo "=== Sysctl: somaxconn ===" && sysctl net.core.somaxconn
echo "=== Sysctl: file-max ===" && sysctl fs.file-max
echo "=== THP status ===" && cat /sys/kernel/mm/transparent_hugepage/enabled
echo "=== CPU governor ===" && cpupower frequency-info -p 2>/dev/null | grep "governor"
echo "=== BBR congestion ===" && sysctl net.ipv4.tcp_congestion_control
```

### Check limits on a running FPM process

```bash
for VER in 72 81 82 83; do
  PID=$(pgrep -o -x "php-fpm: master" 2>/dev/null || pgrep -f "php${VER}" | head -1)
  echo "--- PHP ${VER} FPM (PID: $PID) ---"
  grep -E 'Max open files|Max processes|Max locked memory' /proc/${PID}/limits 2>/dev/null
done
```

### FPM status via curl

```bash
# Set up temporary access (restrict this in production with allow/deny)
for SOCK in /run/php72-fpm/www.sock /run/php81-fpm/www.sock \
            /run/php82-fpm/www.sock /run/php83-fpm/www.sock; do
  echo "--- $SOCK ---"
  curl --silent --unix-socket "$SOCK" "http://localhost/fpm-status?full" 2>/dev/null | head -20
done
```

### Nginx config test

```bash
sudo nginx -t && echo "Nginx config OK"
```

### Reload everything cleanly

```bash
sudo systemctl reload nginx
for VER in 72 81 82 83; do
  sudo systemctl reload php${VER}-php-fpm && echo "PHP ${VER} FPM reloaded"
done
```

---

## Summary Checklist

| # | Area | Config File | Done |
|---|---|---|---|
| 1 | OS limits (soft/hard nofile, nproc) | `/etc/security/limits.d/99-production.conf` | ☐ |
| 2 | PAM limits enforcement | `/etc/pam.d/system-auth` | ☐ |
| 3 | Systemd Nginx unit override | `/etc/systemd/system/nginx.service.d/override.conf` | ☐ |
| 4 | Systemd FPM unit overrides (×4) | `/etc/systemd/system/php*-php-fpm.service.d/` | ☐ |
| 5 | Kernel parameters (sysctl) | `/etc/sysctl.d/99-production.conf` | ☐ |
| 6 | TCP BBR module loaded | `/etc/modules-load.d/tcp_bbr.conf` | ☐ |
| 7 | CPU governor → performance | `/etc/systemd/system/cpupower.service` | ☐ |
| 8 | THP disabled | `/etc/systemd/system/disable-thp.service` | ☐ |
| 9 | Nginx production config | `/etc/nginx/nginx.conf` | ☐ |
| 10 | PHP-FPM pool configs (×4) | `/etc/opt/remi/php{ver}/php-fpm.d/www.conf` | ☐ |
| 11 | OPcache config + JIT (×4) | `/etc/opt/remi/php{ver}/php.d/10-opcache.ini` | ☐ |
| 12 | Logrotate | `/etc/logrotate.d/nginx`, `/etc/logrotate.d/php-fpm-all` | ☐ |
| 13 | SELinux contexts | `setsebool`, `semanage fcontext` | ☐ |
| 14 | tmpfiles.d socket dirs | `/etc/tmpfiles.d/php-fpm-sockets.conf` | ☐ |

---

*EL9 · Nginx + PHP-FPM 7.2 / 8.1 / 8.2 / 8.3 — Production Hardening Guide*
