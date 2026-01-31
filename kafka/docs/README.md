# Apache Kafka 4.1.1 Production Setup Guide
## Complete Step-by-Step Guide for Financial Transactions

[![Kafka Version](https://img.shields.io/badge/Kafka-4.1.1-brightgreen)](https://kafka.apache.org/)
[![Architecture](https://img.shields.io/badge/Architecture-KRaft-blue)](https://kafka.apache.org/documentation/#kraft)
[![Java](https://img.shields.io/badge/Java-17-orange)](https://openjdk.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

---

## Table of Contents

1. [What is This Guide?](#what-is-this-guide)
2. [What You'll Build](#what-youll-build)
3. [Prerequisites](#prerequisites)
4. [Understanding Kafka Basics](#understanding-kafka-basics)
5. [Step-by-Step Installation](#step-by-step-installation)
6. [Configuration Explained](#configuration-explained)
7. [Starting Your Cluster](#starting-your-cluster)
8. [Testing and Verification](#testing-and-verification)
9. [Daily Operations](#daily-operations)
10. [Troubleshooting](#troubleshooting)
11. [Security Setup](#security-setup)
12. [Monitoring](#monitoring)
13. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
14. [Performance Tuning](#performance-tuning)
15. [Frequently Asked Questions](#frequently-asked-questions)

---

## What is This Guide?

This guide helps you set up **Apache Kafka 4.1.1** with **KRaft** (no ZooKeeper) for handling **financial transactions** in a production environment.

### Who This Guide Is For
- System administrators deploying Kafka
- DevOps engineers managing infrastructure
- Developers wanting to understand Kafka setup
- Non-technical managers overseeing the project

### What Makes This Guide Different
-  **Simple explanations** - No jargon, clear language
-  **Copy-paste ready** - All commands and configs ready to use
-  **Production-grade** - Designed for financial transactions
-  **Step-by-step** - Nothing assumed, everything explained
-  **Tested** - Based on real production deployments

---

## What You'll Build

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR KAFKA CLUSTER                       │
│                                                             │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐         │
│  │  Node 1  │      │  Node 2  │      │  Node 3  │         │
│  │  kafka1  │────│  kafka2  │────│  kafka3  │         │
│  │          │      │          │      │          │         │
│  │ Broker 1 │      │ Broker 2 │      │ Broker 3 │         │
│  │Controller│      │Controller│      │Controller│         │
│  └──────────┘      └──────────┘      └──────────┘         │
│                                                             │
│   Data is automatically copied to all 3 nodes            │
│   If 1 node fails, others keep working                   │
│   No single point of failure                             │
└─────────────────────────────────────────────────────────────┘
```

### What This Cluster Gives You

**High Availability** 
- If one server fails, the other two keep working
- Your applications never stop
- Data is never lost

**Data Safety** 
- Every message stored on 3 servers
- Even if 1 server dies, you have 2 copies
- Perfect for financial transactions

**Performance** 
- Handles millions of messages per second
- Low latency (messages arrive in milliseconds)
- Scales as your business grows

---

## Prerequisites

### Hardware Requirements (Per Server)

Think of this like buying a car - you need the right engine for highway driving:

| Component | What It Is | Minimum | Recommended | Why |
|-----------|------------|---------|-------------|-----|
| **CPU** | Computer's brain | 8 cores | 16-24 cores | More cores = faster processing |
| **RAM** | Short-term memory | 32 GB | 64 GB | More RAM = better performance |
| **Storage** | Hard drive space | 500 GB SSD | 1-2 TB NVMe | Fast storage = quick data access |
| **Network** | Internet speed | 1 Gbps | 10 Gbps | Faster network = quicker data transfer |

**Simple Explanation:**
- **CPU cores**: Like having more workers in a factory
- **RAM**: Like having a bigger desk to work on
- **Storage**: Like having a bigger, faster filing cabinet
- **Network**: Like having a wider highway for data

### Software Requirements

| Software | Version | What It Does |
|----------|---------|--------------|
| **Operating System** | RHEL 9 / Oracle Linux 9 / Rocky Linux 9 | The foundation (like Windows, but for servers) |
| **Java** | Java 21 LTS | The engine that runs Kafka |
| **Kafka** | 4.1.1 | The actual Kafka software |

### Network Requirements

You'll need **3 servers** that can talk to each other:

```
Server 1 (kafka1): 192.168.1.101
Server 2 (kafka2): 192.168.1.102
Server 3 (kafka3): 192.168.1.103
```

**Simple Explanation:** These IP addresses are like phone numbers - each server has one so they can communicate.

### What You Need Before Starting

- [ ] 3 physical or virtual servers with the specs above
- [ ] Access to all 3 servers (username/password or SSH key)
- [ ] Root/administrator access on all servers
- [ ] All servers can "ping" each other (can communicate)
- [ ] Firewall allows connections on ports 9092, 9093, 9094

---

## Understanding Kafka Basics

Before we start, let's understand what Kafka actually does (in simple terms).

### What is Kafka?

**Think of Kafka as a super-fast, reliable postal service for your applications.**

```
┌──────────────┐                    ┌──────────────┐
│  Application │─── Message ───   │  Application │
│   (Sender)   │                    │  (Receiver)  │
└──────────────┘                    └──────────────┘
                                           
      │                                     │
      └────────── Kafka stores and delivers ─┘
```

**Real-World Example:**
- Bank app sends: "Transfer $100 from Account A to Account B"
- Kafka receives and stores this message safely
- Payment processor receives the message and executes the transfer
- Even if payment processor is offline, Kafka keeps the message safe

### Key Concepts (Simple Explanations)

**1. Topics** 
- **What:** Categories for your messages (like folders)
- **Example:** `financial-transactions`, `user-logins`, `order-payments`
- **Like:** Different mailboxes for different types of mail

**2. Partitions**
- **What:** Splits in a topic for better performance
- **Example:** Topic with 30 partitions = 30 separate "lanes" for messages
- **Like:** Multiple checkout lanes at a grocery store (faster processing)

**3. Brokers** 
- **What:** The servers that store and serve data
- **Example:** Your 3 servers (kafka1, kafka2, kafka3) are all brokers
- **Like:** Multiple post offices working together

**4. Replication** 
- **What:** Copying data to multiple servers
- **Example:** Each message stored on 3 servers
- **Like:** Making photocopies of important documents

**5. Controllers** 
- **What:** The "manager" that coordinates the cluster
- **Example:** Decides which broker is the leader for each partition
- **Like:** A manager assigning tasks to workers

### Why KRaft? (Simple Explanation)

**Old Way (ZooKeeper):**
```
Kafka Cluster + Separate ZooKeeper Cluster = 2 systems to manage 
```

**New Way (KRaft):**
```
Kafka Cluster with built-in coordination = 1 system to manage 
```

**Benefits:**
- Simpler (less to manage)
- Cheaper (fewer servers needed)
- Faster (no external communication)
- More reliable (fewer things to break)

---

## Step-by-Step Installation

### Overview of What We'll Do

```
Step 1: Prepare servers      (Clean and configure operating system)
Step 2: Install Java          (Kafka needs Java to run)
Step 3: Download Kafka        (Get the Kafka software)
Step 4: Configure system      (Optimize for performance)
Step 5: Set up Kafka          (Configure Kafka itself)
Step 6: Start services        (Turn everything on)
Step 7: Verify                (Make sure it works)
```

**Time Required:** 2-3 hours for all 3 servers

---

### Step 1: Prepare Servers (30 minutes)

**What we're doing:** Getting the servers ready for Kafka installation.

**On ALL 3 servers, do the following:**

#### 1.1 Update Hostname

This gives each server a friendly name.

```bash
# On Server 1
sudo hostnamectl set-hostname kafka1

# On Server 2
sudo hostnamectl set-hostname kafka2

# On Server 3
sudo hostnamectl set-hostname kafka3
```

**What this does:** Changes the server name from something like `localhost` to `kafka1`, making it easier to identify.

#### 1.2 Update /etc/hosts File

This creates a "phonebook" so servers can find each other by name.

```bash
# On ALL servers, add these lines to /etc/hosts
sudo tee -a /etc/hosts <<EOF
192.168.1.101 kafka1
192.168.1.102 kafka2
192.168.1.103 kafka3
EOF
```

**What this does:** Maps server names to IP addresses (like adding contacts to your phone).

#### 1.3 Verify Connectivity

Make sure servers can talk to each other.

```bash
# On kafka1, test connection to others
ping -c 3 kafka2
ping -c 3 kafka3

# On kafka2, test connection to others
ping -c 3 kafka1
ping -c 3 kafka3

# On kafka3, test connection to others
ping -c 3 kafka1
ping -c 3 kafka2
```

**What to expect:** You should see responses like `64 bytes from kafka2...`. If you see `"Destination Host Unreachable"`, there's a network problem.

---

### Step 2: Install Java (15 minutes)

**What we're doing:** Installing Java 21 LTS, which Kafka needs to run.

**Think of Java as:** The engine that makes Kafka work (like a car needs an engine).

#### 2.1 Install Java

```bash
# On ALL 3 servers
cd /opt
wget https://download.bell-sw.com/java/21.0.10+10/bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
tar -xzf bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
mv /opt/jdk-21.0.10+10 /opt/jdk-21.0.10
export JAVA_HOME=/opt/jdk-21.0.10
export PATH=$JAVA_HOME/bin:$PATH
```

**What this does:** Downloads and installs Java from the internet.

#### 2.2 Verify Java Installation

```bash
java -version
```

**What to expect:** Should show something like:
```
openjdk version "21.0.x"
```

#### 2.3 Set JAVA_HOME

This tells the system where Java is installed.

```bash
# Add to ~/.bashrc on ALL servers
echo 'export JAVA_HOME=/opt/jdk-21.0.10' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $JAVA_HOME
```

**What to expect:** Should print `/opt/jdk-21.0.10`

---

### Step 3: Download and Install Kafka (20 minutes)

**What we're doing:** Getting the Kafka software and putting it in the right place.

#### 3.1 Create Kafka User

For security, we create a special user just for Kafka.

```bash
# On ALL 3 servers
sudo useradd -r -s /bin/bash kafka
```

**What this does:** Creates a new user account named `kafka` (like creating a new user on your computer).

#### 3.2 Download Kafka

```bash
# On ALL 3 servers
cd /tmp
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz
```

**What this does:** Downloads Kafka from the official Apache website (like downloading software from the internet).

**Time:** 2-5 minutes depending on internet speed.

#### 3.3 Verify Download (Important!)

This makes sure the download wasn't corrupted.

```bash
# Download checksum file
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz.sha512

# Verify
sha512sum -c kafka_2.13-4.1.1.tgz.sha512
```

**What to expect:** Should say `kafka_2.13-4.1.1.tgz: OK`

**If it fails:** Download again (file might be corrupted).

#### 3.4 Extract Kafka

```bash
# On ALL 3 servers
sudo tar -xzf kafka_2.13-4.1.1.tgz -C /opt/
sudo mv /opt/kafka_2.13-4.1.1 /opt/kafka
sudo chown -R kafka:kafka /opt/kafka
```

**What this does:**
- `tar -xzf`: Unzips the file (like unzipping a .zip file)
- `mv`: Moves and renames the folder
- `chown`: Gives ownership to the kafka user

#### 3.5 Create Data Directories

Kafka needs places to store its data.

```bash
# On ALL 3 servers
sudo mkdir -p /data/kafka/logs /data/kafka/metadata /var/log/kafka
sudo chown -R kafka:kafka /data/kafka /var/log/kafka
```

**What this creates:**
- `/data/kafka/logs`: Where actual message data is stored
- `/data/kafka/metadata`: Where cluster coordination data is stored
- `/var/log/kafka`: Where Kafka writes log files

---

### Step 4: Configure System (30 minutes)

**What we're doing:** Optimizing the operating system for Kafka's needs.

**Think of this as:** Tuning a race car's engine for maximum performance.

#### 4.1 Set File Limits

Kafka opens many files at once. We need to increase the limit.

```bash
# On ALL 3 servers
sudo tee /etc/security/limits.d/kafka.conf <<EOF
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
kafka soft memlock unlimited
kafka hard memlock unlimited
EOF
```

**What this does:**
- `nofile`: Number of files that can be open (100,000)
- `nproc`: Number of processes (32,768)
- `memlock`: Memory that can be locked (unlimited)

**Simple explanation:** Like increasing your car's fuel tank size so it can go further.

#### 4.2 Optimize Kernel Parameters

These settings improve network and disk performance.

```bash
# On ALL 3 servers
sudo tee -a /etc/sysctl.conf <<EOF

# Kafka Performance Tuning
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65000
net.core.somaxconn = 4096
vm.swappiness = 1
vm.dirty_ratio = 80
vm.dirty_background_ratio = 5
vm.max_map_count = 262144
fs.file-max = 2097152
EOF

# Apply changes
sudo sysctl -p
```

**What each setting does:**
- `rmem_max/wmem_max`: Network buffer sizes (bigger = more data in flight)
- `tcp_*`: TCP connection settings (faster network)
- `vm.swappiness`: Use disk instead of RAM (set to 1 = almost never)
- `fs.file-max`: Maximum number of files (very high)

**Simple explanation:** Like upgrading your network cables from slow to fast.

#### 4.3 Disable Swap

Swap makes Kafka slow. We turn it off.

```bash
# On ALL 3 servers
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

**What this does:** Prevents the operating system from using slow disk instead of fast RAM.

**Simple explanation:** Like making sure your computer only uses fast memory, not slow hard drive space.

#### 4.4 Configure Firewall

Open the ports Kafka needs to communicate.

```bash
# On ALL 3 servers
sudo firewall-cmd --permanent --add-port=9092/tcp  # Client connections
sudo firewall-cmd --permanent --add-port=9093/tcp  # SSL connections
sudo firewall-cmd --permanent --add-port=9094/tcp  # Controller communication
sudo firewall-cmd --permanent --add-port=9999/tcp  # Monitoring (JMX)
sudo firewall-cmd --reload
```

**What this does:** Opens "doorways" in the firewall so Kafka can communicate.

**Simple explanation:** Like opening specific doors in a building so people can enter.

---

### Step 5: Configure Kafka (45 minutes)

**What we're doing:** Setting up Kafka's configuration file.

This is the most important step - we're telling Kafka how to behave.

#### 5.1 Generate Cluster UUID (ONCE, on any server)

This creates a unique ID for your entire cluster.

```bash
# Run this ONCE on kafka1
/opt/kafka/bin/kafka-storage.sh random-uuid
```

**What to expect:** A long string like: `7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g`

**IMPORTANT:** Save this UUID! You'll need it on ALL three servers.

**Think of UUID as:** Your cluster's social security number - unique identifier.

#### 5.2 Create Configuration Files

We'll create the main configuration file for each server.

**On SERVER 1 (kafka1):**

```bash
sudo tee /opt/kafka/config/server.properties <<'EOF'
########################## KRaft Mode Configuration ##########################
# This tells Kafka to run in KRaft mode (no ZooKeeper)
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094

########################## Network Settings ##########################
# Where this broker listens for connections
listeners=PLAINTEXT://kafka1:9092,CONTROLLER://kafka1:9094
advertised.listeners=PLAINTEXT://kafka1:9092
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER

########################## Storage Settings ##########################
# Where Kafka stores data
log.dirs=/data/kafka/logs
metadata.log.dir=/data/kafka/metadata

########################## Cluster Configuration ##########################
# Unique ID for this cluster (REPLACE WITH YOUR UUID!)
cluster.id=REPLACE_WITH_YOUR_CLUSTER_UUID

########################## Replication Settings ##########################
# How many copies of data to keep
default.replication.factor=3
min.insync.replicas=2

# Consumer offset storage (CRITICAL for your requirement!)
offsets.topic.replication.factor=3
offsets.topic.num.partitions=50
offsets.retention.minutes=10080

# Transaction log settings
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

########################## Topic Defaults ##########################
# Default number of partitions for new topics
num.partitions=3
auto.create.topics.enable=false

########################## Performance Settings ##########################
# Network and I/O threads
num.network.threads=8
num.io.threads=16

# Socket settings
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

########################## Log Retention ##########################
# How long to keep data (168 hours = 7 days)
log.retention.hours=168
log.retention.check.interval.ms=300000
log.segment.bytes=1073741824
log.cleanup.policy=delete

########################## Compression ##########################
# Use LZ4 compression (fast and efficient)
compression.type=lz4
EOF
```

**On SERVER 2 (kafka2):**

```bash
# Same as kafka1, but change these three lines:
node.id=2
listeners=PLAINTEXT://kafka2:9092,CONTROLLER://kafka2:9094
advertised.listeners=PLAINTEXT://kafka2:9092
```

**On SERVER 3 (kafka3):**

```bash
# Same as kafka1, but change these three lines:
node.id=3
listeners=PLAINTEXT://kafka3:9092,CONTROLLER://kafka3:9094
advertised.listeners=PLAINTEXT://kafka3:9092
```

#### 5.3 Configuration Explained (Simple Terms)

Let's understand what each important setting means:

**KRaft Settings:**
```properties
process.roles=broker,controller
```
- **What:** This server acts as both data storage (broker) and coordinator (controller)
- **Like:** A worker who is also a manager

```properties
node.id=1
```
- **What:** Unique number for this server (1, 2, or 3)
- **Like:** Employee ID number

```properties
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094
```
- **What:** List of all controllers in the cluster
- **Like:** List of all managers who vote on decisions

**Replication Settings:**
```properties
default.replication.factor=3
```
- **What:** Store 3 copies of every message (one on each server)
- **Like:** Making 2 photocopies of important documents

```properties
min.insync.replicas=2
```
- **What:** Need 2 copies confirmed before considering a write successful
- **Like:** Needing 2 signatures to approve a transaction

**Consumer Offset Settings:**
```properties
offsets.topic.replication.factor=3
```
- **What:** The `__consumer_offsets` topic (tracks what messages were read) also has 3 copies
- **Why:** This was your specific requirement!

**Performance Settings:**
```properties
num.network.threads=8
num.io.threads=16
```
- **What:** Number of workers handling network and disk operations
- **Like:** Having 8 cashiers and 16 stockroom workers

#### 5.4 Set File Permissions

```bash
# On ALL 3 servers
sudo chown kafka:kafka /opt/kafka/config/server.properties
```

---

### Step 6: Format Storage (15 minutes)

**What we're doing:** Preparing Kafka's storage (like formatting a hard drive before first use).

**IMPORTANT:** Do this BEFORE starting Kafka for the first time!

```bash
# On kafka1
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t YOUR_CLUSTER_UUID_HERE \
  -c /opt/kafka/config/server.properties

# On kafka2
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t YOUR_CLUSTER_UUID_HERE \
  -c /opt/kafka/config/server.properties

# On kafka3
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t YOUR_CLUSTER_UUID_HERE \
  -c /opt/kafka/config/server.properties
```

**What to expect:** Should see message: `Formatting /data/kafka/metadata with metadata.version 3.9-IV0`

**What this does:** Initializes the storage directories with proper structure.

---

### Step 7: Create Systemd Service (20 minutes)

**What we're doing:** Creating a service so Kafka starts automatically.

**Think of systemd as:** Like setting an app to start automatically when you turn on your computer.

#### 7.1 Create Service File

```bash
# On ALL 3 servers
sudo tee /etc/systemd/system/kafka.service <<'EOF'
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
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M"
Environment="LOG_DIR=/var/log/kafka"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10
LimitNOFILE=100000
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF
```

**What these settings mean:**

```properties
KAFKA_HEAP_OPTS=-Xms6g -Xmx6g
```
- **What:** Allocate 6 GB of RAM to Kafka
- **Why:** More memory = better performance
- **Like:** Giving Kafka a 6 GB workspace

```properties
Restart=on-failure
```
- **What:** If Kafka crashes, automatically restart it
- **Like:** Auto-restart feature on your phone

#### 7.2 Enable Service

```bash
# On ALL 3 servers
sudo systemctl daemon-reload
sudo systemctl enable kafka
```

**What this does:** 
- `daemon-reload`: Tells systemd to read the new service file
- `enable`: Sets Kafka to start automatically on boot

---

## Starting Your Cluster

**What we're doing:** Turning on Kafka for the first time!

**Important:** Start servers ONE AT A TIME, waiting 30 seconds between each.

### Step 1: Start First Server

```bash
# On kafka1
sudo systemctl start kafka

# Check if it started successfully
sudo systemctl status kafka
```

**What to expect:**
- Should see `Active: active (running)` in green
- If you see `Failed`, check the logs: `sudo journalctl -u kafka -n 50`

### Step 2: Wait 30 Seconds

This gives the first server time to initialize.

```bash
sleep 30
```

### Step 3: Start Second Server

```bash
# On kafka2
sudo systemctl start kafka
sudo systemctl status kafka
```

### Step 4: Wait 30 Seconds

```bash
sleep 30
```

### Step 5: Start Third Server

```bash
# On kafka3
sudo systemctl start kafka
sudo systemctl status kafka
```

### Step 6: Verify All Servers Are Running

```bash
# On any server
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

**What to expect:** Should list all 3 brokers (kafka1, kafka2, kafka3)

**If only 2 brokers show up:** Wait another 30 seconds and try again. The third might still be joining.

---

## Testing and Verification

**What we're doing:** Making sure everything works correctly.

### Test 1: Check Cluster Metadata

```bash
/opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server kafka1:9092 describe --status
```

**What to expect:** Should show all 3 nodes with one as the leader.

**Example output:**
```
NodeId  LogEndOffset  Lag  LastFetchTimestamp  LastCaughtUpTimestamp  Status
1       100           0    1234567890          1234567890             Leader
2       100           0    1234567890          1234567890             Follower
3       100           0    1234567890          1234567890             Follower
```

### Test 2: Create a Test Topic

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic test-topic \
  --partitions 3 \
  --replication-factor 3
```

**What this does:** Creates a topic named `test-topic` with 3 partitions and 3 copies.

**What to expect:** `Created topic test-topic.`

### Test 3: Verify Topic Configuration

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic test-topic
```

**What to expect:**
```
Topic: test-topic  PartitionCount: 3  ReplicationFactor: 3
  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3
  Partition: 1  Leader: 2  Replicas: 2,3,1  Isr: 2,3,1
  Partition: 2  Leader: 3  Replicas: 3,1,2  Isr: 3,1,2
```

**What this means:**
- Each partition has a different leader
- Each partition is on all 3 servers (Replicas: 1,2,3)
- All replicas are in-sync (Isr: 1,2,3)

### Test 4: Send Test Messages

```bash
# Send some test messages
echo "Test message 1" | /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic

echo "Test message 2" | /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic
```

### Test 5: Receive Test Messages

```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic \
  --from-beginning
```

**What to expect:** Should see your test messages printed out.

**Press Ctrl+C to stop the consumer.**

### Test 6: Verify Consumer Offsets Topic

This verifies your requirement that `__consumer_offsets` has replication factor of 3.

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic __consumer_offsets
```

**What to expect:**
```
Topic: __consumer_offsets  PartitionCount: 50  ReplicationFactor: 3
```

**If you see `ReplicationFactor: 3`, your requirement is met!**

### Test 7: Clean Up Test Topic

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --delete \
  --topic test-topic
```

---

## Congratulations!

**Your Kafka cluster is now running!**

You now have:
- 3-node Kafka cluster using KRaft
- High availability (can tolerate 1 node failure)
- Data replication (3 copies of everything)
- Consumer offsets with replication factor 3
- Production-ready configuration

---

## Next Steps

1. **Read:** [Daily Operations Guide](docs/OPERATIONS.md)
2. **Set up:** [Monitoring and Alerting](docs/MONITORING.md)
3. **Configure:** [Security (SSL/SASL)](docs/SECURITY.md)
4. **Plan:** [Disaster Recovery](docs/DISASTER_RECOVERY.md)
5. **Optimize:** [Performance Tuning](docs/PERFORMANCE.md)

---

## Getting Help

- **Kafka Documentation:** https://kafka.apache.org/documentation/
- **KRaft Guide:** https://kafka.apache.org/documentation/#kraft
- **Community:** https://kafka.apache.org/contact

---

## License

This guide is provided under the Apache License 2.0.

---

**Last Updated:** January 31, 2026  
**Kafka Version:** 4.1.1  
**Author:** Production Infrastructure Team
