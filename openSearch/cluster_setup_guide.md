I'll provide a comprehensive guide for creating a 3-node OpenSearch cluster, explain the master election algorithm, and show you how to set up OpenSearch Dashboards.

---

# **Part 1: 3-Node OpenSearch Cluster Setup**

## **Cluster Architecture**

```
Server Layout:
├── node-1 (Master-eligible, Data, Ingest) - 192.168.1.101
├── node-2 (Master-eligible, Data, Ingest) - 192.168.1.102
└── node-3 (Master-eligible, Data, Ingest) - 192.168.1.103
```

---

## **Master Election Algorithm in OpenSearch**

### **Algorithm: Zen Discovery (Modified Raft-based)**

OpenSearch uses a **consensus-based master election** algorithm derived from the Zen Discovery protocol, which incorporates principles from the Raft consensus algorithm.

**Key Components:**

1. **Master-Eligible Nodes**: Only nodes with `node.roles: [cluster_manager]` can be elected
2. **Quorum Requirement**: Requires majority (n/2 + 1) of master-eligible nodes
3. **Term-based Election**: Each election has a unique term number
4. **Split-Brain Prevention**: Uses `cluster.initial_cluster_manager_nodes` setting

**Election Process:**

```
Step 1: Detection Phase
├── Node detects master is unavailable
├── Waits for discovery.zen.ping_timeout (default: 3s)
└── Initiates election if no master found

Step 2: Voting Phase
├── Node increments term number
├── Sends vote requests to all master-eligible nodes
├── Collects votes (each node votes once per term)
└── Requires majority: (n/2 + 1) votes

Step 3: Leader Selection
├── Node with majority votes becomes master
├── Tie-breaking: Node with lowest ID wins
├── New master publishes cluster state
└── All nodes acknowledge new master

Step 4: Verification
├── Master sends heartbeats (ping)
├── Nodes respond with acknowledgment
└── Failure triggers new election
```

**Split-Brain Prevention:**
- **minimum_master_nodes** (legacy): Set to (n/2 + 1)
- For 3 nodes: minimum = (3/2 + 1) = 2
- Prevents cluster from accepting writes without quorum

**Example Election Scenario:**
```
Initial State:
- Node-1: Master (Term 5)
- Node-2: Data (Following Node-1)
- Node-3: Data (Following Node-1)

Master Failure:
- Node-1 crashes
- Node-2 detects failure after 3s
- Node-3 detects failure after 3s

Election:
- Node-2 increments term to 6, requests votes
- Node-3 increments term to 6, requests votes
- Node-2 votes for itself (1 vote)
- Node-3 votes for Node-2 (Node-2 has lower ID)
- Node-2 receives 2 votes (majority), becomes master
```

---

## **Cluster Installation - RPM Method**

### **Prerequisites (All 3 Nodes)**

```bash
# On all nodes, add entries to /etc/hosts
sudo tee -a /etc/hosts << EOF
192.168.1.101 node-1 node-1.example.com
192.168.1.102 node-2 node-2.example.com
192.168.1.103 node-3 node-3.example.com
EOF

# System tuning (all nodes)
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# Disable swap
sudo swapoff -a

# Firewall rules (all nodes)
sudo firewall-cmd --permanent --add-port=9200/tcp
sudo firewall-cmd --permanent --add-port=9300/tcp
sudo firewall-cmd --reload
```

### **Install OpenSearch (All 3 Nodes)**

```bash
# Import GPG key
sudo rpm --import https://artifacts.opensearch.org/publickeys/opensearch.pgp

# Create repository
sudo tee /etc/yum.repos.d/opensearch.repo << EOF
[opensearch-2.x]
name=OpenSearch 2.x
baseurl=https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/yum
enabled=1
gpgcheck=1
gpgkey=https://artifacts.opensearch.org/publickeys/opensearch.pgp
EOF

# Install Java and OpenSearch
sudo dnf install -y java-17-openjdk opensearch
```

---

## **Node Configuration**

### **Node-1 Configuration (192.168.1.101)**

```bash
sudo vi /etc/opensearch/opensearch.yml
```

```yaml
# Cluster configuration
cluster.name: production-cluster

# Node configuration
node.name: node-1
node.roles: [cluster_manager, data, ingest]

# Paths
path.data: /var/lib/opensearch
path.logs: /var/log/opensearch

# Network
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

# Discovery and cluster formation
discovery.seed_hosts: ["node-1:9300", "node-2:9300", "node-3:9300"]
cluster.initial_cluster_manager_nodes: ["node-1", "node-2", "node-3"]

# Memory
bootstrap.memory_lock: true

# Security - TLS/SSL Configuration
plugins.security.ssl.transport.pemcert_filepath: esnode.pem
plugins.security.ssl.transport.pemkey_filepath: esnode-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: root-ca.pem
plugins.security.ssl.transport.enforce_hostname_verification: false
plugins.security.ssl.http.enabled: true
plugins.security.ssl.http.pemcert_filepath: esnode.pem
plugins.security.ssl.http.pemkey_filepath: esnode-key.pem
plugins.security.ssl.http.pemtrustedcas_filepath: root-ca.pem
plugins.security.allow_unsafe_democertificates: true
plugins.security.allow_default_init_securityindex: true

plugins.security.authcz.admin_dn:
  - CN=kirk,OU=client,O=client,L=test,C=de

plugins.security.nodes_dn:
  - CN=node-1.example.com,OU=node,O=node,L=test,C=de
  - CN=node-2.example.com,OU=node,O=node,L=test,C=de
  - CN=node-3.example.com,OU=node,O=node,L=test,C=de

# Cluster settings
cluster.routing.allocation.disk.threshold_enabled: true
cluster.routing.allocation.disk.watermark.low: 85%
cluster.routing.allocation.disk.watermark.high: 90%

# Performance tuning
indices.memory.index_buffer_size: 20%
indices.queries.cache.size: 10%
```

### **Node-2 Configuration (192.168.1.102)**

```bash
sudo vi /etc/opensearch/opensearch.yml
```

```yaml
# Cluster configuration
cluster.name: production-cluster

# Node configuration
node.name: node-2
node.roles: [cluster_manager, data, ingest]

# Paths
path.data: /var/lib/opensearch
path.logs: /var/log/opensearch

# Network
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

# Discovery and cluster formation
discovery.seed_hosts: ["node-1:9300", "node-2:9300", "node-3:9300"]
cluster.initial_cluster_manager_nodes: ["node-1", "node-2", "node-3"]

# Memory
bootstrap.memory_lock: true

# Security - Same as Node-1 (with appropriate node DN)
plugins.security.ssl.transport.pemcert_filepath: esnode.pem
plugins.security.ssl.transport.pemkey_filepath: esnode-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: root-ca.pem
plugins.security.ssl.transport.enforce_hostname_verification: false
plugins.security.ssl.http.enabled: true
plugins.security.ssl.http.pemcert_filepath: esnode.pem
plugins.security.ssl.http.pemkey_filepath: esnode-key.pem
plugins.security.ssl.http.pemtrustedcas_filepath: root-ca.pem
plugins.security.allow_unsafe_democertificates: true
plugins.security.allow_default_init_securityindex: true

plugins.security.authcz.admin_dn:
  - CN=kirk,OU=client,O=client,L=test,C=de

plugins.security.nodes_dn:
  - CN=node-1.example.com,OU=node,O=node,L=test,C=de
  - CN=node-2.example.com,OU=node,O=node,L=test,C=de
  - CN=node-3.example.com,OU=node,O=node,L=test,C=de

# Cluster settings
cluster.routing.allocation.disk.threshold_enabled: true
cluster.routing.allocation.disk.watermark.low: 85%
cluster.routing.allocation.disk.watermark.high: 90%

# Performance tuning
indices.memory.index_buffer_size: 20%
indices.queries.cache.size: 10%
```

### **Node-3 Configuration (192.168.1.103)**

Same as Node-2, but change:
```yaml
node.name: node-3
```

---

## **JVM Configuration (All Nodes)**

```bash
sudo vi /etc/opensearch/jvm.options
```

```bash
# Heap size - 3GB for 6GB RAM systems
-Xms3g
-Xmx3g

# GC Configuration
-XX:+UseG1GC
-XX:G1ReservePercent=25
-XX:InitiatingHeapOccupancyPercent=30
```

---

## **Generate Production SSL Certificates**

### **Option 1: Use Demo Certificates (Testing Only)**

```bash
# On all nodes
cd /usr/share/opensearch
sudo -u opensearch bash -c "OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./plugins/opensearch-security/tools/install_demo_configuration.sh -y -i -s"
```

### **Option 2: Generate Production Certificates**

```bash
# On node-1, install OpenSSL
sudo dnf install -y openssl

# Create certificate directory
sudo mkdir -p /etc/opensearch/certs
cd /etc/opensearch/certs

# 1. Create Root CA
sudo openssl genrsa -out root-ca-key.pem 2048
sudo openssl req -new -x509 -sha256 -key root-ca-key.pem -out root-ca.pem -days 730 \
  -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=root.example.com"

# 2. Create Admin Certificate
sudo openssl genrsa -out kirk-key-temp.pem 2048
sudo openssl pkcs8 -inform PEM -outform PEM -in kirk-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out kirk-key.pem
sudo openssl req -new -key kirk-key.pem -out kirk.csr \
  -subj "/C=DE/L=test/O=client/OU=client/CN=kirk"
sudo openssl x509 -req -in kirk.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -sha256 -out kirk.pem -days 730

# 3. Create Node Certificate (repeat for each node)
sudo openssl genrsa -out node-1-key-temp.pem 2048
sudo openssl pkcs8 -inform PEM -outform PEM -in node-1-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out esnode-key.pem
sudo openssl req -new -key esnode-key.pem -out node-1.csr \
  -subj "/C=DE/L=test/O=node/OU=node/CN=node-1.example.com"
sudo openssl x509 -req -in node-1.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -sha256 -out esnode.pem -days 730

# Copy certificates to config directory
sudo cp root-ca.pem kirk.pem kirk-key.pem esnode.pem esnode-key.pem /etc/opensearch/
sudo chown opensearch:opensearch /etc/opensearch/*.pem
sudo chmod 600 /etc/opensearch/*-key.pem

# Copy to other nodes via SCP
sudo scp /etc/opensearch/*.pem node-2:/etc/opensearch/
sudo scp /etc/opensearch/*.pem node-3:/etc/opensearch/
```

---

## **Start the Cluster**

```bash
# Start on all nodes (one by one)
# Node-1 first
sudo systemctl daemon-reload
sudo systemctl enable opensearch
sudo systemctl start opensearch

# Wait 30 seconds, then start Node-2
sudo systemctl start opensearch

# Wait 30 seconds, then start Node-3
sudo systemctl start opensearch

# Check cluster formation
sudo journalctl -u opensearch -f
```

---

## **Verify Cluster**

```bash
# Check cluster health
curl -XGET "https://node-1:9200/_cluster/health?pretty" -u admin:admin --insecure

# Expected output:
# {
#   "cluster_name" : "production-cluster",
#   "status" : "green",
#   "number_of_nodes" : 3,
#   "number_of_data_nodes" : 3,
#   "active_primary_shards" : X,
#   "active_shards" : X,
#   "relocating_shards" : 0,
#   "initializing_shards" : 0,
#   "unassigned_shards" : 0
# }

# Check nodes
curl -XGET "https://node-1:9200/_cat/nodes?v" -u admin:admin --insecure

# Check master
curl -XGET "https://node-1:9200/_cat/master?v" -u admin:admin --insecure

# Check cluster settings
curl -XGET "https://node-1:9200/_cluster/settings?pretty" -u admin:admin --insecure
```

---

# **Part 2: OpenSearch Dashboards Installation**

## **Install OpenSearch Dashboards (Dedicated Server or Node-1)**

### **System Requirements for Dashboards:**
- **RAM**: 2-4 GB (separate from OpenSearch)
- **CPU**: 2 cores
- **Disk**: 5 GB

### **Installation Steps**

```bash
# Install on a separate server or on node-1
# Import GPG key (if not already done)
sudo rpm --import https://artifacts.opensearch.org/publickeys/opensearch.pgp

# Create repository
sudo tee /etc/yum.repos.d/opensearch-dashboards.repo << EOF
[opensearch-dashboards-2.x]
name=OpenSearch Dashboards 2.x
baseurl=https://artifacts.opensearch.org/releases/bundle/opensearch-dashboards/2.x/yum
enabled=1
gpgcheck=1
gpgkey=https://artifacts.opensearch.org/publickeys/opensearch.pgp
EOF

# Install OpenSearch Dashboards
sudo dnf install -y opensearch-dashboards
```

---

## **Configure OpenSearch Dashboards**

```bash
sudo vi /etc/opensearch-dashboards/opensearch_dashboards.yml
```

```yaml
# Server configuration
server.port: 5601
server.host: "0.0.0.0"
server.name: "opensearch-dashboards"

# OpenSearch cluster connection
opensearch.hosts: ["https://node-1:9200", "https://node-2:9200", "https://node-3:9200"]
opensearch.ssl.verificationMode: none

# Authentication
opensearch.username: "admin"
opensearch.password: "admin"  # Change this!

# Security
opensearch.requestHeadersWhitelist: ["authorization", "securitytenant"]
opensearch_security.multitenancy.enabled: true
opensearch_security.multitenancy.tenants.preferred: ["Private", "Global"]
opensearch_security.readonly_mode.roles: ["kibana_read_only"]

# Disable demo security (production)
opensearch_security.cookie.secure: false

# Session timeout
opensearch_security.session.ttl: 3600000  # 1 hour
opensearch_security.session.keepalive: true

# Logging
logging.dest: /var/log/opensearch-dashboards/opensearch-dashboards.log
logging.verbose: false
```

---

## **Start OpenSearch Dashboards**

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable opensearch-dashboards
sudo systemctl start opensearch-dashboards

# Check status
sudo systemctl status opensearch-dashboards

# View logs
sudo tail -f /var/log/opensearch-dashboards/opensearch-dashboards.log
```

---

## **Configure Firewall for Dashboards**

```bash
# Allow port 5601
sudo firewall-cmd --permanent --add-port=5601/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

---

## **Access OpenSearch Dashboards**

1. **Open browser**: `http://your-server-ip:5601`
2. **Login credentials**: 
   - Username: `admin`
   - Password: `admin` (change immediately!)

---

## **Using OpenSearch Dashboards - Quick Start Guide**

### **1. First Login**

```
1. Navigate to http://your-server-ip:5601
2. Login with admin/admin
3. Select tenant: "Global" or "Private"
4. You'll see the home page
```

### **2. Discover - Explore Your Data**

```bash
# First, create sample data via API
curl -XPOST "https://node-1:9200/sample-logs/_doc" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "timestamp": "2025-12-18T10:00:00",
  "level": "INFO",
  "message": "Application started",
  "service": "web-server",
  "host": "node-1"
}'

# Add more documents
curl -XPOST "https://node-1:9200/sample-logs/_doc" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "timestamp": "2025-12-18T10:05:00",
  "level": "ERROR",
  "message": "Connection timeout",
  "service": "database",
  "host": "node-2"
}'
```

**In Dashboards:**
```
1. Go to "Management" → "Stack Management" → "Index Patterns"
2. Click "Create index pattern"
3. Enter pattern: sample-logs*
4. Select time field: timestamp
5. Click "Create index pattern"

6. Go to "Discover"
7. Select "sample-logs*" index pattern
8. View your logs in real-time
```

### **3. Visualizations - Create Charts**

```
Creating a Pie Chart:

1. Go to "Visualize" → "Create visualization"
2. Select "Pie chart"
3. Choose "sample-logs*" index pattern
4. Configuration:
   - Slice Size: Count
   - Split Slices: Terms → level.keyword
5. Click "Update" → "Save"
6. Name it: "Log Levels Distribution"

Creating a Line Chart:

1. Go to "Visualize" → "Create visualization"
2. Select "Line"
3. Choose "sample-logs*" index pattern
4. Configuration:
   - Y-axis: Count
   - X-axis: Date Histogram → timestamp
   - Interval: Auto
5. Click "Update" → "Save"
6. Name it: "Logs Over Time"
```

### **4. Dashboards - Combine Visualizations**

```
1. Go to "Dashboard" → "Create dashboard"
2. Click "Add"
3. Select your saved visualizations:
   - Log Levels Distribution (pie chart)
   - Logs Over Time (line chart)
4. Arrange and resize panels
5. Click "Save"
6. Name it: "System Monitoring Dashboard"
```

### **5. Dev Tools - Query Console**

```
Go to "Dev Tools"

# Example queries:

# 1. Check cluster health
GET _cluster/health

# 2. List all indices
GET _cat/indices?v

# 3. Search logs
GET sample-logs/_search
{
  "query": {
    "match": {
      "level": "ERROR"
    }
  }
}

# 4. Aggregation query
GET sample-logs/_search
{
  "size": 0,
  "aggs": {
    "logs_by_service": {
      "terms": {
        "field": "service.keyword"
      }
    }
  }
}
```

### **6. Alerting - Create Monitors**

```
1. Go to "Alerting" → "Monitors"
2. Click "Create monitor"
3. Monitor details:
   - Name: "High Error Rate Alert"
   - Monitor type: "Per query monitor"
   - Schedule: Every 5 minutes

4. Define query:
   {
     "query": {
       "bool": {
         "filter": {
           "range": {
             "timestamp": {
               "gte": "now-5m"
             }
           }
         },
         "must": {
           "match": {
             "level": "ERROR"
           }
         }
       }
     }
   }

5. Trigger:
   - Name: "Error threshold exceeded"
   - Severity: High
   - Condition: ctx.results[0].hits.total.value > 10

6. Action:
   - Send notification (email, Slack, webhook)

7. Click "Create"
```

### **7. Index Management**

```
Go to "Index Management"

Operations:
- View indices
- Apply policies (ISM)
- Manage snapshots
- Force merge
- Refresh/Flush
- Close/Delete indices

Example: Create Index State Management Policy

1. Go to "Index Management" → "State management policies"
2. Click "Create policy"
3. Policy JSON:

{
  "policy": {
    "description": "Log rotation policy",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": {
              "min_index_age": "7d"
            }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          {
            "replica_count": {
              "number_of_replicas": 1
            }
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "30d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          {
            "delete": {}
          }
        ]
      }
    ]
  }
}

4. Save policy
5. Attach to index pattern
```

---

## **Monitoring Cluster in Dashboards**

### **Built-in Monitoring**

```
1. Go to "Observability" → "Cluster Metrics"
2. View:
   - Cluster health
   - Node statistics
   - Index performance
   - JVM metrics
   - Disk usage
```

### **Custom Monitoring Dashboard**

Create visualizations for:

1. **Cluster Status**
```
GET _cluster/stats
```

2. **Node Performance**
```
GET _nodes/stats
```

3. **Index Statistics**
```
GET _stats
```

4. **Search Performance**
```
GET _nodes/stats/indices/search
```

---

## **Security Best Practices**

### **1. Change Default Passwords**

```bash
# Generate new password hash
cd /usr/share/opensearch/plugins/opensearch-security/tools
sudo -u opensearch bash -c "OPENSEARCH_JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./hash.sh"

# Update internal_users.yml
sudo vi /etc/opensearch/opensearch-security/internal_users.yml

# Apply changes
sudo /usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh \
  -cd /etc/opensearch/opensearch-security \
  -icl -nhnv \
  -cacert /etc/opensearch/root-ca.pem \
  -cert /etc/opensearch/kirk.pem \
  -key /etc/opensearch/kirk-key.pem \
  -h node-1
```

### **2. Create Read-Only User**

```bash
# Edit internal_users.yml
sudo vi /etc/opensearch/opensearch-security/internal_users.yml
```

```yaml
viewer:
  hash: "$2y$12$YOUR_HASH_HERE"
  reserved: false
  backend_roles:
    - "readall"
  description: "Read-only user"
```

### **3. Enable HTTPS for Dashboards**

```bash
# Generate SSL certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/opensearch-dashboards/dashboards-key.pem \
  -out /etc/opensearch-dashboards/dashboards-cert.pem

# Update opensearch_dashboards.yml
sudo vi /etc/opensearch-dashboards/opensearch_dashboards.yml
```

```yaml
server.ssl.enabled: true
server.ssl.certificate: /etc/opensearch-dashboards/dashboards-cert.pem
server.ssl.key: /etc/opensearch-dashboards/dashboards-key.pem
```

---

## **Cluster Management Commands**

### **Check Cluster Health**
```bash
# Health overview
curl -XGET "https://node-1:9200/_cluster/health?pretty" -u admin:admin --insecure

# Node status
curl -XGET "https://node-1:9200/_cat/nodes?v&h=name,role,master,cpu,heapPercent,ramPercent" -u admin:admin --insecure

# Identify current master
curl -XGET "https://node-1:9200/_cat/master?v" -u admin:admin --insecure
```

### **Shard Allocation**
```bash
# View shard distribution
curl -XGET "https://node-1:9200/_cat/shards?v" -u admin:admin --insecure

# Reallocate shards
curl -XPOST "https://node-1:9200/_cluster/reroute?retry_failed=true" -u admin:admin --insecure
```

### **Cluster Settings**
```bash
# View settings
curl -XGET "https://node-1:9200/_cluster/settings?pretty&include_defaults=true" -u admin:admin --insecure

# Update settings
curl -XPUT "https://node-1:9200/_cluster/settings" -u admin:admin --insecure \
  -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.routing.allocation.enable": "all"
  }
}'
```

---

## **Troubleshooting Cluster Issues**

### **Node Not Joining Cluster**
```bash
# Check logs
sudo journalctl -u opensearch -n 100

# Verify network connectivity
telnet node-2 9300

# Check security certificates
sudo openssl x509 -in /etc/opensearch/esnode.pem -text -noout
```

### **Split-Brain Detection**
```bash
# Check for multiple masters
for node in node-1 node-2 node-3; do
  echo "Checking $node:"
  curl -s -XGET "https://$node:9200/_cat/master" -u admin:admin --insecure
done
```

### **Master Election Issues**
```bash
# View cluster state
curl -XGET "https://node-1:9200/_cluster/state?pretty" -u admin:admin --insecure

# Check election history in logs
sudo grep "elected-as-master" /var/log/opensearch/production-cluster.log
```

---

This complete setup gives you a production-ready 3-node OpenSearch cluster with visualization capabilities through OpenSearch Dashboards! The Zen Discovery algorithm ensures reliable master election and cluster stability.
