A **production-ready step-by-step installation guide** for EL9 (RHEL 9, Oracle Linux 9, Rocky Linux 9, etc.) that covers **NGINX, MinIO, mc, and vsftpd 3.0.2**. I’ve written it in a way that can be used as a **documentation guide or deployment checklist**.

---

# Production Installation Guide for EL9

## Prerequisites

* OS: RHEL 9 / Oracle Linux 9 / Rocky Linux 9 (x86_64)
* Root or sudo access
* OpenSSL installed (`openssl` package)
* Firewall configured for required ports
* SELinux disabled or configured for MinIO/FTP

Check:

```bash
uname -a
uname -m
```

* Should be `x86_64` for this guide

---

## NGINX 1.24.0 Installation

1. Add official NGINX repository:

```bash
cat > /etc/yum.repos.d/nginx.repo <<EOF
[nginx-stable]
name=nginx stable repo
baseurl=https://nginx.org/packages/rhel/9/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF
```

2. Install specific version:

```bash
dnf install -y nginx-1.24.0-1.el9.ngx
```

3. Verify installation:

```bash
nginx -v
# nginx version: nginx/1.24.0
```

4. Optional: enable systemd service:

```bash
systemctl enable nginx
systemctl start nginx
systemctl status nginx
```

---

## MinIO & mc Installation

### 3.1 Download binaries

```bash
cd /usr/local/bin
wget https://github.com/minio/minio/releases/download/RELEASE.2020-02-27T00-23-05Z/minio
wget https://github.com/minio/mc/releases/download/RELEASE.2020-02-25T18-10-03Z/mc
```

### 3.2 Install binaries

```bash
chmod 755 minio mc
```

### 3.3 Verify versions

```bash
minio -v
# minio version RELEASE.2020-02-27T00-23-05Z

mc -v
# mc version RELEASE.2020-02-25T18-10-03Z
```

### 3.4 Optional: Create systemd service for MinIO

```bash
cat > /etc/systemd/system/minio.service <<EOF
[Unit]
Description=MinIO
After=network.target

[Service]
User=minio
Group=minio
ExecStart=/usr/local/bin/minio server /data
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable minio
systemctl start minio
systemctl status minio
```

> Ensure `/data` directory exists and `minio:minio` owns it.

---

## vsftpd 3.0.2 Installation

### 4.1 Install build dependencies

```bash
dnf install -y gcc make pam-devel openssl-devel libcap-devel wget
```

### 4.2 Download source and patch if needed

```bash
cd /usr/local/src
wget https://security.appspot.com/downloads/vsftpd-3.0.2.tar.gz
tar -xzf vsftpd-3.0.2.tar.gz
cd vsftpd-3.0.2

# Patch Makefile to remove -Werror if compiling fails
sed -i 's/-Werror//g' Makefile
make
```

### 4.3 Install binary

```bash
cp vsftpd /sbin/vsftpd
chmod 755 /sbin/vsftpd
```

### 4.4 Verify version

```bash
vsftpd -v
# vsftpd: version 3.0.2
```

### 4.5 Create production-ready config

```bash
cat > /etc/vsftpd/vsftpd.conf <<EOF
listen=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
chroot_local_user=YES
allow_writeable_chroot=YES
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/server.crt
rsa_private_key_file=/etc/ssl/private/server.key
ssl_enable=YES
EOF
```

### 4.6 Start vsftpd

```bash
/sbin/vsftpd /etc/vsftpd/vsftpd.conf
# or run in background
nohup /sbin/vsftpd /etc/vsftpd/vsftpd.conf &
```

### 4.7 Optional systemd unit

```bash
cat > /etc/systemd/system/vsftpd.service <<EOF
[Unit]
Description=vsftpd FTP daemon
After=network.target

[Service]
ExecStart=/sbin/vsftpd /etc/vsftpd/vsftpd.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vsftpd
systemctl start vsftpd
systemctl status vsftpd
```

---

## Verification

```bash
nginx -v
minio -v
mc -v
vsftpd -v
```

All outputs should exactly match your required versions:

* NGINX 1.24.0
* MinIO RELEASE.2020-02-27T00-23-05Z
* mc RELEASE.2020-02-25T18-10-03Z
* vsftpd 3.0.2

---

## Production Hardening Tips

* **Firewall:** Allow ports 80/443 (NGINX), 21 + passive FTP ports, 9000+ (MinIO)
* **TLS:** Ensure all services use SSL/TLS
* **Permissions:** Keep binaries 755, config files 600–644
* **Logs:** Monitor `/var/log/nginx/`, `/var/log/vsftpd.log`, MinIO logs
* **Backups:** Backup `/sbin/vsftpd`, `/usr/local/bin/minio`, configs, and data directories

---
