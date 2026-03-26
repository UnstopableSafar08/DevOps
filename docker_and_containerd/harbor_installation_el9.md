# Harbor Production Installation Guide — EL9 (RHEL / Rocky / AlmaLinux 9)

**Domain:** `harbor.sagarmalla.info.np`
**Server:** 4 vCPU / 8 GB RAM
**OS:** Enterprise Linux 9 (RHEL / Rocky / AlmaLinux)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Server Requirements](#2-server-requirements)
3. [System Limits (ulimits)](#3-system-limits-ulimits)
4. [Option 1 — Offline Installation](#4-option-1--offline-installation)
   - [1a. With SSL](#option-1a--offline-with-ssl)
   - [1b. Without SSL](#option-1b--offline-without-ssl)
5. [Option 2 — Online Installation](#5-option-2--online-installation)
   - [2a. With SSL](#option-2a--online-with-ssl)
   - [2b. Without SSL](#option-2b--online-without-ssl)
6. [Post-Installation](#6-post-installation)
7. [Verify Installation](#7-verify-installation)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

### Software Dependencies

| Component | Minimum Version | Notes |
|---|---|---|
| Docker Engine | 24.x or later | Must be CE or EE |
| Docker Compose (plugin) | v2.x | `docker compose` not `docker-compose` |
| OpenSSL | 1.1.1+ | For SSL cert generation |
| Python 3 | 3.6+ | Used by `./prepare` internally |

### Network Requirements

- Port `80` open (HTTP or redirect)
- Port `443` open (HTTPS)
- Port `4443` open (Harbor Notary, optional)
- DNS record pointing `harbor.sagarmalla.info.np` → server IP
- Outbound internet access (for online install only)

### SELinux

Harbor runs fine with SELinux in **enforcing** mode. Do not disable it — configure contexts instead.

```bash
# Verify SELinux mode
getenforce
```

---

## 2. Server Requirements

### Minimum vs Recommended (for 4 vCPU / 8 GB RAM)

| Resource | Minimum | Your Server | Notes |
|---|---|---|---|
| CPU | 2 vCPU | 4 vCPU | Sufficient for production |
| RAM | 4 GB | 8 GB | Sufficient for production |
| OS Disk (`/`) | 40 GB | 40+ GB | OS + Docker images |
| Data Disk | 100 GB+ | depends on usage | Harbor registry storage |
| Swap | 2 GB | 4 GB recommended | Prevents OOM under load |

### Disk Layout (Recommended)

```
/              40 GB   OS, Docker binaries
/var/lib/docker  50 GB   Docker layer cache
/data          200 GB+  Harbor registry data (separate volume preferred)
```

> Mount a dedicated disk at `/data` to keep registry data isolated from the OS.

### Add Swap (if not already present)

```bash
# Check existing swap
free -h

# Create 4GB swapfile
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Persist across reboots
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Tune swappiness for a server workload
echo 'vm.swappiness=10' >> /etc/sysctl.d/99-harbor.conf
sysctl -p /etc/sysctl.d/99-harbor.conf
```

---

## 3. System Limits (ulimits)

### Why This Matters

Harbor (specifically the registry and nginx containers) can open a large number of file descriptors and spawn many threads under concurrent push/pull load. Default EL9 limits are often too low for production.

### 3.1 — System-wide Limits (`/etc/security/limits.conf`)

```bash
cat >> /etc/security/limits.conf <<'EOF'

# Harbor production limits
*         soft    nofile      65536
*         hard    nofile      65536
*         soft    nproc       65536
*         hard    nproc       65536
*         soft    memlock     unlimited
*         hard    memlock     unlimited
root      soft    nofile      65536
root      hard    nofile      65536
root      soft    nproc       65536
root      hard    nproc       65536
EOF
```

### 3.2 — systemd Limits for Docker

```bash
mkdir -p /etc/systemd/system/docker.service.d

cat > /etc/systemd/system/docker.service.d/limits.conf <<'EOF'
[Service]
LimitNOFILE=1048576
LimitNPROC=1048576
LimitCORE=infinity
TasksMax=infinity
EOF

systemctl daemon-reload
systemctl restart docker
```

### 3.3 — Kernel Parameters (`sysctl`)

```bash
cat > /etc/sysctl.d/99-harbor.conf <<'EOF'
# File descriptor and connection limits
fs.file-max = 1048576
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512

# Network tuning
net.core.somaxconn = 32768
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.ip_local_port_range = 1024 65535

# Virtual memory
vm.swappiness = 10
vm.max_map_count = 262144
EOF

sysctl -p /etc/sysctl.d/99-harbor.conf
```

### 3.4 — Verify Limits Are Applied

```bash
# After restart, check effective limits on a running container
docker run --rm busybox sh -c "ulimit -n && ulimit -u"

# Check Docker daemon limits
cat /proc/$(pidof dockerd | awk '{print $1}')/limits
```

---

## 4. Option 1 — Offline Installation

Use this when the Harbor server has **no internet access**.

### Prepare on a Machine WITH Internet Access

```bash
# Download offline installer (example: Harbor v2.10.2)
HARBOR_VERSION=v2.10.2
wget https://github.com/goharbor/harbor/releases/download/${HARBOR_VERSION}/harbor-offline-installer-${HARBOR_VERSION}.tgz
wget https://github.com/goharbor/harbor/releases/download/${HARBOR_VERSION}/harbor-offline-installer-${HARBOR_VERSION}.tgz.asc

# Transfer to your EL9 server
scp harbor-offline-installer-${HARBOR_VERSION}.tgz root@<server-ip>:/opt/
```

### On the EL9 Server — Common Setup Steps

```bash
# Install Docker (must be done manually offline if no repo access)
# Alternatively pre-download RPMs and transfer them

# Enable and start Docker
systemctl enable --now docker

# Install Docker Compose plugin
DOCKER_COMPOSE_VERSION=v2.24.0
curl -SL https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

# Extract Harbor
cd /opt
tar xzvf harbor-offline-installer-*.tgz
cd harbor
```

---

### Option 1a — Offline WITH SSL

#### Step 1 — Generate SSL Certificate (Self-Signed)

```bash
mkdir -p /opt/harbor/cert
cd /opt/harbor/cert

DOMAIN=harbor.sagarmalla.info.np

# Generate CA key and cert
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -sha512 -days 3650 \
  -subj "/C=NP/ST=Bagmati/L=Patan/O=Harbor/CN=${DOMAIN}" \
  -key ca.key -out ca.crt

# Generate server key and CSR
openssl genrsa -out harbor.key 4096
openssl req -sha512 -new \
  -subj "/C=NP/ST=Bagmati/L=Patan/O=Harbor/CN=${DOMAIN}" \
  -key harbor.key -out harbor.csr

# Create v3 extension file with SAN
cat > v3.ext <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=${DOMAIN}
EOF

# Sign the server cert with the CA
openssl x509 -req -sha512 -days 365 \
  -extfile v3.ext \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -in harbor.csr -out harbor.crt

# Verify
openssl x509 -in harbor.crt -noout -dates
```

#### Step 2 — Configure `harbor.yml`

```bash
cp /opt/harbor/harbor.yml.tmpl /opt/harbor/harbor.yml
```

Edit `/opt/harbor/harbor.yml`:

```yaml
hostname: harbor.sagarmalla.info.np

http:
  port: 80

https:
  port: 443
  certificate: /opt/harbor/cert/harbor.crt
  private_key: /opt/harbor/cert/harbor.key

harbor_admin_password: <strong-password>

database:
  password: <strong-db-password>
  max_idle_conns: 50
  max_open_conns: 100

data_volume: /data

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200m
    location: /var/log/harbor

jobservice:
  max_job_workers: 10

notification:
  webhook_job_max_retry: 3

chart:
  absolute_url: disabled
```

#### Step 3 — Run Prepare and Install

```bash
cd /opt/harbor
./prepare
./install.sh
```

---

### Option 1b — Offline WITHOUT SSL

#### Step 1 — Configure `harbor.yml`

```bash
cp /opt/harbor/harbor.yml.tmpl /opt/harbor/harbor.yml
```

Edit `/opt/harbor/harbor.yml`:

```yaml
hostname: harbor.sagarmalla.info.np

http:
  port: 80

# Comment out or remove the entire https block:
# https:
#   port: 443
#   certificate: ...
#   private_key: ...

harbor_admin_password: <strong-password>

database:
  password: <strong-db-password>
  max_idle_conns: 50
  max_open_conns: 100

data_volume: /data

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200m
    location: /var/log/harbor
```

#### Step 2 — Run Prepare and Install

```bash
cd /opt/harbor
./prepare
./install.sh
```

> **Note:** Docker clients must mark this registry as insecure. See [Post-Installation](#6-post-installation).

---

## 5. Option 2 — Online Installation

Use this when the Harbor server has internet access.

### Common Setup — Install Docker and Docker Compose

```bash
# Install required packages
dnf install -y yum-utils curl wget

# Add Docker CE repo
yum-config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# Install Docker
dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker
systemctl enable --now docker
docker version
docker compose version
```

### Download Harbor Online Installer

```bash
HARBOR_VERSION=v2.10.2
wget https://github.com/goharbor/harbor/releases/download/${HARBOR_VERSION}/harbor-online-installer-${HARBOR_VERSION}.tgz
tar xzvf harbor-online-installer-${HARBOR_VERSION}.tgz -C /opt/
cd /opt/harbor
```

---

### Option 2a — Online WITH SSL

#### Using a Real Certificate (Recommended for Production)

If you have a certificate from a trusted CA (Let's Encrypt, ZeroSSL, your org's CA):

```bash
mkdir -p /opt/harbor/cert

# Copy your cert files
cp /path/to/fullchain.pem /opt/harbor/cert/harbor.crt
cp /path/to/privkey.pem   /opt/harbor/cert/harbor.key

chmod 644 /opt/harbor/cert/harbor.crt
chmod 600 /opt/harbor/cert/harbor.key
```

#### Using Let's Encrypt (Certbot)

```bash
dnf install -y certbot

# Obtain cert (port 80 must be free and DNS must resolve)
certbot certonly --standalone \
  -d harbor.sagarmalla.info.np \
  --agree-tos --no-eff-email -m admin@sagarmalla.info.np

# Symlink into harbor cert dir
mkdir -p /opt/harbor/cert
ln -sf /etc/letsencrypt/live/harbor.sagarmalla.info.np/fullchain.pem /opt/harbor/cert/harbor.crt
ln -sf /etc/letsencrypt/live/harbor.sagarmalla.info.np/privkey.pem   /opt/harbor/cert/harbor.key
```

#### Auto-Renew Hook for Let's Encrypt

```bash
cat > /etc/letsencrypt/renewal-hooks/deploy/harbor-reload.sh <<'EOF'
#!/bin/bash
cd /opt/harbor
docker compose down
./prepare
docker compose up -d
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/harbor-reload.sh
```

#### Configure `harbor.yml`

```yaml
hostname: harbor.sagarmalla.info.np

http:
  port: 80

https:
  port: 443
  certificate: /opt/harbor/cert/harbor.crt
  private_key: /opt/harbor/cert/harbor.key

harbor_admin_password: <strong-password>

database:
  password: <strong-db-password>
  max_idle_conns: 50
  max_open_conns: 100

data_volume: /data

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200m
    location: /var/log/harbor

jobservice:
  max_job_workers: 10
```

#### Run Install

```bash
cd /opt/harbor
./prepare
./install.sh
```

---

### Option 2b — Online WITHOUT SSL

#### Configure `harbor.yml`

```yaml
hostname: harbor.sagarmalla.info.np

http:
  port: 80

# https block must be fully commented out
# https:
#   port: 443
#   certificate: ...
#   private_key: ...

harbor_admin_password: <strong-password>

database:
  password: <strong-db-password>
  max_idle_conns: 50
  max_open_conns: 100

data_volume: /data

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200m
    location: /var/log/harbor
```

#### Run Install

```bash
cd /opt/harbor
./prepare
./install.sh
```

> **Note:** Docker clients must mark this registry as insecure. See [Post-Installation](#6-post-installation).

---

## 6. Post-Installation

### Firewall Rules

```bash
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
firewall-cmd --list-ports
```

### Configure Docker Clients — SSL (Self-Signed or Private CA)

On every node that will push/pull from Harbor:

```bash
HARBOR_HOST=harbor.sagarmalla.info.np

# Copy CA cert
mkdir -p /etc/docker/certs.d/${HARBOR_HOST}
cp /opt/harbor/cert/ca.crt /etc/docker/certs.d/${HARBOR_HOST}/ca.crt

systemctl reload docker
```

### Configure Docker Clients — No SSL (Insecure Registry)

On every node that will push/pull from Harbor:

```bash
cat > /etc/docker/daemon.json <<EOF
{
  "insecure-registries": ["harbor.sagarmalla.info.np"]
}
EOF

systemctl restart docker
```

### Enable Harbor to Start on Boot

```bash
# Create systemd service for Harbor
cat > /etc/systemd/system/harbor.service <<'EOF'
[Unit]
Description=Harbor Container Registry
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/harbor
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable harbor
```

---

## 7. Verify Installation

```bash
# All containers should be Up (not Exiting)
cd /opt/harbor
docker compose ps

# Check Harbor health endpoint
curl -k https://harbor.sagarmalla.info.np/api/v2.0/ping

# Check SSL cert expiry
echo | openssl s_client -connect harbor.sagarmalla.info.np:443 2>/dev/null \
  | openssl x509 -noout -dates

# Test docker login
docker login harbor.sagarmalla.info.np
```

Expected `docker compose ps` output — all services `Up`:

```
NAME                      STATUS
harbor-core               Up
harbor-db                 Up
harbor-jobservice         Up
harbor-log                Up
harbor-portal             Up
harbor-redis              Up
harbor-registryctl        Up
nginx                     Up
registry                  Up
```

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `nginx` container keeps restarting | Bad cert path or key mismatch | Check `harbor.yml` paths; verify cert/key modulus match |
| `harbor-core` exits immediately | Wrong DB password or DB not ready | Check `docker compose logs harbor-core` |
| `docker login` fails with 401 | Wrong admin password | Reset via UI or `docker exec harbor-core` |
| `docker pull` fails with cert error | Client doesn't trust CA | Copy `ca.crt` to `/etc/docker/certs.d/<host>/` |
| `docker pull` fails with "http: server gave HTTP response" | Client not configured as insecure | Add to `daemon.json` insecure-registries |
| Portal not reachable on 443 | Firewall blocking port | `firewall-cmd --add-port=443/tcp --permanent` |
| `/data` fills up | No garbage collection | Schedule GC in Harbor UI → Administration → Garbage Collection |

### Cert / Key Mismatch Check

```bash
openssl x509 -noout -modulus -in /opt/harbor/cert/harbor.crt | md5sum
openssl rsa  -noout -modulus -in /opt/harbor/cert/harbor.key | md5sum
# Both hashes must be identical
```

### View Logs

```bash
# All Harbor services
docker compose -f /opt/harbor/docker-compose.yml logs -f

# Specific service
docker compose -f /opt/harbor/docker-compose.yml logs -f nginx
docker compose -f /opt/harbor/docker-compose.yml logs -f harbor-core
```

---

## Quick Reference — Which Option to Choose

| Scenario | Recommended Option |
|---|---|
| Air-gapped / no internet, production with HTTPS | Option 1a |
| Air-gapped / no internet, internal only no HTTPS | Option 1b |
| Internet access, production with trusted cert | Option 2a (Let's Encrypt) |
| Internet access, dev/staging internal only | Option 2b |

---

*Last updated: 2026-03-26*
