#  Quick Start Guide
## Get Kafka Running in 30 Minutes

**For people who want to get started immediately.**

---

##  What You'll Do

1. Generate cluster UUID (2 minutes)
2. Run installation script on 3 servers (10 minutes each)
3. Start Kafka cluster (5 minutes)
4. Verify it works (3 minutes)

**Total time:** ~30-40 minutes

---

##  Before You Start

Make sure you have:

- [ ] 3 servers (physical or virtual) running RHEL 9 / Oracle Linux 9 / Rocky Linux 9
- [ ] Root/sudo access on all 3 servers
- [ ] Servers can communicate with each other (test with `ping`)
- [ ] Internet connection on all servers
- [ ] Server IPs:
  - kafka1: `192.168.1.101`
  - kafka2: `192.168.1.102`
  - kafka3: `192.168.1.103`

**Note:** If your IPs are different, edit `scripts/install-kafka.sh` and change the `NODE_IPS` array.

---

##  Step-by-Step

### Step 1: Download This Repository

On your laptop/workstation:

```bash
# If you have this as a ZIP file, extract it
unzip kafka-production-guide.zip
cd kafka-production-guide

# If using Git
git clone <your-private-repo-url>
cd kafka-production-guide
```

---

### Step 2: Copy Files to Servers

Copy the installation script to all 3 servers:

```bash
# From your workstation
scp scripts/install-kafka.sh root@192.168.1.101:/tmp/
scp scripts/install-kafka.sh root@192.168.1.102:/tmp/
scp scripts/install-kafka.sh root@192.168.1.103:/tmp/
```

---

### Step 3: Generate Cluster UUID

**Do this ONCE on kafka1:**

```bash
# SSH to kafka1
ssh root@192.168.1.101

# Create temporary Kafka directory to get UUID generator
mkdir -p /tmp/kafka-temp
cd /tmp/kafka-temp
wget https://downloads.apache.org/kafka/3.9.1/kafka_2.13-3.9.1.tgz
tar -xzf kafka_2.13-3.9.1.tgz
cd kafka_2.13-3.9.1

# Generate UUID
./bin/kafka-storage.sh random-uuid
```

**Output will look like:** `7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g`

** IMPORTANT:** Copy this UUID! You'll need it for all 3 servers.

Clean up:
```bash
cd ~
rm -rf /tmp/kafka-temp
```

---

### Step 4: Install Kafka on Server 1

**On kafka1:**

```bash
cd /tmp
chmod +x install-kafka.sh
./install-kafka.sh 1 YOUR_CLUSTER_UUID_HERE
```

**Replace `YOUR_CLUSTER_UUID_HERE` with the UUID from Step 3!**

**Example:**
```bash
./install-kafka.sh 1 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
```

**What to expect:**
- Script will ask for confirmation
- Installation takes ~10 minutes
- You'll see green checkmarks () for each step

---

### Step 5: Install Kafka on Server 2

**On kafka2:**

```bash
cd /tmp
chmod +x install-kafka.sh
./install-kafka.sh 2 YOUR_CLUSTER_UUID_HERE
```

**Use the SAME UUID as Step 4!**

---

### Step 6: Install Kafka on Server 3

**On kafka3:**

```bash
cd /tmp
chmod +x install-kafka.sh
./install-kafka.sh 3 YOUR_CLUSTER_UUID_HERE
```

**Use the SAME UUID as Step 4!**

---

### Step 7: Start Kafka Cluster

**Start servers ONE AT A TIME** (important!):

**On kafka1:**
```bash
systemctl start kafka
sleep 30
systemctl status kafka
```

**Wait for kafka1 to be fully running (status shows "active (running)"), then:**

**On kafka2:**
```bash
systemctl start kafka
sleep 30
systemctl status kafka
```

**Wait for kafka2 to be fully running, then:**

**On kafka3:**
```bash
systemctl start kafka
sleep 30
systemctl status kafka
```

---

### Step 8: Verify Cluster

**On any server:**

```bash
/opt/kafka/bin/health-check.sh
```

**What you should see:**
```
Checking Kafka cluster health...
Active Brokers: 3/3
Under-Replicated Partitions: 0
 Cluster is HEALTHY
```

**If you see this, congratulations! Your cluster is working! **

---

##  Test Your Cluster

### Create a Test Topic

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --create \
  --topic test-topic \
  --partitions 3 \
  --replication-factor 3
```

### Send a Test Message

```bash
echo "Hello Kafka!" | /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic
```

### Read the Test Message

```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test-topic \
  --from-beginning
```

**You should see:** `Hello Kafka!`

**Press Ctrl+C to exit the consumer.**

### Verify Consumer Offsets Replication

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka1:9092 \
  --describe \
  --topic __consumer_offsets | head -5
```

**You should see:** `ReplicationFactor: 3`

 **This confirms your requirement is met!**

---

##  What's Next?

Your cluster is now running! Here's what to do next:

### For Production Use:

1. **Enable Security**
   - Read: `docs/SECURITY.md` (not created yet, but reference for future)
   - Enable SSL/TLS encryption
   - Configure SASL authentication

2. **Set Up Monitoring**
   - Install Prometheus and Grafana
   - Configure JMX metrics
   - Set up alerting

3. **Create Production Topics**
   ```bash
   /opt/kafka/bin/kafka-topics.sh \
     --bootstrap-server kafka1:9092 \
     --create \
     --topic financial-transactions \
     --partitions 30 \
     --replication-factor 3 \
     --config min.insync.replicas=2 \
     --config retention.ms=2592000000
   ```

4. **Set Up Disaster Recovery**
   - Configure MirrorMaker 2
   - Set up backup procedures
   - Document recovery processes

5. **Connect Your Applications**
   - Use bootstrap servers: `kafka1:9092,kafka2:9092,kafka3:9092`
   - Configure producers with `acks=all`
   - Configure consumers appropriately

### For Learning:

1. **Read the Full Documentation**
   - Main guide: `README.md`
   - Operations: `docs/OPERATIONS.md`
   - FAQ: `docs/FAQ.md`

2. **Experiment**
   - Create different topics
   - Test producer/consumer performance
   - Try failing a server (see high availability in action)

3. **Optimize**
   - Tune JVM settings
   - Adjust partition counts
   - Experiment with compression

---

##  Need Help?

### Common Issues:

**Problem:** Script fails with "Address already in use"  
**Solution:** Port 9092 is in use. Check: `netstat -tulpn | grep 9092`

**Problem:** Can't connect to other servers  
**Solution:** Check firewall. Run: `firewall-cmd --list-ports`

**Problem:** Broker won't start  
**Solution:** Check logs: `tail -100 /var/log/kafka/server.log`

**Problem:** Under-replicated partitions  
**Solution:** Check all brokers are running: `systemctl status kafka`

### Get More Information:

- **Detailed Setup:** Read `README.md`
- **Daily Operations:** Read `docs/OPERATIONS.md`
- **Common Questions:** Read `docs/FAQ.md`
- **Kafka Documentation:** https://kafka.apache.org/documentation/

---

##  Useful Commands

```bash
# Check Kafka status
systemctl status kafka

# Start Kafka
systemctl start kafka

# Stop Kafka
systemctl stop kafka

# View logs (real-time)
tail -f /var/log/kafka/server.log

# View logs (last 100 lines)
tail -100 /var/log/kafka/server.log

# Check cluster health
/opt/kafka/bin/health-check.sh

# List all topics
/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --list

# Describe a topic
/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka1:9092 --describe --topic test-topic

# Check consumer groups
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka1:9092 --list
```

---

##  Success Checklist

After following this guide, you should have:

- [ ] Kafka installed on all 3 servers
- [ ] All 3 brokers running (verify with health check)
- [ ] No under-replicated partitions
- [ ] No offline partitions
- [ ] Test topic created successfully
- [ ] Messages can be sent and received
- [ ] `__consumer_offsets` has replication factor of 3

**If all items are checked: You're ready to go! **

---

**Last Updated:** January 31, 2026  
**Kafka Version:** 3.9.1  
**Estimated Time:** 30-40 minutes
