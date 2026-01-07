# NGINX "More" Custom Build for Oracle Linux 9/10

This repository provides a **production-ready, custom NGINX build** with **dynamic and static modules** for advanced HTTP, stream, caching, and performance features on **Oracle Linux 9/10**. The setup mirrors production-ready configurations used in high-performance environments.

## Table of Contents

* [Supported Modules](#supported-modules)
* [Prerequisites](#prerequisites)
* [Step 1: Download NGINX and Modules](#step-1-download-nginx-and-modules)
* [Step 2: Compile NGINX with Custom Modules](#step-2-compile-nginx-with-custom-modules)
* [Step 3: Configure Directories and Permissions](#step-3-configure-directories-and-permissions)
* [Step 4: NGINX Configuration Example](#step-4-nginx-configuration-example)
* [Step 5: Systemd Service](#step-5-systemd-service)
* [Step 6: Verify Installation](#step-6-verify-installation)
* [Uninstall NGINX](#uninstall-nginx)
* [Notes](#notes)

## Supported Modules

* **Dynamic Modules**: `ngx_http_perl_module`
* **Custom Modules**:

  * ngx_headers_more
  * ngx_cache_purge
  * ngx_pagespeed
  * ngx_brotli
  * ngx_http_geoip2
  * ngx_module_vts
  * ngx_echo
* **Built-in Modules**: SSL, HTTP/2, stub_status, proxy, gzip, stream, mail, etc.

## Prerequisites

```bash
sudo dnf update -y
sudo dnf install -y gcc gcc-c++ make automake libtool \
pcre2 pcre2-devel zlib zlib-devel libxml2 libxml2-devel \
libxslt libxslt-devel gd gd-devel perl perl-devel \
perl-ExtUtils-Embed libaio libaio-devel brotli \
brotli-devel wget git unzip cmake
```

## Step 1: Download NGINX and Modules

```bash
cd /usr/local/src
wget http://nginx.org/download/nginx-1.26.2.tar.gz
tar -xzvf nginx-1.26.2.tar.gz

git clone https://github.com/openresty/headers-more-nginx-module.git ngx_headers_more
git clone https://github.com/FRiCKLE/ngx_cache_purge.git ngx_cache_purge
git clone https://github.com/pagespeed/ngx_pagespeed.git ngx_pagespeed
git clone https://github.com/google/ngx_brotli.git ngx_brotli
git clone https://github.com/leev/ngx_http_geoip2_module.git ngx_http_geoip2_module
git clone https://github.com/vozlt/nginx-module-vts.git ngx_module_vts
git clone https://github.com/openresty/echo-nginx-module.git ngx_echo
```

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

make -j$(nproc)
make install
```

## Step 3: Configure Directories and Permissions

```bash
useradd --system --no-create-home --shell /sbin/nologin nginx
mkdir -p /var/log/nginx /etc/nginx/run /var/lib/nginx/body /var/lib/nginx/proxy
chown -R nginx:nginx /var/log/nginx /etc/nginx/run /var/lib/nginx
```

## Step 4: NGINX Configuration Example

```nginx
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

## Step 5: Systemd Service

```ini
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

```bash
systemctl daemon-reload
systemctl enable --now nginx
systemctl status nginx
```

## Step 6: Verify Installation

```bash
nginx -V      # Check compiled modules
nginx -t      # Check config syntax
systemctl status nginx
```

## Uninstall NGINX

```bash
systemctl stop nginx
systemctl disable nginx
rm -rf /etc/nginx /usr/sbin/nginx /usr/lib/nginx/modules /var/log/nginx /var/lib/nginx /var/lock/nginx.lock /etc/systemd/system/nginx.service
systemctl daemon-reload
```

## Notes

* Only **one `default_server` per IP:port** is allowed.
* Pagespeed requires `PSOL` precompiled library.
* GeoIP2 requires `libmaxminddb`.
* Ensure proper **permissions** for `/var/log/nginx`, `/etc/nginx/run`, `/var/lib/nginx`.
