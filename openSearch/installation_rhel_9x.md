A production-ready OpenSearch installation and configuration guide for RHEL 9.x, tailored exactly to your server constraints and operational preferences.

# OpenSearch Production Installation Guide

**RHEL 9.6 | Single-Node | Resource-Constrained Production**

---

## 0. Target Architecture

**Server Profile**

| Item      | Value                  |
| --------- | ---------------------- |
| OS        | RHEL 9.6               |
| RAM       | 8 GB                   |
| CPU       | 4 cores (limit: 3)     |
| Disk      | /var – 20 GB           |
| JVM Heap  | 4 GB                   |
| Node Type | Single-node production |

---

## 1. Pre-Installation Validation

### 1.1 Verify OS and Kernel

```bash
cat /etc/redhat-release
uname -r
```

**Why**

* OpenSearch requires modern kernel memory management and mmap support.
* Kernel 5.x+ avoids Lucene mmap instability.

---

### 1.2 Verify Available Resources

```bash
free -h
lscpu
df -h /var
```

**Why**

* Confirms RAM for heap sizing.
* Confirms disk headroom (OpenSearch becomes unstable >85%).

---

## 2. Operating System Hardening (Mandatory)

---

## 2.1 Disable Transparent Huge Pages (THP)

### 2.1.1 Create systemd service

```bash
vi /etc/systemd/system/disable-thp.service
```

```ini
[Unit]
Description=Disable Transparent Huge Pages
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=multi-user.target
```

### 2.1.2 Enable and start

```bash
systemctl daemon-reexec
systemctl enable disable-thp
systemctl start disable-thp
```

**Why (Production-Critical)**
THP causes:

* Latency spikes
* JVM GC stalls
* Index merge slowness

Lucene explicitly **does not support THP**.

---

## 2.2 Configure User Limits

```bash
vi /etc/security/limits.d/opensearch.conf
```

```conf
opensearch soft nofile 65536
opensearch hard nofile 65536
opensearch soft nproc 4096
opensearch hard nproc 4096
opensearch soft memlock unlimited
opensearch hard memlock unlimited
```

**Why**

* OpenSearch opens thousands of segment files.
* Prevents FD exhaustion and thread starvation.
* `memlock` ensures heap never swaps.

---

## 2.3 Kernel Tuning

```bash
vi /etc/sysctl.d/99-opensearch.conf
```

```conf
vm.max_map_count=262144
fs.file-max=2097152
net.core.somaxconn=65535
```

Apply:

```bash
sysctl --system
```

**Why**

* Lucene uses mmap extensively.
* Prevents startup failure and data corruption.
* Improves concurrent connection handling.

---

## 3. Disk Layout Preparation

```bash
mkdir -p /var/lib/opensearch
mkdir -p /var/log/opensearch
```

**Why**

* Separates data and logs from OS.
* Prevents root filesystem exhaustion.
* Enables targeted disk alerts.

---

## 4. Install OpenSearch (RPM)

---

### 4.1 Import GPG Key

```bash
rpm --import https://artifacts.opensearch.org/publickeys/opensearch.pgp
```

**Why**

* Ensures package integrity.
* Mandatory for production compliance.

---

### 4.2 Create Yum Repository

```bash
vi /etc/yum.repos.d/opensearch.repo
```

```ini
[opensearch]
name=OpenSearch Repository
baseurl=https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/yum
gpgcheck=1
gpgkey=https://artifacts.opensearch.org/publickeys/opensearch.pgp
enabled=1
autorefresh=1
type=rpm-md
```

---

### 4.3 Install Package

```bash
dnf clean all
dnf install -y opensearch
```

**Why**

* RPM installs:

  * systemd service
  * dedicated opensearch user
  * secure directory permissions

---

## 5. JVM Configuration (Memory Discipline)

```bash
vi /etc/opensearch/jvm.options
```

```text
-Xms4g
-Xmx4g
```

**Why**

* Fixed heap avoids resizing GC pauses.
* Leaves memory for OS cache.
* Prevents OOM kills.

---

## 6. CPU and Systemd Controls

```bash
mkdir -p /etc/systemd/system/opensearch.service.d
vi /etc/systemd/system/opensearch.service.d/override.conf
```

```ini
[Service]
CPUQuota=300%
LimitNOFILE=65536
LimitMEMLOCK=infinity
```

Reload:

```bash
systemctl daemon-reload
```

**Why**

* Enforces CPU isolation.
* Prevents OpenSearch from starving the OS.
* Guarantees predictable performance.

---

## 7. Core OpenSearch Configuration

```bash
vi /etc/opensearch/opensearch.yml
```

```yaml
cluster.name: prod-opensearch
node.name: node-1

path.data: /var/lib/opensearch
path.logs: /var/log/opensearch

network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

discovery.type: single-node

bootstrap.memory_lock: true

cluster.routing.allocation.disk.threshold_enabled: true
cluster.routing.allocation.disk.watermark.low: 70%
cluster.routing.allocation.disk.watermark.high: 85%
cluster.routing.allocation.disk.watermark.flood_stage: 95%

indices.fielddata.cache.size: 20%
indices.query.bool.max_clause_count: 4096
```

**Why**

* Ensures cluster stability.
* Protects disk from exhaustion.
* Prevents runaway queries.

---

## 8. Permissions Fix

```bash
chown -R opensearch:opensearch /var/lib/opensearch
chown -R opensearch:opensearch /var/log/opensearch
```

**Why**

* Prevents startup failure.
* Required for secure systemd execution.

---

## 9. Security Initialization

```bash
/usr/share/opensearch/plugins/opensearch-security/tools/install_demo_configuration.sh
```

Set admin password:

```bash
export OPENSEARCH_INITIAL_ADMIN_PASSWORD='StrongPasswordHere'
```

**Why**

* Enables TLS, authentication, RBAC.
* Protects REST API from abuse.

---

## 10. Start and Enable Service

```bash
systemctl enable opensearch
systemctl start opensearch
```

---

## 11. Post-Installation Validation

### 11.1 Service Status

```bash
systemctl status opensearch
```

---

### 11.2 Cluster Health

```bash
curl -k -u admin https://localhost:9200/_cluster/health?pretty
```

Expected:

```json
"status" : "green"
```

---

## 12. Production Readiness Checklist

✔ THP disabled
✔ Kernel tuned
✔ JVM heap fixed
✔ Disk watermarks enforced
✔ Security enabled
✔ CPU & memory bounded
✔ Data isolated on /var

---

## 13. Operational Warnings (Very Important)

* **20 GB disk is extremely tight**
* Configure **Index State Management** immediately
* Snapshot frequently
* Monitor disk daily
* Never exceed **85% usage**

---
