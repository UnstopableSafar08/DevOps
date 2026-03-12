## Full Observability Stack Setup

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│  App Nodes (x4)                                             │
│  ├── Promtail     → ships logs    → Loki                   │
│  └── Node Exporter → ships metrics → Prometheus            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Log/Monitoring Server (10.13.222.26)                       │
│  ├── Loki      (log storage, 72hr retention)                │
│  ├── Prometheus (metrics storage)                           │
│  └── Grafana   (unified dashboards + alerts)                │
└─────────────────────────────────────────────────────────────┘
```

---

# Observability Setup and Configurations Guide

## Table of Contents

- [Overview: ELK Stack vs Grafana + Loki + Promtail](#overview)
- [Architecture Design](#architecture-design)
- [Prerequisites](#prerequisites)
- [Step 1: Grafana + Loki + Promtail Stack Setup](#step-1-grafana--loki--promtail-stack-setup)
  - [1.1 Install Loki](#11-install-loki)
  - [1.2 Install Grafana](#12-install-grafana)
  - [1.3 Install Promtail on Application Nodes](#13-install-promtail-on-application-nodes)
- [Step 2: Prometheus Setup for Server Monitoring](#step-2-prometheus-setup-for-server-monitoring)
  - [2.1 Install Prometheus](#21-install-prometheus)
  - [2.2 Install Node Exporter](#22-install-node-exporter)
- [Step 3: Grafana Dashboard Configuration](#step-3-grafana-dashboard-configuration)
  - [3.1 Add Data Sources](#31-add-data-sources)
  - [3.2 Import Pre-built Dashboards](#32-import-pre-built-dashboards)
  - [3.3 Create Custom Dashboards](#33-create-custom-dashboards)
- [Services Port Reference](#services-port-reference)
- [Useful Queries](#useful-queries)

---

## Overview

### ELK Stack vs Grafana + Loki + Promtail

| Factor | ELK Stack | Grafana + Loki + Promtail |
|---|---|---|
| RAM on log server | 4 to 8 GB minimum | 512 MB to 2 GB |
| CPU usage | High (full-text indexing) | Very low (label-based indexing) |
| Disk usage | High (indexes all fields) | 3 to 5x less than ELK |
| Log agent on app nodes | Filebeat (~50 MB) | Promtail (~30 MB) |
| Full-text search | Excellent | Limited (label and regex based) |
| Log parsing and transforms | Very powerful (Grok, ingest pipelines) | Basic (LogQL pipeline stages) |
| Alerting | Built-in via Kibana | Via Grafana alerting |
| Dashboards | Kibana | Grafana (supports metrics and logs together) |
| Setup complexity | High | Low |
| Maintenance overhead | High | Low |
| Metrics and logs in one UI | Requires separate tools | Native in Grafana |
| Learning curve | Steep | Gentle |
| Cost (self-hosted) | Free (basic tier) | 100% Free |

---

## Architecture Design

```
+--------------------------------------------------+
|  Application Nodes                               |
|                                                  |
|  Node 1: 10.10.10.10                            |
|  Node 2: 10.10.10.11                            |
|  Node 3: 10.10.10.12                            |
|  Node 4: 10.10.10.13                            |
|                                                  |
|  Each node runs:                                 |
|    Promtail  -----> ships logs -----> Loki       |
|    Node Exporter -> ships metrics -> Prometheus  |
+--------------------------------------------------+
                          |
                          v
+--------------------------------------------------+
|  Observability Server (localhost)                |
|                                                  |
|    Loki       :3100   (log storage, 72h retain)  |
|    Prometheus :9090   (metrics storage, 30d)     |
|    Grafana    :3000   (unified dashboards)       |
|    Node Exporter :9100 (local server metrics)    |
+--------------------------------------------------+
```

---

## Prerequisites

### Observability Server (localhost)

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Oracle Linux 8+ / RHEL 8+ / Ubuntu 20.04+ | Oracle Linux 9 |
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB | 50 GB |
| Network | Port 3000, 3100, 9090, 9100 open | Same |

### Application Nodes (10.10.10.10 to 10.10.10.13)

| Requirement | Details |
|---|---|
| OS | Any Linux distribution |
| Port outbound | 3100 (to Loki), 9090 (scrape inbound on 9100) |
| Firewall | Allow 9100/tcp inbound (for Prometheus scraping) |
| Promtail access | Read permission on log directories |

### Packages Required on All Nodes

```bash
sudo dnf install -y wget curl tar unzip
```

---

## Step 1: Grafana + Loki + Promtail Stack Setup

### 1.1 Install Loki

Run all commands in this section on the **observability server (localhost)**.

**Create user and directories**

```bash
sudo useradd --no-create-home --shell /bin/false loki
sudo mkdir -p /etc/loki /var/lib/loki /var/log/loki
```

**Download and install Loki binary**

```bash
cd /tmp
wget https://github.com/grafana/loki/releases/download/v3.4.2/loki-linux-amd64.zip
unzip loki-linux-amd64.zip
sudo mv loki-linux-amd64 /usr/local/bin/loki
sudo chmod +x /usr/local/bin/loki
sudo chown loki:loki /usr/local/bin/loki
```

**Create Loki configuration with 72-hour log retention**

```bash
sudo tee /etc/loki/loki.yml > /dev/null <<'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn

common:
  instance_addr: 127.0.0.1
  path_prefix: /var/lib/loki
  storage:
    filesystem:
      chunks_directory: /var/lib/loki/chunks
      rules_directory: /var/lib/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 72h
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32
  max_streams_per_user: 10000
  max_entries_limit_per_query: 50000

compactor:
  working_directory: /var/lib/loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
  delete_request_store: filesystem

ingester:
  chunk_idle_period: 1h
  max_chunk_age: 2h
  chunk_target_size: 1048576
  chunk_retain_period: 30s

storage_config:
  tsdb_shipper:
    active_index_directory: /var/lib/loki/tsdb-index
    cache_location: /var/lib/loki/tsdb-cache
    cache_ttl: 24h

chunk_store_config:
  chunk_cache_config:
    embedded_cache:
      enabled: true
      max_size_mb: 200

table_manager:
  retention_deletes_enabled: true
  retention_period: 72h
EOF
```

**Set permissions**

```bash
sudo chown -R loki:loki /etc/loki /var/lib/loki /var/log/loki
```

**Create Loki systemd service**

```bash
sudo tee /etc/systemd/system/loki.service > /dev/null <<'EOF'
[Unit]
Description=Loki Log Aggregation System
After=network.target

[Service]
User=loki
Group=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/loki.yml
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=loki

[Install]
WantedBy=multi-user.target
EOF
```

**Start and enable Loki**

```bash
sudo systemctl daemon-reload
sudo systemctl start loki
sudo systemctl enable loki
sudo systemctl status loki
```

**Verify Loki is ready**

```bash
curl -s http://localhost:3100/ready
# Expected output: ready
```

---

### 1.2 Install Grafana

Run all commands in this section on the **observability server (localhost)**.

**Add Grafana repository**

```bash
sudo tee /etc/yum.repos.d/grafana.repo > /dev/null <<'EOF'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
```

**Install and start Grafana**

```bash
sudo dnf install -y grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
sudo systemctl status grafana-server
```

**Open firewall ports on the observability server**

```bash
sudo firewall-cmd --permanent --add-port=3000/tcp   # Grafana
sudo firewall-cmd --permanent --add-port=3100/tcp   # Loki
sudo firewall-cmd --permanent --add-port=9090/tcp   # Prometheus
sudo firewall-cmd --permanent --add-port=9100/tcp   # Node Exporter
sudo firewall-cmd --reload
```

Grafana is now accessible at: `http://localhost:3000`

Default credentials: `admin / admin` (you will be prompted to change on first login)

---

### 1.3 Install Promtail on Application Nodes

Run all commands in this section on **each application node** (10.10.10.10, 10.10.10.11, 10.10.10.12, 10.10.10.13).

**Create user and directories**

```bash
sudo useradd --no-create-home --shell /bin/false promtail
sudo mkdir -p /etc/promtail /var/lib/promtail
```

**Download and install Promtail binary**

```bash
cd /tmp
wget https://github.com/grafana/loki/releases/download/v3.4.2/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
sudo mv promtail-linux-amd64 /usr/local/bin/promtail
sudo chmod +x /usr/local/bin/promtail
```

**Create Promtail configuration**

Replace `<HOSTNAME>` with the actual hostname of the node being configured, for example `app-node-01`.

```bash
sudo tee /etc/promtail/promtail.yml > /dev/null <<'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:

  - job_name: gds-admin
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          app: gds-admin
          host: <HOSTNAME>
          env: production
          __path__: /var/apps/gds-admin/gds-admin/storage/logs/*.log
    pipeline_stages:
      - multiline:
          firstline: '^\[\d{4}-\d{2}-\d{2}'
          max_wait_time: 3s
      - regex:
          expression: '^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (?P<env>\w+)\.(?P<level>\w+): (?P<message>.*)'
      - labels:
          level:
          env:
      - timestamp:
          source: timestamp
          format: "2006-01-02 15:04:05"

  - job_name: gds-api
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          app: gds-api
          host: <HOSTNAME>
          env: production
          __path__: /var/apps/gds-api/gds-api/storage/logs/*.log
    pipeline_stages:
      - multiline:
          firstline: '^\[\d{4}-\d{2}-\d{2}'
          max_wait_time: 3s
      - regex:
          expression: '^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (?P<env>\w+)\.(?P<level>\w+): (?P<message>.*)'
      - labels:
          level:
          env:
      - timestamp:
          source: timestamp
          format: "2006-01-02 15:04:05"

  - job_name: gds-web
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          app: gds-web
          host: <HOSTNAME>
          env: production
          __path__: /var/apps/gds-web/gds-web/storage/logs/*.log
    pipeline_stages:
      - multiline:
          firstline: '^\[\d{4}-\d{2}-\d{2}'
          max_wait_time: 3s
      - regex:
          expression: '^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (?P<env>\w+)\.(?P<level>\w+): (?P<message>.*)'
      - labels:
          level:
          env:
      - timestamp:
          source: timestamp
          format: "2006-01-02 15:04:05"

  - job_name: system
    static_configs:
      - targets: ["localhost"]
        labels:
          job: system
          host: <HOSTNAME>
          env: production
          __path__: /var/log/{messages,secure,cron}
    pipeline_stages:
      - regex:
          expression: '(?P<level>error|warn|info|debug|ERROR|WARN|INFO|DEBUG)'
      - labels:
          level:
EOF
```

**Fix log file read permissions**

```bash
# Add promtail to adm group
sudo usermod -aG adm promtail
sudo usermod -aG systemd-journal promtail

# Grant read access to system log files via ACL
sudo dnf install -y acl
sudo setfacl -m u:promtail:r /var/log/messages
sudo setfacl -m u:promtail:r /var/log/secure
sudo setfacl -m u:promtail:r /var/log/cron

# Grant read access to application log directories
sudo setfacl -R -m u:promtail:r /var/apps/gds-admin/gds-admin/storage/logs/
sudo setfacl -R -m u:promtail:r /var/apps/gds-api/gds-api/storage/logs/
sudo setfacl -R -m u:promtail:r /var/apps/gds-web/gds-web/storage/logs/

# Set ownership
sudo chown -R promtail:promtail /etc/promtail /var/lib/promtail
```

**Create Promtail systemd service**

```bash
sudo tee /etc/systemd/system/promtail.service > /dev/null <<'EOF'
[Unit]
Description=Promtail Log Shipper
After=network.target

[Service]
User=promtail
Group=promtail
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/promtail.yml
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Start and enable Promtail**

```bash
sudo systemctl daemon-reload
sudo systemctl start promtail
sudo systemctl enable promtail
sudo systemctl status promtail
```

**Open firewall for Promtail metrics endpoint**

```bash
sudo firewall-cmd --permanent --add-port=9080/tcp
sudo firewall-cmd --reload
```

**Verify Promtail is shipping logs to Loki**

```bash
# Check Promtail targets
curl -s http://localhost:9080/targets

# Verify Loki has received logs (run on observability server)
curl -s "http://localhost:3100/loki/api/v1/labels" | python3 -m json.tool
```

---

## Step 2: Prometheus Setup for Server Monitoring

### 2.1 Install Prometheus

Run all commands in this section on the **observability server (localhost)**.

**Create user and directories**

```bash
sudo useradd --no-create-home --shell /bin/false prometheus
sudo mkdir -p /etc/prometheus /var/lib/prometheus
```

**Download and install Prometheus**

```bash
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v3.2.1/prometheus-3.2.1.linux-amd64.tar.gz
tar xf prometheus-3.2.1.linux-amd64.tar.gz
cd prometheus-3.2.1.linux-amd64
sudo mv prometheus promtool /usr/local/bin/
sudo chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
```

**Create Prometheus configuration**

Replace the IP addresses in the targets section with your actual application node IPs.

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

scrape_configs:

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node-observability-server"
    static_configs:
      - targets: ["localhost:9100"]
        labels:
          instance: "observability-server"
          env: "production"

  - job_name: "node-app-01"
    static_configs:
      - targets: ["10.10.10.10:9100"]
        labels:
          instance: "app-node-01"
          env: "production"
          role: "app"

  - job_name: "node-app-02"
    static_configs:
      - targets: ["10.10.10.11:9100"]
        labels:
          instance: "app-node-02"
          env: "production"
          role: "app"

  - job_name: "node-app-03"
    static_configs:
      - targets: ["10.10.10.12:9100"]
        labels:
          instance: "app-node-03"
          env: "production"
          role: "app"

  - job_name: "node-app-04"
    static_configs:
      - targets: ["10.10.10.13:9100"]
        labels:
          instance: "app-node-04"
          env: "production"
          role: "app"

  - job_name: "loki"
    static_configs:
      - targets: ["localhost:3100"]
EOF

sudo chown prometheus:prometheus /etc/prometheus/prometheus.yml
```

**Create Prometheus systemd service**

```bash
sudo tee /etc/systemd/system/prometheus.service > /dev/null <<'EOF'
[Unit]
Description=Prometheus Monitoring
After=network.target

[Service]
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=30d \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-lifecycle
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

**Start and enable Prometheus**

```bash
sudo systemctl daemon-reload
sudo systemctl start prometheus
sudo systemctl enable prometheus
sudo systemctl status prometheus
```

**Verify Prometheus is running**

```bash
curl -s http://localhost:9090/-/healthy
# Expected output: Prometheus Server is Healthy.
```

---

### 2.2 Install Node Exporter

Node Exporter must be installed on the **observability server** and on **all four application nodes**.

**Create user**

```bash
sudo useradd --no-create-home --shell /bin/false node_exporter
```

**Download and install Node Exporter**

```bash
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.9.0/node_exporter-1.9.0.linux-amd64.tar.gz
tar xf node_exporter-1.9.0.linux-amd64.tar.gz
sudo mv node_exporter-1.9.0.linux-amd64/node_exporter /usr/local/bin/
sudo chown node_exporter:node_exporter /usr/local/bin/node_exporter
```

**Create Node Exporter systemd service**

```bash
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
```

**Start and enable Node Exporter**

```bash
sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter
sudo systemctl status node_exporter
```

**Open firewall port on application nodes (allows Prometheus to scrape)**

```bash
sudo firewall-cmd --permanent --add-port=9100/tcp
sudo firewall-cmd --reload
```

**Verify Node Exporter is exposing metrics**

```bash
curl -s http://localhost:9100/metrics | head -20
```

**Verify all targets are up in Prometheus (run on observability server)**

```bash
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep '"health"'
# All targets should show: "health": "up"
```

---

## Step 3: Grafana Dashboard Configuration

### 3.1 Add Data Sources

Open Grafana at `http://localhost:3000` and log in with your admin credentials.

**Add Loki as a data source**

1. Go to Connections > Data Sources > Add new data source
2. Select Loki
3. Set the following values:

```
Name:  Loki
URL:   http://localhost:3100
```

4. Click Save and Test. The result should show: Data source connected and labels found.

**Add Prometheus as a data source**

1. Go to Connections > Data Sources > Add new data source
2. Select Prometheus
3. Set the following values:

```
Name:           Prometheus
Prometheus URL: http://localhost:9090
```

4. Click Save and Test. The result should show: Successfully queried the Prometheus API.

---

### 3.2 Import Pre-built Dashboards

Grafana has a library of community dashboards that can be imported using a dashboard ID.

1. Go to Dashboards > New > Import
2. Enter the dashboard ID in the "Import via grafana.com" field
3. Click Load, select the appropriate data source, then click Import

| Dashboard | ID | Data Source |
|---|---|---|
| Node Exporter Full (server metrics) | 1860 | Prometheus |
| Loki Dashboard (log exploration) | 13639 | Loki |
| Prometheus Stats | 3662 | Prometheus |

---

### 3.3 Create Custom Dashboards

**Create a new dashboard**

1. Go to Dashboards > New > New Dashboard
2. Click Add visualization
3. Select the data source (Loki or Prometheus)
4. Enter your query and configure the panel

**Recommended panels for a PHP application log dashboard**

Panel 1 - Log volume over time (Loki data source, Time series visualization)

```logql
sum by (app) (count_over_time({job="php-application"}[5m]))
```

Panel 2 - Error count per application (Loki data source, Stat visualization)

```logql
sum by (app) (count_over_time({job="php-application", level="ERROR"}[5m]))
```

Panel 3 - Raw log stream (Loki data source, Logs visualization)

```logql
{job="php-application"} | level="ERROR"
```

Panel 4 - Log stream for a specific application (Loki data source, Logs visualization)

```logql
{job="php-application", app="gds-api"}
```

**Recommended panels for a server metrics dashboard**

Panel 5 - CPU usage per node (Prometheus data source, Time series visualization)

```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

Panel 6 - Memory usage per node (Prometheus data source, Gauge visualization)

```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

Panel 7 - Disk usage per node (Prometheus data source, Gauge visualization)

```promql
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)
```

Panel 8 - Network traffic per node (Prometheus data source, Time series visualization)

```promql
rate(node_network_receive_bytes_total[5m])
rate(node_network_transmit_bytes_total[5m])
```

**Save the dashboard**

1. Click the Save icon (top right of the dashboard)
2. Give the dashboard a name, for example: PHP Application Observability
3. Choose a folder and click Save

---

## Services Port Reference

| Service | Server | Port | URL |
|---|---|---|---|
| Grafana | Observability Server | 3000 | http://localhost:3000 |
| Loki | Observability Server | 3100 | http://localhost:3100 |
| Prometheus | Observability Server | 9090 | http://localhost:9090 |
| Node Exporter | All Servers | 9100 | http://localhost:9100/metrics |
| Promtail | App Nodes | 9080 | http://10.10.10.10:9080/targets |

---

## Useful Queries

### LogQL Queries (Loki)

```logql
# All PHP application errors across all nodes
{job="php-application"} | level="ERROR"

# Errors for a specific application
{job="php-application", app="gds-api"} | level="ERROR"

# Laravel exceptions
{job="php-application"} |= "Exception"

# SSH authentication failures from system logs
{job="system"} |= "Failed password"

# Error count per application over the last 5 minutes
sum by (app) (count_over_time({job="php-application", level="ERROR"}[5m]))

# Logs from a specific node
{job="php-application", host="app-node-01"}
```

### PromQL Queries (Prometheus)

```promql
# CPU usage percentage per instance
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percentage per instance
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage percentage on root partition
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# Inbound network traffic per instance
rate(node_network_receive_bytes_total[5m])

# System load average (1 minute)
node_load1

# Number of running processes
node_procs_running
```

### Verify Log Retention (72 hours)

```bash
# Check Loki retention config
curl -s http://localhost:3100/config | grep retention

# Check compactor status
curl -s http://localhost:3100/loki/api/v1/status/buildinfo | python3 -m json.tool

# Manually verify no logs older than 72 hours exist
curl -s -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="php-application"}' \
  --data-urlencode "start=$(date -d '4 days ago' +%s)000000000" \
  --data-urlencode "end=$(date -d '73 hours ago' +%s)000000000" \
  | python3 -m json.tool
```
