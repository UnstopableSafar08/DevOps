# ELK Stack Setup & Configuration Guide
### Elasticsearch + Kibana + Filebeat on Oracle Linux 9.x

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Elasticsearch Installation & Configuration](#3-elasticsearch-installation--configuration)
4. [Kibana Installation & Configuration](#4-kibana-installation--configuration)
5. [Filebeat on ELK Server (System Logs)](#5-filebeat-on-elk-server-system-logs)
6. [Filebeat on Remote App Server (PHP Logs)](#6-filebeat-on-remote-app-server-php-logs)
7. [Kibana — Viewing Logs](#7-kibana--viewing-logs)
8. [Troubleshooting](#8-troubleshooting)
9. [Performance Tuning](#9-performance-tuning)
10. [Security Recommendations](#10-security-recommendations)

---

## 1. Architecture Overview

```
┌──────────────────────────────┐          ┌──────────────────────────────┐
│   APP SERVER                 │          │   ELK SERVER                 │
│   (e.g. airlines-04)         │          │   (e.g. ett-elk-stack)       │
│                              │  :9200   │                              │
│   Filebeat ──────────────────┼─────────►│   Elasticsearch :9200        │
│   ├── /var/apps/*/logs/*.log │  HTTPS   │   Kibana         :5601       │
│   └── app metrics            │          │   Filebeat (system logs)     │
└──────────────────────────────┘          └──────────────────────────────┘
```

**Server Specs (Minimum Recommended)**

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 Cores | 8 Cores |
| Disk | 50 GB | 200 GB+ |
| OS | Oracle Linux 9.x | Oracle Linux 9.x |

---

## 2. Prerequisites

### 2.1 System Preparation (ELK Server)

```bash
# Update the system
sudo dnf update -y

# Set vm.max_map_count (required by Elasticsearch)
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Disable swap (recommended for Elasticsearch)
sudo swapoff -a
sudo sed -i '/swap/d' /etc/fstab

# Open required firewall ports
sudo firewall-cmd --permanent --add-port=9200/tcp   # Elasticsearch
sudo firewall-cmd --permanent --add-port=5601/tcp   # Kibana
sudo firewall-cmd --reload
```

### 2.2 Add Elastic Repository

```bash
# Import GPG key
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

# Create repo file
sudo tee /etc/yum.repos.d/elastic.repo <<EOF
[elastic-9.x]
name=Elastic repository for 9.x packages
baseurl=https://artifacts.elastic.co/packages/9.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF
```

---

## 3. Elasticsearch Installation & Configuration

### 3.1 Install Elasticsearch

```bash
sudo dnf install elasticsearch -y

# Verify installation
/usr/share/elasticsearch/bin/elasticsearch --version
```

### 3.2 Configure `/etc/elasticsearch/elasticsearch.yml`

```yaml
# ── Cluster ──────────────────────────────────────────────
cluster.name: es-ett

# ── Node ─────────────────────────────────────────────────
node.name: ett-elk-stack

# ── Paths ────────────────────────────────────────────────
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch

# ── Network ──────────────────────────────────────────────
network.host: 0.0.0.0
http.port: 9200

# ── Discovery ────────────────────────────────────────────
discovery.type: single-node

# ── Security ─────────────────────────────────────────────
xpack.security.enabled: true
xpack.security.enrollment.enabled: true

xpack.security.http.ssl:
  enabled: true
  keystore.path: certs/http.p12

xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12
```

### 3.3 JVM Heap Configuration

Edit `/etc/elasticsearch/jvm.options.d/heap.options`:

```bash
# Set to 50% of total RAM (max 31GB)
# For 8GB server:
-Xms2g
-Xmx2g
```

### 3.4 Start Elasticsearch

```bash
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch

# Check status
sudo systemctl status elasticsearch
```

### 3.5 Set Passwords

```bash
# Auto-generate passwords for built-in users
sudo /usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto

# OR set manually
sudo /usr/share/elasticsearch/bin/elasticsearch-setup-passwords interactive
```

### 3.6 Verify Elasticsearch

```bash
curl -u elastic:"YOUR_PASSWORD" -XGET -k https://localhost:9200
```

Expected output:
```json
{
  "name" : "ett-elk-stack",
  "cluster_name" : "es-ett",
  "version" : { "number" : "9.3.0" },
  "tagline" : "You Know, for Search"
}
```

---

## 4. Kibana Installation & Configuration

### 4.1 Install Kibana

```bash
sudo dnf install kibana -y
```

### 4.2 Configure `/etc/kibana/kibana.yml`

```yaml
# ── Server ───────────────────────────────────────────────
server.port: 5601
server.host: "0.0.0.0"
server.name: "ett-elk-stack"

# ── Elasticsearch ─────────────────────────────────────────
elasticsearch.hosts: ["https://localhost:9200"]
elasticsearch.username: "kibana_system"
elasticsearch.password: "YOUR_KIBANA_SYSTEM_PASSWORD"

elasticsearch.ssl.verificationMode: none

# ── Logging ───────────────────────────────────────────────
logging.dest: /var/log/kibana/kibana.log
logging.level: warn
```

### 4.3 Start Kibana

```bash
sudo systemctl enable kibana
sudo systemctl start kibana
sudo systemctl status kibana
```

### 4.4 Verify Kibana

```bash
curl http://localhost:5601/api/status
```

Access via browser: `http://<ELK_SERVER_IP>:5601`

---

## 5. Filebeat on ELK Server (System Logs)

### 5.1 Install Filebeat

```bash
# Version must match Elasticsearch version
sudo dnf install filebeat-9.3.0 -y
filebeat version
```

### 5.2 Configure `/etc/filebeat/filebeat.yml`

```yaml
# ======================== Filebeat Inputs ========================
filebeat.inputs:

  - type: filestream                    # 'log' type is removed in v9.x
    id: system-logs                     # required unique ID
    enabled: true
    paths:
      - /var/log/messages               # General system messages
      - /var/log/secure                 # Auth / SSH logs
      - /var/log/cron                   # Cron job logs
      - /var/log/boot.log               # Boot logs
      - /var/log/audit/audit.log        # Audit logs
    fields:
      log_type: system
      host_env: production
    fields_under_root: true
    prospector.scanner.check_interval: 30s
    close.on_state_change.inactive: 5m
    parsers:
      - multiline:
          type: pattern
          pattern: '^\s'
          negate: false
          match: after

# ======================== Modules ========================
filebeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

# ======================== Elasticsearch Output ========================
output.elasticsearch:
  hosts: ["https://<ELK_SERVER_IP>:9200"]
  username: "elastic"
  password: "YOUR_PASSWORD"
  ssl.verification_mode: none

# ======================== Kibana ========================
setup.kibana:
  host: "http://<ELK_SERVER_IP>:5601"   # HTTP (not HTTPS) if Kibana has no SSL
  username: "elastic"
  password: "YOUR_PASSWORD"

# ======================== General Settings ========================
setup.ilm.enabled: true
setup.template.enabled: true
setup.template.settings:
  index.number_of_shards: 1
  index.number_of_replicas: 0           # 0 for single-node cluster

queue.mem:
  events: 1024
  flush.min_events: 512
  flush.timeout: 10s

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
```

> **⚠️ Important:** `type: log` is **deprecated and removed in Filebeat 9.x**. Always use `type: filestream`.

### 5.3 Enable System Module

```bash
sudo filebeat modules enable system

# Edit module config
sudo vi /etc/filebeat/modules.d/system.yml
```

```yaml
- module: system
  syslog:
    enabled: true
    var.paths: ["/var/log/messages"]    # Oracle Linux uses 'messages'
  auth:
    enabled: true
    var.paths: ["/var/log/secure"]      # Oracle Linux uses 'secure'
```

### 5.4 Setup & Start

```bash
# Load index templates and dashboards
sudo filebeat setup -e --strict.perms=false

# Start Filebeat
sudo systemctl enable filebeat
sudo systemctl start filebeat
sudo systemctl status filebeat
```

### 5.5 Verify Data

```bash
# Check index was created
curl -u elastic:"YOUR_PASSWORD" -k \
  "https://<ELK_SERVER_IP>:9200/_cat/indices/filebeat*?v&h=index,health,docs.count,store.size"
```

---

## 6. Filebeat on Remote App Server (PHP Logs)

### 6.1 Install Filebeat on App Server

```bash
# Add Elastic repo (same as Section 2.2)
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

sudo tee /etc/yum.repos.d/elastic.repo <<EOF
[elastic-9.x]
name=Elastic repository for 9.x packages
baseurl=https://artifacts.elastic.co/packages/9.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF

# Install — version must match ELK server
sudo dnf install filebeat-9.3.0 -y
```

### 6.2 Open Firewall on ELK Server

```bash
# On ELK SERVER — allow app server to reach Elasticsearch
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  source address="<APP_SERVER_IP>" port port="9200" protocol="tcp" accept'
sudo firewall-cmd --reload
```

### 6.3 Configure `/etc/filebeat/filebeat.yml` on App Server

```yaml
# ======================== Filebeat Inputs ========================
filebeat.inputs:

  # --- GDS Admin ---
  - type: filestream
    id: gds-admin-logs
    enabled: true
    paths:
      - /var/apps/gds-admin/gds-admin/storage/logs/*.log
    fields:
      log_type: php-application
      app_name: gds-admin
      host_env: production
    fields_under_root: true
    prospector.scanner.fingerprint.length: 64   # allow files smaller than 1024 bytes
    prospector.scanner.fingerprint.offset: 0
    prospector.scanner.check_interval: 30s
    close.on_state_change.inactive: 5m
    parsers:
      - multiline:
          type: pattern
          pattern: '^\[\d{4}-\d{2}-\d{2}'       # Laravel log format: [YYYY-MM-DD
          negate: true
          match: after

  # --- GDS API ---
  - type: filestream
    id: gds-api-logs
    enabled: true
    paths:
      - /var/apps/gds-api/gds-api/storage/logs/*.log
      - /var/apps/gds-api/gds-api/storage/logs/insurance/*.log
      # Note: exclude directories with thousands of small files to prevent
      # resource exhaustion. Add them only after confirming file counts.
    fields:
      log_type: php-application
      app_name: gds-api
      host_env: production
    fields_under_root: true
    prospector.scanner.fingerprint.length: 64
    prospector.scanner.fingerprint.offset: 0
    prospector.scanner.check_interval: 30s
    close.on_state_change.inactive: 5m
    parsers:
      - multiline:
          type: pattern
          pattern: '^\[\d{4}-\d{2}-\d{2}'
          negate: true
          match: after

  # --- GDS Web ---
  - type: filestream
    id: gds-web-logs
    enabled: true
    paths:
      - /var/apps/gds-web/gds-web/storage/logs/*.log
      - /var/apps/gds-web/gds-web/storage/logs/app/*.log
      - /var/apps/gds-web/gds-web/storage/logs/app-link/*.log
      - /var/apps/gds-web/gds-web/storage/logs/fonepay/*.log
      - /var/apps/gds-web/gds-web/storage/logs/nic/*.log
    fields:
      log_type: php-application
      app_name: gds-web
      host_env: production
    fields_under_root: true
    prospector.scanner.fingerprint.length: 64
    prospector.scanner.fingerprint.offset: 0
    prospector.scanner.check_interval: 30s
    close.on_state_change.inactive: 5m
    parsers:
      - multiline:
          type: pattern
          pattern: '^\[\d{4}-\d{2}-\d{2}'
          negate: true
          match: after

# ======================== Modules ========================
filebeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

# ======================== Output: Remote Elasticsearch ========================
output.elasticsearch:
  hosts: ["https://<ELK_SERVER_IP>:9200"]
  username: "elastic"
  password: "YOUR_PASSWORD"
  ssl.verification_mode: none
  worker: 1
  bulk_max_size: 512

# ======================== Kibana ========================
setup.kibana:
  host: "http://<ELK_SERVER_IP>:5601"
  username: "elastic"
  password: "YOUR_PASSWORD"

# ======================== General Settings ========================
setup.ilm.enabled: true
setup.template.enabled: true
setup.template.settings:
  index.number_of_shards: 1
  index.number_of_replicas: 0

queue.mem:
  events: 1024
  flush.min_events: 512
  flush.timeout: 10s

processors:
  - add_host_metadata: ~
```

### 6.4 Fix Log File Permissions

```bash
# Check ownership
ls -la /var/apps/gds-api/gds-api/storage/logs/

# Allow filebeat (or root) to read logs
sudo chmod -R o+r /var/apps/gds-admin/gds-admin/storage/logs/
sudo chmod -R o+r /var/apps/gds-api/gds-api/storage/logs/
sudo chmod -R o+r /var/apps/gds-web/gds-web/storage/logs/

# Ensure parent directories are traversable
sudo chmod o+x /var/apps/gds-admin/gds-admin/storage/
sudo chmod o+x /var/apps/gds-api/gds-api/storage/
sudo chmod o+x /var/apps/gds-web/gds-web/storage/
```

### 6.5 Setup & Start

```bash
# Test connectivity to remote Elasticsearch
sudo filebeat test output -e

# Test config syntax
sudo filebeat test config -e

# Load templates (runs against remote ES)
sudo filebeat setup -e --strict.perms=false

# Start Filebeat
sudo systemctl enable filebeat
sudo systemctl start filebeat
sudo systemctl status filebeat
```

### 6.6 Re-ingesting Historical Logs

By default, Filebeat only reads **new lines** appended to files. To re-read all existing log files from the beginning:

```bash
# Stop Filebeat first
sudo systemctl stop filebeat

# Delete the registry (tracks read positions)
sudo rm -rf /var/lib/filebeat/registry/

# Start again — will re-read all files from offset 0
sudo systemctl start filebeat
```

> **⚠️ Warning:** Only do this if you actually need historical logs. On servers with thousands of log files this can cause high CPU/memory usage temporarily.

---

## 7. Kibana — Viewing Logs

### 7.1 Create a Data View

1. Open `http://<ELK_SERVER_IP>:5601`
2. Go to **☰ Menu → Stack Management → Data Views**
3. Click **Create data view**
   - Name: `Filebeat Logs`
   - Index pattern: `filebeat-*`
   - Timestamp field: `@timestamp`
4. Click **Save data view to Kibana**

### 7.2 Discover — Filter Logs

Go to **☰ → Discover** and use KQL queries:

```kql
# All PHP application logs
log_type : "php-application"

# Logs from a specific app
app_name : "gds-api"

# Only ERROR level logs
log_type : "php-application" AND message : "*ERROR*"

# SSH authentication failures
log_type : "system" AND log.file.path : "*secure*" AND message : "*Failed*"

# Logs from a specific file
log.file.path : "*gds-api*laravel*"
```

### 7.3 Pre-built Dashboards

Go to **☰ → Dashboards** and search for:
- `Filebeat System` — system log overview
- `Filebeat Syslog` — syslog analysis
- `Filebeat SSH` — SSH login monitoring

---

## 8. Troubleshooting

### 8.1 Diagnostic Commands

```bash
# Test config syntax
sudo filebeat test config -e

# Test Elasticsearch connectivity
sudo filebeat test output -e

# View live logs
sudo journalctl -u filebeat -f

# View last 50 log lines
sudo journalctl -u filebeat -n 50 --no-pager

# Run filebeat manually with verbose output
sudo /usr/share/filebeat/bin/filebeat \
  --environment systemd \
  -c /etc/filebeat/filebeat.yml \
  --path.home /usr/share/filebeat \
  --path.config /etc/filebeat \
  --path.data /var/lib/filebeat \
  --path.logs /var/log/filebeat \
  -e 2>&1 | head -80
```

### 8.2 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Log input is deprecated` | Using `type: log` in Filebeat 9.x | Change to `type: filestream` and add `id:` field |
| `http: server gave HTTP response to HTTPS client` | Wrong protocol for Kibana URL | Change `https://` to `http://` in `setup.kibana.host` |
| `SSL handshake error` | Self-signed cert not trusted | Add `ssl.verification_mode: none` |
| `permission denied` on log files | Filebeat can't read app log files | `chmod o+r` on log directories |
| `files too small to be ingested` | Files under 1024 bytes skipped | Add `prospector.scanner.fingerprint.length: 64` |
| `connection refused :9200` | Elasticsearch not running | `systemctl start elasticsearch` |
| `401 Unauthorized` | Wrong credentials | Verify username/password in config |
| High memory / goroutines | Too many files opened at once | Exclude large directories, add `close.on_state_change.inactive` |

### 8.3 Check Elasticsearch Index

```bash
# List all filebeat indices
curl -u elastic:"YOUR_PASSWORD" -k \
  "https://<ELK_SERVER_IP>:9200/_cat/indices/filebeat*?v&h=index,health,docs.count,store.size"

# Count PHP application documents
curl -u elastic:"YOUR_PASSWORD" -k \
  -H "Content-Type: application/json" \
  -XGET "https://<ELK_SERVER_IP>:9200/filebeat-*/_count" \
  -d '{"query": {"term": {"log_type": "php-application"}}}'

# Sample 3 PHP log documents
curl -u elastic:"YOUR_PASSWORD" -k \
  -H "Content-Type: application/json" \
  -XGET "https://<ELK_SERVER_IP>:9200/filebeat-*/_search?pretty" \
  -d '{
    "query": {"term": {"log_type": "php-application"}},
    "size": 3,
    "_source": ["app_name", "message", "@timestamp", "log.file.path"]
  }'
```

---

## 9. Performance Tuning

### 9.1 Filebeat — Prevent Resource Exhaustion

Add these settings when monitoring directories with many files:

```yaml
# In each filestream input block:
prospector.scanner.check_interval: 30s      # Scan every 30s (default: 10s)
close.on_state_change.inactive: 5m          # Close idle file handles after 5 min
prospector.scanner.fingerprint.length: 64   # Support small files < 1024 bytes
prospector.scanner.fingerprint.offset: 0

# Global queue settings
queue.mem:
  events: 1024
  flush.min_events: 512
  flush.timeout: 10s

# Output throttling
output.elasticsearch:
  worker: 1
  bulk_max_size: 512
```

### 9.2 Check Resource Usage

```bash
# Monitor Filebeat memory and CPU
watch -n 5 'ps aux | grep filebeat | grep -v grep'

# Count open file handles
watch -n 5 'ls /proc/$(pgrep filebeat)/fd | wc -l'

# Check system load
uptime
```

### 9.3 Warning Signs

| Metric | Safe | Warning | Critical |
|--------|------|---------|----------|
| Open files | < 500 | 500–5000 | > 10,000 |
| Goroutines | < 500 | 500–5000 | > 50,000 |
| Memory (RSS) | < 500 MB | 500 MB–2 GB | > 4 GB |
| CPU Load (4 core) | < 2.0 | 2.0–4.0 | > 4.0 |

### 9.4 ILM — Auto-delete Old Indices

```bash
curl -u elastic:"YOUR_PASSWORD" -k \
  -H "Content-Type: application/json" \
  -XPUT "https://<ELK_SERVER_IP>:9200/_ilm/policy/filebeat-policy" \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_size": "5GB",
              "max_age": "7d"
            }
          }
        },
        "delete": {
          "min_age": "30d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }'
```

---

## 10. Security Recommendations

### 10.1 Use a Dedicated Filebeat User in Elasticsearch

```bash
# Create a role with minimal permissions
curl -u elastic:"YOUR_PASSWORD" -k \
  -H "Content-Type: application/json" \
  -XPOST "https://<ELK_SERVER_IP>:9200/_security/role/filebeat_writer" \
  -d '{
    "cluster": ["monitor", "manage_ilm", "manage_index_templates"],
    "indices": [{
      "names": ["filebeat-*"],
      "privileges": ["write", "create_index", "manage"]
    }]
  }'

# Create a dedicated filebeat user
curl -u elastic:"YOUR_PASSWORD" -k \
  -H "Content-Type: application/json" \
  -XPOST "https://<ELK_SERVER_IP>:9200/_security/user/filebeat_ingest" \
  -d '{
    "password": "StrongPassword123!",
    "roles": ["filebeat_writer"],
    "full_name": "Filebeat Ingest User"
  }'
```

Then update all `filebeat.yml` files to use `filebeat_ingest` instead of `elastic`.

### 10.2 Restrict Elasticsearch Access by IP

```bash
# On ELK server — only allow known app server IPs
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  source address="<APP_SERVER_IP>/32" port port="9200" protocol="tcp" accept'

# Block all other external access to 9200
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" \
  port port="9200" protocol="tcp" reject'

sudo firewall-cmd --reload
```

### 10.3 Use SSL Certificate for Kibana

```bash
# Generate a self-signed cert for Kibana
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/kibana/kibana.key \
  -out /etc/kibana/kibana.crt \
  -subj "/CN=<ELK_SERVER_IP>"

# Update kibana.yml
server.ssl.enabled: true
server.ssl.certificate: /etc/kibana/kibana.crt
server.ssl.key: /etc/kibana/kibana.key
```

---

## Quick Reference

### Service Management

```bash
# Elasticsearch
sudo systemctl start|stop|restart|status elasticsearch

# Kibana
sudo systemctl start|stop|restart|status kibana

# Filebeat
sudo systemctl start|stop|restart|status filebeat
```

### Key File Locations

| File | Path |
|------|------|
| Elasticsearch config | `/etc/elasticsearch/elasticsearch.yml` |
| Elasticsearch JVM | `/etc/elasticsearch/jvm.options` |
| Kibana config | `/etc/kibana/kibana.yml` |
| Filebeat config | `/etc/filebeat/filebeat.yml` |
| Filebeat modules | `/etc/filebeat/modules.d/` |
| Filebeat registry | `/var/lib/filebeat/registry/` |
| Elasticsearch logs | `/var/log/elasticsearch/` |
| Kibana logs | `/var/log/kibana/` |
| Filebeat logs | `/var/log/filebeat/` |

### Useful Elasticsearch API Calls

```bash
BASE="https://<ELK_IP>:9200"
AUTH='-u elastic:"YOUR_PASSWORD"'

# Cluster health
curl $AUTH -k "$BASE/_cluster/health?pretty"

# List all indices
curl $AUTH -k "$BASE/_cat/indices?v"

# List data streams
curl $AUTH -k "$BASE/_data_stream/filebeat-*?pretty"

# Index stats
curl $AUTH -k "$BASE/filebeat-*/_stats?pretty"

# Delete an index
curl $AUTH -k -XDELETE "$BASE/.ds-filebeat-9.3.0-2026.03.09-000001"
```

---

*Guide prepared for: Oracle Linux 9.7 | Elastic Stack 9.3.0 | March 2026*
