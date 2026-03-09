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

# PART 1 — LOG/MONITORING SERVER SETUP

## Step 1: Install Dependencies

```bash
# On log/monitoring server
sudo dnf install -y wget curl tar
```

---

## Step 2: Install Loki

```bash
# Create user and directories
sudo useradd --no-create-home --shell /bin/false loki
sudo mkdir -p /etc/loki /var/lib/loki /var/log/loki

# Download Loki
cd /tmp
wget https://github.com/grafana/loki/releases/download/v3.4.2/loki-linux-amd64.zip
unzip loki-linux-amd64.zip
sudo mv loki-linux-amd64 /usr/local/bin/loki
sudo chmod +x /usr/local/bin/loki
sudo chown loki:loki /usr/local/bin/loki
```

### Create Loki Config with 72hr Retention

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

ruler:
  alertmanager_url: http://localhost:9093

# ==================== 72 HOUR RETENTION ====================
limits_config:
  retention_period: 72h          # global 72hr retention
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32
  max_streams_per_user: 10000
  max_entries_limit_per_query: 50000

compactor:
  working_directory: /var/lib/loki/compactor
  compaction_interval: 10m
  retention_enabled: true        # must be true for retention to work
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

```bash
# Fix permissions
sudo chown -R loki:loki /etc/loki /var/lib/loki /var/log/loki
```

### Create Loki Systemd Service

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

```bash
sudo systemctl daemon-reload
sudo systemctl start loki
sudo systemctl enable loki
sudo systemctl status loki

# Verify Loki is ready
curl -s http://localhost:3100/ready
# Expected: ready
```

---

## Step 3: Install Prometheus

```bash
# Create user and directories
sudo useradd --no-create-home --shell /bin/false prometheus
sudo mkdir -p /etc/prometheus /var/lib/prometheus

# Download Prometheus
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v3.2.1/prometheus-3.2.1.linux-amd64.tar.gz
tar xf prometheus-3.2.1.linux-amd64.tar.gz
cd prometheus-3.2.1.linux-amd64
sudo mv prometheus promtool /usr/local/bin/
sudo mv consoles console_libraries /etc/prometheus/
sudo chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
```

### Create Prometheus Config

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files: []

scrape_configs:

  # Prometheus self-monitoring
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  # Log/Monitoring Server itself
  - job_name: "node-log-server"
    static_configs:
      - targets: ["localhost:9100"]
        labels:
          instance: "abc-elk-stack"
          env: "production"

  # App Node 1 — replace IPs with your actual app server IPs
  - job_name: "node-airlines-04"
    static_configs:
      - targets: ["<APP_NODE_1_IP>:9100"]
        labels:
          instance: "airlines-04"
          env: "production"
          role: "app"

  # App Node 2
  - job_name: "node-app-02"
    static_configs:
      - targets: ["<APP_NODE_2_IP>:9100"]
        labels:
          instance: "app-node-02"
          env: "production"
          role: "app"

  # App Node 3
  - job_name: "node-app-03"
    static_configs:
      - targets: ["<APP_NODE_3_IP>:9100"]
        labels:
          instance: "app-node-03"
          env: "production"
          role: "app"

  # App Node 4
  - job_name: "node-app-04"
    static_configs:
      - targets: ["<APP_NODE_4_IP>:9100"]
        labels:
          instance: "app-node-04"
          env: "production"
          role: "app"

  # Loki metrics
  - job_name: "loki"
    static_configs:
      - targets: ["localhost:3100"]
EOF
```

```bash
sudo chown prometheus:prometheus /etc/prometheus/prometheus.yml
```

### Create Prometheus Systemd Service

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

```bash
sudo systemctl daemon-reload
sudo systemctl start prometheus
sudo systemctl enable prometheus
sudo systemctl status prometheus

# Verify
curl -s http://localhost:9090/-/healthy
# Expected: Prometheus Server is Healthy.
```

---

## Step 4: Install Node Exporter on Log Server

```bash
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.9.0/node_exporter-1.9.0.linux-amd64.tar.gz
tar xf node_exporter-1.9.0.linux-amd64.tar.gz
sudo mv node_exporter-1.9.0.linux-amd64/node_exporter /usr/local/bin/
sudo useradd --no-create-home --shell /bin/false node_exporter

sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter
```

---

## Step 5: Install Grafana

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

sudo dnf install -y grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
sudo systemctl status grafana-server
```

### Open Firewall on Log Server

```bash
sudo firewall-cmd --permanent --add-port=3000/tcp   # Grafana
sudo firewall-cmd --permanent --add-port=3100/tcp   # Loki
sudo firewall-cmd --permanent --add-port=9090/tcp   # Prometheus
sudo firewall-cmd --permanent --add-port=9100/tcp   # Node Exporter
sudo firewall-cmd --reload
```

---

# PART 2 — APP NODES SETUP (Run on ALL 4 nodes)

## Step 6: Install Node Exporter on Each App Node

```bash
# Run on EACH app node
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.9.0/node_exporter-1.9.0.linux-amd64.tar.gz
tar xf node_exporter-1.9.0.linux-amd64.tar.gz
sudo mv node_exporter-1.9.0.linux-amd64/node_exporter /usr/local/bin/
sudo useradd --no-create-home --shell /bin/false node_exporter

sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter

# Open firewall for Prometheus scraping
sudo firewall-cmd --permanent --add-port=9100/tcp
sudo firewall-cmd --reload
```

---

## Step 7: Install Promtail on Each App Node

```bash
# Run on EACH app node
cd /tmp
wget https://github.com/grafana/loki/releases/download/v3.4.2/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
sudo mv promtail-linux-amd64 /usr/local/bin/promtail
sudo chmod +x /usr/local/bin/promtail
sudo useradd --no-create-home --shell /bin/false promtail
sudo mkdir -p /etc/promtail /var/lib/promtail
```

### Promtail Config for App Node (airlines-04 example)

```bash
# Adjust hostname and app paths per node
sudo tee /etc/promtail/promtail.yml > /dev/null <<'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml   # tracks read position

clients:
  - url: http://10.13.222.26:3100/loki/api/v1/push   # Loki server

scrape_configs:

  # ── gds-admin logs ──────────────────────────────────
  - job_name: gds-admin
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          app: gds-admin
          host: airlines-04          # change per node
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

  # ── gds-api logs ─────────────────────────────────────
  - job_name: gds-api
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          app: gds-api
          host: airlines-04
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

  # ── gds-web logs ─────────────────────────────────────
  - job_name: gds-web
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          app: gds-web
          host: airlines-04
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

  # ── system logs ──────────────────────────────────────
  - job_name: system
    static_configs:
      - targets: ["localhost"]
        labels:
          job: system
          host: airlines-04
          env: production
          __path__: /var/log/{messages,secure,cron}
    pipeline_stages:
      - regex:
          expression: '(?P<level>error|warn|info|debug|ERROR|WARN|INFO|DEBUG)'
      - labels:
          level:
EOF
```

```bash
# Fix permissions — promtail needs to read log files
sudo usermod -aG $(stat -c '%G' /var/apps/gds-api/gds-api/storage/logs) promtail

# Fix ownership
sudo chown -R promtail:promtail /etc/promtail /var/lib/promtail

# Open firewall
sudo firewall-cmd --permanent --add-port=9080/tcp
sudo firewall-cmd --reload
```

### Create Promtail Systemd Service

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

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start promtail
sudo systemctl enable promtail
sudo systemctl status promtail
```

---

# PART 3 — GRAFANA CONFIGURATION

## Step 8: Configure Grafana Data Sources

Open `http://10.13.222.26:3000` → Login: `admin / admin`

### Add Loki Data Source:
```
Connections → Data Sources → Add new
Type: Loki
URL:  http://localhost:3100
Name: Loki
→ Save & Test  ✅
```

### Add Prometheus Data Source:
```
Connections → Data Sources → Add new
Type: Prometheus
URL:  http://localhost:9090
Name: Prometheus
→ Save & Test  ✅
```

---

## Step 9: Import Pre-built Dashboards

Go to **Dashboards → Import** and use these dashboard IDs:

```
Node Exporter Full:      1860    ← server CPU/RAM/Disk/Network
Loki Dashboard:          13639   ← log exploration
Prometheus Stats:        3662    ← prometheus self-monitoring
```

---

## Step 10: Verify Everything is Working

```bash
# On log server — check all services
sudo systemctl status loki prometheus grafana-server node_exporter

# Check Loki is receiving logs
curl -s "http://localhost:3100/loki/api/v1/labels" | python3 -m json.tool

# Check Prometheus targets are UP
curl -s "http://localhost:9090/api/v1/targets" | python3 -m json.tool | grep '"health"'

# Check retention config
curl -s http://localhost:3100/config | grep retention
```

---

## Step 11: Useful LogQL Queries in Grafana

Once data flows, use these in **Grafana → Explore → Loki:**

```logql
# All PHP errors across all apps
{job="php-application"} |= "ERROR"

# Specific app errors only
{job="php-application", app="gds-api"} |= "ERROR"

# Laravel exceptions
{job="php-application"} |= "Exception"

# Filter by log level label
{job="php-application", level="ERROR"}

# SSH login attempts (system logs)
{job="system"} |= "Failed password"

# Count errors per app (metrics from logs)
sum by (app) (count_over_time({job="php-application"} |= "ERROR" [5m]))
```

---

## Services Port Summary

| Service | Port | URL |
|---|---|---|
| Grafana | 3000 | `http://10.13.222.26:3000` |
| Loki | 3100 | `http://10.13.222.26:3100` |
| Prometheus | 9090 | `http://10.13.222.26:9090` |
| Node Exporter | 9100 | `http://<any-node>:9100` |
| Promtail | 9080 | `http://<app-node>:9080` |

---

## 72-Hour Retention Summary

```
Loki config:
├── limits_config.retention_period: 72h  ✅
├── compactor.retention_enabled: true    ✅
└── table_manager.retention_period: 72h  ✅

Effect:
├── Logs older than 72 hours → auto deleted
├── Disk usage stays bounded
└── No manual cleanup needed
```
