# Getting Started with Kafka
## Your First 15 Minutes

---

##  Welcome!

This guide gets you from zero to a working Kafka cluster in the fastest way possible.

**What you'll accomplish:**
- Understand what Kafka is (5 minutes)
- Install Kafka on 3 servers (10 minutes with script)
- Send your first message (5 minutes)

**Total Time:** 20 minutes

---

## Step 1: Understand the Basics (5 min)

### What is Kafka? (In 30 Seconds)

Kafka is like a **super-fast postal service** for computer applications:
- Applications send messages → Kafka stores them safely
- Other applications read messages → Process them at their own pace
- Everything is fast, reliable, and can handle millions of messages

### Why 3 Servers?

- **Reliability:** If 1 server fails, 2 keep working
- **No Data Loss:** Every message copied to all 3 servers
- **Automatic Failover:** System fixes itself

### What's KRaft?

- **Old way:** Kafka needed a helper system (ZooKeeper)
- **New way (KRaft):** Kafka manages itself
- **Why it matters:** Simpler, faster, cheaper

---

## Step 2: Prepare Your Servers (2 min)

### What You Need

**3 servers with:**
- Operating System: RHEL 9 or compatible
- RAM: 64 GB (minimum 32 GB)
- Disk: 1 TB SSD
- Network: Can talk to each other

**Network Setup:**
```
Server 1: 192.168.1.101 → Will be named "kafka1"
Server 2: 192.168.1.102 → Will be named "kafka2"
Server 3: 192.168.1.103 → Will be named "kafka3"
```

**What You Need Access To:**
- Root/sudo password for all 3 servers
- SSH access to all 3 servers
- Internet connection (to download Kafka)

---

## Step 3: Generate Cluster UUID (1 min)

**On Server 1, run this command:**
```bash
/opt/kafka/bin/kafka-storage.sh random-uuid
```

**You'll get output like:**
```
7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
```

**IMPORTANT:** Copy this UUID! You'll use it on all 3 servers.

---

## Step 4: Run Installation Script (3 min per server)

### Download the Script

**On each server:**
```bash
# Download the automated install script
wget https://your-repo/scripts/install/kafka-install.sh

# Make it executable
chmod +x kafka-install.sh
```

### Run the Script

**On Server 1:**
```bash
sudo ./kafka-install.sh 1 YOUR_UUID_HERE
```

**On Server 2:**
```bash
sudo ./kafka-install.sh 2 YOUR_UUID_HERE
```

**On Server 3:**
```bash
sudo ./kafka-install.sh 3 YOUR_UUID_HERE
```

**Replace `YOUR_UUID_HERE` with your actual UUID from Step 3!**

**What the script does:**
- Installs Java
- Downloads Kafka
- Configures everything
- Sets up system settings
- Creates services

**Time:** About 3 minutes per server

---

## Step 5: Start the Cluster (2 min)

### Start Each Server (One at a Time!)

**On Server 1:**
```bash
sudo systemctl start kafka
```

**Wait 30 seconds**, then on Server 2:
```bash
sudo systemctl start kafka
```

**Wait 30 seconds**, then on Server 3:
```bash
sudo systemctl start kafka
```

### Verify It's Running

**On any server:**
```bash
sudo systemctl status kafka
```

**Look for:** `Active: active (running)` in green

---

## Step 6: Verify the Cluster (1 min)

**Check that all 3 servers are connected:**
```bash
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka1:9092,kafka2:9092,kafka3:9092
```

**Expected output:**
```
kafka1:9092 (id: 1 rack: null) -> ...
kafka2:9092 (id: 2 rack: null) -> ...
kafka3:9092 (id: 3 rack: null) -> ...
```

**Success!** If you see all 3 servers, your cluster is working!

---

## Step 7: Send Your First Message! (2 min)

### Create a Test Topic

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic my-first-topic \
  --partitions 3 \
  --replication-factor 3
```

### Send Some Messages

```bash
/opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic my-first-topic
```

**Type some messages:**
```
Hello Kafka!
This is my first message!
Kafka is working!
```

**Press Ctrl+C when done**

### Read Your Messages

```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic my-first-topic \
  --from-beginning
```

**You should see:**
```
Hello Kafka!
This is my first message!
Kafka is working!
```

**Press Ctrl+C to stop**

---

##  Congratulations!

**You now have:**
 A working 3-node Kafka cluster  
 KRaft architecture (modern, self-managing)  
 High availability (can survive 1 server failure)  
 Your first topic and messages  

---

## What's Next?

### Learn the Basics
1. **[Understand Core Concepts](docs/01-understanding-kafka/concepts.md)**
   - Topics, partitions, replication
   - Producers and consumers
   - How everything fits together

2. **[Daily Operations](docs/05-operations/daily-tasks.md)**
   - Creating topics for production
   - Managing consumer groups
   - Monitoring cluster health

### Set Up for Production
3. **[Configure Monitoring](docs/06-monitoring/health-checks.md)**
   - Health checks
   - Alerts
   - Dashboards

4. **[Security Setup](docs/04-configuration/security.md)**
   - SSL/TLS encryption
   - Authentication
   - Authorization

5. **[Disaster Recovery](docs/08-advanced/disaster-recovery.md)**
   - Backups
   - Mirror clusters
   - Recovery procedures

---

## Quick Test: Is My Cluster Healthy?

Run this command:
```bash
/opt/kafka/bin/health-check.sh
```

**Healthy output:**
```
Active Brokers: 3/3
Under-Replicated Partitions: 0
Status: HEALTHY 
```

**If anything looks wrong:**
1. Check logs: `tail -100 /var/log/kafka/server.log`
2. See: [Troubleshooting Guide](docs/07-troubleshooting/common-issues.md)

---

## Common First-Time Questions

**Q: Can I start using this in production now?**
A: Almost! Add monitoring, security, and test failover first.

**Q: How do I create topics for my application?**
A: See [Topic Management](docs/05-operations/topic-management.md)

**Q: What if a server fails?**
A: The cluster keeps working! See [High Availability](docs/08-advanced/high-availability.md)

**Q: How do I monitor it?**
A: See [Monitoring Guide](docs/06-monitoring/health-checks.md)

**Q: Where are my messages stored?**
A: `/data/kafka/logs/` on all 3 servers (replicated)

---

## Essential Commands (Print This!)

```bash
# Start/Stop Kafka
sudo systemctl start kafka
sudo systemctl stop kafka
sudo systemctl status kafka

# Check cluster health
/opt/kafka/bin/health-check.sh

# List topics
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 --list

# View logs
tail -f /var/log/kafka/server.log

# Check consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka1:9092 \
  --describe --all-groups
```

---

## Need Help?

1. **Check Documentation:** Browse `docs/` folder
2. **Search Issues:** Common problems in [Troubleshooting](docs/07-troubleshooting/common-issues.md)
3. **Cheat Sheets:** Quick references in [cheatsheets/](cheatsheets/)

---

## You Did It! 

You've successfully installed and tested a production-grade Kafka cluster. 

**What you learned:**
- What Kafka is and why it's useful
- How to install a 3-node cluster
- How to send and receive messages
- Basic cluster verification

**Ready for more?** Start with [Understanding Kafka Concepts](docs/01-understanding-kafka/concepts.md)

---

**Welcome to the Kafka community!** 
