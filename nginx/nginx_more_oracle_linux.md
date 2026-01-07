# NGINX "More" Custom Build on Oracle Linux 9/10

This guide provides step-by-step instructions to **compile and install NGINX from source** on **Oracle Linux 9/10**, including a set of **custom dynamic and static modules** for advanced HTTP, stream, and caching functionality. It also covers **configuration, systemd setup, and permissions**.

---

## Supported Modules

* **Dynamic Modules**:

  * `ngx_http_perl_module`

* **Custom Modules**:

  * ngx_headers_more
  * ngx_cache_purge
  * ngx_pagespeed
  * ngx_brotli
  * ngx_http_geoip2
  * ngx_module_vts
  * ngx_echo

* **Built-in Modules**:

  * SSL, HTTP/2, stub_status, proxy, gzip, stream, mail, etc.

---

## Prerequisites

Update system and install build dependencies:

```bash
sudo dnf update -y

sudo dnf install -y \
    gcc gcc-c++ make automake libtool \
    pcre2 pcre2-devel \
    zlib zlib-devel \
    libxml2 libxml2-devel \
    libxslt libxslt-devel \
    gd gd-devel \
    perl perl-devel perl-ExtUtils-Embed \
    libaio libaio-devel \
    brotli brotli-devel \
    wget git unzip cmake
```

> **Note**: On Oracle Linux 9/10, the `geoip` library is replaced by `geoipupdate` or `libmaxminddb` for GeoIP2.

---

## Step 1: Download NGINX and Modules

```bash
cd /usr/local/src

# NGINX source
wget http://nginx.org/download/nginx-1.26.2.tar.gz
tar -xzvf nginx-1.26.2.tar.gz

# Custom modules
git clone https://github.com/openresty/headers-more-nginx-module.git ngx_headers_more
git clone https://github.com/FRiCKLE/ngx_cache_purge.git ngx_cache_purge
git clone https://github.com/pagespeed/ngx_pagespeed.git ngx_pagespeed
git clone https://github.com/google/ngx_brotli.git ngx_brotli
git clone https://github.com/leev/ngx_http_geoip2_module.git ngx_http_geoip2_module
git clone https://github.com/vozlt/nginx-module-vts.git ngx_module_vts
git clone https://github.com/openresty/echo-nginx-module.git ngx_echo
```

> Optional: Download PSOL for Pagespeed:

```bash
cd ngx_pagespeed
wget https://dl.google.com/dl/page-speed/psol/1.13.35.2-x64.tar.gz
tar -xzvf 1.13.35.2-x64.tar.gz
```

---

## Step 2: Compile NGINX with Custom Modules

```bash
cd /usr/local/src/nginx-1.26.2

./configure \
  --prefix=/etc/nginx \
  --sbin-path=/usr/sbin/nginx \
  --conf-path=/etc/nginx/nginx.conf \
  --pid-path=/etc/nginx/run/nginx.pid \
  --lock-path=/var/lock/nginx.lock \
  --modules-path=/usr/lib/nginx/modules \
  --http-log-path=/var/log/nginx/access.log \
  --error-log-path=/var/log/nginx/error.log \
  --http-client-body-temp-path=/var/lib/nginx/body \
  --http-proxy-temp-path=/var/lib/nginx/proxy \
  --with-compat \
  --with-http_ssl_module \
  --with-http_v2_module \
  --with-http_perl_module=dynamic \
  --with-http_stub_status_module \
  --with-http_realip_module \
  --with-http_gzip_static_module \
  --with-threads \
  --with-stream \
  --with-stream_ssl_module \
  --add-module=/usr/local/src/ngx_headers_more \
  --add-module=/usr/local/src/ngx_cache_purge \
  --add-module=/usr/local/src/ngx_pagespeed \
  --add-module=/usr/local/src/ngx_brotli \
  --add-module=/usr/local/src/ngx_http_geoip2_module \
  --add-module=/usr/local/src/ngx_module_vts \
  --add-module=/usr/local/src/ngx_echo

# Build and install
make -j$(nproc)
make install
```

---

## Step 3: Configure Directories and Permissions

```bash
# Create user
useradd --system --no-create-home --shell /sbin/nologin nginx

# Logs and PID\mkdir -p /var/log/nginx /etc/nginx/run
chown -R nginx:nginx /var/log/nginx /etc/nginx/run

# Temp directories
mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy
chown -R nginx:nginx /var/lib/nginx
```

---

## Step 4: NGINX Configuration Example

```nginx
# /etc/nginx/nginx.conf
load_module /usr/lib/nginx/modules/ngx_http_perl_module.so;

user nginx;
worker_processes auto;
pid /etc/nginx/run/nginx.pid;

events {
    worker_connections 65535;
    use epoll;
    multi_accept on;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    server_tokens off;

    client_max_body_size 50m;
    client_body_temp_path /var/lib/nginx/body;
    proxy_temp_path /var/lib/nginx/proxy;

    gzip on;
    brotli on;

    include /etc/nginx/conf.d/*.conf;

    server {
        listen 80 default_server;
        server_name _;
        root /etc/nginx/html;
        index index.html index.htm;

        location / {
            try_files $uri $uri/ =404;
        }

        location /nginx_status {
            stub_status;
            allow 127.0.0.1;
            deny all;
        }
    }
}

stream {
    include /etc/nginx/stream.d/*.conf;
}
```

---

## Step 5: Systemd Service

```ini
# /etc/systemd/system/nginx.service
[Unit]
Description=NGINX
After=network.target

[Service]
Type=forking
ExecStartPre=/usr/sbin/nginx -t
ExecStart=/usr/sbin/nginx
ExecReload=/usr/sbin/nginx -s reload
ExecStop=/usr/sbin/nginx -s quit
PIDFile=/etc/nginx/run/nginx.pid
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Reload systemd and start NGINX:

```bash
systemctl daemon-reload
systemctl enable --now nginx
systemctl status nginx
```

---

## Step 6: Verify Installation

```bash
nginx -V   # Check compiled modules
nginx -t   # Check config syntax
systemctl status nginx
```

* Stub status: `curl http://127.0.0.1/nginx_status`
* Check dynamic modules: `ls /usr/lib/nginx/modules/`

---

## Notes

* Oracle Linux 9+ uses **C++20**, so some older modules may need `--std=c++11` for compatibility.
* GeoIP2 requires `libmaxminddb`.
* Pagespeed requires `PSOL` (precompiled).
* Only **one default_server** per IP:port is allowed.

This setup provides a **production-ready, custom NGINX build** with full module support, proper permissions, optimized workers, and dynamic Perl module support.
