# Step-by-Step Installation Guide
## Complete Kafka 4.1.1 KRaft Cluster Setup

---

##  Overview

**What You're Building:**
- 3 Kafka servers working together as one cluster
- Each server can handle requests (High Availability)
- Data replicated 3 times (No Data Loss)
- Automatic failover (Fault Tolerance)

**Time Required:** ~5 hours first time, ~2 hours after practice

**Difficulty Level:** Intermediate (We'll guide you through every step!)

---

##  Before You Start

### What You Need

**3 Servers with:**
- Operating System: RHEL 9.x / Rocky Linux 9.x / AlmaLinux 9.x / Oracle Linux 9.x
- CPU: 16+ cores (minimum 8)
- RAM: 64 GB (minimum 32 GB)
- Disk: 1-2 TB NVMe SSD
- Network: 10 Gbps (minimum 1 Gbps)

**Network Setup:**
```
Server 1 (kafka1): 192.168.1.101
Server 2 (kafka2): 192.168.1.102
Server 3 (kafka3): 192.168.1.103
```

**Access Requirements:**
- Root or sudo access to all 3 servers
- SSH access to all servers
- Internet connectivity (for downloading Kafka)

**Knowledge Required:**
- Basic Linux command line
- Basic text editor (vi or nano)
- SSH usage

---

##  Installation Process

The installation has 10 major phases:

1. **Prepare Operating System** (30 min per server)
2. **Install Java** (10 min per server)
3. **Tune System Settings** (20 min per server)
4. **Download Kafka** (10 min total)
5. **Configure Kafka** (30 min per server)
6. **Format Storage** (5 min per server)
7. **Create Systemd Service** (10 min per server)
8. **Start Cluster** (15 min total)
9. **Verify Installation** (20 min total)
10. **Test High Availability** (30 min total)

**Total Time:** Approximately 5 hours

---

## PHASE 1: Prepare Operating System

### Why This Matters
Before installing Kafka, we need to prepare the operating system to handle high-performance operations. Think of this like preparing a race car before a race.

### Step 1.1: Set Hostname

**What we're doing:** Giving each server a clear, meaningful name.

**On Server 1:**
```bash
sudo hostnamectl set-hostname kafka1
```

**On Server 2:**
```bash
sudo hostnamectl set-hostname kafka2
```

**On Server 3:**
```bash
sudo hostnamectl set-hostname kafka3
```

**Why:** Clear hostnames make it easy to identify which server you're working on.

**Verify:**
```bash
hostname
# Should output: kafka1 (or kafka2, kafka3)
```

---

### Step 1.2: Update /etc/hosts

**What we're doing:** Teaching each server how to find the others by name.

**Run on ALL 3 servers:**
```bash
sudo nano /etc/hosts
```

**Add these lines at the end:**
```
192.168.1.101 kafka1
192.168.1.102 kafka2
192.168.1.103 kafka3
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

**Why:** Kafka needs to communicate between servers using hostnames, not just IP addresses.

**Verify:**
```bash
ping -c 3 kafka1
ping -c 3 kafka2
ping -c 3 kafka3
```

**Expected:** All pings should succeed (3 packets transmitted, 3 received).

---

### Step 1.3: Create Kafka User

**What we're doing:** Creating a dedicated user account for running Kafka (security best practice).

**Run on ALL 3 servers:**
```bash
sudo useradd -r -s /bin/bash kafka
```

**Explanation of command:**
- `useradd` = Create new user
- `-r` = System user (not a regular login user)
- `-s /bin/bash` = Shell to use (bash)
- `kafka` = Username

**Why:** Running Kafka as root is dangerous. A dedicated user limits security risks.

**Verify:**
```bash
id kafka
# Should show: uid=xxx(kafka) gid=xxx(kafka) groups=xxx(kafka)
```

---

### Step 1.4: Create Data Directories

**What we're doing:** Creating folders where Kafka will store data.

**Run on ALL 3 servers:**
```bash
# Create main directories
sudo mkdir -p /data/kafka/logs
sudo mkdir -p /data/kafka/metadata
sudo mkdir -p /var/log/kafka

# Set ownership to kafka user
sudo chown -R kafka:kafka /data/kafka
sudo chown -R kafka:kafka /var/log/kafka

# Set permissions
sudo chmod -R 755 /data/kafka
sudo chmod -R 755 /var/log/kafka
```

**Explanation:**
- `/data/kafka/logs` = Where topic data is stored (most disk space)
- `/data/kafka/metadata` = Where KRaft metadata is stored (small)
- `/var/log/kafka` = Where Kafka writes log files

**Why:** Kafka needs specific locations with proper permissions to store data safely.

**Verify:**
```bash
ls -la /data/kafka/
ls -la /var/log/kafka/
```

**Expected:** All directories owned by `kafka:kafka`

---

## PHASE 2: Install Java

### Why This Matters
Kafka is written in Java, so we need Java installed to run it.

### Step 2.1: Install Java 21 LTS

**What we're doing:** Installing the Java Development Kit (JDK) version 17.

**Run on ALL 3 servers:**
```bash
cd /opt
wget https://download.bell-sw.com/java/21.0.10+10/bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
tar -xzf bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
mv /opt/jdk-21.0.10+10 /opt/jdk-21.0.10
export JAVA_HOME=/opt/jdk-21.0.10
export PATH=$JAVA_HOME/bin:$PATH
```

**Explanation:**
- `dnf` = Package manager for RHEL 9
- `-y` = Automatically answer "yes" to prompts
- `jdk-21.0.10-devel` = Java 21 LTS with development tools

**This will take:** ~2-3 minutes per server

**Verify:**
```bash
java -version
```

**Expected output:**
```
openjdk version "21.0.x" xxxx-xx-xx
OpenJDK Runtime Environment...
OpenJDK 64-Bit Server VM...
```

---

### Step 2.2: Set JAVA_HOME

**What we're doing:** Telling the system where Java is installed.

**Run on ALL 3 servers:**
```bash
echo 'export JAVA_HOME=/opt/jdk-21.0.10' | sudo tee -a /etc/profile.d/java.sh
echo 'export PATH=$JAVA_HOME/bin:$PATH' | sudo tee -a /etc/profile.d/java.sh
source /etc/profile.d/java.sh
```

**Explanation:**
- Creates a configuration file that sets JAVA_HOME
- Makes Java commands available everywhere
- `source` = Apply changes immediately

**Verify:**
```bash
echo $JAVA_HOME
# Should output: /opt/jdk-21.0.10
```

---

## PHASE 3: Tune System Settings

### Why This Matters
Default Linux settings are for general-purpose use. We need to optimize for high-performance messaging.

### Step 3.1: Set File Limits

**What we're doing:** Allowing Kafka to open many files simultaneously.

**The Problem:** By default, Linux limits how many files a program can open. Kafka needs to open thousands of files (for different partitions and connections).

**Run on ALL 3 servers:**
```bash
sudo nano /etc/security/limits.d/kafka.conf
```

**Add this content:**
```
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
kafka soft memlock unlimited
kafka hard memlock unlimited
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

**Explanation:**
- `nofile` = Number of open files (100,000)
- `nproc` = Number of processes (32,768)
- `memlock` = Memory locking (unlimited)
- `soft` = Warning limit
- `hard` = Maximum limit

**Why:** Kafka will crash if it can't open enough files. This prevents that.

---

### Step 3.2: Configure Kernel Parameters

**What we're doing:** Optimizing network and memory settings for high performance.

**Run on ALL 3 servers:**
```bash
sudo nano /etc/sysctl.conf
```

**Add these lines at the end:**
```bash
# Network Performance
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

# Memory Management
vm.swappiness = 1
vm.dirty_ratio = 80
vm.dirty_background_ratio = 5
vm.max_map_count = 262144

# File System
fs.file-max = 2097152
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

**Apply changes immediately:**
```bash
sudo sysctl -p
```

**Explanation (in simple terms):**
- **Network settings** = Allow bigger data transfers (like wider pipes for water)
- **Connection settings** = Handle more simultaneous connections
- **Memory settings** = Optimize how data is cached
- **File system** = Allow more open files system-wide

**Why:** Default settings are too conservative for Kafka's high-performance needs.

---

### Step 3.3: Disable Swap

**What we're doing:** Preventing the system from using slow disk storage as memory.

**The Problem:** When RAM is full, Linux uses disk space as extra memory ("swap"). This is VERY SLOW and causes Kafka performance problems.

**Run on ALL 3 servers:**
```bash
# Disable swap immediately
sudo swapoff -a

# Permanently disable (comment out in /etc/fstab)
sudo sed -i.bak '/ swap / s/^/#/' /etc/fstab
```

**Explanation:**
- `swapoff -a` = Turn off swap right now
- `sed` command = Disable swap permanently (will survive reboot)

**Why:** Swap kills Kafka performance. We have enough RAM, so we don't need swap.

**Verify:**
```bash
free -h
```

**Expected:** Swap line should show `0B` for total, used, and free.

---

### Step 3.4: Configure Firewall

**What we're doing:** Opening network ports so Kafka servers can communicate.

**Run on ALL 3 servers:**
```bash
# Open Kafka broker port
sudo firewall-cmd --permanent --add-port=9092/tcp

# Open Kafka SSL port (optional, for future use)
sudo firewall-cmd --permanent --add-port=9093/tcp

# Open KRaft controller port
sudo firewall-cmd --permanent --add-port=9094/tcp

# Open JMX monitoring port
sudo firewall-cmd --permanent --add-port=9999/tcp

# Reload firewall to apply changes
sudo firewall-cmd --reload
```

**Explanation of ports:**
- `9092` = Main Kafka communication port (clients connect here)
- `9093` = SSL-encrypted communication (secure connections)
- `9094` = KRaft controller communication (cluster coordination)
- `9999` = JMX monitoring (for metrics and monitoring tools)

**Why:** Firewall blocks all ports by default. We need to explicitly allow Kafka ports.

**Verify:**
```bash
sudo firewall-cmd --list-ports
```

**Expected output:**
```
9092/tcp 9093/tcp 9094/tcp 9999/tcp
```

---

## PHASE 4: Download Kafka

### Why This Matters
We need the Kafka software package.

### Step 4.1: Download Kafka (Run on Server 1 only, then copy)

**What we're doing:** Downloading the official Kafka release.

**On Server 1:**
```bash
# Go to /tmp directory
cd /tmp

# Download Kafka 4.1.1
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz

# Download checksum for verification
sudo wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz.sha512
```

**Explanation:**
- `wget` = Download files from internet
- `kafka_2.13-4.1.1.tgz` = Kafka 4.1.1 with Scala 2.13
- `.sha512` = Checksum file (for verifying download integrity)

**This will take:** ~2-3 minutes (depending on internet speed)

---

### Step 4.2: Verify Download

**What we're doing:** Making sure the download wasn't corrupted.

**On Server 1:**
```bash
cd /tmp
sha512sum -c kafka_2.13-4.1.1.tgz.sha512
```

**Expected output:**
```
kafka_2.13-4.1.1.tgz: OK
```

**Why:** Verifying the checksum ensures the file wasn't corrupted during download.

**If verification fails:** Delete the file and download again.

---

### Step 4.3: Extract and Install

**What we're doing:** Unpacking Kafka and putting it in the right location.

**On Server 1:**
```bash
# Extract the archive
sudo tar -xzf kafka_2.13-4.1.1.tgz -C /opt/

# Rename to simpler name
sudo mv /opt/kafka_2.13-4.1.1 /opt/kafka

# Set ownership to kafka user
sudo chown -R kafka:kafka /opt/kafka

# Verify extraction
ls -la /opt/kafka
```

**Expected:** Should see directories like `bin/`, `config/`, `libs/`

---

### Step 4.4: Copy to Other Servers

**What we're doing:** Installing Kafka on the other 2 servers.

**From Server 1:**
```bash
# Copy to Server 2
sudo rsync -av /opt/kafka/ kafka2:/opt/kafka/

# Copy to Server 3
sudo rsync -av /opt/kafka/ kafka3:/opt/kafka/
```

**Alternative (if rsync doesn't work):**
Repeat steps 4.1-4.3 on Server 2 and Server 3.

**On Server 2 and 3:**
```bash
# Set correct ownership
sudo chown -R kafka:kafka /opt/kafka
```

---

## PHASE 5: Configure Kafka

### Why This Matters
This is the most important phase! Configuration determines how Kafka behaves.

### Step 5.1: Generate Cluster UUID (Run ONCE on Server 1)

**What we're doing:** Creating a unique ID for this cluster.

**The Concept:** Every Kafka cluster needs a unique identifier (like a social security number for the cluster). All 3 servers must use the SAME UUID.

**On Server 1 only:**
```bash
/opt/kafka/bin/kafka-storage.sh random-uuid
```

**Example output:**
```
7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
```

**CRITICAL:** Copy this UUID! You'll need it for all 3 servers.

**Save it temporarily:**
```bash
export CLUSTER_UUID="7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g"
echo $CLUSTER_UUID
```

**Why:** The UUID identifies this specific Kafka cluster. All brokers in the cluster must share the same UUID.

---

### Step 5.2: Configure Server Properties (Server 1)

**What we're doing:** Creating the main configuration file for Kafka.

**On Server 1:**
```bash
# Backup original config
sudo cp /opt/kafka/config/server.properties /opt/kafka/config/server.properties.backup

# Create new config
sudo nano /opt/kafka/config/server.properties
```

**Delete everything and paste this:**
```properties
############################# KRaft Configuration #############################

# Process roles: This server acts as both broker and controller
process.roles=broker,controller

# Node ID: Unique identifier for this server (MUST be different on each server)
node.id=1

# Controller Quorum: List of all controllers (all 3 servers)
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094

############################# Listeners #############################

# Listeners: Network interfaces this server listens on
listeners=PLAINTEXT://kafka1:9092,CONTROLLER://kafka1:9094

# Advertised Listeners: What address clients should use
advertised.listeners=PLAINTEXT://kafka1:9092

# Inter Broker Listener: How brokers talk to each other
inter.broker.listener.name=PLAINTEXT

# Controller Listener: How controllers communicate
controller.listener.names=CONTROLLER

############################# Log Directories #############################

# Data storage locations
log.dirs=/data/kafka/logs
metadata.log.dir=/data/kafka/metadata

############################# Cluster Configuration #############################

# Cluster ID: REPLACE WITH YOUR UUID FROM STEP 5.1
cluster.id=REPLACE_WITH_YOUR_CLUSTER_UUID

############################# Replication & Fault Tolerance #############################

# Default Replication: Keep 3 copies of every partition
default.replication.factor=3

# Minimum In-Sync Replicas: Require 2 copies before confirming write
min.insync.replicas=2

# Offset Topic: Consumer position tracking
offsets.topic.replication.factor=3
offsets.topic.num.partitions=50
offsets.retention.minutes=10080

# Transaction State: For exactly-once semantics
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

############################# Topic Defaults #############################

# Default Partitions: How many partitions for new topics
num.partitions=3

# Auto Create Topics: Disable (create explicitly for safety)
auto.create.topics.enable=false

############################# Performance Tuning #############################

# Network Threads: Handle network requests (8 threads)
num.network.threads=8

# IO Threads: Handle disk operations (16 threads)
num.io.threads=16

# Buffer Sizes: Network buffer sizes
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

############################# Log Retention & Cleanup #############################

# Retention: Keep data for 7 days (168 hours)
log.retention.hours=168

# Cleanup Frequency: Check for old data every 5 minutes
log.retention.check.interval.ms=300000

# Segment Size: Size of each log file (1 GB)
log.segment.bytes=1073741824

# Cleanup Policy: Delete old data
log.cleanup.policy=delete

############################# Compression #############################

# Compression: Use LZ4 (fast and efficient)
compression.type=lz4
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

**IMPORTANT:** Replace `REPLACE_WITH_YOUR_CLUSTER_UUID` with your actual UUID from Step 5.1!

---

### Step 5.3: Explanation of Key Settings

Let me explain the most important settings in simple terms:

**`process.roles=broker,controller`**
- **Simple:** This server does two jobs: stores data (broker) and coordinates (controller)
- **Why:** In KRaft, we don't need separate coordinator servers

**`node.id=1`**
- **Simple:** This server's unique ID number
- **Why:** Each server needs a unique number (1, 2, 3)

**`controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094`**
- **Simple:** List of all servers that can be controllers
- **Why:** Tells Kafka which servers can coordinate the cluster

**`default.replication.factor=3`**
- **Simple:** Make 3 copies of every message
- **Why:** If 1 or 2 servers fail, we still have data

**`min.insync.replicas=2`**
- **Simple:** Wait for 2 copies before saying "saved successfully"
- **Why:** Ensures data is safely stored even if one server is down

**`offsets.topic.replication.factor=3`**
- **Simple:** Keep 3 copies of consumer positions
- **Why:** This is your requirement! Ensures consumer offsets survive failures

**`num.partitions=3`**
- **Simple:** Split each topic into 3 parts
- **Why:** Allows parallel processing (faster)

**`log.retention.hours=168`**
- **Simple:** Keep data for 7 days (168 hours)
- **Why:** Old data gets deleted to save disk space

**`compression.type=lz4`**
- **Simple:** Compress data using LZ4 algorithm
- **Why:** Saves disk space and network bandwidth

---

### Step 5.4: Configure Server 2

**What we're doing:** Same config as Server 1, but with different node.id and listeners.

**On Server 2:**
```bash
# Copy config from Server 1 as starting point
sudo scp kafka1:/opt/kafka/config/server.properties /opt/kafka/config/server.properties

# Edit for Server 2
sudo nano /opt/kafka/config/server.properties
```

**Change ONLY these lines:**
```properties
node.id=2
listeners=PLAINTEXT://kafka2:9092,CONTROLLER://kafka2:9094
advertised.listeners=PLAINTEXT://kafka2:9092
```

**Keep everything else the same!**

**Save and exit**

---

### Step 5.5: Configure Server 3

**On Server 3:**
```bash
# Copy config from Server 1
sudo scp kafka1:/opt/kafka/config/server.properties /opt/kafka/config/server.properties

# Edit for Server 3
sudo nano /opt/kafka/config/server.properties
```

**Change ONLY these lines:**
```properties
node.id=3
listeners=PLAINTEXT://kafka3:9092,CONTROLLER://kafka3:9094
advertised.listeners=PLAINTEXT://kafka3:9092
```

**Save and exit**

---

### Step 5.6: Set Ownership

**What we're doing:** Making sure kafka user owns the config files.

**Run on ALL 3 servers:**
```bash
sudo chown kafka:kafka /opt/kafka/config/server.properties
```

---

## PHASE 6: Format Storage

### Why This Matters
Before first use, we need to format Kafka's storage (like formatting a hard drive).

**CRITICAL:** Run this ONLY ONCE before the very first startup. NEVER run this on a running cluster!

### Step 6.1: Format Storage on Each Server

**On Server 1:**
```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t YOUR_CLUSTER_UUID_HERE \
  -c /opt/kafka/config/server.properties
```

**Replace `YOUR_CLUSTER_UUID_HERE` with your actual UUID from Step 5.1!**

**Expected output:**
```
Formatting /data/kafka/metadata with metadata.version 3.9-IV0.
```

**Repeat on Server 2:**
```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t YOUR_CLUSTER_UUID_HERE \
  -c /opt/kafka/config/server.properties
```

**Repeat on Server 3:**
```bash
sudo -u kafka /opt/kafka/bin/kafka-storage.sh format \
  -t YOUR_CLUSTER_UUID_HERE \
  -c /opt/kafka/config/server.properties
```

**Why:** This initializes the storage directories with Kafka's internal metadata structure.

** WARNING:** Never run format on an existing cluster! It will DELETE all data!

---

## PHASE 7: Create Systemd Service

### Why This Matters
Systemd will automatically start Kafka when the server boots and restart it if it crashes.

### Step 7.1: Create Service File

**Run on ALL 3 servers:**
```bash
sudo nano /etc/systemd/system/kafka.service
```

**Paste this content:**
```ini
[Unit]
Description=Apache Kafka Server (KRaft Mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=kafka
Group=kafka

# Java Settings
Environment="JAVA_HOME=/opt/jdk-21.0.10"

# Heap Size: 6 GB (adjust based on your RAM)
Environment="KAFKA_HEAP_OPTS=-Xms6g -Xmx6g"

# JVM Performance Settings
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M -XX:MinMetaspaceFreeRatio=50 -XX:MaxMetaspaceFreeRatio=80"

# Log Directory
Environment="LOG_DIR=/var/log/kafka"

# Start Command
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties

# Stop Command
ExecStop=/opt/kafka/bin/kafka-server-stop.sh

# Restart Policy
Restart=on-failure
RestartSec=10

# Resource Limits
LimitNOFILE=100000
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
```

**Save and exit**

---

### Step 7.2: Explanation of Service Settings

**`User=kafka`**
- **Simple:** Run Kafka as the kafka user (not root)
- **Why:** Security best practice

**`KAFKA_HEAP_OPTS=-Xms6g -Xmx6g`**
- **Simple:** Kafka gets 6 GB of RAM for Java heap
- **Why:** Kafka needs memory for caching and processing
- **Note:** If you have 128 GB RAM, you could use 8-10 GB

**`Restart=on-failure`**
- **Simple:** If Kafka crashes, automatically restart it
- **Why:** Improves reliability

**`LimitNOFILE=100000`**
- **Simple:** Allow opening 100,000 files
- **Why:** Kafka needs many file handles for partitions

---

### Step 7.3: Enable Service

**Run on ALL 3 servers:**
```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable kafka
```

**Expected output:**
```
Created symlink /etc/systemd/system/multi-user.target.wants/kafka.service → /etc/systemd/system/kafka.service.
```

**Why:** This ensures Kafka starts automatically when the server reboots.

---

## PHASE 8: Start Cluster

### Why This Matters
Time to start your Kafka cluster!

### Step 8.1: Start Servers (One at a Time)

**Important:** Start servers one at a time with pauses between them.

**On Server 1:**
```bash
sudo systemctl start kafka
```

**Wait 30 seconds**, then check:
```bash
sudo systemctl status kafka
```

**Expected output:**
```
 kafka.service - Apache Kafka Server (KRaft Mode)
   Loaded: loaded (/etc/systemd/system/kafka.service; enabled)
   Active: active (running) since...
```

**Look for:** `Active: active (running)` in green

---

**On Server 2 (after Server 1 is running):**
```bash
sudo systemctl start kafka
sleep 30
sudo systemctl status kafka
```

---

**On Server 3 (after Server 2 is running):**
```bash
sudo systemctl start kafka
sleep 30
sudo systemctl status kafka
```

---

### Step 8.2: Check Logs

**If any server fails to start, check logs:**
```bash
sudo journalctl -u kafka -n 100 --no-pager
```

**Or check log file:**
```bash
tail -50 /var/log/kafka/server.log
```

**Common startup issues and solutions:**
- **Port already in use:** Another process is using port 9092. Find and stop it.
- **Permission denied:** Check ownership of /data/kafka directories
- **Cluster UUID mismatch:** All servers must use the same UUID
- **Java not found:** Check JAVA_HOME is set correctly

---

## PHASE 9: Verify Installation

### Why This Matters
We need to confirm everything is working correctly.

### Step 9.1: Check Cluster Metadata

**On any server:**
```bash
/opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka1:9092 describe --status
```

**Expected output:**
```
ClusterId: <your-cluster-uuid>
LeaderId: 1
LeaderEpoch: 1
HighWatermark: 100
MaxFollowerLag: 0
MaxFollowerLagTimeMs: 0
CurrentVoters: [1,2,3]
CurrentObservers: []
```

**What to look for:**
- `CurrentVoters: [1,2,3]` ← All 3 servers are participating
- `LeaderId: 1` ← Server 1 is currently the controller

---

### Step 9.2: List Brokers

**On any server:**
```bash
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

**Expected output:**
```
kafka1:9092 (id: 1 rack: null) -> (...)
kafka2:9092 (id: 2 rack: null) -> (...)
kafka3:9092 (id: 3 rack: null) -> (...)
```

**What to look for:** All 3 servers listed

---

### Step 9.3: Create Test Topic

**On any server:**
```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic test-topic \
  --partitions 3 \
  --replication-factor 3
```

**Expected output:**
```
Created topic test-topic.
```

**Verify topic:**
```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic test-topic
```

**Expected output:**
```
Topic: test-topic       PartitionCount: 3       ReplicationFactor: 3
        Topic: test-topic       Partition: 0    Leader: 1       Replicas: 1,2,3 Isr: 1,2,3
        Topic: test-topic       Partition: 1    Leader: 2       Replicas: 2,3,1 Isr: 2,3,1
        Topic: test-topic       Partition: 2    Leader: 3       Replicas: 3,1,2 Isr: 3,1,2
```

**What to look for:**
- `ReplicationFactor: 3` ← 3 copies
- `Replicas: 1,2,3` ← Data on all servers
- `Isr: 1,2,3` ← All replicas are in sync

---

### Step 9.4: Send Test Messages

**Open a producer console:**
```bash
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic
```

**Type some messages:**
```
Hello Kafka!
This is message 2
Testing 123
```

**Press Ctrl+C to exit**

---

### Step 9.5: Read Test Messages

**Open a consumer console:**
```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic \
  --from-beginning
```

**Expected:** You should see the messages you typed earlier.

**Press Ctrl+C to exit**

**Success!** If you see your messages, Kafka is working!

---

## PHASE 10: Test High Availability

### Why This Matters
We need to verify the cluster can survive a server failure.

### Step 10.1: Test Broker Failover

**What we're testing:** Can the cluster survive if one server goes down?

**Step 1:** Note current leaders
```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic test-topic
```

**Step 2:** Stop Server 1
```bash
# On Server 1
sudo systemctl stop kafka
```

**Step 3:** Check cluster health (from Server 2 or 3)
```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka2:9092 \
  --describe \
  --topic test-topic
```

**Expected:** Partitions should still have leaders (on Server 2 and 3)

**Step 4:** Test sending/receiving messages (should still work!)
```bash
# Send a message
echo "Server 1 is down, but I still work!" | \
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka2:9092,kafka3:9092 \
  --topic test-topic

# Read messages
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka2:9092,kafka3:9092 \
  --topic test-topic \
  --from-beginning
```

**Expected:** You should see ALL messages, including the new one!

**Step 5:** Restart Server 1
```bash
# On Server 1
sudo systemctl start kafka
```

**Wait 30 seconds**, then verify it rejoined:
```bash
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

**Success!** If the cluster continued working with Server 1 down, your HA setup is correct!

---

##  Congratulations!

**You've successfully installed a production-grade Kafka cluster!**

 3 servers running Kafka  
 KRaft mode (no ZooKeeper)  
 Replication factor 3  
 Consumer offsets replicated 3 times  
 High availability tested  
 Automatic failover working  

---

##  Next Steps

1. **[Set Up Monitoring](../06-monitoring/health-checks.md)**
   - Configure health checks
   - Set up dashboards
   - Configure alerts

2. **[Learn Daily Operations](../05-operations/daily-tasks.md)**
   - Creating topics
   - Managing consumers
   - Monitoring cluster health

3. **[Configure Security](../04-configuration/security.md)**
   - Enable SSL/TLS
   - Set up authentication
   - Configure authorization

4. **[Plan Disaster Recovery](../08-advanced/disaster-recovery.md)**
   - Set up mirror cluster
   - Configure backups
   - Document recovery procedures

---

##  Troubleshooting

**If something didn't work:**
1. Check logs: `tail -100 /var/log/kafka/server.log`
2. Verify config: `cat /opt/kafka/config/server.properties`
3. Check network: `ping kafka1; ping kafka2; ping kafka3`
4. Verify Java: `java -version`
5. Check ports: `netstat -tulpn | grep 9092`

**See:** [Common Issues Guide](../07-troubleshooting/common-issues.md)

---

##  Summary

**What You Built:**
```
3-Server Kafka Cluster (KRaft Mode)
├── kafka1 (192.168.1.101) - Broker + Controller
├── kafka2 (192.168.1.102) - Broker + Controller
└── kafka3 (192.168.1.103) - Broker + Controller

Features:
 3x data replication
 Automatic failover
 High availability
 Production-ready
```

**Time Invested:** ~5 hours  
**Value:** Enterprise-grade messaging platform  
**Next:** Put it to work! 
