# **Common Mistakes Beginners Make - OpenSearch Setup**

I'll organize this by critical areas where beginners typically make mistakes.

---

## **1. System Configuration Mistakes**

### **❌ Forgetting vm.max_map_count**
**Problem:** OpenSearch fails to start with cryptic errors
```bash
# Error in logs:
max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]
```

**Fix:**
```bash
# Check current value
sysctl vm.max_map_count

# Set temporarily (lost on reboot)
sudo sysctl -w vm.max_map_count=262144

# Set permanently (survives reboot) - THIS IS WHAT BEGINNERS FORGET
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### **❌ Not Disabling Swap or Not Disabling it Permanently**
**Problem:** Poor performance, JVM issues
```bash
# Beginners often disable swap but don't make it permanent
sudo swapoff -a  # Only disables until reboot!

# Correct way - edit /etc/fstab
sudo nano /etc/fstab
# Comment out swap line:
# /dev/mapper/rhel-swap none swap defaults 0 0

# Verify swap is disabled after reboot
free -h
```

### **❌ Ignoring File Descriptor Limits**
**Problem:** "Too many open files" errors under load
```bash
# Check current limits
ulimit -n  # Shows 1024 (too low!)

# Beginners forget to set BOTH soft and hard limits
sudo tee -a /etc/security/limits.conf << EOF
opensearch soft nofile 65536
opensearch hard nofile 65536
opensearch soft nproc 4096
opensearch hard nproc 4096
EOF

# Verify after relogging
sudo su - opensearch
ulimit -n  # Should show 65536
```

### **❌ Not Setting memlock Properly**
**Problem:** bootstrap.memory_lock fails
```bash
# Check if memory locking is working
curl -XGET "https://localhost:9200/_nodes?filter_path=**.mlockall" -u admin:admin --insecure

# If false, add to limits.conf
opensearch soft memlock unlimited
opensearch hard memlock unlimited

# AND add to systemd service
sudo mkdir -p /etc/systemd/system/opensearch.service.d/
sudo nano /etc/systemd/system/opensearch.service.d/override.conf

[Service]
LimitMEMLOCK=infinity

sudo systemctl daemon-reload
sudo systemctl restart opensearch
```

---

## **2. Memory and JVM Configuration Mistakes**

### **❌ Setting Heap Size Wrong**
**Common mistakes:**

```bash
# WRONG: Setting heap too large (>50% of RAM)
-Xms7g
-Xmx7g  # On 8GB system - leaves nothing for OS/Lucene!

# WRONG: Mismatched Xms and Xmx
-Xms2g
-Xmx4g  # Should be SAME value

# WRONG: Setting heap > 32GB (loses compressed pointers)
-Xms40g
-Xmx40g  # Loses performance benefits

# CORRECT: 50% of RAM, matching values
-Xms3g
-Xmx3g  # On 6-8GB system
```

**Rule of thumb:**
- Use 50% of physical RAM
- Never exceed 32GB heap (use multiple nodes instead)
- Always set Xms = Xmx (prevents heap resizing)

### **❌ Not Accounting for System Memory**
```bash
# Beginners forget memory breakdown:
Total 8GB RAM:
├── 3GB - JVM Heap
├── 1GB - JVM Off-heap (direct buffers, threads)
├── 2GB - OS
├── 2GB - Lucene file system cache (critical!)
└── = 0GB left! (This is BAD)

# If you allocate 6GB limit but set 4GB heap:
Total 6GB Limit:
├── 4GB - JVM Heap
├── 1GB - JVM Off-heap
├── 1GB - Lucene cache (TOO SMALL!)
└── Better: 3GB heap, 3GB for off-heap + cache
```

### **❌ Ignoring JVM GC Logs**
```bash
# Beginners don't enable GC logging
# Add to jvm.options:
-Xlog:gc*,gc+age=trace,safepoint:file=/var/log/opensearch/gc.log:utctime,pid,tags:filecount=32,filesize=64m
```

---

## **3. Security Configuration Mistakes**

### **❌ Using Demo Certificates in Production**
**Problem:** Huge security risk!
```bash
# Check if using demo certs
sudo ls -la /etc/opensearch/*.pem
# Files like esnode.pem created by install_demo_configuration.sh

# Demo certs warning in logs:
WARN: DEMO CERTIFICATES DETECTED. PLEASE REPLACE THEM FOR PRODUCTION USE.

# Generate production certificates (see earlier in guide)
```

### **❌ Not Changing Default Passwords**
```bash
# Check if still using defaults
curl -XGET "https://localhost:9200" -u admin:admin --insecure
# If this works, you're using default password!

# List all default users that need password changes:
# - admin
# - kibanaserver  
# - kibanaro
# - logstash
# - readall
# - snapshotrestore
```

### **❌ Disabling Security Plugin Entirely**
```bash
# NEVER do this in production:
plugins.security.disabled: true  # ❌ BAD!

# Even for testing, use demo config instead
```

### **❌ Forgetting to Configure Dashboards Authentication**
```yaml
# opensearch_dashboards.yml
# Beginners forget to set credentials
opensearch.username: "kibanaserver"  # Not admin!
opensearch.password: "kibanaserver"  # Change this!

# Wrong: Using admin credentials for Dashboards
opensearch.username: "admin"  # ❌ Over-privileged
```

### **❌ Not Configuring HTTPS for Dashboards**
```bash
# Many beginners leave Dashboards on HTTP
server.port: 5601
server.host: "0.0.0.0"  # Accessible to internet on HTTP! ❌

# Should use HTTPS or bind to localhost only
server.host: "127.0.0.1"  # If using reverse proxy
# OR
server.ssl.enabled: true
```

---

## **4. Network and Firewall Mistakes**

### **❌ Binding to 0.0.0.0 Without Firewall**
```yaml
# opensearch.yml
network.host: 0.0.0.0  # Exposed to internet!

# Check if exposed:
curl http://your-public-ip:9200
# If this works from outside = SECURITY RISK

# Fix: Configure firewall properly
sudo firewall-cmd --list-all
# Only allow specific IPs
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port port="9200" protocol="tcp" accept'
```

### **❌ Forgetting SELinux (RHEL Specific)**
```bash
# OpenSearch fails to start, logs show permission denied
# Beginners disable SELinux instead of configuring it

# WRONG:
sudo setenforce 0  # ❌ Disables security

# CORRECT:
# Check denials
sudo ausearch -m avc -ts recent | grep opensearch

# Allow required permissions
sudo semanage port -a -t opensearch_port_t -p tcp 9200
sudo semanage port -a -t opensearch_port_t -p tcp 9300

# If specific file access needed:
sudo chcon -R -t opensearch_conf_t /etc/opensearch
sudo chcon -R -t opensearch_var_lib_t /var/lib/opensearch
```

### **❌ Not Opening Transport Port (9300)**
```bash
# Beginners only open 9200, forget 9300 for cluster communication
sudo firewall-cmd --permanent --add-port=9200/tcp  # ✓
# Missing:
sudo firewall-cmd --permanent --add-port=9300/tcp  # Cluster breaks!

# Verify both ports:
sudo ss -tlnp | grep -E '9200|9300'
```

### **❌ DNS/Hostname Issues**
```bash
# Using IP addresses instead of hostnames
discovery.seed_hosts: ["192.168.1.101:9300"]  # Works but not ideal

# Better: Use hostnames
discovery.seed_hosts: ["node-1:9300", "node-2:9300"]

# But forgetting to configure /etc/hosts
# Add to ALL nodes:
192.168.1.101 node-1
192.168.1.102 node-2
192.168.1.103 node-3

# Verify DNS resolution
ping node-1
ping node-2
```

---

## **5. Storage and Disk Management Mistakes**

### **❌ Using Root Partition for Data**
```yaml
# Default in tarball installation:
path.data: /opt/opensearch/data  # On root partition! ❌

# Correct: Use dedicated partition
path.data: /var/lib/opensearch  # Or dedicated mount
path.logs: /var/log/opensearch

# Check disk usage
df -h /var/lib/opensearch
```

### **❌ Not Monitoring Disk Space**
```bash
# OpenSearch stops accepting writes at 90% disk usage (default)
# Beginners don't monitor until too late

# Set up monitoring
curl -XGET "https://localhost:9200/_cat/allocation?v" -u admin:admin --insecure

# Configure watermarks
curl -XPUT "https://localhost:9200/_cluster/settings" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "85%",
    "cluster.routing.allocation.disk.watermark.high": "90%",
    "cluster.routing.allocation.disk.watermark.flood_stage": "95%"
  }
}'

# Set up alert when disk > 80%
```

### **❌ No Log Rotation**
```bash
# Logs grow indefinitely
ls -lh /var/log/opensearch/
# production-cluster.log is 10GB! ❌

# Create logrotate config
sudo nano /etc/logrotate.d/opensearch

/var/log/opensearch/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 opensearch opensearch
}
```

### **❌ Wrong Permissions on Data Directory**
```bash
# After manual creation, forgetting to set ownership
sudo mkdir -p /var/lib/opensearch/data
# Missing:
sudo chown -R opensearch:opensearch /var/lib/opensearch

# Verify permissions
ls -la /var/lib/opensearch
# Should show: drwxr-xr-x opensearch opensearch
```

---

## **6. Cluster Configuration Mistakes**

### **❌ Wrong Discovery Settings**
```yaml
# Single-node but using cluster discovery
discovery.type: zen  # ❌ Wrong for single node
discovery.seed_hosts: ["localhost"]

# Correct for single node:
discovery.type: single-node

# Correct for cluster (3 nodes):
discovery.seed_hosts: ["node-1:9300", "node-2:9300", "node-3:9300"]
cluster.initial_cluster_manager_nodes: ["node-1", "node-2", "node-3"]
```

### **❌ Not Setting initial_cluster_manager_nodes**
```yaml
# In multi-node cluster, forgetting this causes split-brain
# Missing:
cluster.initial_cluster_manager_nodes: ["node-1", "node-2", "node-3"]

# Results in:
# - Nodes don't form cluster
# - Each node thinks it's master
# - Data inconsistency
```

### **❌ Mismatched cluster.name**
```yaml
# Node-1:
cluster.name: production-cluster

# Node-2:
cluster.name: production  # ❌ Typo! Won't join

# Verify cluster name on all nodes
grep "cluster.name" /etc/opensearch/opensearch.yml
```

### **❌ Wrong Node Roles**
```yaml
# Making all nodes master-eligible but no data nodes
node.roles: [cluster_manager]  # ❌ No place to store data!

# Or opposite - no master-eligible nodes
node.roles: [data, ingest]  # ❌ No master election possible!

# Correct for balanced cluster:
node.roles: [cluster_manager, data, ingest]
```

### **❌ Not Configuring Replicas Properly**
```bash
# Single-node cluster with replica shards
# Cluster stays YELLOW because replicas can't be allocated

# Check:
curl -XGET "https://localhost:9200/_cluster/health?pretty" -u admin:admin --insecure
# Status: yellow, unassigned_shards: X

# Fix for single-node:
curl -XPUT "https://localhost:9200/_template/default" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["*"],
  "order": -1,
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}'
```

---

## **7. Performance Tuning Mistakes**

### **❌ Not Tuning Refresh Interval**
```yaml
# Default refresh_interval: 1s (very frequent!)
# Fine for dev, wasteful in production

# Beginners don't tune per use case:

# High-write scenario (logs):
PUT /logs-*/_settings
{
  "index.refresh_interval": "30s"
}

# Near real-time search (e-commerce):
PUT /products/_settings
{
  "index.refresh_interval": "5s"
}

# Bulk loading (disable during load):
PUT /bulk-data/_settings
{
  "index.refresh_interval": "-1"
}
# Re-enable after:
PUT /bulk-data/_settings
{
  "index.refresh_interval": "30s"
}
```

### **❌ Too Many Shards**
```bash
# Creating too many small shards
# Each shard has overhead (~10MB memory)

# WRONG for small index (1GB):
"number_of_shards": 10  # 100MB per shard, too small!

# Rule of thumb:
# - Shard size: 10-50GB
# - Max shards per node: 1000
# - For 1GB index: 1 shard
# - For 100GB index: 3-5 shards

# Check shard distribution
curl -XGET "https://localhost:9200/_cat/shards?v&s=index" -u admin:admin --insecure
```

### **❌ Not Using Bulk API**
```python
# WRONG: Individual inserts (100 documents)
for doc in documents:
    requests.post('https://node-1:9200/index/_doc', json=doc)
# Result: 100 HTTP requests, slow!

# CORRECT: Bulk API
bulk_data = ""
for doc in documents:
    bulk_data += json.dumps({"index": {"_index": "index"}}) + "\n"
    bulk_data += json.dumps(doc) + "\n"

requests.post('https://node-1:9200/_bulk', 
              data=bulk_data,
              headers={'Content-Type': 'application/x-ndjson'})
# Result: 1 HTTP request, 10-100x faster!
```

### **❌ Over-indexing Fields**
```json
// WRONG: Indexing everything
{
  "mappings": {
    "properties": {
      "description": {"type": "text"},  // Will be searched
      "metadata": {"type": "text"}       // Won't be searched! Waste
    }
  }
}

// CORRECT: Disable indexing for unused fields
{
  "mappings": {
    "properties": {
      "description": {"type": "text"},
      "metadata": {"type": "text", "index": false}  // Still stored, not indexed
    }
  }
}
```

---

## **8. Monitoring and Maintenance Mistakes**

### **❌ No Monitoring Setup**
```bash
# Beginners install and forget
# No idea when issues occur

# Minimum monitoring:
# 1. Cluster health
# 2. Disk space
# 3. JVM heap usage
# 4. CPU/memory
# 5. Query performance

# Create monitoring script (run via cron every 5 min)
sudo nano /usr/local/bin/opensearch-health-check.sh
```

```bash
#!/bin/bash
OPENSEARCH_URL="https://localhost:9200"
AUTH="admin:admin"
LOG="/var/log/opensearch/health-check.log"

echo "[$(date)] Health Check" >> $LOG

# Cluster health
HEALTH=$(curl -s -XGET "$OPENSEARCH_URL/_cluster/health" -u "$AUTH" --insecure | jq -r '.status')
if [ "$HEALTH" != "green" ]; then
    echo "WARNING: Cluster status is $HEALTH" >> $LOG
    # Send alert
fi

# Disk usage
DISK=$(df -h /var/lib/opensearch | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK -gt 80 ]; then
    echo "WARNING: Disk usage is ${DISK}%" >> $LOG
fi

# Heap usage
HEAP=$(curl -s -XGET "$OPENSEARCH_URL/_cat/nodes?h=heap.percent" -u "$AUTH" --insecure)
if [ $HEAP -gt 85 ]; then
    echo "WARNING: Heap usage is ${HEAP}%" >> $LOG
fi
```

### **❌ Not Checking Logs Regularly**
```bash
# Common log locations beginners miss:
/var/log/opensearch/production-cluster.log  # Main log
/var/log/opensearch/gc.log                   # GC log
/var/log/messages                            # System log
sudo journalctl -u opensearch                # Systemd log

# Set up log monitoring for errors
sudo grep -i "error\|exception\|failed" /var/log/opensearch/*.log
```

### **❌ No Slow Query Logging**
```bash
# Enable slow log to find problematic queries
curl -XPUT "https://localhost:9200/_cluster/settings" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "index.search.slowlog.threshold.query.warn": "10s",
    "index.search.slowlog.threshold.query.info": "5s",
    "index.search.slowlog.threshold.fetch.warn": "1s",
    "index.indexing.slowlog.threshold.index.warn": "10s"
  }
}'

# Check slow logs
tail -f /var/log/opensearch/production-cluster_index_search_slowlog.json
```

---

## **9. Backup and Recovery Mistakes**

### **❌ No Backup Strategy**
```bash
# Biggest mistake: Running production without backups!

# Minimum backup setup:
# 1. Configure snapshot repository
# 2. Schedule automatic snapshots
# 3. Test restore procedure

# Create snapshot repository
curl -XPUT "https://localhost:9200/_snapshot/backup_repo" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/var/backup/opensearch",
    "compress": true
  }
}'

# Test snapshot creation
curl -XPUT "https://localhost:9200/_snapshot/backup_repo/test_snapshot?wait_for_completion=true" \
  -u admin:admin --insecure
```

### **❌ Not Testing Restore**
```bash
# Creating backups but never testing restore = FALSE SENSE OF SECURITY

# Test restore procedure:
# 1. Create test index
curl -XPUT "https://localhost:9200/test_restore" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "settings": {"number_of_shards": 1, "number_of_replicas": 0}
}'

# 2. Add data
curl -XPOST "https://localhost:9200/test_restore/_doc" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'{"test": "data"}'

# 3. Take snapshot
curl -XPUT "https://localhost:9200/_snapshot/backup_repo/restore_test?wait_for_completion=true" \
  -u admin:admin --insecure

# 4. Delete index
curl -XDELETE "https://localhost:9200/test_restore" -u admin:admin --insecure

# 5. Restore from snapshot
curl -XPOST "https://localhost:9200/_snapshot/backup_repo/restore_test/_restore" \
  -u admin:admin --insecure

# 6. Verify data
curl -XGET "https://localhost:9200/test_restore/_search" -u admin:admin --insecure
```

### **❌ Storing Backups on Same Server**
```yaml
# Snapshot repository on same disk as data
path.repo: ["/var/lib/opensearch/backups"]  # ❌ Same disk as data!

# If disk fails, you lose both data AND backups!

# Better: Use remote storage
# - NFS mount
# - S3 (requires repository-s3 plugin)
# - Different server
```

---

## **10. Production Readiness Checklist**

### **Pre-Launch Checklist (What Beginners Skip)**

```bash
# System Configuration
☐ vm.max_map_count set to 262144 (and persisted)
☐ Swap disabled (and persisted in /etc/fstab)
☐ File descriptor limits set to 65536
☐ Memory lock enabled (ulimit -l = unlimited)
☐ SELinux configured (not disabled)

# Memory & JVM
☐ Heap size = 50% of RAM (max 32GB)
☐ Xms = Xmx (matching values)
☐ GC logging enabled
☐ System memory reserved for OS & Lucene cache

# Security
☐ Demo certificates replaced with production certs
☐ All default passwords changed
☐ HTTPS enabled for both OpenSearch & Dashboards
☐ Firewall configured (only necessary ports open)
☐ Security plugin enabled (not disabled)
☐ Role-based access control configured

# Storage
☐ Data directory on dedicated partition (not root)
☐ Log rotation configured
☐ Disk space monitoring set up
☐ Watermark thresholds configured

# Cluster Configuration (Multi-node)
☐ cluster.name identical on all nodes
☐ discovery.seed_hosts configured
☐ initial_cluster_manager_nodes set
☐ Node roles properly assigned
☐ Network connectivity between nodes verified
☐ Transport port (9300) open between nodes

# Performance
☐ refresh_interval tuned for use case
☐ Shard count appropriate for data size
☐ Index templates configured
☐ Bulk API used for ingestion
☐ Unused fields not indexed

# Monitoring
☐ Cluster health monitoring active
☐ Disk space alerts configured
☐ JVM heap alerts configured
☐ Slow query logging enabled
☐ Log aggregation set up

# Backup & Recovery
☐ Snapshot repository configured
☐ Automated snapshot schedule
☐ Snapshot retention policy
☐ Restore procedure tested
☐ Backups stored off-server

# Documentation
☐ Architecture diagram created
☐ Configuration documented
☐ Runbook for common issues
☐ Emergency contact list
☐ Disaster recovery plan
```

---

## **Quick Verification Commands**

Run these to catch common mistakes:

```bash
#!/bin/bash
echo "=== OpenSearch Health Check ==="

echo "1. Checking vm.max_map_count..."
sysctl vm.max_map_count | grep -q 262144 && echo "✓ OK" || echo "✗ FAIL"

echo "2. Checking swap..."
swapon -s | grep -q "Filename" && echo "✗ FAIL - Swap is ON" || echo "✓ OK - Swap is OFF"

echo "3. Checking file descriptor limits..."
sudo su - opensearch -c "ulimit -n" | grep -q "65536" && echo "✓ OK" || echo "✗ FAIL"

echo "4. Checking if OpenSearch is running..."
systemctl is-active opensearch && echo "✓ OK" || echo "✗ FAIL"

echo "5. Checking cluster health..."
HEALTH=$(curl -s -XGET "https://localhost:9200/_cluster/health" -u admin:admin --insecure | jq -r '.status')
echo "Status: $HEALTH"

echo "6. Checking heap usage..."
curl -s -XGET "https://localhost:9200/_cat/nodes?v&h=heap.percent,ram.percent" -u admin:admin --insecure

echo "7. Checking disk space..."
df -h /var/lib/opensearch

echo "8. Checking for demo certificates..."
grep -q "DEMO" /var/log/opensearch/*.log && echo "✗ WARNING - Using demo certificates!" || echo "✓ OK"

echo "9. Checking default password..."
curl -s -XGET "https://localhost:9200" -u admin:admin --insecure > /dev/null 2>&1 && echo "✗ WARNING - Still using default password!" || echo "✓ OK"

echo "10. Checking firewall..."
sudo firewall-cmd --list-ports | grep -q "9200\|9300" && echo "✓ OK" || echo "✗ FAIL"
```

Save this as `/usr/local/bin/opensearch-verify.sh` and run before going live!

---

## **Most Critical Mistakes (Top 5)**

1. **Not persisting system tuning** - Settings lost on reboot
2. **Wrong heap size** - Performance issues or OOM
3. **Using demo certificates** - Major security vulnerability
4. **No backups** - Data loss when (not if) something fails
5. **No monitoring** - Problems go unnoticed until catastrophic failure

**Pro Tip:** Set calendar reminders:
- Daily: Check cluster health
- Weekly: Review logs
- Monthly: Test backup restore
- Quarterly: Capacity planning review

This comprehensive list should help beginners avoid the most common pitfalls!
