# Grafana + Loki + Promtail Resource Allocation and Tuning Guide

## Server Specification Reference

| Resource | Available |
|---|---|
| RAM | 8 GB |
| CPU | 4 cores |
| Disk | 100 GB |
| OS | Oracle Linux 9 / RHEL 9 |

---

## Table of Contents

- [Resource Allocation Summary](#resource-allocation-summary)
- [Disk Layout Planning](#disk-layout-planning)
- [Operating System Tuning](#operating-system-tuning)
- [Loki Resource Configuration](#loki-resource-configuration)
- [Grafana Resource Configuration](#grafana-resource-configuration)
- [Promtail Resource Configuration](#promtail-resource-configuration)
- [Systemd Resource Controls](#systemd-resource-controls)
- [Verify All Limits Are Applied](#verify-all-limits-are-applied)
- [Monitoring Resource Usage](#monitoring-resource-usage)
- [Troubleshooting Resource Issues](#troubleshooting-resource-issues)

---

## Resource Allocation Summary

This section shows how to distribute the 8 GB RAM and 4 CPU cores across all services on a single server running the full stack.

### RAM Allocation

```
Total RAM: 8192 MB
-----------------------------------------------------------
Service             Allocated     Heap/Cache     Purpose
-----------------------------------------------------------
Loki                3072 MB       2048 MB heap   Log storage engine
Grafana              512 MB        512 MB heap   Dashboard UI
Promtail             256 MB        256 MB heap   Log shipping agent
Node Exporter         64 MB         64 MB        Metrics exporter
Operating System    1024 MB           -          Kernel, network buffers
Page Cache Reserve  3264 MB           -          Disk I/O cache (OS managed)
-----------------------------------------------------------
Total               8192 MB
```

Page cache is not "wasted" RAM. The OS uses remaining free memory as disk read cache, which significantly speeds up Loki chunk reads and index lookups. Leaving 3+ GB for page cache on a log server is intentional.

### CPU Allocation

```
Total CPU: 4 cores
-----------------------------------------------------------
Service             CPU Quota     Threads/Workers
-----------------------------------------------------------
Loki                2.0 cores     ingester, querier, compactor
Grafana             0.5 cores     HTTP handlers, alerting
Promtail            0.5 cores     file tail workers
Node Exporter       0.1 cores     metric collectors
OS / system         0.9 cores     kernel, network, I/O scheduler
-----------------------------------------------------------
Total               4.0 cores
```

### Disk Allocation

```
Total Disk: 100 GB
-----------------------------------------------------------
Path                        Size        Purpose
-----------------------------------------------------------
/                            10 GB      OS root partition
/var/lib/loki                60 GB      Loki chunks, index, WAL, cache
/var/lib/grafana              5 GB      Grafana database, plugins, images
/var/lib/promtail             1 GB      Promtail positions file
/var/log                      5 GB      System logs and service journals
/tmp                          2 GB      Temporary files
Unallocated reserve          17 GB      Growth headroom
-----------------------------------------------------------
Total                       100 GB
```

---

## Disk Layout Planning

### Create Dedicated Mount for Loki (Recommended)

If you have a separate disk or LVM volume available, mount it at `/var/lib/loki` before installing Loki. This isolates Loki I/O from the OS root and prevents log storage from filling the root filesystem.

```bash
# Example using LVM (adjust volume group name to match your system)
sudo lvcreate -L 60G -n loki_data <your_vg_name>
sudo mkfs.xfs /dev/<your_vg_name>/loki_data
sudo mkdir -p /var/lib/loki

# Add to /etc/fstab for persistent mount
echo '/dev/<your_vg_name>/loki_data  /var/lib/loki  xfs  defaults,noatime  0 2' \
  | sudo tee -a /etc/fstab

sudo mount -a
sudo df -h /var/lib/loki
```

Using `noatime` in mount options prevents the OS from updating the access timestamp on every file read, which reduces unnecessary disk writes on Loki chunk files.

### Create Loki Directory Structure

```bash
sudo mkdir -p /var/lib/loki/chunks
sudo mkdir -p /var/lib/loki/tsdb-index
sudo mkdir -p /var/lib/loki/tsdb-cache
sudo mkdir -p /var/lib/loki/wal
sudo mkdir -p /var/lib/loki/compactor
sudo mkdir -p /var/lib/loki/rules
sudo chown -R loki:loki /var/lib/loki
```

### Set Up Log Rotation for Service Journals

Without log rotation, systemd journals can grow unbounded. Cap journal size to prevent filling `/var/log`.

```bash
sudo mkdir -p /etc/systemd/journald.conf.d/

sudo tee /etc/systemd/journald.conf.d/size-limit.conf > /dev/null <<'EOF'
[Journal]
SystemMaxUse=2G
SystemKeepFree=1G
SystemMaxFileSize=200M
MaxRetentionSec=7day
EOF

sudo systemctl restart systemd-journald
```

---

## Operating System Tuning

These kernel and system settings apply to the entire server and benefit all services running on it.

### Increase File Descriptor Limits

Loki opens a file descriptor for every active chunk file, WAL segment, and index file. On a busy server receiving logs from 4 app nodes it can easily open 10,000 or more file descriptors. The default Linux limit of 1024 is far too low.

```bash
sudo tee /etc/security/limits.d/observability.conf > /dev/null <<'EOF'
# Loki
loki        soft    nofile      65536
loki        hard    nofile      65536
loki        soft    nproc       32768
loki        hard    nproc       32768

# Grafana
grafana     soft    nofile      16384
grafana     hard    nofile      16384

# Promtail
promtail    soft    nofile      16384
promtail    hard    nofile      16384

# Root (covers services run as root)
root        soft    nofile      65536
root        hard    nofile      65536
EOF
```

### Kernel Parameters via sysctl

```bash
sudo tee /etc/sysctl.d/99-observability.conf > /dev/null <<'EOF'
# Maximum number of open file descriptors system-wide
fs.file-max = 524288

# Maximum number of inotify watches (used by Promtail to watch log files)
# Each watched log file consumes one inotify watch
# With 4 app nodes sending multiple log files, set this high
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512

# Network buffer sizes for high log ingestion throughput
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 65536
net.core.wmem_default = 65536
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Increase backlog for high connection rates from Promtail agents
net.core.somaxconn = 32768
net.ipv4.tcp_max_syn_backlog = 16384

# Virtual memory settings
# Reduce swappiness - prefer RAM over swap for log processing workload
vm.swappiness = 10

# Allow more dirty pages before forcing writeback
# Helps Loki WAL writes perform consistently
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# Increase max map count for memory-mapped index files
vm.max_map_count = 262144
EOF

# Apply all sysctl settings immediately
sudo sysctl -p /etc/sysctl.d/99-observability.conf
```

### Verify Current System Limits

```bash
# Check current system-wide file descriptor limit
cat /proc/sys/fs/file-max

# Check current inotify limits
cat /proc/sys/fs/inotify/max_user_watches

# Check open file counts per service (after services are running)
cat /proc/$(pgrep -f "loki")/limits | grep "open files"
cat /proc/$(pgrep -f "grafana")/limits | grep "open files"
cat /proc/$(pgrep -f "promtail")/limits | grep "open files"
```

---

## Loki Resource Configuration

### Loki Application-Level Resource Settings

The following is a complete `/etc/loki/loki.yml` with resource allocation tuned for 8 GB RAM and 4 CPU cores. Comments explain the reasoning for each value.

```bash
sudo tee /etc/loki/loki.yml > /dev/null <<'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn

  # Limit concurrent HTTP and gRPC connections
  # Prevents runaway memory growth under heavy query load
  http_server_read_timeout: 60s
  http_server_write_timeout: 60s
  grpc_server_max_recv_msg_size: 67108864     # 64 MB max gRPC message
  grpc_server_max_send_msg_size: 67108864     # 64 MB max gRPC response

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

# -------------------------------------------------------
# Ingester resource tuning
# The ingester holds active chunks in memory before
# flushing to disk. Tuning this directly controls RAM use.
# -------------------------------------------------------
ingester:
  # How long a chunk can sit idle before being flushed to disk
  # Shorter = less RAM used, more frequent disk writes
  # Longer = more RAM used, fewer disk writes
  # 30m is a good balance for 8 GB RAM
  chunk_idle_period: 30m

  # Maximum age of any chunk before it is force-flushed
  # Keeps memory usage bounded
  max_chunk_age: 1h

  # Target size of each chunk in bytes (1 MB)
  # Larger chunks = better compression, more RAM per chunk
  chunk_target_size: 1048576

  # How long to retain a chunk in memory after flushing
  # Keep short to free RAM quickly after flush
  chunk_retain_period: 30s

  # Maximum number of chunks per ingester kept in memory
  # 8 GB server: cap at 2000 to limit ingester RAM to ~2 GB
  max_transfer_retries: 0

  # WAL (Write Ahead Log) stores incoming logs before they
  # are assembled into chunks. Enables crash recovery.
  wal:
    dir: /var/lib/loki/wal
    # Checkpoint WAL every 5 minutes
    checkpoint_duration: 5m
    # Flush WAL to chunk store when WAL size reaches 1 GB
    flush_on_shutdown: true
    replay_memory_ceiling: 512MB

  # Limit concurrent ingestion goroutines
  # Prevents CPU starvation under burst ingestion
  concurrent_flushes: 2

# -------------------------------------------------------
# Querier resource tuning
# Controls how much memory and CPU queries can consume
# -------------------------------------------------------
querier:
  # Maximum number of concurrent queries
  # 4 CPU cores: keep this at 4-8 to avoid overloading
  max_concurrent: 4

  # Query timeout
  query_timeout: 1m

  # Engine timeout
  engine:
    timeout: 3m

# -------------------------------------------------------
# Query frontend
# Splits large queries into smaller pieces and caches results
# -------------------------------------------------------
query_range:
  # Split queries by 1-hour intervals to parallelize
  split_queries_by_interval: 1h
  parallelise_shardable_queries: true

  results_cache:
    cache:
      embedded_cache:
        enabled: true
        # Cache size: 256 MB
        # Reduces repeated disk reads for recent queries
        max_size_mb: 256
        ttl: 1h

# -------------------------------------------------------
# Compactor
# Runs background compaction and retention deletion
# Limit its CPU and I/O impact on the main query path
# -------------------------------------------------------
compactor:
  working_directory: /var/lib/loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h

  # Number of goroutines deleting expired chunks
  # Keep low to avoid I/O spikes during retention cleanup
  retention_delete_worker_count: 50

  delete_request_store: filesystem

# -------------------------------------------------------
# Storage config
# Controls cache sizes for index and chunk lookups
# -------------------------------------------------------
storage_config:
  tsdb_shipper:
    active_index_directory: /var/lib/loki/tsdb-index
    cache_location: /var/lib/loki/tsdb-cache
    cache_ttl: 24h

chunk_store_config:
  chunk_cache_config:
    embedded_cache:
      enabled: true
      # Chunk read cache: 512 MB
      # Frequently accessed chunks are served from RAM
      # avoiding disk reads entirely
      max_size_mb: 512
      ttl: 2h

# -------------------------------------------------------
# Limits (applies per-tenant, single tenant here)
# These are the most important settings to prevent a
# single burst of logs from consuming all server resources
# -------------------------------------------------------
limits_config:
  # 72-hour log retention
  retention_period: 72h

  # Maximum ingestion rate per second
  # 16 MB/s allows ~1 MB/s per app node across 4 nodes
  # with headroom for bursts
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32

  # Maximum number of active log streams
  # Each unique label combination = 1 stream
  max_streams_per_user: 10000

  # Maximum number of log entries returned per query
  max_entries_limit_per_query: 50000

  # Maximum bytes returned per query
  max_query_series_limit: 10000

  # Maximum time range a query can span
  # Prevents expensive full-retention queries from 
  # consuming all available RAM
  max_query_lookback: 72h
  max_query_length: 72h

  # Cardinality limit: max unique label values
  max_label_names_per_series: 30

  # Per-stream rate limiting
  per_stream_rate_limit: 3MB
  per_stream_rate_limit_burst: 15MB

table_manager:
  retention_deletes_enabled: true
  retention_period: 72h
EOF
```

### Loki Go Runtime Settings

Loki is written in Go. The Go runtime has its own memory management settings that must be tuned separately from the application config.

```bash
sudo mkdir -p /etc/systemd/system/loki.service.d/

sudo tee /etc/systemd/system/loki.service.d/runtime.conf > /dev/null <<'EOF'
[Service]
# GOGC controls when Go garbage collector runs
# Default is 100 (GC when heap doubles)
# Lower value = more frequent GC = lower peak RAM, higher CPU
# 75 is a good balance for a log server
Environment=GOGC=75

# GOMEMLIMIT is a hard memory ceiling for the Go runtime
# Set to 2.5 GB (leaving RAM for OS, Grafana, Promtail)
# Format must be in bytes
Environment=GOMEMLIMIT=2684354560

# GOMAXPROCS limits how many OS threads Go can use simultaneously
# Set to 2 to share CPU with Grafana and Promtail
Environment=GOMAXPROCS=2
EOF
```

---

## Grafana Resource Configuration

### Grafana Application-Level Resource Settings

```bash
sudo tee /etc/grafana/grafana.ini > /dev/null <<'EOF'
[server]
http_port = 3000
domain = localhost
root_url = http://localhost:3000/

# Number of HTTP workers serving dashboard requests
# 4 cores shared: keep at 2 to avoid starving Loki
[server]
router_logging = false

[database]
# Grafana uses SQLite by default which is fine for single server
# SQLite file is stored at /var/lib/grafana/grafana.db
type = sqlite3
path = /var/lib/grafana/grafana.db

# Maximum number of open SQLite connections
# Keep low for SQLite - it does not benefit from many connections
max_open_conn = 10
max_idle_conn = 5
conn_max_lifetime = 14400

[dataproxy]
# Timeout for data source queries sent to Loki and Prometheus
timeout = 30
dial_timeout = 10
keep_alive_seconds = 30

# Maximum idle connections to each data source
idle_conn_timeout_seconds = 90

[analytics]
reporting_enabled = false
check_for_updates = false

[log]
mode = console
level = warn

[log.console]
format = text

[paths]
data = /var/lib/grafana
logs = /var/log/grafana
plugins = /var/lib/grafana/plugins
provisioning = /etc/grafana/provisioning

[alerting]
enabled = true
# Maximum concurrent alert rule evaluations
# Keep at 1-2 on a shared server
concurrent_render_limit = 2

[rendering]
# Disable server-side rendering to save RAM if you do not need PNG exports
# If disabled, panel image rendering in alerts will not work
server_url =
callback_url =

[feature_toggles]
# Disable unused features to reduce background CPU usage
enable =
EOF
```

### Grafana Go Runtime Settings

```bash
sudo mkdir -p /etc/systemd/system/grafana-server.service.d/

sudo tee /etc/systemd/system/grafana-server.service.d/runtime.conf > /dev/null <<'EOF'
[Service]
Environment=GOGC=100
# Hard memory ceiling: 512 MB
Environment=GOMEMLIMIT=536870912
Environment=GOMAXPROCS=1
EOF
```

---

## Promtail Resource Configuration

Promtail is lightweight by design. On the observability server itself it only tails local system logs. The main Promtail resource concern is on app nodes where it watches many log files simultaneously.

### Promtail Application-Level Resource Settings

```bash
sudo tee /etc/promtail/promtail.yml > /dev/null <<'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: warn

positions:
  # Stores the last-read byte position for each file
  # Stored on disk so Promtail resumes after restart
  filename: /var/lib/promtail/positions.yaml

  # How often to sync positions to disk
  # More frequent = safer recovery, more disk I/O
  sync_period: 30s

clients:
  - url: http://localhost:3100/loki/api/v1/push

    # Batch settings: controls how much data is buffered
    # before sending a push request to Loki
    # Larger batches = fewer HTTP requests = less CPU
    # but more RAM used while batching
    batchwait: 1s
    batchsize: 1048576     # 1 MB batch size

    # Retry settings
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10

    timeout: 10s

scrape_configs:

  - job_name: system
    static_configs:
      - targets: ["localhost"]
        labels:
          job: system
          host: observability-server
          env: production
          __path__: /var/log/{messages,secure,cron}
    pipeline_stages:
      - regex:
          expression: '(?P<level>error|warn|info|debug|ERROR|WARN|INFO|DEBUG)'
      - labels:
          level:
EOF
```

### Promtail Go Runtime Settings

```bash
sudo mkdir -p /etc/systemd/system/promtail.service.d/

sudo tee /etc/systemd/system/promtail.service.d/runtime.conf > /dev/null <<'EOF'
[Service]
Environment=GOGC=100
# Hard memory ceiling: 256 MB
Environment=GOMEMLIMIT=268435456
Environment=GOMAXPROCS=1
EOF
```

---

## Systemd Resource Controls

Systemd cgroups provide a second layer of enforcement on top of application-level limits. Even if a service has a bug causing a memory leak, systemd will kill and restart it before it can affect other services.

### Loki Systemd Service with Resource Controls

```bash
sudo tee /etc/systemd/system/loki.service > /dev/null <<'EOF'
[Unit]
Description=Loki Log Aggregation System
After=network.target
Documentation=https://grafana.com/docs/loki/latest/

[Service]
User=loki
Group=loki
ExecStart=/usr/local/bin/loki -config.file=/etc/loki/loki.yml
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10s
TimeoutStopSec=30s

StandardOutput=journal
StandardError=journal
SyslogIdentifier=loki

# File descriptor limit
LimitNOFILE=65536
# Process limit
LimitNPROC=32768
# Prevent core dumps
LimitCORE=0

# Systemd cgroup resource controls
# CPU: allow Loki to use up to 2 full cores (200%)
CPUQuota=200%
# CPU scheduling weight (higher = more CPU time vs other services)
CPUWeight=60

# Memory: hard limit of 3 GB
# If Loki exceeds this, systemd kills and restarts it
MemoryMax=3G
# Soft warning threshold at 2.5 GB
MemoryHigh=2560M
# Startup memory allowance
MemorySwapMax=0

# I/O weight (Loki does the most disk I/O)
IOWeight=60

[Install]
WantedBy=multi-user.target
EOF
```

### Grafana Systemd Service with Resource Controls

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
SyslogIdentifier=grafana

LimitNOFILE=16384
LimitNPROC=8192

CPUQuota=50%
CPUWeight=20

MemoryMax=512M
MemoryHigh=450M
MemorySwapMax=0

IOWeight=20

[Install]
WantedBy=multi-user.target
EOF
```

### Promtail Systemd Service with Resource Controls

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
SyslogIdentifier=promtail

LimitNOFILE=16384
LimitNPROC=8192

CPUQuota=50%
CPUWeight=10

MemoryMax=256M
MemoryHigh=220M
MemorySwapMax=0

IOWeight=20

[Install]
WantedBy=multi-user.target
EOF
```

**Apply all systemd changes**

```bash
sudo systemctl daemon-reload
sudo systemctl restart loki
sudo systemctl restart grafana-server
sudo systemctl restart promtail
```

---

## Verify All Limits Are Applied

Run these checks after restarting all services to confirm every limit is in effect.

### File Descriptor Limits

```bash
# Loki
cat /proc/$(pgrep -x loki)/limits | grep -E "open files|processes"

# Grafana
cat /proc/$(pgrep -f grafana-server)/limits | grep -E "open files|processes"

# Promtail
cat /proc/$(pgrep -x promtail)/limits | grep -E "open files|processes"
```

Expected output for Loki:
```
Max open files            65536                65536                files
Max processes             32768                32768                processes
```

### Memory Limits via Systemd

```bash
# Check cgroup memory limits for each service
systemctl show loki.service | grep -E "Memory|CPU"
systemctl show grafana-server.service | grep -E "Memory|CPU"
systemctl show promtail.service | grep -E "Memory|CPU"
```

### Current Memory and CPU Usage

```bash
# Summary of all services at once
systemd-cgtop -d 1 -n 3

# Per-service detail
systemctl status loki | grep Memory
systemctl status grafana-server | grep Memory
systemctl status promtail | grep Memory
```

### Verify inotify Limits (Important for Promtail)

```bash
# Current limit
cat /proc/sys/fs/inotify/max_user_watches

# Current usage by promtail
cat /proc/$(pgrep -x promtail)/fdinfo/* 2>/dev/null | grep -c inotify || \
  echo "check: ls /proc/$(pgrep -x promtail)/fd | wc -l"
```

### Verify Disk Space Allocation

```bash
# Show disk usage per Loki directory
du -sh /var/lib/loki/*
du -sh /var/lib/grafana
du -sh /var/lib/promtail

# Show overall disk layout
df -h
```

---

## Monitoring Resource Usage

Use these commands for ongoing monitoring of resource consumption.

### Real-time Service Resource Usage

```bash
# Watch CPU and memory for all three services every 2 seconds
watch -n 2 'ps aux | grep -E "loki|grafana|promtail" | grep -v grep | \
  awk "{printf \"%-12s %5s %5s %s\n\", \$1, \$3, \$4, \$11}"'
```

### Loki Internal Metrics

```bash
# Ingester: how many chunks are in memory right now
curl -s http://localhost:3100/metrics | grep ingester_memory_chunks

# Ingester: how much memory the chunk store is using
curl -s http://localhost:3100/metrics | grep ingester_chunk_utilization

# How many active streams are open
curl -s http://localhost:3100/metrics | grep ingester_streams_created_total

# WAL size
du -sh /var/lib/loki/wal/

# Compactor: retention deletion status
curl -s http://localhost:3100/metrics | grep loki_compactor
```

### Disk Growth Rate

```bash
# Check how fast Loki chunks directory is growing
# Run this twice with a gap to measure write rate
du -sh /var/lib/loki/chunks
sleep 60
du -sh /var/lib/loki/chunks
```

### Open File Descriptors per Service

```bash
# Loki open file count
ls /proc/$(pgrep -x loki)/fd | wc -l

# Grafana open file count
ls /proc/$(pgrep -f grafana-server)/fd | wc -l

# Promtail open file count
ls /proc/$(pgrep -x promtail)/fd | wc -l
```

---

## Troubleshooting Resource Issues

### Loki Using Too Much RAM

**Symptoms:** `systemctl status loki` shows near or at MemoryMax, OOM kills in journalctl.

```bash
# Check current memory usage
systemctl status loki | grep Memory

# Reduce chunk cache in loki.yml
# Change: max_size_mb: 512 -> max_size_mb: 256
# Change: max_size_mb: 256 -> max_size_mb: 128 (results cache)

# Reduce ingester chunk age to flush to disk faster
# Change: max_chunk_age: 1h -> max_chunk_age: 30m
# Change: chunk_idle_period: 30m -> chunk_idle_period: 15m

# Lower GOMEMLIMIT
# Change: GOMEMLIMIT=2684354560 -> GOMEMLIMIT=2147483648  (2 GB)

sudo systemctl restart loki
```

### Loki Using Too Much CPU

**Symptoms:** High load average, Loki CPUQuota throttling in `systemd-cgtop`.

```bash
# Check if Loki is being CPU throttled
systemctl status loki | grep CPU

# Reduce concurrent querier goroutines in loki.yml
# Change: max_concurrent: 4 -> max_concurrent: 2

# Reduce compactor workers
# Change: retention_delete_worker_count: 50 -> retention_delete_worker_count: 10

# Reduce GOMAXPROCS
# Change: GOMAXPROCS=2 -> GOMAXPROCS=1

sudo systemctl restart loki
```

### Disk Filling Up Too Fast

**Symptoms:** `/var/lib/loki` growing faster than expected, disk usage alert.

```bash
# Check current disk usage breakdown
du -sh /var/lib/loki/*

# Check if WAL is abnormally large (should be < 1 GB normally)
du -sh /var/lib/loki/wal

# Check if compactor is running and deleting old chunks
curl -s http://localhost:3100/metrics | grep compactor_runs_total

# If compactor is not running, force it
curl -s -X POST http://localhost:3100/loki/api/v1/delete \
  --data 'match[]={job="php-application"}' \
  --data "start=1970-01-01T00:00:00Z" \
  --data "end=$(date -d '73 hours ago' --iso-8601=seconds)"

# Verify retention is enabled in loki.yml
grep retention /etc/loki/loki.yml
```

### Promtail Too Many Open Files

**Symptoms:** `failed to start tailer: too many open files` in journalctl.

```bash
# Check current open file count
ls /proc/$(pgrep -x promtail)/fd | wc -l

# Compare to limit
cat /proc/$(pgrep -x promtail)/limits | grep "open files"

# If count is near limit, increase in limits.d config
sudo tee -a /etc/security/limits.d/observability.conf > /dev/null <<'EOF'
promtail     soft    nofile      32768
promtail     hard    nofile      32768
EOF

# Also update LimitNOFILE in promtail.service
sudo sed -i 's/LimitNOFILE=16384/LimitNOFILE=32768/' \
  /etc/systemd/system/promtail.service

sudo systemctl daemon-reload
sudo systemctl restart promtail
```

### Grafana Slow to Load Dashboards

**Symptoms:** Dashboard panels take more than 5 seconds to render.

```bash
# Check if Grafana is being memory limited
systemctl status grafana-server | grep Memory

# Check Loki query duration (slow queries cause slow dashboards)
curl -s http://localhost:3100/metrics | grep query_range_request_duration

# Reduce the time range in Grafana dashboards from "Last 72h" to "Last 6h"
# Heavy queries scanning 72 hours of logs on 8 GB RAM will always be slow

# Enable query caching in loki.yml if not already enabled
grep "results_cache" /etc/loki/loki.yml
```

---

## Quick Reference: Resource Limit Values

| Setting | Location | Value | Adjustable |
|---|---|---|---|
| Loki MemoryMax | loki.service | 3 GB | Yes |
| Loki CPUQuota | loki.service | 200% | Yes |
| Loki LimitNOFILE | loki.service | 65536 | Yes |
| Loki GOMEMLIMIT | loki.service.d/runtime.conf | 2.5 GB | Yes |
| Loki GOMAXPROCS | loki.service.d/runtime.conf | 2 | Yes |
| Loki chunk cache | loki.yml | 512 MB | Yes |
| Loki results cache | loki.yml | 256 MB | Yes |
| Loki max concurrent queries | loki.yml | 4 | Yes |
| Grafana MemoryMax | grafana-server.service | 512 MB | Yes |
| Grafana CPUQuota | grafana-server.service | 50% | Yes |
| Grafana GOMEMLIMIT | grafana-server.service.d/runtime.conf | 512 MB | Yes |
| Promtail MemoryMax | promtail.service | 256 MB | Yes |
| Promtail CPUQuota | promtail.service | 50% | Yes |
| Promtail batch size | promtail.yml | 1 MB | Yes |
| System max file descriptors | sysctl | 524288 | Yes |
| Inotify max watches | sysctl | 524288 | Yes |
| Journal max disk use | journald.conf | 2 GB | Yes |
| Log retention | loki.yml | 72 hours | Yes |
