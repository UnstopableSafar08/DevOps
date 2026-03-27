# Grafana Alloy Installation and Configuration Guide

## Platform: EL9 (RHEL / Rocky / AlmaLinux)

### Exporters Covered

- Node Exporter (built-in)
- Process Exporter (built-in)
- Nginx Exporter (external)
- HAProxy Exporter (external)
- Redis Exporter (external)
- Kafka Exporter (external)
- JMX Exporter (external, Java agent)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Online Installation](#2-online-installation)
3. [Offline Installation](#3-offline-installation)
4. [Exporter Setup](#4-exporter-setup)
   - [Nginx](#41-nginx-exporter)
   - [HAProxy](#42-haproxy-exporter)
   - [Redis](#43-redis-exporter)
   - [Kafka](#44-kafka-exporter)
   - [JMX](#45-jmx-exporter)
5. [Alloy Configuration](#5-alloy-configuration)
6. [Systemd Hardening](#6-systemd-hardening)
7. [Verification](#7-verification)

---

## 1. Architecture Overview

```
+---------------------+       +---------------------+       +----------+
|   Target Server     |       |   Alloy (agent)      |       |Prometheus|
|                     |       |                      |       |          |
| node_exporter ------+------>| prometheus.scrape    |       |          |
| process_exporter ---+------>| prometheus.scrape    +------>| :9090    |
| nginx_exporter -----+------>| prometheus.scrape    | write |          |
| haproxy_exporter ---+------>| prometheus.scrape    |       |          |
| redis_exporter -----+------>| prometheus.scrape    |       +----------+
| kafka_exporter -----+------>| prometheus.scrape    |
| jmx_exporter -------+------>| prometheus.scrape    |
+---------------------+       +----------------------+
```

Alloy runs on the same server as the exporters. It scrapes all exporter endpoints and ships metrics to Prometheus via `remote_write`.

Built-in exporters (node, process) are embedded inside Alloy and do not require separate binaries. External exporters (nginx, haproxy, redis, kafka, jmx) are standalone binaries managed by systemd.

---

## 2. Online Installation

### 2.1 Add Grafana Repository

```bash
cat <<EOF > /etc/yum.repos.d/grafana.repo
[grafana]
name=Grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
```

### 2.2 Install Alloy

```bash
dnf install -y alloy
```

### 2.3 Enable and Start

```bash
systemctl enable --now alloy
systemctl status alloy
```

### 2.4 Default Paths

| Path | Purpose |
|------|---------|
| `/etc/alloy/config.alloy` | Main configuration file |
| `/var/lib/alloy` | WAL and data directory |
| `/usr/bin/alloy` | Binary |
| `journalctl -u alloy -f` | Logs |

---

## 3. Offline Installation

Use this method when the target server has no internet access.

### 3.1 Download RPM on an Internet-Connected Machine

```bash
# Method A: Download via dnf
dnf download --resolve alloy \
  --repofrompath=grafana,https://rpm.grafana.com \
  --repo=grafana

# Method B: Download directly from GitHub releases
VERSION="1.7.1"
curl -Lo alloy-${VERSION}-1.amd64.rpm \
  https://github.com/grafana/alloy/releases/download/v${VERSION}/alloy-${VERSION}-1.amd64.rpm
```

Verify the file is a valid RPM:

```bash
file alloy-*.rpm
# Expected: RPM v3.0 bin i386/x86_64
```

### 3.2 Transfer to Target Server

```bash
scp alloy-*.rpm root@<server-ip>:/tmp/
```

### 3.3 Install on Target Server

```bash
dnf localinstall -y /tmp/alloy-*.rpm

# If dnf is unavailable
rpm -ivh /tmp/alloy-*.rpm
```

### 3.4 Verify Installation

```bash
alloy --version
systemctl enable --now alloy
systemctl status alloy
```

### 3.5 Downloading All External Exporter Binaries (Offline Prep)

Run the following on an internet-connected machine to prepare all binaries for transfer:

```bash
mkdir -p ~/alloy-exporters && cd ~/alloy-exporters

# Nginx exporter
curl -Lo nginx-prometheus-exporter.tar.gz \
  https://github.com/nginx/nginx-prometheus-exporter/releases/download/v1.3.0/nginx-prometheus-exporter_1.3.0_linux_amd64.tar.gz

# HAProxy exporter
curl -Lo haproxy_exporter \
  https://github.com/prometheus/haproxy_exporter/releases/download/v0.15.0/haproxy_exporter-0.15.0.linux-amd64.tar.gz

# Redis exporter
curl -Lo redis_exporter.tar.gz \
  https://github.com/oliver006/redis_exporter/releases/download/v1.62.0/redis_exporter-v1.62.0.linux-amd64.tar.gz

# Kafka exporter
curl -Lo kafka_exporter.tar.gz \
  https://github.com/danielqsj/kafka_exporter/releases/download/v1.7.0/kafka_exporter-1.7.0.linux-amd64.tar.gz

# JMX exporter (Java agent JAR)
curl -Lo jmx_prometheus_javaagent.jar \
  https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar
```

Extract and verify each binary:

```bash
tar -xzf nginx-prometheus-exporter.tar.gz
tar -xzf haproxy_exporter*.tar.gz
tar -xzf redis_exporter.tar.gz
tar -xzf kafka_exporter.tar.gz

for bin in nginx-prometheus-exporter haproxy_exporter redis_exporter kafka_exporter; do
  file $bin
done
# Each must output: ELF 64-bit LSB executable
```

Transfer all binaries to the target server:

```bash
scp nginx-prometheus-exporter \
    haproxy_exporter \
    redis_exporter \
    kafka_exporter \
    jmx_prometheus_javaagent.jar \
    root@<server-ip>:/usr/local/bin/
```

---

## 4. Exporter Setup

### 4.1 Nginx Exporter

Nginx must expose the `stub_status` page before the exporter can scrape it.

**Enable stub_status in nginx:**

```bash
cat <<EOF > /etc/nginx/conf.d/stub_status.conf
server {
    listen 127.0.0.1:80;
    server_name localhost;

    location /stub_status {
        stub_status;
        allow 127.0.0.1;
        deny all;
    }
}
EOF

nginx -t && systemctl reload nginx
```

Verify:

```bash
curl http://127.0.0.1:80/stub_status
```

**Install and configure the exporter:**

```bash
chmod +x /usr/local/bin/nginx-prometheus-exporter
```

```ini
# /etc/systemd/system/nginx-prometheus-exporter.service
[Unit]
Description=Nginx Prometheus Exporter
After=nginx.service

[Service]
ExecStart=/usr/local/bin/nginx-prometheus-exporter \
  --nginx.scrape-uri=http://127.0.0.1:80/stub_status \
  --web.listen-address=:9113
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now nginx-prometheus-exporter
curl -s http://127.0.0.1:9113/metrics | grep nginx_up
```

---

### 4.2 HAProxy Exporter

HAProxy must expose its stats socket or HTTP stats page.

**Enable HAProxy stats in haproxy.cfg:**

```
# /etc/haproxy/haproxy.cfg
frontend stats
    bind 127.0.0.1:8404
    stats enable
    stats uri /stats
    stats refresh 10s
    no log
```

```bash
systemctl reload haproxy
curl http://127.0.0.1:8404/stats
```

**Install and configure the exporter:**

```bash
chmod +x /usr/local/bin/haproxy_exporter
```

```ini
# /etc/systemd/system/haproxy-exporter.service
[Unit]
Description=HAProxy Exporter
After=haproxy.service

[Service]
ExecStart=/usr/local/bin/haproxy_exporter \
  --haproxy.scrape-uri=http://127.0.0.1:8404/stats?stats;csv \
  --web.listen-address=:9101
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now haproxy-exporter
curl -s http://127.0.0.1:9101/metrics | grep haproxy_up
```

---

### 4.3 Redis Exporter

**Install and configure the exporter:**

```bash
chmod +x /usr/local/bin/redis_exporter
```

```ini
# /etc/systemd/system/redis-exporter.service
[Unit]
Description=Redis Exporter
After=redis.service

[Service]
ExecStart=/usr/local/bin/redis_exporter \
  --redis.addr=redis://127.0.0.1:6379 \
  --web.listen-address=:9121
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

If Redis requires a password:

```ini
Environment=REDIS_PASSWORD=your_redis_password
```

```bash
systemctl daemon-reload
systemctl enable --now redis-exporter
curl -s http://127.0.0.1:9121/metrics | grep redis_up
```

---

### 4.4 Kafka Exporter

**Install and configure the exporter:**

```bash
chmod +x /usr/local/bin/kafka_exporter
```

```ini
# /etc/systemd/system/kafka-exporter.service
[Unit]
Description=Kafka Exporter
After=network.target

[Service]
ExecStart=/usr/local/bin/kafka_exporter \
  --kafka.server=127.0.0.1:9092 \
  --web.listen-address=:9308
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

For multiple Kafka brokers:

```ini
ExecStart=/usr/local/bin/kafka_exporter \
  --kafka.server=10.68.2.10:9092 \
  --kafka.server=10.68.2.11:9092 \
  --kafka.server=10.68.2.12:9092 \
  --web.listen-address=:9308
```

```bash
systemctl daemon-reload
systemctl enable --now kafka-exporter
curl -s http://127.0.0.1:9308/metrics | grep kafka_brokers
```

---

### 4.5 JMX Exporter

JMX exporter runs as a Java agent attached to the JVM process (Tomcat, Kafka, etc.). It does not run as a standalone service.

**Place the JAR:**

```bash
mkdir -p /opt/jmx-exporter
mv /usr/local/bin/jmx_prometheus_javaagent.jar /opt/jmx-exporter/
```

**Create JMX config file:**

```bash
cat <<EOF > /opt/jmx-exporter/config.yaml
lowercaseOutputName: true
lowercaseOutputLabelNames: true
rules:
  - pattern: ".*"
EOF
```

**Attach to Tomcat:**

Edit the Tomcat service or `setenv.sh`:

```bash
# /opt/tomcat/bin/setenv.sh
CATALINA_OPTS="$CATALINA_OPTS -javaagent:/opt/jmx-exporter/jmx_prometheus_javaagent.jar=9404:/opt/jmx-exporter/config.yaml"
```

Or via systemd override:

```bash
systemctl edit tomcat
```

```ini
[Service]
Environment="JAVA_OPTS=-javaagent:/opt/jmx-exporter/jmx_prometheus_javaagent.jar=9404:/opt/jmx-exporter/config.yaml"
```

```bash
systemctl daemon-reload
systemctl restart tomcat
curl -s http://127.0.0.1:9404/metrics | grep jvm_memory
```

**JMX config for Kafka (if Kafka runs as JVM):**

```bash
# In Kafka's systemd unit or kafka-server-start.sh
export KAFKA_OPTS="-javaagent:/opt/jmx-exporter/jmx_prometheus_javaagent.jar=9405:/opt/jmx-exporter/kafka-config.yaml"
```

---

## 5. Alloy Configuration

Place this file at `/etc/alloy/config.alloy`. Replace `<PROMETHEUS_IP>` and `<PROMETHEUS_PORT>` with your actual values.

```alloy
// /etc/alloy/config.alloy

// ── Node Exporter (built-in) ──────────────────────────────────────────────────
prometheus.exporter.unix "node" {
  enable_collectors = [
    "cpu",
    "diskstats",
    "filesystem",
    "loadavg",
    "meminfo",
    "netdev",
    "netstat",
    "stat",
    "time",
    "uname",
    "vmstat",
  ]
}

prometheus.scrape "node" {
  targets         = prometheus.exporter.unix.node.targets
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "node"
  scrape_interval = "15s"
}

// ── Process Exporter (built-in) ───────────────────────────────────────────────
prometheus.exporter.process "procs" {
  matcher {
    name    = "nginx"
    cmdline = ["nginx: master process"]
  }
  matcher {
    name    = "haproxy"
    cmdline = ["haproxy"]
  }
  matcher {
    name    = "redis"
    cmdline = ["redis-server"]
  }
  matcher {
    name    = "kafka"
    cmdline = ["kafka.Kafka"]
  }
  matcher {
    name    = "tomcat"
    cmdline = ["org.apache.catalina.startup.Bootstrap"]
  }
}

prometheus.scrape "process" {
  targets         = prometheus.exporter.process.procs.targets
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "process"
  scrape_interval = "15s"
}

// ── Nginx (nginx-prometheus-exporter on :9113) ────────────────────────────────
prometheus.scrape "nginx" {
  targets = [
    {"__address__" = "127.0.0.1:9113"},
  ]
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "nginx"
  scrape_interval = "15s"
}

// ── HAProxy (haproxy-exporter on :9101) ───────────────────────────────────────
prometheus.scrape "haproxy" {
  targets = [
    {"__address__" = "127.0.0.1:9101"},
  ]
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "haproxy"
  scrape_interval = "15s"
}

// ── Redis (redis-exporter on :9121) ───────────────────────────────────────────
prometheus.scrape "redis" {
  targets = [
    {"__address__" = "127.0.0.1:9121"},
  ]
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "redis"
  scrape_interval = "15s"
}

// ── Kafka (kafka-exporter on :9308) ───────────────────────────────────────────
prometheus.scrape "kafka" {
  targets = [
    {"__address__" = "127.0.0.1:9308"},
  ]
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "kafka"
  scrape_interval = "30s"
}

// ── JMX Exporter (Tomcat on :9404, Kafka JVM on :9405) ───────────────────────
prometheus.scrape "jmx" {
  targets = [
    {"__address__" = "127.0.0.1:9404", "app" = "tomcat"},
    {"__address__" = "127.0.0.1:9405", "app" = "kafka-jvm"},
  ]
  forward_to      = [prometheus.remote_write.prometheus.receiver]
  job_name        = "jmx"
  scrape_interval = "30s"
}

// ── Remote Write → Prometheus ─────────────────────────────────────────────────
prometheus.remote_write "prometheus" {
  endpoint {
    url = "http://<PROMETHEUS_IP>:<PROMETHEUS_PORT>/api/v1/write"
  }

  external_labels = {
    instance = "<SERVER_IP>",
    host     = "<HOSTNAME>",
    env      = "production",
  }

  queue_config {
    capacity             = 10000
    max_samples_per_send = 2000
    batch_send_deadline  = "5s"
  }
}
```

**Apply the config:**

```bash
# Validate syntax
alloy fmt /etc/alloy/config.alloy

# Restart
systemctl restart alloy
journalctl -u alloy -f
```

---

## 6. Systemd Hardening

### 6.1 Restrict Alloy UI to Localhost

```bash
systemctl edit alloy
```

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/alloy run /etc/alloy/config.alloy \
  --server.http.listen-addr=127.0.0.1:12345 \
  --disable-reporting
```

```bash
systemctl daemon-reload
systemctl restart alloy
```

### 6.2 Enable Prometheus remote_write Receiver

On the Prometheus server:

```bash
systemctl edit prometheus
```

```ini
[Service]
ExecStart=
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-remote-write-receiver
```

```bash
systemctl daemon-reload
systemctl restart prometheus
```

### 6.3 Firewall — Allow Alloy to Reach Prometheus

```bash
# On the Prometheus server — allow inbound from Alloy host
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="<ALLOY_SERVER_IP>/32" port port="9090" protocol="tcp" accept'
firewall-cmd --reload
```

---

## 7. Verification

### 7.1 Check All Exporter Ports

```bash
ss -tlnp | grep -E '9113|9101|9121|9308|9404|9405|9253'
```

### 7.2 Verify Each Exporter Metric Endpoint

```bash
curl -s http://127.0.0.1:9113/metrics | grep nginx_up
curl -s http://127.0.0.1:9101/metrics | grep haproxy_up
curl -s http://127.0.0.1:9121/metrics | grep redis_up
curl -s http://127.0.0.1:9308/metrics | grep kafka_brokers
curl -s http://127.0.0.1:9404/metrics | grep jvm_memory
```

### 7.3 Check Alloy is Ready

```bash
curl -s http://127.0.0.1:12345/-/ready
```

### 7.4 Confirm Metrics Arrived in Prometheus

```bash
PROM="http://<PROMETHEUS_IP>:<PROMETHEUS_PORT>"

curl -s "${PROM}/api/v1/query?query=nginx_up"          | jq '.data.result[0].value'
curl -s "${PROM}/api/v1/query?query=haproxy_up"        | jq '.data.result[0].value'
curl -s "${PROM}/api/v1/query?query=redis_up"          | jq '.data.result[0].value'
curl -s "${PROM}/api/v1/query?query=kafka_brokers"     | jq '.data.result[0].value'
curl -s "${PROM}/api/v1/query?query=jvm_memory_bytes_used" | jq '.data.result[0].value'
curl -s "${PROM}/api/v1/query?query=node_cpu_seconds_total" | jq '.data.result[0].metric'
```

### 7.5 Exporter and Alloy Service Status

```bash
systemctl status alloy \
  nginx-prometheus-exporter \
  haproxy-exporter \
  redis-exporter \
  kafka-exporter
```

---

## Exporter Port Reference

| Exporter | Port | Type |
|----------|------|------|
| Node Exporter | built-in | Alloy built-in |
| Process Exporter | built-in | Alloy built-in |
| Nginx Exporter | 9113 | External binary |
| HAProxy Exporter | 9101 | External binary |
| Redis Exporter | 9121 | External binary |
| Kafka Exporter | 9308 | External binary |
| JMX Exporter (Tomcat) | 9404 | Java agent |
| JMX Exporter (Kafka JVM) | 9405 | Java agent |

---

## Grafana Dashboard IDs

| Dashboard | Grafana ID |
|-----------|-----------|
| Node Exporter Full | 1860 |
| Nginx | 12708 |
| HAProxy | 367 |
| Redis | 763 |
| Kafka | 7589 |
| JMX / Java | 8563 |

Import via: Grafana -> Dashboards -> Import -> Enter ID -> Load
