## Tool Purpose Explanation

**Promtail - Log Collector**

Promtail acts as a shipping agent on each server. It reads log files from applications (Tomcat, PHP) and sends them to a central location. Think of it as a mail carrier picking up letters from individual houses and delivering them to a central post office.

Why needed: Without it, logs stay scattered across 50+ servers making troubleshooting nearly impossible.

---

**Loki - Log Storage and Query Engine**

Loki is the central warehouse that stores all logs sent by Promtail. It indexes logs efficiently and allows fast searching through millions of log lines. Unlike traditional databases, it doesn't index the content of logs but uses labels (like tags) to organize them.

Why needed: Provides a single place to store and search logs from all servers. Handles high volume with minimal resource usage. The 2-day retention policy is configured here.

---

**Prometheus - Metrics Collection and Monitoring**

Prometheus collects numerical metrics from servers like CPU usage, memory consumption, disk space, and application performance. It stores time-series data and can trigger alerts when thresholds are breached.

Why needed: While Loki handles text logs, Prometheus tracks server health and performance numbers. Together they give complete visibility - logs show "what happened" and metrics show "how the system is performing".

---

**Grafana - Visualization Dashboard**

Grafana is the user interface where teams view logs and metrics. It connects to both Loki and Prometheus, allowing users to create dashboards with graphs, charts, and log viewers. The RBAC implementation here controls who can see which module's data.

Why needed: Provides a single glass pane for all teams. DevOps can see everything, while developers see only their module logs. No need to SSH into servers or run command-line queries.

---

**Combined Workflow**

Application generates logs → Promtail ships logs → Loki stores logs → Grafana displays logs

Server generates metrics → Prometheus collects metrics → Grafana displays metrics

Result: Teams troubleshoot issues, monitor application health, and analyze patterns from a web browser without touching production servers directly.


## Architecture Workflow

```
┌────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER (50+ Servers)            │
│  ┌──────────────┐  ┌──────────────┐       ┌──────────────┐     │
│  │ Module-1     │  │ Module-2     │  ...  │ Module-10    │     │
│  │ (Tomcat/PHP) │  │ (Tomcat/PHP) │       │ (Tomcat/PHP) │     │
│  │  + Promtail  │  │  + Promtail  │       │  + Promtail  │     │
│  │  + Node Exp  │  │  + Node Exp  │       │  + Node Exp  │     │
│  └──────┬───────┘  └──────┬───────┘       └──────┬───────┘     │
│         │                  │                       │           │
└─────────┼──────────────────┼───────────────────────┼───────────┘
          │                  │                       │
          │ (HTTP Push)      │                       │
          ▼                  ▼                       ▼
┌────────────────────────────────────────────────────────────────┐
│                    AGGREGATION LAYER                           │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │   Loki Cluster (HA)        │  │  Prometheus (HA)         │  │
│  │  - Distributor (LB)        │  │  - Metrics Collection    │  │
│  │  - Ingester                │  │  - Alerting              │  │
│  │  - Querier                 │  │                          │  │
│  │  - Query Frontend          │  │                          │  │
│  └────────┬───────────────────┘  └───────┬──────────────────┘  │
│           │                              │                     │
│           ▼                              │                     │
│  ┌────────────────────┐                  │                     │
│  │  Object Storage    │                  │                     │
│  │  (MinIO/NFS)       │                  │                     │
│  │  - 2 day retention │                  │                     │
│  └────────────────────┘                  │                     │
└──────────────────────────────────────────┼─────────────────────┘
                                           │
          ┌────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Grafana (HA Optional)                                   │   │
│  │  - Loki Data Source                                      │   │
│  │  - Prometheus Data Source                                │   │
│  │  - RBAC: Teams (DevOps, SRE, Dev) → Module Permissions   │   │
│  │  - Dashboards: module_name → node_xx filters             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Server Requirements

**Core Infrastructure Servers:**

- **Loki Cluster**: 3 servers (HA setup)
  - CPU: 8 cores
  - RAM: 16GB
  - Disk: 200GB SSD (local state)
  - Role: Distributor, Ingester, Querier

- **Object Storage (MinIO)**: 2 servers (HA)
  - CPU: 4 cores
  - RAM: 8GB
  - Disk: 500GB-1TB (based on log volume)
  - Role: Log chunk storage

- **Prometheus**: 2 servers (HA)
  - CPU: 4 cores
  - RAM: 16GB
  - Disk: 200GB SSD
  - Role: Metrics collection and alerting

- **Grafana**: 2 servers (HA optional, but recommended)
  - CPU: 4 cores
  - RAM: 8GB
  - Disk: 50GB
  - Role: Visualization and RBAC

- **Load Balancer**: 1 server (HAProxy/Nginx)
  - CPU: 2 cores
  - RAM: 4GB
  - Disk: 20GB
  - Role: Loki distributor LB

**Total Core Servers: 10 servers**

## RBAC Implementation Structure

Grafana Organizations/Teams mapped to modules:

```
Grafana RBAC Structure:
├── Organization: Production
    ├── Team: DevOps (Admin access to all modules)
    ├── Team: SRE (Viewer/Editor access to all modules)
    ├── Team: Module-1-Dev (Viewer access to Module-1 only)
    ├── Team: Module-2-Dev (Viewer access to Module-2 only)
    └── ... (per module teams)

Dashboard Variables:
- module_name: {job="module-1", job="module-2", ...}
- node: label_values(node_uname_info, nodename)

Data Source Permissions:
- Loki: Query with label filters enforced by team
- Prometheus: Same label-based filtering
```

## Label Strategy for Logs

```
Promtail configuration uses consistent labels:
{
  job="module-1",
  environment="production",
  node="server-01",
  application="tomcat|php"
}
```

## Key Implementation Notes

- Loki retention configured at 48 hours via compactor settings
- Promtail scrapes logs and pushes to Loki distributor via load balancer
- Node Exporter on all application servers for infrastructure metrics
- Grafana folder permissions per module with team-based access control
- Use Grafana query templates to enforce module-based filtering per user role
- MinIO provides S3-compatible object storage for Loki chunks



---
## Installation Steps

### Server 1-3: Loki Cluster Installation

```bash
# Download and install Loki
cd /opt
wget https://github.com/grafana/loki/releases/download/v2.9.3/loki-linux-amd64.zip
unzip loki-linux-amd64.zip
chmod +x loki-linux-amd64
mv loki-linux-amd64 /usr/local/bin/loki

# Create user and directories
useradd --no-create-home --shell /bin/false loki
mkdir -p /etc/loki /var/lib/loki
chown -R loki:loki /etc/loki /var/lib/loki
```

**Loki Configuration:** `/etc/loki/config.yml`

```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9095

common:
  path_prefix: /var/lib/loki
  storage:
    filesystem:
      chunks_directory: /var/lib/loki/chunks
      rules_directory: /var/lib/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2023-01-01
      store: boltdb-shipper
      object_store: s3
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /var/lib/loki/boltdb-shipper-active
    cache_location: /var/lib/loki/boltdb-shipper-cache
    shared_store: s3
  aws:
    s3: s3://minioadmin:minioadmin@minio-server:9000/loki
    s3forcepathstyle: true

limits_config:
  retention_period: 48h
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  ingestion_rate_mb: 50
  ingestion_burst_size_mb: 100

chunk_store_config:
  max_look_back_period: 48h

table_manager:
  retention_deletes_enabled: true
  retention_period: 48h

compactor:
  working_directory: /var/lib/loki/compactor
  shared_store: s3
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

querier:
  max_concurrent: 20

query_range:
  parallelise_shardable_queries: true
```

**Loki Systemd Service:** `/etc/systemd/system/loki.service`

```ini
[Unit]
Description=Loki Service
After=network.target

[Service]
Type=simple
User=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/config.yml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable loki
systemctl start loki
```

### Server 4-5: MinIO Installation

```bash
# Install MinIO
cd /opt
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
mv minio /usr/local/bin/

# Create directories
mkdir -p /data/minio
useradd --no-create-home --shell /bin/false minio
chown -R minio:minio /data/minio
```

**MinIO Systemd Service:** `/etc/systemd/system/minio.service`

```ini
[Unit]
Description=MinIO
After=network.target

[Service]
Type=notify
User=minio
Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=minioadmin123"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable minio
systemctl start minio

# Create bucket
mc alias set localminio http://localhost:9000 minioadmin minioadmin123
mc mb localminio/loki
```

### Server 6-7: Prometheus Installation

```bash
# Download and install Prometheus
cd /opt
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar -xzf prometheus-2.48.0.linux-amd64.tar.gz
mv prometheus-2.48.0.linux-amd64 prometheus
cp prometheus/prometheus /usr/local/bin/
cp prometheus/promtool /usr/local/bin/

# Create user and directories
useradd --no-create-home --shell /bin/false prometheus
mkdir -p /etc/prometheus /var/lib/prometheus
chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
```

**Prometheus Configuration:** `/etc/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets:
        - 'app-server-01:9100'
        - 'app-server-02:9100'
        - 'app-server-50:9100'
        labels:
          module: 'module-1'
      - targets:
        - 'app-server-51:9100'
        labels:
          module: 'module-2'

  - job_name: 'loki'
    static_configs:
      - targets:
        - 'loki-01:3100'
        - 'loki-02:3100'
        - 'loki-03:3100'
```

**Prometheus Systemd Service:** `/etc/systemd/system/prometheus.service`

```ini
[Unit]
Description=Prometheus
After=network.target

[Service]
User=prometheus
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=2d \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
```

### Server 8-9: Grafana Installation

```bash
# Install Grafana
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list
apt-get update
apt-get install grafana -y
```

**Grafana Configuration:** `/etc/grafana/grafana.ini`

```ini
[server]
protocol = http
http_port = 3000
domain = grafana.yourdomain.com
root_url = %(protocol)s://%(domain)s:%(http_port)s/

[security]
admin_user = admin
admin_password = changeme

[auth]
disable_login_form = false

[users]
allow_sign_up = false
auto_assign_org = true
auto_assign_org_role = Viewer

[auth.anonymous]
enabled = false

[log]
mode = console file
level = info

[database]
type = sqlite3
path = grafana.db
```

**Grafana Data Source Provisioning:** `/etc/grafana/provisioning/datasources/datasources.yml`

```yaml
apiVersion: 1

datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki-loadbalancer:3100
    isDefault: true
    jsonData:
      maxLines: 1000
    editable: false

  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-01:9090
    isDefault: false
    editable: false
```

```bash
systemctl daemon-reload
systemctl enable grafana-server
systemctl start grafana-server
```

### Server 10: HAProxy Load Balancer

```bash
apt-get install haproxy -y
```

**HAProxy Configuration:** `/etc/haproxy/haproxy.cfg`

```conf
global
    log /dev/log local0
    maxconn 4096
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5000
    timeout client 50000
    timeout server 50000

frontend loki_frontend
    bind *:3100
    default_backend loki_backend

backend loki_backend
    balance roundrobin
    option httpchk GET /ready
    server loki-01 loki-01:3100 check
    server loki-02 loki-02:3100 check
    server loki-03 loki-03:3100 check
```

```bash
systemctl restart haproxy
systemctl enable haproxy
```

### Application Servers (50+ Servers): Promtail Installation

```bash
# Download and install Promtail
cd /opt
wget https://github.com/grafana/loki/releases/download/v2.9.3/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
chmod +x promtail-linux-amd64
mv promtail-linux-amd64 /usr/local/bin/promtail

# Create user and directories
useradd --no-create-home --shell /bin/false promtail
mkdir -p /etc/promtail
chown -R promtail:promtail /etc/promtail
```

**Promtail Configuration:** `/etc/promtail/config.yml`

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki-loadbalancer:3100/loki/api/v1/push

scrape_configs:
  - job_name: tomcat
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: __hostname__
          application: tomcat
          __path__: /opt/tomcat/logs/*.log

  - job_name: php
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: __hostname__
          application: php
          __path__: /var/log/php/*.log

  - job_name: apache
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: __hostname__
          application: apache
          __path__: /var/log/apache2/*.log
```

**Promtail Systemd Service:** `/etc/systemd/system/promtail.service`

```ini
[Unit]
Description=Promtail Service
After=network.target

[Service]
Type=simple
User=promtail
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Node Exporter Installation (All Application Servers)

```bash
# Download and install Node Exporter
cd /opt
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar -xzf node_exporter-1.7.0.linux-amd64.tar.gz
mv node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/

# Create user
useradd --no-create-home --shell /bin/false node_exporter
```

**Node Exporter Systemd Service:** `/etc/systemd/system/node_exporter.service`

```ini
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable promtail node_exporter
systemctl start promtail node_exporter
```

## Grafana RBAC Configuration

**Create Teams via Grafana UI or API:**

```bash
# Create teams via API
curl -X POST -H "Content-Type: application/json" -d '{"name":"DevOps"}' http://admin:changeme@grafana-server:3000/api/teams
curl -X POST -H "Content-Type: application/json" -d '{"name":"SRE"}' http://admin:changeme@grafana-server:3000/api/teams
curl -X POST -H "Content-Type: application/json" -d '{"name":"Module-1-Dev"}' http://admin:changeme@grafana-server:3000/api/teams
curl -X POST -H "Content-Type: application/json" -d '{"name":"Module-2-Dev"}' http://admin:changeme@grafana-server:3000/api/teams
```

**Dashboard Template Variables:**

```
Variable Name: module_name
Type: Query
Data Source: Loki
Query: label_values(job)

Variable Name: node
Type: Query
Data Source: Prometheus
Query: label_values(node_uname_info{job="$module_name"}, nodename)
```

**LogQL Query Example in Dashboard:**

```
{job="$module_name", node="$node"} |= ""
```

All configurations provided. Adjust paths, IPs, and credentials as per your environment.


