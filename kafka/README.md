# Production-Ready Apache Kafka Cluster Guide

A comprehensive guide for deploying, configuring, and operating Apache Kafka clusters in production environments, with focus on KRaft mode (ZooKeeper-less architecture).

## Table of Contents

- [Overview](#overview)
- [Architecture Decision: KRaft vs ZooKeeper](#architecture-decision-kraft-vs-zookeeper)
- [Infrastructure Planning](#infrastructure-planning)
- [Hardware Requirements](#hardware-requirements)
- [Network Architecture](#network-architecture)
- [Installation and Setup](#installation-and-setup)
- [Production Configuration](#production-configuration)
- [Security Hardening](#security-hardening)
- [Monitoring and Observability](#monitoring-and-observability)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Performance Tuning](#performance-tuning)
- [Operational Procedures](#operational-procedures)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Capacity Planning](#capacity-planning)
- [Migration Strategies](#migration-strategies)
- [Best Practices Checklist](#best-practices-checklist)
- [References](#references)

---

## Overview

Apache Kafka is a distributed event streaming platform designed for high-throughput, fault-tolerant, and scalable data pipelines. This guide covers production deployment with emphasis on:

- **Reliability**: Zero data loss configuration
- **Availability**: High availability and fault tolerance
- **Performance**: Optimized throughput and latency
- **Security**: Authentication, authorization, and encryption
- **Operability**: Monitoring, maintenance, and troubleshooting

### Version Information

This guide is based on **Apache Kafka 3.9.0** (latest stable release) with KRaft mode. KRaft removes the dependency on ZooKeeper and provides improved performance and simplified operations.

---

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

---

## Infrastructure Planning

### Cluster Sizing

#### Minimum Production Setup
```
Cluster Size: 5 brokers (recommended over 3)
Rationale: 
- Tolerates 2 node failures
- Allows rolling updates with buffer
- Better load distribution
```

#### Small Production (< 100 TB/day)
- **Brokers**: 5 nodes
- **Partitions**: Up to 10,000
- **Throughput**: 100 MB/s aggregate

#### Medium Production (100-500 TB/day)
- **Brokers**: 7-10 nodes
- **Partitions**: 10,000 - 50,000
- **Throughput**: 500 MB/s aggregate

#### Large Production (> 500 TB/day)
- **Brokers**: 10+ nodes
- **Partitions**: 50,000+
- **Throughput**: > 500 MB/s aggregate

### Replication Factor

```
Critical Topics (financial, audit): RF = 3, min.insync.replicas = 2
Standard Topics: RF = 3, min.insync.replicas = 2
Non-critical Topics: RF = 2, min.insync.replicas = 1
```

---

## Hardware Requirements

### Compute Resources

#### Per Broker Node

**Production Tier 1 (High-throughput)**
```yaml
CPU: 24-32 cores (2.5 GHz+)
RAM: 64-128 GB
Disk: 4-8 TB NVMe SSD (RAID 10)
Network: 10 Gbps
```

**Production Tier 2 (Standard)**
```yaml
CPU: 16 cores (2.4 GHz+)
RAM: 32-64 GB
Disk: 2-4 TB SSD
Network: 10 Gbps
```

**Production Tier 3 (Small/Development)**
```yaml
CPU: 8 cores
RAM: 16-32 GB
Disk: 1 TB SSD
Network: 1 Gbps
```

### Storage Considerations

**Disk Type Priority:**
1. **NVMe SSD** (Best: Low latency, high IOPS)
2. **SATA SSD** (Good: Balance of cost and performance)
3. **HDD** (Not recommended: High latency, poor random I/O)

**RAID Configuration:**
- **RAID 10**: Recommended for production (redundancy + performance)
- **RAID 0**: Higher risk but maximum performance
- **No RAID**: Use Kafka replication instead (common in cloud)

**Disk Layout:**
```
/var/kafka-logs-1    # Separate disk/volume
/var/kafka-logs-2    # Separate disk/volume
/var/kafka-logs-3    # Separate disk/volume
/opt/kafka           # Application binaries
/var/log/kafka       # Application logs
```

### Memory Allocation

**JVM Heap:**
```bash
# For 64 GB RAM system
KAFKA_HEAP_OPTS="-Xms16g -Xmx16g"

# For 32 GB RAM system
KAFKA_HEAP_OPTS="-Xms8g -Xmx8g"

# Rule of thumb: 25-50% of system RAM, leaving rest for page cache
```

**Page Cache:**
Kafka relies heavily on OS page cache. Leave 40-60% of RAM for page cache.

---

## Network Architecture

### Network Topology

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │   (Optional)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
    │ Broker 1│         │ Broker 2│         │ Broker 3│
    │  (AZ-1) │◄───────►│  (AZ-2) │◄───────►│  (AZ-3) │
    └────┬────┘         └────┬────┘         └────┬────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Monitoring    │
                    │   & Alerting    │
                    └─────────────────┘
```

### Port Configuration

**Required Ports:**
```yaml
9092: Broker listener (PLAINTEXT)
9093: Controller listener (KRaft)
9094: SSL/TLS listener (optional)
9095: SASL listener (optional)
9999: JMX monitoring port
```

**Firewall Rules:**
```bash
# Broker-to-broker communication
Allow: TCP 9092, 9093 (inter-broker)

# Client-to-broker communication
Allow: TCP 9092 (from application subnets)

# Monitoring
Allow: TCP 9999 (from monitoring subnet)
```

### DNS and Hostnames

**Recommendation:**
Use fully qualified domain names (FQDN) instead of IP addresses:

```properties
# Good
advertised.listeners=PLAINTEXT://kafka-broker-1.prod.company.com:9092

# Avoid
advertised.listeners=PLAINTEXT://10.0.1.5:9092
```

### Multi-Region Considerations

**Same Region (Recommended):**
- Latency: < 2ms
- Suitable for synchronous replication

**Multi-Region (Advanced):**
- Use MirrorMaker 2.0 for async replication
- Not recommended for synchronous replication (latency issues)

---

## Installation and Setup

### Prerequisites

```bash
# Install Java 11 or 17
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk

# Verify Java installation
java -version

# Create Kafka user
sudo useradd -r -s /bin/bash -d /opt/kafka kafka

# Create directories
sudo mkdir -p /opt/kafka
sudo mkdir -p /var/kafka-logs-1
sudo mkdir -p /var/kafka-logs-2
sudo mkdir -p /var/kafka-logs-3
sudo mkdir -p /var/log/kafka

# Set ownership
sudo chown -R kafka:kafka /opt/kafka
sudo chown -R kafka:kafka /var/kafka-logs-*
sudo chown -R kafka:kafka /var/log/kafka
```

### Download and Install Kafka

```bash
# Download Kafka
cd /tmp
wget https://downloads.apache.org/kafka/3.9.0/kafka_2.13-3.9.0.tgz

# Extract
tar -xzf kafka_2.13-3.9.0.tgz
sudo mv kafka_2.13-3.9.0/* /opt/kafka/

# Create symbolic link
sudo ln -s /opt/kafka /opt/kafka-current
```

### System Configuration

#### File Descriptor Limits

Edit `/etc/security/limits.conf`:
```bash
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32000
kafka hard nproc 32000
```

#### Kernel Parameters

Edit `/etc/sysctl.conf`:
```bash
# Swap settings
vm.swappiness=1
vm.dirty_ratio=80
vm.dirty_background_ratio=5

# Network settings
net.core.wmem_default=131072
net.core.rmem_default=131072
net.core.wmem_max=2097152
net.core.rmem_max=2097152
net.ipv4.tcp_wmem=4096 65536 2048000
net.ipv4.tcp_rmem=4096 87380 2048000
net.ipv4.tcp_window_scaling=1
net.ipv4.tcp_max_syn_backlog=8192

# Connection tracking
net.netfilter.nf_conntrack_max=1048576
net.core.somaxconn=1024
```

Apply settings:
```bash
sudo sysctl -p
```

#### Disable Swap

```bash
# Temporary
sudo swapoff -a

# Permanent - comment out swap in /etc/fstab
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

---

## Production Configuration

### KRaft Mode Configuration

#### Server Properties - Broker 1

Create `/opt/kafka/config/server.properties`:

```properties
############################# Server Basics #############################

# Unique node ID (use 1, 2, 3, 4, 5 for 5-node cluster)
node.id=1

# Process roles: combined broker and controller
process.roles=broker,controller

############################# Listeners #############################

# Listener configuration
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
advertised.listeners=PLAINTEXT://kafka-broker-1.prod.company.com:9092

# Controller listener name
controller.listener.names=CONTROLLER

# Inter-broker listener
inter.broker.listener.name=PLAINTEXT

############################# Controller Quorum #############################

# Controller quorum voters (all nodes)
controller.quorum.voters=1@kafka-broker-1.prod.company.com:9093,2@kafka-broker-2.prod.company.com:9093,3@kafka-broker-3.prod.company.com:9093,4@kafka-broker-4.prod.company.com:9093,5@kafka-broker-5.prod.company.com:9093

############################# Log Directories #############################

# Data directories (use multiple for better I/O distribution)
log.dirs=/var/kafka-logs-1,/var/kafka-logs-2,/var/kafka-logs-3

############################# Socket Server Settings #############################

# Number of threads handling network requests
num.network.threads=8

# Number of threads doing disk I/O
num.io.threads=16

# Send buffer size
socket.send.buffer.bytes=102400

# Receive buffer size
socket.receive.buffer.bytes=102400

# Maximum request size
socket.request.max.bytes=104857600

############################# Log Basics #############################

# Default number of partitions
num.partitions=6

# Number of threads for log recovery and flushing
num.recovery.threads.per.data.dir=2

############################# Replication Settings #############################

# Default replication factor
default.replication.factor=3

# Minimum in-sync replicas
min.insync.replicas=2

# Disable unclean leader election (critical for data integrity)
unclean.leader.election.enable=false

# Number of replica fetcher threads
num.replica.fetchers=4

# Replica lag time
replica.lag.time.max.ms=30000

# Replica fetch max bytes
replica.fetch.max.bytes=1048576

############################# Internal Topics #############################

# Offsets topic configuration
offsets.topic.replication.factor=3
offsets.topic.num.partitions=50

# Transaction state log
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
transaction.state.log.num.partitions=50

############################# Log Retention #############################

# Retention by time (7 days)
log.retention.hours=168

# Retention by size (optional - per partition)
# log.retention.bytes=1073741824

# Segment file size (1 GB)
log.segment.bytes=1073741824

# Check interval for log retention
log.retention.check.interval.ms=300000

# Minimum age before segment deletion
log.segment.delete.delay.ms=60000

############################# Log Compaction #############################

# Enable log cleaner
log.cleaner.enable=true

# Number of log cleaner threads
log.cleaner.threads=2

# Log cleaner I/O buffer size
log.cleaner.io.buffer.size=524288

# Log cleaner dedupe buffer size
log.cleaner.dedupe.buffer.size=134217728

############################# Topic Settings #############################

# Disable auto topic creation
auto.create.topics.enable=false

# Compression type
compression.type=producer

# Maximum message size
message.max.bytes=1048576

############################# Controller Settings #############################

# Controller socket timeout
controller.socket.timeout.ms=30000

# Controlled shutdown
controlled.shutdown.enable=true
controlled.shutdown.max.retries=3

############################# Background Threads #############################

# Number of background threads
background.threads=10

############################# Metrics #############################

# Metrics reporters
metric.reporters=

# Metrics recording level
metrics.recording.level=INFO

############################# Quotas #############################

# Producer quota (bytes/sec per client)
# quota.producer.default=10485760

# Consumer quota (bytes/sec per client)
# quota.consumer.default=10485760

############################# Group Coordinator Settings #############################

# Group coordinator settings
group.initial.rebalance.delay.ms=3000
group.max.session.timeout.ms=1800000
group.min.session.timeout.ms=6000
```

**Important:** 
- Change `node.id` to 2, 3, 4, 5 for other brokers
- Update `advertised.listeners` with correct hostname for each broker

### JVM Configuration

Create `/opt/kafka/bin/kafka-server-start-production.sh`:

```bash
#!/bin/bash

# JVM Heap Settings (adjust based on available RAM)
export KAFKA_HEAP_OPTS="-Xms16g -Xmx16g"

# JVM Performance Options (G1GC recommended)
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC \
  -XX:MaxGCPauseMillis=20 \
  -XX:InitiatingHeapOccupancyPercent=35 \
  -XX:G1HeapRegionSize=16M \
  -XX:MinMetaspaceSize=96m \
  -XX:MaxMetaspaceSize=512m \
  -XX:+ParallelRefProcEnabled \
  -XX:+DisableExplicitGC"

# GC Logging
export KAFKA_GC_LOG_OPTS="-Xlog:gc*:file=/var/log/kafka/gc.log:time,tags:filecount=10,filesize=100M"

# JMX Monitoring
export KAFKA_JMX_OPTS="-Dcom.sun.management.jmxremote \
  -Dcom.sun.management.jmxremote.authenticate=false \
  -Dcom.sun.management.jmxremote.ssl=false \
  -Dcom.sun.management.jmxremote.port=9999 \
  -Djava.rmi.server.hostname=kafka-broker-1.prod.company.com"

# Start Kafka
exec /opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
```

Make executable:
```bash
chmod +x /opt/kafka/bin/kafka-server-start-production.sh
```

### Systemd Service

Create `/etc/systemd/system/kafka.service`:

```ini
[Unit]
Description=Apache Kafka Server (KRaft Mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=kafka
Group=kafka
Environment="LOG_DIR=/var/log/kafka"
ExecStart=/opt/kafka/bin/kafka-server-start-production.sh
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kafka

# Process limits
LimitNOFILE=100000
LimitNPROC=32000

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kafka
sudo systemctl start kafka
sudo systemctl status kafka
```

### Cluster Initialization

**Step 1: Generate Cluster ID (run once on any node)**

```bash
CLUSTER_ID=$(kafka-storage.sh random-uuid)
echo $CLUSTER_ID
# Save this UUID - you'll need it on all nodes
# Example: 4L6g3nShT-eMCtK-X86ZQw
```

**Step 2: Format storage on each broker**

```bash
# On each broker (use the SAME cluster ID from step 1)
kafka-storage.sh format \
  -t 4L6g3nShT-eMCtK-X86ZQw \
  -c /opt/kafka/config/server.properties
```

**Step 3: Start all brokers**

```bash
# On each broker
sudo systemctl start kafka
```

**Step 4: Verify cluster formation**

```bash
# Check controller quorum status
kafka-metadata-quorum.sh \
  --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  describe --status

# List brokers
kafka-broker-api-versions.sh \
  --bootstrap-server kafka-broker-1.prod.company.com:9092 | grep id
```

---

## Security Hardening

### SSL/TLS Encryption

#### Generate Certificates

```bash
# Create Certificate Authority (CA)
openssl req -new -x509 -keyout ca-key -out ca-cert -days 3650 \
  -subj "/CN=KafkaCA" -passout pass:ca-password

# Create keystore for broker
keytool -keystore kafka.broker1.keystore.jks -alias broker1 \
  -validity 3650 -genkey -keyalg RSA -ext SAN=dns:kafka-broker-1.prod.company.com \
  -storepass broker-password -keypass broker-password \
  -dname "CN=kafka-broker-1.prod.company.com, OU=Kafka, O=Company, L=City, ST=State, C=US"

# Create CSR
keytool -keystore kafka.broker1.keystore.jks -alias broker1 \
  -certreq -file broker1.csr -storepass broker-password

# Sign certificate
openssl x509 -req -CA ca-cert -CAkey ca-key -in broker1.csr \
  -out broker1-signed.crt -days 3650 -CAcreateserial \
  -passin pass:ca-password

# Import CA cert
keytool -keystore kafka.broker1.keystore.jks -alias CARoot \
  -import -file ca-cert -storepass broker-password -noprompt

# Import signed certificate
keytool -keystore kafka.broker1.keystore.jks -alias broker1 \
  -import -file broker1-signed.crt -storepass broker-password

# Create truststore
keytool -keystore kafka.broker1.truststore.jks -alias CARoot \
  -import -file ca-cert -storepass broker-password -noprompt
```

#### SSL Configuration

Add to `server.properties`:

```properties
# SSL Listeners
listeners=PLAINTEXT://:9092,SSL://:9094,CONTROLLER://:9093
advertised.listeners=PLAINTEXT://kafka-broker-1.prod.company.com:9092,SSL://kafka-broker-1.prod.company.com:9094

# SSL Configuration
ssl.keystore.location=/opt/kafka/ssl/kafka.broker1.keystore.jks
ssl.keystore.password=broker-password
ssl.key.password=broker-password
ssl.truststore.location=/opt/kafka/ssl/kafka.broker1.truststore.jks
ssl.truststore.password=broker-password

# SSL Client Authentication
ssl.client.auth=required

# SSL Protocol
ssl.protocol=TLSv1.3
ssl.enabled.protocols=TLSv1.3,TLSv1.2

# Cipher suites
ssl.cipher.suites=TLS_AES_256_GCM_SHA384,TLS_AES_128_GCM_SHA256
```

### SASL Authentication

#### SASL/SCRAM Configuration

**Step 1: Create SCRAM credentials**

```bash
# Create admin user
kafka-configs.sh --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=admin-secret]' \
  --entity-type users --entity-name admin

# Create producer user
kafka-configs.sh --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=producer-secret]' \
  --entity-type users --entity-name producer-user

# Create consumer user
kafka-configs.sh --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=consumer-secret]' \
  --entity-type users --entity-name consumer-user
```

**Step 2: Configure broker for SASL**

Add to `server.properties`:

```properties
# SASL Listeners
listeners=SASL_SSL://:9095,CONTROLLER://:9093
advertised.listeners=SASL_SSL://kafka-broker-1.prod.company.com:9095

# SASL Configuration
sasl.enabled.mechanisms=SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512

# Inter-broker SASL
security.inter.broker.protocol=SASL_SSL
```

**Step 3: Create JAAS configuration**

Create `/opt/kafka/config/kafka_server_jaas.conf`:

```
KafkaServer {
    org.apache.kafka.common.security.scram.ScramLoginModule required
    username="admin"
    password="admin-secret";
};
```

Update `kafka-server-start-production.sh`:

```bash
export KAFKA_OPTS="-Djava.security.auth.login.config=/opt/kafka/config/kafka_server_jaas.conf"
```

### Authorization (ACLs)

Enable ACLs in `server.properties`:

```properties
# Enable ACLs
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer

# Super users
super.users=User:admin
```

#### Create ACLs

```bash
# Allow producer to write to topic
kafka-acls.sh --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  --add --allow-principal User:producer-user \
  --operation Write --topic financial-transactions

# Allow consumer to read from topic
kafka-acls.sh --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  --add --allow-principal User:consumer-user \
  --operation Read --topic financial-transactions \
  --group financial-consumer-group

# List ACLs
kafka-acls.sh --bootstrap-server kafka-broker-1.prod.company.com:9092 \
  --list --topic financial-transactions
```

---

## Monitoring and Observability

### Key Metrics to Monitor

#### Broker Metrics

**Critical Metrics:**
```
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions
  Alert: > 0 for > 5 minutes

kafka.controller:type=KafkaController,name=ActiveControllerCount
  Alert: != 1 on any broker

kafka.server:type=ReplicaManager,name=PartitionCount
  Monitor: Track growth

kafka.server:type=ReplicaManager,name=LeaderCount
  Monitor: Should be balanced across brokers

kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce
  Alert: p99 > 100ms

kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Fetch
  Alert: p99 > 100ms
```

**Performance Metrics:**
```
kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec
kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec
kafka.log:type=LogFlushStats,name=LogFlushRateAndTimeMs
```

**System Metrics:**
```
# CPU Usage
# Memory Usage
# Disk I/O (IOPS, throughput)
# Network I/O (bandwidth utilization)
# Disk space usage
```

### Prometheus and Grafana Setup

#### Install JMX Exporter

```bash
# Download JMX Exporter
cd /opt/kafka
wget https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.19.0/jmx_prometheus_javaagent-0.19.0.jar
```

#### JMX Exporter Configuration

Create `/opt/kafka/config/kafka-metrics.yml`:

```yaml
lowercaseOutputName: true
lowercaseOutputLabelNames: true

rules:
  # Broker metrics
  - pattern: kafka.server<type=(.+), name=(.+)><>Value
    name: kafka_server_$1_$2
    
  # Controller metrics
  - pattern: kafka.controller<type=(.+), name=(.+)><>Value
    name: kafka_controller_$1_$2
    
  # Network metrics
  - pattern: kafka.network<type=(.+), name=(.+), request=(.+)><>Count
    name: kafka_network_$1_$2_total
    labels:
      request: $3
      
  # Log metrics
  - pattern: kafka.log<type=(.+), name=(.+)><>Value
    name: kafka_log_$1_$2
```

Update `kafka-server-start-production.sh`:

```bash
export KAFKA_OPTS="$KAFKA_OPTS -javaagent:/opt/kafka/jmx_prometheus_javaagent-0.19.0.jar=7071:/opt/kafka/config/kafka-metrics.yml"
```

#### Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets:
        - 'kafka-broker-1.prod.company.com:7071'
        - 'kafka-broker-2.prod.company.com:7071'
        - 'kafka-broker-3.prod.company.com:7071'
        - 'kafka-broker-4.prod.company.com:7071'
        - 'kafka-broker-5.prod.company.com:7071'
```

### Logging Configuration

Configure Log4j in `/opt/kafka/config/log4j.properties`:

```properties
# Root logger
log4j.rootLogger=INFO, stdout, kafkaAppender

# Console appender
log4j.appender.stdout=org.apache.log4j.ConsoleAppender
log4j.appender.stdout.layout=org.apache.log4j.PatternLayout
log4j.appender.stdout.layout.ConversionPattern=[%d] %p %m (%c)%n

# File appender
log4j.appender.kafkaAppender=org.apache.log4j.RollingFileAppender
log4j.appender.kafkaAppender.File=/var/log/kafka/server.log
log4j.appender.kafkaAppender.MaxFileSize=100MB
log4j.appender.kafkaAppender.MaxBackupIndex=10
log4j.appender.kafkaAppender.layout=org.apache.log4j.PatternLayout
log4j.appender.kafkaAppender.layout.ConversionPattern=[%d] %p %m (%c)%n

# Request logging
log4j.appender.requestAppender=org.apache.log4j.RollingFileAppender
log4j.appender.requestAppender.File=/var/log/kafka/kafka-request.log
log4j.appender.requestAppender.MaxFileSize=100MB
log4j.appender.requestAppender.MaxBackupIndex=10
log4j.appender.requestAppender.layout=org.apache.log4j.PatternLayout
log4j.appender.requestAppender.layout.ConversionPattern=[%d] %p %m (%c)%n

# Controller logging
log4j.logger.kafka.controller=INFO, controllerAppender
log4j.additivity.kafka.controller=false
log4j.appender.controllerAppender=org.apache.log4j.RollingFileAppender
log4j.appender.controllerAppender.File=/var/log/kafka/controller.log
log4j.appender.controllerAppender.MaxFileSize=100MB
log4j.appender.controllerAppender.MaxBackupIndex=10
```

### Alerting Rules

**Critical Alerts (PagerDuty/Opsgenie):**
```yaml
groups:
  - name: kafka_critical
    rules:
      - alert: KafkaBrokerDown
        expr: up{job="kafka"} == 0
        for: 1m
        annotations:
          summary: "Kafka broker {{ $labels.instance }} is down"
          
      - alert: KafkaUnderReplicatedPartitions
        expr: kafka_server_replicamanager_underreplicatedpartitions > 0
        for: 5m
        annotations:
          summary: "Kafka has under-replicated partitions"
          
      - alert: KafkaNoActiveController
        expr: sum(kafka_controller_kafkacontroller_activecontrollercount) != 1
        for: 1m
        annotations:
          summary: "Kafka cluster has no active controller"
```

**Warning Alerts (Slack/Email):**
```yaml
  - name: kafka_warning
    rules:
      - alert: KafkaHighProduceLatency
        expr: kafka_network_requestmetrics_totaltimems{request="Produce",quantile="0.99"} > 100
        for: 10m
        annotations:
          summary: "Kafka produce latency is high"
          
      - alert: KafkaDiskUsageHigh
        expr: (node_filesystem_avail_bytes{mountpoint="/var/kafka-logs-1"} / node_filesystem_size_bytes{mountpoint="/var/kafka-logs-1"}) < 0.2
        for: 5m
        annotations:
          summary: "Kafka disk usage is high"
```

---

## Backup and Disaster Recovery

### Backup Strategies

#### Option 1: Topic Mirroring (Recommended)

Use MirrorMaker 2.0 for real-time replication to DR cluster:

```properties
# mm2.properties
clusters=primary,secondary
primary.bootstrap.servers=kafka1.primary:9092,kafka2.primary:9092
secondary.bootstrap.servers=kafka1.secondary:9092,kafka2.secondary:9092

primary->secondary.enabled=true
primary->secondary.topics=.*

# Replication settings
replication.factor=3
refresh.topics.interval.seconds=60
sync.topic.configs.enabled=true
```

Start MirrorMaker:
```bash
connect-mirror-maker.sh mm2.properties
```

#### Option 2: Snapshot Backups

```bash
#!/bin/bash
# kafka-backup.sh

BACKUP_DIR="/backup/kafka"
DATE=$(date +%Y%m%d-%H%M%S)

# Stop broker (for consistent backup)
systemctl stop kafka

# Backup Kafka data
tar -czf $BACKUP_DIR/kafka-data-$DATE.tar.gz /var/kafka-logs-*

# Backup configuration
tar -czf $BACKUP_DIR/kafka-config-$DATE.tar.gz /opt/kafka/config

# Start broker
systemctl start kafka

# Retention: Keep last 7 days
find $BACKUP_DIR -name "kafka-data-*.tar.gz" -mtime +7 -delete
```

#### Option 3: Kafka Connect

Use Kafka Connect with S3 sink for archival:

```json
{
  "name": "s3-sink-connector",
  "config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "tasks.max": "10",
    "topics": "financial-transactions",
    "s3.bucket.name": "kafka-archive",
    "s3.region": "us-east-1",
    "flush.size": "10000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "format.class": "io.confluent.connect.s3.format.json.JsonFormat",
    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd",
    "partition.duration.ms": "3600000",
    "timestamp.extractor": "Record"
  }
}
```

### Disaster Recovery Procedures

#### Scenario: Single Broker Failure

```bash
# 1. Identify failed broker
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# 2. Replace hardware (if needed)

# 3. Reinstall Kafka

# 4. Restore configuration
tar -xzf kafka-config-backup.tar.gz -C /opt/kafka/

# 5. Format storage with SAME cluster ID
kafka-storage.sh format -t <CLUSTER_ID> -c /opt/kafka/config/server.properties

# 6. Start broker
systemctl start kafka

# 7. Monitor re-replication
watch kafka-topics.sh --describe --bootstrap-server kafka1:9092 --under-replicated-partitions
```

#### Scenario: Total Cluster Loss

```bash
# 1. Restore from backup on all nodes
for i in 1 2 3 4 5; do
  ssh kafka$i "tar -xzf /backup/kafka/kafka-data-latest.tar.gz -C /"
done

# 2. Start all brokers
for i in 1 2 3 4 5; do
  ssh kafka$i "systemctl start kafka"
done

# 3. Verify cluster health
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# 4. Verify data integrity
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list kafka1:9092 \
  --topic financial-transactions --time -1
```

### RTO and RPO Targets

```
Recovery Time Objective (RTO):
  Single broker failure: < 15 minutes
  Multi-broker failure: < 1 hour
  Total cluster failure: < 4 hours

Recovery Point Objective (RPO):
  With MirrorMaker: Near-zero (< 1 second)
  With snapshots: Last backup interval (typically hours)
  With acks=all and RF=3: Zero data loss
```

---

## Performance Tuning

### Producer Configuration

**High Throughput Configuration:**
```properties
bootstrap.servers=kafka1:9092,kafka2:9092,kafka3:9092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer

# Throughput optimization
acks=1
compression.type=lz4
batch.size=65536
linger.ms=10
buffer.memory=67108864

# Retries
retries=2147483647
max.in.flight.requests.per.connection=5
```

**Low Latency Configuration:**
```properties
# Latency optimization
acks=1
compression.type=none
batch.size=16384
linger.ms=0
buffer.memory=33554432
```

**High Durability Configuration (Financial Transactions):**
```properties
# Durability optimization
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
retries=2147483647
compression.type=lz4

# Timeouts
request.timeout.ms=30000
delivery.timeout.ms=120000

# Transactions
transactional.id=producer-1
transaction.timeout.ms=60000
```

### Consumer Configuration

**High Throughput Configuration:**
```properties
bootstrap.servers=kafka1:9092,kafka2:9092,kafka3:9092
group.id=consumer-group-1
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=org.apache.kafka.common.serialization.StringDeserializer

# Throughput optimization
fetch.min.bytes=1048576
fetch.max.wait.ms=500
max.partition.fetch.bytes=1048576

# Poll settings
max.poll.records=500
max.poll.interval.ms=300000

# Offset commit
enable.auto.commit=false
```

**Low Latency Configuration:**
```properties
# Latency optimization
fetch.min.bytes=1
fetch.max.wait.ms=100
max.partition.fetch.bytes=524288
max.poll.records=100
```

### Topic Configuration

```bash
# High throughput topic
kafka-topics.sh --create \
  --bootstrap-server kafka1:9092 \
  --topic high-throughput-topic \
  --partitions 50 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config compression.type=lz4 \
  --config segment.bytes=1073741824 \
  --config retention.ms=86400000

# Low latency topic
kafka-topics.sh --create \
  --bootstrap-server kafka1:9092 \
  --topic low-latency-topic \
  --partitions 20 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config compression.type=none \
  --config segment.bytes=536870912

# Compacted topic (state management)
kafka-topics.sh --create \
  --bootstrap-server kafka1:9092 \
  --topic compacted-topic \
  --partitions 10 \
  --replication-factor 3 \
  --config cleanup.policy=compact \
  --config min.compaction.lag.ms=0 \
  --config segment.ms=3600000
```

### Partition Strategy

**Calculating Optimal Partitions:**
```
Target Throughput (MB/s) / Producer Throughput per Partition (MB/s) = Partitions

Example:
  Target: 500 MB/s
  Per partition: 10 MB/s
  Partitions: 500 / 10 = 50 partitions
```

**Guidelines:**
- Start with: (target_throughput_MB_s / 10 MB/s)
- Minimum: Number of consumers in largest consumer group
- Maximum: Consider operational overhead (1000s of partitions require more resources)
- Rule of thumb: 1000-2000 partitions per broker maximum

---

## Operational Procedures

### Rolling Restart

```bash
#!/bin/bash
# rolling-restart.sh

BROKERS=(kafka1 kafka2 kafka3 kafka4 kafka5)

for broker in "${BROKERS[@]}"; do
  echo "Restarting $broker..."
  
  # Stop broker
  ssh $broker "systemctl stop kafka"
  
  # Wait for partitions to re-elect leaders (30 seconds)
  sleep 30
  
  # Start broker
  ssh $broker "systemctl start kafka"
  
  # Wait for broker to fully start and rejoin (60 seconds)
  sleep 60
  
  # Verify broker is up
  kafka-broker-api-versions.sh --bootstrap-server $broker:9092
  
  # Check for under-replicated partitions
  under_rep=$(kafka-topics.sh --describe --bootstrap-server kafka1:9092 \
    --under-replicated-partitions | wc -l)
  
  if [ $under_rep -gt 0 ]; then
    echo "WARNING: $under_rep under-replicated partitions after restarting $broker"
  fi
  
  echo "Waiting 2 minutes before next broker..."
  sleep 120
done

echo "Rolling restart complete"
```

### Adding a New Broker

```bash
# 1. Install Kafka on new node (broker 6)

# 2. Configure server.properties with node.id=6
# Add to controller.quorum.voters on ALL nodes (requires restart)

# 3. Format storage
kafka-storage.sh format -t <CLUSTER_ID> -c /opt/kafka/config/server.properties

# 4. Start new broker
systemctl start kafka

# 5. Verify broker joined
kafka-broker-api-versions.sh --bootstrap-server kafka6:9092

# 6. Create partition reassignment plan
cat > reassignment.json << EOF
{
  "version": 1,
  "partitions": [
    {"topic": "my-topic", "partition": 0, "replicas": [1,2,6]},
    {"topic": "my-topic", "partition": 1, "replicas": [2,3,6]}
  ]
}
EOF

# 7. Execute reassignment
kafka-reassign-partitions.sh --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json --execute

# 8. Monitor progress
kafka-reassign-partitions.sh --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json --verify
```

### Removing a Broker

```bash
# 1. Generate reassignment to move partitions OFF broker 5
kafka-reassign-partitions.sh --bootstrap-server kafka1:9092 \
  --broker-list "1,2,3,4" \
  --topics-to-move-json-file topics.json \
  --generate

# 2. Execute reassignment
kafka-reassign-partitions.sh --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json --execute

# 3. Wait for completion (can take hours)
kafka-reassign-partitions.sh --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json --verify

# 4. Stop broker
ssh kafka5 "systemctl stop kafka"

# 5. Update controller.quorum.voters on remaining nodes (requires restart)
```

### Increasing Partition Count

```bash
# WARNING: Cannot decrease partition count

# Increase partitions
kafka-topics.sh --alter \
  --bootstrap-server kafka1:9092 \
  --topic my-topic \
  --partitions 100

# Note: Existing messages won't be redistributed
# New messages will use new partitions
```

### Upgrading Kafka Version

```bash
# Kafka supports rolling upgrades

# 1. Read upgrade notes
# https://kafka.apache.org/documentation/#upgrade

# 2. Update inter.broker.protocol.version (optional, for rollback safety)
# In server.properties: inter.broker.protocol.version=3.8

# 3. Rolling upgrade
for broker in kafka1 kafka2 kafka3 kafka4 kafka5; do
  ssh $broker << EOF
    # Stop broker
    systemctl stop kafka
    
    # Backup current version
    cp -r /opt/kafka /opt/kafka-3.8-backup
    
    # Install new version
    tar -xzf kafka_2.13-3.9.0.tgz -C /opt/
    rm -rf /opt/kafka/*
    mv /opt/kafka_2.13-3.9.0/* /opt/kafka/
    
    # Restore configuration
    cp /opt/kafka-3.8-backup/config/server.properties /opt/kafka/config/
    
    # Start broker
    systemctl start kafka
EOF
  
  sleep 120  # Wait before next broker
done

# 4. After all brokers upgraded, update inter.broker.protocol.version to 3.9
# Requires another rolling restart
```

---

## Troubleshooting Guide

### Common Issues

#### Issue: Under-Replicated Partitions

**Symptoms:**
```
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions > 0
```

**Diagnosis:**
```bash
# List under-replicated partitions
kafka-topics.sh --describe \
  --bootstrap-server kafka1:9092 \
  --under-replicated-partitions

# Check broker logs
tail -f /var/log/kafka/server.log | grep -i "replica"

# Check network connectivity
ping kafka2
telnet kafka2 9092
```

**Resolution:**
1. Check if any broker is down - restart if needed
2. Check network connectivity between brokers
3. Check disk space on affected brokers
4. Check for I/O bottlenecks (iostat -x 5)
5. Increase num.replica.fetchers if network is slow

#### Issue: No Active Controller

**Symptoms:**
```
kafka.controller:type=KafkaController,name=ActiveControllerCount != 1
```

**Diagnosis:**
```bash
# Check controller status
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# Check logs on all brokers
grep -i "controller" /var/log/kafka/server.log
```

**Resolution:**
1. Verify quorum health (need majority of nodes)
2. Check for network partitions
3. Restart broker with highest node.id first
4. If stuck, rolling restart all brokers

#### Issue: High Produce Latency

**Symptoms:**
```
Produce request p99 latency > 100ms
```

**Diagnosis:**
```bash
# Check broker metrics
kafka-run-class.sh kafka.tools.JmxTool \
  --object-name kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce \
  --jmx-url service:jmx:rmi:///jndi/rmi://kafka1:9999/jmxrmi

# Check disk I/O
iostat -x 5

# Check network
iftop -i eth0
```

**Resolution:**
1. Check disk I/O (use faster disks, RAID 10, or NVMe)
2. Reduce batch.size or linger.ms on producer
3. Increase num.io.threads on broker
4. Add more partitions to distribute load
5. Check if log compaction is running (CPU intensive)

#### Issue: Consumer Lag

**Symptoms:**
```
Consumer group lag continuously increasing
```

**Diagnosis:**
```bash
# Check consumer lag
kafka-consumer-groups.sh --bootstrap-server kafka1:9092 \
  --group my-consumer-group --describe

# Check consumer logs
# Check if consumers are alive

# Check partition distribution
kafka-consumer-groups.sh --bootstrap-server kafka1:9092 \
  --group my-consumer-group --describe --members
```

**Resolution:**
1. Scale out consumers (add more instances)
2. Increase max.poll.records for batch processing
3. Optimize consumer processing logic
4. Check for slow consumers (look at processing time)
5. Increase session.timeout.ms if consumers are timing out

#### Issue: Disk Full

**Symptoms:**
```
ERROR Error while writing to checkpoint file (kafka.server.LogDirFailureChannel)
```

**Diagnosis:**
```bash
# Check disk space
df -h /var/kafka-logs-*

# Check largest topics
kafka-log-dirs.sh --bootstrap-server kafka1:9092 \
  --broker-list 1 --describe
```

**Resolution:**
```bash
# Immediate: Reduce retention
kafka-configs.sh --bootstrap-server kafka1:9092 \
  --entity-type topics --entity-name large-topic \
  --alter --add-config retention.ms=3600000

# Long-term: Add more disk or brokers
```

#### Issue: Slow Consumer Rebalance

**Symptoms:**
```
Consumer group rebalance takes > 30 seconds
```

**Resolution:**
```properties
# On consumers:
session.timeout.ms=30000
heartbeat.interval.ms=3000
max.poll.interval.ms=600000

# On broker server.properties:
group.initial.rebalance.delay.ms=3000
```

### Diagnostic Commands

```bash
# Check cluster status
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# List all topics
kafka-topics.sh --list --bootstrap-server kafka1:9092

# Describe topic
kafka-topics.sh --describe --bootstrap-server kafka1:9092 --topic my-topic

# Check consumer groups
kafka-consumer-groups.sh --list --bootstrap-server kafka1:9092

# Check consumer lag
kafka-consumer-groups.sh --bootstrap-server kafka1:9092 \
  --group my-group --describe

# Check log segments
kafka-log-dirs.sh --bootstrap-server kafka1:9092 \
  --describe --broker-list 1,2,3

# Check broker configs
kafka-configs.sh --bootstrap-server kafka1:9092 \
  --entity-type brokers --entity-name 1 --describe

# Verify topic configs
kafka-configs.sh --bootstrap-server kafka1:9092 \
  --entity-type topics --entity-name my-topic --describe

# Test connectivity
kafka-broker-api-versions.sh --bootstrap-server kafka1:9092
```

---

## Capacity Planning

### Disk Space Calculation

```
Required Disk Space = (Daily Throughput × Retention Days × Replication Factor) / Number of Brokers

Example:
  Daily Throughput: 1 TB
  Retention: 7 days
  Replication Factor: 3
  Brokers: 5
  
  Required per Broker = (1000 GB × 7 × 3) / 5 = 4,200 GB
  
  With 30% buffer: 4,200 × 1.3 = 5,460 GB (~6 TB per broker)
```

### Throughput Planning

**Single Partition Limits:**
```
Producer: ~10-50 MB/s per partition
Consumer: ~20-100 MB/s per partition
```

**Broker Limits:**
```
Network: Limited by NIC (1 Gbps = 125 MB/s, 10 Gbps = 1250 MB/s)
Disk: Limited by disk I/O (SSD: 500+ MB/s, NVMe: 3000+ MB/s)
```

### Memory Requirements

```
JVM Heap: 6-16 GB (typically 25-50% of total RAM)
Page Cache: Remaining RAM (50-75%)

Example for 64 GB RAM:
  JVM Heap: 16 GB
  Page Cache: 45 GB
  OS/Other: 3 GB
```

### Network Bandwidth

```
Required Bandwidth = Peak Throughput × Replication Factor × 1.5 (buffer)

Example:
  Peak: 500 MB/s
  Replication: 3
  Required: 500 × 3 × 1.5 = 2,250 MB/s = 18 Gbps
  
  Recommendation: Use 25 Gbps NICs
```

---

## Migration Strategies

### Migrating from ZooKeeper to KRaft

**Note:** Direct migration from ZooKeeper to KRaft is supported but complex. Test thoroughly in non-production first.

```bash
# 1. Ensure all brokers on Kafka 3.3+

# 2. Enable migration on ZooKeeper brokers
# Add to server.properties:
zookeeper.metadata.migration.enable=true

# 3. Deploy KRaft controllers (separate from brokers)
# Configure controllers with migration enabled

# 4. Update brokers to use KRaft controllers
# Add to server.properties:
controller.quorum.voters=1@controller1:9093,2@controller2:9093,3@controller3:9093

# 5. Rolling restart brokers

# 6. Monitor migration
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# 7. Finalize migration (irreversible)
kafka-metadata-migration.sh --finalize

# 8. Remove ZooKeeper configuration
# Remove: zookeeper.connect from server.properties

# 9. Decommission ZooKeeper cluster
```

### Blue-Green Deployment

```bash
# 1. Deploy new KRaft cluster (Green)

# 2. Set up MirrorMaker 2.0 from old cluster (Blue) to new cluster (Green)

# 3. Let MirrorMaker catch up (monitor lag)

# 4. During maintenance window:
#    a. Stop producers/consumers
#    b. Wait for MirrorMaker to catch up completely
#    c. Update application configs to point to Green cluster
#    d. Start producers/consumers

# 5. Monitor Green cluster

# 6. Keep Blue cluster for rollback (1-2 weeks)

# 7. Decommission Blue cluster
```

---

## Best Practices Checklist

### Pre-Production Checklist

**Infrastructure:**
- [ ] Minimum 5 broker nodes deployed
- [ ] Brokers distributed across availability zones
- [ ] Adequate CPU, memory, and disk resources
- [ ] 10 Gbps network connectivity
- [ ] Firewall rules configured
- [ ] DNS entries created
- [ ] NTP configured for time synchronization

**Configuration:**
- [ ] replication.factor=3 for all critical topics
- [ ] min.insync.replicas=2
- [ ] unclean.leader.election.enable=false
- [ ] auto.create.topics.enable=false
- [ ] log.retention properly configured
- [ ] JVM heap size appropriate (6-16 GB)
- [ ] File descriptors increased (100k+)
- [ ] Swap disabled
- [ ] Kernel parameters tuned

**Security:**
- [ ] SSL/TLS enabled
- [ ] SASL authentication configured
- [ ] ACLs defined for all users
- [ ] Certificates valid and not expiring soon
- [ ] Secrets management implemented
- [ ] Network segmentation applied

**Monitoring:**
- [ ] JMX exporter configured
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards created
- [ ] Critical alerts configured
- [ ] On-call rotation established
- [ ] Runbooks documented

**Backup & DR:**
- [ ] Backup strategy defined
- [ ] MirrorMaker 2.0 configured (if using)
- [ ] Backup testing completed
- [ ] DR procedures documented
- [ ] RTO/RPO targets defined
- [ ] DR drills scheduled

**Testing:**
- [ ] Load testing completed
- [ ] Failover testing completed
- [ ] Rolling restart tested
- [ ] Consumer lag monitoring verified
- [ ] Performance benchmarks documented

### Operational Checklist

**Daily:**
- [ ] Check under-replicated partitions (should be 0)
- [ ] Check active controller count (should be 1)
- [ ] Review critical alerts
- [ ] Check consumer lag
- [ ] Review disk space

**Weekly:**
- [ ] Review performance metrics
- [ ] Check for slow consumers
- [ ] Review partition distribution
- [ ] Check log segment sizes
- [ ] Review security logs

**Monthly:**
- [ ] Capacity planning review
- [ ] Performance tuning review
- [ ] Update documentation
- [ ] Review and update alerts
- [ ] Security audit
- [ ] DR drill

**Quarterly:**
- [ ] Kafka version upgrade planning
- [ ] Hardware refresh planning
- [ ] Architecture review
- [ ] Disaster recovery test
- [ ] Security penetration testing

---

## References

### Official Documentation

1. **Apache Kafka Documentation**  
   https://kafka.apache.org/documentation/

2. **KRaft (KIP-500) Documentation**  
   https://kafka.apache.org/documentation/#kraft

3. **Kafka Operations Guide**  
   https://kafka.apache.org/documentation/#operations

4. **Kafka Configuration Reference**  
   https://kafka.apache.org/documentation/#configuration

5. **Kafka Security Guide**  
   https://kafka.apache.org/documentation/#security

### Kafka Improvement Proposals

6. **KIP-500: Replace ZooKeeper with Self-Managed Metadata Quorum**  
   https://cwiki.apache.org/confluence/display/KAFKA/KIP-500

7. **KIP-631: The Quorum-based Kafka Controller**  
   https://cwiki.apache.org/confluence/display/KAFKA/KIP-631

8. **KIP-595: A Raft Protocol for the Metadata Quorum**  
   https://cwiki.apache.org/confluence/display/KAFKA/KIP-595

### Best Practices & Production Guides

9. **Confluent Production Checklist**  
   https://docs.confluent.io/platform/current/installation/deployment.html

10. **LinkedIn: Running Kafka at Scale**  
    https://engineering.linkedin.com/kafka/running-kafka-scale

11. **Uber: Reliable Reprocessing at Uber with Kafka**  
    https://eng.uber.com/reliable-reprocessing/

12. **Netflix: Kafka Inside Keystone Pipeline**  
    https://netflixtechblog.com/kafka-inside-keystone-pipeline-dd5aeabaf6bb

### Monitoring & Observability

13. **Kafka Monitoring with Prometheus**  
    https://github.com/prometheus/jmx_exporter

14. **Confluent Monitoring Stack**  
    https://docs.confluent.io/platform/current/installation/docker/operations/monitoring.html

15. **Kafka Lag Exporter**  
    https://github.com/lightbend/kafka-lag-exporter

### Performance & Tuning

16. **Kafka Performance Optimization Guide**  
    https://www.confluent.io/blog/configure-kafka-to-minimize-latency/

17. **Kafka Benchmarking**  
    https://kafka.apache.org/documentation/#maximizingefficiency

18. **Capacity Planning**  
    https://docs.confluent.io/platform/current/kafka/deployment.html#capacity-planning

### Tools & Utilities

19. **Kafka Manager (CMAK)**  
    https://github.com/yahoo/CMAK

20. **Kafdrop - Kafka Web UI**  
    https://github.com/obsidiandynamics/kafdrop

21. **Conduktor Platform**  
    https://www.conduktor.io/

22. **kcat (formerly kafkacat)**  
    https://github.com/edenhill/kcat

### Disaster Recovery

23. **MirrorMaker 2.0 Documentation**  
    https://kafka.apache.org/documentation/#georeplication

24. **Disaster Recovery Strategies**  
    https://www.confluent.io/blog/disaster-recovery-multi-datacenter-apache-kafka-deployments/

### Security

25. **Kafka Security Documentation**  
    https://kafka.apache.org/documentation/#security

26. **SASL/SCRAM Authentication**  
    https://kafka.apache.org/documentation/#security_sasl_scram

27. **SSL/TLS Configuration**  
    https://kafka.apache.org/documentation/#security_ssl

### Cloud-Specific Guides

28. **AWS MSK Best Practices**  
    https://docs.aws.amazon.com/msk/latest/developerguide/bestpractices.html

29. **Azure Event Hubs (Kafka-compatible)**  
    https://docs.microsoft.com/en-us/azure/event-hubs/

30. **Google Cloud Pub/Sub with Kafka**  
    https://cloud.google.com/pubsub/docs/kafka

### Books & Training

31. **"Kafka: The Definitive Guide" by Neha Narkhede et al.**  
    O'Reilly Media

32. **"Kafka Streams in Action" by William Bejeck**  
    Manning Publications

33. **Confluent Developer Courses**  
    https://developer.confluent.io/courses/

### Community Resources

34. **Apache Kafka Mailing Lists**  
    https://kafka.apache.org/contact

35. **Confluent Community Forum**  
    https://forum.confluent.io/

36. **Kafka Users Slack**  
    https://kafka-users.slack.com/

37. **Stack Overflow - Kafka Tag**  
    https://stackoverflow.com/questions/tagged/apache-kafka

### Release Information

38. **Kafka Release Notes**  
    https://kafka.apache.org/downloads

39. **Upgrade Guide**  
    https://kafka.apache.org/documentation/#upgrade

---

## Contributing

This guide is maintained as an open-source project. Contributions are welcome!

**How to Contribute:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

**Areas for Contribution:**
- Additional troubleshooting scenarios
- Cloud-specific deployment guides
- Performance tuning case studies
- Updated configuration examples
- Monitoring dashboard templates

## License

This guide is released under the MIT License.

## Changelog

**Version 1.0.0** (2025-01-19)
- Initial release
- Focus on Kafka 3.9.0 with KRaft mode
- Comprehensive production deployment guide
- Security, monitoring, and DR procedures

---

**Maintained by:** [Sagar Malla]  
**Last Updated:** 2025-01-19  
**Kafka Version:** 3.9.0  
**Status:** Production Ready
