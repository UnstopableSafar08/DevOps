# Loki Cluster Setup: Read and Write Node Separation with HAProxy

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Node Roles and IP Assignment](#node-roles-and-ip-assignment)
- [Prerequisites](#prerequisites)
- [Step 1: Install and Configure MinIO (Shared Object Storage)](#step-1-install-and-configure-minio-shared-object-storage)
- [Step 2: Install and Configure Loki Write Node](#step-2-install-and-configure-loki-write-node)
- [Step 3: Install and Configure Loki Read Node](#step-3-install-and-configure-loki-read-node)
- [Step 4: Install and Configure HAProxy](#step-4-install-and-configure-haproxy)
- [Step 5: Configure Promtail on Application Nodes](#step-5-configure-promtail-on-application-nodes)
- [Step 6: Configure Grafana to Use the Cluster](#step-6-configure-grafana-to-use-the-cluster)
- [Step 7: Verify the Cluster](#step-7-verify-the-cluster)
- [Cluster Operations and Maintenance](#cluster-operations-and-maintenance)

---

## Architecture Overview

Loki in Simple Scalable Deployment (SSD) mode separates the log ingestion path from the log query path. This allows independent scaling of reads and writes and prevents heavy query loads from affecting log ingestion.

```
                        +---------------------------+
                        |  App Nodes (Promtail)     |
                        |  10.10.10.10 - 10.10.10.13|
                        +-------------+-------------+
                                      |
                          POST /loki/api/v1/push
                                      |
                        +-------------v-------------+
                        |        HAProxy            |
                        |     10.10.10.1 :3100      |
                        |                           |
                        |  Routes by HTTP method:   |
                        |  POST  --> Write Node     |
                        |  GET   --> Read Node      |
                        +------+------------+-------+
                               |            |
               +---------------v--+    +----v--------------+
               |  Loki Write Node |    |  Loki Read Node   |
               |   10.10.10.2     |    |   10.10.10.3      |
               |                  |    |                   |
               |  Components:     |    |  Components:      |
               |  - Distributor   |    |  - Query Frontend |
               |  - Ingester      |    |  - Querier        |
               +--------+---------+    |  - Compactor      |
                        |              |  - Index Gateway  |
                        |              +--------+----------+
                        |                       |
                        +-----------+-----------+
                                    |
                        +-----------v-----------+
                        |    MinIO              |
                        |   10.10.10.1 :9000    |
                        |                       |
                        |  Shared object store  |
                        |  for chunks and index |
                        +-----------------------+
                                    |
                        +-----------v-----------+
                        |    Grafana            |
                        |   10.10.10.1 :3000    |
                        |                       |
                        |  Queries via HAProxy  |
                        |  :3100 (read path)    |
                        +-----------------------+
```

### Data Flow

**Write path (log ingestion)**

```
Promtail --> HAProxy :3100 --> Loki Write Node --> MinIO (chunks + index)
```

**Read path (log queries)**

```
Grafana --> HAProxy :3100 --> Loki Read Node --> MinIO (chunks + index)
```

### Loki Component Targets

| Target Mode | Components Included | Node |
|---|---|---|
| write | Distributor, Ingester | 10.10.10.2 |
| read | Query Frontend, Querier | 10.10.10.3 |
| backend | Compactor, Index Gateway, Ruler, Query Scheduler | 10.10.10.3 |

The read node in this setup runs both `read` and `backend` targets since there is only one read node. In a larger cluster these would be separated further.

---

## Node Roles and IP Assignment

| Node | IP | Role | Services |
|---|---|---|---|
| haproxy-node | 10.10.10.1 | Load Balancer and Storage | HAProxy, MinIO, Grafana |
| loki-write | 10.10.10.2 | Write Path | Loki (write target) |
| loki-read | 10.10.10.3 | Read Path and Backend | Loki (read + backend target) |
| app-node-01 | 10.10.10.10 | Application | Promtail, Node Exporter |
| app-node-02 | 10.10.10.11 | Application | Promtail, Node Exporter |
| app-node-03 | 10.10.10.12 | Application | Promtail, Node Exporter |
| app-node-04 | 10.10.10.13 | Application | Promtail, Node Exporter |

---

## Prerequisites

### All Nodes

```bash
sudo dnf install -y wget curl tar unzip
```

### Firewall Rules Summary

| Node | Port | Direction | Purpose |
|---|---|---|---|
| haproxy-node | 3100 | Inbound | Loki API (from Promtail and Grafana) |
| haproxy-node | 9000 | Inbound | MinIO API (from Loki nodes) |
| haproxy-node | 9001 | Inbound | MinIO Console |
| haproxy-node | 3000 | Inbound | Grafana UI |
| loki-write | 3100 | Inbound | Loki HTTP (from HAProxy) |
| loki-write | 9095 | Inbound | Loki gRPC (memberlist ring) |
| loki-write | 7946 | Inbound | Memberlist gossip |
| loki-read | 3100 | Inbound | Loki HTTP (from HAProxy) |
| loki-read | 9095 | Inbound | Loki gRPC (memberlist ring) |
| loki-read | 7946 | Inbound | Memberlist gossip |
| app-nodes | 9100 | Inbound | Node Exporter (from Prometheus) |

---

## Step 1: Install and Configure MinIO (Shared Object Storage)

MinIO provides the shared S3-compatible object store that both the write node and read node use to persist log chunks and TSDB index data. Run all commands in this section on **10.10.10.1 (haproxy-node)**.

Both Loki nodes must point to the same object store. This is what allows the write node to persist data and the read node to query it independently.

**Create MinIO user and directories**

```bash
sudo useradd --no-create-home --shell /bin/false minio
sudo mkdir -p /var/lib/minio/data
sudo chown -R minio:minio /var/lib/minio
```

**Download and install MinIO**

```bash
cd /tmp
wget https://dl.min.io/server/minio/release/linux-amd64/minio
sudo mv minio /usr/local/bin/minio
sudo chmod +x /usr/local/bin/minio
```

**Create MinIO environment file**

```bash
sudo tee /etc/minio.env > /dev/null <<'EOF'
MINIO_ROOT_USER=lokiadmin
MINIO_ROOT_PASSWORD=lokipassword
MINIO_VOLUMES=/var/lib/minio/data
MINIO_OPTS="--address :9000 --console-address :9001"
EOF

sudo chmod 640 /etc/minio.env
sudo chown minio:minio /etc/minio.env
```

**Create MinIO systemd service**

```bash
sudo tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO Object Storage
After=network.target

[Service]
User=minio
Group=minio
EnvironmentFile=/etc/minio.env
ExecStart=/usr/local/bin/minio server $MINIO_VOLUMES $MINIO_OPTS
Restart=on-failure
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
```

**Start MinIO**

```bash
sudo systemctl daemon-reload
sudo systemctl start minio
sudo systemctl enable minio
sudo systemctl status minio
```

**Open firewall for MinIO**

```bash
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --permanent --add-port=9001/tcp
sudo firewall-cmd --reload
```

**Create the Loki bucket in MinIO**

```bash
# Install MinIO client
cd /tmp
wget https://dl.min.io/client/mc/release/linux-amd64/mc
sudo mv mc /usr/local/bin/mc
sudo chmod +x /usr/local/bin/mc

# Configure MinIO client
mc alias set local http://10.10.10.1:9000 lokiadmin lokipassword

# Create bucket for Loki
mc mb local/loki-chunks

# Verify bucket was created
mc ls local
```

---

## Step 2: Install and Configure Loki Write Node

Run all commands in this section on **10.10.10.2 (loki-write)**.

The write node runs the `write` target which includes the Distributor and Ingester components. The Distributor receives incoming log streams from Promtail and distributes them to Ingesters. The Ingester builds log chunks and flushes them to the shared MinIO object store.

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

**Create Loki write node configuration**

```bash
sudo tee /etc/loki/loki.yml > /dev/null <<'EOF'
auth_enabled: false

# This node runs the write target only
target: write

server:
  http_listen_port: 3100
  grpc_listen_port: 9095
  log_level: warn

# Memberlist is used for the ingester ring and distributor ring
# Both write and read nodes must list each other here
memberlist:
  join_members:
    - 10.10.10.2:7946
    - 10.10.10.3:7946
  bind_port: 7946

common:
  path_prefix: /var/lib/loki
  replication_factor: 1
  ring:
    instance_addr: 10.10.10.2
    kvstore:
      store: memberlist

# Use MinIO as shared object storage
storage_config:
  aws:
    s3: http://lokiadmin:lokipassword@10.10.10.1:9000/loki-chunks
    s3forcepathstyle: true
  tsdb_shipper:
    active_index_directory: /var/lib/loki/tsdb-index
    cache_location: /var/lib/loki/tsdb-cache
    cache_ttl: 24h

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: index_
        period: 24h

ingester:
  chunk_idle_period: 1h
  max_chunk_age: 2h
  chunk_target_size: 1048576
  chunk_retain_period: 30s
  wal:
    dir: /var/lib/loki/wal

limits_config:
  retention_period: 72h
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32
  max_streams_per_user: 10000
  max_entries_limit_per_query: 50000

# Compactor runs on the read/backend node, not here
# Write node does not need compactor config
EOF
```

**Set permissions**

```bash
sudo chown -R loki:loki /etc/loki /var/lib/loki /var/log/loki
```

**Create Loki write node systemd service**

```bash
sudo tee /etc/systemd/system/loki.service > /dev/null <<'EOF'
[Unit]
Description=Loki Write Node
After=network.target

[Service]
User=loki
Group=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/loki.yml
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=loki-write

[Install]
WantedBy=multi-user.target
EOF
```

**Open firewall ports**

```bash
sudo firewall-cmd --permanent --add-port=3100/tcp   # Loki HTTP
sudo firewall-cmd --permanent --add-port=9095/tcp   # Loki gRPC
sudo firewall-cmd --permanent --add-port=7946/tcp   # Memberlist
sudo firewall-cmd --permanent --add-port=7946/udp   # Memberlist UDP
sudo firewall-cmd --reload
```

**Start the write node**

```bash
sudo systemctl daemon-reload
sudo systemctl start loki
sudo systemctl enable loki
sudo systemctl status loki
```

**Verify write node is ready**

```bash
curl -s http://10.10.10.2:3100/ready
# Expected: ready

# Check which components are running
curl -s http://10.10.10.2:3100/services
```

---

## Step 3: Install and Configure Loki Read Node

Run all commands in this section on **10.10.10.3 (loki-read)**.

The read node runs the `read` and `backend` targets. The `read` target includes Query Frontend and Querier. The `backend` target includes the Compactor, Index Gateway, and Query Scheduler. The Compactor handles log retention deletion, so the 72-hour retention policy is enforced here.

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

**Create Loki read node configuration**

```bash
sudo tee /etc/loki/loki.yml > /dev/null <<'EOF'
auth_enabled: false

# This node runs the read and backend targets
target: read,backend

server:
  http_listen_port: 3100
  grpc_listen_port: 9095
  log_level: warn

memberlist:
  join_members:
    - 10.10.10.2:7946
    - 10.10.10.3:7946
  bind_port: 7946

common:
  path_prefix: /var/lib/loki
  replication_factor: 1
  ring:
    instance_addr: 10.10.10.3
    kvstore:
      store: memberlist

# Same MinIO shared object storage as write node
storage_config:
  aws:
    s3: http://lokiadmin:lokipassword@10.10.10.1:9000/loki-chunks
    s3forcepathstyle: true
  tsdb_shipper:
    active_index_directory: /var/lib/loki/tsdb-index
    cache_location: /var/lib/loki/tsdb-cache
    cache_ttl: 24h

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: index_
        period: 24h

# 72-hour retention is enforced by the compactor running on this node
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
  delete_request_store: s3

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 200

querier:
  max_concurrent: 10

query_scheduler:
  max_outstanding_requests_per_tenant: 2048

frontend:
  max_outstanding_per_tenant: 2048

chunk_store_config:
  chunk_cache_config:
    embedded_cache:
      enabled: true
      max_size_mb: 300
EOF
```

**Set permissions**

```bash
sudo chown -R loki:loki /etc/loki /var/lib/loki /var/log/loki
```

**Create Loki read node systemd service**

```bash
sudo tee /etc/systemd/system/loki.service > /dev/null <<'EOF'
[Unit]
Description=Loki Read Node
After=network.target

[Service]
User=loki
Group=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/loki.yml
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=loki-read

[Install]
WantedBy=multi-user.target
EOF
```

**Open firewall ports**

```bash
sudo firewall-cmd --permanent --add-port=3100/tcp
sudo firewall-cmd --permanent --add-port=9095/tcp
sudo firewall-cmd --permanent --add-port=7946/tcp
sudo firewall-cmd --permanent --add-port=7946/udp
sudo firewall-cmd --reload
```

**Start the read node**

```bash
sudo systemctl daemon-reload
sudo systemctl start loki
sudo systemctl enable loki
sudo systemctl status loki
```

**Verify read node is ready**

```bash
curl -s http://10.10.10.3:3100/ready
# Expected: ready

curl -s http://10.10.10.3:3100/services
```

---

## Step 4: Install and Configure HAProxy

Run all commands in this section on **10.10.10.1 (haproxy-node)**.

HAProxy routes traffic based on the HTTP method and request path. Write requests (POST to /loki/api/v1/push) go to the write node. All read requests (GET) go to the read node. This ensures the write path and read path are completely isolated at the network level.

**Install HAProxy**

```bash
sudo dnf install -y haproxy
```

**Create HAProxy configuration**

```bash
sudo tee /etc/haproxy/haproxy.cfg > /dev/null <<'EOF'
#---------------------------------------------------------------------
# Global settings
#---------------------------------------------------------------------
global
    log         /dev/log local0
    log         /dev/log local1 notice
    chroot      /var/lib/haproxy
    pidfile     /var/run/haproxy.pid
    maxconn     50000
    user        haproxy
    group       haproxy
    daemon

    stats socket /var/lib/haproxy/stats

#---------------------------------------------------------------------
# Default settings
#---------------------------------------------------------------------
defaults
    mode                    http
    log                     global
    option                  httplog
    option                  dontlognull
    option                  forwardfor
    option                  http-server-close
    retries                 3
    timeout connect         5s
    timeout client          60s
    timeout server          60s
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

#---------------------------------------------------------------------
# HAProxy stats page
# Access at: http://10.10.10.1:8080/stats
#---------------------------------------------------------------------
listen stats
    bind *:8080
    stats enable
    stats uri /stats
    stats refresh 10s
    stats realm HAProxy\ Statistics
    stats auth admin:admin123
    stats show-legends
    stats show-node

#---------------------------------------------------------------------
# Loki frontend - single entry point on port 3100
# Routes to write or read backend based on HTTP method and path
#---------------------------------------------------------------------
frontend loki_frontend
    bind *:3100
    mode http

    # ACL: identify write requests (Promtail push endpoint)
    acl is_push_request  path_beg /loki/api/v1/push
    acl is_post_method   method   POST

    # ACL: identify ready and metrics checks
    acl is_ready         path     /ready
    acl is_metrics       path_beg /metrics

    # Route POST push requests to write backend
    use_backend loki_write_backend  if is_push_request is_post_method

    # Route all other requests (queries) to read backend
    default_backend loki_read_backend

#---------------------------------------------------------------------
# Loki write backend
# Handles: POST /loki/api/v1/push
# Target:  Loki write node (10.10.10.2)
#---------------------------------------------------------------------
backend loki_write_backend
    mode http
    balance roundrobin
    option httpchk GET /ready
    http-check expect string ready

    server loki-write 10.10.10.2:3100 check inter 10s rise 2 fall 3

#---------------------------------------------------------------------
# Loki read backend
# Handles: all GET queries from Grafana
# Target:  Loki read node (10.10.10.3)
#---------------------------------------------------------------------
backend loki_read_backend
    mode http
    balance roundrobin
    option httpchk GET /ready
    http-check expect string ready

    server loki-read 10.10.10.3:3100 check inter 10s rise 2 fall 3

EOF
```

**Validate the HAProxy configuration**

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
# Expected: Configuration file is valid
```

**Open firewall ports**

```bash
sudo firewall-cmd --permanent --add-port=3100/tcp   # Loki API
sudo firewall-cmd --permanent --add-port=8080/tcp   # HAProxy stats
sudo firewall-cmd --permanent --add-port=3000/tcp   # Grafana
sudo firewall-cmd --reload
```

**Start and enable HAProxy**

```bash
sudo systemctl start haproxy
sudo systemctl enable haproxy
sudo systemctl status haproxy
```

**Verify HAProxy is routing correctly**

```bash
# Check write backend health
curl -s http://10.10.10.1:3100/ready
# Expected: ready (served via HAProxy -> read node)

# Check HAProxy stats page
curl -s -u admin:admin123 http://10.10.10.1:8080/stats | grep -i loki
```

The stats page is also accessible in a browser at `http://10.10.10.1:8080/stats`.

---

## Step 5: Configure Promtail on Application Nodes

Run all commands in this section on **each application node** (10.10.10.10 to 10.10.10.13).

Promtail must point to the HAProxy address on port 3100, not directly to the Loki write node. This ensures all traffic flows through the load balancer and can be rerouted if the backend changes.

**Install Promtail**

```bash
sudo useradd --no-create-home --shell /bin/false promtail
sudo mkdir -p /etc/promtail /var/lib/promtail

cd /tmp
wget https://github.com/grafana/loki/releases/download/v3.4.2/promtail-linux-amd64.zip
unzip promtail-linux-amd64.zip
sudo mv promtail-linux-amd64 /usr/local/bin/promtail
sudo chmod +x /usr/local/bin/promtail
```

**Create Promtail configuration**

Replace `<HOSTNAME>` with the actual hostname of the node being configured.

```bash
sudo tee /etc/promtail/promtail.yml > /dev/null <<'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  # Point to HAProxy, not directly to the write node
  - url: http://10.10.10.1:3100/loki/api/v1/push
    # Retry configuration for resilience
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    timeout: 10s

scrape_configs:

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
sudo dnf install -y acl
sudo setfacl -m u:promtail:r /var/log/messages
sudo setfacl -m u:promtail:r /var/log/secure
sudo setfacl -m u:promtail:r /var/log/cron
sudo setfacl -R -m u:promtail:r /var/apps/gds-api/gds-api/storage/logs/
sudo setfacl -R -m u:promtail:r /var/apps/gds-admin/gds-admin/storage/logs/
sudo setfacl -R -m u:promtail:r /var/apps/gds-web/gds-web/storage/logs/
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

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start promtail
sudo systemctl enable promtail
sudo systemctl status promtail
```

---

## Step 6: Configure Grafana to Use the Cluster

Run all commands in this section on **10.10.10.1 (haproxy-node)** where Grafana is installed.

Grafana must use HAProxy as the Loki endpoint, not the read node directly. HAProxy will route all GET requests to the read node automatically.

**Add Loki data source pointing to HAProxy**

1. Open Grafana at `http://10.10.10.1:3000`
2. Go to Connections > Data Sources > Add new data source
3. Select Loki
4. Configure as follows:

```
Name:  Loki-Cluster
URL:   http://10.10.10.1:3100
```

5. Click Save and Test

Grafana sends GET requests to HAProxy port 3100. HAProxy routes these to the read node at 10.10.10.3 because they are not POST push requests. The read node queries MinIO and returns the log data.

---

## Step 7: Verify the Cluster

### Check Node Status

```bash
# Check write node is ready
curl -s http://10.10.10.2:3100/ready

# Check read node is ready
curl -s http://10.10.10.3:3100/ready

# Check via HAProxy (should return ready from read node)
curl -s http://10.10.10.1:3100/ready
```

### Check All Services Running on Each Node

```bash
# Write node - should list distributor and ingester
curl -s http://10.10.10.2:3100/services

# Read node - should list query-frontend, querier, compactor, index-gateway
curl -s http://10.10.10.3:3100/services
```

### Check Memberlist Ring (Cluster Gossip)

```bash
# Check ingester ring membership from write node
curl -s http://10.10.10.2:3100/ring | head -30

# Check from read node
curl -s http://10.10.10.3:3100/ring | head -30
```

### Check MinIO Has Data

```bash
# On haproxy-node - list chunks being stored
mc ls local/loki-chunks --recursive | head -20

# Check bucket size
mc du local/loki-chunks
```

### Verify HAProxy Is Routing Correctly

```bash
# This is a GET request so HAProxy should route to read node (10.10.10.3)
curl -v http://10.10.10.1:3100/loki/api/v1/labels 2>&1 | grep -E "Connected|HTTP"

# Check HAProxy backend status
curl -s -u admin:admin123 "http://10.10.10.1:8080/stats;csv" | \
  grep loki | awk -F',' '{print $1, $2, $18, $19}'
# Output columns: pxname, svname, status, weight
# Status should show: UP for both backends
```

### Send a Test Log Entry

```bash
# Send a test log directly through HAProxy (POST goes to write node)
curl -s -X POST http://10.10.10.1:3100/loki/api/v1/push \
  -H "Content-Type: application/json" \
  -d '{
    "streams": [
      {
        "stream": {"job": "test", "host": "manual"},
        "values": [
          ["'"$(date +%s%N)"'", "test log entry from cluster verification"]
        ]
      }
    ]
  }'
# Expected: HTTP 204 No Content (empty response = success)

# Query that log back through HAProxy (GET goes to read node)
curl -s -G "http://10.10.10.1:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="test"}' \
  --data-urlencode 'limit=1' | python3 -m json.tool
```

If the query returns the test log entry, the full write-to-read path through MinIO is working correctly.

### Verify 72-Hour Retention

```bash
# Check retention is configured in compactor (runs on read node)
curl -s http://10.10.10.3:3100/config | python3 -m json.tool | grep -A2 retention

# Check compactor is running
curl -s http://10.10.10.3:3100/services | grep compactor
```

---

## Cluster Operations and Maintenance

### Restart Order

Always restart nodes in this order to avoid data loss:

```
1. Stop Promtail on all app nodes first  (stop sending new data)
2. Stop Loki write node                  (allow ingesters to flush to MinIO)
3. Stop Loki read node                   (safe to stop query path)
4. Stop HAProxy                          (stop routing)
5. Stop MinIO last                       (shared storage, stop last)

Reverse the order for startup:
1. Start MinIO
2. Start HAProxy
3. Start Loki write node
4. Start Loki read node
5. Start Promtail on all app nodes
```

### Check Write Node Ingester Flush Status

```bash
# Before restarting write node, flush ingesters to MinIO manually
curl -s -X POST http://10.10.10.2:3100/flush

# Then verify all chunks are flushed
curl -s http://10.10.10.2:3100/metrics | grep ingester_chunks_flushed
```

### Monitor Resource Usage

```bash
# Check write node metrics
curl -s http://10.10.10.2:3100/metrics | grep -E "^loki_ingester|^loki_distributor"

# Check read node metrics
curl -s http://10.10.10.3:3100/metrics | grep -E "^loki_query|^loki_compactor"

# Check HAProxy connection counts
curl -s -u admin:admin123 "http://10.10.10.1:8080/stats;csv" | \
  grep loki | awk -F',' '{print $1, $2, $7, $8, $9}'
# Output columns: pxname, svname, current_sessions, max_sessions, total_sessions
```

### Service Port Reference

| Node | Service | Port | Purpose |
|---|---|---|---|
| 10.10.10.1 | HAProxy | 3100 | Loki API (write and read routing) |
| 10.10.10.1 | HAProxy Stats | 8080 | Dashboard at /stats |
| 10.10.10.1 | MinIO API | 9000 | Object storage API |
| 10.10.10.1 | MinIO Console | 9001 | Web UI for MinIO |
| 10.10.10.1 | Grafana | 3000 | Dashboard UI |
| 10.10.10.2 | Loki Write | 3100 | HTTP API |
| 10.10.10.2 | Loki Write | 9095 | gRPC |
| 10.10.10.2 | Loki Write | 7946 | Memberlist gossip |
| 10.10.10.3 | Loki Read | 3100 | HTTP API |
| 10.10.10.3 | Loki Read | 9095 | gRPC |
| 10.10.10.3 | Loki Read | 7946 | Memberlist gossip |
| All app nodes | Promtail | 9080 | Promtail metrics and targets |
