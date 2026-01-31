# Complete Kafka Setup Guide
## Step-by-Step Installation with Simple Explanations

---

## Table of Contents

1. [Introduction - What We're Building](#introduction)
2. [Understanding the Basics](#understanding-the-basics)
3. [Before You Start](#before-you-start)
4. [Step 1: Prepare Your Servers](#step-1-prepare-your-servers)
5. [Step 2: Install Java](#step-2-install-java)
6. [Step 3: Download and Install Kafka](#step-3-download-and-install-kafka)
7. [Step 4: Configure Your Cluster](#step-4-configure-your-cluster)
8. [Step 5: Format and Start Kafka](#step-5-format-and-start-kafka)
9. [Step 6: Verify Everything Works](#step-6-verify-everything-works)
10. [Step 7: Create Your First Topic](#step-7-create-your-first-topic)
11. [Step 8: Test Message Flow](#step-8-test-message-flow)
12. [Next Steps](#next-steps)

---

## Introduction

### What We're Building

Imagine you're building a **super-reliable post office** for digital messages (financial transactions). This post office needs to:

- **Never lose a letter** (message) even if a building burns down
- **Deliver letters super fast** (in milliseconds)
- **Handle millions of letters per day**
- **Work 24/7 without stopping**

That's what we're building with Kafka!

### What is Kafka? (Simple Explanation)

**Kafka is like a super-powered message delivery system.**

Think of it like this:
- **Normal email:** You send a message directly to one person
- **Kafka:** You post a message to a topic (like a bulletin board), and many people can read it

**Real-world analogy:**
- You're a bank processing payments
- Each payment is a message
- Kafka ensures every payment is processed exactly once
- Even if servers crash, no payment is lost

### What is KRaft? (Our Architecture)

**KRaft is the "brain" of Kafka** - the new, modern way Kafka manages itself.

**Old way (ZooKeeper):**
- Like having a separate building to manage the post office
- More complex, two systems to maintain
- No longer supported (ended November 2025)

**New way (KRaft):**
- Kafka manages itself
- Simpler, faster, more reliable
- This is what we're using!

---

## Understanding the Basics

### Key Concepts Explained Simply

#### 1. **Broker** = A Kafka Server

Think of each broker as **one post office branch**.

- You'll have 3 brokers (3 post office branches)
- Each one can handle messages independently
- Together, they form a cluster (the whole post office network)

#### 2. **Topic** = A Category of Messages

Think of a topic as **a mailbox for specific types of mail**.

Examples:
- `payments` topic → All payment transactions
- `notifications` topic → All customer notifications
- `audit-logs` topic → All security logs

#### 3. **Partition** = A Sub-division of a Topic

Think of partitions as **different drawers in the mailbox**.

Why split into partitions?
- **Speed:** Multiple workers can process different drawers simultaneously
- **Organization:** Related messages stay together
- **Scalability:** More drawers = handle more messages

#### 4. **Replication** = Making Copies for Safety

Think of replication as **making photocopies of every letter**.

How it works:
- Every message is stored on 3 different servers
- If one server dies, you still have 2 copies
- Automatic: Kafka handles this for you

**Example:**
```
Message: "Payment $1000 from Account A to Account B"

Copy 1: Stored on Server 1 
Copy 2: Stored on Server 2 
Copy 3: Stored on Server 3 

If Server 1 crashes → You still have copies on Server 2 & 3!
```

#### 5. **Controller** = The Manager

Think of the controller as **the post office manager**.

What it does:
- Decides which server is in charge of which messages
- Handles failures (reassigns work if a server dies)
- Keeps everything organized

In KRaft:
- All 3 servers can be managers
- They vote on decisions (democracy!)
- If one manager dies, others take over (automatic)

---

## Before You Start

### What You Need

#### Hardware: 3 Servers

Each server needs:

| Item | Minimum | Why? |
|------|---------|------|
| **CPU** | 8 cores | Like having 8 workers processing messages |
| **RAM** | 32 GB | Memory to remember recent messages |
| **Disk** | 500 GB SSD | Storage for all messages |
| **Network** | 1 Gbps | Fast communication between servers |

 **Analogy:** Think of CPU as workers, RAM as short-term memory, Disk as filing cabinets, Network as roads between buildings.

#### Network Setup

Your 3 servers need names and addresses:

```
Server 1: kafka1 (192.168.1.101)
Server 2: kafka2 (192.168.1.102)
Server 3: kafka3 (192.168.1.103)
```

 **Note:** Replace these IP addresses with your actual server IPs!

#### Operating System

- RHEL 9, Oracle Linux 9, Rocky Linux 9, or AlmaLinux 9
- Fresh installation recommended
- Root access (admin permissions)

#### Your Computer

- SSH client (to connect to servers)
- Text editor (to view files)
- Basic terminal knowledge

---

##  Step 1: Prepare Your Servers

### What We're Doing

Before installing Kafka, we need to prepare our servers - like setting up a building before opening a post office.

### Why This Matters

Kafka needs special system settings to work well. Think of it like this:
- A race car needs special tuning to go fast
- Kafka needs special system settings to handle millions of messages

### Step 1.1: Set the Hostname

**What:** Give each server a name (kafka1, kafka2, kafka3)

**Why:** So servers can identify each other

**How:**

On Server 1:
```bash
sudo hostnamectl set-hostname kafka1
```

On Server 2:
```bash
sudo hostnamectl set-hostname kafka2
```

On Server 3:
```bash
sudo hostnamectl set-hostname kafka3
```

**What just happened?**
- You named each server
- Like putting a nameplate on each post office branch

### Step 1.2: Update Hosts File

**What:** Tell each server where the others are located

**Why:** Servers need to know how to find each other (like an address book)

**How:**

On ALL 3 servers, edit `/etc/hosts`:

```bash
sudo nano /etc/hosts
```

Add these lines:
```
192.168.1.101 kafka1
192.168.1.102 kafka2
192.168.1.103 kafka3
```

 **Remember:** Replace the IP addresses with YOUR server IPs!

**What just happened?**
- You created an address book
- Now when Server 1 says "call kafka2", it knows the phone number (IP)

### Step 1.3: Disable Swap (CRITICAL!)

**What:** Turn off swap memory

**Why:** Swap makes Kafka slow. Think of it like this:
- **RAM (memory):** Fast filing cabinet next to your desk
- **Swap:** Slow storage room in the basement
- We want Kafka to use only the fast cabinet!

**How:**

```bash
# Turn off swap immediately
sudo swapoff -a

# Make it permanent (so it stays off after reboot)
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

**What just happened?**
- Kafka will only use fast memory (RAM)
- This makes message processing much faster

### Step 1.4: Increase File Limits

**What:** Allow Kafka to open many files at once

**Why:** Kafka needs to open many files (like having many file drawers open simultaneously)

**How:**

Create a new file:
```bash
sudo nano /etc/security/limits.d/kafka.conf
```

Add these lines:
```
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
```

**What just happened?**
- You told the system: "Let Kafka open up to 100,000 files at once"
- Normal limit is only 1,024 - not enough for Kafka!

**Analogy:** Like giving a librarian permission to check out 100,000 books instead of just 1,000.

### Step 1.5: Tune Kernel Parameters

**What:** Adjust operating system settings for better performance

**Why:** Default settings are for normal computers, not high-performance message systems

**How:**

Edit system configuration:
```bash
sudo nano /etc/sysctl.conf
```

Add these lines at the end:
```bash
# Network Performance
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Don't swap unless absolutely necessary
vm.swappiness = 1

# File system optimizations
vm.max_map_count = 262144
fs.file-max = 2097152
```

Apply changes:
```bash
sudo sysctl -p
```

**What just happened?**

Let me explain each setting in simple terms:

1. **Network buffers (rmem/wmem):** 
   - Like making the post office's mail trucks bigger
   - Can carry more messages in one trip
   - Faster delivery!

2. **vm.swappiness = 1:**
   - Says "only use slow swap as last resort"
   - Keep everything in fast memory

3. **vm.max_map_count:**
   - How many memory maps Kafka can create
   - Like having more sorting tables in the post office

4. **fs.file-max:**
   - Total files the entire system can open
   - Needs to be high for Kafka

### Step 1.6: Configure Firewall

**What:** Open network ports so servers can communicate

**Why:** Servers need to talk to each other - like opening phone lines between post offices

**How:**

```bash
# Open Kafka ports
sudo firewall-cmd --permanent --add-port=9092/tcp  # Kafka broker
sudo firewall-cmd --permanent --add-port=9094/tcp  # Controller communication
sudo firewall-cmd --reload
```

**What just happened?**
- Port 9092: Where applications send/receive messages
- Port 9094: Where Kafka servers coordinate with each other

**Analogy:** 
- Port 9092 = Customer entrance
- Port 9094 = Staff entrance (for employees only)

### Step 1.7: Create Kafka User

**What:** Create a special user account for Kafka

**Why:** Security! Don't run Kafka as root (admin). Create a dedicated user.

**How:**

```bash
sudo useradd -r -s /bin/bash kafka
```

**What just happened?**
- Created a user named "kafka"
- This user will run the Kafka software
- Like hiring a dedicated post office manager

### Step 1.8: Create Data Directories

**What:** Create folders where Kafka stores messages

**Why:** Need organized storage - like building filing cabinets before opening for business

**How:**

```bash
# Create directories
sudo mkdir -p /data/kafka/logs
sudo mkdir -p /data/kafka/metadata
sudo mkdir -p /var/log/kafka

# Give ownership to kafka user
sudo chown -R kafka:kafka /data/kafka
sudo chown -R kafka:kafka /var/log/kafka
```

**What just happened?**

Created 3 important folders:
1. **/data/kafka/logs** → Stores actual messages (like filing cabinets for letters)
2. **/data/kafka/metadata** → Stores cluster information (like the manager's notebook)
3. **/var/log/kafka** → Stores system logs (like a diary of what happened)

---

##  Step 2: Install Java

### What We're Doing

Installing Java - the programming language Kafka is written in.

### Why This Matters

Kafka is built with Java, so Java must be installed first - like needing electricity before turning on lights.

### Step 2.1: Install Java 21 LTS

**How:**

```bash
# Install Java
cd /opt
wget https://download.bell-sw.com/java/21.0.10+10/bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
tar -xzf bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
mv /opt/jdk-21.0.10+10 /opt/jdk-21.0.10
export JAVA_HOME=/opt/jdk-21.0.10
export PATH=$JAVA_HOME/bin:$PATH

# Verify installation
java -version
```

You should see:
```
openjdk version "21.0.x"
```

**What just happened?**
- Installed Java 21 LTS (the recommended version)
- Verified it's working

### Step 2.2: Set JAVA_HOME

**What:** Tell the system where Java is installed

**Why:** Kafka needs to know where to find Java

**How:**

```bash
# Find Java location
dirname $(dirname $(readlink -f $(which java)))

# Set JAVA_HOME
echo 'export JAVA_HOME=/opt/jdk-21.0.10' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $JAVA_HOME
```

**What just happened?**
- Created a signpost pointing to Java
- Now Kafka knows where to find it

---

##  Step 3: Download and Install Kafka

### What We're Doing

Downloading and extracting Kafka software on all 3 servers.

### Step 3.1: Download Kafka

**How:**

```bash
# Go to temp directory
cd /tmp

# Download Kafka 4.1.1
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz

# Verify download (should see kafka_2.13-4.1.1.tgz)
ls -lh kafka_2.13-4.1.1.tgz
```

**What just happened?**
- Downloaded Kafka (about 100 MB)
- Like downloading the post office operating manual and software

### Step 3.2: Extract and Install

**How:**

```bash
# Extract the file
sudo tar -xzf kafka_2.13-4.1.1.tgz -C /opt/

# Rename for easier access
sudo mv /opt/kafka_2.13-4.1.1 /opt/kafka

# Give ownership to kafka user
sudo chown -R kafka:kafka /opt/kafka

# Verify installation
ls /opt/kafka
```

You should see folders like: `bin`, `config`, `libs`

**What just happened?**

Extracted Kafka to `/opt/kafka` with these important folders:
- **bin/** → Executable programs (like tools in a toolbox)
- **config/** → Configuration files (like instruction manuals)
- **libs/** → Supporting code libraries (like parts inventory)

**Analogy:** Like unpacking a new appliance and putting it in its permanent location.

---

##  Step 4: Configure Your Cluster

### What We're Doing

This is the most important step! We're creating the configuration files that tell Kafka how to work.

### Understanding the Configuration

Think of the configuration file as **the instruction manual** for your Kafka cluster. It tells each server:
- What its job is (broker? controller? both?)
- Who the other servers are
- Where to store data
- How to handle messages

### Step 4.1: Generate Cluster UUID

**What:** Create a unique ID for your cluster

**Why:** Like a birth certificate for your cluster - identifies it uniquely

**How:**

On **any ONE server** (only do this once):

```bash
/opt/kafka/bin/kafka-storage.sh random-uuid
```

You'll get something like:
```
7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
```

**IMPORTANT:** Save this! You'll need it on ALL 3 servers.

**What just happened?**
- Generated a unique ID for your cluster
- Like getting a license plate number

### Step 4.2: Configure Server 1 (kafka1)

**How:**

Edit the configuration file:
```bash
sudo -u kafka nano /opt/kafka/config/server.properties
```

**Replace everything** with this configuration:

```properties
# ============================================
# KAFKA NODE 1 CONFIGURATION
# ============================================

# ------------------------------------------
# SECTION 1: KRAFT SETUP (The Brain)
# ------------------------------------------

# What roles does this server have?
# broker = handles messages from applications
# controller = manages the cluster
# We're doing BOTH on each server
process.roles=broker,controller

# This server's unique ID (like an employee ID number)
node.id=1

# Who are all the controllers in the cluster?
# Format: ID@hostname:port
# We have 3 controllers (servers 1, 2, and 3)
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094

# ------------------------------------------
# SECTION 2: NETWORK CONFIGURATION
# ------------------------------------------

# How do clients and other servers connect to us?
# PLAINTEXT = no encryption (for internal network)
# 9092 = port for message traffic (like a loading dock)
# 9094 = port for controller traffic (like a management office)
listeners=PLAINTEXT://kafka1:9092,CONTROLLER://kafka1:9094

# What address should clients use to reach us?
# This is like your mailing address
advertised.listeners=PLAINTEXT://kafka1:9092

# Which network to use for broker-to-broker communication
inter.broker.listener.name=PLAINTEXT

# Which network to use for controller communication
controller.listener.names=CONTROLLER

# ------------------------------------------
# SECTION 3: DATA STORAGE
# ------------------------------------------

# Where to store messages (like filing cabinet location)
log.dirs=/data/kafka/logs

# Where to store cluster metadata (like manager's notebook)
metadata.log.dir=/data/kafka/metadata

# Cluster UUID (replace with YOUR cluster UUID!)
cluster.id=REPLACE_WITH_YOUR_CLUSTER_UUID

# ------------------------------------------
# SECTION 4: REPLICATION & SAFETY
# ------------------------------------------

# How many copies of each message? (Default for new topics)
# 3 = message stored on 3 different servers
default.replication.factor=3

# How many servers must confirm before we say "message saved"?
# 2 = at least 2 servers must confirm (including leader)
# This prevents data loss while maintaining speed
min.insync.replicas=2

# Consumer offset topic replication
# This is WHERE Kafka remembers which messages consumers have read
# CRITICAL: Must be 3 for your requirements!
offsets.topic.replication.factor=3

# Transaction log replication (for exactly-once processing)
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

# ------------------------------------------
# SECTION 5: CONSUMER OFFSETS CONFIGURATION
# ------------------------------------------

# How many partitions for the __consumer_offsets topic?
# More partitions = better performance with many consumer groups
offsets.topic.num.partitions=50

# How long to keep consumer offset data (in minutes)
# 10080 minutes = 7 days
# Even if consumer is offline for a week, it can resume
offsets.retention.minutes=10080

# ------------------------------------------
# SECTION 6: TOPIC DEFAULTS
# ------------------------------------------

# Default number of partitions for new topics
# 3 = messages split across 3 partitions for parallel processing
num.partitions=3

# Should Kafka auto-create topics when you write to them?
# false = must create topics manually (safer for production)
auto.create.topics.enable=false

# ------------------------------------------
# SECTION 7: PERFORMANCE TUNING
# ------------------------------------------

# Network threads (handle incoming connections)
# 8 = like having 8 receptionists at the front desk
num.network.threads=8

# I/O threads (handle reading/writing to disk)
# 16 = like having 16 workers in the filing room
num.io.threads=16

# Network buffer sizes (how much data to send at once)
# Bigger buffers = fewer trips, more efficient
socket.send.buffer.bytes=102400      # 100 KB send buffer
socket.receive.buffer.bytes=102400    # 100 KB receive buffer
socket.request.max.bytes=104857600    # 100 MB max request

# ------------------------------------------
# SECTION 8: DATA RETENTION
# ------------------------------------------

# How long to keep messages?
# 168 hours = 7 days (one week)
# After this, old messages are deleted
log.retention.hours=168

# How often to check for old messages to delete?
# 300000 ms = 5 minutes
log.retention.check.interval.ms=300000

# How big can one log file get before starting a new one?
# 1073741824 bytes = 1 GB
log.segment.bytes=1073741824

# How to clean up old data?
# delete = remove old messages after retention period
# compact = keep only latest value for each key
log.cleanup.policy=delete

# ------------------------------------------
# SECTION 9: COMPRESSION
# ------------------------------------------

# Default compression for messages
# lz4 = very fast, good compression (best for most use cases)
# Other options: none, gzip, snappy, zstd
compression.type=lz4
```

**Understanding Key Settings:**

Let me explain the most important settings in simple terms:

1. **node.id=1**
   - Like an employee ID
   - Server 1 = ID 1, Server 2 = ID 2, etc.

2. **replication.factor=3**
   - Every message stored 3 times
   - Can lose 1 server without losing data
   - Like making 3 photocopies of every document

3. **min.insync.replicas=2**
   - Need 2 servers to confirm write
   - Protects against data loss
   - Like requiring 2 signatures for important documents

4. **offsets.topic.replication.factor=3**
   - **THIS IS YOUR REQUIREMENT!**
   - Consumer offsets stored 3 times
   - Tracks which messages consumers have read

5. **num.partitions=3**
   - Split topics into 3 parts
   - Allows parallel processing
   - Like having 3 checkout lanes instead of 1

6. **log.retention.hours=168**
   - Keep messages for 7 days
   - After that, they're deleted (to save space)
   - Like throwing away old mail after a week

7. **compression.type=lz4**
   - Compress messages to save space
   - LZ4 is very fast with good compression
   - Like zip files for messages

### Step 4.3: Configure Server 2 (kafka2)

On Server 2, create the **same configuration** but change these lines:

```properties
# Change only these 3 lines:
node.id=2
listeners=PLAINTEXT://kafka2:9092,CONTROLLER://kafka2:9094
advertised.listeners=PLAINTEXT://kafka2:9092

# Everything else stays the same!
```

 **Key point:** Only the node ID and hostname change. All other settings are identical.

### Step 4.4: Configure Server 3 (kafka3)

On Server 3, create the **same configuration** but change these lines:

```properties
# Change only these 3 lines:
node.id=3
listeners=PLAINTEXT://kafka3:9092,CONTROLLER://kafka3:9094
advertised.listeners=PLAINTEXT://kafka3:9094

# Everything else stays the same!
```

---

##  Step 5: Format and Start Kafka

### What We're Doing

Preparing the storage and starting Kafka services.

### Step 5.1: Format Storage (ALL 3 Servers)

**What:** Initialize the data directories

**Why:** Like formatting a new hard drive before first use

**CRITICAL:** Use the SAME cluster UUID on ALL 3 servers!

**How:**

On **Server 1**:
```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g \
  -c /opt/kafka/config/server.properties
```

On **Server 2**:
```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g \
  -c /opt/kafka/config/server.properties
```

On **Server 3**:
```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g \
  -c /opt/kafka/config/server.properties
```

 **Remember:** Replace the UUID with YOUR cluster UUID from Step 4.1!

You should see:
```
Formatting /data/kafka/metadata with metadata.version 3.9-IV0.
```

**What just happened?**
- Prepared the data directories
- Wrote cluster information
- Like setting up the filing system before opening for business

### Step 5.2: Create Systemd Service

**What:** Create a service so Kafka starts automatically

**Why:** Makes Kafka start on boot and easy to manage

**How:**

On **ALL 3 servers**:

```bash
sudo nano /etc/systemd/system/kafka.service
```

Add this content:

```ini
[Unit]
Description=Apache Kafka Server (KRaft Mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=kafka
Group=kafka

# Where Java is installed
Environment="JAVA_HOME=/opt/jdk-21.0.10"

# How much memory for Kafka
Environment="KAFKA_HEAP_OPTS=-Xms6g -Xmx6g"

# Performance tuning
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20"

# Log directory
Environment="LOG_DIR=/var/log/kafka"

# Start command
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties

# Stop command
ExecStop=/opt/kafka/bin/kafka-server-stop.sh

# Auto-restart if it crashes
Restart=on-failure
RestartSec=10

# File and process limits
LimitNOFILE=100000
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
```

**Understanding the Service File:**

- **KAFKA_HEAP_OPTS=-Xms6g -Xmx6g**
  - Give Kafka 6 GB of memory
  - Like giving a worker 6 GB of desk space

- **Restart=on-failure**
  - If Kafka crashes, automatically restart it
  - Like having a backup generator

- **LimitNOFILE=100000**
  - Allow 100,000 open files
  - Remember we configured this earlier

### Step 5.3: Enable and Start Service

**How:**

On **ALL 3 servers**, run these commands:

```bash
# Reload systemd (so it sees the new service)
sudo systemctl daemon-reload

# Enable Kafka (start on boot)
sudo systemctl enable kafka

# Start Kafka NOW
sudo systemctl start kafka

# Check status
sudo systemctl status kafka
```

You should see:
```
 kafka.service - Apache Kafka Server (KRaft Mode)
   Loaded: loaded
   Active: active (running)
```

**What just happened?**

1. Kafka is now running!
2. It will auto-start if server reboots
3. It will auto-restart if it crashes

**Important:** Start servers one at a time, waiting 30 seconds between each:
1. Start Server 1 → Wait 30 seconds
2. Start Server 2 → Wait 30 seconds
3. Start Server 3 → Done!

---

##  Step 6: Verify Everything Works

### What We're Doing

Running tests to make sure the cluster is working correctly.

### Step 6.1: Check Cluster Status

**How:**

```bash
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 \
  describe --status
```

**What you should see:**

```
ClusterId:              7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
LeaderId:               1
LeaderEpoch:            2
HighWatermark:          152
MaxFollowerLag:         0
MaxFollowerLagTimeMs:   0
CurrentVoters:          [1,2,3]
CurrentObservers:       []
```

**What this means:**
-  All 3 servers are working
-  Server 1 is the current leader
-  No lag (everyone is caught up)

**Analogy:** Like checking all 3 post office branches are open and communicating.

### Step 6.2: List All Brokers

**How:**

```bash
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

**What you should see:**

```
kafka1:9092 (id: 1 rack: null)
kafka2:9092 (id: 2 rack: null)
kafka3:9092 (id: 3 rack: null)
```

**What this means:**
-  All 3 brokers are visible
-  They all have unique IDs
-  The cluster is healthy

### Step 6.3: Check Logs

**How:**

```bash
# View last 50 lines of log
sudo tail -50 /var/log/kafka/server.log

# Check for errors
sudo grep -i error /var/log/kafka/server.log

# Check for warnings
sudo grep -i warn /var/log/kafka/server.log
```

**What to look for:**
-  Should see "Kafka Server started"
-  Should see "Broker 1 has been successfully registered"
-  Should NOT see critical errors

---

## Step 7: Create Your First Topic

### What We're Doing

Creating a topic for storing messages. This is where your financial transactions will go!

### Understanding Topics

Remember: **A topic is like a mailbox for a specific type of message.**

For financial transactions, you might create:
- `payments` - For all payment messages
- `transfers` - For money transfers
- `audit-logs` - For audit trail

### Step 7.1: Create a Topic

**How:**

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

**Let me explain each parameter:**

- **--topic financial-transactions**
  - Name of your topic
  - Choose a meaningful name

- **--partitions 30**
  - Split topic into 30 partitions
  - More partitions = more parallelism
  - 30 is good for financial transactions

- **--replication-factor 3**
  - Store each message on 3 servers
  - **YOUR REQUIREMENT!**
  - Ensures high availability

- **--config min.insync.replicas=2**
  - Need 2 servers to confirm write
  - Protects against data loss
  - Best practice for financial data

- **--config retention.ms=604800000**
  - Keep messages for 7 days (604800000 milliseconds)
  - Adjust based on your needs
  - Financial data might need longer retention

- **--config compression.type=lz4**
  - Compress messages to save space
  - LZ4 is fast and efficient

**What just happened?**
- Created a topic named "financial-transactions"
- 30 partitions for parallel processing
- 3 copies of every message
- Retention set to 7 days

### Step 7.2: Verify Topic Creation

**How:**

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic financial-transactions
```

**What you should see:**

```
Topic: financial-transactions    PartitionCount: 30    ReplicationFactor: 3
  Partition: 0    Leader: 1    Replicas: 1,2,3    Isr: 1,2,3
  Partition: 1    Leader: 2    Replicas: 2,3,1    Isr: 2,3,1
  Partition: 2    Leader: 3    Replicas: 3,1,2    Isr: 3,1,2
  ...
```

**What this means:**
-  30 partitions created
-  Replication factor = 3
-  Every partition has 3 replicas
-  All replicas are in-sync (Isr)

**Understanding the output:**

- **Leader:** Which server is in charge of this partition
- **Replicas:** All servers storing this partition (1,2,3 = all three!)
- **Isr:** In-Sync Replicas (servers that are up-to-date)

### Step 7.3: Verify Consumer Offsets Topic

Remember your requirement: **__consumer_offsets must have replication factor 3**

**How:**

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic __consumer_offsets
```

**What you should see:**

```
Topic: __consumer_offsets    PartitionCount: 50    ReplicationFactor: 3
```

**What this means:**
-  Consumer offsets topic exists
-  Replication factor = 3 (YOUR REQUIREMENT MET!)
-  50 partitions (from our configuration)

**Important:** This topic is created automatically. You don't create it manually!

---

##  Step 8: Test Message Flow

### What We're Doing

Sending and receiving test messages to verify everything works end-to-end.

### Step 8.1: Send Test Messages (Producer)

**How:**

Open a terminal and run:

```bash
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions
```

Now type some test messages:

```
> Payment: $100 from Account A to Account B
> Payment: $250 from Account C to Account D
> Transfer: $1000 from Account E to Account F
```

Press Ctrl+C when done.

**What just happened?**
- You sent 3 messages to Kafka
- Each message was:
  - Stored on 3 different servers
  - Assigned to one of the 30 partitions
  - Compressed with LZ4
  - Confirmed by at least 2 servers

**Analogy:** Like mailing 3 letters that get automatically photocopied and stored in 3 different post offices.

### Step 8.2: Receive Test Messages (Consumer)

**How:**

Open a NEW terminal and run:

```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic financial-transactions \
  --from-beginning
```

**What you should see:**

```
Payment: $100 from Account A to Account B
Payment: $250 from Account C to Account D
Transfer: $1000 from Account E to Account F
```

Press Ctrl+C when done.

**What just happened?**
- You read messages from Kafka
- Messages delivered in order (within each partition)
- Even though messages stored on 3 servers, consumer got them once
- Your read position (offset) was stored in __consumer_offsets

**Analogy:** Like picking up mail from your mailbox - you get each letter once, even though copies exist in multiple locations.

### Step 8.3: Performance Test (Optional)

**How:**

Test producer throughput:

```bash
/opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic financial-transactions \
  --num-records 1000000 \
  --record-size 1024 \
  --throughput -1 \
  --producer-props \
    bootstrap.servers=kafka1:9092 \
    acks=all \
    compression.type=lz4
```

**What you should see:**

```
1000000 records sent, 50000 records/sec (48.83 MB/sec)
```

**What this means:**
-  Cluster can handle 50,000+ messages per second
-  That's over 180 million messages per hour!
-  More than enough for financial transactions

---

##  Next Steps

### Congratulations! 

You now have a production-ready Kafka cluster running!

**What you've accomplished:**

 3-node Kafka cluster with KRaft  
 High availability (survives 1 server failure)  
 Data replication (3 copies of everything)  
 Consumer offsets replicated 3 times (**YOUR REQUIREMENT!**)  
 Performance tested and verified  

### What to Do Now

#### Immediate Tasks (This Week)

1. **Set Up Monitoring**
   - See: [Operations Guide](05-operations-guide.md)
   - Monitor cluster health daily
   - Set up alerts for issues

2. **Configure Security**
   - See: [Security Guide](13-security-guide.md)
   - Enable SSL/TLS encryption
   - Set up authentication (SASL)
   - Configure access controls (ACLs)

3. **Create Your Real Topics**
   - Design your topic structure
   - Set appropriate retention policies
   - Configure compression

#### Short-Term Tasks (Next Month)

4. **Set Up Disaster Recovery**
   - See: [Disaster Recovery Guide](06-disaster-recovery.md)
   - Configure MirrorMaker 2 for backup cluster
   - Test failover procedures
   - Document recovery processes

5. **Performance Tuning**
   - See: [Performance Guide](14-performance-tuning.md)
   - Optimize based on your workload
   - Monitor and adjust

6. **Connect Your Applications**
   - See: [Application Integration Guide](15-application-integration.md)
   - Configure producers
   - Configure consumers
   - Test thoroughly

#### Long-Term Tasks (Ongoing)

7. **Regular Maintenance**
   - Daily health checks
   - Weekly performance reviews
   - Monthly capacity planning
   - Quarterly disaster recovery drills

8. **Team Training**
   - Train operations team
   - Document procedures
   - Create runbooks
   - Schedule on-call rotation

### Learning Resources

- **[Operations Guide](05-operations-guide.md)** - Daily operations
- **[Troubleshooting Guide](09-troubleshooting.md)** - Common issues
- **[Commands Cheat Sheet](08-commands-cheatsheet.md)** - Quick reference
- **[FAQ](10-faq.md)** - Frequently asked questions

### Getting Help

If you encounter issues:

1. Check the **[Troubleshooting Guide](09-troubleshooting.md)**
2. Review the **logs** (`/var/log/kafka/server.log`)
3. Check the **[FAQ](10-faq.md)**
4. Consult Apache Kafka documentation

---

##  Summary Checklist

Use this checklist to verify your installation:

### System Preparation
- [ ] All 3 servers have correct hostnames
- [ ] `/etc/hosts` configured on all servers
- [ ] Swap disabled on all servers
- [ ] File limits increased
- [ ] Kernel parameters tuned
- [ ] Firewall configured
- [ ] Kafka user created
- [ ] Data directories created

### Software Installation
- [ ] Java 21 LTS installed on all servers
- [ ] JAVA_HOME set correctly
- [ ] Kafka downloaded and extracted
- [ ] Permissions set correctly

### Configuration
- [ ] Cluster UUID generated
- [ ] server.properties configured on Server 1
- [ ] server.properties configured on Server 2
- [ ] server.properties configured on Server 3
- [ ] All configs use SAME cluster UUID
- [ ] offsets.topic.replication.factor=3 

### Service Setup
- [ ] Systemd service created on all servers
- [ ] Storage formatted on all servers
- [ ] Services enabled on all servers
- [ ] Services started successfully

### Verification
- [ ] All 3 brokers visible
- [ ] Cluster status shows 3 voters
- [ ] No errors in logs
- [ ] Test topic created successfully
- [ ] Messages sent and received successfully
- [ ] __consumer_offsets has replication factor 3 

### Production Readiness
- [ ] Monitoring configured
- [ ] Security configured
- [ ] Backup strategy implemented
- [ ] Operations team trained
- [ ] Documentation complete

---

##  Key Concepts Summary

### What You've Learned

1. **Kafka Basics**
   - Topics, Partitions, Replication
   - Brokers and Controllers
   - Producers and Consumers

2. **KRaft Architecture**
   - Why it's better than ZooKeeper
   - How controller quorum works
   - Self-managing cluster

3. **High Availability**
   - Replication factor = 3
   - min.insync.replicas = 2
   - Automatic failover

4. **Configuration**
   - Critical settings and why they matter
   - Performance tuning
   - Safety vs. speed tradeoffs

### Key Takeaways

 **Replication = Safety**
- 3 copies = survive 1 failure
- 2 confirmations = no data loss

 **Partitions = Speed**
- More partitions = more parallelism
- But don't overdo it (30-50 is good)

 **Retention = Storage**
- Longer retention = more disk space
- Balance business needs with cost

 **Monitoring = Peace of Mind**
- Watch cluster health daily
- Alert on problems early
- Prevent issues before they happen

---

**Congratulations on completing the setup!** 

You now have enterprise-grade Kafka infrastructure ready for financial transactions.

---

*Last Updated: January 31, 2026*  
*Version: 1.0*  
*Kafka: 4.1.1 (KRaft Mode)*
