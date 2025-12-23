# OpenSearch 3.4.0 Installation Guide

## Installation on Oracle Linux Server 9.6 using RPM

This guide provides step-by-step instructions for installing OpenSearch 3.4.0 on Oracle Linux Server 9.6 using RPM packages.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
  - [Method 1: Direct RPM Installation](#method-1-direct-rpm-installation)
  - [Method 2: YUM Repository Installation](#method-2-yum-repository-installation)
- [Post-Installation Configuration](#post-installation-configuration)
- [Verification](#verification)
- [Optional Configuration](#optional-configuration)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

---

## Prerequisites

Before installing OpenSearch, ensure you have:

- Oracle Linux Server 9.6 installed
- Root or sudo access
- Internet connectivity for downloading packages
- At least 4GB of RAM (8GB or more recommended for production)
- Sufficient disk space (minimum 10GB free)

---

## System Requirements

### Required System Configuration

OpenSearch requires specific kernel parameter settings for optimal performance.

**Set vm.max_map_count (Required for Production)**

```bash
sudo sysctl -w vm.max_map_count=262144
```

**Make it permanent across reboots:**

```bash
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

**Verify the setting:**

```bash
sysctl vm.max_map_count
```

### Disable Swap (Optional but Recommended)

For better performance, consider disabling swap:

```bash
sudo swapoff -a
```

To disable permanently, comment out swap entries in `/etc/fstab`.

---

## Installation Methods

### Method 1: Direct RPM Installation

This method involves downloading the RPM package directly and installing it.

#### Step 1: Download the RPM Package

Choose the appropriate package for your system architecture:

**For x64 Architecture:**
```bash
cd /tmp
wget https://artifacts.opensearch.org/releases/bundle/opensearch/3.4.0/opensearch-3.4.0-linux-x64.rpm
```

**For ARM64 Architecture:**
```bash
cd /tmp
wget https://artifacts.opensearch.org/releases/bundle/opensearch/3.4.0/opensearch-3.4.0-linux-arm64.rpm
```

#### Step 2: Import the GPG Key

Import the OpenSearch GPG key to verify package authenticity:

```bash
sudo rpm --import https://artifacts.opensearch.org/publickeys/opensearch-release.pgp
```

#### Step 3: Install OpenSearch

**Important:** OpenSearch 3.4.0 requires you to set a custom admin password during installation. The password must meet these requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

**For x64 systems:**
```bash
sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD='openSearch@123#' rpm -ivh opensearch-3.4.0-linux-x64.rpm
```

**Alternative using yum:**
```bash
sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD='openSearch@123#' yum install -y opensearch-3.4.0-linux-x64.rpm
```

**For ARM64 systems:**
```bash
sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD='openSearch@123#' rpm -ivh opensearch-3.4.0-linux-arm64.rpm
```

Replace `openSearch@123#` with your actual strong password.

---

### Method 2: YUM Repository Installation

This method configures a YUM repository for easier package management and updates.

#### Step 1: Add the OpenSearch YUM Repository

```bash
sudo curl -SL https://artifacts.opensearch.org/releases/bundle/opensearch/3.x/opensearch-3.x.repo -o /etc/yum.repos.d/opensearch-3.x.repo
```

#### Step 2: Verify Repository Configuration

```bash
cat /etc/yum.repos.d/opensearch-3.x.repo
```

The file should contain:
```ini
[opensearch-3.x]
name=OpenSearch 3.x repository
baseurl=https://artifacts.opensearch.org/releases/bundle/opensearch/3.x/yum
enabled=1
gpgcheck=1
gpgkey=https://artifacts.opensearch.org/publickeys/opensearch-release.pgp
```

#### Step 3: Import the GPG Key

```bash
sudo rpm --import https://artifacts.opensearch.org/publickeys/opensearch-release.pgp
```

#### Step 4: Clean YUM Cache

```bash
sudo yum clean all
sudo yum makecache
```

#### Step 5: Install OpenSearch

```bash
sudo env OPENSEARCH_INITIAL_ADMIN_PASSWORD='openSearch@123#' yum install -y opensearch-3.4.0
```

#### Step 6: Verify GPG Key During Installation

During installation, verify the GPG key fingerprint matches:

```
Fingerprint: A8B2 D9E0 4CD5 1FEF 6AA2 DB53 BA81 D999 8119 1457
```

---

## Post-Installation Configuration

### Step 1: Reload Systemd Daemon

```bash
sudo systemctl daemon-reload
```

### Step 2: Enable OpenSearch Service

Enable OpenSearch to start automatically on system boot:

```bash
sudo systemctl enable opensearch
```

### Step 3: Start OpenSearch Service

```bash
sudo systemctl start opensearch
```

### Step 4: Check Service Status

```bash
sudo systemctl status opensearch
```

Expected output should show the service as "active (running)".

---

## Verification

### Verify OpenSearch is Running

Wait approximately 60 seconds for OpenSearch to fully initialize, then test the installation:

```bash
curl -X GET https://localhost:9200 -u admin:openSearch@123# -k
```

**Expected Response:**
```json
{
  "name" : "hostname",
  "cluster_name" : "opensearch",
  "cluster_uuid" : "...",
  "version" : {
    "distribution" : "opensearch",
    "number" : "3.4.0",
    "build_type" : "rpm",
    "build_hash" : "...",
    "build_date" : "...",
    "build_snapshot" : false,
    "lucene_version" : "...",
    "minimum_wire_compatibility_version" : "...",
    "minimum_index_compatibility_version" : "..."
  },
  "tagline" : "The OpenSearch Project: https://opensearch.org/"
}
```

### Check OpenSearch Logs

If there are issues, check the logs:

```bash
sudo tail -f /var/log/opensearch/opensearch.log
```

---

## Optional Configuration

### Configure OpenSearch Settings

Edit the main configuration file:

```bash
sudo vi /etc/opensearch/opensearch.yml
```

**Common Configuration Options:**

```yaml
# Cluster name
cluster.name: my-opensearch-cluster

# Node name
node.name: node-1

# Network settings
network.host: 0.0.0.0

# HTTP port
http.port: 9200

# Discovery settings (for single-node cluster)
discovery.type: single-node

# Path settings
path.data: /var/lib/opensearch
path.logs: /var/log/opensearch
```

### Configure JVM Heap Size

Edit the JVM options file:

```bash
sudo vi /etc/opensearch/jvm.options
```

**Set heap size to approximately 50% of available RAM:**

```
# Example for 8GB RAM system
-Xms4g
-Xmx4g
```

**Important:** Never set heap size greater than 31GB even if you have more RAM available.

### Configure OpenSearch for Remote Access

If you want to access OpenSearch from remote hosts:

1. Edit `/etc/opensearch/opensearch.yml`:
```yaml
network.host: 0.0.0.0
```

2. Configure firewall:
```bash
sudo firewall-cmd --permanent --add-port=9200/tcp
sudo firewall-cmd --permanent --add-port=9300/tcp
sudo firewall-cmd --reload
```

### Restart After Configuration Changes

```bash
sudo systemctl restart opensearch
sudo systemctl status opensearch
```

---

## Troubleshooting

### OpenSearch Won't Start

1. **Check logs:**
```bash
sudo journalctl -u opensearch -n 100 --no-pager
sudo tail -100 /var/log/opensearch/opensearch.log
```

2. **Verify vm.max_map_count:**
```bash
sysctl vm.max_map_count
```

3. **Check disk space:**
```bash
df -h /var/lib/opensearch
```

4. **Verify permissions:**
```bash
sudo ls -la /var/lib/opensearch
sudo ls -la /var/log/opensearch
```

### Connection Refused

1. **Check if service is running:**
```bash
sudo systemctl status opensearch
```

2. **Verify port is listening:**
```bash
sudo ss -tlnp | grep 9200
```

3. **Check firewall rules:**
```bash
sudo firewall-cmd --list-all
```

### Memory Issues

If you see OutOfMemoryError in logs:

1. **Increase heap size** (edit `/etc/opensearch/jvm.options`)
2. **Reduce number of shards** per index
3. **Add more RAM** to the system

### Permission Denied Errors

```bash
sudo chown -R opensearch:opensearch /var/lib/opensearch
sudo chown -R opensearch:opensearch /var/log/opensearch
sudo chown -R opensearch:opensearch /etc/opensearch
```

---

## Uninstallation

### Stop OpenSearch Service

```bash
sudo systemctl stop opensearch
sudo systemctl disable opensearch
```

### Remove OpenSearch Package

**Using RPM:**
```bash
sudo rpm -e opensearch
```

**Using YUM:**
```bash
sudo yum remove -y opensearch
```

### Remove Data and Configuration (Optional)

**Warning:** This will delete all your data permanently.

```bash
sudo rm -rf /var/lib/opensearch
sudo rm -rf /var/log/opensearch
sudo rm -rf /etc/opensearch
sudo rm -f /etc/yum.repos.d/opensearch-3.x.repo
```

### Remove User and Group

```bash
sudo userdel opensearch
sudo groupdel opensearch
```

---

## Additional Resources

- **Official Documentation:** https://opensearch.org/docs/latest/
- **Installation Guide:** https://opensearch.org/docs/latest/install-and-configure/install-opensearch/rpm/
- **Configuration Reference:** https://opensearch.org/docs/latest/install-and-configure/configuration/
- **Community Forum:** https://forum.opensearch.org/
- **GitHub Issues:** https://github.com/opensearch-project/OpenSearch/issues

---

## Important Notes

- OpenSearch 3.4.0 includes a bundled JDK - no separate Java installation required
- Default installation includes demo security certificates
- For production environments, configure proper SSL/TLS certificates
- Default ports:
  - **9200**: REST API (HTTP/HTTPS)
  - **9300**: Inter-node communication
  - **9600**: Performance Analyzer
- The default admin user is `admin` with the password you set during installation
- Always backup your data before performing upgrades or major configuration changes

---

## License

OpenSearch is licensed under the Apache License 2.0.

---

**Last Updated:** December 2024  
**Version:** 3.4.0  
**Platform:** Oracle Linux Server 9.6
