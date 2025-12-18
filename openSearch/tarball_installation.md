I'll provide a comprehensive guide for installing OpenSearch on RHEL 9.6 with production-ready configurations tailored to your server specs.

## **Minimum Prerequisites**

### System Requirements:
- **Java**: OpenSearch requires Java 11 or later (OpenJDK recommended)
- **Memory**: Minimum 4 GB RAM (you have 6 GB allocated - suitable)
- **Disk Space**: Minimum 10 GB (you have 20 GB in /var - adequate for small production)
- **CPU**: Minimum 2 cores (you have 3 cores allocated - good)
- **User**: Non-root user for running OpenSearch (security best practice)

### System Tuning:
```bash
# 1. Increase virtual memory limits
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# 2. Disable swap (recommended for production)
sudo swapoff -a
# Comment out swap entries in /etc/fstab to persist

# 3. Increase file descriptor limits
sudo tee -a /etc/security/limits.conf << EOF
opensearch soft nofile 65536
opensearch hard nofile 65536
opensearch soft nproc 4096
opensearch hard nproc 4096
opensearch soft memlock unlimited
opensearch hard memlock unlimited
EOF
```

---

## **Installation Steps**

### **1. Install Java (OpenJDK 17)**
```bash
sudo dnf install -y java-17-openjdk java-17-openjdk-devel

# Verify installation
java -version
```

### **2. Create OpenSearch User**
```bash
sudo useradd -m -s /bin/bash opensearch
```

### **3. Download and Install OpenSearch**
```bash
# Download OpenSearch (version 2.11.1 - latest stable as of Jan 2025)
cd /tmp
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.1/opensearch-2.11.1-linux-x64.tar.gz

# Verify checksum (optional but recommended)
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.1/opensearch-2.11.1-linux-x64.tar.gz.sha512
sha512sum -c opensearch-2.11.1-linux-x64.tar.gz.sha512

# Extract to /opt
sudo tar -xzf opensearch-2.11.1-linux-x64.tar.gz -C /opt/
sudo mv /opt/opensearch-2.11.1 /opt/opensearch

# Set ownership
sudo chown -R opensearch:opensearch /opt/opensearch
```

### **4. Configure Data and Log Directories**
```bash
# Create directories in /var (where you have 20GB)
sudo mkdir -p /var/lib/opensearch/data
sudo mkdir -p /var/log/opensearch
sudo chown -R opensearch:opensearch /var/lib/opensearch
sudo chown -R opensearch:opensearch /var/log/opensearch
```

---

## **Production Configuration**

### **5. Configure opensearch.yml**
```bash
sudo nano /opt/opensearch/config/opensearch.yml
```

**Production configuration for your specs:**
```yaml
# Cluster settings
cluster.name: production-cluster
node.name: node-1

# Paths
path.data: /var/lib/opensearch/data
path.logs: /var/log/opensearch

# Network settings
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

# Discovery (single-node setup for your resources)
discovery.type: single-node

# Memory and performance
bootstrap.memory_lock: true

# Security plugin settings (disable demo config for production)
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

# Index settings for limited resources
indices.memory.index_buffer_size: 20%
indices.queries.cache.size: 10%
```

### **6. Configure JVM Options (Critical for 6GB Memory Limit)**
```bash
sudo nano /opt/opensearch/config/jvm.options
```

**Set heap size to 3GB (50% of your 6GB limit):**
```bash
# Edit these lines:
-Xms3g
-Xmx3g

# Keep these important settings:
-XX:+UseG1GC
-XX:G1ReservePercent=25
-XX:InitiatingHeapOccupancyPercent=30
```

### **7. Firewall Configuration**
```bash
sudo firewall-cmd --permanent --add-port=9200/tcp
sudo firewall-cmd --permanent --add-port=9300/tcp
sudo firewall-cmd --reload
```

### **8. Create Systemd Service**
```bash
sudo nano /etc/systemd/system/opensearch.service
```

```ini
[Unit]
Description=OpenSearch
Documentation=https://opensearch.org/docs/
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=opensearch
Group=opensearch
Environment=OPENSEARCH_HOME=/opt/opensearch
Environment=OPENSEARCH_PATH_CONF=/opt/opensearch/config
Environment=OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk

WorkingDirectory=/opt/opensearch

ExecStart=/opt/opensearch/bin/opensearch

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
LimitMEMLOCK=infinity
LimitCPU=180m
MemoryLimit=6G

# Security
StandardOutput=journal
StandardError=journal
SyslogIdentifier=opensearch

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### **9. Initialize Security**
```bash
# Set environment variables
sudo -u opensearch bash << 'EOF'
export OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk
cd /opt/opensearch
./opensearch-tar-install.sh
EOF
```

### **10. Start OpenSearch**
```bash
sudo systemctl daemon-reload
sudo systemctl enable opensearch
sudo systemctl start opensearch

# Check status
sudo systemctl status opensearch

# Monitor logs
sudo tail -f /var/log/opensearch/production-cluster.log
```

---

## **Post-Installation Configuration**

### **11. Change Default Admin Password**
```bash
cd /opt/opensearch/plugins/opensearch-security/tools

# Set admin password
sudo -u opensearch bash -c "OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./hash.sh"
# Enter your new password and copy the hash

# Update internal_users.yml
sudo nano /opt/opensearch/config/opensearch-security/internal_users.yml
# Replace the admin hash with your new hash

# Apply security configuration
sudo -u opensearch bash -c "cd /opt/opensearch && OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./plugins/opensearch-security/tools/securityadmin.sh -cd config/opensearch-security -icl -nhnv -cacert config/root-ca.pem -cert config/kirk.pem -key config/kirk-key.pem"
```

### **12. Verify Installation**
```bash
# Test connection (use your new admin password)
curl -XGET https://localhost:9200 -u 'admin:your-password' --insecure

# Check cluster health
curl -XGET https://localhost:9200/_cluster/health?pretty -u 'admin:your-password' --insecure
```

---

## **Production Recommendations for Your Setup**

### **Resource Optimization:**
1. **Heap Size**: 3GB is optimal (50% of 6GB)
2. **Index Refresh Interval**: Increase to 30s for write-heavy workloads
   ```bash
   PUT /_all/_settings
   {
     "index.refresh_interval": "30s"
   }
   ```

3. **Shard Allocation**: Single primary shard for indices (no replicas in single-node)

### **Monitoring:**
```bash
# Install OpenSearch Dashboards (optional, requires additional resources)
# Alternatively, use curl commands or external monitoring tools

# Monitor heap usage
curl -XGET 'https://localhost:9200/_cat/nodes?v&h=heap.percent,ram.percent,cpu' -u admin:password --insecure
```

### **Backup Strategy:**
```bash
# Configure snapshot repository (recommended for production)
# Use S3, NFS, or local filesystem
```

### **Important Notes:**
- Your 20GB /var partition will fill quickly with logs and data - monitor disk usage
- Consider log rotation for /var/log/opensearch
- Single-node setup means no high availability - plan for backups
- 6GB memory with 3GB heap leaves 3GB for OS and Lucene file caching
- Monitor performance and adjust settings based on workload

This configuration is optimized for your resource constraints while maintaining production readiness!
