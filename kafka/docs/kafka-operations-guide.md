# Kafka Production Operations & Troubleshooting Guide
## Quick Reference for Daily Operations

---

## 1. CLUSTER HEALTH MONITORING

### Daily Health Checks

```bash
# 1. Check cluster status
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status

# 2. List all brokers
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092

# 3. Check under-replicated partitions (Should be 0)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions

# 4. Check offline partitions (Should be 0)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --unavailable-partitions

# 5. Check consumer group lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe --all-groups
```

### Automated Monitoring Script

```bash
#!/bin/bash
# /opt/kafka/bin/daily-health-check.sh

BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== Kafka Health Check - $DATE ===" | tee -a /var/log/kafka/health.log

# Broker count
BROKERS=$(/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server $BOOTSTRAP 2>/dev/null | grep -c "^kafka")
echo "Active Brokers: $BROKERS/3" | tee -a /var/log/kafka/health.log

# Under-replicated partitions
URP=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --under-replicated-partitions 2>/dev/null | grep -c "Topic:")
echo "Under-Replicated Partitions: $URP" | tee -a /var/log/kafka/health.log

# Offline partitions
OFFLINE=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --unavailable-partitions 2>/dev/null | grep -c "Topic:")
echo "Offline Partitions: $OFFLINE" | tee -a /var/log/kafka/health.log

# Alert if issues
if [ "$BROKERS" -lt 3 ] || [ "$URP" -gt 0 ] || [ "$OFFLINE" -gt 0 ]; then
  echo "ALERT: Cluster health issues detected!" | tee -a /var/log/kafka/health.log
  # Send alert (email, Slack, PagerDuty, etc.)
  exit 1
else
  echo "Status: HEALTHY" | tee -a /var/log/kafka/health.log
  exit 0
fi
```

---

## 2. COMMON OPERATIONS

### Topic Management

```bash
# Create topic (financial transactions example)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic financial-transactions \
  --partitions 30 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config retention.ms=604800000 \
  --config compression.type=lz4

# List all topics
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --list

# Describe topic
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic financial-transactions

# Increase partitions (cannot decrease)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --alter \
  --topic financial-transactions \
  --partitions 50

# Update topic configuration
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type topics \
  --entity-name financial-transactions \
  --alter \
  --add-config retention.ms=1209600000

# Delete topic (if enabled)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --topic test-topic
```

### Consumer Group Management

```bash
# List consumer groups
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --list

# Describe consumer group
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --group payment-processor-group

# Reset consumer group offsets (CAUTION!)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions \
  --reset-offsets \
  --to-earliest \
  --execute

# Reset to specific offset
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions:0 \
  --reset-offsets \
  --to-offset 1000 \
  --execute

# Delete consumer group (must be inactive)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --group test-group
```

### Testing and Performance

```bash
# Producer performance test
/opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic test-topic \
  --num-records 1000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props \
    bootstrap.servers=kafka1:9092 \
    acks=all \
    compression.type=lz4

# Consumer performance test
/opt/kafka/bin/kafka-consumer-perf-test.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic \
  --messages 1000000 \
  --threads 1

# End-to-end latency test
/opt/kafka/bin/kafka-run-class.sh kafka.tools.EndToEndLatency \
  kafka1:9092 \
  test-topic \
  10000 \
  all \
  1024
```

---

## 3. TROUBLESHOOTING SCENARIOS

### Scenario 1: Broker Not Starting

**Symptoms:**
- `systemctl status kafka` shows failed
- Errors in `/var/log/kafka/server.log`

**Diagnosis Steps:**
```bash
# 1. Check logs
tail -100 /var/log/kafka/server.log

# 2. Check ports
netstat -tulpn | grep 9092

# 3. Check disk space
df -h /data/kafka

# 4. Check file permissions
ls -la /data/kafka/

# 5. Check Java process
ps aux | grep kafka
```

**Common Causes & Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| Port already in use | Another process using 9092 | `kill -9 <pid>` or change port |
| Disk full | No space left | Clean old logs or add disk |
| Permission denied | Wrong ownership | `chown -R kafka:kafka /data/kafka` |
| Invalid cluster.id | Mismatched UUID | Reformat with correct UUID |
| JVM out of memory | Heap too small | Increase `KAFKA_HEAP_OPTS` |

### Scenario 2: Under-Replicated Partitions

**Symptoms:**
- Under-replicated partitions > 0
- Alerts firing
- Performance degradation

**Diagnosis:**
```bash
# Identify affected topics
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions

# Check broker status
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092

# Check controller logs
tail -100 /var/log/kafka/controller.log
```

**Common Causes:**
1. **Broker failure** - Wait for broker to rejoin
2. **Network issues** - Check connectivity between brokers
3. **Disk I/O saturation** - Check `iostat -x 1`
4. **High CPU** - Check `top` or `htop`

**Solutions:**
```bash
# 1. Restart affected broker
systemctl restart kafka

# 2. Trigger preferred replica election
/opt/kafka/bin/kafka-leader-election.sh \
  --bootstrap-server kafka1:9092 \
  --election-type PREFERRED \
  --all-topic-partitions

# 3. Manual reassignment (if needed)
# Create reassignment plan
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --topics-to-move-json-file topics.json \
  --broker-list "1,2,3" \
  --generate > reassignment.json

# Execute
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --execute
```

### Scenario 3: Consumer Lag

**Symptoms:**
- Increasing consumer lag
- Delayed processing
- Alerts from monitoring

**Diagnosis:**
```bash
# Check consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --group payment-processor-group

# Monitor in real-time
watch -n 2 '/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --group payment-processor-group'
```

**Common Causes & Solutions:**

| Cause | Indicator | Solution |
|-------|-----------|----------|
| Slow processing | CPU high on consumer | Optimize code or add consumers |
| Network issues | High network latency | Check network, move consumers closer |
| Rebalancing | Frequent rebalances | Increase `session.timeout.ms` |
| Small fetch size | Low throughput | Increase `fetch.min.bytes` |
| Under-provisioned | Lag always increasing | Add consumer instances |

**Quick Fixes:**
```bash
# Scale consumers
# Add more instances of consumer application

# Increase consumer parallelism
# Ensure: num_consumers <= num_partitions

# Optimize consumer configuration
# In consumer properties:
fetch.min.bytes=1048576
fetch.max.wait.ms=500
max.poll.records=500
```

### Scenario 4: Disk Space Issues

**Symptoms:**
- Disk usage >85%
- Broker becoming unstable
- Write errors

**Diagnosis:**
```bash
# Check disk usage
df -h /data/kafka

# Check segment sizes
du -sh /data/kafka/logs/*

# Check oldest segments
find /data/kafka/logs -name "*.log" -exec ls -lh {} \; | head -20
```

**Solutions:**
```bash
# 1. Reduce retention
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type topics \
  --entity-name large-topic \
  --alter \
  --add-config retention.ms=86400000  # 1 day

# 2. Enable log compaction (if applicable)
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type topics \
  --entity-name compacted-topic \
  --alter \
  --add-config cleanup.policy=compact

# 3. Manual cleanup (CAUTION!)
# Stop broker first!
systemctl stop kafka
rm -rf /data/kafka/logs/__consumer_offsets-*/00000000000000000000.log
systemctl start kafka

# 4. Add more disk space
# Mount new disk and migrate partitions
```

### Scenario 5: High CPU Usage

**Symptoms:**
- CPU usage >80%
- Slow response times
- Increased latency

**Diagnosis:**
```bash
# Check CPU usage
top -p $(pgrep -f kafka.Kafka)

# Check thread usage
jstack <kafka_pid> | grep "java.lang.Thread.State" | sort | uniq -c

# Check GC activity
jstat -gc <kafka_pid> 1000
```

**Common Causes:**
1. **Compression overhead** - Using gzip instead of lz4
2. **SSL/TLS encryption** - Encryption overhead
3. **Too many partitions** - Excessive metadata
4. **GC pauses** - Heap too small or poorly tuned

**Solutions:**
```bash
# 1. Switch to LZ4 compression
# In topic config:
compression.type=lz4

# 2. Tune JVM GC
# In /etc/systemd/system/kafka.service:
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20"

# 3. Reduce partition count (new topics)
# 4. Scale horizontally (add brokers)
```

### Scenario 6: Network Partition

**Symptoms:**
- Controller election in progress
- Brokers unreachable
- Client connection errors

**Diagnosis:**
```bash
# Check connectivity
for i in 1 2 3; do
  ping -c 3 kafka$i
  telnet kafka$i 9092
done

# Check controller status
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status

# Check logs for election
grep -i "election" /var/log/kafka/controller.log
```

**Solution:**
```bash
# 1. Fix network issue
# 2. Wait for automatic recovery (typically <30 seconds)
# 3. Verify cluster converged
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --replication
```

---

## 4. MAINTENANCE PROCEDURES

### Rolling Restart (Zero Downtime)

```bash
# Rolling restart procedure
# Execute on each node in sequence

# Node 1
ssh kafka1 'sudo systemctl stop kafka'
sleep 60  # Wait for ISR to stabilize
ssh kafka1 'sudo systemctl start kafka'
sleep 30  # Wait for broker to rejoin

# Verify health before proceeding
/opt/kafka/bin/health-check.sh

# Node 2
ssh kafka2 'sudo systemctl stop kafka'
sleep 60
ssh kafka2 'sudo systemctl start kafka'
sleep 30

# Verify health
/opt/kafka/bin/health-check.sh

# Node 3
ssh kafka3 'sudo systemctl stop kafka'
sleep 60
ssh kafka3 'sudo systemctl start kafka'
sleep 30

# Final verification
/opt/kafka/bin/cluster-status.sh
```

### Configuration Changes

```bash
# Dynamic broker configuration (no restart needed)
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type brokers \
  --entity-name 1 \
  --alter \
  --add-config log.retention.hours=168

# Cluster-wide configuration
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type brokers \
  --entity-default \
  --alter \
  --add-config log.retention.hours=168
```

### Adding a New Broker (Scale Out)

```bash
# 1. Install Kafka on new node (kafka4)
# 2. Configure with new node.id=4
# 3. Start broker
systemctl start kafka

# 4. Verify broker joined
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092

# 5. Create reassignment plan to include new broker
cat > topics-to-move.json <<EOF
{
  "topics": [
    {"topic": "financial-transactions"}
  ],
  "version": 1
}
EOF

/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "1,2,3,4" \
  --generate

# 6. Execute reassignment
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --execute --throttle 50000000  # 50MB/s

# 7. Monitor progress
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

### Decommissioning a Broker

```bash
# 1. Move partitions off the broker
# Create reassignment plan excluding broker 4
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "1,2,3" \
  --generate

# 2. Execute reassignment
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# 3. Verify completion
/opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server kafka1:9092 \
  --reassignment-json-file reassignment.json \
  --verify

# 4. Stop and remove broker
systemctl stop kafka
systemctl disable kafka
```

---

## 5. DISASTER RECOVERY PROCEDURES

### Single Node Failure Recovery

```bash
# Automatic recovery - No action needed if:
# - Cluster has 3 nodes minimum
# - Replication factor >= 3
# - min.insync.replicas = 2

# Recovery steps for permanent hardware failure:
# 1. Install new hardware
# 2. Install OS and Kafka
# 3. Use SAME node.id and cluster.id
# 4. Format storage with SAME cluster UUID
# 5. Start service - automatic replication begins

# Verify recovery
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions
```

### Complete Cluster Failure Recovery

```bash
# Prerequisites:
# - Backups available
# - DR cluster running

# Option 1: Restore from DR cluster (Recommended)
# 1. Promote DR cluster to production
# 2. Update application configs
# 3. Rebuild primary cluster
# 4. Reverse MirrorMaker direction

# Option 2: Restore from backups
# 1. Rebuild cluster infrastructure
# 2. Format storage with ORIGINAL cluster UUID
# 3. Restore data directories
rsync -av /backup/kafka/logs/ /data/kafka/logs/
rsync -av /backup/kafka/metadata/ /data/kafka/metadata/

# 4. Start all brokers
# 5. Verify data integrity
```

### Data Corruption Recovery

```bash
# Symptoms:
# - Broker won't start
# - Corrupt log segment errors
# - CRC mismatch errors

# Recovery procedure:
# 1. Stop affected broker
systemctl stop kafka

# 2. Identify corrupted segments
grep -i "corrupt" /var/log/kafka/server.log

# 3. Move corrupted segments
mkdir -p /data/kafka/corrupted
mv /data/kafka/logs/topic-0/00000000000000000100.log /data/kafka/corrupted/

# 4. Start broker (will replicate from other brokers)
systemctl start kafka

# 5. Monitor replication
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions
```

---

## 6. PERFORMANCE OPTIMIZATION

### Identify Bottlenecks

```bash
# 1. CPU bottleneck
top -p $(pgrep -f kafka.Kafka)
# Solution: Add brokers or reduce compression

# 2. Disk I/O bottleneck
iostat -x 1
# Solution: Add more disks (RAID) or use faster storage

# 3. Network bottleneck
iftop -i eth0
# Solution: Upgrade network or add brokers

# 4. Memory bottleneck
free -h
vmstat 1
# Solution: Increase page cache (add RAM)

# 5. JVM GC bottleneck
jstat -gc <pid> 1000
# Solution: Tune GC or increase heap
```

### Optimization Actions

```bash
# 1. Partition optimization
# Calculate: Partitions = max(t/p, t/c)
# Recommended: 30-50 partitions per topic for financial data

# 2. Producer batching
# In producer config:
batch.size=32768
linger.ms=10
compression.type=lz4

# 3. Consumer optimization
# In consumer config:
fetch.min.bytes=1048576
fetch.max.wait.ms=500
max.poll.records=500

# 4. Broker configuration
# In server.properties:
num.network.threads=8
num.io.threads=16
```

---

## 7. MONITORING QUERIES

### JMX Metrics (via JConsole or Prometheus)

```bash
# Key metrics to monitor:

# 1. Messages in per second
kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec

# 2. Bytes in/out per second
kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec
kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec

# 3. Under-replicated partitions (should be 0)
kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions

# 4. Offline partitions (should be 0)
kafka.controller:type=KafkaController,name=OfflinePartitionsCount

# 5. Active controller count (should be 1)
kafka.controller:type=KafkaController,name=ActiveControllerCount

# 6. Request latency (p99)
kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce
kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchConsumer

# 7. ISR shrink/expand rate
kafka.server:type=ReplicaManager,name=IsrShrinksPerSec
kafka.server:type=ReplicaManager,name=IsrExpandsPerSec
```

### Log Analysis

```bash
# Find errors
grep -i "error" /var/log/kafka/server.log | tail -50

# Find warnings
grep -i "warn" /var/log/kafka/server.log | tail -50

# Monitor rebalances
grep -i "rebalance" /var/log/kafka/server.log

# Monitor leader elections
grep -i "election" /var/log/kafka/controller.log

# GC pauses
grep -i "gc pause" /var/log/kafka/gc.log
```

---

## 8. QUICK REFERENCE COMMANDS

```bash
# Cluster Status
kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status

# Topic Operations
kafka-topics.sh --bootstrap-server kafka1:9092 --list
kafka-topics.sh --bootstrap-server kafka1:9092 --describe --topic <topic>
kafka-topics.sh --bootstrap-server kafka1:9092 --create --topic <topic> --partitions 3 --replication-factor 3

# Consumer Groups
kafka-consumer-groups.sh --bootstrap-server kafka1:9092 --list
kafka-consumer-groups.sh --bootstrap-server kafka1:9092 --describe --group <group>

# Performance Testing
kafka-producer-perf-test.sh --topic test --num-records 1000000 --record-size 1024 --throughput -1 --producer-props bootstrap.servers=kafka1:9092
kafka-consumer-perf-test.sh --bootstrap-server kafka1:9092 --topic test --messages 1000000

# Health Checks
kafka-topics.sh --bootstrap-server kafka1:9092 --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server kafka1:9092 --describe --unavailable-partitions

# Service Management
systemctl start kafka
systemctl stop kafka
systemctl restart kafka
systemctl status kafka
journalctl -u kafka -f
```

---

## 9. ALERT THRESHOLDS

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Under-replicated partitions | >0 for 5m | >10 for 1m | Investigate broker health |
| Offline partitions | >0 | >0 for 1m | Immediate action required |
| Consumer lag | >10000 | >100000 | Scale consumers |
| Disk usage | >80% | >90% | Clean logs or add disk |
| CPU usage | >80% | >95% | Add brokers |
| Memory usage | >85% | >95% | Increase RAM |
| GC pause time | >1s | >5s | Tune GC or add heap |
| Network saturation | >80% | >95% | Upgrade network |

---

**Document Version:** 1.0  
**Last Updated:** January 31, 2026  
**Kafka Version:** 4.1.1
