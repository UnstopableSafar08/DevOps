# Installing containerd on RHEL-based Linux Distributions

This guide covers installing containerd on RHEL, Rocky Linux, Oracle Linux, and AWS Amazon Linux.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Method 1: Using Docker's Official Repository (Recommended)](#method-1-using-dockers-official-repository-recommended)
  - [Method 2: Binary Installation (All Versions)](#method-2-binary-installation-all-versions)
- [Distribution-Specific Notes](#distribution-specific-notes)
- [Verification](#verification)
- [Firewall Configuration](#firewall-configuration)
- [Production-Ready Practices](#production-ready-practices)
  - [Security Hardening](#security-hardening)
  - [Performance Tuning](#performance-tuning)
  - [Monitoring and Logging](#monitoring-and-logging)
  - [Backup and Disaster Recovery](#backup-and-disaster-recovery)
  - [Updates and Maintenance](#updates-and-maintenance)
  - [High Availability Considerations](#high-availability-considerations)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)
- [Additional Resources](#additional-resources)

## Prerequisites

- Root or sudo access
- Internet connectivity
- SELinux configured (typically enforcing on these distributions)

## Installation Methods

### Method 1: Using Docker's Official Repository (Recommended)

This method works consistently across RHEL 8+, Rocky Linux 8+, Oracle Linux 8+, and Amazon Linux 2023.

#### Step 1: Install required packages

```bash
sudo dnf install -y dnf-utils device-mapper-persistent-data lvm2
```

#### Step 2: Add Docker repository

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
```

#### Step 3: Install containerd

```bash
sudo dnf install -y containerd.io
```

#### Step 4: Configure containerd

Generate the default configuration:

```bash
sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml
```

#### Step 5: Configure systemd cgroup driver (for Kubernetes)

If you're using containerd with Kubernetes, enable systemd cgroup driver:

```bash
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
```

#### Step 6: Start and enable containerd

```bash
sudo systemctl enable --now containerd
sudo systemctl status containerd
```

---

### Method 2: Binary Installation (All Versions)

This method works on any version of these distributions.

#### Step 1: Download containerd

```bash
# Set version (check https://github.com/containerd/containerd/releases for latest)
CONTAINERD_VERSION="1.7.13"

# Download
wget https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz

# Extract to /usr/local
sudo tar Cxzvf /usr/local containerd-${CONTAINERD_VERSION}-linux-amd64.tar.gz
```

#### Step 2: Download and install runc

```bash
# Set version
RUNC_VERSION="1.1.12"

# Download
wget https://github.com/opencontainers/runc/releases/download/v${RUNC_VERSION}/runc.amd64

# Install
sudo install -m 755 runc.amd64 /usr/local/sbin/runc
```

#### Step 3: Download and install CNI plugins

```bash
# Set version
CNI_VERSION="1.4.0"

# Download
wget https://github.com/containernetworking/plugins/releases/download/v${CNI_VERSION}/cni-plugins-linux-amd64-v${CNI_VERSION}.tgz

# Create directory and extract
sudo mkdir -p /opt/cni/bin
sudo tar Cxzvf /opt/cni/bin cni-plugins-linux-amd64-v${CNI_VERSION}.tgz
```

#### Step 4: Configure systemd service

```bash
sudo mkdir -p /usr/local/lib/systemd/system
sudo curl -o /usr/local/lib/systemd/system/containerd.service https://raw.githubusercontent.com/containerd/containerd/main/containerd.service
```

#### Step 5: Create configuration

```bash
sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml
```

For Kubernetes:
```bash
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
```

#### Step 6: Start containerd

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now containerd
sudo systemctl status containerd
```

---

## Distribution-Specific Notes

### Amazon Linux 2023

Amazon Linux 2023 works well with Method 1. For Amazon Linux 2, you may need to use Method 2 or enable the Docker repository specifically.

```bash
# Amazon Linux 2
sudo amazon-linux-extras install docker
sudo yum install -y containerd
```

### RHEL 8/9

RHEL subscriptions may require additional repository configuration. Ensure you have access to required repos:

```bash
sudo subscription-manager repos --enable codeready-builder-for-rhel-9-$(arch)-rpms
```

### Rocky Linux & Oracle Linux

These distributions work seamlessly with Method 1 as they maintain high compatibility with RHEL.

---

## Verification

Verify containerd is running:

```bash
sudo systemctl status containerd
```

Check version:

```bash
containerd --version
```

Test with ctr (containerd CLI):

```bash
sudo ctr version
```

---

## Firewall Configuration

If you're using firewalld, you may need to configure it for container networking:

```bash
sudo firewall-cmd --permanent --zone=trusted --add-interface=cni0
sudo firewall-cmd --reload
```

---

## Production-Ready Practices

### Security Hardening

#### 1. Enable and Configure SELinux

Keep SELinux in enforcing mode for production:

```bash
# Verify SELinux is enforcing
getenforce

# Set to enforcing if not already
sudo setenforce 1
```

Ensure containerd SELinux policy is installed:

```bash
# For RHEL/Rocky/Oracle
sudo dnf install -y container-selinux

# Verify SELinux booleans
sudo getsebool -a | grep container
```

#### 2. Restrict Root Access

Create a dedicated user for container operations:

```bash
# Create containerd group
sudo groupadd containerd

# Add users to the group
sudo usermod -aG containerd <username>

# Configure containerd socket permissions
sudo mkdir -p /etc/systemd/system/containerd.service.d/
sudo tee /etc/systemd/system/containerd.service.d/override.conf <<EOF
[Service]
SocketGroup=containerd
SocketMode=0660
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

#### 3. Enable Content Trust and Image Verification

Configure containerd to only pull signed images:

```bash
# Edit /etc/containerd/config.toml
sudo nano /etc/containerd/config.toml
```

Add under plugins section:
```toml
[plugins."io.containerd.grpc.v1.cri".registry]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
      endpoint = ["https://registry-1.docker.io"]
```

#### 4. Implement Network Policies

Configure firewalld zones properly:

```bash
# Create dedicated zone for containers
sudo firewall-cmd --permanent --new-zone=containers
sudo firewall-cmd --permanent --zone=containers --set-target=DROP
sudo firewall-cmd --permanent --zone=containers --add-interface=cni0
sudo firewall-cmd --permanent --zone=containers --add-interface=docker0

# Allow only necessary ports
sudo firewall-cmd --permanent --zone=containers --add-port=10250/tcp  # kubelet
sudo firewall-cmd --reload
```

#### 5. Regular Security Scanning

Install and configure vulnerability scanning:

```bash
# Install trivy for image scanning
sudo dnf install -y wget
wget https://github.com/aquasecurity/trivy/releases/download/v0.48.0/trivy_0.48.0_Linux-64bit.rpm
sudo rpm -ivh trivy_0.48.0_Linux-64bit.rpm

# Scan images regularly
trivy image <image-name>
```

### Performance Tuning

#### 1. Configure Resource Limits

Edit `/etc/containerd/config.toml`:

```toml
[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "runc"
  
  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
    runtime_type = "io.containerd.runc.v2"
    
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
      SystemdCgroup = true
      
[plugins."io.containerd.grpc.v1.cri".cni]
  bin_dir = "/opt/cni/bin"
  conf_dir = "/etc/cni/net.d"
```

#### 2. Optimize Storage Driver

For production, use overlay2:

```bash
# Verify current storage driver
sudo ctr plugins ls | grep overlay

# Edit config if needed
sudo sed -i 's/snapshotter = .*/snapshotter = "overlayfs"/' /etc/containerd/config.toml
```

#### 3. Configure Kernel Parameters

Create `/etc/sysctl.d/99-containerd.conf`:

```bash
sudo tee /etc/sysctl.d/99-containerd.conf <<EOF
# Enable IP forwarding
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Increase connection tracking
net.netfilter.nf_conntrack_max = 1000000

# Optimize network buffer sizes
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864

# File descriptor limits
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 8192
EOF

# Apply settings
sudo sysctl --system
```

Load required kernel modules:

```bash
sudo tee /etc/modules-load.d/containerd.conf <<EOF
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

#### 4. Set System Resource Limits

Edit `/etc/security/limits.d/containerd.conf`:

```bash
sudo tee /etc/security/limits.d/containerd.conf <<EOF
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
EOF
```

Update systemd service limits in `/etc/systemd/system/containerd.service.d/limits.conf`:

```bash
sudo mkdir -p /etc/systemd/system/containerd.service.d/
sudo tee /etc/systemd/system/containerd.service.d/limits.conf <<EOF
[Service]
LimitNOFILE=1048576
LimitNPROC=1048576
LimitCORE=infinity
TasksMax=infinity
EOF

sudo systemctl daemon-reload
sudo systemctl restart containerd
```

### Monitoring and Logging

#### 1. Configure Centralized Logging

Forward containerd logs to centralized system:

```bash
# Configure journald persistence
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal

# Edit journald config
sudo tee -a /etc/systemd/journald.conf <<EOF
[Journal]
Storage=persistent
Compress=yes
MaxRetentionSec=1month
MaxFileSec=1day
EOF

sudo systemctl restart systemd-journald
```

#### 2. Enable Metrics Collection

Configure containerd metrics endpoint in `/etc/containerd/config.toml`:

```toml
[metrics]
  address = "127.0.0.1:1338"
```

Set up Prometheus monitoring:

```bash
# Sample prometheus config
sudo tee /etc/prometheus/containerd.yml <<EOF
scrape_configs:
  - job_name: 'containerd'
    static_configs:
      - targets: ['localhost:1338']
EOF
```

#### 3. Log Rotation

Configure log rotation for container logs:

```bash
sudo tee /etc/logrotate.d/containerd <<EOF
/var/log/containers/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    sharedscripts
}
EOF
```

#### 4. Health Checks

Create monitoring script:

```bash
sudo tee /usr/local/bin/containerd-health-check.sh <<'EOF'
#!/bin/bash
# Containerd health check script

# Check if containerd is running
if ! systemctl is-active --quiet containerd; then
    echo "CRITICAL: containerd service is not running"
    exit 2
fi

# Check containerd API
if ! timeout 5 ctr version &>/dev/null; then
    echo "CRITICAL: containerd API is not responding"
    exit 2
fi

# Check disk space
DISK_USAGE=$(df -h /var/lib/containerd | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "WARNING: Disk usage is at ${DISK_USAGE}%"
    exit 1
fi

echo "OK: containerd is healthy"
exit 0
EOF

sudo chmod +x /usr/local/bin/containerd-health-check.sh

# Add to cron
echo "*/5 * * * * /usr/local/bin/containerd-health-check.sh" | sudo crontab -
```

### Backup and Disaster Recovery

#### 1. Configuration Backup

```bash
# Create backup script
sudo tee /usr/local/bin/backup-containerd.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/containerd"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configuration
tar czf "$BACKUP_DIR/containerd-config-$DATE.tar.gz" \
    /etc/containerd/ \
    /etc/systemd/system/containerd.service.d/ \
    /etc/cni/net.d/ 2>/dev/null

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "containerd-config-*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/containerd-config-$DATE.tar.gz"
EOF

sudo chmod +x /usr/local/bin/backup-containerd.sh

# Schedule daily backups
echo "0 2 * * * /usr/local/bin/backup-containerd.sh" | sudo crontab -
```

#### 2. Image Backup Strategy

```bash
# Export critical images
sudo ctr images export /backup/critical-images-$(date +%Y%m%d).tar image1:tag image2:tag

# Automate with script
sudo tee /usr/local/bin/backup-images.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/images"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# List of critical images
CRITICAL_IMAGES=(
    "registry.k8s.io/kube-apiserver:v1.28.0"
    "registry.k8s.io/kube-controller-manager:v1.28.0"
    # Add your critical images
)

for image in "${CRITICAL_IMAGES[@]}"; do
    IMAGE_NAME=$(echo "$image" | tr '/:' '_')
    ctr images export "$BACKUP_DIR/${IMAGE_NAME}-${DATE}.tar" "$image"
done

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.tar" -mtime +30 -delete
EOF

sudo chmod +x /usr/local/bin/backup-images.sh
```

#### 3. Disaster Recovery Plan

Document and test your recovery procedure:

```bash
# Recovery script template
sudo tee /usr/local/bin/restore-containerd.sh <<'EOF'
#!/bin/bash
# Containerd disaster recovery script

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

echo "Stopping containerd..."
sudo systemctl stop containerd

echo "Restoring configuration..."
sudo tar xzf "$BACKUP_FILE" -C /

echo "Starting containerd..."
sudo systemctl start containerd

echo "Verifying installation..."
sudo ctr version

echo "Recovery completed"
EOF

sudo chmod +x /usr/local/bin/restore-containerd.sh
```

### Updates and Maintenance

#### 1. Automated Updates (Use with Caution)

```bash
# Enable automatic security updates only
sudo dnf install -y dnf-automatic

# Configure for security updates only
sudo sed -i 's/apply_updates = no/apply_updates = yes/' /etc/dnf/automatic.conf
sudo sed -i 's/upgrade_type = default/upgrade_type = security/' /etc/dnf/automatic.conf

# Enable timer
sudo systemctl enable --now dnf-automatic.timer
```

#### 2. Manual Update Procedure

Create update checklist:

```bash
# Pre-update checks
sudo systemctl status containerd
sudo ctr version
sudo ctr images ls
sudo df -h /var/lib/containerd

# Update containerd
sudo dnf update containerd.io -y

# Post-update verification
sudo systemctl restart containerd
sudo systemctl status containerd
sudo ctr version

# Test with sample container
sudo ctr run --rm docker.io/library/alpine:latest test-container echo "Test successful"
```

#### 3. Maintenance Windows

```bash
# Create maintenance mode script
sudo tee /usr/local/bin/containerd-maintenance.sh <<'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "Entering maintenance mode..."
        # Drain workloads if using Kubernetes
        # kubectl drain $(hostname) --ignore-daemonsets --delete-emptydir-data
        sudo systemctl stop containerd
        ;;
    end)
        echo "Exiting maintenance mode..."
        sudo systemctl start containerd
        # Uncordon if using Kubernetes
        # kubectl uncordon $(hostname)
        ;;
    *)
        echo "Usage: $0 {start|end}"
        exit 1
        ;;
esac
EOF

sudo chmod +x /usr/local/bin/containerd-maintenance.sh
```

### High Availability Considerations

#### 1. Storage Configuration

For HA setups, use shared storage or distributed storage:

```bash
# Example: Configure for shared storage mount
sudo mkdir -p /mnt/shared-containerd
# Mount your shared storage (NFS, Ceph, etc.)

# Update containerd config
sudo tee -a /etc/containerd/config.toml <<EOF
[plugins."io.containerd.grpc.v1.cri".containerd]
  snapshotter = "overlayfs"
[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "registry.k8s.io/pause:3.9"
EOF
```

#### 2. Load Balancing

When using multiple containerd nodes:

```bash
# Configure keepalived for VIP (example)
sudo dnf install -y keepalived

# Sample keepalived config for HA
sudo tee /etc/keepalived/keepalived.conf <<EOF
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass secretpass
    }
    virtual_ipaddress {
        192.168.1.100
    }
}
EOF
```

#### 3. Monitoring HA Status

```bash
# Create HA monitoring script
sudo tee /usr/local/bin/check-ha-status.sh <<'EOF'
#!/bin/bash

# Check containerd on all nodes
NODES=("node1" "node2" "node3")

for node in "${NODES[@]}"; do
    echo "Checking $node..."
    ssh "$node" "systemctl is-active containerd" || echo "WARNING: $node containerd is down"
done
EOF

sudo chmod +x /usr/local/bin/check-ha-status.sh
```

#### 4. Documentation

Maintain runbooks for:
- Node failure procedures
- Storage failover
- Network partition handling
- Rollback procedures

---

## Troubleshooting

### Check logs

```bash
sudo journalctl -u containerd -f
```

### SELinux issues

If you encounter SELinux denials:

```bash
sudo ausearch -m avc -ts recent
```

Consider setting SELinux to permissive temporarily for testing:

```bash
sudo setenforce 0
```

### Restart containerd

```bash
sudo systemctl restart containerd
```

---

## Uninstallation

### Method 1 (Repository installation):

```bash
sudo systemctl stop containerd
sudo dnf remove -y containerd.io
sudo rm -rf /etc/containerd
```

### Method 2 (Binary installation):

```bash
sudo systemctl stop containerd
sudo systemctl disable containerd
sudo rm /usr/local/lib/systemd/system/containerd.service
sudo rm /usr/local/bin/containerd*
sudo rm /usr/local/bin/ctr
sudo rm /usr/local/sbin/runc
sudo rm -rf /opt/cni
sudo rm -rf /etc/containerd
```

---

## Additional Resources

- [containerd Documentation](https://github.com/containerd/containerd)
- [Kubernetes CRI Documentation](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)
