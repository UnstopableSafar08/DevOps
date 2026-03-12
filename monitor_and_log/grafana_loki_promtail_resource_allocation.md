# Grafana + Loki + Promtail + Prometheus Resource Allocation Guide

## Deployment Models Covered

This guide covers resource allocation for two deployment models:

- Single Server: all tools run on one machine
- Separate Servers: each tool runs on its own dedicated machine

---

## Table of Contents

- [Deployment Model Comparison](#deployment-model-comparison)
- [Model 1: Single Server Deployment](#model-1-single-server-deployment)
  - [Single Server Architecture](#single-server-architecture)
  - [Single Server RAM Allocation](#single-server-ram-allocation)
  - [Single Server CPU Allocation](#single-server-cpu-allocation)
  - [Single Server Disk Allocation](#single-server-disk-allocation)
  - [Single Server OS Tuning](#single-server-os-tuning)
  - [Single Server Systemd Resource Controls](#single-server-systemd-resource-controls)
  - [Single Server Application Configs](#single-server-application-configs)
- [Model 2: Separate Server Deployment](#model-2-separate-server-deployment)
  - [Separate Server Architecture](#separate-server-architecture)
  - [Loki Server](#loki-server)
  - [Prometheus Server](#prometheus-server)
  - [Grafana Server](#grafana-server)
  - [Promtail on App Nodes](#promtail-on-app-nodes)
- [Resource Comparison Table](#resource-comparison-table)
- [Which Model to Choose](#which-model-to-choose)

---

## Deployment Model Comparison

| Factor | Single Server | Separate Servers |
|---|---|---|
| Minimum servers needed | 1 | 4 (Loki, Prometheus, Grafana, App nodes) |
| Total RAM required | 8 GB minimum | 2 GB per dedicated server minimum |
| Cost | Low | Higher |
| Failure impact | All tools go down together | One tool fails, others continue |
| Resource contention | High (tools compete for RAM and CPU) | None (each tool has full resources) |
| Scaling | Limited (fixed single machine) | Each tool scales independently |
| Maintenance complexity | Low | Higher |
| Suitable for | Dev, UAT, small production | Production, high availability |
| Monitoring the monitor | Difficult | Easy (Prometheus on its own server) |

---

## Model 1: Single Server Deployment

All tools run on one server. This model requires careful resource partitioning to prevent any single tool from starving the others.

### Single Server Architecture

```
+--------------------------------------------------------------+
|  Single Observability Server                                 |
|  Example specs: 8 GB RAM, 4 CPU cores, 100 GB disk          |
|                                                              |
|  +----------+  +------------+  +---------+  +----------+   |
|  |  Loki    |  | Prometheus |  | Grafana |  | Promtail |   |
|  |  :3100   |  |   :9090    |  |  :3000  |  |  :9080   |   |
|  | 3072 MB  |  |  1024 MB   |  | 512 MB  |  | 256 MB   |   |
|  | 2.0 CPU  |  |  0.5 CPU   |  | 0.5 CPU |  | 0.25 CPU |   |
|  | 60 GB    |  |  10 GB     |  | 5 GB    |  | 0.5 GB   |   |
|  +----------+  +------------+  +---------+  +----------+   |
|                                                              |
|  Remaining: 1152 MB RAM for OS + page cache                  |
|             0.75 CPU for OS and I/O                          |
|             24.5 GB disk for OS, logs, tmp, headroom         |
+--------------------------------------------------------------+
          ^                    ^
          |                    |
   Promtail push          Grafana queries
   from app nodes         from browser
   (10.10.10.10-13)
```

---

### Single Server RAM Allocation

Total available RAM: 8192 MB

```
+-------------------------------------------------------------------+
|  Service          | Allocated  | Purpose                          |
+-------------------------------------------------------------------+
|  Loki             | 3072 MB    | Chunk cache, ingester, querier   |
|  Prometheus       | 1024 MB    | Time series head block, WAL      |
|  Grafana          |  512 MB    | Dashboard rendering, SQLite      |
|  Promtail         |  256 MB    | Log batching, pipeline stages    |
|  Node Exporter    |   64 MB    | Metric collection                |
|  OS kernel        |  512 MB    | Network stack, process table     |
|  Page cache       | 2752 MB    | Disk read cache (OS managed)     |
+-------------------------------------------------------------------+
|  Total            | 8192 MB                                       |
+-------------------------------------------------------------------+
```

Page cache note: The OS automatically uses all RAM not claimed by processes
as a disk read cache. For Loki this dramatically speeds up chunk reads. Do
not try to eliminate page cache by allocating all RAM to services. The
2752 MB reserved here will be used by the OS as cache automatically.

### Single Server CPU Allocation

Total available CPU: 4 cores (400% in systemd CPUQuota notation)

```
+-------------------------------------------------------------------+
|  Service          | CPUQuota | CPUWeight | Notes                  |
+-------------------------------------------------------------------+
|  Loki             | 200%     | 60        | Ingestion + queries    |
|  Prometheus       |  50%     | 20        | Scraping + compaction  |
|  Grafana          |  50%     | 15        | HTTP + alert eval      |
|  Promtail         |  25%     | 10        | File tailing           |
|  Node Exporter    |  10%     |  5        | Metric collection      |
|  OS reserved      |  65%     |  -        | Kernel, I/O, network   |
+-------------------------------------------------------------------+
|  Total            | 400%                                          |
+-------------------------------------------------------------------+
```

CPUWeight controls relative priority when all services compete for CPU
simultaneously. Loki gets the most because it handles both ingestion
bursts from Promtail and query requests from Grafana at the same time.

### Single Server Disk Allocation

Total available disk: 100 GB

> Default Path : `/var/lib/`

```
+-------------------------------------------------------------------+
|  Path                    | Size  | Purpose                        |
+-------------------------------------------------------------------+
|  / (root OS partition)   | 10 GB | OS, binaries, config           |
|  /var/lib/loki           | 60 GB | Chunks, WAL, index, cache      |
|  /var/lib/loki/chunks    | 45 GB | Compressed log chunks          |
|  /var/lib/loki/wal       |  5 GB | Write-ahead log (crash safety) |
|  /var/lib/loki/tsdb-*    |  5 GB | TSDB index and cache           |
|  /var/lib/loki/compact   |  5 GB | Compactor working directory    |
|  /var/lib/prometheus     | 10 GB | TSDB blocks, WAL               |
|  /var/lib/grafana        |  5 GB | SQLite DB, plugins, images     |
|  /var/lib/promtail       |  1 GB | Positions file                 |
|  /var/log                |  5 GB | Journald, service logs         |
|  /tmp                    |  2 GB | Temporary files                |
|  Unallocated headroom    |  7 GB | Growth buffer                  |
+-------------------------------------------------------------------+
|  Total                   | 100 GB                                 |
+-------------------------------------------------------------------+
```

### Single Server OS Tuning

Apply these settings on the single observability server.

```bash
# File descriptor and inotify limits
sudo tee /etc/security/limits.d/observability.conf > /dev/null <<'EOF'
loki        soft    nofile      65536
loki        hard    nofile      65536
loki        soft    nproc       32768
loki        hard    nproc       32768
prometheus  soft    nofile      65536
prometheus  hard    nofile      65536
prometheus  soft    nproc       32768
prometheus  hard    nproc       32768
grafana     soft    nofile      16384
grafana     hard    nofile      16384
promtail    soft    nofile      16384
promtail    hard    nofile      16384
EOF
```

```bash
# Kernel parameters
sudo tee /etc/sysctl.d/99-observability.conf > /dev/null <<'EOF'
# System-wide file descriptor limit
fs.file-max = 524288

# Inotify for Promtail file watching
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512

# Network buffers for log ingestion
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.somaxconn = 32768
net.ipv4.tcp_max_syn_backlog = 16384

# Memory behavior
# Low swappiness: prefer RAM over swap for all services
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.max_map_count = 262144
EOF

sudo sysctl -p /etc/sysctl.d/99-observability.conf
```

```bash
# Journal size cap to protect /var/log
sudo mkdir -p /etc/systemd/journald.conf.d/
sudo tee /etc/systemd/journald.conf.d/limits.conf > /dev/null <<'EOF'
[Journal]
SystemMaxUse=2G
SystemKeepFree=1G
SystemMaxFileSize=200M
MaxRetentionSec=7day
EOF
sudo systemctl restart systemd-journald
```

```bash
# Loki disk directories
sudo mkdir -p \
  /var/lib/loki/chunks \
  /var/lib/loki/wal \
  /var/lib/loki/tsdb-index \
  /var/lib/loki/tsdb-cache \
  /var/lib/loki/compactor \
  /var/lib/loki/rules
sudo chown -R loki:loki /var/lib/loki
```

### Single Server Systemd Resource Controls

#### Loki Service

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
RestartSec=10s
TimeoutStopSec=60s
StandardOutput=journal
StandardError=journal

# File descriptor limit
LimitNOFILE=65536
LimitNPROC=32768
LimitCORE=0

# Go runtime tuning
# GOGC=75: GC runs more often, keeps RAM lower at cost of slightly more CPU
# GOMEMLIMIT: hard ceiling at 2.75 GB, below systemd MemoryMax of 3 GB
# GOMAXPROCS=2: Loki uses up to 2 OS threads, matching CPUQuota
Environment=GOGC=75
Environment=GOMEMLIMIT=2952790016
Environment=GOMAXPROCS=2

# Systemd cgroup limits
CPUQuota=200%
CPUWeight=60
MemoryMax=3G
MemoryHigh=2750M
MemorySwapMax=0
IOWeight=60

[Install]
WantedBy=multi-user.target
EOF
```

#### Prometheus Service

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
  --storage.tsdb.wal-compression \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-lifecycle \
  --query.max-concurrency=4 \
  --query.timeout=2m
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

LimitNOFILE=65536
LimitNPROC=32768

# Go runtime tuning
# GOMEMLIMIT: hard ceiling at 900 MB, below systemd MemoryMax of 1 GB
Environment=GOGC=100
Environment=GOMEMLIMIT=943718400
Environment=GOMAXPROCS=1

CPUQuota=50%
CPUWeight=20
MemoryMax=1G
MemoryHigh=900M
MemorySwapMax=0
IOWeight=30

[Install]
WantedBy=multi-user.target
EOF
```

#### Grafana Service

```bash
sudo tee /etc/systemd/system/grafana-server.service > /dev/null <<'EOF'
[Unit]
Description=Grafana Dashboard Server
After=network.target

[Service]
User=grafana
Group=grafana
ExecStart=/usr/sbin/grafana-server \
  --config=/etc/grafana/grafana.ini \
  --homepath=/usr/share/grafana \
  --packaging=rpm
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

LimitNOFILE=16384
LimitNPROC=8192

Environment=GOGC=100
Environment=GOMEMLIMIT=503316480
Environment=GOMAXPROCS=1

CPUQuota=50%
CPUWeight=15
MemoryMax=512M
MemoryHigh=460M
MemorySwapMax=0
IOWeight=20

[Install]
WantedBy=multi-user.target
EOF
```

#### Promtail Service

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

LimitNOFILE=16384
LimitNPROC=8192

Environment=GOGC=100
Environment=GOMEMLIMIT=251658240
Environment=GOMAXPROCS=1

CPUQuota=25%
CPUWeight=10
MemoryMax=256M
MemoryHigh=220M
MemorySwapMax=0
IOWeight=20

[Install]
WantedBy=multi-user.target
EOF
```

```bash
# Apply all changes
sudo systemctl daemon-reload
sudo systemctl restart loki prometheus grafana-server promtail
```

### Single Server Application Configs

#### Loki Config for Single Server

The key difference from a dedicated server is smaller cache sizes and lower
concurrency limits to share RAM with Prometheus and Grafana.

```bash
sudo tee /etc/loki/loki.yml > /dev/null <<'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn
  http_server_read_timeout: 60s
  http_server_write_timeout: 60s

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

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

ingester:
  # Flush chunks to disk after 30m idle (frees RAM faster than 1h)
  chunk_idle_period: 30m
  max_chunk_age: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 30s
  concurrent_flushes: 2
  wal:
    dir: /var/lib/loki/wal
    checkpoint_duration: 5m
    flush_on_shutdown: true
    # Limit WAL replay memory on single server
    replay_memory_ceiling: 256MB

querier:
  # Reduced from default because CPU is shared with Prometheus and Grafana
  max_concurrent: 4
  query_timeout: 60s

query_range:
  split_queries_by_interval: 1h
  parallelise_shardable_queries: true
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        # Reduced cache: 128 MB (sharing RAM with other services)
        max_size_mb: 128
        ttl: 1h

compactor:
  working_directory: /var/lib/loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  # Reduced workers: minimize I/O competition with Prometheus
  retention_delete_worker_count: 30
  delete_request_store: filesystem

storage_config:
  tsdb_shipper:
    active_index_directory: /var/lib/loki/tsdb-index
    cache_location: /var/lib/loki/tsdb-cache
    cache_ttl: 24h

chunk_store_config:
  chunk_cache_config:
    embedded_cache:
      enabled: true
      # Reduced chunk cache: 256 MB (sharing RAM with other services)
      max_size_mb: 256
      ttl: 2h

limits_config:
  retention_period: 72h
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32
  max_streams_per_user: 10000
  max_entries_limit_per_query: 50000
  max_query_lookback: 72h
  max_query_length: 72h
  per_stream_rate_limit: 3MB
  per_stream_rate_limit_burst: 15MB

table_manager:
  retention_deletes_enabled: true
  retention_period: 72h
EOF
```

#### Prometheus Config for Single Server

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  # Reduced scrape frequency on shared server to lower CPU usage
  scrape_interval: 30s
  evaluation_interval: 30s
  scrape_timeout: 10s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node-observability-server"
    static_configs:
      - targets: ["localhost:9100"]

  - job_name: "loki"
    static_configs:
      - targets: ["localhost:3100"]

  - job_name: "node-app-01"
    static_configs:
      - targets: ["10.10.10.10:9100"]
        labels:
          instance: "app-node-01"

  - job_name: "node-app-02"
    static_configs:
      - targets: ["10.10.10.11:9100"]
        labels:
          instance: "app-node-02"

  - job_name: "node-app-03"
    static_configs:
      - targets: ["10.10.10.12:9100"]
        labels:
          instance: "app-node-03"

  - job_name: "node-app-04"
    static_configs:
      - targets: ["10.10.10.13:9100"]
        labels:
          instance: "app-node-04"
EOF
```

---

## Model 2: Separate Server Deployment

Each tool runs on its own dedicated server. Every server has its full
resources available to one service only. This eliminates resource
contention and allows independent scaling and failure isolation.

### Separate Server Architecture

```
+------------------+     +------------------+     +------------------+
|  Loki Server     |     | Prometheus Server|     |  Grafana Server  |
|  10.10.10.20     |     |  10.10.10.21     |     |  10.10.10.22     |
|                  |     |                  |     |                  |
|  Recommended:    |     |  Recommended:    |     |  Recommended:    |
|  4 GB RAM        |     |  4 GB RAM        |     |  2 GB RAM        |
|  2 CPU cores     |     |  2 CPU cores     |     |  2 CPU cores     |
|  100 GB disk     |     |  50 GB disk      |     |  20 GB disk      |
+--------+---------+     +--------+---------+     +--------+---------+
         ^                        ^                        |
         |                        |                        |
    Promtail push            Node Exporter            Queries Loki
    from app nodes           scrape from              Queries Prometheus
    (port 3100)              app nodes (9100)         (port 3100, 9090)
         ^                        ^
         |                        |
+--------+---------+     +--------+---------+
|  App Node 01     |     |  App Node 02-04  |
|  10.10.10.10     |     |  10.10.10.11-13  |
|                  |     |                  |
|  Promtail        |     |  Promtail        |
|  Node Exporter   |     |  Node Exporter   |
+------------------+     +------------------+
```

---

### Loki Server

Dedicated server for Loki. All RAM and CPU goes to Loki only.

#### Loki Server: Recommended Specs

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disk | 50 GB | 100 GB |
| Network | 100 Mbps | 1 Gbps |

The disk size depends entirely on your log volume and retention period.
Calculate as: (average MB/s ingestion rate) x (retention seconds) x 1.3
The 1.3 factor accounts for index overhead and WAL.

For example, 1 MB/s ingestion with 72h retention:
1 MB/s x 259200 seconds x 1.3 = approximately 337 GB

#### Loki Server: RAM Allocation (4 GB example)

```
+-------------------------------------------------------------------+
|  Purpose               | Size    | Config location               |
+-------------------------------------------------------------------+
|  Chunk read cache      | 1024 MB | chunk_store_config            |
|  Query results cache   |  512 MB | query_range.results_cache     |
|  Ingester chunks (RAM) |  768 MB | ingester settings             |
|  WAL replay ceiling    |  512 MB | ingester.wal                  |
|  OS and page cache     | 1280 MB | OS managed                    |
+-------------------------------------------------------------------+
|  Total                 | 4096 MB                                  |
+-------------------------------------------------------------------+
```

#### Loki Server: RAM Allocation (8 GB example)

```
+-------------------------------------------------------------------+
|  Purpose               | Size    | Config location               |
+-------------------------------------------------------------------+
|  Chunk read cache      | 2048 MB | chunk_store_config            |
|  Query results cache   | 1024 MB | query_range.results_cache     |
|  Ingester chunks (RAM) | 1536 MB | ingester settings             |
|  WAL replay ceiling    |  512 MB | ingester.wal                  |
|  OS and page cache     | 2976 MB | OS managed                    |
+-------------------------------------------------------------------+
|  Total                 | 8096 MB                                  |
+-------------------------------------------------------------------+
```

#### Loki Server: Disk Layout (100 GB)

> Default Path : `/var/lib/`

```
+-------------------------------------------------------------------+
|  Path                     | Size   | Purpose                     |
+-------------------------------------------------------------------+
|  / (OS root)              |  10 GB | OS, binaries                |
|  /var/lib/loki/chunks     |  65 GB | Compressed log chunks       |
|  /var/lib/loki/wal        |  10 GB | Write-ahead log             |
|  /var/lib/loki/tsdb-index |   5 GB | TSDB index                  |
|  /var/lib/loki/tsdb-cache |   2 GB | Index cache                 |
|  /var/lib/loki/compactor  |   3 GB | Compactor workspace         |
|  /var/log                 |   3 GB | Journald                    |
|  Headroom                 |   2 GB | Buffer                      |
+-------------------------------------------------------------------+
|  Total                    | 100 GB                               |
+-------------------------------------------------------------------+
```

#### Loki Server: OS Tuning

```bash
sudo tee /etc/security/limits.d/loki.conf > /dev/null <<'EOF'
loki    soft    nofile      131072
loki    hard    nofile      131072
loki    soft    nproc       65536
loki    hard    nproc       65536
EOF
```

```bash
sudo tee /etc/sysctl.d/99-loki.conf > /dev/null <<'EOF'
fs.file-max = 1048576
fs.inotify.max_user_watches = 524288
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.core.somaxconn = 65536
vm.swappiness = 10
vm.dirty_ratio = 20
vm.dirty_background_ratio = 5
vm.max_map_count = 262144
EOF

sudo sysctl -p /etc/sysctl.d/99-loki.conf
```

#### Loki Server: Systemd Service

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
RestartSec=10s
TimeoutStopSec=60s
StandardOutput=journal
StandardError=journal

LimitNOFILE=131072
LimitNPROC=65536
LimitCORE=0

# Dedicated server: Loki gets all the RAM and all CPU cores
# GOMEMLIMIT set to 85% of total RAM (3.4 GB on a 4 GB server)
# On 8 GB server: change GOMEMLIMIT=6871947674
Environment=GOGC=75
Environment=GOMEMLIMIT=3650722201
Environment=GOMAXPROCS=2

# No CPU quota on a dedicated server - use all available CPU
# No MemoryMax hard limit - let GOMEMLIMIT in Go handle it
# IOWeight=100 is the default maximum
IOWeight=100

[Install]
WantedBy=multi-user.target
EOF
```

#### Loki Server: Application Config (4 GB RAM, 2 CPU)

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

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

ingester:
  # Dedicated server: can hold chunks in RAM longer before flushing
  chunk_idle_period: 1h
  max_chunk_age: 2h
  chunk_target_size: 1048576
  chunk_retain_period: 30s
  # More concurrent flushes: dedicated I/O
  concurrent_flushes: 4
  wal:
    dir: /var/lib/loki/wal
    checkpoint_duration: 5m
    flush_on_shutdown: true
    replay_memory_ceiling: 512MB

querier:
  # Dedicated server: use more concurrent queriers
  max_concurrent: 8
  query_timeout: 2m

query_range:
  split_queries_by_interval: 1h
  parallelise_shardable_queries: true
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        # Larger cache on dedicated server: 512 MB
        max_size_mb: 512
        ttl: 2h

compactor:
  working_directory: /var/lib/loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  # More workers: dedicated I/O available
  retention_delete_worker_count: 100
  delete_request_store: filesystem

storage_config:
  tsdb_shipper:
    active_index_directory: /var/lib/loki/tsdb-index
    cache_location: /var/lib/loki/tsdb-cache
    cache_ttl: 24h

chunk_store_config:
  chunk_cache_config:
    embedded_cache:
      enabled: true
      # Large chunk cache on dedicated server: 1024 MB
      max_size_mb: 1024
      ttl: 4h

limits_config:
  retention_period: 72h
  ingestion_rate_mb: 32
  ingestion_burst_size_mb: 64
  max_streams_per_user: 50000
  max_entries_limit_per_query: 100000
  max_query_lookback: 72h
  max_query_length: 72h
  per_stream_rate_limit: 5MB
  per_stream_rate_limit_burst: 25MB

table_manager:
  retention_deletes_enabled: true
  retention_period: 72h
EOF
```

---

### Prometheus Server

Dedicated server for Prometheus metric collection and storage.

#### Prometheus Server: Recommended Specs

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 2 GB | 4 GB |
| CPU | 1 core | 2 cores |
| Disk | 30 GB | 50 GB |
| Network | 100 Mbps | 1 Gbps |

Prometheus RAM usage scales with the number of active time series in memory
(the head block). Estimate 2 to 3 bytes per sample per scrape interval.
With 5 targets each exposing 1000 metrics at 15s scrape interval, expect
approximately 300 MB RAM for the head block alone.

#### Prometheus Server: RAM Allocation (4 GB)

```
+-------------------------------------------------------------------+
|  Purpose                    | Size   | Notes                     |
+-------------------------------------------------------------------+
|  TSDB head block (RAM)      | 1024 MB| Active time series        |
|  TSDB query cache           |  512 MB| Query result cache        |
|  WAL (in-memory buffer)     |  256 MB| Pre-flush write buffer    |
|  Remote write buffer        |  128 MB| If using remote write     |
|  OS and page cache          | 2176 MB| TSDB block read cache     |
+-------------------------------------------------------------------+
|  Total                      | 4096 MB                            |
+-------------------------------------------------------------------+
```

#### Prometheus Server: Disk Layout (50 GB)

```
+-------------------------------------------------------------------+
|  Path                         | Size  | Purpose                  |
+-------------------------------------------------------------------+
|  / (OS root)                  | 10 GB | OS, binaries             |
|  /var/lib/prometheus          | 35 GB | TSDB blocks and WAL      |
|    blocks/                    | 28 GB | Compressed metric blocks |
|    wal/                       |  5 GB | Write-ahead log          |
|    chunks_head/               |  2 GB | Head chunk files         |
|  /var/log                     |  3 GB | Journald                 |
|  Headroom                     |  2 GB | Buffer                   |
+-------------------------------------------------------------------+
|  Total                        | 50 GB                            |
+-------------------------------------------------------------------+
```

Prometheus TSDB retention of 30 days at a typical scrape load of 5 targets
with 1000 metrics each uses approximately 2 to 5 GB on disk due to
Prometheus compression. The 35 GB allocation here is generous.

#### Prometheus Server: OS Tuning

```bash
sudo tee /etc/security/limits.d/prometheus.conf > /dev/null <<'EOF'
prometheus    soft    nofile      65536
prometheus    hard    nofile      65536
prometheus    soft    nproc       32768
prometheus    hard    nproc       32768
EOF
```

```bash
sudo tee /etc/sysctl.d/99-prometheus.conf > /dev/null <<'EOF'
fs.file-max = 524288
vm.swappiness = 10
vm.dirty_ratio = 20
vm.dirty_background_ratio = 5
net.core.somaxconn = 32768
EOF

sudo sysctl -p /etc/sysctl.d/99-prometheus.conf
```

#### Prometheus Server: Systemd Service

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
  --storage.tsdb.wal-compression \
  --storage.tsdb.min-block-duration=2h \
  --storage.tsdb.max-block-duration=25h \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-lifecycle \
  --query.max-concurrency=10 \
  --query.timeout=2m
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

LimitNOFILE=65536
LimitNPROC=32768

# Dedicated server: Prometheus gets all CPU
# GOMEMLIMIT: 85% of 4 GB = 3.4 GB
Environment=GOGC=100
Environment=GOMEMLIMIT=3650722201
Environment=GOMAXPROCS=2

[Install]
WantedBy=multi-user.target
EOF
```

---

### Grafana Server

Dedicated server for Grafana. Grafana is stateless in terms of metrics and
logs (all data lives in Loki and Prometheus). Its disk needs are minimal.

#### Grafana Server: Recommended Specs

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 512 MB | 2 GB |
| CPU | 1 core | 2 cores |
| Disk | 10 GB | 20 GB |
| Network | 100 Mbps | 1 Gbps |

Grafana RAM usage is dominated by panel rendering (generating PNG images
for alerts) and dashboard panel query result buffering. For a team of fewer
than 20 concurrent dashboard viewers, 2 GB RAM is more than sufficient.

#### Grafana Server: RAM Allocation (2 GB)

```
+-------------------------------------------------------------------+
|  Purpose                    | Size   | Notes                     |
+-------------------------------------------------------------------+
|  Grafana process heap       |  512 MB| Dashboard, alerts, API    |
|  SQLite database cache      |  128 MB| Dashboard and user store  |
|  Panel image renderer       |  256 MB| Alert screenshots         |
|  OS and page cache          | 1152 MB| Plugin files, static      |
+-------------------------------------------------------------------+
|  Total                      | 2048 MB                            |
+-------------------------------------------------------------------+
```

#### Grafana Server: Disk Layout (20 GB)

```
+-------------------------------------------------------------------+
|  Path                    | Size  | Purpose                       |
+-------------------------------------------------------------------+
|  / (OS root)             | 10 GB | OS, binaries                  |
|  /var/lib/grafana        |  8 GB | SQLite DB, plugins, images    |
|    grafana.db            |  1 GB | Dashboard and user database   |
|    plugins/              |  2 GB | Installed plugins             |
|    png/                  |  2 GB | Alert panel images            |
|    sessions/             |  1 GB | User session data             |
|  /var/log/grafana        |  1 GB | Grafana logs                  |
|  Headroom                |  1 GB | Buffer                        |
+-------------------------------------------------------------------+
|  Total                   | 20 GB                                 |
+-------------------------------------------------------------------+
```

#### Grafana Server: OS Tuning

```bash
sudo tee /etc/security/limits.d/grafana.conf > /dev/null <<'EOF'
grafana    soft    nofile      16384
grafana    hard    nofile      16384
grafana    soft    nproc        8192
grafana    hard    nproc        8192
EOF
```

```bash
sudo tee /etc/sysctl.d/99-grafana.conf > /dev/null <<'EOF'
fs.file-max = 131072
vm.swappiness = 10
net.core.somaxconn = 16384
EOF

sudo sysctl -p /etc/sysctl.d/99-grafana.conf
```

#### Grafana Server: Systemd Service

```bash
sudo tee /etc/systemd/system/grafana-server.service > /dev/null <<'EOF'
[Unit]
Description=Grafana Dashboard Server
After=network.target

[Service]
User=grafana
Group=grafana
ExecStart=/usr/sbin/grafana-server \
  --config=/etc/grafana/grafana.ini \
  --homepath=/usr/share/grafana \
  --packaging=rpm
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

LimitNOFILE=16384
LimitNPROC=8192

# Dedicated server: Grafana gets all CPU
# GOMEMLIMIT: 85% of 2 GB = 1.7 GB
Environment=GOGC=100
Environment=GOMEMLIMIT=1825361101
Environment=GOMAXPROCS=2

[Install]
WantedBy=multi-user.target
EOF
```

#### Grafana Application Config for Dedicated Server

```bash
sudo tee /etc/grafana/grafana.ini > /dev/null <<'EOF'
[server]
http_port = 3000
domain = 10.10.10.22
root_url = http://10.10.10.22:3000/

[database]
type = sqlite3
path = /var/lib/grafana/grafana.db
# Dedicated server: allow more concurrent DB connections
max_open_conn = 25
max_idle_conn = 10
conn_max_lifetime = 14400

[dataproxy]
timeout = 60
dial_timeout = 10
keep_alive_seconds = 30
# More idle connections allowed on dedicated server
idle_conn_timeout_seconds = 90
max_idle_connections = 100

[analytics]
reporting_enabled = false
check_for_updates = false

[log]
mode = console
level = warn

[paths]
data = /var/lib/grafana
logs = /var/log/grafana
plugins = /var/lib/grafana/plugins

[alerting]
enabled = true
# Dedicated server: allow more concurrent alert evaluations
concurrent_render_limit = 5
EOF
```

---

### Promtail on App Nodes

Promtail runs on every application node. It is very lightweight. The
resource allocation below applies to each individual app node.

#### App Node: Recommended Specs for Promtail

Promtail itself needs very little. These are the minimum additions to
whatever your application already requires:

| Resource | Promtail Addition |
|---|---|
| RAM | 128 to 256 MB on top of app requirements |
| CPU | 0.1 to 0.25 cores on top of app requirements |
| Disk | 100 MB for positions file and binary |
| Network | Outbound to Loki server port 3100 |

#### App Node: Promtail RAM Breakdown

```
+-------------------------------------------------------------------+
|  Purpose              | Size   | Notes                           |
+-------------------------------------------------------------------+
|  Log batch buffer     |  64 MB | Held before pushing to Loki     |
|  Pipeline stage RAM   |  32 MB | Regex, multiline processing     |
|  File handle cache    |  32 MB | Open file descriptors           |
|  Go runtime overhead  |  32 MB | Goroutines, GC                  |
|  OS overhead          |  96 MB | Buffer                          |
+-------------------------------------------------------------------+
|  Total                | 256 MB                                   |
+-------------------------------------------------------------------+
```

#### App Node: Promtail OS Tuning

```bash
sudo tee /etc/security/limits.d/promtail.conf > /dev/null <<'EOF'
promtail    soft    nofile      65536
promtail    hard    nofile      65536
promtail    soft    nproc       16384
promtail    hard    nproc       16384
EOF
```

```bash
sudo tee /etc/sysctl.d/99-promtail.conf > /dev/null <<'EOF'
# Inotify watches: one per log file being watched
# With multiple Laravel apps and subdirectories, set high
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
fs.file-max = 131072
EOF

sudo sysctl -p /etc/sysctl.d/99-promtail.conf
```

#### App Node: Promtail Systemd Service

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

LimitNOFILE=65536
LimitNPROC=16384

Environment=GOGC=100
Environment=GOMEMLIMIT=251658240
Environment=GOMAXPROCS=1

# Cap Promtail to avoid competing with the main application
CPUQuota=25%
CPUWeight=10
MemoryMax=256M
MemoryHigh=220M
MemorySwapMax=0

[Install]
WantedBy=multi-user.target
EOF
```

#### App Node: Promtail Application Config

Point clients URL to the dedicated Loki server, not localhost.

```bash
sudo tee /etc/promtail/promtail.yml > /dev/null <<'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: warn

positions:
  filename: /var/lib/promtail/positions.yaml
  sync_period: 30s

clients:
  # Point to dedicated Loki server
  - url: http://10.10.10.20:3100/loki/api/v1/push
    batchwait: 1s
    batchsize: 1048576
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    timeout: 10s

scrape_configs:

  - job_name: php-application
    static_configs:
      - targets: ["localhost"]
        labels:
          job: php-application
          host: <HOSTNAME>
          env: production
          __path__: /var/apps/*/storage/logs/*.log
    pipeline_stages:
      - multiline:
          firstline: '^\[\d{4}-\d{2}-\d{2}'
          max_wait_time: 3s
      - regex:
          expression: '^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (?P<env>\w+)\.(?P<level>\w+): (?P<message>.*)'
      - labels:
          level:
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
EOF
```

---

## Resource Comparison Table

### RAM Comparison

| Service | Single Server (8 GB total) | Dedicated Server |
|---|---|---|
| Loki MemoryMax | 3 GB | No hard cap (GOMEMLIMIT 85% of server RAM) |
| Loki chunk cache | 256 MB | 1024 MB |
| Loki results cache | 128 MB | 512 MB |
| Loki GOMEMLIMIT | 2.75 GB | 3.4 GB (on 4 GB server) |
| Prometheus MemoryMax | 1 GB | No hard cap |
| Prometheus GOMEMLIMIT | 900 MB | 3.4 GB (on 4 GB server) |
| Grafana MemoryMax | 512 MB | No hard cap |
| Grafana GOMEMLIMIT | 480 MB | 1.7 GB (on 2 GB server) |
| Promtail MemoryMax | 256 MB | 256 MB (app node) |

### CPU Comparison

| Service | Single Server (4 cores) | Dedicated Server |
|---|---|---|
| Loki CPUQuota | 200% (2 cores) | No quota (all cores) |
| Loki GOMAXPROCS | 2 | Equal to server core count |
| Prometheus CPUQuota | 50% (0.5 cores) | No quota |
| Prometheus GOMAXPROCS | 1 | Equal to server core count |
| Grafana CPUQuota | 50% (0.5 cores) | No quota |
| Grafana GOMAXPROCS | 1 | Equal to server core count |
| Promtail CPUQuota | 25% on app node | 25% on app node |

### Disk Comparison

| Service | Single Server | Dedicated Server |
|---|---|---|
| Loki /var/lib/loki | 60 GB | 90 GB (on 100 GB disk) |
| Prometheus /var/lib/prometheus | 10 GB | 40 GB (on 50 GB disk) |
| Grafana /var/lib/grafana | 5 GB | 18 GB (on 20 GB disk) |
| Promtail /var/lib/promtail | 1 GB | 1 GB (app node) |

### File Descriptor Limits Comparison

| Service | Single Server LimitNOFILE | Dedicated Server LimitNOFILE |
|---|---|---|
| Loki | 65536 | 131072 |
| Prometheus | 65536 | 65536 |
| Grafana | 16384 | 16384 |
| Promtail (app node) | 16384 | 65536 |

---

## Which Model to Choose

```
Is this a production environment serving real users?
  YES --> Use separate servers
  NO  --> Single server is fine

Do you need any service to stay up if another crashes?
  YES --> Use separate servers
  NO  --> Single server is fine

Is your total log ingestion rate above 5 MB/s?
  YES --> Use separate servers (single server Loki will struggle)
  NO  --> Single server is fine

Is your server RAM 16 GB or more?
  YES --> Single server works well with generous allocations
  NO  --> Consider separate servers if below 8 GB

Do you have budget for only one server?
  YES --> Single server, apply all limits from Model 1
  NO  --> Separate servers for production

Will the number of app nodes grow beyond 10?
  YES --> Separate servers, especially for Prometheus scrape load
  NO  --> Single server is fine
```
