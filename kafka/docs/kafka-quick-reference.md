# Kafka 4.1.1 Production Setup - Quick Reference Card

## RECOMMENDED CONFIGURATION

### Version Information
- **Kafka Version:** 4.1.1 (Latest Stable)
- **Java Version:** Java 21 LTS (Recommended for brokers)
- **Scala Version:** 2.13
- **Mode:** KRaft (No ZooKeeper)

### Why Kafka 4.1.1?
 Last version supporting both ZooKeeper and KRaft (bridge release)  
 Production-ready KRaft since 3.3.0  
 Extended support: Minimum 2 years  
 66 bug fixes over 3.9.0  
 Perfect for financial transactions  

---

## HARDWARE REQUIREMENTS

### Minimum Production Setup (3 Nodes)

| Component | Minimum | Recommended | Optimal |
|-----------|---------|-------------|---------|
| **CPU** | 8 cores | 16-24 cores | 24+ cores |
| **RAM** | 32 GB | 64 GB | 128 GB |
| **Heap** | 6 GB | 6-8 GB | 6-10 GB |
| **Storage** | 500 GB SSD | 1-2 TB NVMe | 2+ TB RAID10 |
| **Network** | 1 Gbps | 10 Gbps | 25 Gbps |

**Memory Formula:** `write_throughput_MB/s × 30 seconds`

---

## CRITICAL SYSTEM SETTINGS

### File Limits (/etc/security/limits.d/kafka.conf)
```bash
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
```

### Kernel Parameters (/etc/sysctl.conf)
```bash
vm.swappiness = 1
vm.max_map_count = 262144
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
fs.file-max = 2097152
```

### Disable Swap (CRITICAL!)
```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

---

## CLUSTER CONFIGURATION

### Node Information
```
Node 1: kafka1 (192.168.1.101) - Controller ID: 1, Broker ID: 1
Node 2: kafka2 (192.168.1.102) - Controller ID: 2, Broker ID: 2
Node 3: kafka3 (192.168.1.103) - Controller ID: 3, Broker ID: 3
```

### Critical server.properties Settings
```properties
# KRaft Mode
process.roles=broker,controller
node.id=1  # Unique per node
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094

# Replication (CRITICAL for Financial Transactions)
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3  # __consumer_offsets = 3

# Performance
num.network.threads=8
num.io.threads=16
compression.type=lz4
```

### JVM Configuration
```bash
KAFKA_HEAP_OPTS="-Xms6g -Xmx6g"
KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20"
```

---

## INSTALLATION QUICK START

### 1. Generate Cluster UUID (Once)
```bash
/opt/kafka/bin/kafka-storage.sh random-uuid
# Save this UUID for all nodes!
```

### 2. Format Storage (All Nodes)
```bash
/opt/kafka/bin/kafka-storage.sh format \
  -t <CLUSTER_UUID> \
  -c /opt/kafka/config/server.properties
```

### 3. Start Service (All Nodes)
```bash
sudo systemctl enable kafka
sudo systemctl start kafka
```

### 4. Verify Cluster
```bash
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status
```

---

## HIGH AVAILABILITY

### Fault Tolerance
- **3 Controllers** = Can tolerate 1 controller failure
- **Replication Factor 3** = Can tolerate 1 broker failure
- **min.insync.replicas=2** = Writes require 2 confirmations

### Recovery Times
| Scenario | Recovery Time |
|----------|---------------|
| Single node failure | Automatic (~2-5 min) |
| Network partition | Automatic (~30 sec) |
| Graceful restart | 1-2 minutes |
| Data corruption | 5-10 minutes |

---

## CONSUMER OFFSET CONFIGURATION

**__consumer_offsets topic automatically created with:**
```properties
offsets.topic.replication.factor=3
offsets.topic.num.partitions=50
offsets.retention.minutes=10080  # 7 days
```

**Verify:**
```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --topic __consumer_offsets
```

---

## DISASTER RECOVERY

### MirrorMaker 2 (Active-Passive DR)
```
Primary Cluster → MirrorMaker 2 → DR Cluster
RTO: 5-15 minutes
RPO: Near-zero (<1 second lag)
```

### Failover Procedure
1. Stop primary cluster (if disaster)
2. Promote DR cluster
3. Update application configs
4. Monitor convergence

---

## DAILY HEALTH CHECKS

```bash
# 1. Check brokers (Should be 3)
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092 | grep -c "kafka"

# 2. Under-replicated partitions (Should be 0)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions

# 3. Offline partitions (Should be 0)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --unavailable-partitions

# 4. Consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe --all-groups
```

---

## CRITICAL METRICS TO MONITOR

| Metric | Warning | Critical |
|--------|---------|----------|
| Under-replicated partitions | >0 | >10 |
| Offline partitions | >0 | >0 |
| Consumer lag | >10000 | >100000 |
| Disk usage | >80% | >90% |
| CPU usage | >80% | >95% |
| GC pause | >1s | >5s |

---

## PRODUCER CONFIGURATION (Financial Transactions)

```properties
acks=all                          # Wait for all replicas
retries=2147483647                # Infinite retries
enable.idempotence=true           # Exactly-once
compression.type=lz4              # Fast compression
max.in.flight.requests.per.connection=1  # Ordering
```

---

## CONSUMER CONFIGURATION (Financial Transactions)

```properties
enable.auto.commit=false          # Manual commit
isolation.level=read_committed    # Only committed records
session.timeout.ms=30000
heartbeat.interval.ms=3000
max.poll.interval.ms=300000
```

---

## TOPIC CREATION (Financial Transactions Example)

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic financial-transactions \
  --partitions 30 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config retention.ms=604800000 \
  --config compression.type=lz4
```

---

## ROLLING RESTART PROCEDURE

```bash
# Node 1
sudo systemctl stop kafka    # on kafka1
sleep 60                     # Wait for ISR
sudo systemctl start kafka   # on kafka1
sleep 30                     # Wait for rejoin

# Verify health
/opt/kafka/bin/health-check.sh

# Repeat for Node 2 and Node 3
```

---

## SECURITY (Financial Compliance)

### Enable SSL/TLS
```properties
listeners=SSL://kafka1:9093,CONTROLLER://kafka1:9094
ssl.keystore.location=/opt/kafka/ssl/kafka.server.keystore.jks
ssl.truststore.location=/opt/kafka/ssl/kafka.server.truststore.jks
ssl.client.auth=required
```

### Enable SASL
```properties
sasl.enabled.mechanisms=SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
```

---

## PERFORMANCE OPTIMIZATION

### Partition Calculation
```
Partitions = max(throughput/producer_throughput, throughput/consumer_throughput)
Financial transactions: Start with 30-50 partitions
```

### Compression
- **lz4**: Best for general use (recommended)
- **snappy**: Good balance
- **gzip**: High compression, high CPU
- **zstd**: Best compression (Kafka 2.1+)

---

## TROUBLESHOOTING QUICK REFERENCE

| Issue | Check | Fix |
|-------|-------|-----|
| Broker won't start | Logs, ports, disk | Check /var/log/kafka/server.log |
| Under-replicated | Broker status | Restart broker, reassign |
| High CPU | Compression, GC | Switch to lz4, tune GC |
| Disk full | Retention, cleanup | Reduce retention |
| Consumer lag | Processing speed | Scale consumers |

---

## USEFUL COMMANDS

```bash
# Cluster status
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# List topics
kafka-topics.sh --bootstrap-server kafka1:9092 --list

# Consumer groups
kafka-consumer-groups.sh --bootstrap-server kafka1:9092 --list

# Performance test
kafka-producer-perf-test.sh --topic test --num-records 1000000 \
  --record-size 1024 --throughput -1 \
  --producer-props bootstrap.servers=kafka1:9092

# Service management
systemctl start|stop|restart|status kafka
journalctl -u kafka -f
```

---

## FIREWALL PORTS

```bash
9092  # Kafka broker (PLAINTEXT)
9093  # Kafka broker (SSL)
9094  # KRaft controller
9999  # JMX monitoring
```

---

## FILES LOCATION

```
Configuration: /opt/kafka/config/server.properties
Data: /data/kafka/logs/
Metadata: /data/kafka/metadata/
Logs: /var/log/kafka/
Service: /etc/systemd/system/kafka.service
```

---

## SUPPORT & DOCUMENTATION

- Official Docs: https://kafka.apache.org/documentation/
- KRaft Guide: https://kafka.apache.org/documentation/#kraft
- Confluent Docs: https://docs.confluent.io/
- Performance: https://kafka.apache.org/documentation/#hwandos

---

## NEXT STEPS AFTER INSTALLATION

1.  Verify all 3 brokers are running
2.  Create test topic with replication factor 3
3.  Test producer/consumer
4.  Set up monitoring (JMX, Prometheus, Grafana)
5.  Configure MirrorMaker 2 for DR
6.  Enable security (SSL/SASL)
7.  Set up automated backups
8.  Document runbooks
9.  Train operations team
10.  Schedule regular health checks

---

**Quick Reference Version:** 1.0  
**Last Updated:** January 31, 2026  
**Kafka Version:** 4.1.1 (Production-Ready KRaft)
