# Daily Operations Guide
## Managing Your Kafka Cluster - Simple Guide

This guide explains how to operate and maintain your Kafka cluster in simple terms.

---

##  Table of Contents

1. [Daily Health Checks](#daily-health-checks)
2. [Common Tasks](#common-tasks)
3. [Creating Topics](#creating-topics)
4. [Managing Consumers](#managing-consumers)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

##  Daily Health Checks

**What:** Things to check every day to ensure your cluster is healthy.

**When:** Start of each business day (takes 5 minutes).

### Check 1: Are All Brokers Running?

**What this checks:** All 3 servers are online and responding.

```bash
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

**What to expect:**
```
kafka1:9092 (id: 1 rack: null) -> ...
kafka2:9092 (id: 2 rack: null) -> ...
kafka3:9092 (id: 3 rack: null) -> ...
```

**What this means:**
-  Good: You see all 3 servers listed
-  Bad: Only 1 or 2 servers show up

**If bad:** One server might be down. Check: `systemctl status kafka` on each server.

---

### Check 2: Under-Replicated Partitions

**What this checks:** Whether all data has enough copies.

**Think of it as:** Checking if all your important documents have backup copies.

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --under-replicated-partitions
```

**What to expect:**
-  Good: No output (empty result)
-  Bad: Shows list of partitions

**What it means:**
- If empty: All data has 3 copies (good!)
- If not empty: Some data has less than 3 copies (investigate!)

**Why it matters:** Financial transactions need backup copies for safety.

---

### Check 3: Offline Partitions

**What this checks:** Whether any data is completely unavailable.

**Think of it as:** Checking if any filing cabinets are locked and inaccessible.

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --unavailable-partitions
```

**What to expect:**
-  Good: No output (empty result)
-  Bad: Shows list of partitions (CRITICAL!)

**What it means:**
- If empty: All data is accessible (good!)
- If not empty: Some data can't be accessed (URGENT FIX NEEDED!)

---

### Check 4: Consumer Lag

**What this checks:** Whether consumers are keeping up with incoming messages.

**Think of it as:** Checking if your mail sorters are keeping up with incoming mail.

```bash
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --all-groups
```

**What to expect:**
```
GROUP           TOPIC              PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
payment-group   transactions       0          1000            1000            0
payment-group   transactions       1          1500            1500            0
```

**What these numbers mean:**
- **CURRENT-OFFSET:** Last message the consumer processed
- **LOG-END-OFFSET:** Latest message available
- **LAG:** Difference (how far behind consumer is)

**Interpreting LAG:**
-  LAG = 0: Perfect! Consumer is up-to-date
-  LAG < 10,000: Acceptable
-  LAG > 100,000: Consumer is falling behind (needs investigation)

---

##  Common Tasks

### Task 1: Creating a Topic

**What:** A topic is like a folder where messages are stored.

**When:** Before your application starts sending messages.

**Example: Create a topic for financial transactions**

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic financial-transactions \
  --partitions 30 \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --config retention.ms=2592000000 \
  --config compression.type=lz4
```

**Breaking down the command:**

| Parameter | Value | What It Means |
|-----------|-------|---------------|
| `--topic` | financial-transactions | Name of the topic (like a folder name) |
| `--partitions` | 30 | Split into 30 parts for better performance |
| `--replication-factor` | 3 | Store 3 copies (one on each server) |
| `--config min.insync.replicas` | 2 | Need 2 copies confirmed before success |
| `--config retention.ms` | 2592000000 | Keep data for 30 days (in milliseconds) |
| `--config compression.type` | lz4 | Compress data to save space |

**Simple explanation:**
- **Partitions:** Like having 30 checkout lanes instead of 1 (faster processing)
- **Replication:** Like making 2 photocopies (data safety)
- **Min in-sync replicas:** Like needing 2 signatures on important documents
- **Retention:** Like keeping files for 30 days before archiving
- **Compression:** Like zipping files to save space

---

### Task 2: Listing All Topics

**What:** See all topics in your cluster.

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --list
```

**What to expect:**
```
financial-transactions
user-events
order-payments
```

---

### Task 3: Viewing Topic Details

**What:** See detailed information about a specific topic.

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic financial-transactions
```

**What to expect:**
```
Topic: financial-transactions  PartitionCount: 30  ReplicationFactor: 3
  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3
  Partition: 1  Leader: 2  Replicas: 2,3,1  Isr: 2,3,1
  ...
```

**Understanding the output:**

| Term | What It Means |
|------|---------------|
| **PartitionCount** | Total number of partitions (30) |
| **ReplicationFactor** | Number of copies (3) |
| **Leader** | Which server handles writes for this partition |
| **Replicas** | Which servers have copies of this partition |
| **Isr** | In-Sync Replicas (replicas that are up-to-date) |

**What to check:**
-  Replicas should be: 1,2,3 (all three servers)
-  Isr should match Replicas (all copies up-to-date)
-  If Isr is smaller than Replicas: Some copies are behind

---

### Task 4: Changing Topic Configuration

**What:** Modify settings for an existing topic.

**Example: Change retention from 7 days to 30 days**

```bash
/opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka1:9092 \
  --entity-type topics \
  --entity-name financial-transactions \
  --alter \
  --add-config retention.ms=2592000000
```

**Common configurations to change:**

| Setting | What It Does | Example Value |
|---------|--------------|---------------|
| `retention.ms` | How long to keep data | 2592000000 (30 days) |
| `retention.bytes` | Maximum size of topic | 1073741824 (1 GB) |
| `compression.type` | Compression method | lz4, gzip, snappy |
| `min.insync.replicas` | Required replicas | 2 (for safety) |

---

### Task 5: Deleting a Topic (Use with Caution!)

**What:** Permanently delete a topic and all its data.

** WARNING: This cannot be undone! Data will be lost!**

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --topic test-topic
```

**Best practice:**
1. Always backup data before deleting
2. Verify you're deleting the right topic
3. Check with stakeholders first
4. Never delete production topics without approval

---

##  Managing Consumer Groups

**What:** Consumer groups are applications that read messages from topics.

### View All Consumer Groups

```bash
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --list
```

**What to expect:**
```
payment-processor-group
fraud-detection-group
notification-service-group
```

---

### View Consumer Group Details

```bash
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --group payment-processor-group
```

**What to expect:**
```
GROUP                 TOPIC              PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
payment-processor     transactions       0          5000            5000            0
payment-processor     transactions       1          4800            5100            300
```

**What this tells you:**
- **CURRENT-OFFSET:** Consumer read up to message 5000
- **LOG-END-OFFSET:** Latest message is 5000
- **LAG:** Consumer is 0 messages behind (caught up!)

---

### Reset Consumer Offsets (Advanced)

**What:** Make consumers re-read messages from a specific point.

** Use with caution!** This makes consumers re-process messages.

**Example: Reset to beginning (re-process all messages)**

```bash
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --group payment-processor-group \
  --topic financial-transactions \
  --reset-offsets \
  --to-earliest \
  --execute
```

**Common reset options:**

| Option | What It Does |
|--------|--------------|
| `--to-earliest` | Start from very first message |
| `--to-latest` | Skip to newest message |
| `--to-offset 1000` | Start from message 1000 |
| `--shift-by -100` | Go back 100 messages |

**When to use:**
- Re-processing after a bug fix
- Testing consumer logic
- Recovering from data processing error

** Important:** Stop consumers before resetting offsets!

---

##  Monitoring

### Check Cluster Health (Quick)

**One-line health check:**

```bash
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status
```

**What to expect:**
```
NodeId  LogEndOffset  Lag  LastFetchTimestamp  Status
1       1000          0    1234567890          Leader
2       1000          0    1234567890          Follower
3       1000          0    1234567890          Follower
```

**Good indicators:**
-  All 3 nodes listed
-  Lag = 0 for all nodes
-  One Leader, two Followers

---

### Monitor Disk Space

**Why:** Kafka stores a lot of data. Running out of disk space is bad!

```bash
df -h /data/kafka
```

**What to expect:**
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdb1       1.0T  250G  750G  25% /data/kafka
```

**What to watch:**
-  Use% < 80%: Good
-  Use% 80-90%: Warning (plan to add space)
-  Use% > 90%: Critical (clean up or add space NOW)

**What to do if disk is full:**
1. Check retention settings (reduce if too high)
2. Delete old/unused topics
3. Add more disk space
4. Enable compression

---

### Monitor Service Status

**Check if Kafka is running:**

```bash
systemctl status kafka
```

**What to expect:**
```
 kafka.service - Apache Kafka Server (KRaft Mode)
   Loaded: loaded
   Active: active (running) since ...
```

**Indicators:**
-  Active: active (running) - Good!
-  Active: failed - Service crashed
-  Active: activating - Service starting

---

##  Troubleshooting

### Problem 1: "Cannot connect to Kafka"

**Symptoms:**
- Applications can't connect
- Error: "Connection refused"

**Checks:**

1. **Is Kafka running?**
   ```bash
   systemctl status kafka
   ```

2. **Is port 9092 open?**
   ```bash
   netstat -tulpn | grep 9092
   ```

3. **Can you ping the server?**
   ```bash
   ping kafka1
   ```

4. **Check firewall:**
   ```bash
   firewall-cmd --list-ports
   # Should show 9092/tcp
   ```

**Solutions:**
- If Kafka stopped: `systemctl start kafka`
- If port blocked: `firewall-cmd --add-port=9092/tcp --permanent && firewall-cmd --reload`
- If can't ping: Check network connectivity

---

### Problem 2: "Under-Replicated Partitions"

**Symptoms:**
- Under-replicated partitions > 0
- Data not fully replicated

**What it means:**
Some data doesn't have 3 copies (risky!).

**Checks:**

1. **Check all brokers are up:**
   ```bash
   /opt/kafka/bin/kafka-broker-api-versions.sh \
     --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
   ```

2. **Check disk space:**
   ```bash
   df -h /data/kafka
   ```

3. **Check network between servers:**
   ```bash
   ping kafka2  # from kafka1
   ping kafka3  # from kafka1
   ```

**Solutions:**
- If a broker is down: `systemctl start kafka` on that broker
- If disk full: Free up space or add disk
- Wait 5-10 minutes: Replication catches up automatically

---

### Problem 3: "High Consumer Lag"

**Symptoms:**
- LAG column shows high numbers (> 100,000)
- Consumers falling behind

**What it means:**
Your consumers can't keep up with incoming messages.

**Checks:**

1. **How high is the lag?**
   ```bash
   /opt/kafka/bin/kafka-consumer-groups.sh \
     --bootstrap-server kafka1:9092 \
     --describe --group your-group-name
   ```

2. **Is lag increasing or decreasing?**
   Run the command twice, 1 minute apart. Compare LAG values.

**Solutions:**

| Scenario | Solution |
|----------|----------|
| Lag decreasing | Good! Consumer catching up. Wait. |
| Lag constant | Add more consumer instances |
| Lag increasing | Urgent! Scale consumers or optimize code |

**How to scale consumers:**
- Add more instances of your consumer application
- Note: Max consumers = number of partitions
- Example: 30 partitions = max 30 consumer instances

---

### Problem 4: "Kafka Won't Start"

**Symptoms:**
- `systemctl start kafka` fails
- Service shows "failed" status

**Checks:**

1. **Check Kafka logs:**
   ```bash
   tail -100 /var/log/kafka/server.log
   ```

2. **Check systemd logs:**
   ```bash
   journalctl -u kafka -n 100 --no-pager
   ```

3. **Check ports:**
   ```bash
   netstat -tulpn | grep 9092
   # Should be empty if Kafka is stopped
   ```

**Common errors and solutions:**

| Error in logs | Cause | Solution |
|---------------|-------|----------|
| "Address already in use" | Another process using port 9092 | Kill other process or change port |
| "No space left on device" | Disk full | Free up space: `df -h /data/kafka` |
| "Permission denied" | Wrong file permissions | `chown -R kafka:kafka /data/kafka` |
| "cluster.id mismatch" | Wrong cluster UUID | Reformat storage with correct UUID |

---

##  Maintenance

### Restart Single Broker (No Downtime)

**When:** Applying configuration changes or OS updates.

**Steps:**

1. **Stop broker 1:**
   ```bash
   ssh kafka1
   sudo systemctl stop kafka
   ```

2. **Wait 60 seconds:**
   ```bash
   sleep 60
   ```
   This lets other brokers take over leadership.

3. **Start broker 1:**
   ```bash
   sudo systemctl start kafka
   ```

4. **Wait 30 seconds:**
   ```bash
   sleep 30
   ```

5. **Verify it rejoined:**
   ```bash
   /opt/kafka/bin/kafka-broker-api-versions.sh \
     --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
   ```

6. **Repeat for broker 2 and broker 3**

**Why this works:**
- With 3 brokers, cluster stays online even if 1 is down
- Waiting ensures smooth leadership transfer
- No data loss because data is replicated

---

### Rolling Restart (All Brokers)

**When:** Upgrading Kafka version or major changes.

**Full procedure:**

```bash
# Broker 1
ssh kafka1 'sudo systemctl stop kafka'
sleep 60
ssh kafka1 'sudo systemctl start kafka'
sleep 30

# Verify health
/opt/kafka/bin/health-check.sh

# Broker 2
ssh kafka2 'sudo systemctl stop kafka'
sleep 60
ssh kafka2 'sudo systemctl start kafka'
sleep 30

# Verify health
/opt/kafka/bin/health-check.sh

# Broker 3
ssh kafka3 'sudo systemctl stop kafka'
sleep 60
ssh kafka3 'sudo systemctl start kafka'
sleep 30

# Final verification
/opt/kafka/bin/cluster-status.sh
```

**Time required:** ~10-15 minutes for all 3 brokers

---

### Check Logs

**Where logs are:**
- **Kafka application logs:** `/var/log/kafka/server.log`
- **Systemd logs:** `journalctl -u kafka`
- **Garbage collection logs:** `/var/log/kafka/gc.log`

**View real-time logs:**
```bash
tail -f /var/log/kafka/server.log
```

**Search for errors:**
```bash
grep -i error /var/log/kafka/server.log | tail -50
grep -i exception /var/log/kafka/server.log | tail -50
```

**What to look for:**
-  INFO messages: Normal operations
-  WARN messages: Potential issues (investigate)
-  ERROR messages: Problems (fix immediately)

---

##  Getting Help

If you need help:

1. **Check this guide first**
2. **Check Kafka logs:** `/var/log/kafka/server.log`
3. **Check systemd logs:** `journalctl -u kafka -n 100`
4. **Search online:** Use error messages from logs
5. **Ask for help:** Include log snippets and error messages

**Useful resources:**
- Kafka Documentation: https://kafka.apache.org/documentation/
- Community Forum: https://kafka.apache.org/contact
- Stack Overflow: Tag `apache-kafka`

---

**Last Updated:** January 31, 2026  
**Kafka Version:** 4.1.1  
**Difficulty:** Beginner-friendly
