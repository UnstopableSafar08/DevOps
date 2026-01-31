# Kafka Commands Cheat Sheet
## Quick Reference for Common Operations

---

##  Table of Contents

1. [Service Management](#service-management)
2. [Cluster Operations](#cluster-operations)
3. [Topic Operations](#topic-operations)
4. [Consumer Group Operations](#consumer-group-operations)
5. [Testing and Performance](#testing-and-performance)
6. [Monitoring and Health Checks](#monitoring-and-health-checks)
7. [Troubleshooting](#troubleshooting)

---

##  Service Management

### Start/Stop/Restart Kafka

```bash
# Start Kafka
sudo systemctl start kafka

# Stop Kafka
sudo systemctl stop kafka

# Restart Kafka
sudo systemctl restart kafka

# Check status
sudo systemctl status kafka

# Enable auto-start on boot
sudo systemctl enable kafka

# Disable auto-start
sudo systemctl disable kafka
```

### View Logs

```bash
# View real-time logs
sudo journalctl -u kafka -f

# View last 100 lines
sudo journalctl -u kafka -n 100

# View logs from last hour
sudo journalctl -u kafka --since "1 hour ago"

# View server log file
tail -f /var/log/kafka/server.log

# Search for errors
grep -i error /var/log/kafka/server.log

# Search for warnings
grep -i warn /var/log/kafka/server.log
```

---

##  Cluster Operations

### Check Cluster Status

```bash
# View cluster metadata
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status

# View controller information
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --replication

# List all brokers
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

### Check Broker Details

```bash
# Get broker configuration
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --describe --entity-type brokers --entity-name 1

# Get cluster ID
cat /data/kafka/metadata/meta.properties | grep cluster.id
```

---

##  Topic Operations

### Create Topic

```bash
# Create basic topic
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic my-topic \
  --partitions 30 \
  --replication-factor 3

# Create topic with custom configuration
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

**What each setting means:**
- `partitions`: Number of partitions (higher = more parallelism)
- `replication-factor`: Number of copies (3 = stored on 3 servers)
- `min.insync.replicas`: Minimum replicas that must acknowledge write
- `retention.ms`: How long to keep messages (ms)
- `compression.type`: Compression algorithm (lz4, gzip, snappy, zstd)

### List Topics

```bash
# List all topics
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --list

# List topics with details
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --list --exclude-internal
```

### Describe Topic

```bash
# Describe specific topic
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic financial-transactions

# Describe all topics
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe

# Show under-replicated partitions only
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions

# Show unavailable partitions only
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --unavailable-partitions
```

### Modify Topic

```bash
# Increase partitions (cannot decrease!)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --alter \
  --topic financial-transactions \
  --partitions 50

# Modify topic configuration
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type topics \
  --entity-name financial-transactions \
  --alter \
  --add-config retention.ms=1209600000

# Remove configuration override
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type topics \
  --entity-name financial-transactions \
  --alter \
  --delete-config retention.ms
```

### Delete Topic

```bash
# Delete topic (if deletion enabled)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --topic test-topic

# Force delete (dangerous - use with caution!)
sudo rm -rf /data/kafka/logs/test-topic-*
```

---

##  Consumer Group Operations

### List Consumer Groups

```bash
# List all consumer groups
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --list

# List groups for specific topic
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --list --state
```

### Describe Consumer Group

```bash
# View consumer group details
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --group payment-processor-group

# View all groups
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe --all-groups

# Show only groups with lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe --all-groups | grep -v "0         0"
```

**Understanding the output:**
- `CURRENT-OFFSET`: Last message consumer read
- `LOG-END-OFFSET`: Latest message in partition
- `LAG`: Number of unprocessed messages
- `CONSUMER-ID`: Which consumer is processing this partition

### Reset Consumer Group Offsets

```bash
# Reset to earliest (beginning)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions \
  --reset-offsets --to-earliest \
  --execute

# Reset to latest (end)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions \
  --reset-offsets --to-latest \
  --execute

# Reset to specific offset
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions:0 \
  --reset-offsets --to-offset 1000 \
  --execute

# Reset by time (to 2 hours ago)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions \
  --reset-offsets --by-duration PT2H \
  --execute
```

** WARNING:** Resetting offsets will cause consumers to reprocess messages!

### Delete Consumer Group

```bash
# Delete consumer group (must be inactive first!)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --group test-group
```

---

##  Testing and Performance

### Console Producer (Send Messages)

```bash
# Start interactive producer
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions

# Then type messages (one per line):
# Payment: $100 from A to B
# Payment: $250 from C to D
# Press Ctrl+C to exit

# Produce from file
cat messages.txt | /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions

# Produce with key (for ordering)
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --property "parse.key=true" \
  --property "key.separator=:"

# Then type: key:value
# account-123:Payment $100
```

### Console Consumer (Read Messages)

```bash
# Read from beginning
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --from-beginning

# Read only new messages
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions

# Read with consumer group
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --group test-consumer-group

# Read with key and timestamp
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --from-beginning \
  --property print.key=true \
  --property print.timestamp=true

# Read specific partition
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --partition 0 \
  --from-beginning
```

### Performance Testing

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

##  Monitoring and Health Checks

### Quick Health Check

```bash
# Check if all brokers are up
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092 | wc -l

# Should show 3 (one per broker)

# Check for under-replicated partitions
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --under-replicated-partitions | wc -l

# Should show 0 (no under-replicated partitions)

# Check for offline partitions
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe --unavailable-partitions | wc -l

# Should show 0 (no offline partitions)
```

### Comprehensive Health Check Script

```bash
#!/bin/bash
# Save as: /opt/kafka/bin/health-check.sh

BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"

echo "=== Kafka Health Check ==="
echo ""

# Check brokers
echo "1. Checking brokers..."
BROKERS=$(/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server $BOOTSTRAP 2>/dev/null | grep -c "kafka")
echo "   Active brokers: $BROKERS/3"

# Check under-replicated partitions
echo "2. Checking replication..."
URP=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --under-replicated-partitions 2>/dev/null | grep -c "Topic:")
echo "   Under-replicated partitions: $URP"

# Check offline partitions
echo "3. Checking availability..."
OFFLINE=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --unavailable-partitions 2>/dev/null | grep -c "Topic:")
echo "   Offline partitions: $OFFLINE"

# Overall status
echo ""
if [ "$BROKERS" -eq 3 ] && [ "$URP" -eq 0 ] && [ "$OFFLINE" -eq 0 ]; then
  echo "Status:  HEALTHY"
  exit 0
else
  echo "Status:  UNHEALTHY"
  exit 1
fi
```

### Monitor in Real-Time

```bash
# Watch cluster status
watch -n 5 '/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status'

# Watch consumer lag
watch -n 2 '/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe --group payment-processor-group'

# Monitor logs
tail -f /var/log/kafka/server.log | grep -i -E "error|warn|exception"
```

---

##  Troubleshooting

### Check Disk Space

```bash
# Check data directory disk usage
df -h /data/kafka

# Check log sizes by topic
du -sh /data/kafka/logs/*

# Find largest log segments
find /data/kafka/logs -name "*.log" -exec ls -lh {} \; | sort -k5 -h | tail -20
```

### Check Process and Resources

```bash
# Check if Kafka process is running
ps aux | grep kafka

# Check memory usage
free -h

# Check disk I/O
iostat -x 1

# Check network connections
netstat -tulpn | grep -E "9092|9094"

# Check file handles
lsof -p $(pgrep -f kafka.Kafka) | wc -l
```

### Force Stop Kafka

```bash
# If systemctl stop doesn't work
sudo systemctl kill kafka

# Or find and kill process
kill -9 $(pgrep -f kafka.Kafka)
```

### Clean Up Test Data

```bash
# Delete all topics (careful!)
for topic in $(/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --list); do
  echo "Deleting $topic"
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --delete --topic $topic
done

# Clean old log segments
/opt/kafka/bin/kafka-run-class.sh kafka.tools.LogCleaner \
  /opt/kafka/config/server.properties
```

---

##  Pro Tips

### Use Aliases for Common Commands

Add to `~/.bashrc`:

```bash
alias kafka-topics='/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092'
alias kafka-consumer-groups='/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka1:9092'
alias kafka-console-consumer='/opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka1:9092'
alias kafka-console-producer='/opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka1:9092'
alias kafka-health='/opt/kafka/bin/health-check.sh'
```

Then you can use:
```bash
kafka-topics --list
kafka-consumer-groups --describe --all-groups
kafka-health
```

### Common One-Liners

```bash
# Count messages in topic
/opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions | awk -F':' '{sum += $3} END {print sum}'

# Find topics with most partitions
/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --describe | \
  grep "PartitionCount" | sort -t':' -k2 -nr | head -10

# Find consumer groups with most lag
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka1:9092 \
  --describe --all-groups | grep -v "0         0" | sort -k5 -nr | head -10
```

---

##  Quick Reference Card

### Most Used Commands

| Task | Command |
|------|---------|
| **Start Kafka** | `sudo systemctl start kafka` |
| **Stop Kafka** | `sudo systemctl stop kafka` |
| **Check Status** | `sudo systemctl status kafka` |
| **View Logs** | `tail -f /var/log/kafka/server.log` |
| **List Topics** | `kafka-topics.sh --list` |
| **Create Topic** | `kafka-topics.sh --create --topic NAME --partitions 3 --replication-factor 3` |
| **Describe Topic** | `kafka-topics.sh --describe --topic NAME` |
| **Send Message** | `kafka-console-producer.sh --topic NAME` |
| **Read Messages** | `kafka-console-consumer.sh --topic NAME --from-beginning` |
| **List Groups** | `kafka-consumer-groups.sh --list` |
| **Check Lag** | `kafka-consumer-groups.sh --describe --group NAME` |
| **Health Check** | `/opt/kafka/bin/health-check.sh` |

---

##  Emergency Commands

### When Things Go Wrong

```bash
# 1. Quick diagnosis
sudo systemctl status kafka
tail -100 /var/log/kafka/server.log
/opt/kafka/bin/health-check.sh

# 2. Check for common issues
df -h /data/kafka  # Disk full?
free -h            # Out of memory?
netstat -tulpn | grep 9092  # Port conflict?

# 3. Safe restart
sudo systemctl restart kafka
sleep 30
sudo systemctl status kafka

# 4. If restart fails, check logs
journalctl -u kafka -n 200
```

---

**Keep this cheat sheet handy for quick reference!**

---

*Last Updated: January 31, 2026*  
*Kafka Version: 4.1.1*  
*For: Production Operations*
