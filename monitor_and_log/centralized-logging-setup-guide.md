# Centralized Log Visualization Infrastructure Setup Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Tool Explanations](#tool-explanations)
3. [Infrastructure Requirements](#infrastructure-requirements)
4. [High Availability Architecture](#high-availability-architecture)
5. [Installation Steps](#installation-steps)
6. [Configuration Files](#configuration-files)
7. [RBAC Implementation](#rbac-implementation)
8. [Testing and Validation](#testing-and-validation)

---

## Architecture Overview

### Workflow Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION SERVERS                             │
│                         (50+ Servers / 10 Modules)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (Logs Generated)
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   Promtail    │          │   Promtail    │          │   Promtail    │
│   (Agent)     │          │   (Agent)     │          │   (Agent)     │
│  Tomcat Node  │          │   PHP Node    │          │  Module N     │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        │ (Push Logs)              │ (Push Logs)              │ (Push Logs)
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │   Load Balancer (HAProxy) │
                    │   (Optional for HA)       │
                    └───────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐         ┌───────────────────┐
        │   Loki Writer 1   │         │   Loki Writer 2   │
        │   (Log Ingestion) │         │   (Log Ingestion) │
        └───────────────────┘         └───────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                            (Store Locally)
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │   Local Storage (XFS)     │
                    │   /data/loki/chunks       │
                    │   /data/loki/index        │
                    │   (2 Days Retention)      │
                    └───────────────────────────┘
                                    │
                                    │ (Query Logs)
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐         ┌───────────────────┐
        │   Loki Reader 1   │         │   Loki Reader 2   │
        │   (Query Service) │         │   (Query Service) │
        └───────────────────┘         └───────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    │ (LogQL Queries)
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │     Grafana Cluster       │
                    │   (Visualization Layer)   │
                    │   - RBAC Enabled          │
                    │   - Dashboards            │
                    └───────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐         ┌───────────────────┐
        │   Prometheus 1    │         │   Prometheus 2    │
        │   (Metrics)       │         │   (Metrics)       │
        └───────────────────┘         └───────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    (Scrape Metrics from Loki & System)
```

### Data Flow Explanation

1. **Log Generation**: Applications (Tomcat/PHP) write logs to local files
2. **Log Collection**: Promtail agents tail log files and forward to Loki writers
3. **Log Ingestion**: Loki writers receive, process, and store logs locally
4. **Log Storage**: Logs stored in local filesystem with 2-day retention
5. **Log Querying**: Loki readers query stored logs
6. **Visualization**: Grafana queries Loki readers and displays dashboards
7. **Monitoring**: Prometheus scrapes metrics from all components

---

## Tool Explanations

### What is Promtail?
**Simple Explanation**: Promtail is like a smart log collector. Think of it as a worker that constantly watches your application log files and immediately sends new log entries to a central location (Loki). It runs on every server where your applications are running.

**Technical Details**:
- Log shipping agent designed for Loki
- Tails log files in real-time
- Adds metadata (labels) to logs for better filtering
- Handles log parsing and transformation
- Supports multiple log formats (JSON, regex patterns)

**Why Use It?**:
- Lightweight and efficient
- Native integration with Loki
- Automatic service discovery
- Minimal resource consumption

### What is Loki?
**Simple Explanation**: Loki is like a massive filing cabinet for logs. Instead of storing every word in every log (which takes lots of space), it stores logs efficiently and creates an index based on labels (like filing tabs). When you need to find logs, you search by these labels, then read the actual log content.

**Technical Details**:
- Horizontally scalable log aggregation system
- Indexes metadata (labels) not full-text content
- Inspired by Prometheus but for logs
- Uses object storage or local filesystem
- Supports LogQL query language

**Why Use It?**:
- Cost-effective (low storage overhead)
- Fast queries on labeled data
- Native Grafana integration
- Scales horizontally
- Simple operational model

**Key Terminology**:
- **Chunks**: Compressed log data blocks
- **Index**: Metadata about log streams
- **Streams**: Collection of logs with same label set
- **Labels**: Key-value pairs for log organization
- **LogQL**: Query language for searching logs

### What is Prometheus?
**Simple Explanation**: Prometheus is a monitoring system that collects and stores metrics (numbers) about your infrastructure. It's like having a health monitoring device that checks the heartbeat, temperature, and vital signs of your servers and applications every few seconds.

**Technical Details**:
- Time-series database for metrics
- Pull-based metric collection (scraping)
- PromQL query language
- Alerting capabilities
- Service discovery

**Why Use It?**:
- Monitor Loki and Promtail health
- Track system resource usage
- Alert on infrastructure issues
- Identify performance bottlenecks
- Capacity planning

**Key Metrics to Track**:
- Loki ingestion rate
- Promtail scrape positions
- Disk usage and I/O
- Query performance
- Error rates

### What is Grafana?
**Simple Explanation**: Grafana is like your visualization dashboard. Imagine a car dashboard that shows speed, fuel, and engine temperature. Grafana does the same for your logs and metrics - it creates beautiful charts, graphs, and log views that help you understand what's happening in your infrastructure.

**Technical Details**:
- Data visualization and analytics platform
- Supports multiple data sources
- Customizable dashboards
- Role-based access control (RBAC)
- Alerting and notification system

**Why Use It?**:
- Unified view of logs and metrics
- Powerful query builder
- Team collaboration features
- Fine-grained access control
- Extensive plugin ecosystem

---

## Infrastructure Requirements

### Server Specifications

For **10 modules** and **50+ servers** with **2-day retention**:

#### 1. Loki Cluster (Write + Read)
**Quantity**: 2 servers (HA setup with 1 writer, 1 reader per node)

**Specifications per server**:
- CPU: 8 cores (16 vCPU)
- RAM: 32 GB
- Storage: 2 TB NVMe/SSD (local storage for chunks and index)
  - /data/loki/chunks: 1.5 TB
  - /data/loki/index: 100 GB
  - OS and system: 400 GB
- Network: 10 Gbps (critical for log ingestion)
- Filesystem: XFS (recommended for Loki)

**Calculation Logic**:
- Estimated log volume: 50 servers * 10 GB/day = 500 GB/day
- 2-day retention: 500 GB * 2 = 1 TB raw logs
- With compression (3:1): ~350 GB actual storage
- Buffer space: 1.5 TB provides adequate headroom

#### 2. Grafana Cluster
**Quantity**: 2 servers (HA active-passive)

**Specifications per server**:
- CPU: 4 cores (8 vCPU)
- RAM: 16 GB
- Storage: 200 GB SSD
- Network: 1 Gbps
- Filesystem: ext4 or XFS

#### 3. Prometheus Cluster
**Quantity**: 2 servers (HA setup)

**Specifications per server**:
- CPU: 4 cores (8 vCPU)
- RAM: 16 GB
- Storage: 500 GB SSD
- Network: 1 Gbps
- Filesystem: ext4 or XFS

#### 4. HAProxy Load Balancer (Optional but Recommended)
**Quantity**: 1 server (can be smaller)

**Specifications**:
- CPU: 2 cores (4 vCPU)
- RAM: 8 GB
- Storage: 100 GB
- Network: 10 Gbps

#### 5. Application Servers (Existing)
**Quantity**: 50+ servers (no changes needed)

**Promtail Requirements (per server)**:
- CPU: Minimal (~0.1 core)
- RAM: 128-256 MB
- Storage: 10 GB (for positions file and buffer)

### Total Infrastructure Summary

| Component Type | Quantity | Purpose | Critical |
|---------------|----------|---------|----------|
| Loki Servers | 2 | Log storage and querying | Yes |
| Grafana Servers | 2 | Visualization and dashboards | Yes |
| Prometheus Servers | 2 | Metrics monitoring | Yes |
| HAProxy Server | 1 | Load balancing | Recommended |
| **Total New Servers** | **7** | - | - |

### Network Requirements
- Internal network: Minimum 10 Gbps between Promtail and Loki
- User access: 1 Gbps to Grafana
- Low latency (<5ms) within the logging cluster

### Storage I/O Requirements
- Loki servers: 10,000+ IOPS (NVMe/SSD mandatory)
- Write-intensive workload during ingestion
- Read-intensive during queries

---

## High Availability Architecture

### Two-Part Architecture: Write and Read Separation

#### Part 1: Log Write (Ingestion Path)
The write path is optimized for high throughput and reliability.

**Components**:
1. **Promtail Agents** (on all 50+ servers)
   - Send logs to Loki writers via load balancer
   - Automatic retry on failure
   - Buffer logs locally during outages

2. **HAProxy Load Balancer**
   - Distributes write load across Loki writers
   - Health checks on Loki instances
   - Automatic failover

3. **Loki Writers** (2 instances)
   - Receive and process incoming logs
   - Write to local storage
   - Index creation and maintenance

**Write Path Flow**:
```
Promtail → HAProxy → Loki Writer 1 (Active)
                  ↘→ Loki Writer 2 (Standby/Active)
                           ↓
                    Local Storage
```

#### Part 2: Log Read (Query Path)
The read path is optimized for query performance and user experience.

**Components**:
1. **Loki Readers** (2 instances)
   - Handle LogQL queries from Grafana
   - Read from local storage
   - Query optimization and caching

2. **Grafana** (2 instances)
   - Load balanced for user access
   - Queries distributed across Loki readers
   - Dashboard rendering

**Read Path Flow**:
```
User → Grafana 1 (Active) → Loki Reader 1
            or                    or
     → Grafana 2 (Standby) → Loki Reader 2
                                  ↓
                           Local Storage
```

### HA Benefits

1. **No Single Point of Failure**: Each component has redundancy
2. **Performance Isolation**: Writes don't impact queries
3. **Independent Scaling**: Scale write and read capacity separately
4. **Maintenance Windows**: Update one component while other serves traffic
5. **Load Distribution**: Spread load across multiple instances

### Shared Storage Consideration

**Current Setup**: Each Loki instance uses local storage
- **Pros**: Simple, no network dependency, better performance
- **Cons**: Each instance has its own data, queries may miss logs

**Future Enhancement**: MinIO for shared object storage
- **Pros**: True HA, all instances see all logs, easier scaling
- **Cons**: Network overhead, additional infrastructure

---

## Installation Steps

### Prerequisites

#### On All Servers
```bash
# Update system packages
sudo yum update -y

# Install required tools
sudo yum install -y wget curl vim unzip tar

# Disable SELinux (or configure policies)
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# Configure firewall (adjust rules as needed)
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Set timezone
sudo timedatectl set-timezone UTC

# Install chrony for time synchronization
sudo yum install -y chrony
sudo systemctl start chronyd
sudo systemctl enable chronyd
```

### Step 1: Prepare Loki Servers

#### 1.1 Create Loki User and Directories
```bash
# On both Loki servers (loki-server-1 and loki-server-2)

# Create loki user
sudo useradd --system --no-create-home --shell /bin/false loki

# Create directories for Loki
sudo mkdir -p /opt/loki
sudo mkdir -p /data/loki/{chunks,index}
sudo mkdir -p /etc/loki
sudo mkdir -p /var/log/loki

# Set ownership
sudo chown -R loki:loki /opt/loki /data/loki /etc/loki /var/log/loki

# Set permissions
sudo chmod 755 /data/loki
```

#### 1.2 Format and Mount Storage (if using dedicated disk)
```bash
# Identify the disk (example: /dev/sdb)
lsblk

# Format with XFS filesystem
sudo mkfs.xfs /dev/sdb

# Get UUID
sudo blkid /dev/sdb

# Create mount point
sudo mkdir -p /data/loki

# Add to /etc/fstab for persistent mount
# Replace UUID with your actual UUID
echo "UUID=your-uuid-here /data/loki xfs defaults,noatime 0 2" | sudo tee -a /etc/fstab

# Mount
sudo mount -a

# Verify
df -h /data/loki
```

#### 1.3 Download and Install Loki
```bash
# Define version
LOKI_VERSION="3.0.0"

# Download Loki binary
cd /tmp
wget https://github.com/grafana/loki/releases/download/v${LOKI_VERSION}/loki-linux-amd64.zip

# Extract
unzip loki-linux-amd64.zip

# Move binary
sudo mv loki-linux-amd64 /opt/loki/loki

# Set executable permissions
sudo chmod +x /opt/loki/loki

# Verify installation
/opt/loki/loki --version
```

#### 1.4 Configure Firewall for Loki
```bash
# Loki HTTP API port
sudo firewall-cmd --permanent --add-port=3100/tcp

# Loki gRPC port (for distributed mode)
sudo firewall-cmd --permanent --add-port=9095/tcp

# Reload firewall
sudo firewall-cmd --reload
```

### Step 2: Prepare Grafana Servers

#### 2.1 Install Grafana
```bash
# On both Grafana servers (grafana-server-1 and grafana-server-2)

# Add Grafana repository
cat <<EOF | sudo tee /etc/yum.repos.d/grafana.repo
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

# Install Grafana
sudo yum install -y grafana

# Create necessary directories
sudo mkdir -p /var/lib/grafana/dashboards
sudo mkdir -p /etc/grafana/provisioning/{datasources,dashboards}

# Set ownership
sudo chown -R grafana:grafana /var/lib/grafana /etc/grafana
```

#### 2.2 Configure Firewall for Grafana
```bash
# Grafana web interface port
sudo firewall-cmd --permanent --add-port=3000/tcp

# Reload firewall
sudo firewall-cmd --reload
```

### Step 3: Prepare Prometheus Servers

#### 3.1 Create Prometheus User and Directories
```bash
# On both Prometheus servers (prometheus-server-1 and prometheus-server-2)

# Create prometheus user
sudo useradd --system --no-create-home --shell /bin/false prometheus

# Create directories
sudo mkdir -p /opt/prometheus
sudo mkdir -p /data/prometheus
sudo mkdir -p /etc/prometheus
sudo mkdir -p /var/log/prometheus

# Set ownership
sudo chown -R prometheus:prometheus /opt/prometheus /data/prometheus /etc/prometheus /var/log/prometheus
```

#### 3.2 Download and Install Prometheus
```bash
# Define version
PROMETHEUS_VERSION="2.50.0"

# Download Prometheus
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

# Extract
tar -xzf prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz
cd prometheus-${PROMETHEUS_VERSION}.linux-amd64

# Move binaries
sudo mv prometheus promtool /opt/prometheus/

# Move configuration files
sudo mv prometheus.yml /etc/prometheus/
sudo mv consoles /etc/prometheus/
sudo mv console_libraries /etc/prometheus/

# Set permissions
sudo chmod +x /opt/prometheus/{prometheus,promtool}
sudo chown -R prometheus:prometheus /etc/prometheus

# Verify installation
/opt/prometheus/prometheus --version
```

#### 3.3 Configure Firewall for Prometheus
```bash
# Prometheus web interface port
sudo firewall-cmd --permanent --add-port=9090/tcp

# Reload firewall
sudo firewall-cmd --reload
```

### Step 4: Install Promtail on Application Servers

#### 4.1 Install Promtail Agent
```bash
# On all 50+ application servers

# Define version
PROMTAIL_VERSION="3.0.0"

# Create promtail user
sudo useradd --system --no-create-home --shell /bin/false promtail

# Create directories
sudo mkdir -p /opt/promtail
sudo mkdir -p /etc/promtail
sudo mkdir -p /var/log/promtail
sudo mkdir -p /var/lib/promtail

# Download Promtail
cd /tmp
wget https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-amd64.zip

# Extract
unzip promtail-linux-amd64.zip

# Move binary
sudo mv promtail-linux-amd64 /opt/promtail/promtail

# Set permissions
sudo chmod +x /opt/promtail/promtail
sudo chown -R promtail:promtail /opt/promtail /etc/promtail /var/log/promtail /var/lib/promtail

# Verify installation
/opt/promtail/promtail --version
```

#### 4.2 Configure Firewall for Promtail
```bash
# Promtail metrics endpoint (for Prometheus scraping)
sudo firewall-cmd --permanent --add-port=9080/tcp

# Reload firewall
sudo firewall-cmd --reload
```

### Step 5: Install HAProxy (Optional Load Balancer)

#### 5.1 Install HAProxy
```bash
# On HAProxy server

# Install HAProxy
sudo yum install -y haproxy

# Enable and start service
sudo systemctl enable haproxy
```

#### 5.2 Configure Firewall for HAProxy
```bash
# HAProxy stats page
sudo firewall-cmd --permanent --add-port=8080/tcp

# Loki write endpoint
sudo firewall-cmd --permanent --add-port=3100/tcp

# Reload firewall
sudo firewall-cmd --reload
```

---

## Configuration Files

### Loki Configuration

#### Writer Configuration (loki-server-1)
Create file: `/etc/loki/loki-writer.yaml`

```yaml
# Loki Writer Configuration
# This configuration optimizes Loki for log ingestion (write path)
# Server: loki-server-1 (Writer Node)

# Authentication disabled for internal network
auth_enabled: false

# Server configuration
server:
  http_listen_port: 3100
  grpc_listen_port: 9095
  log_level: info
  log_format: json

# Distributor configuration - handles incoming log streams
distributor:
  ring:
    kvstore:
      store: inmemory
    # Single instance mode - no ring replication needed for local storage
    replication_factor: 1

# Ingester configuration - writes logs to storage
ingester:
  # Lifecycle configuration
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  
  # Chunk configuration - how logs are batched before writing
  chunk_idle_period: 5m       # Flush chunks after 5 minutes of inactivity
  chunk_block_size: 262144    # 256KB chunks
  chunk_retain_period: 30s    # Keep chunks in memory for 30s after flushing
  max_chunk_age: 1h           # Force flush after 1 hour
  
  # Transfer configuration - disabled for single instance
  max_transfer_retries: 0
  
  # WAL configuration - write-ahead log for data durability
  wal:
    enabled: true
    dir: /data/loki/wal
    flush_on_shutdown: true

# Schema configuration - defines how data is stored and indexed
schema_config:
  configs:
    # Schema version for 2-day retention
    - from: 2024-01-01
      store: tsdb                # Use TSDB (time series database) index
      object_store: filesystem   # Use local filesystem for chunks
      schema: v13                # Latest stable schema version
      index:
        prefix: index_
        period: 24h              # Create new index every 24 hours

# Storage configuration - where data is physically stored
storage_config:
  # TSDB configuration for index
  tsdb_shipper:
    active_index_directory: /data/loki/index
    cache_location: /data/loki/index-cache
    shared_store: filesystem
  
  # Filesystem configuration for chunks
  filesystem:
    directory: /data/loki/chunks
  
  # BoltDB configuration (legacy, kept for compatibility)
  boltdb_shipper:
    active_index_directory: /data/loki/index
    cache_location: /data/loki/index-cache
    shared_store: filesystem

# Compactor configuration - manages chunk compaction and retention
compactor:
  working_directory: /data/loki/compactor
  shared_store: filesystem
  compaction_interval: 10m
  # Retention configuration - 2 days
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

# Limits configuration - resource and rate limits
limits_config:
  # Retention period - 2 days (48 hours)
  retention_period: 48h
  
  # Ingestion limits
  ingestion_rate_mb: 50               # 50 MB/s per stream
  ingestion_burst_size_mb: 100        # Burst up to 100 MB
  max_streams_per_user: 10000         # Maximum streams per tenant
  max_global_streams_per_user: 100000 # Global maximum streams
  
  # Query limits
  max_query_length: 721h              # Maximum query range (30 days)
  max_query_parallelism: 32           # Parallel query execution
  max_entries_limit_per_query: 10000  # Maximum log entries per query
  max_streams_matchers_per_query: 1000
  
  # Chunk limits
  max_chunks_per_query: 2000000
  max_query_series: 1000
  
  # Label limits
  max_label_name_length: 1024
  max_label_value_length: 2048
  max_label_names_per_series: 30
  
  # Cardinality limits
  cardinality_limit: 100000
  
  # Reject old samples to prevent backdating
  reject_old_samples: true
  reject_old_samples_max_age: 168h    # 7 days
  
  # Creation grace period for out-of-order samples
  creation_grace_period: 10m

# Chunk store configuration
chunk_store_config:
  max_look_back_period: 48h           # Match retention period
  chunk_cache_config:
    enable_fifocache: true
    fifocache:
      max_size_bytes: 1GB             # 1GB cache for chunks
      ttl: 1h

# Query frontend configuration - not used in writer, but defined for completeness
query_range:
  results_cache:
    cache:
      enable_fifocache: true
      fifocache:
        max_size_bytes: 500MB
        ttl: 24h
  cache_results: true
  max_retries: 5
  parallelise_shardable_queries: true

# Table manager configuration (legacy, for old schema versions)
table_manager:
  retention_deletes_enabled: true
  retention_period: 48h

# Runtime configuration
runtime_config:
  file: /etc/loki/runtime-config.yaml
  period: 10s

# Tracing configuration (optional)
tracing:
  enabled: false
```

#### Reader Configuration (loki-server-2)
Create file: `/etc/loki/loki-reader.yaml`

```yaml
# Loki Reader Configuration
# This configuration optimizes Loki for log querying (read path)
# Server: loki-server-2 (Reader Node)

# Authentication disabled for internal network
auth_enabled: false

# Server configuration
server:
  http_listen_port: 3100
  grpc_listen_port: 9095
  log_level: info
  log_format: json

# Querier configuration - handles log queries
querier:
  # Query timeout configuration
  query_timeout: 5m
  query_ingesters_within: 3h
  
  # Engine configuration
  engine:
    timeout: 5m
    max_look_back_period: 48h
  
  # Tail configuration for real-time log streaming
  tail_max_duration: 1h
  
  # Parallelization
  max_concurrent: 20

# Query frontend configuration - caching and splitting
frontend:
  # Log query middleware
  log_queries_longer_than: 5s
  compress_responses: true
  max_outstanding_per_tenant: 2048
  
  # Query splitting
  split_queries_by_interval: 30m

# Query range configuration - result caching
query_range:
  # Align queries to improve cache efficiency
  align_queries_with_step: true
  
  # Results cache configuration
  results_cache:
    cache:
      enable_fifocache: true
      fifocache:
        max_size_bytes: 2GB         # 2GB cache for query results
        ttl: 24h
  
  # Cache settings
  cache_results: true
  max_retries: 5
  parallelise_shardable_queries: true

# Limits configuration - must match writer
limits_config:
  # Query limits
  max_query_length: 721h
  max_query_parallelism: 32
  max_entries_limit_per_query: 10000
  max_streams_matchers_per_query: 1000
  max_chunks_per_query: 2000000
  max_query_series: 1000
  
  # Cardinality limits
  cardinality_limit: 100000

# Schema configuration - must match writer
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

# Storage configuration - read from same location as writer
storage_config:
  tsdb_shipper:
    active_index_directory: /data/loki/index
    cache_location: /data/loki/index-cache
    shared_store: filesystem
  
  filesystem:
    directory: /data/loki/chunks
  
  boltdb_shipper:
    active_index_directory: /data/loki/index
    cache_location: /data/loki/index-cache
    shared_store: filesystem

# Chunk store configuration
chunk_store_config:
  max_look_back_period: 48h
  chunk_cache_config:
    enable_fifocache: true
    fifocache:
      max_size_bytes: 2GB             # 2GB cache for chunks
      ttl: 1h

# Compactor configuration - disabled on reader
compactor:
  working_directory: /data/loki/compactor
  shared_store: filesystem
  compaction_interval: 10m

# Runtime configuration
runtime_config:
  file: /etc/loki/runtime-config.yaml
  period: 10s

# Tracing configuration (optional)
tracing:
  enabled: false
```

#### Runtime Configuration (Both Servers)
Create file: `/etc/loki/runtime-config.yaml`

```yaml
# Loki Runtime Configuration
# This file can be modified without restarting Loki

# Ingester configuration
ingester:
  # Maximum series per query
  max_series_per_query: 100000
  
  # Maximum samples per query
  max_samples_per_query: 1000000

# Distributor configuration
distributor:
  # Rate limiting
  ingestion_rate_strategy: global
  ingestion_rate_mb: 50
  ingestion_burst_size_mb: 100
```

#### Loki Systemd Service (Writer)
Create file: `/etc/systemd/system/loki-writer.service`

```ini
[Unit]
Description=Loki Writer Service
Documentation=https://grafana.com/docs/loki/latest/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=loki
Group=loki
ExecStart=/opt/loki/loki \
  -config.file=/etc/loki/loki-writer.yaml \
  -target=all
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=loki-writer

# Resource limits
LimitNOFILE=65536
LimitNPROC=8192

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data/loki /var/log/loki

[Install]
WantedBy=multi-user.target
```

#### Loki Systemd Service (Reader)
Create file: `/etc/systemd/system/loki-reader.service`

```ini
[Unit]
Description=Loki Reader Service
Documentation=https://grafana.com/docs/loki/latest/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=loki
Group=loki
ExecStart=/opt/loki/loki \
  -config.file=/etc/loki/loki-reader.yaml \
  -target=querier,query-frontend
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=loki-reader

# Resource limits
LimitNOFILE=65536
LimitNPROC=8192

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data/loki /var/log/loki

[Install]
WantedBy=multi-user.target
```

### Promtail Configuration

#### Promtail Configuration for Tomcat Server
Create file: `/etc/promtail/promtail-config.yaml`

```yaml
# Promtail Configuration for Tomcat Application Server
# This agent collects logs and sends them to Loki

# Server configuration
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: info

# Positions file - tracks which logs have been read
positions:
  filename: /var/lib/promtail/positions.yaml

# Loki client configuration - where to send logs
clients:
  - url: http://haproxy-server:3100/loki/api/v1/push
    # If not using HAProxy, use direct Loki writer URL:
    # url: http://loki-server-1:3100/loki/api/v1/push
    
    # Batching configuration for efficient log shipping
    batchwait: 1s          # Wait 1 second before sending batch
    batchsize: 1048576     # Send batch when it reaches 1MB
    
    # Retry configuration
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    
    # Timeout configuration
    timeout: 10s

# Scrape configuration - defines which logs to collect
scrape_configs:
  # Tomcat access logs
  - job_name: tomcat-access
    static_configs:
      - targets:
          - localhost
        labels:
          job: tomcat-access
          module_name: user-management      # Change per module
          node: tomcat-node-01             # Change per server
          environment: production           # Environment label
          application: tomcat
          __path__: /opt/tomcat/logs/access_log.*
    
    # Pipeline stages for log parsing
    pipeline_stages:
      # Parse timestamp from log line
      - regex:
          expression: '^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<bytes>\d+)'
      
      # Parse timestamp into time field
      - timestamp:
          source: timestamp
          format: '02/Jan/2006:15:04:05 -0700'
      
      # Add labels from parsed fields
      - labels:
          method:
          status:

  # Tomcat catalina logs
  - job_name: tomcat-catalina
    static_configs:
      - targets:
          - localhost
        labels:
          job: tomcat-catalina
          module_name: user-management      # Change per module
          node: tomcat-node-01             # Change per server
          environment: production
          application: tomcat
          log_type: catalina
          __path__: /opt/tomcat/logs/catalina.out
    
    # Pipeline stages for multiline logs
    pipeline_stages:
      # Combine multiline Java stack traces
      - multiline:
          firstline: '^\d{4}-\d{2}-\d{2}'  # Line starts with date
          max_wait_time: 3s
          max_lines: 128
      
      # Parse log level
      - regex:
          expression: '^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) (?P<level>\w+) '
      
      # Add level as label
      - labels:
          level:

  # Tomcat application logs
  - job_name: tomcat-application
    static_configs:
      - targets:
          - localhost
        labels:
          job: tomcat-application
          module_name: user-management      # Change per module
          node: tomcat-node-01             # Change per server
          environment: production
          application: tomcat
          log_type: application
          __path__: /opt/tomcat/logs/app-*.log
    
    pipeline_stages:
      # Parse JSON logs (if application logs in JSON)
      - json:
          expressions:
            timestamp: timestamp
            level: level
            message: message
            logger: logger
      
      # Convert timestamp
      - timestamp:
          source: timestamp
          format: RFC3339
      
      # Add labels
      - labels:
          level:
          logger:
```

#### Promtail Configuration for PHP Server
Create file: `/etc/promtail/promtail-config.yaml`

```yaml
# Promtail Configuration for PHP Application Server
# This agent collects PHP and web server logs

# Server configuration
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: info

# Positions file
positions:
  filename: /var/lib/promtail/positions.yaml

# Loki client configuration
clients:
  - url: http://haproxy-server:3100/loki/api/v1/push
    batchwait: 1s
    batchsize: 1048576
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    timeout: 10s

# Scrape configuration
scrape_configs:
  # Apache/Nginx access logs
  - job_name: web-access
    static_configs:
      - targets:
          - localhost
        labels:
          job: web-access
          module_name: payment-gateway      # Change per module
          node: php-node-01                # Change per server
          environment: production
          application: php
          log_type: access
          __path__: /var/log/httpd/access_log
    
    pipeline_stages:
      # Parse Apache combined log format
      - regex:
          expression: '^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>[^"]+)" (?P<status>\d+) (?P<bytes>\d+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
      
      # Parse timestamp
      - timestamp:
          source: timestamp
          format: '02/Jan/2006:15:04:05 -0700'
      
      # Add labels
      - labels:
          method:
          status:

  # Apache/Nginx error logs
  - job_name: web-error
    static_configs:
      - targets:
          - localhost
        labels:
          job: web-error
          module_name: payment-gateway      # Change per module
          node: php-node-01                # Change per server
          environment: production
          application: php
          log_type: error
          __path__: /var/log/httpd/error_log
    
    pipeline_stages:
      # Parse error log format
      - regex:
          expression: '^\[(?P<timestamp>[^\]]+)\] \[(?P<level>\w+)\]'
      
      # Parse timestamp
      - timestamp:
          source: timestamp
          format: 'Mon Jan 02 15:04:05.000000 2006'
      
      # Add labels
      - labels:
          level:

  # PHP application logs
  - job_name: php-application
    static_configs:
      - targets:
          - localhost
        labels:
          job: php-application
          module_name: payment-gateway      # Change per module
          node: php-node-01                # Change per server
          environment: production
          application: php
          log_type: application
          __path__: /var/www/html/logs/*.log
    
    pipeline_stages:
      # Parse PHP log format
      - regex:
          expression: '^\[(?P<timestamp>[^\]]+)\] (?P<channel>\w+)\.(?P<level>\w+): (?P<message>.+)'
      
      # Parse timestamp
      - timestamp:
          source: timestamp
          format: '2006-01-02 15:04:05'
      
      # Add labels
      - labels:
          level:
          channel:

  # PHP error logs
  - job_name: php-error
    static_configs:
      - targets:
          - localhost
        labels:
          job: php-error
          module_name: payment-gateway      # Change per module
          node: php-node-01                # Change per server
          environment: production
          application: php
          log_type: php-error
          __path__: /var/log/php-fpm/error.log
    
    pipeline_stages:
      # Combine multiline PHP errors
      - multiline:
          firstline: '^\[\d{2}-[A-Za-z]{3}-\d{4}'
          max_wait_time: 3s
      
      # Parse error format
      - regex:
          expression: '^\[(?P<timestamp>[^\]]+)\] (?P<level>\w+):'
      
      # Add labels
      - labels:
          level:
```

#### Promtail Systemd Service
Create file: `/etc/systemd/system/promtail.service`

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
ExecStart=/opt/promtail/promtail \
  -config.file=/etc/promtail/promtail-config.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=promtail

# Resource limits
LimitNOFILE=65536

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/promtail

[Install]
WantedBy=multi-user.target
```

### Grafana Configuration

#### Grafana Main Configuration
Create file: `/etc/grafana/grafana.ini`

```ini
# Grafana Configuration File
# Documentation: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/

##################### Server Configuration #####################
[server]
# Protocol (http, https, h2, socket)
protocol = http

# The IP address to bind to
http_addr = 0.0.0.0

# The port to bind to
http_port = 3000

# The public facing domain name used to access Grafana from a browser
domain = grafana.yourdomain.com

# Redirect to correct domain if host header does not match domain
enforce_domain = false

# The full public facing URL
root_url = %(protocol)s://%(domain)s:%(http_port)s/

# Serve Grafana from subpath
serve_from_sub_path = false

# Log web requests
router_logging = false

# Enable gzip compression
enable_gzip = true

##################### Database Configuration #####################
[database]
# Database type (sqlite3, mysql, postgres)
type = sqlite3

# Database host (for mysql/postgres)
host = 127.0.0.1:3306

# Database name
name = grafana

# Database user
user = root

# Database password
password =

# For sqlite3 only, path relative to data_path setting
path = grafana.db

# Max idle connections in the connection pool
max_idle_conn = 2

# Max open connections in the connection pool
max_open_conn = 0

# Connection max lifetime (seconds)
conn_max_lifetime = 14400

# Log queries (for debugging)
log_queries = false

##################### Authentication Configuration #####################
[auth]
# Set to true to disable login form
disable_login_form = false

# Set to true to disable signout menu
disable_signout_menu = false

# Anonymous access
[auth.anonymous]
enabled = false

# Basic authentication
[auth.basic]
enabled = true

# LDAP authentication (configure if needed)
[auth.ldap]
enabled = false
config_file = /etc/grafana/ldap.toml
allow_sign_up = true

##################### Session Configuration #####################
[session]
# Session provider (memory, file, redis, mysql, postgres)
provider = file

# Provider config depends on provider type
provider_config = sessions

# Session cookie name
cookie_name = grafana_sess

# Session cookie secure
cookie_secure = false

# Session life time in seconds
session_life_time = 86400

##################### Security Configuration #####################
[security]
# Default admin user password (change immediately after first login)
admin_user = admin
admin_password = admin

# Secret key for signing (generate unique key)
secret_key = SW2YcwTIb9zpOOhoPsMm

# Disable gravatar profile images
disable_gravatar = false

# Data source proxy whitelist
data_source_proxy_whitelist =

# Disable protection against brute force login attempts
disable_brute_force_login_protection = false

##################### Users Configuration #####################
[users]
# Allow users to sign up
allow_sign_up = false

# Allow non-admin users to create organizations
allow_org_create = false

# Auto assign users to organization
auto_assign_org = true

# Auto assign organization role
auto_assign_org_role = Viewer

# Require email verification
verify_email_enabled = false

# Default home dashboard path
default_theme = dark

##################### Logging Configuration #####################
[log]
# Log mode (console, file, syslog)
mode = console file

# Log level (trace, debug, info, warn, error, critical)
level = info

# File logging
[log.file]
log_rotate = true
max_lines = 1000000
max_size_shift = 28
daily_rotate = true
max_days = 7

##################### Metrics Configuration #####################
[metrics]
enabled = true
interval_seconds = 10

# Prometheus metrics
[metrics.prometheus]
enabled = true

##################### Dashboards Configuration #####################
[dashboards]
# Versions to keep for each dashboard
versions_to_keep = 20

# Minimum dashboard refresh interval
min_refresh_interval = 5s

# Default home dashboard
default_home_dashboard_path =

##################### Data Sources Configuration #####################
[datasources]
# Upper limit of data sources that Grafana will return
datasource_limit = 5000

##################### Alerting Configuration #####################
[alerting]
enabled = true
execute_alerts = true

# Evaluation timeout
evaluation_timeout_seconds = 30

# Notification timeout
notification_timeout_seconds = 30

# Max attempts to send notifications
max_attempts = 3

##################### Explore Configuration #####################
[explore]
enabled = true

##################### Plugins Configuration #####################
[plugins]
enable_alpha = false
app_tls_skip_verify_insecure = false

##################### Feature Toggles #####################
[feature_toggles]
enable = 

##################### RBAC Configuration #####################
[rbac]
# Enable RBAC permissions
enabled = true

##################### Live Configuration #####################
[live]
max_connections = 100
allowed_origins = *
```

#### Grafana Loki Datasource Provisioning
Create file: `/etc/grafana/provisioning/datasources/loki.yaml`

```yaml
# Grafana Datasource Provisioning for Loki
# This file automatically configures Loki as a datasource

apiVersion: 1

# Delete existing datasources before creating new ones
deleteDatasources:
  - name: Loki
    orgId: 1

# Datasource configuration
datasources:
  # Loki datasource
  - name: Loki
    type: loki
    access: proxy
    orgId: 1
    url: http://loki-server-2:3100
    isDefault: true
    version: 1
    editable: true
    jsonData:
      # Maximum number of lines to return
      maxLines: 1000
      # Timeout for queries
      timeout: 300
      # Derived fields for linking logs to traces (optional)
      derivedFields:
        - datasourceUid: tempo
          matcherRegex: "trace_id=(\\w+)"
          name: TraceID
          url: "$${__value.raw}"
    
  # Prometheus datasource for metrics
  - name: Prometheus
    type: prometheus
    access: proxy
    orgId: 1
    url: http://prometheus-server-1:9090
    isDefault: false
    version: 1
    editable: true
    jsonData:
      # Scrape interval
      timeInterval: 15s
      # Query timeout
      queryTimeout: 60s
      # HTTP method for queries
      httpMethod: POST
```

#### Grafana Dashboard Provisioning
Create file: `/etc/grafana/provisioning/dashboards/dashboards.yaml`

```yaml
# Grafana Dashboard Provisioning
# This file tells Grafana where to find dashboard JSON files

apiVersion: 1

providers:
  # Default dashboard provider
  - name: 'default'
    orgId: 1
    folder: 'General'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

#### Grafana Systemd Service
The service is already created by the RPM installation, but verify:

```bash
# View the service file
sudo systemctl cat grafana-server
```

### Prometheus Configuration

#### Prometheus Main Configuration
Create file: `/etc/prometheus/prometheus.yml`

```yaml
# Prometheus Configuration
# This file defines what metrics to scrape and how

# Global configuration
global:
  # How frequently to scrape targets
  scrape_interval: 15s
  
  # How long until a scrape request times out
  scrape_timeout: 10s
  
  # How frequently to evaluate rules
  evaluation_interval: 15s
  
  # Labels to attach to any time series or alerts
  external_labels:
    cluster: 'logging-cluster'
    environment: 'production'

# Alertmanager configuration (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093

# Load rules once and periodically evaluate them
rule_files:
  - "/etc/prometheus/rules/*.yml"

# Scrape configurations
scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          component: 'prometheus'

  # Loki Writer
  - job_name: 'loki-writer'
    static_configs:
      - targets: ['loki-server-1:3100']
        labels:
          component: 'loki'
          role: 'writer'

  # Loki Reader
  - job_name: 'loki-reader'
    static_configs:
      - targets: ['loki-server-2:3100']
        labels:
          component: 'loki'
          role: 'reader'

  # Grafana
  - job_name: 'grafana'
    static_configs:
      - targets:
          - 'grafana-server-1:3000'
          - 'grafana-server-2:3000'
        labels:
          component: 'grafana'

  # Promtail agents - Node discovery
  # Configure file_sd_configs for dynamic discovery of Promtail instances
  - job_name: 'promtail'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/promtail-*.yml'
        refresh_interval: 5m
    relabel_configs:
      # Relabel to add module_name and node labels
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 'localhost:9080'

  # System metrics - Node Exporter
  - job_name: 'node-exporter'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/nodes-*.yml'
        refresh_interval: 5m

# Remote write configuration (optional - for long-term storage)
# remote_write:
#   - url: http://remote-storage:9009/api/v1/push
```

#### Prometheus Alerting Rules
Create file: `/etc/prometheus/rules/loki-alerts.yml`

```yaml
# Prometheus Alerting Rules for Loki Infrastructure
# These rules generate alerts when issues are detected

groups:
  # Loki health and availability alerts
  - name: loki_health
    interval: 30s
    rules:
      # Loki instance down
      - alert: LokiDown
        expr: up{job=~"loki.*"} == 0
        for: 5m
        labels:
          severity: critical
          component: loki
        annotations:
          summary: "Loki instance {{ $labels.instance }} is down"
          description: "Loki {{ $labels.role }} on {{ $labels.instance }} has been down for more than 5 minutes"

      # High ingestion lag
      - alert: LokiHighIngestionLag
        expr: |
          (time() - loki_ingester_flush_queue_length) > 300
        for: 10m
        labels:
          severity: warning
          component: loki
        annotations:
          summary: "Loki ingestion lag is high"
          description: "Loki on {{ $labels.instance }} has ingestion lag over 5 minutes"

      # Disk space low
      - alert: LokiDiskSpaceLow
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/data/loki"} / node_filesystem_size_bytes{mountpoint="/data/loki"}) < 0.15
        for: 5m
        labels:
          severity: warning
          component: loki
        annotations:
          summary: "Loki disk space is running low"
          description: "Loki storage on {{ $labels.instance }} has less than 15% free space"

  # Promtail health alerts
  - name: promtail_health
    interval: 30s
    rules:
      # Promtail instance down
      - alert: PromtailDown
        expr: up{job="promtail"} == 0
        for: 5m
        labels:
          severity: warning
          component: promtail
        annotations:
          summary: "Promtail instance {{ $labels.instance }} is down"
          description: "Promtail on {{ $labels.instance }} has been down for more than 5 minutes"

      # High file lag
      - alert: PromtailHighFileLag
        expr: |
          (time() - promtail_file_bytes_total) > 600
        for: 10m
        labels:
          severity: warning
          component: promtail
        annotations:
          summary: "Promtail file lag is high"
          description: "Promtail on {{ $labels.instance }} is lagging behind on file reading"

  # Grafana health alerts
  - name: grafana_health
    interval: 30s
    rules:
      # Grafana instance down
      - alert: GrafanaDown
        expr: up{job="grafana"} == 0
        for: 5m
        labels:
          severity: critical
          component: grafana
        annotations:
          summary: "Grafana instance {{ $labels.instance }} is down"
          description: "Grafana on {{ $labels.instance }} has been down for more than 5 minutes"
```

#### Prometheus Service Discovery for Promtail
Create file: `/etc/prometheus/targets/promtail-nodes.yml`

```yaml
# Prometheus Service Discovery for Promtail Instances
# Add all application servers running Promtail

# This is an example - create one file per module for better organization

# User Management Module
- targets:
    - 'tomcat-node-01:9080'
    - 'tomcat-node-02:9080'
  labels:
    module_name: 'user-management'
    application: 'tomcat'
    environment: 'production'

# Payment Gateway Module
- targets:
    - 'php-node-01:9080'
    - 'php-node-02:9080'
  labels:
    module_name: 'payment-gateway'
    application: 'php'
    environment: 'production'

# Add more modules as needed...
```

#### Prometheus Systemd Service
Create file: `/etc/systemd/system/prometheus.service`

```ini
[Unit]
Description=Prometheus Time Series Database
Documentation=https://prometheus.io/docs/introduction/overview/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/opt/prometheus/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/data/prometheus \
  --storage.tsdb.retention.time=15d \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-lifecycle
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=prometheus

# Resource limits
LimitNOFILE=65536

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data/prometheus

[Install]
WantedBy=multi-user.target
```

### HAProxy Configuration

#### HAProxy Configuration File
Create file: `/etc/haproxy/haproxy.cfg`

```cfg
# HAProxy Configuration for Loki Load Balancing
# This load balancer distributes log write traffic across Loki writers

#---------------------------------------------------------------------
# Global settings
#---------------------------------------------------------------------
global
    # Logging
    log         127.0.0.1 local0
    log         127.0.0.1 local1 notice
    
    # Runtime
    chroot      /var/lib/haproxy
    pidfile     /var/run/haproxy.pid
    maxconn     4000
    user        haproxy
    group       haproxy
    daemon
    
    # Performance tuning
    nbproc      4
    nbthread    2
    cpu-map     auto:1/1-4 0-3
    
    # Stats socket for runtime API
    stats socket /var/lib/haproxy/stats mode 600 level admin
    stats timeout 2m

#---------------------------------------------------------------------
# Default settings
#---------------------------------------------------------------------
defaults
    mode                    http
    log                     global
    option                  httplog
    option                  dontlognull
    option                  http-server-close
    option                  redispatch
    retries                 3
    timeout http-request    10s
    timeout queue           1m
    timeout connect         10s
    timeout client          30s
    timeout server          30s
    timeout http-keep-alive 10s
    timeout check           10s
    maxconn                 3000

#---------------------------------------------------------------------
# Stats page configuration
#---------------------------------------------------------------------
listen stats
    bind *:8080
    stats enable
    stats uri /stats
    stats realm HAProxy\ Statistics
    stats auth admin:changeme123
    stats refresh 30s
    stats show-legends
    stats show-node

#---------------------------------------------------------------------
# Loki write path load balancer
#---------------------------------------------------------------------
frontend loki_write_frontend
    bind *:3100
    default_backend loki_write_backend
    
    # Logging
    option httplog
    log-format "%ci:%cp [%tr] %ft %b/%s %TR/%Tw/%Tc/%Tr/%Ta %ST %B %CC %CS %tsc %ac/%fc/%bc/%sc/%rc %sq/%bq %hr %hs %{+Q}r"
    
    # Health check endpoint
    acl health_check path_beg /ready
    use_backend loki_health if health_check

#---------------------------------------------------------------------
# Loki write backend
#---------------------------------------------------------------------
backend loki_write_backend
    balance roundrobin
    option httpchk GET /ready
    http-check expect status 200
    
    # Connection pooling
    option http-keep-alive
    
    # Servers
    server loki-writer-1 loki-server-1:3100 check inter 5s rise 2 fall 3 maxconn 1000
    server loki-writer-2 loki-server-2:3100 check inter 5s rise 2 fall 3 maxconn 1000 backup

#---------------------------------------------------------------------
# Loki health check backend
#---------------------------------------------------------------------
backend loki_health
    server loki-writer-1 loki-server-1:3100 check
```

---

## RBAC Implementation

### Understanding RBAC in Grafana

**RBAC (Role-Based Access Control)** allows you to control:
1. Who can access which dashboards
2. What data sources they can query
3. Which modules/applications they can see logs for

### RBAC Strategy for Module-Based Access

#### 1. Organization Structure

Create separate Organizations or use Teams within a single Organization:

**Option A: Single Organization with Teams** (Recommended)
- One Grafana organization
- Multiple teams (DevOps, SRE, Dev-Team-UserManagement, Dev-Team-Payment, etc.)
- Each team has access to specific module logs

**Option B: Multiple Organizations**
- Separate organization for each major team
- Better isolation but more complex management

#### 2. Create Teams in Grafana

```bash
# Using Grafana API to create teams

# Set variables
GRAFANA_URL="http://grafana-server-1:3000"
ADMIN_USER="admin"
ADMIN_PASS="admin"

# Create teams for each module
curl -X POST "${GRAFANA_URL}/api/teams" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DevOps Team",
    "email": "devops@company.com"
  }'

curl -X POST "${GRAFANA_URL}/api/teams" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SRE Team",
    "email": "sre@company.com"
  }'

curl -X POST "${GRAFANA_URL}/api/teams" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dev Team - User Management",
    "email": "dev-usermgmt@company.com"
  }'

curl -X POST "${GRAFANA_URL}/api/teams" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dev Team - Payment Gateway",
    "email": "dev-payment@company.com"
  }'

# Repeat for all 10 modules...
```

#### 3. Create Users and Assign to Teams

```bash
# Create user
curl -X POST "${GRAFANA_URL}/api/admin/users" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Developer",
    "email": "john@company.com",
    "login": "john",
    "password": "secure_password",
    "OrgId": 1
  }'

# Get user ID from response, then add to team
USER_ID=2  # From API response
TEAM_ID=3  # Dev Team - User Management

curl -X POST "${GRAFANA_URL}/api/teams/${TEAM_ID}/members" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d "{
    \"userId\": ${USER_ID}
  }"
```

#### 4. Create Dashboards with Variable Filters

Create a dashboard with these variables:

**Dashboard JSON snippet** - Variables section:

```json
{
  "templating": {
    "list": [
      {
        "name": "module_name",
        "type": "query",
        "label": "Module Name",
        "datasource": "Loki",
        "query": "label_values(module_name)",
        "multi": false,
        "includeAll": false,
        "refresh": 1,
        "sort": 1
      },
      {
        "name": "node",
        "type": "query",
        "label": "Node",
        "datasource": "Loki",
        "query": "label_values({module_name=\"$module_name\"}, node)",
        "multi": true,
        "includeAll": true,
        "refresh": 1,
        "sort": 1
      },
      {
        "name": "log_level",
        "type": "custom",
        "label": "Log Level",
        "query": "ERROR,WARN,INFO,DEBUG",
        "multi": true,
        "includeAll": true
      }
    ]
  }
}
```

#### 5. Set Dashboard Permissions

```bash
# Set permissions on dashboard to restrict access by team

DASHBOARD_UID="abc123"  # Dashboard UID
TEAM_ID=3               # Dev Team - User Management

# Grant view permission to specific team
curl -X POST "${GRAFANA_URL}/api/dashboards/uid/${DASHBOARD_UID}/permissions" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "teamId": '${TEAM_ID}',
        "permission": 1
      }
    ]
  }'
```

Permission levels:
- 1 = View
- 2 = Edit
- 4 = Admin

#### 6. Implement Query Filtering with RBAC

**Using Grafana Enterprise RBAC** (if available):

Configure data source permissions to automatically filter queries based on team membership.

**Using Query Variables** (Community Edition):

Create dashboard queries that use variables for automatic filtering:

```
{module_name="$module_name", node=~"$node"} |= "$search_query" | level =~ "$log_level"
```

#### 7. RBAC Permission Matrix

| Team | Module Access | Node Access | Dashboard Permissions |
|------|---------------|-------------|----------------------|
| DevOps Team | All 10 modules | All 50+ nodes | Admin on all dashboards |
| SRE Team | All 10 modules | All 50+ nodes | Edit on all dashboards |
| Dev Team - User Management | user-management only | Related nodes only | View on specific dashboard |
| Dev Team - Payment Gateway | payment-gateway only | Related nodes only | View on specific dashboard |

### RBAC Configuration Script

Create file: `/opt/grafana/scripts/setup-rbac.sh`

```bash
#!/bin/bash
# Grafana RBAC Setup Script
# This script automates team and user creation with proper permissions

set -e

# Configuration
GRAFANA_URL="http://localhost:3000"
ADMIN_USER="admin"
ADMIN_PASS="admin"

# Module names (adjust based on your modules)
MODULES=(
  "user-management"
  "payment-gateway"
  "inventory-system"
  "reporting-engine"
  "api-gateway"
  "notification-service"
  "data-warehouse"
  "analytics-platform"
  "customer-portal"
  "admin-console"
)

# Function to create team
create_team() {
  local team_name=$1
  local team_email=$2
  
  echo "Creating team: ${team_name}"
  curl -s -X POST "${GRAFANA_URL}/api/teams" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${team_name}\",
      \"email\": \"${team_email}\"
    }"
  echo
}

# Function to create user
create_user() {
  local username=$1
  local email=$2
  local password=$3
  local name=$4
  
  echo "Creating user: ${username}"
  curl -s -X POST "${GRAFANA_URL}/api/admin/users" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${name}\",
      \"email\": \"${email}\",
      \"login\": \"${username}\",
      \"password\": \"${password}\",
      \"OrgId\": 1
    }"
  echo
}

# Create infrastructure teams
echo "Creating infrastructure teams..."
create_team "DevOps Team" "devops@company.com"
create_team "SRE Team" "sre@company.com"

# Create development teams for each module
echo "Creating development teams for modules..."
for module in "${MODULES[@]}"; do
  team_name="Dev Team - $(echo $module | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')"
  team_email="dev-${module}@company.com"
  create_team "${team_name}" "${team_email}"
done

echo "RBAC setup complete!"
echo "Remember to:"
echo "1. Create users manually or via API"
echo "2. Assign users to appropriate teams"
echo "3. Set dashboard permissions"
echo "4. Configure data source access"
```

Make script executable:
```bash
sudo chmod +x /opt/grafana/scripts/setup-rbac.sh
```

---

## Starting Services

### Start Loki Services

```bash
# On loki-server-1 (Writer)
sudo systemctl daemon-reload
sudo systemctl enable loki-writer
sudo systemctl start loki-writer
sudo systemctl status loki-writer

# Check logs
sudo journalctl -u loki-writer -f

# On loki-server-2 (Reader)
sudo systemctl daemon-reload
sudo systemctl enable loki-reader
sudo systemctl start loki-reader
sudo systemctl status loki-reader

# Check logs
sudo journalctl -u loki-reader -f
```

### Start Grafana Services

```bash
# On both Grafana servers
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
sudo systemctl status grafana-server

# Check logs
sudo journalctl -u grafana-server -f

# Access Grafana
# http://grafana-server-1:3000
# Default login: admin/admin (change immediately)
```

### Start Prometheus Services

```bash
# On both Prometheus servers
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
sudo systemctl status prometheus

# Check logs
sudo journalctl -u prometheus -f

# Access Prometheus
# http://prometheus-server-1:9090
```

### Start Promtail Services

```bash
# On all application servers (50+)
sudo systemctl daemon-reload
sudo systemctl enable promtail
sudo systemctl start promtail
sudo systemctl status promtail

# Check logs
sudo journalctl -u promtail -f
```

### Start HAProxy Service

```bash
# On HAProxy server
sudo systemctl daemon-reload
sudo systemctl enable haproxy
sudo systemctl start haproxy
sudo systemctl status haproxy

# Check logs
sudo journalctl -u haproxy -f

# Access stats page
# http://haproxy-server:8080/stats
# Login: admin/changeme123
```

---

## Testing and Validation

### 1. Verify Promtail is Sending Logs

```bash
# Check Promtail metrics
curl http://application-server:9080/metrics

# Look for these metrics:
# promtail_sent_entries_total - number of log entries sent
# promtail_dropped_entries_total - should be 0
# promtail_targets_active_total - number of active log files being tailed
```

### 2. Verify Loki is Receiving Logs

```bash
# Check Loki ready status
curl http://loki-server-1:3100/ready

# Check Loki metrics
curl http://loki-server-1:3100/metrics

# Query logs directly via API
curl -G -s "http://loki-server-1:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="tomcat-access"}' | jq

# Get label values
curl -G -s "http://loki-server-1:3100/loki/api/v1/label/module_name/values" | jq
```

### 3. Verify Grafana can Query Loki

```bash
# Login to Grafana UI
# Go to Explore
# Select Loki datasource
# Run query: {module_name="user-management"}
# You should see logs appearing
```

### 4. Verify Prometheus is Scraping

```bash
# Access Prometheus UI
# http://prometheus-server-1:9090

# Go to Status > Targets
# Verify all targets are UP
# Check for:
#   - Loki writer
#   - Loki reader
#   - Grafana instances
#   - Promtail agents
```

### 5. Test Log Retention

```bash
# Check current log storage
du -sh /data/loki/chunks/
du -sh /data/loki/index/

# Wait 48 hours and verify old logs are deleted
# Compactor should automatically remove logs older than 2 days
```

### 6. Test HA Failover

```bash
# Stop Loki writer 1
sudo systemctl stop loki-writer

# Verify Promtail switches to writer 2
# Check HAProxy stats page for backend status

# Verify logs still flow
# Query Grafana - logs should continue appearing

# Start writer 1 back up
sudo systemctl start loki-writer
```

### 7. Performance Testing

```bash
# Generate log load
for i in {1..1000}; do
  echo "$(date) INFO Test log entry $i" >> /opt/tomcat/logs/catalina.out
done

# Monitor Loki ingestion rate
curl -s http://loki-server-1:3100/metrics | grep loki_ingester_chunks_created_total

# Monitor query performance in Grafana
# Run large time range queries
# Check response times
```

### 8. RBAC Testing

```bash
# Login as different users
# Verify each user sees only their assigned modules
# Try to access dashboards outside their permissions
# Should see "Access denied" or no data
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Promtail Not Sending Logs

**Symptoms:**
- promtail_sent_entries_total not increasing
- No logs appearing in Loki

**Solutions:**
```bash
# Check Promtail logs
sudo journalctl -u promtail -n 100

# Verify log file permissions
sudo -u promtail ls -la /opt/tomcat/logs/

# Test Loki connectivity
curl -v http://loki-server-1:3100/ready

# Check firewall
sudo firewall-cmd --list-all

# Verify Promtail configuration syntax
/opt/promtail/promtail -config.file=/etc/promtail/promtail-config.yaml -dry-run
```

#### Issue 2: Loki High Memory Usage

**Symptoms:**
- OOM kills
- Slow query performance

**Solutions:**
```bash
# Check memory usage
free -h

# Reduce chunk cache size in loki.yaml
# chunk_cache_config:
#   fifocache:
#     max_size_bytes: 512MB  # Reduced from 1GB

# Restart Loki
sudo systemctl restart loki-writer
```

#### Issue 3: Disk Space Full

**Symptoms:**
- Loki stops accepting logs
- Errors in logs about disk space

**Solutions:**
```bash
# Check disk usage
df -h /data/loki

# Manually run compactor
# (Usually automatic, but can force)

# Reduce retention period temporarily
# Update loki.yaml retention_period to 24h

# Clean up old chunks manually (dangerous - backup first)
find /data/loki/chunks -mtime +2 -delete
```

#### Issue 4: Queries Timing Out

**Symptoms:**
- Grafana shows timeout errors
- Slow dashboard loading

**Solutions:**
```bash
# Increase query timeout in Grafana datasource
# Set timeout to 300s

# Optimize LogQL queries
# Bad: {job="tomcat"} |= "error"
# Good: {job="tomcat", level="ERROR"}

# Add more query parallelism in loki-reader.yaml
# max_query_parallelism: 64
```

---

## Maintenance Tasks

### Daily Tasks

```bash
# Check service health
sudo systemctl status loki-writer loki-reader grafana-server prometheus promtail

# Check disk usage
df -h /data/loki

# Review error logs
sudo journalctl -u loki-writer -p err --since today
```

### Weekly Tasks

```bash
# Review Prometheus alerts
# Check for any firing alerts

# Review log volume trends
# Use Grafana dashboard to check ingestion rates

# Check for failed Promtail agents
# Review Prometheus targets
```

### Monthly Tasks

```bash
# Update system packages
sudo yum update -y

# Rotate old Grafana dashboards
# Archive unused dashboards

# Review and update RBAC permissions
# Add/remove users as needed

# Performance review
# Check query response times
# Analyze slow queries
```

---

## Backup and Recovery

### Backup Loki Data

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/loki"
DATE=$(date +%Y%m%d)

# Stop Loki
sudo systemctl stop loki-writer

# Backup chunks and index
sudo tar -czf ${BACKUP_DIR}/loki-data-${DATE}.tar.gz /data/loki/

# Start Loki
sudo systemctl start loki-writer
```

### Backup Grafana

```bash
# Backup Grafana database and dashboards
BACKUP_DIR="/backup/grafana"
DATE=$(date +%Y%m%d)

# Backup SQLite database
sudo cp /var/lib/grafana/grafana.db ${BACKUP_DIR}/grafana-db-${DATE}.db

# Backup configuration
sudo cp /etc/grafana/grafana.ini ${BACKUP_DIR}/grafana-ini-${DATE}.ini

# Backup provisioning
sudo tar -czf ${BACKUP_DIR}/grafana-provisioning-${DATE}.tar.gz /etc/grafana/provisioning/
```

---

## Useful Commands Reference

### Loki Commands

```bash
# Check Loki version
/opt/loki/loki --version

# Validate configuration
/opt/loki/loki -config.file=/etc/loki/loki-writer.yaml -verify-config

# Query logs via API
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="tomcat"}' \
  --data-urlencode 'start=1577836800000000000' | jq

# Get label names
curl -s "http://localhost:3100/loki/api/v1/labels" | jq

# Get series
curl -G -s "http://localhost:3100/loki/api/v1/series" \
  --data-urlencode 'match[]={job="tomcat"}' | jq
```

### Promtail Commands

```bash
# Check Promtail version
/opt/promtail/promtail --version

# Validate configuration
/opt/promtail/promtail -config.file=/etc/promtail/promtail-config.yaml -dry-run

# Check positions file
cat /var/lib/promtail/positions.yaml
```

### Prometheus Commands

```bash
# Check Prometheus version
/opt/prometheus/prometheus --version

# Validate configuration
/opt/prometheus/promtool check config /etc/prometheus/prometheus.yml

# Query via API
curl -s "http://localhost:9090/api/v1/query?query=up" | jq
```

---

## Security Hardening Checklist

### Network Security
- [ ] Configure firewall rules on all servers
- [ ] Use internal network for Promtail → Loki communication
- [ ] Enable HTTPS for Grafana (use nginx/apache as reverse proxy)
- [ ] Restrict Prometheus/Loki ports to internal network only

### Authentication
- [ ] Change default Grafana admin password
- [ ] Enable LDAP/OAuth for Grafana if available
- [ ] Implement API key authentication for Loki (in production)
- [ ] Enable basic auth on HAProxy stats page

### Data Security
- [ ] Implement log scrubbing for sensitive data (credit cards, passwords)
- [ ] Enable encryption at rest for Loki storage
- [ ] Regular security audits of log content
- [ ] Implement data retention policies compliant with regulations

### Access Control
- [ ] Implement RBAC in Grafana
- [ ] Regular audit of user permissions
- [ ] Remove inactive users
- [ ] Monitor failed login attempts

---

## Future Enhancements

### Phase 2: MinIO Integration

When ready to migrate to shared object storage:

1. Install MinIO cluster
2. Update Loki configuration to use S3-compatible storage
3. Migrate existing data from local filesystem to MinIO
4. Enable true HA with shared state

### Phase 3: Advanced Features

- Implement log sampling for high-volume applications
- Set up Grafana OnCall for alerting
- Integrate with Jaeger for distributed tracing
- Implement log analytics with ML-based anomaly detection
- Set up log forwarding to SIEM systems

### Phase 4: Scaling

- Add more Loki instances for increased throughput
- Implement Loki microservices mode for better scaling
- Add read replicas for query performance
- Implement caching layer with Redis/Memcached

---

## Conclusion

This setup provides a production-ready, highly available centralized logging infrastructure with:

- **Scalability**: Handles 50+ servers and 10 modules
- **High Availability**: No single point of failure
- **Security**: RBAC implementation for access control
- **Performance**: Optimized for both write and read operations
- **Maintainability**: Clear separation of concerns and easy troubleshooting

The architecture is designed to grow with your needs, with a clear path to add MinIO for shared storage and scale horizontally as log volume increases.

---

## Support and Documentation Links

- Loki Documentation: https://grafana.com/docs/loki/latest/
- Promtail Documentation: https://grafana.com/docs/loki/latest/clients/promtail/
- Grafana Documentation: https://grafana.com/docs/grafana/latest/
- Prometheus Documentation: https://prometheus.io/docs/
- LogQL Query Language: https://grafana.com/docs/loki/latest/logql/
- HAProxy Documentation: http://www.haproxy.org/

---

**Document Version**: 1.0
**Last Updated**: 2024
**Prepared For**: Centralized Logging Infrastructure Setup
