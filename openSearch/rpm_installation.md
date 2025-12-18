the RPM installation method to the guide. This is actually the recommended approach for RHEL systems as it provides better system integration.

---

## **Installation Methods**

# **Method 1: RPM Installation (Recommended for RHEL)**

### **1. Import OpenSearch GPG Key**
```bash
sudo rpm --import https://artifacts.opensearch.org/publickeys/opensearch.pgp
```

### **2. Create YUM Repository**
```bash
sudo tee /etc/yum.repos.d/opensearch.repo << EOF
[opensearch-2.x]
name=OpenSearch 2.x
baseurl=https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/yum
enabled=1
gpgcheck=1
gpgkey=https://artifacts.opensearch.org/publickeys/opensearch.pgp
EOF
```

### **3. Install Java (OpenJDK 17)**
```bash
sudo dnf install -y java-17-openjdk java-17-openjdk-devel

# Verify installation
java -version
```

### **4. Install OpenSearch**
```bash
# Install OpenSearch package
sudo dnf install -y opensearch

# The RPM creates:
# - User: opensearch
# - Home: /usr/share/opensearch
# - Config: /etc/opensearch
# - Data: /var/lib/opensearch
# - Logs: /var/log/opensearch
```

### **5. System Tuning (Same as tarball method)**
```bash
# Increase virtual memory limits
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# Disable swap
sudo swapoff -a
# Comment out swap in /etc/fstab

# File descriptor limits (already set by RPM, but verify)
sudo tee -a /etc/security/limits.conf << EOF
opensearch soft nofile 65536
opensearch hard nofile 65536
opensearch soft nproc 4096
opensearch hard nproc 4096
opensearch soft memlock unlimited
opensearch hard memlock unlimited
EOF
```

### **6. Configure opensearch.yml**
```bash
sudo nano /etc/opensearch/opensearch.yml
```

**Production configuration:**
```yaml
# Cluster settings
cluster.name: production-cluster
node.name: node-1

# Paths (already set by RPM)
path.data: /var/lib/opensearch
path.logs: /var/log/opensearch

# Network settings
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

# Discovery (single-node for your resources)
discovery.type: single-node

# Memory lock
bootstrap.memory_lock: true

# Security plugin settings
plugins.security.disabled: false
plugins.security.ssl.http.enabled: true
plugins.security.ssl.http.pemcert_filepath: esnode.pem
plugins.security.ssl.http.pemkey_filepath: esnode-key.pem
plugins.security.ssl.http.pemtrustedcas_filepath: root-ca.pem
plugins.security.ssl.transport.pemcert_filepath: esnode.pem
plugins.security.ssl.transport.pemkey_filepath: esnode-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: root-ca.pem
plugins.security.ssl.transport.enforce_hostname_verification: false
plugins.security.allow_default_init_securityindex: true
plugins.security.authcz.admin_dn:
  - CN=kirk,OU=client,O=client,L=test,C=de

# Performance settings for limited resources
indices.memory.index_buffer_size: 20%
indices.queries.cache.size: 10%
```

### **7. Configure JVM Heap Size**
```bash
sudo nano /etc/opensearch/jvm.options
```

**Set heap to 3GB (50% of 6GB limit):**
```bash
# Modify these lines:
-Xms3g
-Xmx3g

# Keep G1GC settings:
-XX:+UseG1GC
-XX:G1ReservePercent=25
-XX:InitiatingHeapOccupancyPercent=30
```

### **8. Configure Resource Limits in Systemd**
```bash
sudo mkdir -p /etc/systemd/system/opensearch.service.d/
sudo nano /etc/systemd/system/opensearch.service.d/override.conf
```

**Add resource limits:**
```ini
[Service]
# Memory limits
MemoryLimit=6G
MemoryAccounting=true

# CPU limits
CPUQuota=300%
CPUAccounting=true

# File descriptor limits
LimitNOFILE=65536
LimitNPROC=4096
LimitMEMLOCK=infinity
```

### **9. SELinux Configuration (RHEL Specific)**
```bash
# Check SELinux status
getenforce

# If SELinux is enforcing, configure policies
sudo semanage port -a -t opensearch_port_t -p tcp 9200
sudo semanage port -a -t opensearch_port_t -p tcp 9300

# Allow OpenSearch to bind to network
sudo setsebool -P opensearch_can_network_connect 1

# If issues persist, check audit logs
sudo ausearch -m avc -ts recent | grep opensearch
```

### **10. Firewall Configuration**
```bash
sudo firewall-cmd --permanent --add-port=9200/tcp
sudo firewall-cmd --permanent --add-port=9300/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

### **11. Disable Demo Security Configuration**
```bash
# Remove demo certificates and install production ones
# Or run security initialization
sudo /usr/share/opensearch/bin/opensearch-plugin install --batch opensearch-security

# Initialize security
cd /usr/share/opensearch
sudo -u opensearch bash -c "OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./plugins/opensearch-security/tools/install_demo_configuration.sh -y -i -s"
```

### **12. Start and Enable OpenSearch**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable opensearch

# Start service
sudo systemctl start opensearch

# Check status
sudo systemctl status opensearch

# View logs
sudo journalctl -u opensearch -f

# Or check log files
sudo tail -f /var/log/opensearch/production-cluster.log
```

### **13. Verify Installation**
```bash
# Wait for OpenSearch to start (30-60 seconds)
sleep 60

# Test connection (default password: admin/admin)
curl -XGET https://localhost:9200 -u 'admin:admin' --insecure

# Check cluster health
curl -XGET https://localhost:9200/_cluster/health?pretty -u 'admin:admin' --insecure

# Expected output:
# {
#   "cluster_name" : "production-cluster",
#   "status" : "green",
#   "number_of_nodes" : 1
# }
```

### **14. Change Default Passwords**
```bash
# Generate password hash
cd /usr/share/opensearch/plugins/opensearch-security/tools
sudo -u opensearch bash -c "OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./hash.sh"

# Enter your new password and copy the hash
# Update internal_users.yml
sudo nano /etc/opensearch/opensearch-security/internal_users.yml

# Find the admin user section and replace hash:
# admin:
#   hash: "$2y$12$YOUR_NEW_HASH_HERE"
#   reserved: true
#   backend_roles:
#   - "admin"

# Apply security configuration
sudo /usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh \
  -cd /etc/opensearch/opensearch-security \
  -icl -nhnv \
  -cacert /etc/opensearch/root-ca.pem \
  -cert /etc/opensearch/kirk.pem \
  -key /etc/opensearch/kirk-key.pem

# Restart OpenSearch
sudo systemctl restart opensearch
```

---

# **Method 2: Tarball Installation (Alternative)**

*See the complete tarball installation steps provided earlier in the guide.*

---

## **RPM vs Tarball: Which to Choose?**

| Feature | RPM Installation | Tarball Installation |
|---------|-----------------|---------------------|
| **System Integration** | ✅ Better (systemd, paths) | ⚠️ Manual setup needed |
| **Updates** | ✅ `dnf update opensearch` | ⚠️ Manual download |
| **Uninstall** | ✅ `dnf remove opensearch` | ⚠️ Manual cleanup |
| **SELinux** | ✅ Better compatibility | ⚠️ May need adjustments |
| **Customization** | ⚠️ Standard paths | ✅ Full control |
| **Multi-version** | ⚠️ One version per system | ✅ Side-by-side installs |

**Recommendation**: Use **RPM for production** on RHEL 9.6 for easier management and updates.

---

## **Post-Installation Steps (Both Methods)**

### **Configure Log Rotation**
```bash
sudo nano /etc/logrotate.d/opensearch
```

```bash
/var/log/opensearch/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 opensearch opensearch
    sharedscripts
    postrotate
        /bin/kill -HUP `cat /var/run/opensearch/opensearch.pid 2>/dev/null` 2>/dev/null || true
    endscript
}
```

### **Monitoring Scripts**
```bash
# Create monitoring script
sudo nano /usr/local/bin/opensearch-monitor.sh
```

```bash
#!/bin/bash
# OpenSearch Monitoring Script

OPENSEARCH_URL="https://localhost:9200"
ADMIN_USER="admin"
ADMIN_PASS="your-password"

echo "=== OpenSearch Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Cluster Health
echo "Cluster Health:"
curl -s -XGET "${OPENSEARCH_URL}/_cluster/health?pretty" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" --insecure

# Node Stats
echo -e "\nNode Stats:"
curl -s -XGET "${OPENSEARCH_URL}/_cat/nodes?v&h=name,heap.percent,ram.percent,cpu,disk.used_percent" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" --insecure

# Index Stats
echo -e "\nIndex Stats:"
curl -s -XGET "${OPENSEARCH_URL}/_cat/indices?v&h=index,docs.count,store.size,health" \
  -u "${ADMIN_USER}:${ADMIN_PASS}" --insecure

# Disk Usage
echo -e "\nDisk Usage (/var):"
df -h /var
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/opensearch-monitor.sh

# Test it
sudo /usr/local/bin/opensearch-monitor.sh
```

### **Setup Automated Backups (Snapshot Repository)**
```bash
# Create backup directory
sudo mkdir -p /var/backup/opensearch
sudo chown opensearch:opensearch /var/backup/opensearch

# Register snapshot repository
curl -XPUT "https://localhost:9200/_snapshot/backup_repo" \
  -u "admin:your-password" --insecure \
  -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/var/backup/opensearch",
    "compress": true
  }
}'

# Create a snapshot
curl -XPUT "https://localhost:9200/_snapshot/backup_repo/snapshot_1?wait_for_completion=true" \
  -u "admin:your-password" --insecure
```

### **Performance Tuning for Your Specs**

```bash
# Index template for single-node setup
curl -XPUT "https://localhost:9200/_index_template/production_template" \
  -u "admin:your-password" --insecure \
  -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "refresh_interval": "30s",
      "translog.durability": "async",
      "translog.sync_interval": "30s"
    }
  }
}'
```

### **Cron Jobs for Maintenance**
```bash
sudo crontab -e -u opensearch
```

```bash
# Daily health check at 2 AM
0 2 * * * /usr/local/bin/opensearch-monitor.sh >> /var/log/opensearch/monitor.log 2>&1

# Weekly snapshot at 3 AM Sunday
0 3 * * 0 curl -XPUT "https://localhost:9200/_snapshot/backup_repo/snapshot_$(date +\%Y\%m\%d)" -u "admin:password" --insecure

# Daily cleanup of old snapshots (keep last 7)
0 4 * * * curl -XDELETE "https://localhost:9200/_snapshot/backup_repo/snapshot_$(date -d '7 days ago' +\%Y\%m\%d)" -u "admin:password" --insecure
```

---

## **Troubleshooting**

### **Common Issues:**

1. **Service fails to start:**
```bash
# Check logs
sudo journalctl -xeu opensearch
sudo tail -100 /var/log/opensearch/production-cluster.log

# Check Java version
java -version

# Verify memory lock
sudo su - opensearch -c "ulimit -l"
```

2. **Out of Memory:**
```bash
# Check heap usage
curl -XGET 'https://localhost:9200/_cat/nodes?v&h=heap.percent' -u admin:password --insecure

# Reduce heap if needed (to 2GB)
sudo sed -i 's/-Xms3g/-Xms2g/' /etc/opensearch/jvm.options
sudo sed -i 's/-Xmx3g/-Xmx2g/' /etc/opensearch/jvm.options
sudo systemctl restart opensearch
```

3. **Disk Space Issues:**
```bash
# Check disk usage
df -h /var

# Clean old logs
sudo find /var/log/opensearch -name "*.log.*" -mtime +7 -delete

# Set cluster watermark
curl -XPUT "https://localhost:9200/_cluster/settings" \
  -u "admin:password" --insecure \
  -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "85%",
    "cluster.routing.allocation.disk.watermark.high": "90%"
  }
}'
```

4. **Connection refused:**
```bash
# Check if service is running
sudo systemctl status opensearch

# Check if port is listening
sudo ss -tlnp | grep 9200

# Check firewall
sudo firewall-cmd --list-all

# Check SELinux denials
sudo ausearch -m avc -ts recent
```

---

## **Production Checklist**

- ✅ Java 17 installed
- ✅ System tuning applied (vm.max_map_count, limits)
- ✅ SELinux configured (RHEL specific)
- ✅ Firewall rules configured
- ✅ Heap size set to 3GB
- ✅ Resource limits configured in systemd
- ✅ Default passwords changed
- ✅ SSL/TLS enabled
- ✅ Snapshot repository configured
- ✅ Log rotation configured
- ✅ Monitoring script created
- ✅ Backup schedule configured
- ✅ Single-node discovery configured

Your OpenSearch installation is now production-ready on RHEL 9.6!
