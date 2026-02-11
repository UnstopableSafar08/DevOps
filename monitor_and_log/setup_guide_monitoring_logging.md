# Centralized Log Visualization Platform

Production-ready centralized logging and monitoring solution for Tomcat and PHP applications using Promtail, Loki, Prometheus, and Grafana with RBAC implementation.

## Overview

This setup provides centralized log aggregation and visualization for 10 modules across 50+ servers with 2-day retention period and role-based access control.

## Architecture
```
Application Servers (50+)
  ↓ Promtail (Log Collection)
Load Balancer (HAProxy)
  ↓
Loki Cluster (3 nodes)
  ↓ Log Storage
Grafana + Prometheus
  ↓
Dashboard Access (RBAC)
```

## Technology Stack

### Promtail
Log shipping agent installed on application servers. Reads log files and forwards them to Loki with metadata labels. Acts as the data collection layer that monitors specified log paths continuously.

### Loki
Log aggregation system that indexes and stores logs using labels rather than full-text indexing. Designed for high-volume log ingestion with minimal resource overhead and cost-efficient storage.

### Prometheus
Time-series metrics database that collects and stores numerical data from servers and applications. Monitors system health, performance metrics, and triggers alerts based on defined thresholds.

### Grafana
Visualization platform that queries Loki and Prometheus to display logs and metrics through customizable dashboards. Provides RBAC for controlling user access to specific modules and data sources.

### HAProxy
Load balancer that distributes incoming log traffic across multiple Loki instances. Ensures high availability and prevents single point of failure in the logging infrastructure.

## Server Requirements

### Core Infrastructure (8 Servers Total)

**Loki Cluster (3 servers)**
- CPU: 8 cores
- RAM: 16GB
- Disk: 1TB SSD
- OS: Ubuntu 20.04/22.04

**Prometheus (2 servers)**
- CPU: 4 cores
- RAM: 16GB
- Disk: 200GB SSD
- OS: Ubuntu 20.04/22.04

**Grafana (2 servers)**
- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB
- OS: Ubuntu 20.04/22.04

**Load Balancer (1 server)**
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB
- OS: Ubuntu 20.04/22.04

### Application Servers (50+)
- Promtail and Node Exporter installed
- Minimal resource overhead

## Installation Guide

### Step 1: Prepare All Servers

Run on all servers before starting installation:
```bash
# Update system packages
apt-get update && apt-get upgrade -y

# Install required dependencies
apt-get install wget curl unzip apt-transport-https software-properties-common -y

# Configure firewall rules
ufw allow 22/tcp
ufw allow 3100/tcp  # Loki
ufw allow 9090/tcp  # Prometheus
ufw allow 3000/tcp  # Grafana
ufw allow 9080/tcp  # Promtail
ufw allow 9100/tcp  # Node Exporter
ufw --force enable

# Set timezone
timedatectl set-timezone UTC

# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
```

### Step 2: Install Loki Cluster (Servers 1-3)
```bash
# Download Loki binary
cd /opt
wget https://github.com/grafana/loki/releases/download/v2.9.3/loki-linux-amd64.zip
unzip loki-linux-amd64.zip
chmod +x loki-linux-amd64
mv loki-linux-amd64 /usr/local/bin/loki

# Create user and directories
useradd --no-create-home --shell /bin/false loki
mkdir -p /etc/loki /var/lib/loki/chunks /var/lib/loki/boltdb-shipper-active /var/lib/loki/boltdb-shipper-cache /var/lib/loki/compactor
chown -R loki:loki /etc/loki /var/lib/loki
chmod -R 755 /var/lib/loki
```

Create Loki configuration file: `/etc/loki/config.yml`
```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9095
  log_level: info

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
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /var/lib/loki/boltdb-shipper-active
    cache_location: /var/lib/loki/boltdb-shipper-cache
    cache_ttl: 24h
  filesystem:
    directory: /var/lib/loki/chunks

limits_config:
  retention_period: 48h
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  ingestion_rate_mb: 50
  ingestion_burst_size_mb: 100
  max_query_length: 721h
  max_query_lookback: 48h

chunk_store_config:
  max_look_back_period: 48h

table_manager:
  retention_deletes_enabled: true
  retention_period: 48h

compactor:
  working_directory: /var/lib/loki/compactor
  shared_store: filesystem
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

querier:
  max_concurrent: 20

query_range:
  parallelise_shardable_queries: true
  cache_results: true
```

Create systemd service: `/etc/systemd/system/loki.service`
```ini
[Unit]
Description=Loki Log Aggregation System
Documentation=https://grafana.com/docs/loki/latest/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=loki
Group=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/config.yml
Restart=on-failure
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Start Loki service:
```bash
systemctl daemon-reload
systemctl enable loki
systemctl start loki
systemctl status loki

# Verify Loki is running
curl http://localhost:3100/ready
```

### Step 3: Install HAProxy Load Balancer (Server 4)
```bash
# Install HAProxy
apt-get install haproxy -y

# Backup original configuration
cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup
```

Configure HAProxy: `/etc/haproxy/haproxy.cfg`
```conf
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon
    maxconn 4096

defaults
    log global
    mode http
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor except 127.0.0.0/8
    option redispatch
    retries 3
    timeout connect 5000
    timeout client 50000
    timeout server 50000

frontend loki_frontend
    bind *:3100
    default_backend loki_backend
    mode http

backend loki_backend
    balance roundrobin
    mode http
    option httpchk GET /ready
    http-check expect status 200
    server loki-01 10.0.1.101:3100 check inter 5s rise 2 fall 3
    server loki-02 10.0.1.102:3100 check inter 5s rise 2 fall 3
    server loki-03 10.0.1.103:3100 check inter 5s rise 2 fall 3

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
```

Replace IP addresses with your actual Loki server IPs.
```bash
# Test configuration
haproxy -c -f /etc/haproxy/haproxy.cfg

# Restart HAProxy
systemctl restart haproxy
systemctl enable haproxy
systemctl status haproxy

# Verify load balancer
curl http://localhost:3100/ready
```

### Step 4: Install Prometheus (Servers 5-6)
```bash
# Download Prometheus
cd /opt
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar -xzf prometheus-2.48.0.linux-amd64.tar.gz
cd prometheus-2.48.0.linux-amd64

# Copy binaries
cp prometheus /usr/local/bin/
cp promtool /usr/local/bin/

# Create user and directories
useradd --no-create-home --shell /bin/false prometheus
mkdir -p /etc/prometheus /var/lib/prometheus
cp -r consoles console_libraries /etc/prometheus/
chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
```

Create Prometheus configuration: `/etc/prometheus/prometheus.yml`
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    environment: 'on-prem'

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files: []

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'loki'
    static_configs:
      - targets:
        - '10.0.1.101:3100'
        - '10.0.1.102:3100'
        - '10.0.1.103:3100'
        labels:
          service: 'loki'

  - job_name: 'node-exporter-module-1'
    static_configs:
      - targets:
        - 'app-server-01:9100'
        - 'app-server-02:9100'
        - 'app-server-03:9100'
        labels:
          module: 'module-1'
          environment: 'production'

  - job_name: 'node-exporter-module-2'
    static_configs:
      - targets:
        - 'app-server-04:9100'
        - 'app-server-05:9100'
        labels:
          module: 'module-2'
          environment: 'production'

  - job_name: 'node-exporter-module-3'
    static_configs:
      - targets:
        - 'app-server-06:9100'
        labels:
          module: 'module-3'
          environment: 'production'
```

Add all 50+ servers with appropriate module labels. Each module should have its own job or use labels to differentiate.

Create systemd service: `/etc/systemd/system/prometheus.service`
```ini
[Unit]
Description=Prometheus Monitoring System
Documentation=https://prometheus.io/docs/introduction/overview/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=2d \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.enable-lifecycle
Restart=on-failure
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Start Prometheus:
```bash
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
systemctl status prometheus

# Verify Prometheus
curl http://localhost:9090/-/healthy
```

### Step 5: Install Grafana (Servers 7-8)
```bash
# Add Grafana repository
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list

# Install Grafana
apt-get update
apt-get install grafana -y
```

Configure Grafana: `/etc/grafana/grafana.ini`
```ini
[server]
protocol = http
http_addr = 0.0.0.0
http_port = 3000
domain = grafana.yourdomain.com
root_url = %(protocol)s://%(domain)s:%(http_port)s/
enable_gzip = true

[database]
type = sqlite3
path = grafana.db

[security]
admin_user = admin
admin_password = Admin@12345
secret_key = SW2YcwTIb9zpOOhoPsMm
disable_gravatar = true

[users]
allow_sign_up = false
allow_org_create = false
auto_assign_org = true
auto_assign_org_role = Viewer

[auth]
disable_login_form = false
disable_signout_menu = false

[auth.anonymous]
enabled = false

[auth.basic]
enabled = true

[log]
mode = console file
level = info

[log.console]
level = info
format = console

[log.file]
level = info
format = text
log_rotate = true
max_lines = 1000000
max_size_shift = 28
daily_rotate = true
max_days = 7

[alerting]
enabled = true
execute_alerts = true
```

Create datasource provisioning: `/etc/grafana/provisioning/datasources/datasources.yml`
```yaml
apiVersion: 1

deleteDatasources:
  - name: Loki
    orgId: 1
  - name: Prometheus
    orgId: 1

datasources:
  - name: Loki
    type: loki
    access: proxy
    orgId: 1
    url: http://10.0.1.104:3100
    isDefault: true
    version: 1
    editable: false
    jsonData:
      maxLines: 1000
      timeout: 60
      httpHeaderName1: "X-Scope-OrgID"
    secureJsonData:
      httpHeaderValue1: "tenant1"

  - name: Prometheus
    type: prometheus
    access: proxy
    orgId: 1
    url: http://10.0.1.105:9090
    isDefault: false
    version: 1
    editable: false
    jsonData:
      timeInterval: 15s
      httpMethod: POST
```

Replace URLs with your actual load balancer and Prometheus IPs.

Start Grafana:
```bash
systemctl daemon-reload
systemctl enable grafana-server
systemctl start grafana-server
systemctl status grafana-server

# Access Grafana
# Open browser: http://grafana-server-ip:3000
# Login: admin / Admin@12345
```

### Step 6: Install Promtail on Application Servers (All 50+ Servers)
```bash
# Download Promtail
cd /opt
wget https://github.com/grafana/loki/releases/download/v2.9.3/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
chmod +x promtail-linux-amd64
mv promtail-linux-amd64 /usr/local/bin/promtail

# Create user and directories
useradd --no-create-home --shell /bin/false promtail
mkdir -p /etc/promtail
chown -R promtail:promtail /etc/promtail

# Add promtail user to required groups for log access
usermod -a -G adm promtail
```

Create Promtail configuration: `/etc/promtail/config.yml`

Update the `job` label value based on the module (module-1, module-2, etc.):
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: info

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://10.0.1.104:3100/loki/api/v1/push
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    timeout: 10s

scrape_configs:
  - job_name: tomcat-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: app-server-01
          application: tomcat
          log_type: application
          __path__: /opt/tomcat/logs/catalina.out

  - job_name: tomcat-access-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: app-server-01
          application: tomcat
          log_type: access
          __path__: /opt/tomcat/logs/localhost_access_log.*.txt

  - job_name: php-fpm-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: app-server-01
          application: php-fpm
          log_type: application
          __path__: /var/log/php*-fpm.log

  - job_name: apache-access-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: app-server-01
          application: apache
          log_type: access
          __path__: /var/log/apache2/access.log

  - job_name: apache-error-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: app-server-01
          application: apache
          log_type: error
          __path__: /var/log/apache2/error.log

  - job_name: system-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: module-1
          environment: production
          node: app-server-01
          application: system
          log_type: syslog
          __path__: /var/log/syslog
```

Important: Update these values for each server:
- `job`: module-1, module-2, module-3, etc.
- `node`: app-server-01, app-server-02, etc.
- `__path__`: Actual log file paths on your servers

Create systemd service: `/etc/systemd/system/promtail.service`
```ini
[Unit]
Description=Promtail Log Collector
Documentation=https://grafana.com/docs/loki/latest/clients/promtail/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=promtail
Group=promtail
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Start Promtail:
```bash
systemctl daemon-reload
systemctl enable promtail
systemctl start promtail
systemctl status promtail

# Verify Promtail is sending logs
curl http://localhost:9080/metrics
```

### Step 7: Install Node Exporter on Application Servers (All 50+ Servers)
```bash
# Download Node Exporter
cd /opt
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar -xzf node_exporter-1.7.0.linux-amd64.tar.gz
cp node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/

# Create user
useradd --no-create-home --shell /bin/false node_exporter
```

Create systemd service: `/etc/systemd/system/node_exporter.service`
```ini
[Unit]
Description=Node Exporter
Documentation=https://prometheus.io/docs/guides/node-exporter/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \
  --collector.filesystem.mount-points-exclude='^/(dev|proc|sys|var/lib/docker/.+|var/lib/kubelet/.+)($|/)' \
  --collector.netclass.ignored-devices='^(veth.*|docker.*|br-.*)$'
Restart=on-failure
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Start Node Exporter:
```bash
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
systemctl status node_exporter

# Verify metrics are being exposed
curl http://localhost:9100/metrics
```

### Step 8: Configure Grafana RBAC

Access Grafana web interface and configure teams and permissions.

**Create Teams:**

Navigate to Configuration > Teams > New Team

Create the following teams:
- DevOps (Admin access to all modules)
- SRE (Editor access to all modules)
- Module-1-Dev (Viewer access to Module-1)
- Module-2-Dev (Viewer access to Module-2)
- Module-3-Dev (Viewer access to Module-3)
- Continue for all 10 modules

**Assign Users to Teams:**

Configuration > Users > Add user to team

**Create Folders for Each Module:**

Dashboards > New Folder
- Create folders: Module-1, Module-2, Module-3, etc.

**Set Folder Permissions:**

For each folder:
- Click folder settings > Permissions
- Add team with appropriate role:
  - DevOps: Admin
  - SRE: Editor
  - Module-X-Dev: Viewer (only for their module)

**Alternative: Use Grafana API for Bulk RBAC Setup:**
```bash
# Set variables
GRAFANA_URL="http://grafana-server-ip:3000"
ADMIN_USER="admin"
ADMIN_PASS="Admin@12345"

# Create teams
for i in {1..10}; do
  curl -X POST -H "Content-Type: application/json" \
    -d "{\"name\":\"Module-${i}-Dev\"}" \
    http://${ADMIN_USER}:${ADMIN_PASS}@${GRAFANA_URL}/api/teams
done

curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"DevOps"}' \
  http://${ADMIN_USER}:${ADMIN_PASS}@${GRAFANA_URL}/api/teams

curl -X POST -H "Content-Type: application/json" \
  -d '{"name":"SRE"}' \
  http://${ADMIN_USER}:${ADMIN_PASS}@${GRAFANA_URL}/api/teams

# Create folders and set permissions (manual or via API)
```

### Step 9: Create Grafana Dashboard with Variables

**Create New Dashboard:**

Dashboards > New > New Dashboard > Add visualization

**Add Dashboard Variables:**

Dashboard Settings > Variables > Add variable

Variable 1 - Module Selection:
- Name: `module_name`
- Type: Query
- Data Source: Loki
- Query: `label_values(job)`
- Multi-value: Yes
- Include All option: Yes

Variable 2 - Node Selection:
- Name: `node`
- Type: Query
- Data Source: Loki
- Query: `label_values({job="$module_name"}, node)`
- Multi-value: Yes
- Include All option: Yes

Variable 3 - Application Filter:
- Name: `application`
- Type: Query
- Data Source: Loki
- Query: `label_values({job="$module_name"}, application)`
- Multi-value: Yes
- Include All option: Yes

**Add Log Panel:**

Add Panel > Visualization: Logs

Query (Loki):
```
{job=~"$module_name", node=~"$node", application=~"$application"} |= ""
```

Panel Settings:
- Title: Application Logs
- Options: Show time, Show labels
- Enable log context

**Add Metrics Panel:**

Add Panel > Visualization: Time series

Query (Prometheus):
```
rate(node_cpu_seconds_total{job=~"node-exporter-$module_name", mode="idle"}[5m])
```

**Save Dashboard:**

Save dashboard to appropriate module folder with RBAC permissions.

### Step 10: Verification and Testing

**Verify Loki Ingestion:**
```bash
# Check Loki metrics
curl http://loki-server:3100/metrics | grep loki_ingester_streams_created_total

# Query logs via API
curl -G -s "http://loki-server:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="module-1"}' \
  --data-urlencode 'limit=10' | jq
```

**Verify Prometheus Targets:**

Open Prometheus UI: http://prometheus-server:9090/targets

Ensure all Node Exporter targets are UP.

**Verify Promtail Status:**
```bash
# Check Promtail logs
journalctl -u promtail -f

# Check positions file
cat /tmp/positions.yaml
```

**Test Log Search in Grafana:**

- Login to Grafana
- Navigate to Explore
- Select Loki data source
- Run query: `{job="module-1"}`
- Verify logs are visible

**Test RBAC:**

- Login as Module-1-Dev user
- Verify access only to Module-1 dashboard
- Attempt to access Module-2 dashboard (should be denied)

### Step 11: Monitoring and Maintenance

**Setup Disk Space Alerts:**

Add to Prometheus `/etc/prometheus/rules/alerts.yml`:
```yaml
groups:
  - name: loki_alerts
    interval: 30s
    rules:
      - alert: LokiDiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/var/lib/loki"} / node_filesystem_size_bytes{mountpoint="/var/lib/loki"}) < 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Loki disk space below 20% on {{ $labels.instance }}"
          description: "Disk usage is at {{ $value | humanizePercentage }}"

      - alert: LokiIngestionRate
        expr: rate(loki_distributor_bytes_received_total[1m]) == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Loki not receiving logs"
          description: "No log ingestion detected for 5 minutes"
```

**Log Rotation for Loki:**

Add cron job for compaction verification:
```bash
# Add to crontab
0 */6 * * * systemctl status loki | grep -q "active (running)" || systemctl restart loki
```

**Backup Strategy:**
```bash
# Backup Grafana dashboards and datasources
tar -czf grafana-backup-$(date +%Y%m%d).tar.gz /var/lib/grafana/grafana.db /etc/grafana/

# Backup Prometheus configuration
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz /etc/prometheus/

# Backup Loki configuration
tar -czf loki-backup-$(date +%Y%m%d).tar.gz /etc/loki/
```

## Troubleshooting

### Promtail Not Sending Logs
```bash
# Check Promtail logs
journalctl -u promtail -n 100 --no-pager

# Verify network connectivity to Loki
telnet loki-loadbalancer 3100

# Check file permissions
ls -la /var/log/apache2/
ls -la /opt/tomcat/logs/

# Test Promtail configuration
promtail -config.file=/etc/promtail/config.yml -dry-run
```

### Loki Not Showing Logs in Grafana
```bash
# Check Loki logs
journalctl -u loki -n 100 --no-pager

# Verify Loki is receiving data
curl http://localhost:3100/metrics | grep loki_distributor_bytes_received_total

# Test Loki query directly
curl -G -s "http://localhost:3100/loki/api/v1/labels"

# Check Grafana datasource connectivity
curl http://grafana-server:3000/api/datasources/proxy/1/loki/api/v1/labels
```

### Prometheus Targets Down
```bash
# Check Prometheus logs
journalctl -u prometheus -n 100 --no-pager

# Verify target connectivity
curl http://target-server:9100/metrics

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

# Check Prometheus configuration syntax
promtool check config /etc/prometheus/prometheus.yml
```

### High Disk Usage on Loki
```bash
# Check disk usage
df -h /var/lib/loki

# Verify compactor is running
journalctl -u loki | grep compactor

# Manually trigger compaction (if needed)
curl -X POST http://localhost:3100/loki/api/v1/delete?query={job="old-module"}&start=0&end=1234567890

# Check retention settings
grep retention /etc/loki/config.yml
```

### Grafana Dashboard Variables Not Working
```bash
# Verify Loki labels exist
curl -G -s "http://loki-server:3100/loki/api/v1/labels" | jq

# Check specific label values
curl -G -s "http://loki-server:3100/loki/api/v1/label/job/values" | jq

# Test query in Grafana Explore before adding to dashboard
```

## Performance Tuning

### Loki Optimization
```yaml
# Increase ingestion limits for high-volume environments
limits_config:
  ingestion_rate_mb: 100
  ingestion_burst_size_mb: 200
  max_streams_per_user: 10000
  max_global_streams_per_user: 50000
```

### Promtail Optimization
```yaml
# Batch logs before sending
clients:
  - url: http://loki:3100/loki/api/v1/push
    batchwait: 1s
    batchsize: 1048576
```

### Prometheus Optimization
```yaml
# Adjust scrape intervals based on needs
global:
  scrape_interval: 30s
  scrape_timeout: 10s
```

## Security Recommendations

### Enable HTTPS for Grafana
```bash
# Generate self-signed certificate (use proper CA cert in production)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/grafana/grafana.key \
  -out /etc/grafana/grafana.crt
```

Update `/etc/grafana/grafana.ini`:
```ini
[server]
protocol = https
cert_file = /etc/grafana/grafana.crt
cert_key = /etc/grafana/grafana.key
```

### Restrict Network Access
```bash
# Allow only specific IPs to access Loki
ufw allow from 10.0.1.0/24 to any port 3100
ufw allow from 10.0.2.0/24 to any port 3100

# Allow only Grafana to access Prometheus
ufw allow from grafana-server-ip to any port 9090
```

### Change Default Passwords
```bash
# Change Grafana admin password
grafana-cli admin reset-admin-password NewSecurePassword123
```

## Maintenance Tasks

### Daily

- Monitor disk space on Loki servers
- Check Grafana for login anomalies
- Review alert notifications

### Weekly

- Review log ingestion rates and patterns
- Check for outdated or unused dashboards
- Verify backup completion

### Monthly

- Update Grafana, Loki, Prometheus, and Promtail to latest stable versions
- Review and optimize slow queries
- Audit user access and RBAC permissions
- Test disaster recovery procedures

## Useful Commands Reference
```bash
# Check service status on all servers
systemctl status loki prometheus grafana-server promtail node_exporter haproxy

# View real-time logs
journalctl -u loki -f
journalctl -u promtail -f
journalctl -u prometheus -f

# Restart all services
systemctl restart loki prometheus grafana-server promtail node_exporter

# Check connectivity between components
curl http://loki-server:3100/ready
curl http://prometheus-server:9090/-/healthy
curl http://grafana-server:3000/api/health

# Query Loki from command line
logcli --addr="http://loki-server:3100" query '{job="module-1"}' --limit=50 --since=1h

# View Promtail positions
cat /tmp/positions.yaml

# Check Prometheus targets
curl http://prometheus-server:9090/api/v1/targets | jq

# Reload configurations without restart
curl -X POST http://prometheus-server:9090/-/reload
```

## Additional Resources

- Loki Documentation: https://grafana.com/docs/loki/latest/
- Prometheus Documentation: https://prometheus.io/docs/
- Grafana Documentation: https://grafana.com/docs/grafana/latest/
- Promtail Documentation: https://grafana.com/docs/loki/latest/clients/promtail/
