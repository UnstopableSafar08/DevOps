<img width="1142" height="325" alt="image" src="https://github.com/user-attachments/assets/6d2d01f6-8128-47d1-ab72-10081903b889" /># Apache Kafka 4.x KRaft Cluster — Production Setup Guide

> **Environment:** 3-node combined broker+controller cluster  
> **Kafka:** 4.1.2 | **Java:** BellSoft Liberica JDK 21 (LTS) | **OS:** Oracle Linux 9 / RHEL 9  
> **Hardware per node:** 8 vCPU · 16 GB RAM · Dedicated data disk · Swap disabled

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Node Planning](#3-node-planning)
4. [Install BellSoft Liberica JDK 21](#4-install-bellsoft-liberica-jdk-21)
5. [Install Apache Kafka 4.1.2](#5-install-apache-kafka-412)
6. [Directory Structure](#6-directory-structure)
7. [server.properties](#7-serverproperties)
8. [JVM Tuning](#8-jvm-tuning)
9. [Logging — log4j2.yaml](#9-logging--log4j2yaml)
10. [systemd Service Unit](#10-systemd-service-unit)
11. [OS-Level Tuning](#11-os-level-tuning)
12. [Initialize the KRaft Cluster](#12-initialize-the-kraft-cluster)
13. [Start and Verify](#13-start-and-verify)
14. [Producer Configuration](#14-producer-configuration)
15. [Create Production Topics](#15-create-production-topics)
16. [Maintenance Operations](#16-maintenance-operations)
17. [Why Swap Must Be Disabled](#17-why-swap-must-be-disabled)

---

## 1. Architecture Overview

### What is Kafka?

Apache Kafka is a distributed event streaming platform designed for high-throughput, fault-tolerant, and scalable data pipelines. This guide covers production deployment with emphasis on:

- **Reliability**: Zero data loss configuration
- **Availability**: High availability and fault tolerance
- **Performance**: Optimized throughput and latency
- **Security**: Authentication, authorization, and encryption
- **Operability**: <a href="https://github.com/UnstopableSafar08/DevOps/blob/main/kafka/readme-old.md#monitoring-and-observability" Monitoring</a>, maintenance, and troubleshooting

Prior to Kafka 3.3, every cluster required a separate Apache ZooKeeper ensemble for metadata management. **KRaft** (Kafka Raft) is Kafka's built-in consensus mechanism that replaces ZooKeeper entirely. As of Kafka 4.0, ZooKeeper support is completely removed — all clusters run KRaft exclusively.

## Architecture Decision: KRaft vs ZooKeeper

### KRaft Mode (Recommended)

**What is KRaft?**
KRaft (Kafka Raft) is Kafka's built-in consensus protocol that eliminates the need for ZooKeeper. Introduced in KIP-500, it's production-ready since Kafka 3.3.

**Advantages:**
- Simpler architecture (no separate ZooKeeper cluster)
- Faster metadata operations (10x improvement)
- Better scalability (millions of partitions)
- Sub-second controller failover
- Reduced operational complexity
- Lower infrastructure costs
- Future-proof (ZooKeeper support will be removed in Kafka 4.0+)

**When to Use:**
- New Kafka deployments
- Long-lived clusters (3+ years)
- Large-scale deployments (>50k partitions)
- Cost-sensitive environments

### ZooKeeper Mode (Legacy)

**When to Consider:**
- Existing production clusters already on ZooKeeper
- Need for immediate production deployment with minimal risk
- Organization has limited Kafka expertise
- Short-lived projects (1-2 years)
- Regulatory requirements for proven technology

**Migration Path:**
ZooKeeper-based clusters should plan migration to KRaft mode by 2025-2026, as support will be removed in Kafka 4.0.


### Cluster Layout

```
┌──────────────────────────────────────────────────────────────┐
│                   3-Node KRaft Cluster                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Node 1     │  │   Node 2     │  │   Node 3     │      │
│  │ 10.x.x.147   │  │ 10.x.x.148   │  │ 10.x.x.149   │      │
│  │              │  │              │  │              │      │
│  │  [Broker]    │  │  [Broker]    │  │  [Broker]    │      │
│  │ [Controller] │  │ [Controller] │  │ [Controller] │      │
│  │              │  │              │  │              │      │
│  │  Port 9092   │  │  Port 9092   │  │  Port 9092   │      │
│  │  (clients)   │  │  (clients)   │  │  (clients)   │      │
│  │  Port 9093   │  │  Port 9093   │  │  Port 9093   │      │
│  │  (internal)  │  │  (internal)  │  │  (internal)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  Data disk:     /data/kafka      (message log segments)      │
│  Metadata disk: /kafka/metadata  (KRaft consensus log)       │
│  App logs:      /var/log/kafka                               │
└──────────────────────────────────────────────────────────────┘
```

Each node runs both `broker` and `controller` roles. With 3 controllers, the cluster tolerates **1 node failure** while maintaining quorum (2 of 3 nodes).

### Kafka / Java Version Matrix

| Kafka | Recommended Java | Notes |
|-------|-----------------|-------|
| 4.1.x | JDK 21 (LTS) | Production recommended |
| 4.0.x | JDK 17 or 21 | ZooKeeper fully removed |
| 3.7.x | JDK 17 | Last ZooKeeper-compatible release |

---

## 2. Prerequisites

### System Requirements (per node)

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB |
| Data disk | 100 GB | 500 GB+ SSD/NVMe |
| Metadata disk | 20 GB | Separate SSD |
| Swap | **Disabled** | **Disabled** |
| OS | RHEL/OEL 8+ | RHEL/OEL 9 |

### Disable Swap (mandatory)

Swap causes multi-second JVM GC pauses. Kafka with swap is unreliable in production.

```bash
# Disable immediately
swapoff -a

# Remove from fstab permanently
sed -i '/swap/d' /etc/fstab

# Verify
free -h
# Swap: 0B  0B  0B
```

### Required Packages

```bash
dnf install -y curl wget tar gzip util-linux-user
```

### Firewall Rules (all 3 nodes)

```bash
firewall-cmd --permanent --add-port=9092/tcp   # broker — clients
firewall-cmd --permanent --add-port=9093/tcp   # controller — internal only
firewall-cmd --reload
firewall-cmd --list-ports
```

> **Security note:** Port 9093 (controller) should be firewalled from external access. Only inter-node traffic needs port 9093.

### SELinux — Label Kafka Directories

```bash
semanage fcontext -a -t var_log_t "/var/log/kafka(/.*)?"
semanage fcontext -a -t var_t "/data/kafka(/.*)?"
semanage fcontext -a -t var_t "/kafka(/.*)?"
restorecon -Rv /var/log/kafka /data/kafka /kafka
```

### Create Kafka System User

```bash
useradd --system --no-create-home --shell /sbin/nologin kafka
```

---

## 3. Node Planning

Set these values on each server before starting. Only `NODE_ID` and `ADVERTISED_IP` differ per node.

| Node | Hostname | IP | NODE_ID |
|------|----------|----|---------|
| Node 1 | kafka-node1 | 10.x.x.147 | 1 |
| Node 2 | kafka-node2 | 10.x.x.148 | 2 |
| Node 3 | kafka-node3 | 10.x.x.149 | 3 |

### /etc/hosts — all nodes

```bash
cat >> /etc/hosts <<EOF
10.x.x.147  kafka-node1
10.x.x.148  kafka-node2
10.x.x.149  kafka-node3
EOF
```

---

## 4. Install BellSoft Liberica JDK 21

BellSoft Liberica is a certified, production-grade OpenJDK distribution. JDK 21 is the current LTS release with best compatibility for Kafka 4.x.

```bash
#!/bin/bash
set -euo pipefail

JDK_URL="https://download.bell-sw.com/java/21.0.11+11/bellsoft-jdk21.0.11+11-linux-amd64.tar.gz"
TARBALL="/tmp/bellsoft-jdk21.tar.gz"
INSTALL_BASE="/usr/lib/jvm"

echo "[1/5] Downloading BellSoft Liberica JDK 21..."
curl -fL --progress-bar -o "$TARBALL" "$JDK_URL"

echo "[2/5] Extracting to ${INSTALL_BASE}..."
mkdir -p "$INSTALL_BASE"
tar -xzf "$TARBALL" -C "$INSTALL_BASE"

EXTRACTED=$(tar -tzf "$TARBALL" | head -1 | cut -d/ -f1)
JAVA_HOME_PATH="${INSTALL_BASE}/${EXTRACTED}"

echo "[3/5] Creating symlink /usr/jdk21 → ${JAVA_HOME_PATH}"
ln -sfn "$JAVA_HOME_PATH" /usr/jdk21

echo "[4/5] Registering with alternatives..."
update-alternatives --install /usr/bin/java  java  "${JAVA_HOME_PATH}/bin/java"  100
update-alternatives --install /usr/bin/javac javac "${JAVA_HOME_PATH}/bin/javac" 100
update-alternatives --set java  "${JAVA_HOME_PATH}/bin/java"
update-alternatives --set javac "${JAVA_HOME_PATH}/bin/javac"

echo "[5/5] Writing /etc/profile.d/java.sh..."
cat > /etc/profile.d/java.sh <<JEOF
export JAVA_HOME=/usr/jdk21
export PATH=\$JAVA_HOME/bin:\$PATH
JEOF

source /etc/profile.d/java.sh
rm -f "$TARBALL"

echo "--- JDK install complete ---"
java -version
```

### Verify

```bash
source /etc/profile.d/java.sh
java -version
# openjdk version "21.0.11" 2025-04-15 LTS
# OpenJDK Runtime Environment BellSoft Liberica (build 21.0.11+11-LTS)
```

> **Note:** `/usr/jdk21` should be readable by the `kafka` user. Verify:
> ```bash
> ls -la /usr/jdk21/bin/java
> sudo -u kafka /usr/jdk21/bin/java -version
> ```

---

## 5. Install Apache Kafka 4.1.2

```bash
#!/bin/bash
set -euo pipefail

KAFKA_VERSION="4.1.2"
SCALA_VERSION="2.13"
KAFKA_URL="https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"
TARBALL="/tmp/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"
INSTALL_DIR="/kafka"

echo "Downloading Kafka ${KAFKA_VERSION}..."
wget -q --show-progress -O "$TARBALL" "$KAFKA_URL"

echo "Extracting to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
tar -xzf "$TARBALL" -C "$INSTALL_DIR"
ln -sfn "${INSTALL_DIR}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}" "${INSTALL_DIR}/kafka"

echo "Adding Kafka to PATH..."
echo "export PATH=${INSTALL_DIR}/kafka/bin:\$PATH" > /etc/profile.d/kafka.sh
source /etc/profile.d/kafka.sh

rm -f "$TARBALL"
echo "Kafka ${KAFKA_VERSION} installed at ${INSTALL_DIR}/kafka"
```

> **Note:** Remove or rename the default sample configs to prevent accidental use:
> ```bash
> mv /kafka/kafka/config/broker.properties \
>    /kafka/kafka/config/broker.properties.DEFAULT_UNUSED
> mv /kafka/kafka/config/controller.properties \
>    /kafka/kafka/config/controller.properties.DEFAULT_UNUSED
> ```
> The default `broker.properties` has `log.dirs=/tmp/...` and `replication.factor=1` — dangerous if accidentally started.

---

## 6. Directory Structure

Separate data and metadata onto different disks to eliminate I/O contention.

```
/
├── data/
│   └── kafka/               ← message log segments (dedicated data disk)
├── kafka/
│   ├── kafka/               ← Kafka installation
│   │   ├── bin/
│   │   └── config/
│   │       ├── server.properties
│   │       ├── log4j2.yaml
│   │       └── jvm.options
│   └── metadata/            ← KRaft metadata log (separate from data)
└── var/log/kafka/           ← all application logs
    ├── server.log
    ├── controller.log
    ├── state-change.log
    ├── kafka-request.log
    ├── log-cleaner.log
    ├── kafka-authorizer.log
    └── kafka-gc.log
```

### Create Directories

```bash
mkdir -p /data/kafka
mkdir -p /kafka/metadata
mkdir -p /var/log/kafka
mkdir -p /etc/kafka

# Ownership
chown -R kafka:kafka /data/kafka
chown -R kafka:kafka /kafka/metadata
chown -R kafka:kafka /var/log/kafka
chown -R kafka:kafka /kafka/kafka
```

### fstab Mount Options (if separate disks)

```bash
# /etc/fstab — XFS with performance flags for Kafka workloads
/dev/sdX  /data   xfs  defaults,noatime,nodiratime,allocsize=64m  0 0
/dev/sdY  /kafka  xfs  defaults,noatime,nodiratime                 0 0
```

---

## 7. server.properties

Create `/kafka/kafka/config/server.properties` on each node. Only `node.id` and `advertised.listeners` change per node.

```properties
########################
# KRaft Cluster Identity
########################

# Roles this node plays
# broker = stores and serves messages
# controller = participates in cluster elections
process.roles=broker,controller

# Unique node ID — must differ on every node (1, 2, or 3)
node.id=1

# All 3 controller voters — identical on every node
controller.quorum.voters=1@10.x.x.147:9093,2@10.x.x.148:9093,3@10.x.x.149:9093

########################
# Listeners
########################

# Listen on all interfaces — clients on 9092, controllers on 9093
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093

# Address advertised to clients — set to THIS node's IP
advertised.listeners=PLAINTEXT://10.x.x.147:9092

inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT

########################
# Storage
########################

# Message log segments — dedicated data disk
log.dirs=/data/kafka

# KRaft metadata log — separate from message data
metadata.log.dir=/kafka/metadata

########################
# Log Retention
########################

# Keep messages for 7 days
log.retention.hours=168

# No size-based cap globally (-1 = disabled)
# Set per-topic if needed with --config retention.bytes=...
log.retention.bytes=-1

# 1 GB segment files — faster cleanup and crash recovery
log.segment.bytes=1073741824

# Check retention eligibility every 5 minutes
log.retention.check.interval.ms=300000

# Timestamps use producer-side time
log.message.timestamp.type=CreateTime

# Cleanup policy — delete old segments (not compaction)
log.cleanup.policy=delete

########################
# Flush Policy
########################

# Do NOT force fsync on every N messages or every interval.
# Rely on replication (min.insync.replicas=2 + acks=all) for durability.
# Forced fsync kills throughput and provides false safety.
# Long value = effectively disabled.
log.flush.interval.messages=9223372036854775807
log.flush.interval.ms=9223372036854775807

########################
# Replication & Durability
########################

# 3 copies of every topic by default — survives 1 node failure
default.replication.factor=3

# Producer must get confirmation from 2 of 3 replicas
# Use with acks=all on producers — guarantees no data loss on leader failure
min.insync.replicas=2

# Internal topics — also 3x replicated
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

# Never allow an out-of-sync replica to become leader
# An out-of-sync leader = permanent silent data loss
unclean.leader.election.enable=false

# Rebalance partition leadership periodically for even load distribution
auto.leader.rebalance.enable=true
leader.imbalance.check.interval.seconds=300

# No accidental topic creation from application typos
auto.create.topics.enable=false

# Allow topic deletion via admin commands
delete.topic.enable=true

########################
# Message Size
########################

# Max message size: 10 MB (broker, replica fetch, and consumer fetch aligned)
message.max.bytes=10485760
replica.fetch.max.bytes=10485760
fetch.max.bytes=10485760

# Respect producer's compression — no re-compression overhead at broker
compression.type=producer

########################
# Network & I/O Threads
########################
# Rule: network.threads = CPU cores, io.threads = 2x CPU cores

num.network.threads=8
num.io.threads=16
num.recovery.threads.per.data.dir=4
background.threads=10

# Socket buffers — 1 MB to match kernel sysctl rmem_max/wmem_max
socket.send.buffer.bytes=1048576
socket.receive.buffer.bytes=1048576
socket.request.max.bytes=104857600

# Request queue depth — 1000 handles burst without OOM risk
queued.max.requests=1000

########################
# Connections
########################

max.connections.per.ip=500
connections.max.idle.ms=540000
request.timeout.ms=30000

########################
# Partition Defaults
########################

# 6 partitions default = 2 per node on a 3-broker cluster
num.partitions=6

########################
# Replication Tuning
########################

# Mark replica out-of-sync after 30 seconds without fetch
replica.lag.time.max.ms=30000
replica.socket.timeout.ms=30000

# Replica fetch buffer — 1 MB, matches socket buffers
replica.socket.receive.buffer.bytes=1048576
replica.fetch.wait.max.ms=500

# 4 parallel replication threads per broker
num.replica.fetchers=4

########################
# Graceful Shutdown
########################

controlled.shutdown.enable=true
controlled.shutdown.max.retries=3
controlled.shutdown.retry.backoff.ms=5000

########################
# Consumer Group Coordinator
########################

# Wait 3s after first consumer joins before assigning partitions
# Prevents repeated rebalancing during rolling deployments
group.initial.rebalance.delay.ms=3000

# Keep consumer offset bookmarks for 7 days (matches log retention)
offsets.retention.minutes=10080

########################
# Transactions
########################

transaction.max.timeout.ms=900000

########################
# Protocol Version
########################

inter.broker.protocol.version=4.1
```

### Per-node changes

**Node 2:**
```bash
sed -i 's/^node.id=1/node.id=2/' /kafka/kafka/config/server.properties
sed -i 's/advertised.listeners=PLAINTEXT:\/\/10.x.x.147/advertised.listeners=PLAINTEXT:\/\/10.x.x.148/' \
    /kafka/kafka/config/server.properties
```

**Node 3:**
```bash
sed -i 's/^node.id=1/node.id=3/' /kafka/kafka/config/server.properties
sed -i 's/advertised.listeners=PLAINTEXT:\/\/10.x.x.147/advertised.listeners=PLAINTEXT:\/\/10.x.x.149/' \
    /kafka/kafka/config/server.properties
```

---

## 8. JVM Tuning

Create `/kafka/kafka/config/jvm.options`:

```bash
cat > /kafka/kafka/config/jvm.options <<'EOF'
KAFKA_HEAP_OPTS=-Xms6g -Xmx6g
KAFKA_JVM_PERFORMANCE_OPTS=-server -XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16m -XX:+ExplicitGCInvokesConcurrent -XX:+ParallelRefProcEnabled -XX:+UseCompressedOops -XX:+OptimizeStringConcat -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/log/kafka/heap-dump.hprof
KAFKA_GC_LOG_OPTS=-Xlog:gc*:file=/var/log/kafka/kafka-gc.log:time,uptime:filecount=5,filesize=100m
EOF

```

### RAM Allocation Rationale

| Allocation | Size | Purpose |
|-----------|------|---------|
| JVM heap | 6 GB | Kafka broker objects, metadata cache |
| OS page cache | ~8 GB | Partition segment reads — Kafka's hot path |
| OS + other | ~2 GB | Kernel, system processes |

> **Why not more heap?** Page cache is faster than JVM heap for Kafka reads. More heap = larger GC pauses + less page cache = slower reads. 6g on 16g is the right balance.

### Verify heap after restart

```bash
ps aux | grep kafka | grep -o '\-Xm[sx][^ ]*'
# -Xms6g
# -Xmx6g
```

---

## 9. Logging — log4j2.yaml

Kafka 4.x uses Log4j2 natively. Create `/kafka/kafka/config/log4j2.yaml`:

```yaml
Configuration:
  Properties:
    Property:
      - name: "kafka.logs.dir"
        value: "."
      - name: "logPattern"
        value: "[%d] %p %m (%c)%n"

  Appenders:
    Console:
      name: STDOUT
      PatternLayout:
        pattern: "${logPattern}"

    RollingFile:
      - name: KafkaAppender
        fileName: "${sys:kafka.logs.dir}/server.log"
        filePattern: "${sys:kafka.logs.dir}/server.log.%d{yyyy-MM-dd-HH}"
        PatternLayout:
          pattern: "${logPattern}"
        TimeBasedTriggeringPolicy:
          modulate: true
          interval: 1
        DefaultRolloverStrategy:
          max: 30

      - name: StateChangeAppender
        fileName: "${sys:kafka.logs.dir}/state-change.log"
        filePattern: "${sys:kafka.logs.dir}/state-change.log.%d{yyyy-MM-dd-HH}"
        PatternLayout:
          pattern: "${logPattern}"
        TimeBasedTriggeringPolicy:
          modulate: true
          interval: 1
        DefaultRolloverStrategy:
          max: 30

      - name: RequestAppender
        fileName: "${sys:kafka.logs.dir}/kafka-request.log"
        filePattern: "${sys:kafka.logs.dir}/kafka-request.log.%d{yyyy-MM-dd-HH}"
        PatternLayout:
          pattern: "${logPattern}"
        TimeBasedTriggeringPolicy:
          modulate: true
          interval: 1
        DefaultRolloverStrategy:
          max: 30

      - name: CleanerAppender
        fileName: "${sys:kafka.logs.dir}/log-cleaner.log"
        filePattern: "${sys:kafka.logs.dir}/log-cleaner.log.%d{yyyy-MM-dd-HH}"
        PatternLayout:
          pattern: "${logPattern}"
        TimeBasedTriggeringPolicy:
          modulate: true
          interval: 1
        DefaultRolloverStrategy:
          max: 30

      - name: ControllerAppender
        fileName: "${sys:kafka.logs.dir}/controller.log"
        filePattern: "${sys:kafka.logs.dir}/controller.log.%d{yyyy-MM-dd-HH}"
        PatternLayout:
          pattern: "${logPattern}"
        TimeBasedTriggeringPolicy:
          modulate: true
          interval: 1
        DefaultRolloverStrategy:
          max: 30

      - name: AuthorizerAppender
        fileName: "${sys:kafka.logs.dir}/kafka-authorizer.log"
        filePattern: "${sys:kafka.logs.dir}/kafka-authorizer.log.%d{yyyy-MM-dd-HH}"
        PatternLayout:
          pattern: "${logPattern}"
        TimeBasedTriggeringPolicy:
          modulate: true
          interval: 1
        DefaultRolloverStrategy:
          max: 30

  Loggers:
    Root:
      level: INFO
      AppenderRef:
        - ref: STDOUT
        - ref: KafkaAppender

    Logger:
      - name: kafka
        level: INFO

      - name: org.apache.kafka
        level: INFO

      # Request log — WARN in production (very high volume at INFO)
      # Temporarily set to INFO for debugging, revert immediately after
      - name: kafka.request.logger
        level: WARN
        additivity: false
        AppenderRef:
          ref: RequestAppender

      - name: kafka.network.RequestChannel$
        level: WARN
        additivity: false
        AppenderRef:
          ref: RequestAppender

      - name: org.apache.kafka.controller
        level: INFO
        additivity: false
        AppenderRef:
          ref: ControllerAppender

      - name: org.apache.kafka.storage.internals.log.LogCleaner
        level: INFO
        additivity: false
        AppenderRef:
          ref: CleanerAppender

      - name: org.apache.kafka.storage.internals.log.LogCleaner$CleanerThread
        level: INFO
        additivity: false
        AppenderRef:
          ref: CleanerAppender

      - name: org.apache.kafka.storage.internals.log.Cleaner
        level: INFO
        additivity: false
        AppenderRef:
          ref: CleanerAppender

      - name: state.change.logger
        level: INFO
        additivity: false
        AppenderRef:
          ref: StateChangeAppender

      - name: kafka.authorizer.logger
        level: INFO
        additivity: false
        AppenderRef:
          ref: AuthorizerAppender
```

### logrotate — OS-level backup

```bash
cat > /etc/logrotate.d/kafka <<'EOF'
/var/log/kafka/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    dateext
    dateformat -%Y%m%d
    sharedscripts
    postrotate
        # Log4j2 handles its own rolling — this covers any files Log4j2 misses
        /bin/kill -HUP $(cat /var/run/kafka/kafka.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
EOF
```

> **Note:** Avoid `copytruncate` with Kafka. It can lose log lines written between the copy and truncate operations. Log4j2's own rolling (configured above) is the primary rotation mechanism.

---

## 10. systemd Service Unit

```bash
cat > /etc/systemd/system/kafka.service <<'EOF'
[Unit]
Description=Apache Kafka KRaft Broker
Documentation=https://kafka.apache.org
Requires=network-online.target
After=network-online.target

[Service]
# Protect Kafka from OOM killer — lower score = less likely to be killed
# Critical on hosts with swap disabled — OOM killer is the only safety net
OOMScoreAdjust=-500

Type=simple
User=kafka
Group=kafka

Environment="JAVA_HOME=/usr/jdk21"
Environment="LOG_DIR=/var/log/kafka"
Environment="KAFKA_LOG4J_OPTS=-Dlog4j2.configurationFile=file:/kafka/kafka/config/log4j2.yaml"

# JVM heap and GC options loaded from file
EnvironmentFile=/kafka/kafka/config/jvm.options

ExecStart=/kafka/kafka/bin/kafka-server-start.sh \
    /kafka/kafka/config/server.properties

ExecStop=/kafka/kafka/bin/kafka-server-stop.sh

Restart=on-failure
RestartSec=10s

# Match limits set in /etc/security/limits.d/kafka.conf
LimitNOFILE=800000
LimitNPROC=65536

# Allow 2 minutes for startup (large partition counts take time to recover)
TimeoutStartSec=120
# Allow 2 minutes for graceful shutdown
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
```

### Verify OOMScoreAdjust is applied after start

```bash
systemctl start kafka
cat /proc/$(pgrep -f kafka.Kafka)/oom_score_adj
# Expected: -500
```

---

## 11. OS-Level Tuning

### Kernel Parameters

```bash
cat > /etc/sysctl.d/99-kafka.conf <<'EOF'
# Minimize swap usage — Kafka GC pauses spike when pages are swapped
# With swap disabled this is a safety setting for any future swap device
vm.swappiness=1

# Allow dirty page ratio to reach 80% before forcing writeback
# Kafka writes sequentially — OS buffering is beneficial
vm.dirty_ratio=80

# Start background writeback at 5% dirty pages — smooth continuous flushing
vm.dirty_background_ratio=5

# Socket buffer sizes — 128 MB maximum
# Must be >= socket.send.buffer.bytes and socket.receive.buffer.bytes in server.properties
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.core.rmem_default=8388608
net.core.wmem_default=8388608

# TCP buffer sizes: min / default / max
net.ipv4.tcp_rmem=4096 87380 134217728
net.ipv4.tcp_wmem=4096 65536 134217728

# Queue more packets before dropping — absorbs burst traffic
net.core.netdev_max_backlog=5000

# TCP window scaling for high-bandwidth inter-broker replication
net.ipv4.tcp_window_scaling=1

# System-wide file descriptor limit
fs.file-max=1000000
EOF

sysctl -p /etc/sysctl.d/99-kafka.conf
```

### File Descriptor Limits

Kafka opens one file descriptor per partition segment. A 1000-partition cluster with multiple segments per partition requires hundreds of thousands of file descriptors.

```bash
cat > /etc/security/limits.d/kafka.conf <<'EOF'
kafka soft nofile 800000
kafka hard nofile 800000
kafka soft nproc  65536
kafka hard nproc  65536
EOF
```

### Disk Scheduler

```bash
# SSD/NVMe — no scheduling overhead
echo none > /sys/block/sda/queue/scheduler

# HDD — deadline prevents starvation
# echo mq-deadline > /sys/block/sda/queue/scheduler

# Sequential read-ahead: 4 MB — helps Kafka's sequential segment reads
echo 4096 > /sys/block/sda/queue/read_ahead_kb
```

**Persist via udev (survives reboot):**

```bash
cat > /etc/udev/rules.d/60-kafka-disk.rules <<'EOF'
ACTION=="add|change", KERNEL=="sda", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="none"
ACTION=="add|change", KERNEL=="sdb", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="none"
EOF

udevadm control --reload-rules
```

---

## 12. Initialize the KRaft Cluster

> **Critical:** The cluster UUID must be identical on all 3 nodes. Generate once, copy everywhere.

### Step 1 — Generate UUID (Node 1 only)

```bash
CLUSTER_ID=$(/kafka/kafka/bin/kafka-storage.sh random-uuid)
echo "Cluster UUID: $CLUSTER_ID"
# Save this — you need it on Node 2 and Node 3
```

### Step 2 — Format storage (all 3 nodes)

```bash
# Replace with UUID from Step 1
CLUSTER_ID="<paste-uuid-here>"

/kafka/kafka/bin/kafka-storage.sh format \
  --cluster-id "$CLUSTER_ID" \
  --config /kafka/kafka/config/server.properties

# Expected output:
# Formatting /data/kafka with metadata.version X.X-IVX
# Formatting /kafka/metadata with metadata.version X.X-IVX
```

---

## 13. Start and Verify

### Start on all 3 nodes

```bash
systemctl enable --now kafka
systemctl status kafka
```

### Verify quorum health

```bash
/kafka/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server 10.x.x.147:9092 \
  describe --status
```

**Expected healthy output:**

```
ClusterId:              <your-cluster-uuid>
LeaderId:               2
LeaderEpoch:            4
HighWatermark:          898126
MaxFollowerLag:         0
MaxFollowerLagTimeMs:   360
CurrentVoters:          [{"id": 1, ...}, {"id": 2, ...}, {"id": 3, ...}]
CurrentObservers:       []
```

| Field | Healthy value |
|-------|--------------|
| MaxFollowerLag | 0 |
| MaxFollowerLagTimeMs | < 500 |
| CurrentVoters | all 3 nodes |
| CurrentObservers | empty |

### Verify all brokers registered

```bash
/kafka/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server 10.x.x.147:9092 2>/dev/null | grep "id:"

# Expected:
# 10.x.x.149:9092 (id: 3 rack: null isFenced: false)
# 10.x.x.148:9092 (id: 2 rack: null isFenced: false)
# 10.x.x.147:9092 (id: 1 rack: null isFenced: false)
```

`isFenced: false` on all nodes = brokers active and serving traffic.

### Check OOM protection

```bash
cat /proc/$(pgrep -f kafka.Kafka)/oom_score_adj
# Must show: -500
```

---

## 14. Producer Configuration

Save as `/kafka/kafka/config/producer.properties`:

```properties
bootstrap.servers=10.x.x.147:9092,10.x.x.148:9092,10.x.x.149:9092

# Idempotence — exactly-once delivery per partition, no duplicates on retry
enable.idempotence=true

# acks=all required with idempotence=true
# Producer waits for acknowledgment from all in-sync replicas
acks=all

# Retries — safe with idempotence (deduplication handles retry duplicates)
retries=2147483647
retry.backoff.ms=500
retry.backoff.max.ms=5000

# Batching — 64 KB batch, wait up to 5ms to fill batch
# Increases throughput at cost of minor latency
batch.size=65536
linger.ms=5
buffer.memory=33554432

# Max in-flight — idempotence requires <= 5
max.in.flight.requests.per.connection=5

# LZ4 compression — fast, ~40% size reduction, minimal CPU overhead
compression.type=lz4

# Timeouts
request.timeout.ms=30000
delivery.timeout.ms=120000
```

---

## 15. Create Production Topics

```bash
/kafka/kafka/bin/kafka-topics.sh --create \
  --bootstrap-server 10.x.x.147:9092 \
  --topic prod-events \
  --partitions 6 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config compression.type=lz4 \
  --config retention.ms=604800000 \
  --config retention.bytes=107374182400

# Verify
/kafka/kafka/bin/kafka-topics.sh \
  --bootstrap-server 10.x.x.147:9092 \
  --describe --topic prod-events
```

### Partition count guidance

| Throughput target | Partitions |
|------------------|-----------|
| < 50 MB/s | 6 (2 per broker) |
| 50–200 MB/s | 12 (4 per broker) |
| 200 MB/s+ | 24+ (8+ per broker) |

> **Rule:** More partitions = more parallelism for consumers, but more open file handles and slower rebalancing. Start conservative, scale up.

---

## 16. Maintenance Operations

### Check under-replicated partitions

```bash
# Should return empty on a healthy cluster
/kafka/kafka/bin/kafka-topics.sh \
  --bootstrap-server 10.x.x.147:9092 \
  --describe --under-replicated-partitions
```

### Check consumer group lag

```bash
/kafka/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server 10.x.x.147:9092 \
  --describe --all-groups
```

### Rolling restart (zero downtime)

```bash
# Restart ONE node at a time. Wait for ISR to recover before next node.
systemctl restart kafka
sleep 30

# Verify ISR clean before proceeding to next node
/kafka/kafka/bin/kafka-topics.sh \
  --bootstrap-server 10.x.x.147:9092 \
  --describe --under-replicated-partitions
# Output must be empty before restarting next node
```

### Check disk usage per broker

```bash
du -sh /data/kafka/
df -h /data
```

### Temporarily enable request logging (debug only)

```bash
# Enable
sed -i 's/kafka.request.logger.*level: WARN/kafka.request.logger\n        level: INFO/' \
    /kafka/kafka/config/log4j2.yaml
systemctl restart kafka

# REVERT after debugging — request log is extremely high volume
sed -i 's/kafka.request.logger.*level: INFO/kafka.request.logger\n        level: WARN/' \
    /kafka/kafka/config/log4j2.yaml
systemctl restart kafka
```

---

## 17. Why Swap Must Be Disabled

Swap is disabled on Kafka hosts by design — not as an optimization, but as a **correctness requirement**.

### The failure chain with swap enabled

```
Memory pressure
→ OS swaps out JVM heap pages to disk
→ GC runs, accesses swapped-out page
→ OS swaps page back in (disk I/O: milliseconds)
→ GC pause: 20ms → seconds
→ Broker stops responding to controller heartbeats
→ Controller marks broker as dead
→ Partition leadership election triggered
→ Consumer rebalancing cascades across cluster
→ Throughput drops, latency spikes, alert storm
```

This failure mode is not theoretical. It is the most common root cause of mysterious Kafka instability in environments where swap is left on.

### Why it is safe to disable swap

On a properly sized Kafka host, memory pressure should not occur:

| Memory | Size | Notes |
|--------|------|-------|
| JVM heap | 6 GB | Fixed (`-Xms` = `-Xmx`) |
| OS page cache | ~8 GB | Kafka's read performance |
| OS + kernel | ~2 GB | Always available |
| **Total** | **16 GB** | No pressure point |

### OOM protection without swap

With swap disabled, the OOM killer is the only safety net. Ensure `OOMScoreAdjust=-500` is set in the systemd unit so the kernel targets other processes first:

```bash
# Verify after each restart
cat /proc/$(pgrep -f kafka.Kafka)/oom_score_adj
# Must show: -500
```

### Industry precedent

Running Kafka with swap disabled is standard practice at Confluent, LinkedIn, and Uber — all documented in their respective engineering blogs. `vm.swappiness=1` (not 0) is set as a secondary guard in case a swap device is added in future.

---

## Quick Reference

### Health check commands

```bash
# Quorum status
/kafka/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server 10.x.x.147:9092 describe --status

# All brokers
/kafka/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server 10.x.x.147:9092 2>/dev/null | grep "id:"

# Under-replicated partitions (must be empty)
/kafka/kafka/bin/kafka-topics.sh \
  --bootstrap-server 10.x.x.147:9092 \
  --describe --under-replicated-partitions

# OOM protection
cat /proc/$(pgrep -f kafka.Kafka)/oom_score_adj

# Heap in use
ps aux | grep kafka | grep -o '\-Xm[sx][^ ]*'

# Service status
systemctl status kafka
```

### Configuration files summary

| File | Purpose |
|------|---------|
| `/kafka/kafka/config/server.properties` | Broker/controller config |
| `/kafka/kafka/config/jvm.options` | Heap and GC settings |
| `/kafka/kafka/config/log4j2.yaml` | Application logging |
| `/kafka/kafka/config/producer.properties` | Producer defaults |
| `/etc/systemd/system/kafka.service` | Process management |
| `/etc/sysctl.d/99-kafka.conf` | Kernel parameters |
| `/etc/security/limits.d/kafka.conf` | File descriptor limits |
| `/etc/logrotate.d/kafka` | Log rotation |
| `/etc/udev/rules.d/60-kafka-disk.rules` | Disk scheduler (persistent) |

---

*Guide based on production deployment of Apache Kafka 4.1.2 KRaft cluster on Oracle Linux 9, 8-core / 16 GB nodes. All configurations verified against running cluster.*
