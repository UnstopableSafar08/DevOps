# NGINX 1.28.x Installation Guide for RHEL

This guide covers installing NGINX 1.28.x (stable version) on Red Hat Enterprise Linux (RHEL) 8 and 9.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Method 1: Install from Official NGINX Repository (Recommended)](#method-1-install-from-official-nginx-repository-recommended)
3. [Method 2: Compile from Source](#method-2-compile-from-source)
4. [Post-Installation Configuration](#post-installation-configuration)
5. [Basic NGINX Commands](#basic-nginx-commands)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- RHEL 8 or RHEL 9 (or compatible: Rocky Linux, AlmaLinux, CentOS Stream)
- Root or sudo access
- Internet connection

**Check your RHEL version:**
```bash
cat /etc/redhat-release
```

---

## Method 1: Install from Official NGINX Repository (Recommended)

This method installs NGINX 1.28.x from the official NGINX repository, ensuring you get the latest stable version.

### Step 1: Install Required Dependencies

```bash
sudo dnf install -y yum-utils
```

**What this does:** Installs utilities needed to manage repositories.

### Step 2: Add the Official NGINX Repository

Create the NGINX repository configuration file:

```bash
sudo tee /etc/yum.repos.d/nginx.repo > /dev/null <<EOF
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/rhel/\$releasever/\$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true

[nginx-mainline]
name=nginx mainline repo
baseurl=http://nginx.org/packages/mainline/rhel/\$releasever/\$basearch/
gpgcheck=1
enabled=0
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF
```

**What this does:**
- Creates two repository entries: `nginx-stable` (enabled) and `nginx-mainline` (disabled)
- `nginx-stable` provides NGINX 1.28.x
- Uses official NGINX GPG key for package verification
- `module_hotfixes=true` prevents conflicts with RHEL modules

### Step 3: Verify Repository Configuration

```bash
sudo dnf repolist | grep nginx
```

**Expected output:**
```
nginx-stable    nginx stable repo
```

### Step 4: Check Available NGINX Version

```bash
sudo dnf info nginx
```

Look for version information showing 1.28.x:
```
Name         : nginx
Version      : 1.28.0
Release      : 1.el9.ngx
Architecture : x86_64
```

### Step 5: Install NGINX 1.28.x

```bash
sudo dnf install -y nginx
```

**What this does:** Downloads and installs NGINX 1.28.x and its dependencies.

### Step 6: Verify Installation

```bash
nginx -v
```

**Expected output:**
```
nginx version: nginx/1.28.0
```

### Step 7: Start and Enable NGINX

```bash
# Start NGINX
sudo systemctl start nginx

# Enable NGINX to start on boot
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

**Expected status output:**
```
● nginx.service - nginx - high performance web server
   Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled)
   Active: active (running)
```

### Step 8: Configure Firewall

Allow HTTP and HTTPS traffic through the firewall:

```bash
# Allow HTTP (port 80)
sudo firewall-cmd --permanent --add-service=http

# Allow HTTPS (port 443)
sudo firewall-cmd --permanent --add-service=https

# Reload firewall
sudo firewall-cmd --reload

# Verify rules
sudo firewall-cmd --list-services
```

### Step 9: Test NGINX

**From the server:**
```bash
curl http://localhost
```

**From a web browser:**
Navigate to `http://your-server-ip`

You should see the default NGINX welcome page.

---

## Method 2: Compile from Source

This method gives you full control over NGINX features and modules.

### Step 1: Install Build Dependencies

```bash
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y pcre pcre-devel zlib zlib-devel openssl openssl-devel wget
```

**What this does:** Installs compilers, libraries, and tools needed to build NGINX.

### Step 2: Download NGINX 1.28.0 Source

```bash
cd /tmp
wget http://nginx.org/download/nginx-1.28.0.tar.gz
```

**Verify the download:**
```bash
ls -lh nginx-1.28.0.tar.gz
```

### Step 3: Extract the Archive

```bash
tar -xzf nginx-1.28.0.tar.gz
cd nginx-1.28.0
```

### Step 4: Configure the Build

**Basic configuration:**
```bash
./configure \
  --prefix=/etc/nginx \
  --sbin-path=/usr/sbin/nginx \
  --modules-path=/usr/lib64/nginx/modules \
  --conf-path=/etc/nginx/nginx.conf \
  --error-log-path=/var/log/nginx/error.log \
  --http-log-path=/var/log/nginx/access.log \
  --pid-path=/var/run/nginx.pid \
  --lock-path=/var/run/nginx.lock \
  --http-client-body-temp-path=/var/cache/nginx/client_temp \
  --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
  --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
  --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp \
  --http-scgi-temp-path=/var/cache/nginx/scgi_temp \
  --user=nginx \
  --group=nginx \
  --with-http_ssl_module \
  --with-http_realip_module \
  --with-http_addition_module \
  --with-http_sub_module \
  --with-http_dav_module \
  --with-http_flv_module \
  --with-http_mp4_module \
  --with-http_gunzip_module \
  --with-http_gzip_static_module \
  --with-http_random_index_module \
  --with-http_secure_link_module \
  --with-http_stub_status_module \
  --with-http_auth_request_module \
  --with-http_xslt_module=dynamic \
  --with-http_image_filter_module=dynamic \
  --with-http_geoip_module=dynamic \
  --with-threads \
  --with-stream \
  --with-stream_ssl_module \
  --with-stream_ssl_preread_module \
  --with-stream_realip_module \
  --with-stream_geoip_module=dynamic \
  --with-http_slice_module \
  --with-mail \
  --with-mail_ssl_module \
  --with-compat \
  --with-file-aio \
  --with-http_v2_module
```

**What this does:** Configures the build with commonly used modules and standard paths.

**For additional modules (like HTTP/3 QUIC support):**
```bash
./configure \
  --prefix=/etc/nginx \
  --sbin-path=/usr/sbin/nginx \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_v3_module \
  --with-stream \
  --with-stream_ssl_module \
  --with-stream_quic_module
```

### Step 5: Compile and Install

```bash
# Compile (use number of CPU cores for faster build)
make -j$(nproc)

# Install
sudo make install
```

**What this does:** 
- Compiles NGINX with configured modules
- Installs binaries, configuration files, and directories

### Step 6: Create NGINX User

```bash
sudo useradd -r -M -s /sbin/nologin nginx
```

### Step 7: Create Required Directories

```bash
sudo mkdir -p /var/cache/nginx/{client_temp,proxy_temp,fastcgi_temp,uwsgi_temp,scgi_temp}
sudo chown -R nginx:nginx /var/cache/nginx
```

### Step 8: Create Systemd Service File

```bash
sudo tee /usr/lib/systemd/system/nginx.service > /dev/null <<'EOF'
[Unit]
Description=nginx - high performance web server
Documentation=http://nginx.org/en/docs/
After=network-online.target remote-fs.target nss-lookup.target
Wants=network-online.target

[Service]
Type=forking
PIDFile=/var/run/nginx.pid
ExecStartPre=/usr/sbin/nginx -t -c /etc/nginx/nginx.conf
ExecStart=/usr/sbin/nginx -c /etc/nginx/nginx.conf
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID

[Install]
WantedBy=multi-user.target
EOF
```

### Step 9: Reload Systemd and Start NGINX

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start NGINX
sudo systemctl start nginx

# Enable on boot
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
```

### Step 10: Verify Installation

```bash
nginx -v
```

**Expected output:**
```
nginx version: nginx/1.28.0
```

### Step 11: Configure Firewall

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Post-Installation Configuration

### Default Configuration Location

**Main config:** `/etc/nginx/nginx.conf`

**Site configs:** `/etc/nginx/conf.d/`

### Basic Configuration Example

Create a simple website configuration:

```bash
sudo tee /etc/nginx/conf.d/mysite.conf > /dev/null <<'EOF'
server {
    listen       80;
    server_name  example.com www.example.com;
    root         /usr/share/nginx/html;
    index        index.html index.htm;

    location / {
        try_files $uri $uri/ =404;
    }

    error_page 404 /404.html;
    location = /404.html {
        internal;
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        internal;
    }
}
EOF
```

### Test Configuration

```bash
sudo nginx -t
```

**Expected output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Reload NGINX

```bash
sudo systemctl reload nginx
```

### SELinux Configuration (If Enabled)

If you encounter permission issues with SELinux:

```bash
# Check SELinux status
sestatus

# Allow NGINX to make network connections
sudo setsebool -P httpd_can_network_connect 1

# Set proper context for web content
sudo chcon -R -t httpd_sys_content_t /usr/share/nginx/html

# For custom document roots
sudo semanage fcontext -a -t httpd_sys_content_t "/path/to/your/content(/.*)?"
sudo restorecon -R /path/to/your/content
```

---

## Basic NGINX Commands

### Service Management

```bash
# Start NGINX
sudo systemctl start nginx

# Stop NGINX
sudo systemctl stop nginx

# Restart NGINX (stops then starts)
sudo systemctl restart nginx

# Reload configuration (graceful, no downtime)
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx

# Enable on boot
sudo systemctl enable nginx

# Disable on boot
sudo systemctl disable nginx
```

### Configuration Testing

```bash
# Test configuration syntax
sudo nginx -t

# Test and display configuration
sudo nginx -T
```

### Version and Module Information

```bash
# Show version
nginx -v

# Show version and configure options
nginx -V
```

### Log Files

```bash
# View error log
sudo tail -f /var/log/nginx/error.log

# View access log
sudo tail -f /var/log/nginx/access.log

# View both logs
sudo tail -f /var/log/nginx/*.log
```

---

## Troubleshooting

### Issue: Port 80 Already in Use

**Check what's using port 80:**
```bash
sudo ss -tulpn | grep :80
```

**Common culprit: Apache (httpd)**
```bash
# Stop Apache
sudo systemctl stop httpd

# Disable Apache
sudo systemctl disable httpd

# Start NGINX
sudo systemctl start nginx
```

### Issue: Permission Denied

**Check NGINX user:**
```bash
ps aux | grep nginx
```

**Verify file permissions:**
```bash
ls -la /usr/share/nginx/html
```

**Fix permissions:**
```bash
sudo chown -R nginx:nginx /usr/share/nginx/html
sudo chmod -R 755 /usr/share/nginx/html
```

### Issue: SELinux Blocking NGINX

**Check SELinux denials:**
```bash
sudo ausearch -m avc -ts recent | grep nginx
```

**Temporary disable for testing (NOT for production):**
```bash
sudo setenforce 0
```

**Re-enable SELinux:**
```bash
sudo setenforce 1
```

**Proper fix - create SELinux policy:**
```bash
sudo ausearch -m avc -ts recent | grep nginx | audit2allow -M nginx_custom
sudo semodule -i nginx_custom.pp
```

### Issue: Cannot Access from External Network

**Check firewall:**
```bash
sudo firewall-cmd --list-all
```

**Ensure HTTP/HTTPS are allowed:**
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

**Check if NGINX is listening:**
```bash
sudo ss -tulpn | grep nginx
```

### Issue: Configuration Syntax Error

**Test configuration:**
```bash
sudo nginx -t
```

**Common mistakes:**
- Missing semicolons (;)
- Unclosed braces ({ })
- Invalid directives
- Wrong file paths

**View detailed error:**
```bash
sudo tail -20 /var/log/nginx/error.log
```

### Issue: NGINX Won't Start After Reboot

**Check service status:**
```bash
sudo systemctl status nginx
```

**Check if enabled:**
```bash
sudo systemctl is-enabled nginx
```

**Enable if not:**
```bash
sudo systemctl enable nginx
```

### Issue: Upgrade from Repository Shows No Updates

**Clear cache:**
```bash
sudo dnf clean all
sudo dnf makecache
```

**Check for updates:**
```bash
sudo dnf check-update nginx
```

**Force reinstall specific version:**
```bash
sudo dnf reinstall nginx-1.28.0
```

---

## Upgrading to Future 1.28.x Releases

When NGINX 1.28.1, 1.28.2, etc. are released:

```bash
# Check for updates
sudo dnf check-update nginx

# Upgrade NGINX
sudo dnf update nginx

# Verify new version
nginx -v

# Reload NGINX
sudo systemctl reload nginx
```

---

## NGINX 1.28.0 Key Features

NGINX 1.28.0 includes several important improvements:

- **SSL Optimizations:** Memory and CPU usage improvements in complex SSL configurations
- **Dynamic DNS Resolution:** Automatic re-resolution of hostnames in upstream groups
- **QUIC Performance:** CUBIC congestion control algorithm for better performance
- **OCSP Support:** Enhanced certificate validation capabilities
- **Variable Support:** New variables in proxy_limit_rate and related directives

---

## Security Recommendations

### 1. Keep NGINX Updated

```bash
# Regular updates
sudo dnf update nginx
```

### 2. Hide NGINX Version

Edit `/etc/nginx/nginx.conf`:
```nginx
http {
    server_tokens off;
    ...
}
```

### 3. Configure SSL/TLS Properly

```nginx
server {
    listen 443 ssl http2;
    
    ssl_certificate /path/to/cert.crt;
    ssl_certificate_key /path/to/cert.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
}
```

### 4. Set Up Rate Limiting

```nginx
http {
    limit_req_zone $binary_remote_addr zone=mylimit:10m rate=10r/s;
    
    server {
        location / {
            limit_req zone=mylimit burst=20;
        }
    }
}
```

### 5. Regular Log Monitoring

```bash
# Setup logrotate for NGINX
sudo cat > /etc/logrotate.d/nginx <<'EOF'
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 nginx adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
EOF
```

---

## Summary

You now have NGINX 1.28.x installed and running on RHEL. You can:

- ✅ Access NGINX at `http://your-server-ip`
- ✅ Manage NGINX with systemctl commands
- ✅ Edit configurations in `/etc/nginx/`
- ✅ Monitor logs in `/var/log/nginx/`
- ✅ Secure with firewall and SELinux

**Next Steps:**
- Configure virtual hosts for your websites
- Set up SSL/TLS certificates (Let's Encrypt recommended)
- Configure reverse proxy for applications
- Implement caching and optimization
- Set up monitoring and alerting
