# PHP Multi-Version Installation Guide
### EL9 (RHEL/Rocky/AlmaLinux 9.x) + Nginx 1.28.0 — Production Setup

> **Server Specs:** EL9.7 · 8 GB RAM · 4 CPU Cores

---

## Table of Contents

1. [System Preparation](#1-system-preparation)
2. [Install Base Utilities](#2-install-base-utilities)
3. [Add Required Repositories](#3-add-required-repositories)
4. [Install PHP 8.1](#4-install-php-81)
5. [Install PHP 8.2](#5-install-php-82)
6. [Install Nginx 1.28.0](#6-install-nginx-1280)
7. [PHP-FPM Pool Configuration](#7-php-fpm-pool-configuration)
8. [Nginx Virtual Host Configuration](#8-nginx-virtual-host-configuration)
9. [System Limits & File Descriptors](#9-system-limits--file-descriptors)
10. [Production Best Practices](#10-production-best-practices)
11. [Managing Services](#11-managing-services)
12. [Validation & Troubleshooting](#12-validation--troubleshooting)

---

## 1. System Preparation

```bash
# Full system update
dnf update -y

# Disable SELinux enforcing (or configure it properly for your app)
setenforce 0
sed -i 's/^SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

# Set timezone
timedatectl set-timezone "Asia/Kathmandu"
```

---

## 2. Install Base Utilities

```bash
dnf install -y \
  tar curl vim wget telnet traceroute net-tools lsof \
  unzip zip rsync bind-utils socat httpd-tools \
  yum-utils dnf-utils tmux nc

# Install EPEL for htop and other utilities
dnf install epel-release -y
dnf install -y htop
```

---

## 3. Add Required Repositories

```bash
# EPEL for EL9
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm

# Remi repository (provides PHP 8.1, 8.2, 8.3, etc.)
dnf install -y https://rpms.remirepo.net/enterprise/remi-release-9.rpm

# Nginx mainline repo (for Nginx 1.28.0)
cat > /etc/yum.repos.d/nginx.repo << 'EOF'
[nginx-mainline]
name=nginx mainline repo
baseurl=http://nginx.org/packages/mainline/rhel/$releasever/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF
```

---

## 4. Install PHP 8.1

```bash
# Reset any active PHP module stream
dnf module reset php -y
dnf module enable php:remi-8.1 -y

dnf install -y \
  php81 \
  php81-php-cli \
  php81-php-common \
  php81-php-fpm \
  php81-php-bcmath \
  php81-php-bz2 \
  php81-php-calendar \
  php81-php-curl \
  php81-php-dba \
  php81-php-devel \
  php81-php-exif \
  php81-php-ftp \
  php81-php-gd \
  php81-php-gettext \
  php81-php-iconv \
  php81-php-intl \
  php81-php-json \
  php81-php-mbstring \
  php81-php-mysqli \
  php81-php-mysqlnd \
  php81-php-opcache \
  php81-php-pcntl \
  php81-php-pdo \
  php81-php-posix \
  php81-php-process \
  php81-php-readline \
  php81-php-session \
  php81-php-simplexml \
  php81-php-soap \
  php81-php-sockets \
  php81-php-sodium \
  php81-php-sqlite3 \
  php81-php-xml \
  php81-php-xmlreader \
  php81-php-xmlwriter \
  php81-php-xsl \
  php81-php-zip \
  php81-php-pecl-igbinary \
  php81-php-pecl-msgpack \
  php81-php-pecl-redis \
  php81-php-pecl-xmlrpc

# Verify installation
/opt/remi/php81/root/usr/bin/php -v
```

---

## 5. Install PHP 8.2

```bash
# Reset module stream before switching version
dnf module reset php -y
dnf module enable php:remi-8.2 -y

dnf install -y \
  php82 \
  php82-php-cli \
  php82-php-common \
  php82-php-fpm \
  php82-php-bcmath \
  php82-php-bz2 \
  php82-php-calendar \
  php82-php-curl \
  php82-php-dba \
  php82-php-devel \
  php82-php-exif \
  php82-php-ftp \
  php82-php-gd \
  php82-php-gettext \
  php82-php-iconv \
  php82-php-intl \
  php82-php-json \
  php82-php-mbstring \
  php82-php-mysqli \
  php82-php-mysqlnd \
  php82-php-opcache \
  php82-php-pcntl \
  php82-php-pdo \
  php82-php-posix \
  php82-php-process \
  php82-php-readline \
  php82-php-session \
  php82-php-simplexml \
  php82-php-soap \
  php82-php-sockets \
  php82-php-sodium \
  php82-php-sqlite3 \
  php82-php-xml \
  php82-php-xmlreader \
  php82-php-xmlwriter \
  php82-php-xsl \
  php82-php-zip \
  php82-php-pecl-igbinary \
  php82-php-pecl-msgpack \
  php82-php-pecl-redis \
  php82-php-pecl-xmlrpc

# Verify installation
/opt/remi/php82/root/usr/bin/php -v
```

> **Note:** Both PHP versions coexist independently. PHP 8.1 binaries live under `/opt/remi/php81/` and PHP 8.2 under `/opt/remi/php82/`. They do **not** conflict.

---

## 6. Install Nginx 1.28.0

```bash
# Disable AppStream NGINX Module (Critical)
dnf module disable -y nginx

dnf install -y nginx

# Confirm version
nginx -v
# Expected: nginx version: nginx/1.28.0

# Enable and start
systemctl enable nginx
systemctl start nginx
```

---

## 7. PHP-FPM Pool Configuration

Each PHP version runs its own PHP-FPM service listening on a dedicated Unix socket. This is safer and faster than TCP ports for local communication.

### PHP 8.1 FPM Pool — `/etc/opt/remi/php81/php-fpm.d/www.conf`

```ini
[www]
user = nginx
group = nginx
listen = /run/php-fpm/php81.sock
listen.owner = nginx
listen.group = nginx
listen.mode = 0660

; --- Process Manager (tuned for 8 GB RAM / 4 cores) ---
pm = dynamic
pm.max_children = 50
pm.start_servers = 10
pm.min_spare_servers = 5
pm.max_spare_servers = 20
pm.max_requests = 500

; --- Timeouts ---
request_terminate_timeout = 60s
request_slowlog_timeout = 10s
slowlog = /var/log/php81-fpm-slow.log

; --- Logging ---
access.log = /var/log/php81-fpm-access.log
php_flag[display_errors] = off
php_admin_value[error_log] = /var/log/php81-fpm-error.log
php_admin_flag[log_errors] = on

; --- Security ---
php_admin_value[open_basedir] = /var/www:/tmp:/usr/share/php
php_admin_value[disable_functions] = exec,passthru,shell_exec,system,proc_open,popen
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size] = 64M
php_admin_value[memory_limit] = 256M
php_admin_value[max_execution_time] = 60
php_admin_value[session.save_path] = /var/lib/php/sessions/php81

; --- OPcache ---
php_admin_value[opcache.enable] = 1
php_admin_value[opcache.memory_consumption] = 128
php_admin_value[opcache.interned_strings_buffer] = 16
php_admin_value[opcache.max_accelerated_files] = 10000
php_admin_value[opcache.revalidate_freq] = 60
php_admin_value[opcache.validate_timestamps] = 0
```

### PHP 8.2 FPM Pool — `/etc/opt/remi/php82/php-fpm.d/www.conf`

```ini
[www]
user = nginx
group = nginx
listen = /run/php-fpm/php82.sock
listen.owner = nginx
listen.group = nginx
listen.mode = 0660

pm = dynamic
pm.max_children = 50
pm.start_servers = 10
pm.min_spare_servers = 5
pm.max_spare_servers = 20
pm.max_requests = 500

request_terminate_timeout = 60s
request_slowlog_timeout = 10s
slowlog = /var/log/php82-fpm-slow.log

access.log = /var/log/php82-fpm-access.log
php_flag[display_errors] = off
php_admin_value[error_log] = /var/log/php82-fpm-error.log
php_admin_flag[log_errors] = on

php_admin_value[open_basedir] = /var/www:/tmp:/usr/share/php
php_admin_value[disable_functions] = exec,passthru,shell_exec,system,proc_open,popen
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size] = 64M
php_admin_value[memory_limit] = 256M
php_admin_value[max_execution_time] = 60
php_admin_value[session.save_path] = /var/lib/php/sessions/php82

php_admin_value[opcache.enable] = 1
php_admin_value[opcache.memory_consumption] = 128
php_admin_value[opcache.interned_strings_buffer] = 16
php_admin_value[opcache.max_accelerated_files] = 10000
php_admin_value[opcache.revalidate_freq] = 60
php_admin_value[opcache.validate_timestamps] = 0
```

### Enable & Start Both FPM Services

```bash
# Create socket directory
mkdir -p /run/php-fpm
chown nginx:nginx /run/php-fpm

# Create session directories
mkdir -p /var/lib/php/sessions/php81 /var/lib/php/sessions/php82
chown nginx:nginx /var/lib/php/sessions/php81 /var/lib/php/sessions/php82

# Enable services
systemctl enable php81-php-fpm php82-php-fpm
systemctl start php81-php-fpm php82-php-fpm

# Verify sockets exist
ls -la /run/php-fpm/
```

---

## 8. Nginx Virtual Host Configuration

### Main Nginx Config — `/etc/nginx/nginx.conf`

```nginx
user nginx;
worker_processes auto;          # auto = 1 worker per CPU core (4 cores)
worker_rlimit_nofile 65535;     # match system ulimit

error_log /var/log/nginx/error.log warn;
pid       /run/nginx.pid;

events {
    worker_connections  4096;   # 4 cores × 4096 = ~16k concurrent connections
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # --- Logging ---
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # --- Performance ---
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;
    keepalive_requests 1000;
    types_hash_max_size 2048;
    server_tokens off;

    # --- Buffer Tuning ---
    client_body_buffer_size    16k;
    client_header_buffer_size  1k;
    client_max_body_size       64m;
    large_client_header_buffers 4 8k;

    # --- Timeouts ---
    client_body_timeout   12;
    client_header_timeout 12;
    send_timeout          10;

    # --- Gzip ---
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json
               application/javascript application/xml+rss text/javascript;

    # --- Rate Limiting ---
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    include /etc/nginx/conf.d/*.conf;
}
```

### Site Using PHP 8.1 — `/etc/nginx/conf.d/app-php81.conf`

```nginx
server {
    listen 80;
    server_name app81.example.com;
    root /var/www/app81/public;
    index index.php index.html;

    # Rate limiting
    limit_req zone=api burst=50 nodelay;
    limit_conn conn_limit 20;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass unix:/run/php-fpm/php81.sock;  # PHP 8.1 socket
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;

        fastcgi_connect_timeout 60s;
        fastcgi_send_timeout    60s;
        fastcgi_read_timeout    60s;
        fastcgi_buffer_size     128k;
        fastcgi_buffers         4 256k;
        fastcgi_busy_buffers_size 256k;
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Static asset caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

### Site Using PHP 8.2 — `/etc/nginx/conf.d/app-php82.conf`

```nginx
server {
    listen 80;
    server_name app82.example.com;
    root /var/www/app82/public;
    index index.php index.html;

    limit_req zone=api burst=50 nodelay;
    limit_conn conn_limit 20;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass unix:/run/php-fpm/php82.sock;  # PHP 8.2 socket
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;

        fastcgi_connect_timeout 60s;
        fastcgi_send_timeout    60s;
        fastcgi_read_timeout    60s;
        fastcgi_buffer_size     128k;
        fastcgi_buffers         4 256k;
        fastcgi_busy_buffers_size 256k;
    }

    location ~ /\. {
        deny all;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

---

## 9. System Limits & File Descriptors

This is one of the most overlooked areas in production PHP/Nginx deployments. Under heavy load, hitting the default limits (1024 open files per process) causes `Too many open files` errors.

### 9.1 System-Wide Limits — `/etc/sysctl.conf`

```bash
cat >> /etc/sysctl.conf << 'EOF'

# --- File Descriptors ---
fs.file-max = 2097152              # Max open files system-wide
fs.nr_open  = 2097152

# --- Network Tuning ---
net.core.somaxconn          = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout     = 15
net.ipv4.tcp_keepalive_time  = 300
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse        = 1
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# --- Virtual Memory ---
vm.swappiness         = 10
vm.dirty_ratio        = 15
vm.dirty_background_ratio = 5
EOF

# Apply immediately
sysctl -p
```

### 9.2 User Process Limits — `/etc/security/limits.conf`

```bash
cat >> /etc/security/limits.conf << 'EOF'

# nginx process limits
nginx           soft    nofile  65535
nginx           hard    nofile  65535
nginx           soft    nproc   65535
nginx           hard    nproc   65535

# Root limits (for CLI tools)
root            soft    nofile  65535
root            hard    nofile  65535

# Wildcard (catch-all for all users)
*               soft    nofile  65535
*               hard    nofile  65535
*               soft    nproc   65535
*               hard    nproc   65535
EOF
```

### 9.3 PAM Limits — `/etc/security/limits.d/99-custom.conf`

```bash
cat > /etc/security/limits.d/99-custom.conf << 'EOF'
# Production server limits
*    soft nofile 65535
*    hard nofile 65535
*    soft nproc  65535
*    hard nproc  65535
nginx soft nofile 65535
nginx hard nofile 65535
EOF
```

### 9.4 Systemd Service Limits

For systemd-managed services (Nginx, PHP-FPM), limits must also be set via systemd override files — `limits.conf` alone is **not** enough.

```bash
# Nginx service override
mkdir -p /etc/systemd/system/nginx.service.d/
cat > /etc/systemd/system/nginx.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65535
LimitNPROC=65535
EOF

# PHP 8.1 FPM service override
mkdir -p /etc/systemd/system/php81-php-fpm.service.d/
cat > /etc/systemd/system/php81-php-fpm.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65535
LimitNPROC=65535
EOF

# PHP 8.2 FPM service override
mkdir -p /etc/systemd/system/php82-php-fpm.service.d/
cat > /etc/systemd/system/php82-php-fpm.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65535
LimitNPROC=65535
EOF

# Reload systemd and restart services
systemctl daemon-reload
systemctl restart nginx php81-php-fpm php82-php-fpm
```

### 9.5 Verify Limits Are Applied

```bash
# Check nginx worker process limits
cat /proc/$(pgrep -o nginx)/limits | grep -E "open files|processes"

# Check PHP-FPM limits
cat /proc/$(pgrep -o php81)/limits | grep -E "open files|processes"

# Check current system-wide open file count
cat /proc/sys/fs/file-nr

# Show effective limits for a running process
prlimit --pid $(pgrep -o nginx)
```

---

## 10. Production Best Practices

### 10.1 OPcache — Maximum Performance

OPcache dramatically reduces PHP execution time by caching compiled bytecode. Add to each version's `php.ini`:

`/etc/opt/remi/php81/php.d/10-opcache.ini` and `/etc/opt/remi/php82/php.d/10-opcache.ini`:

```ini
opcache.enable=1
opcache.enable_cli=0
opcache.memory_consumption=256        ; MB — increase if many PHP files
opcache.interned_strings_buffer=32
opcache.max_accelerated_files=20000
opcache.revalidate_freq=0             ; 0 = never revalidate in production
opcache.validate_timestamps=0         ; disable for maximum speed in production
opcache.save_comments=1
opcache.fast_shutdown=1
opcache.huge_code_pages=1             ; requires transparent huge pages enabled
```

> **Important:** Set `validate_timestamps=0` in production and reload PHP-FPM after each deployment to clear the cache: `systemctl reload php82-php-fpm`

### 10.2 PHP-FPM Process Manager Sizing

On this server (8 GB RAM, 4 cores), a safe formula for `pm.max_children` is:

```
max_children = (Available RAM for PHP) / (Average PHP process size)

Example: 4096 MB / 80 MB per process = ~50 children
```

Monitor actual memory per process:
```bash
ps --no-headers -o "rss,cmd" -C php-fpm | awk '{sum+=$1} END {print sum/NR/1024 " MB avg per process"}'
```

### 10.3 Nginx Worker Connections Formula

```
max_connections = worker_processes × worker_connections
               = 4 × 4096 = 16,384 simultaneous connections

Each connection uses ~1 file descriptor, so ensure:
worker_rlimit_nofile ≥ worker_connections × 2
```

### 10.4 Logrotate for PHP-FPM & Nginx

```bash
cat > /etc/logrotate.d/php-fpm-custom << 'EOF'
/var/log/php81-fpm*.log /var/log/php82-fpm*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload php81-php-fpm php82-php-fpm > /dev/null 2>&1 || true
    endscript
}
EOF
```

### 10.5 Security Hardening

```nginx
# Add to nginx http{} block
server_tokens off;                    # Hide nginx version

# Add to each server block
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Content-Security-Policy "default-src 'self'" always;

# Block common exploit paths
location ~* \.(htaccess|htpasswd|git|env|bak|sql|sh)$ {
    deny all;
    return 404;
}
```

```bash
# Disable unused PHP functions (in php.ini or FPM pool)
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,curl_multi_exec,parse_ini_file,show_source

# PHP security settings
expose_php = Off
display_errors = Off
log_errors = On
allow_url_fopen = Off
allow_url_include = Off
session.cookie_httponly = 1
session.cookie_secure = 1
session.use_strict_mode = 1
```

### 10.6 Firewall

```bash
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

### 10.7 Swap Configuration (for 8 GB RAM)

```bash
# Create a 2 GB swapfile as safety net
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Set low swappiness to prefer RAM
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.d/99-swap.conf
```

### 10.8 Deployment Checklist

| Check | Command |
|---|---|
| Test Nginx config | `nginx -t` |
| Reload Nginx | `systemctl reload nginx` |
| Clear OPcache after deploy | `systemctl reload php82-php-fpm` |
| Monitor PHP-FPM status | `systemctl status php82-php-fpm` |
| Check open file limits | `cat /proc/$(pgrep -o nginx)/limits` |
| Watch error logs | `tail -f /var/log/php82-fpm-error.log` |
| Check slow log | `tail -f /var/log/php82-fpm-slow.log` |

---

## 11. Managing Services

```bash
# Start all services
systemctl start nginx php81-php-fpm php82-php-fpm

# Enable on boot
systemctl enable nginx php81-php-fpm php82-php-fpm

# Graceful reload (no downtime)
systemctl reload nginx
systemctl reload php81-php-fpm
systemctl reload php82-php-fpm

# Status overview
systemctl status nginx php81-php-fpm php82-php-fpm

# View live logs
journalctl -fu nginx
journalctl -fu php81-php-fpm
journalctl -fu php82-php-fpm
```

---

## 12. Validation & Troubleshooting

### Test PHP-FPM Sockets

```bash
# Confirm sockets are listening
ls -la /run/php-fpm/
# Expected output:
# srw-rw---- 1 nginx nginx ... php81.sock
# srw-rw---- 1 nginx nginx ... php82.sock
```

### PHP Info Test Page

```bash
# Temporarily create an info page (remove after testing!)
echo "<?php phpinfo();" > /var/www/app81/public/info.php
curl http://app81.example.com/info.php | grep "PHP Version"
rm /var/www/app81/public/info.php   # Remove immediately after use
```

### Common Issues

| Problem | Cause | Fix |
|---|---|---|
| `502 Bad Gateway` | FPM socket missing or wrong permissions | Check socket exists, owner is `nginx:nginx` |
| `Too many open files` | File descriptor limit too low | Apply systemd `LimitNOFILE` overrides, reload |
| `connect() to unix socket failed` | FPM not running or wrong socket path | `systemctl status php82-php-fpm`, check socket path in nginx conf |
| High memory usage | `pm.max_children` too high | Reduce to match actual RAM / avg process size |
| Slow cold requests | OPcache not warming | Enable `opcache.preload` (PHP 7.4+) |
| PHP sessions not writable | Wrong ownership on session dir | `chown nginx:nginx /var/lib/php/sessions/php82` |

### Quick Resource Check

```bash
# CPU, memory, load
htop

# Open file descriptors system-wide
cat /proc/sys/fs/file-nr
# Output: [used] [unused] [max]

# Per-process file descriptor count
ls /proc/$(pgrep -o nginx)/fd | wc -l

# Active connections
ss -s
netstat -an | grep :80 | wc -l
```

---

## Summary

```
EL9 Server
├── Nginx 1.28.0 (mainline)
│   ├── app81.example.com  →  /run/php-fpm/php81.sock
│   └── app82.example.com  →  /run/php-fpm/php82.sock
│
├── PHP 8.1-FPM  (/opt/remi/php81/)
│   └── Pool: dynamic, 50 children max, 256MB/process
│
└── PHP 8.2-FPM  (/opt/remi/php82/)
    └── Pool: dynamic, 50 children max, 256MB/process

System Limits
├── fs.file-max: 2,097,152
├── LimitNOFILE: 65,535 (per service via systemd)
└── worker_connections: 4,096 × 4 cores = 16,384 max connections
```

---

*Generated for EL9.7 · Nginx 1.28.0 · PHP 8.1 & 8.2 via Remi Repo*
