# Apache Kafka Production Setup Guide for Financial Transactions
## 3-Node KRaft Cluster on EL9/RHEL/Oracle Linux

---

## 1. RECOMMENDED KAFKA VERSION FOR PRODUCTION (Financial Transactions)

### **Recommended Version: Apache Kafka 4.1.1 (Latest Stable)**

**Why Kafka 4.1.1:**
- **Last version supporting both ZooKeeper and KRaft** (bridge release)
- Production-ready KRaft mode (since 3.3.0)
- Extended support: Minimum 2 years from release date
- Stable bug fixes over 3.9.0 (66 issues fixed)
- Full compatibility with financial transaction requirements
- Active community support and security patches

**Important Notes:**
- **Kafka 4.0+** only supports KRaft (ZooKeeper removed entirely)
- **Kafka 3.9.x** is the recommended bridge version before migrating to 4.x
- KRaft has been production-ready since Kafka 3.3.0 (October 2022)

---

## 2. PREREQUISITES & MINIMUM REQUIREMENTS

### **2.1 Operating System Requirements**

```bash
# Supported Operating Systems
- RHEL 9.x / Rocky Linux 9.x / AlmaLinux 9.x / Oracle Linux 9.x
- Fedora (latest stable versions)

# OS Configuration
- Kernel: 4.18+ (RHEL 9 default)
- SELinux: Can be enabled (ensure proper policies)
- File System: XFS or ext4 (XFS recommended)
```

### **2.2 Java Requirements**

| Kafka Version | Java Version Required | Notes |
|---------------|----------------------|-------|
| **3.9.x** | **Java 11 (minimum)** | Clients/Streams: Java 11+ |
| **3.9.x** | **Java 21 LTS (recommended for brokers)** | Brokers/Tools: Java 21 LTS+ |
| **3.9.x** | **Java 21 (supported)** | LTS version, future-proof |

**Recommended Java Installation:**
```bash
# Install OpenJDK 17 (Recommended for brokers)
cd /opt
wget https://download.bell-sw.com/java/21.0.10+10/bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
tar -xzf bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
mv /opt/jdk-21.0.10+10 /opt/jdk-21.0.10
export JAVA_HOME=/opt/jdk-21.0.10
export PATH=$JAVA_HOME/bin:$PATH

# Verify installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/opt/jdk-21.0.10' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### **2.3 Hardware Minimum Requirements**

#### **For Financial Transactions (Minimum Production)**

| Component | Minimum | Recommended | Optimal |
|-----------|---------|-------------|---------|
| **CPU** | 8 cores | 16-24 cores | 24+ cores |
| **RAM** | 32 GB | 64 GB | 128 GB |
| **Heap Memory** | 6 GB | 6-8 GB | 6-10 GB |
| **Disk** | 500 GB SSD | 1-2 TB NVMe | 2+ TB NVMe RAID10 |
| **Network** | 1 Gbps | 10 Gbps | 25 Gbps |

#### **Memory Allocation Strategy**
```
Total RAM: 64 GB
├── JVM Heap: 6 GB (Kafka broker)
├── OS Page Cache: 50+ GB (critical for performance)
├── OS + Other: 6-8 GB
└── Buffer: For active readers/writers
```

**Memory Calculation Formula:**
```
Memory Needed = write_throughput_MB/s × 30 seconds
```

### **2.4 Storage Requirements**

```bash
# Storage Configuration
- Type: NVMe SSD or SAS SSD (No NAS!)
- RAID: RAID 10 (performance + redundancy)
- File System: XFS (recommended) or ext4
- Mount Options: noatime,nodiratime

# Directory Structure
/data/kafka/
├── logs/          # Kafka topic data (minimum 500GB-2TB)
└── metadata/      # KRaft metadata logs (minimum 10GB)
```

### **2.5 Network Requirements**

```
- Minimum: 1 Gbps (development)
- Production: 10 Gbps
- Financial/High-Frequency: 25 Gbps
- Low Latency: <1ms within datacenter
- Same datacenter deployment (avoid multi-DC for latency)
```

---

## 3. SYSTEM CONFIGURATION & TUNING

### **3.1 OS-Level Limits (Soft/Hard Limits)**

Create `/etc/security/limits.d/kafka.conf`:

```bash
# Kafka user limits
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
kafka soft memlock unlimited
kafka hard memlock unlimited

# Root user limits (if running as root - NOT RECOMMENDED)
root soft nofile 100000
root hard nofile 100000
```

**Apply immediately without reboot:**
```bash
sudo prlimit --pid $KAFKA_PID --nofile=100000:100000
```

### **3.2 Kernel Parameters (/etc/sysctl.conf)**

```bash
# Network Tuning
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.tcp_slow_start_after_idle = 0

# Connection Tuning
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65000
net.core.somaxconn = 4096

# Virtual Memory
vm.swappiness = 1
vm.dirty_ratio = 80
vm.dirty_background_ratio = 5
vm.max_map_count = 262144

# File System
fs.file-max = 2097152
```

**Apply changes:**
```bash
sudo sysctl -p
```

### **3.3 Disable Swap (Critical for Performance)**

```bash
# Disable swap immediately
sudo swapoff -a

# Permanently disable (comment out in /etc/fstab)
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

### **3.4 Disk Mount Options**

```bash
# /etc/fstab entry for Kafka data partition
UUID=<your-uuid> /data/kafka xfs noatime,nodiratime,nobarrier 0 2

# Remount
sudo mount -o remount /data/kafka
```

### **3.5 Firewall Configuration**

```bash
# Open required ports
sudo firewall-cmd --permanent --add-port=9092/tcp  # Kafka broker
sudo firewall-cmd --permanent --add-port=9093/tcp  # Kafka broker (SSL)
sudo firewall-cmd --permanent --add-port=9094/tcp  # KRaft controller
sudo firewall-cmd --reload
```

---

## 4. KAFKA INSTALLATION (3-Node Cluster)

### **Hostname setup**
```bash
cat <<EOF | tee -a /etc/hosts
192.168.1.101 kafka1
192.168.1.102 kafka2
192.168.1.103 kafka3
EOF
```

### **4.1 Download and Extract Kafka**

```bash
# Create Kafka user
sudo useradd -r -s /bin/bash kafka

# Download Kafka 4.1.1
cd /opt
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz

# Verify checksum
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz.sha512
sha512sum -c kafka_2.13-4.1.1.tgz.sha512

# Extract
sudo tar -xzf kafka_2.13-4.1.1.tgz
sudo mv kafka_2.13-4.1.1 /opt/kafka
sudo chown -R kafka:kafka /opt/kafka

# Create data directories
sudo mkdir -p /data/kafka/logs /data/kafka/metadata
sudo chown -R kafka:kafka /data/kafka
```

### **4.2 Cluster Information**

```
NODE 1 (kafka1): 192.168.1.101 - Controller ID: 1, Broker ID: 1
NODE 2 (kafka2): 192.168.1.102 - Controller ID: 2, Broker ID: 2
NODE 3 (kafka3): 192.168.1.103 - Controller ID: 3, Broker ID: 3
```

### **4.3 Generate Cluster UUID (Run Once on Any Node)**

```bash
/opt/kafka/bin/kafka-storage.sh random-uuid
# Output example: 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g

# Save this UUID - you'll need it for all nodes
export CLUSTER_UUID="7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g"
```

### **4.4 KRaft Configuration (server.properties)**

**NODE 1 (kafka1) - /opt/kafka/config/server.properties:**

```properties
# KRaft Mode Configuration
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094

# Listeners
listeners=PLAINTEXT://kafka1:9092,CONTROLLER://kafka1:9094
advertised.listeners=PLAINTEXT://kafka1:9092
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER

# Log Directories
log.dirs=/data/kafka/logs
metadata.log.dir=/data/kafka/metadata

# Cluster Configuration
cluster.id=<REPLACE_WITH_YOUR_CLUSTER_UUID>

# Replication & Fault Tolerance
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

# Consumer Offsets (CRITICAL for your requirement)
offsets.topic.num.partitions=50
offsets.topic.replication.factor=3
offsets.retention.minutes=10080

# Topic Defaults
num.partitions=3
auto.create.topics.enable=false

# Performance Tuning
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log Retention & Cleanup
log.retention.hours=168
log.retention.check.interval.ms=300000
log.segment.bytes=1073741824
log.cleanup.policy=delete

# Compression
compression.type=lz4

# JMX Monitoring
#kafka.jmx.enable=true
#kafka.jmx.port=9999
```

**NODE 2 (kafka2) - /opt/kafka/config/server.properties:**
```properties
# Change only these values from NODE 1 config:
node.id=2
listeners=PLAINTEXT://kafka2:9092,CONTROLLER://kafka2:9094
advertised.listeners=PLAINTEXT://kafka2:9092

# Keep all other settings identical to NODE 1
```

**NODE 3 (kafka3) - /opt/kafka/config/server.properties:**
```properties
# Change only these values from NODE 1 config:
node.id=3
listeners=PLAINTEXT://kafka3:9092,CONTROLLER://kafka3:9094
advertised.listeners=PLAINTEXT://kafka3:9092

# Keep all other settings identical to NODE 1
```

### **4.5 JVM Configuration**

Create `/opt/kafka/bin/kafka-server-start-jvm.sh`:

```bash
#!/bin/bash
export KAFKA_HEAP_OPTS="-Xms6g -Xmx6g"
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M -XX:MinMetaspaceFreeRatio=50 -XX:MaxMetaspaceFreeRatio=80 -XX:+ExplicitGCInvokesConcurrent"

# GC Logging
export KAFKA_GC_LOG_OPTS="-Xlog:gc*:file=/var/log/kafka/gc.log:time,tags:filecount=10,filesize=100M"

# JMX Monitoring
export JMX_PORT=9999

/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
```

### **4.6 Format Storage (Run on ALL nodes BEFORE first start)**

```bash
# On NODE 1
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t $CLUSTER_UUID \
  -c /opt/kafka/config/server.properties

# On NODE 2
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t $CLUSTER_UUID \
  -c /opt/kafka/config/server.properties

# On NODE 3
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t $CLUSTER_UUID \
  -c /opt/kafka/config/server.properties
```

### **4.7 Systemd Service Configuration**

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
Environment="JAVA_HOME=/opt/jdk-21.0.10"
Environment="KAFKA_HEAP_OPTS=-Xms6g -Xmx6g"
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M -XX:MinMetaspaceFreeRatio=50 -XX:MaxMetaspaceFreeRatio=80"
Environment="LOG_DIR=/var/log/kafka"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10
LimitNOFILE=100000
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
```

**Enable and start services (on ALL nodes):**

```bash
# Create log directory
sudo mkdir -p /var/log/kafka
sudo chown kafka:kafka /var/log/kafka

# Reload systemd
sudo systemctl daemon-reload

# Enable Kafka service
sudo systemctl enable kafka

# Start Kafka (one node at a time, wait 30 seconds between nodes)
sudo systemctl start kafka

# Check status
sudo systemctl status kafka
```

### **4.8 Verify Cluster Status**

```bash
# Check cluster metadata
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status

# List brokers
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092

# Check controller
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --replication
```

---

## 5. CONSUMER OFFSET CONFIGURATION

**The `__consumer_offsets` topic is automatically created with replication factor = 3** when you set:

```properties
offsets.topic.replication.factor=3
```

**Verify offset topic configuration:**

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic __consumer_offsets
```

**Expected Output:**
```
Topic: __consumer_offsets       PartitionCount: 50      ReplicationFactor: 3
```

---

## 6. HIGH AVAILABILITY STRATEGIES

### **6.1 Replication Strategy**

```properties
# In server.properties (already configured above)
default.replication.factor=3
min.insync.replicas=2
```

**How it works:**
- Data replicated across all 3 brokers
- Writes require acknowledgment from 2 replicas (including leader)
- Can tolerate 1 broker failure without data loss
- Can tolerate 1 controller failure (2 controllers remain for quorum)

### **6.2 Controller Quorum**

```
3 Controllers = Can tolerate 1 failure
Quorum requires: (N/2) + 1 = 2 controllers minimum
```

### **6.3 Producer Configuration for HA**

```properties
# Producer settings for financial transactions
acks=all                     # Wait for all in-sync replicas
retries=2147483647           # Max retries
max.in.flight.requests.per.connection=1  # Ordering guarantee
enable.idempotence=true      # Exactly-once semantics
compression.type=lz4         # Fast compression
```

### **6.4 Consumer Configuration for HA**

```properties
# Consumer settings
enable.auto.commit=false     # Manual commit control
isolation.level=read_committed  # Only read committed records
session.timeout.ms=30000
heartbeat.interval.ms=3000
max.poll.interval.ms=300000
```

### **6.5 Network Failure Handling**

**KRaft automatically handles:**
- Leader election (typically <5 seconds)
- Controller failover (automatic)
- Network partitions (via quorum voting)

**Monitoring network health:**
```bash
# Check under-replicated partitions
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --under-replicated-partitions

# Check offline partitions
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --unavailable-partitions
```

---

## 7. DISASTER RECOVERY & MINIMAL DOWNTIME

### **7.1 Node Failure Recovery**

**Scenario: Single broker/controller failure**

```bash
# Cluster continues operating (2 nodes minimum for quorum)
# No action required immediately

# To replace failed node:
1. Fix/replace hardware
2. Reinstall OS and Kafka
3. Use SAME node.id and cluster.id
4. Format storage with SAME cluster UUID
5. Start service
6. Wait for automatic replication
```

**Recovery Time: ~2-5 minutes** (automatic)

### **7.2 Graceful Shutdown**

```bash
# Controlled shutdown (recommended during maintenance)
/opt/kafka/bin/kafka-server-stop.sh

# Wait for leadership transfer (~30 seconds)
# Then perform maintenance
```

### **7.3 Fast Restart**

```bash
# Start broker
sudo systemctl start kafka

# Verify broker rejoined
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092
```

**Recovery Time: ~1-2 minutes** (depending on catch-up)

### **7.4 Data Backup Strategy**

```bash
# Option 1: MirrorMaker 2 (recommended - see section 8)

# Option 2: File-level backup (during maintenance window)
sudo rsync -av /data/kafka/logs/ /backup/kafka/logs/
sudo rsync -av /data/kafka/metadata/ /backup/kafka/metadata/

# Option 3: Snapshot-based backup (if using cloud/SAN)
# AWS: EBS snapshots
# VMware: VM snapshots (with Kafka stopped!)
```

---

## 8. MIRROR CLUSTER (BACKUP/DR CLUSTER)

### **8.1 MirrorMaker 2 Setup**

MirrorMaker 2 provides real-time replication to a secondary cluster.

**Architecture:**
```
Primary Cluster (kafka1-3) → MirrorMaker 2 → DR Cluster (kafka-dr1-3)
```

**Install MirrorMaker 2:**

Create `/opt/kafka/config/mm2.properties`:

```properties
# Cluster aliases
clusters = primary, dr
primary.bootstrap.servers = kafka1:9092,kafka2:9092,kafka3:9092
dr.bootstrap.servers = kafka-dr1:9092,kafka-dr2:9092,kafka-dr3:9092

# Enable replication from primary to DR
primary->dr.enabled = true

# Topics to replicate (use regex)
primary->dr.topics = .*

# Replication settings
replication.factor = 3
sync.topic.configs.enabled = true
refresh.topics.enabled = true
refresh.topics.interval.seconds = 60
refresh.groups.enabled = true
refresh.groups.interval.seconds = 60

# Checkpoints
checkpoints.topic.replication.factor = 3
heartbeats.topic.replication.factor = 3
offset-syncs.topic.replication.factor = 3

# Performance
tasks.max = 4
```

**Start MirrorMaker 2:**

```bash
/opt/kafka/bin/connect-mirror-maker.sh /opt/kafka/config/mm2.properties
```

**Create systemd service:**

```ini
[Unit]
Description=Kafka MirrorMaker 2
After=kafka.service

[Service]
Type=simple
User=kafka
ExecStart=/opt/kafka/bin/connect-mirror-maker.sh /opt/kafka/config/mm2.properties
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### **8.2 DR Cluster Setup**

**DR Cluster (separate hardware/datacenter):**
- Same configuration as primary cluster
- Different cluster.id
- Different hostnames: kafka-dr1, kafka-dr2, kafka-dr3

**Failover Procedure:**
1. Stop primary cluster (if disaster)
2. Promote DR cluster consumers to active
3. Update application configs to point to DR cluster
4. Monitor lag and convergence

**Recovery Time Objective (RTO): ~5-15 minutes**  
**Recovery Point Objective (RPO): Near-zero (async replication lag: <1 second)**

---

## 9. MONITORING & ALERTING

### **9.1 Critical Metrics to Monitor**

```bash
# JMX Metrics (port 9999)
kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec
kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec
kafka.controller:type=KafkaController,name=ActiveControllerCount
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions
kafka.server:type=ReplicaManager,name=PartitionCount
kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent
```

### **9.2 Health Check Script**

Create `/opt/kafka/bin/health-check.sh`:

```bash
#!/bin/bash
BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"

# Check broker count
BROKERS=$(/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server $BOOTSTRAP 2>/dev/null | grep -c "^kafka")

if [ "$BROKERS" -lt 3 ]; then
  echo "CRITICAL: Only $BROKERS brokers available"
  exit 2
fi

# Check under-replicated partitions
URP=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --under-replicated-partitions 2>/dev/null | grep -c "Topic:")

if [ "$URP" -gt 0 ]; then
  echo "WARNING: $URP under-replicated partitions"
  exit 1
fi

echo "OK: Cluster healthy - $BROKERS brokers, 0 under-replicated partitions"
exit 0
```

### **9.3 Log Monitoring**

```bash
# Monitor logs
tail -f /var/log/kafka/server.log

# Check for errors
grep -i error /var/log/kafka/server.log
grep -i exception /var/log/kafka/server.log
```

---

## 10. SECURITY BEST PRACTICES

### **10.1 Enable SSL/TLS (Recommended for Financial)**

```properties
# server.properties
listeners=PLAINTEXT://kafka1:9092,SSL://kafka1:9093,CONTROLLER://kafka1:9094
advertised.listeners=PLAINTEXT://kafka1:9092,SSL://kafka1:9093

# SSL Configuration
ssl.keystore.location=/opt/kafka/ssl/kafka.server.keystore.jks
ssl.keystore.password=<password>
ssl.key.password=<password>
ssl.truststore.location=/opt/kafka/ssl/kafka.server.truststore.jks
ssl.truststore.password=<password>
ssl.client.auth=required
```

### **10.2 Enable SASL Authentication**

```properties
# server.properties
sasl.enabled.mechanisms=SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
```

### **10.3 Enable ACLs**

```bash
# Create admin user
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=admin-secret]' \
  --entity-type users --entity-name admin
```

---

## 11. PERFORMANCE OPTIMIZATION

### **11.1 Partition Strategy**

```bash
# Calculate optimal partition count
Partitions = max(t/p, t/c)
where:
  t = target throughput (MB/s)
  p = producer throughput per partition (MB/s)
  c = consumer throughput per partition (MB/s)

# Financial transactions: Start with 30-50 partitions per topic
```

### **11.2 Batch Configuration**

```properties
# Producer batching
batch.size=32768
linger.ms=10
compression.type=lz4
```

### **11.3 OS Page Cache Optimization**

```bash
# Ensure majority of RAM is available for page cache
# Formula: Total RAM - Heap - OS Reserve = Page Cache
# Example: 64GB - 6GB - 4GB = 54GB page cache
```

---

## 12. MAINTENANCE PROCEDURES

### **12.1 Rolling Restart**

```bash
# Stop broker 1
sudo systemctl stop kafka  # on kafka1

# Wait for ISR to stabilize (30 seconds)
sleep 30

# Start broker 1
sudo systemctl start kafka  # on kafka1

# Repeat for broker 2 and broker 3
```

### **12.2 Partition Reassignment**

```bash
# Generate reassignment plan
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --topics-to-move-json-file topics.json \
  --broker-list "1,2,3" \
  --generate

# Execute reassignment
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# Verify completion
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

---

## 13. TROUBLESHOOTING GUIDE

### **13.1 Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| Broker won't start | Port conflict | Check `netstat -tulpn \| grep 9092` |
| Under-replicated partitions | Network/disk issues | Check network, disk I/O |
| Consumer lag | Slow processing | Scale consumers, optimize code |
| Out of memory | Heap too small | Increase heap or optimize GC |
| High CPU | Compression overhead | Reduce compression or use lz4 |

### **13.2 Performance Debugging**

```bash
# Test producer performance
/opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic test-topic \
  --num-records 1000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props bootstrap.servers=kafka1:9092

# Test consumer performance
/opt/kafka/bin/kafka-consumer-perf-test.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic \
  --messages 1000000
```

---

## 14. SUMMARY CHECKLIST

### **Pre-Production Checklist:**

- [ ] OS tuning completed (limits, sysctl, swap disabled)
- [ ] Firewall rules configured
- [ ] Java 21 LTS installed and configured
- [ ] Kafka 4.1.1 installed on all 3 nodes
- [ ] Cluster formatted with same UUID
- [ ] `offsets.topic.replication.factor=3` configured
- [ ] Systemd services enabled and started
- [ ] Cluster health verified
- [ ] MirrorMaker 2 configured for DR
- [ ] Monitoring configured (JMX, logs)
- [ ] Security configured (SSL/SASL)
- [ ] Backup strategy implemented
- [ ] Documentation created
- [ ] Team trained on operations

---

## 15. REFERENCE METRICS TABLE

### **Java Support Matrix**

| Kafka Version | Java 11 | Java 21 LTS | Java 21 |
|---------------|---------|---------|---------|
| 3.9.x |  (Clients) |  (All) |  (All) |
| 4.0.x |  (Clients) |  (All) |  (All) |

### **Expected Performance Metrics**

| Metric | Expected Value | Alert Threshold |
|--------|---------------|-----------------|
| Producer throughput | 50-100 MB/s per broker | <10 MB/s |
| Consumer throughput | 50-100 MB/s per broker | <10 MB/s |
| End-to-end latency (p99) | <100ms | >500ms |
| Replication lag | <1 second | >10 seconds |
| Under-replicated partitions | 0 | >0 |
| Offline partitions | 0 | >0 |

---

## ADDITIONAL RESOURCES

- Official Documentation: https://kafka.apache.org/documentation/
- KRaft Documentation: https://kafka.apache.org/documentation/#kraft
- Confluent Best Practices: https://docs.confluent.io/platform/current/kafka/deployment.html
- Performance Tuning: https://kafka.apache.org/documentation/#hwandos

---

**Document Version:** 1.0  
**Last Updated:** January 31, 2026  
**Kafka Version:** 4.1.1  
**Operating System:** RHEL 9.x / Oracle Linux 9.x / Rocky Linux 9.x
