# Frequently Asked Questions (FAQ)
## Common Questions About Kafka - Simple Answers

---

##  General Questions

### Q1: What is Kafka in simple terms?

**Answer:**

Imagine a super-reliable postal service for computer programs:

```
Sender Program → Kafka → Receiver Program
```

**Real example:**
- Your banking app sends: "Transfer $100 from A to B"
- Kafka stores this message safely
- Payment processor picks it up and executes it
- Even if payment processor is offline, Kafka keeps the message safe

**Key features:**
-  Never loses messages (stores multiple copies)
-  Very fast (handles millions of messages per second)
-  Reliable (keeps working even if servers fail)
-  Ordered (messages arrive in the order they were sent)

**Think of Kafka as:**
- A message queue (like email inbox)
- A database for events (like a timeline)
- A conveyor belt for data (like factory assembly line)

---

### Q2: Why use Kafka instead of a regular database?

**Answer:**

| Task | Use This | Why |
|------|----------|-----|
| **Store customer data** | Database (MySQL, PostgreSQL) | Need to query and update data |
| **Process live events** | Kafka | Need to handle millions of events per second |
| **Send messages between apps** | Kafka | Need reliable, fast message delivery |

**Simple example:**

**Database approach:**
```
App → Write to Database → Other App reads from Database
Problem: Slow if millions of updates per second
```

**Kafka approach:**
```
App → Write to Kafka → Other App reads from Kafka
Benefit: Can handle millions of events per second
```

**When to use Kafka:**
-  Real-time data processing
-  Microservices communication
-  Event streaming
-  Log aggregation
-  Financial transactions

**When NOT to use Kafka:**
-  Simple CRUD operations (use database)
-  Need immediate response (use REST API)
-  Small data volumes (overhead not worth it)

---

### Q3: What is KRaft and why do we use it?

**Answer:**

**Old way (ZooKeeper):**
```
Kafka Cluster (3 servers) + ZooKeeper Cluster (3 servers) = 6 servers total
```

**New way (KRaft):**
```
Kafka Cluster (3 servers) = 3 servers total
```

**Benefits of KRaft:**
-  **Simpler:** One system instead of two
-  **Cheaper:** Need fewer servers (50% cost savings)
-  **Faster:** No network calls to external system
-  **More reliable:** Fewer things to break
-  **Future-proof:** Only supported option going forward

**Think of it as:**
- ZooKeeper: Like having a separate manager team
- KRaft: Managers are built into the worker team

**Important:** ZooKeeper support ended November 2025. KRaft is the only option for new clusters.

---

### Q4: What are topics, partitions, and replicas?

**Answer with simple analogies:**

**Topic = Filing Cabinet**
- A category for storing related messages
- Example: `financial-transactions`, `user-logins`, `order-payments`

**Partition = Drawer in Filing Cabinet**
- Topics split into multiple partitions
- Example: Topic with 30 partitions = 30 drawers
- Why: Allows parallel processing (faster!)

**Replica = Photocopy**
- Each partition stored on multiple servers
- Example: Replication factor 3 = 3 copies
- Why: If one server fails, others have the data

**Visual:**
```
Topic: financial-transactions
├─ Partition 0 → Copy on Server 1, Server 2, Server 3
├─ Partition 1 → Copy on Server 2, Server 3, Server 1
└─ Partition 2 → Copy on Server 3, Server 1, Server 2
```

---

##  Technical Questions

### Q5: How many partitions should my topic have?

**Answer:**

**Simple formula:**
```
Partitions = Target throughput ÷ Per-partition throughput
```

**Example calculation:**
- You need to process 300 MB/s
- Each partition handles ~10 MB/s
- Partitions needed = 300 ÷ 10 = 30 partitions

**Quick guide:**

| Use Case | Partitions | Why |
|----------|------------|-----|
| Small app (< 10 MB/s) | 3-6 | Matches 3 brokers |
| Medium app (10-100 MB/s) | 12-30 | Good parallelism |
| Large app (> 100 MB/s) | 30-50+ | Maximum throughput |

**Rules of thumb:**
- Start with 3-6 partitions per topic
- Max consumers = number of partitions
- More partitions = more parallelism BUT more overhead

**Important:** You can increase partitions later, but NOT decrease them!

---

### Q6: What should my replication factor be?

**Answer:**

**For production (financial transactions):**
```
Replication factor = 3 (ALWAYS!)
```

**Why 3?**
-  Tolerates 1 server failure
-  Allows maintenance without downtime
-  Provides data safety
-  Industry standard

**What each number means:**

| Replication Factor | Data Copies | Fault Tolerance | Use Case |
|-------------------|-------------|-----------------|----------|
| 1 | Single copy |  None | Testing only |
| 2 | Two copies |  1 server can fail | Not recommended |
| 3 | Three copies |  1 server can fail | **Production** |

**Simple explanation:**
- Replication 1: Like keeping important document in one place (risky!)
- Replication 3: Like keeping 3 copies in different safes (safe!)

**For financial transactions: ALWAYS use 3!**

---

### Q7: What is min.insync.replicas and what should it be?

**Answer:**

**What it means:**
Minimum number of replicas that must confirm a write before it's considered successful.

**Setting:**
```
min.insync.replicas = 2 (recommended)
```

**Why 2?**
```
Replication factor: 3 servers have copies
Min in-sync replicas: 2 must confirm
Result: Write succeeds if at least 2 servers confirm
```

**Scenarios:**

| Scenario | min.insync.replicas=1 | min.insync.replicas=2 | min.insync.replicas=3 |
|----------|----------------------|----------------------|----------------------|
| All 3 servers up |  Writes succeed |  Writes succeed |  Writes succeed |
| 2 servers up |  Writes succeed |  Writes succeed |  Writes fail |
| 1 server up |  Writes succeed |  Writes fail |  Writes fail |

**Recommendation:**
- **For financial data:** Use 2 (balances safety and availability)
- **For logs/metrics:** Use 1 (availability more important)
- **For critical audit data:** Use 3 (maximum safety)

**Simple explanation:**
- min.insync.replicas=1: Like needing 1 signature
- min.insync.replicas=2: Like needing 2 signatures (safer!)
- min.insync.replicas=3: Like needing all 3 signatures (very restrictive)

---

### Q8: How much RAM does Kafka need?

**Answer:**

**Quick formula:**
```
Total RAM needed = Heap + Page Cache + OS

For a 64 GB server:
- Kafka Heap: 6 GB
- Page Cache: 54 GB
- OS + other: 4 GB
Total: 64 GB
```

**Why this split?**

**Heap (6 GB):**
- Java memory for Kafka process
- Too small = Crashes
- Too large = Slow garbage collection
- Sweet spot: 4-12 GB

**Page Cache (54 GB):**
- Operating system file cache
- THIS IS CRITICAL for Kafka!
- More page cache = Better performance
- Kafka relies on this for speed

**Simple explanation:**
- Heap = Kafka's working desk (small, but fast)
- Page Cache = Kafka's filing system (large, for data)

**Server sizing guide:**

| Server RAM | Heap Size | Page Cache | Good For |
|------------|-----------|------------|----------|
| 32 GB | 4 GB | ~24 GB | Small workloads |
| 64 GB | 6 GB | ~54 GB | **Recommended** |
| 128 GB | 8-10 GB | ~110 GB | Large workloads |

**Rule:** Never use more than 50% of server RAM for heap!

---

### Q9: How long should I keep data (retention)?

**Answer:**

**Common retention settings:**

| Use Case | Retention | Example |
|----------|-----------|---------|
| **Financial transactions** | 30-90 days | `retention.ms=2592000000` (30 days) |
| **Logs/metrics** | 7 days | `retention.ms=604800000` |
| **Audit trail** | 1-7 years | `retention.ms=31536000000` (1 year) |
| **Real-time only** | 1 day | `retention.ms=86400000` |

**Factors to consider:**

1. **Regulatory requirements**
   - Financial services: Often 7 years
   - GDPR: May limit retention

2. **Disk space**
   - Formula: `Daily data × Retention days = Storage needed`
   - Example: 100 GB/day × 30 days = 3 TB needed

3. **Use case**
   - Can consumers re-read old data? → Longer retention
   - Real-time only? → Shorter retention

**Configuration examples:**

```bash
# 7 days
--config retention.ms=604800000

# 30 days
--config retention.ms=2592000000

# 1 year
--config retention.ms=31536000000
```

**Simple explanation:**
- Think of retention like how long you keep emails
- Financial data: Keep longer (legal requirements)
- Temporary data: Keep shorter (save space)

---

### Q10: What compression should I use?

**Answer:**

**Quick recommendation: Use LZ4**

```
compression.type=lz4
```

**Compression comparison:**

| Type | Speed | Compression Ratio | CPU Usage | When to Use |
|------|-------|------------------|-----------|-------------|
| **lz4** |  Very fast |  Good |  Low | **Recommended for most cases** |
| **snappy** |  Fast |  Good |  Low | Alternative to lz4 |
| **gzip** |  Slow |  Better |  High | When space is critical |
| **zstd** |  Fast |  Better |  Medium | Modern option (Kafka 2.1+) |
| **none** |  Fastest |  None |  None | When CPU is limited |

**For financial transactions:**
```
compression.type=lz4
```

**Why LZ4?**
-  Very fast (minimal latency)
-  Low CPU usage
-  Good compression (~50% size reduction)
-  Default in many systems

**Example savings:**
```
Without compression: 1 GB message data
With LZ4:           ~500 MB (50% savings)
With gzip:          ~400 MB (60% savings, but slower)
```

**Simple explanation:**
- none: Like sending files as-is (fast, big)
- lz4: Like using quick zip (fast, smaller)
- gzip: Like using maximum compression (slow, smallest)

---

##  Security Questions

### Q11: Do I need to enable security (SSL/SASL)?

**Answer:**

**For production financial transactions: YES!**

**Why security is critical:**

1. **Encryption (SSL/TLS)**
   - Prevents eavesdropping on messages
   - Required for: Credit card data, personal information
   - Requirement: PCI-DSS, GDPR, SOX

2. **Authentication (SASL)**
   - Verifies who is connecting
   - Prevents unauthorized access
   - Required for: Multi-tenant environments

**Minimum security for financial transactions:**
```
 SSL/TLS encryption (encrypt data in transit)
 SASL authentication (verify clients)
 ACLs (control who can read/write)
 Disk encryption (protect data at rest)
```

**When you can skip security:**
-  Never for production financial data!
-  Only for isolated development environments

**Security levels:**

| Level | Configuration | Use Case |
|-------|--------------|----------|
| **None** | No security | Development only |
| **Basic** | SSL only | Internal apps |
| **Recommended** | SSL + SASL | **Production** |
| **Maximum** | SSL + SASL + ACLs + Encryption at rest | Financial/Healthcare |

**For this guide:** We start with no security for simplicity, but you MUST enable it before production!

See: [Security Setup Guide](SECURITY.md) for step-by-step instructions.

---

### Q12: What ports does Kafka use?

**Answer:**

**Required ports:**

| Port | Protocol | Purpose | Open To |
|------|----------|---------|---------|
| **9092** | PLAINTEXT | Client connections | Applications |
| **9093** | SSL | Encrypted client connections | Applications (if SSL enabled) |
| **9094** | CONTROLLER | Internal cluster communication | Only between Kafka servers |
| **9999** | JMX | Monitoring | Monitoring tools |

**Firewall rules:**

**Between Kafka servers (kafka1, kafka2, kafka3):**
```bash
# Open all ports to each other
9092/tcp - ALLOW from kafka1, kafka2, kafka3
9094/tcp - ALLOW from kafka1, kafka2, kafka3
```

**From application servers:**
```bash
# Open client port only
9092/tcp - ALLOW from app servers
```

**From internet:**
```bash
# NEVER expose directly to internet!
# Use VPN or bastion host
```

**Checking if ports are open:**
```bash
# From application server
telnet kafka1 9092
# Should connect successfully

# From internet (should fail!)
telnet kafka1 9092
# Should timeout or refuse connection
```

---

##  Troubleshooting Questions

### Q13: My cluster says "Under-Replicated Partitions" - is this bad?

**Answer:**

**Short answer: Yes, investigate immediately!**

**What it means:**
Some data doesn't have the required number of copies (usually 3).

**Is it an emergency?**

| Duration | Severity | Action |
|----------|----------|--------|
| < 5 minutes |  Warning | Wait, might resolve automatically |
| 5-30 minutes |  Concern | Investigate cause |
| > 30 minutes |  CRITICAL | Fix immediately! |

**Common causes:**

1. **Broker is down**
   - Check: `systemctl status kafka` on each server
   - Fix: `systemctl start kafka` on failed broker

2. **Network issue**
   - Check: `ping kafka2` from kafka1
   - Fix: Resolve network connectivity

3. **Disk full**
   - Check: `df -h /data/kafka`
   - Fix: Free up space or add disk

4. **Broker overloaded**
   - Check: CPU and disk I/O (`top`, `iostat`)
   - Fix: Add more brokers or reduce load

**How to check:**
```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --under-replicated-partitions
```

**What to expect:**
-  Good: No output (all partitions fully replicated)
-  Bad: Lists partitions (needs fixing)

---

### Q14: How do I know if my cluster is healthy?

**Answer:**

**Quick health check (30 seconds):**

```bash
# 1. All brokers online?
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092 | grep kafka

# Should show 3 brokers

# 2. Any under-replicated partitions?
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --under-replicated-partitions

# Should be empty

# 3. Any offline partitions?
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --unavailable-partitions

# Should be empty
```

**Health indicators:**

| Metric | Healthy | Unhealthy |
|--------|---------|-----------|
| **Brokers online** | 3/3 | < 3 |
| **Under-replicated partitions** | 0 | > 0 |
| **Offline partitions** | 0 | > 0 |
| **Disk usage** | < 80% | > 90% |
| **Consumer lag** | < 10,000 | > 100,000 |

**Automated health check script:**
```bash
#!/bin/bash
# Save as /opt/kafka/bin/health-check.sh

echo "Checking Kafka cluster health..."

# Check brokers
BROKERS=$(kafka-broker-api-versions.sh --bootstrap-server kafka1:9092 2>/dev/null | grep -c kafka)
echo "Brokers online: $BROKERS/3"

# Check under-replicated
URP=$(kafka-topics.sh --bootstrap-server kafka1:9092 --describe --under-replicated-partitions 2>/dev/null | grep -c Topic)
echo "Under-replicated partitions: $URP"

# Check offline
OFFLINE=$(kafka-topics.sh --bootstrap-server kafka1:9092 --describe --unavailable-partitions 2>/dev/null | grep -c Topic)
echo "Offline partitions: $OFFLINE"

# Overall status
if [ "$BROKERS" -eq 3 ] && [ "$URP" -eq 0 ] && [ "$OFFLINE" -eq 0 ]; then
  echo " Cluster is HEALTHY"
  exit 0
else
  echo " Cluster has ISSUES"
  exit 1
fi
```

**Run daily:** Add to cron job to check automatically.

---

### Q15: Can I lose data with Kafka?

**Answer:**

**With proper configuration: Almost impossible!**

**How Kafka prevents data loss:**

1. **Replication**
   ```
   replication.factor=3
   ```
   - Every message copied to 3 servers
   - Even if 2 servers explode, data safe on 3rd

2. **Acknowledgments**
   ```
   acks=all
   min.insync.replicas=2
   ```
   - Producer waits for 2 servers to confirm
   - Write only succeeds if data safely stored

3. **Disk persistence**
   - Messages written to disk immediately
   - Even if power fails, data recovers from disk

**Scenarios:**

| Scenario | Data Lost? | Why |
|----------|-----------|-----|
| 1 server fails |  NO | Other 2 servers have copies |
| 2 servers fail simultaneously |  NO | 1 server still has copy |
| All 3 servers fail |  MAYBE | If power loss without UPS |
| Disk corruption |  NO | Other replicas have good copies |
| Network partition |  NO | Writes pause until healed |

**When data CAN be lost:**

1. **Wrong configuration**
   ```
   acks=1  ← Only leader confirms (risky!)
   replication.factor=1  ← No copies (very risky!)
   ```

2. **All 3 servers destroyed simultaneously**
   - Fire, flood, meteor strike
   - Mitigation: Mirror cluster in different datacenter

3. **Human error**
   - Accidentally deleting topics
   - Mitigation: Disable delete in production

**For financial transactions (ZERO data loss):**
```properties
# Producer settings
acks=all                          # All replicas must confirm
enable.idempotence=true           # Prevent duplicates
retries=2147483647                # Never give up

# Topic settings
replication.factor=3              # 3 copies
min.insync.replicas=2             # Need 2 copies

# Broker settings
unclean.leader.election.enable=false  # Never elect out-of-sync leader
```

**Simple explanation:**
- Properly configured Kafka is MORE reliable than most databases
- Bank-grade reliability is achievable
- But configuration matters!

---

##  Performance Questions

### Q16: Why is Kafka so fast?

**Answer:**

**Kafka's speed secrets:**

1. **Sequential disk I/O**
   - Writes messages one after another (like a log book)
   - Modern disks: Sequential = 600 MB/s, Random = 100 KB/s
   - Kafka uses sequential = 6000x faster!

2. **Page cache**
   - Operating system caches data in RAM
   - Reads served from RAM instead of disk
   - RAM = 1000x faster than disk

3. **Zero-copy**
   - Data goes from disk → network without copying
   - Saves CPU and time
   - Technical magic!

4. **Batching**
   - Sends many messages together instead of one-by-one
   - Example: 1000 small messages = 1 big batch
   - Network trips: 1 instead of 1000

5. **Compression**
   - Smaller data = faster network transfer
   - Example: 1 GB → 500 MB with lz4
   - Transfer time: Half!

**Real-world numbers:**

| Metric | Value |
|--------|-------|
| **Messages per second** | 1-2 million |
| **Throughput** | 100-200 MB/s per broker |
| **Latency (p99)** | < 10 ms |

**Simple explanation:**
- Kafka is fast because it does things in bulk (batching)
- Uses RAM instead of disk when possible (caching)
- Writes sequentially like a diary (sequential I/O)

---

### Q17: How do I make Kafka faster?

**Answer:**

**Quick wins:**

1. **Enable compression**
   ```properties
   compression.type=lz4
   ```
   - Reduces network transfer
   - Impact: 40-60% faster

2. **Batch producer messages**
   ```properties
   batch.size=32768
   linger.ms=10
   ```
   - Sends multiple messages together
   - Impact: 10-50% faster

3. **Increase partitions**
   ```bash
   --partitions 30
   ```
   - More parallel processing
   - Impact: Scales with partitions

4. **Add page cache (RAM)**
   ```
   Current RAM: 32 GB → Upgrade to 64 GB
   ```
   - More data in fast RAM
   - Impact: 50-200% faster reads

5. **Use faster storage**
   ```
   Current: SATA SSD → Upgrade to NVMe
   ```
   - Faster disk I/O
   - Impact: 2-5x faster writes

**Configuration for maximum performance:**

**Producer:**
```properties
acks=1                    # Don't wait for all replicas
compression.type=lz4      # Fast compression
batch.size=32768          # Larger batches
linger.ms=10              # Wait 10ms to batch
buffer.memory=33554432    # Large send buffer
```

**Consumer:**
```properties
fetch.min.bytes=1048576   # Fetch 1 MB minimum
fetch.max.wait.ms=500     # Wait max 500ms
max.partition.fetch.bytes=1048576  # 1 MB per partition
```

**Broker:**
```properties
num.network.threads=8     # More network workers
num.io.threads=16         # More disk workers
```

**Trade-offs:**
| Optimization | Speed Gain | Risk |
|--------------|------------|------|
| acks=1 instead of all | 50-100% |  Can lose data |
| Large batches | 20-50% |  Higher latency |
| More partitions | Linear |  More overhead |

**For financial transactions:**
-  Enable compression (safe)
-  Add RAM (safe)
-  More partitions (safe)
-  Don't reduce acks (risky!)
-  Don't reduce replication (risky!)

---

##  Operational Questions

### Q18: Can I upgrade Kafka without downtime?

**Answer:**

**Yes! Using rolling restart.**

**Procedure:**

1. **Stop broker 1**
   ```bash
   ssh kafka1 'systemctl stop kafka'
   sleep 60
   ```

2. **Upgrade broker 1**
   ```bash
   ssh kafka1 'cd /tmp && wget new_kafka_version.tgz'
   ssh kafka1 'tar -xzf new_kafka_version.tgz'
   ssh kafka1 'mv /opt/kafka /opt/kafka.old'
   ssh kafka1 'mv kafka_new_version /opt/kafka'
   ```

3. **Start broker 1**
   ```bash
   ssh kafka1 'systemctl start kafka'
   sleep 60
   ```

4. **Verify broker 1 joined**
   ```bash
   kafka-broker-api-versions.sh --bootstrap-server kafka1:9092
   ```

5. **Repeat for broker 2 and 3**

**Requirements:**
-  Replication factor ≥ 3
-  No under-replicated partitions
-  Brokers are healthy

**Downtime:** Zero (if done correctly)

**Time required:** 15-30 minutes for 3 brokers

---

### Q19: Should I run Kafka in Docker/Kubernetes?

**Answer:**

**It depends on your needs.**

**Traditional VMs/Bare Metal (This Guide):**

**Pros:**
-  Simpler troubleshooting
-  Better performance (no container overhead)
-  Easier disk management
-  Lower learning curve

**Cons:**
-  Manual server management
-  Slower provisioning
-  No auto-scaling

**Docker/Kubernetes:**

**Pros:**
-  Easy deployment
-  Auto-scaling
-  Modern DevOps workflow

**Cons:**
-  More complex troubleshooting
-  Need persistent volumes
-  Additional overhead
-  Steep learning curve

**Recommendation:**

| Scenario | Use |
|----------|-----|
| **First Kafka deployment** | VMs/Bare metal |
| **Existing K8s infrastructure** | Kubernetes |
| **High-frequency trading** | Bare metal |
| **Microservices architecture** | Kubernetes |
| **Financial transactions** | VMs/Bare metal (this guide) |

**Why VMs for financial transactions:**
- More predictable performance
- Simpler compliance (fewer layers)
- Easier to meet SLAs

---

### Q20: How do I backup Kafka?

**Answer:**

**Three backup strategies:**

**1. MirrorMaker 2 (Best for production)**

Creates live copy in separate datacenter:

```
Primary Cluster → MirrorMaker 2 → DR Cluster
```

**Pros:**
-  Real-time backup
-  Can failover quickly
-  No data loss

**Cons:**
-  Requires second cluster
-  Double the cost

**2. Topic Export**

Export specific topics to files:

```bash
kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --from-beginning \
  > backup.txt
```

**Pros:**
-  Simple
-  Human-readable

**Cons:**
-  Slow for large topics
-  Stops at current message

**3. File System Snapshot**

Snapshot the data directories:

```bash
# Stop Kafka first!
systemctl stop kafka

# Backup
rsync -av /data/kafka/ /backup/kafka-$(date +%Y%m%d)/

# Restart Kafka
systemctl start kafka
```

**Pros:**
-  Complete cluster backup
-  Exact copy

**Cons:**
-  Requires downtime
-  Large storage needed

**Recommendation:**
- **For production:** MirrorMaker 2
- **For development:** File system snapshots
- **For specific data:** Topic export

See: [Disaster Recovery Guide](DISASTER_RECOVERY.md) for complete setup.

---

##  Getting More Help

**If your question isn't answered here:**

1. Check the [Operations Guide](OPERATIONS.md)
2. Check [Kafka Documentation](https://kafka.apache.org/documentation/)
3. Search [Stack Overflow](https://stackoverflow.com/questions/tagged/apache-kafka)
4. Ask the [Kafka Community](https://kafka.apache.org/contact)

---

**Last Updated:** January 31, 2026  
**Kafka Version:** 4.1.1  
**Maintained by:** Production Infrastructure Team
