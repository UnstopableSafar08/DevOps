# Installing Nginx 1.24 on Oracle Linux (Offline Method)

Since your target server has no internet, you'll download dependencies on an internet-connected machine and transfer them.

## Method 1: Compile from Source (Recommended for specific version)

### On the Internet-Connected Server

**1. Download Nginx source:**
```bash
cd /tmp
wget https://nginx.org/download/nginx-1.24.0.tar.gz
```

**2. Download required dependencies (RPMs):**
```bash
mkdir nginx-deps
cd nginx-deps

# Download build tools and libraries
yumdownloader --resolve --destdir=. gcc make pcre pcre-devel zlib zlib-devel openssl openssl-devel
```

> If `yumdownloader` is missing: `yum install yum-utils`

**3. Bundle everything:**
```bash
cd /tmp
tar czvf nginx-offline.tar.gz nginx-1.24.0.tar.gz nginx-deps/
```

**4. Transfer to offline server:**
```bash
scp nginx-offline.tar.gz user@offline-server:/tmp/
```

---

### On the Offline Server

**1. Extract:**
```bash
cd /tmp
tar xzvf nginx-offline.tar.gz
```

**2. Install dependencies:**
```bash
cd nginx-deps
yum install -y *.rpm
# OR if yum complains:
rpm -Uvh --force --nodeps *.rpm
```

**3. Compile and install Nginx:**
```bash
cd /tmp
tar xzvf nginx-1.24.0.tar.gz
cd nginx-1.24.0

./configure \
  --prefix=/etc/nginx \
  --sbin-path=/usr/sbin/nginx \
  --conf-path=/etc/nginx/nginx.conf \
  --error-log-path=/var/log/nginx/error.log \
  --http-log-path=/var/log/nginx/access.log \
  --pid-path=/var/run/nginx.pid \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_realip_module \
  --with-http_gzip_static_module

make
make install
```

---

## Method 2: Pre-built RPM (Easier)

### On Internet-Connected Server

**1. Add Nginx official repo and download RPM:**
```bash
# Create repo file
cat > /etc/yum.repos.d/nginx.repo <<EOF
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/\$releasever/\$basearch/
gpgcheck=0
enabled=1
EOF

# Download nginx 1.24 + dependencies
mkdir /tmp/nginx-rpm
yumdownloader --resolve --destdir=/tmp/nginx-rpm nginx-1.24.0
```

**2. Bundle and transfer:**
```bash
cd /tmp
tar czvf nginx-rpm.tar.gz nginx-rpm/
scp nginx-rpm.tar.gz user@offline-server:/tmp/
```

### On Offline Server

```bash
cd /tmp
tar xzvf nginx-rpm.tar.gz
cd nginx-rpm
yum install -y *.rpm
```

---

## Post-Installation (Both Methods)

**Create systemd service** (only needed for Method 1):
```bash
cat > /etc/systemd/system/nginx.service <<'EOF'
[Unit]
Description=The NGINX HTTP server
After=network.target

[Service]
Type=forking
PIDFile=/var/run/nginx.pid
ExecStartPre=/usr/sbin/nginx -t
ExecStart=/usr/sbin/nginx
ExecReload=/usr/sbin/nginx -s reload
ExecStop=/bin/kill -s QUIT $MAINPID

[Install]
WantedBy=multi-user.target
EOF
```

**Start and enable:**
```bash
systemctl daemon-reload
systemctl enable nginx
systemctl start nginx
systemctl status nginx
```

**Verify version:**
```bash
nginx -v
```

**Open firewall:**
```bash
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

---

## ⚠️ Important Tip

Make sure **both servers have the same Oracle Linux version** (e.g., both OL8 or both OL9). RPM dependencies are version-specific, otherwise you'll get library mismatch errors.

Check version with:
```bash
cat /etc/oracle-release
```
