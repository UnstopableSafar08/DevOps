# PHP 8.1 + Nginx 1.28.0 — Production Installation Guide
### EL9 (RHEL / Rocky / AlmaLinux 9.x)

---

## Prerequisites

- EL9.7 server with `root` or `sudo` access
- Minimum: 2 GB RAM, 2 CPU cores
- Ports `80` and `443` open in firewall

---

## 1. System Update & Base Utilities

```bash
dnf update -y

dnf install -y \
  tar curl vim wget net-tools lsof \
  unzip zip rsync bind-utils \
  yum-utils dnf-utils tmux
```

---

## 2. Add Repositories

```bash
# EPEL
dnf install -y \
  https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm

# Remi (PHP 8.1 source)
dnf install -y \
  https://rpms.remirepo.net/enterprise/remi-release-9.rpm

# Nginx 1.28 mainline
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

## 3. Install PHP 8.1 (as `php`)

This installs PHP 8.1 via the Remi module stream so the binary is available as `php` system-wide — not as `php81`.

```bash
# Reset module stream before switching version
dnf module reset php -y
dnf module enable php:remi-8.2 -y

dnf install -y \
  php \
  php-cli \
  php-common \
  php-fpm \
  php-bcmath \
  php-bz2 \
  php-calendar \
  php-curl \
  php-dba \
  php-devel \
  php-exif \
  php-ftp \
  php-gd \
  php-gettext \
  php-iconv \
  php-intl \
  php-json \
  php-mbstring \
  php-mysqli \
  php-mysqlnd \
  php-opcache \
  php-pcntl \
  php-pdo \
  php-posix \
  php-process \
  php-readline \
  php-session \
  php-simplexml \
  php-soap \
  php-sockets \
  php-sodium \
  php-sqlite3 \
  php-xml \
  php-xmlreader \
  php-xmlwriter \
  php-xsl \
  php-zip \
  php-pecl-igbinary \
  php-pecl-msgpack \
  php-pecl-redis \
  php-pecl-xmlrpc

# Verify installation
/opt/remi/php82/root/usr/bin/php -v

# Verify — should output PHP 8.1.x
php -v
```

---

## 4. Install Nginx 1.28.0

```bash
# Disable AppStream NGINX Module (Critical)
dnf module disable -y nginx

dnf install -y nginx

# Verify version
nginx -v
# Expected: nginx version: nginx/1.28.0
```

---

## 5. Configure PHP-FPM

Edit `/etc/php-fpm.d/www.conf`:

```bash
# Backup the default config
cp /etc/php-fpm.d/www.conf /etc/php-fpm.d/www.conf.bak
```

Replace the key directives:

```ini
[www]
; Run as nginx user
user  = nginx
group = nginx

; Use Unix socket (faster than TCP for local communication)
listen = /run/php-fpm/www.sock
listen.owner = nginx
listen.group = nginx
listen.mode  = 0660

; Process manager
pm                   = dynamic
pm.max_children      = 50
pm.start_servers     = 5
pm.min_spare_servers = 5
pm.max_spare_servers = 15
pm.max_requests      = 500

; Logging
php_flag[display_errors]        = off
php_admin_flag[log_errors]      = on
php_admin_value[error_log]      = /var/log/php-fpm/error.log

; Limits
php_admin_value[memory_limit]       = 256M
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size]       = 64M
php_admin_value[max_execution_time]  = 60
```

---

## 6. Configure PHP.ini (Production Settings)

Edit `/etc/php.ini`:

```bash
# Key production settings — find and update each line
sed -i 's/^expose_php = On/expose_php = Off/'             /etc/php.ini
sed -i 's/^display_errors = On/display_errors = Off/'     /etc/php.ini
sed -i 's/^;date.timezone =/date.timezone = UTC/'         /etc/php.ini
```

Or edit manually — confirm these values:

```ini
expose_php           = Off
display_errors       = Off
log_errors           = On
date.timezone        = UTC
memory_limit         = 256M
upload_max_filesize  = 64M
post_max_size        = 64M
max_execution_time   = 60
```

### OPcache (append to `/etc/php.d/10-opcache.ini`)

```ini
opcache.enable=1
opcache.enable_cli=0
opcache.memory_consumption=128
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.revalidate_freq=60
opcache.validate_timestamps=1
opcache.fast_shutdown=1
```

---

## 7. Configure Nginx

### Main Config — `/etc/nginx/nginx.conf`

```nginx
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;

error_log /var/log/nginx/error.log warn;
pid       /run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log  /var/log/nginx/access.log main;

    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;
    server_tokens off;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    include /etc/nginx/conf.d/*.conf;
}
```

### PHP Info Site — `/etc/nginx/conf.d/phpinfo.conf`

```nginx
server {
    listen      80;
    server_name _;                         # Catch-all — replace with your domain
    root        /var/www/phpinfo;
    index       index.php index.html;

    # Security headers
    add_header X-Frame-Options      "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff"  always;
    add_header X-XSS-Protection     "1; mode=block" always;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    # Pass PHP files to PHP-FPM
    location ~ \.php$ {
        try_files       $uri =404;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass    unix:/run/php-fpm/www.sock;
        fastcgi_index   index.php;
        fastcgi_param   SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include         fastcgi_params;
        fastcgi_read_timeout 60s;
    }

    # Deny hidden files
    location ~ /\. {
        deny all;
    }
}
```

### Create the Web Root & PHP Info Page

```bash
mkdir -p /var/www/phpinfo
cat > /var/www/phpinfo/index.php << 'EOF'
<?php phpinfo();
EOF

chown -R nginx:nginx /var/www/phpinfo
chmod 755 /var/www/phpinfo
```

---

## 8. System Limits & File Descriptors

### Kernel Parameters — `/etc/sysctl.d/99-production.conf`

```bash
cat > /etc/sysctl.d/99-production.conf << 'EOF'
fs.file-max                    = 2097152
net.core.somaxconn             = 65535
net.ipv4.tcp_max_syn_backlog   = 65535
net.ipv4.tcp_fin_timeout       = 15
net.ipv4.tcp_tw_reuse          = 1
net.ipv4.ip_local_port_range   = 1024 65535
vm.swappiness                  = 10
EOF

sysctl -p /etc/sysctl.d/99-production.conf
```

### User Limits — `/etc/security/limits.d/99-production.conf`

```bash
cat > /etc/security/limits.d/99-production.conf << 'EOF'
nginx   soft    nofile  65535
nginx   hard    nofile  65535
*       soft    nofile  65535
*       hard    nofile  65535
EOF
```

### Systemd Service Overrides

> `limits.conf` alone does **not** apply to systemd services. You must also set limits here.

```bash
# Nginx
mkdir -p /etc/systemd/system/nginx.service.d
cat > /etc/systemd/system/nginx.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65535
EOF

# PHP-FPM
mkdir -p /etc/systemd/system/php-fpm.service.d
cat > /etc/systemd/system/php-fpm.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65535
EOF

systemctl daemon-reload
```

---

## 9. Firewall

```bash
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

---

## 10. Enable & Start Services

```bash
systemctl enable  nginx php-fpm
systemctl start   nginx php-fpm

systemctl status  nginx php-fpm
```

---

## 11. Verify

```bash
# Nginx config test
nginx -t

# PHP version
php -v

# Socket exists
ls -la /run/php-fpm/www.sock

# Open the PHP info page
curl -s http://localhost | grep -i "PHP Version"
```

Open `http://<your-server-ip>/` in a browser — you should see the PHP info page.

> **Security reminder:** Remove or protect the `phpinfo()` page before going live.
> ```bash
> rm /var/www/phpinfo/index.php
> ```

---

## Quick Reference

| Service | Config File | Socket / Log |
|---|---|---|
| Nginx 1.28 | `/etc/nginx/nginx.conf` | `/var/log/nginx/` |
| PHP-FPM 8.1 | `/etc/php-fpm.d/www.conf` | `/run/php-fpm/www.sock` |
| PHP config | `/etc/php.ini` | `/var/log/php-fpm/error.log` |
| OPcache | `/etc/php.d/10-opcache.ini` | — |

| Task | Command |
|---|---|
| Reload Nginx | `systemctl reload nginx` |
| Reload PHP-FPM | `systemctl reload php-fpm` |
| Test Nginx config | `nginx -t` |
| Watch error log | `tail -f /var/log/nginx/error.log` |
| Watch PHP-FPM log | `tail -f /var/log/php-fpm/error.log` |

---

*EL9.7 · Nginx 1.28.0 · PHP 8.1 via Remi module stream*
