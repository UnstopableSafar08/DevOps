# Kafka Quick Reference Cheat Sheet
## Essential Commands for Daily Operations

---

##  Common Commands

### Cluster Management

```bash
# Check cluster status
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status

# List all brokers
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092

# Health check
/opt/kafka/bin/health-check.sh
```

---

### Topic Operations

```bash
# Create topic
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic TOPIC_NAME \
  --partitions 3 \
  --replication-factor 3

# List all topics
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --list

# Describe topic
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic TOPIC_NAME

# Delete topic
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --topic TOPIC_NAME

# Alter topic (add partitions)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --alter \
  --topic TOPIC_NAME \
  --partitions 50
```

---

### Consumer Group Management

```bash
# List consumer groups
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --list

# Describe consumer group (see lag)
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --group GROUP_NAME

# Reset consumer group offsets to earliest
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group GROUP_NAME \
  --topic TOPIC_NAME \
  --reset-offsets \
  --to-earliest \
  --execute

# Reset to latest
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group GROUP_NAME \
  --topic TOPIC_NAME \
  --reset-offsets \
  --to-latest \
  --execute
```

---

### Testing & Debugging

```bash
# Console producer (send messages manually)
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic TOPIC_NAME

# Console consumer (read messages)
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic TOPIC_NAME \
  --from-beginning

# Consumer with group
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic TOPIC_NAME \
  --group TEST_GROUP \
  --from-beginning
```

---

### Service Management

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

# View logs
journalctl -u kafka -f

# Check service configuration
systemctl cat kafka
```

---

### Log Management

```bash
# View server log
tail -f /var/log/kafka/server.log

# View last 100 lines
tail -100 /var/log/kafka/server.log

# Search for errors
grep -i error /var/log/kafka/server.log

# Search for warnings
grep -i warn /var/log/kafka/server.log

# Follow logs from specific time
journalctl -u kafka --since "1 hour ago" -f
```

---

### Health Checks

```bash
# Check under-replicated partitions (should be 0)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --under-replicated-partitions

# Check offline partitions (should be 0)
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --unavailable-partitions

# Check consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --all-groups

# Verify all brokers responsive
for i in 1 2 3; do
  echo "Testing kafka$i..."
  telnet kafka$i 9092
done
```

---

##  Configuration

### Important Files

```bash
# Main configuration
/opt/kafka/config/server.properties

# Systemd service
/etc/systemd/system/kafka.service

# Data directories
/data/kafka/logs/           # Topic data
/data/kafka/metadata/       # KRaft metadata

# Log files
/var/log/kafka/server.log   # Main log
```

### Key Settings

```properties
# Node identification
node.id=1                   # Unique per server
cluster.id=<UUID>           # Same for all servers

# Replication
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3

# Performance
num.partitions=3
compression.type=lz4
```

---

##  Troubleshooting

### Quick Diagnostics

```bash
# Check if Kafka is running
ps aux | grep kafka

# Check ports
netstat -tulpn | grep 9092

# Check disk space
df -h /data/kafka

# Check memory
free -h

# Check CPU
top -p $(pgrep -f kafka.Kafka)

# Check network connectivity
ping kafka1
ping kafka2
ping kafka3
```

### Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| Won't start | Logs | `tail -100 /var/log/kafka/server.log` |
| Port in use | Ports | `netstat -tulpn \| grep 9092` |
| Slow performance | Disk | `iostat -x 1` |
| High CPU | Threads | `top -H -p $(pgrep -f kafka)` |

---

##  Monitoring

### JMX Metrics (port 9999)

```bash
# Enable JMX in server.properties
#kafka.jmx.enable=true
#kafka.jmx.port=9999

# Connect with JConsole
jconsole kafka1:9999
```

### Key Metrics

- `kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec`
- `kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec`
- `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`
- `kafka.controller:type=KafkaController,name=ActiveControllerCount`

---

##  Maintenance

### Rolling Restart

```bash
# Node 1
sudo systemctl stop kafka   # on kafka1
sleep 60
sudo systemctl start kafka  # on kafka1
sleep 30

# Verify
/opt/kafka/bin/health-check.sh

# Repeat for nodes 2 and 3
```

### Backup

```bash
# Backup configuration
tar -czf kafka-config-backup-$(date +%Y%m%d).tar.gz \
  /opt/kafka/config/

# Backup data (during maintenance window only!)
rsync -av /data/kafka/logs/ /backup/kafka/logs/
```

---

##  Quick Reference

### Bootstrap Servers

Always use all 3 servers for redundancy:
```
kafka1:9092,kafka2:9092,kafka3:9092
```

### Ports

- `9092` - Kafka broker (clients)
- `9093` - Kafka SSL
- `9094` - KRaft controller
- `9999` - JMX monitoring

### Critical Commands (Memorize These!)

```bash
# Service control
systemctl start|stop|restart|status kafka

# Health check
/opt/kafka/bin/health-check.sh

# List topics
/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --list

# Consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka1:9092 --describe --all-groups

# View logs
tail -f /var/log/kafka/server.log
```

---

##  Emergency Contacts

### When to Escalate

- All brokers down
- Data loss suspected
- Security breach
- Corruption detected
- Unable to resolve in 1 hour

### Pre-Escalation Checklist

1. Checked logs: `/var/log/kafka/server.log`
2. Verified network connectivity
3. Confirmed disk space available
4. Reviewed recent changes
5. Attempted restart
6. Documented error messages

---

##  More Information

- Full Documentation: `docs/`
- Installation Guide: `docs/03-installation/step-by-step-guide.md`
- Troubleshooting: `docs/07-troubleshooting/common-issues.md`
- Configuration Reference: `docs/04-configuration/server-properties.md`

---

**Print this cheat sheet and keep it handy!**
