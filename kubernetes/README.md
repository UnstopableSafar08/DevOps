# Production-Ready Kubernetes HA Cluster Setup with containerd
## RHEL/Oracle Linux Edition

## Table of Contents
1. [Cluster Specifications](#cluster-specifications)
2. [System Prerequisites](#system-prerequisites)
3. [Architecture Overview](#architecture-overview)
4. [Pre-Installation Checklist](#pre-installation-checklist)
5. [Initial Setup (All Nodes)](#initial-setup-all-nodes)
6. [HAProxy & Keepalived Setup](#haproxy--keepalived-setup)
7. [Control Plane Setup](#control-plane-setup)
8. [Worker Nodes Setup](#worker-nodes-setup)
9. [CNI Installation (Flannel)](#cni-installation-flannel)
10. [Rancher Installation](#rancher-installation)
11. [Production Best Practices](#production-best-practices)
12. [Verification & Testing](#verification--testing)
13. [Troubleshooting](#troubleshooting)

---

## Cluster Specifications

| Component | Count | IP Addresses |
|-----------|-------|--------------|
| Master Nodes | 3 | 10.10.10.10, 10.10.10.11, 10.10.10.12 |
| Worker Nodes | 6 | 10.10.10.13, 10.10.10.14, 10.10.10.15, 10.10.10.16, 10.10.10.17, 10.10.10.18 |
| HAProxy Nodes | 2 | 10.10.10.7, 10.10.10.8 |
| Keepalived VIP | 1 | 10.10.10.6 |
| Rancher Management | 1 | 10.10.13.19 |

**Network Configuration:**
- Pod CIDR: 10.244.0.0/16 (Flannel default)
- Service CIDR: 10.96.0.0/12
- Container Runtime: containerd
- CNI: Flannel
- Kubernetes Version: 1.29.x
- OS: RHEL 9.x / Oracle Linux 9.x

---

## System Prerequisites

### Operating System Requirements

**Supported OS Versions:**
- Red Hat Enterprise Linux 9.x (RHEL 9.0, 9.1, 9.2, 9.3+)
- Oracle Linux 9.x
- Rocky Linux 9.x (alternative)
- AlmaLinux 9.x (alternative)

**Minimum OS Configuration:**
- Fresh installation or minimal install
- Latest security patches applied
- System registered with Red Hat Subscription Manager (RHEL) or Oracle ULN (Oracle Linux)

### Hardware Requirements

#### Master Nodes (3 nodes)
- **CPU**: 4 vCPU (minimum), 8 vCPU (recommended)
- **RAM**: 8GB (minimum), 16GB (recommended)
- **Disk**: 
  - Root partition: 50GB (minimum), 100GB (recommended)
  - `/var` partition: 50GB+ (for container images and logs)
  - `/etcd` partition: 20GB+ SSD/NVMe (recommended for performance)
- **Network**: 1 Gbps (minimum), 10 Gbps (recommended)

#### Worker Nodes (6 nodes)
- **CPU**: 4 vCPU (minimum), 8-16 vCPU (recommended)
- **RAM**: 16GB (minimum), 32GB+ (recommended)
- **Disk**: 
  - Root partition: 100GB (minimum), 200GB+ (recommended)
  - `/var` partition: 100GB+ (for container images, logs, and persistent volumes)
- **Network**: 1 Gbps (minimum), 10 Gbps (recommended)

#### HAProxy Nodes (2 nodes)
- **CPU**: 2 vCPU (minimum), 4 vCPU (recommended)
- **RAM**: 4GB (minimum), 8GB (recommended)
- **Disk**: 20GB (root partition)
- **Network**: 1 Gbps (minimum), 10 Gbps (recommended)

#### Rancher Management Node (1 node)
- **CPU**: 4 vCPU (minimum), 8 vCPU (recommended)
- **RAM**: 8GB (minimum), 16GB (recommended)
- **Disk**: 50GB (root partition), 100GB+ (recommended with separate `/var` for Docker)
- **Network**: 1 Gbps

### Network Requirements

#### Network Infrastructure
- **Bandwidth**: Minimum 1 Gbps between all cluster nodes
- **Latency**: < 10ms between nodes (< 2ms recommended)
- **MTU**: 1500 bytes (default) or 9000 bytes (jumbo frames for better performance)
- **DNS**: Functioning DNS server or properly configured `/etc/hosts`
- **NTP**: Time synchronization across all nodes (chrony/ntpd)

#### IP Address Requirements
- Static IP addresses for all nodes (DHCP reservations acceptable)
- One additional IP for Keepalived VIP (10.10.10.6)
- IP addresses must be in the same subnet or routable

#### Required Network Ports

**Master Nodes:**
| Port | Protocol | Purpose |
|------|----------|---------|
| 6443 | TCP | Kubernetes API Server |
| 2379-2380 | TCP | etcd server client API |
| 10250 | TCP | Kubelet API |
| 10259 | TCP | kube-scheduler |
| 10257 | TCP | kube-controller-manager |
| 8472 | UDP | Flannel VXLAN |

**Worker Nodes:**
| Port | Protocol | Purpose |
|------|----------|---------|
| 10250 | TCP | Kubelet API |
| 30000-32767 | TCP | NodePort Services |
| 8472 | UDP | Flannel VXLAN |

**HAProxy Nodes:**
| Port | Protocol | Purpose |
|------|----------|---------|
| 6443 | TCP | Kubernetes API (frontend) |
| 9000 | TCP | HAProxy Stats |
| 112 | Protocol 112 | VRRP (Keepalived) |

### Storage Requirements

#### Disk Layout Recommendations

**Master Nodes:**
```
/dev/sda1   -> /boot      (1GB)
/dev/sda2   -> /          (50GB)
/dev/sda3   -> /var       (50GB)
/dev/sda4   -> /var/lib/etcd (20GB SSD/NVMe recommended)
```

**Worker Nodes:**
```
/dev/sda1   -> /boot      (1GB)
/dev/sda2   -> /          (100GB)
/dev/sda3   -> /var       (200GB+)
```

#### Filesystem Types
- **Root (/)**: XFS (RHEL default) or ext4
- **etcd**: XFS or ext4 on SSD/NVMe for optimal performance
- **Container Storage**: XFS recommended (better performance with overlay2)

#### Storage Performance
- **IOPS**: 
  - Master nodes (etcd): 3000+ IOPS (SSD/NVMe recommended)
  - Worker nodes: 1000+ IOPS
- **Throughput**: 100 MB/s minimum, 500 MB/s+ recommended

### Software Prerequisites

#### Required Packages
- **RHEL 9 Subscription**: Active subscription or free developer subscription
- **Repository Access**: Access to BaseOS and AppStream repositories
- **Updates**: System fully updated with latest security patches

#### Required Tools (to be installed)
- curl, wget
- git
- yum-utils or dnf-utils
- bash-completion
- vim or nano
- net-tools
- bind-utils
- iptables
- ipvsadm (for kube-proxy ipvs mode)
- chrony or ntp

### Security Requirements

#### SELinux
- SELinux must be set to `permissive` or `disabled` (Kubernetes limitation)
- Recommendation: Set to `permissive` for better security posture

#### Firewall
- Firewalld can remain enabled with proper rules configured
- Or disable for initial setup and enable with proper rules

#### SSH Access
- SSH key-based authentication configured (recommended)
- Root access or sudo privileges required
- SSH access from management workstation to all nodes

### Additional Requirements

#### Time Synchronization
- All nodes must have synchronized time
- Maximum time drift: < 500ms
- chrony or ntpd configured and running

#### DNS Resolution
- All nodes can resolve each other's hostnames
- DNS server configured or `/etc/hosts` properly populated
- Reverse DNS lookup working (recommended)

#### Internet Access
- Direct internet access for package downloads (or)
- Access to local mirror/satellite server (or)
- Air-gapped installation with pre-downloaded packages

#### User Accounts
- Non-root user with sudo privileges (recommended)
- Root access for initial setup

---

## Architecture Overview

```
                          ┌─────────────────────────┐
                          │   VIP (10.10.10.6)      │
                          │   Keepalived            │
                          └──────────┬──────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                  │
            ┌───────▼────────┐              ┌─────────▼───────┐
            │  HAProxy 1     │              │  HAProxy 2      │
            │  10.10.10.7    │              │  10.10.10.8     │
            │  MASTER        │              │  BACKUP         │
            └───────┬────────┘              └─────────┬───────┘
                    │                                  │
                    └──────────────┬───────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
    ┌────▼─────────┐        ┌─────▼─────────┐        ┌──────▼──────────┐
    │ Master 1     │        │ Master 2      │        │ Master 3        │
    │ 10.10.10.10  │        │ 10.10.10.11   │        │ 10.10.10.12     │
    │ etcd member  │        │ etcd member   │        │ etcd member     │
    └──────────────┘        └───────────────┘        └─────────────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │             │            │           │             │
    ┌────▼─────┐ ┌────▼─────┐ ┌───▼─────┐ ┌───▼─────┐ ┌─────▼────┐ ┌─────▼────┐
    │Worker 1  │ │Worker 2  │ │Worker 3 │ │Worker 4 │ │Worker 5  │ │Worker 6  │
    │10.10.10. │ │10.10.10. │ │10.10.10.│ │10.10.10.│ │10.10.10. │ │10.10.10. │
    │   13     │ │   14     │ │   15    │ │   16    │ │   17     │ │   18     │
    └──────────┘ └──────────┘ └─────────┘ └─────────┘ └──────────┘ └──────────┘

                          ┌─────────────────────────┐
                          │  Rancher Management     │
                          │  10.10.13.19            │
                          │  (Separate Network)     │
                          └─────────────────────────┘
```

---

## Pre-Installation Checklist

Run through this checklist before beginning installation:

### Infrastructure Checklist
- [ ] All nodes provisioned with correct specifications
- [ ] Static IP addresses assigned
- [ ] Network connectivity verified between all nodes
- [ ] Internet access or local repository access configured
- [ ] DNS resolution working (or /etc/hosts prepared)
- [ ] SSH access configured to all nodes
- [ ] RHEL subscriptions active (or Oracle ULN access configured)

### System Checklist
- [ ] RHEL 9.x / Oracle Linux 9.x installed on all nodes
- [ ] Latest patches applied (`dnf update`)
- [ ] Hostnames set correctly on all nodes
- [ ] Time synchronization configured (chrony)
- [ ] SELinux policy reviewed
- [ ] Firewall rules planned
- [ ] Storage layout meets requirements

### Security Checklist
- [ ] Root or sudo access available
- [ ] SSH keys distributed (recommended)
- [ ] Security policies reviewed
- [ ] Backup strategy planned
- [ ] Disaster recovery plan documented

### Documentation Ready
- [ ] IP address spreadsheet
- [ ] Join tokens storage location planned
- [ ] Certificate backup location prepared
- [ ] Runbook for operations team

---

## Initial Setup (All Nodes)

Run these steps on **ALL nodes** (masters, workers, HAProxy, and Rancher).

### 1. Register System and Enable Repositories

#### For RHEL 9

```bash
# Register system with Red Hat
sudo subscription-manager register --username <your-username>

# Attach subscription
sudo subscription-manager attach --auto

# Enable required repositories
sudo subscription-manager repos --enable=rhel-9-for-x86_64-baseos-rpms
sudo subscription-manager repos --enable=rhel-9-for-x86_64-appstream-rpms

# Verify repositories
sudo subscription-manager repos --list-enabled
```

#### For Oracle Linux 9

```bash
# Oracle Linux repositories are pre-configured
# Verify repository configuration
sudo dnf repolist

# Enable additional repositories if needed
sudo dnf config-manager --enable ol9_baseos_latest
sudo dnf config-manager --enable ol9_appstream
sudo dnf config-manager --enable ol9_addons
```

### 2. Update System

```bash
# Update all packages
sudo dnf update -y

# Reboot if kernel was updated
sudo reboot

# Verify system version
cat /etc/redhat-release
# Should show: Red Hat Enterprise Linux release 9.x or Oracle Linux Server release 9.x

# Check kernel version
uname -r
```

### 3. Install Required Packages

```bash
# Install essential tools
sudo dnf install -y \
    curl \
    wget \
    git \
    vim \
    bash-completion \
    net-tools \
    bind-utils \
    yum-utils \
    iptables \
    ipvsadm \
    socat \
    conntrack \
    chrony \
    rsync

# Enable and start chrony for time sync
sudo systemctl enable chronyd
sudo systemctl start chronyd

# Verify time sync
chronyc tracking
```

### 4. Set Hostnames

```bash
# Master nodes
sudo hostnamectl set-hostname k8s-master-01  # On 10.10.10.10
sudo hostnamectl set-hostname k8s-master-02  # On 10.10.10.11
sudo hostnamectl set-hostname k8s-master-03  # On 10.10.10.12

# Worker nodes
sudo hostnamectl set-hostname k8s-worker-01  # On 10.10.10.13
sudo hostnamectl set-hostname k8s-worker-02  # On 10.10.10.14
sudo hostnamectl set-hostname k8s-worker-03  # On 10.10.10.15
sudo hostnamectl set-hostname k8s-worker-04  # On 10.10.10.16
sudo hostnamectl set-hostname k8s-worker-05  # On 10.10.10.17
sudo hostnamectl set-hostname k8s-worker-06  # On 10.10.10.18

# HAProxy nodes
sudo hostnamectl set-hostname haproxy-01  # On 10.10.10.7
sudo hostnamectl set-hostname haproxy-02  # On 10.10.10.8

# Rancher node
sudo hostnamectl set-hostname rancher-mgmt  # On 10.10.13.19

# Verify
hostnamectl status
```

### 5. Configure /etc/hosts

```bash
# Backup existing file
sudo cp /etc/hosts /etc/hosts.backup

# Add cluster entries
cat <<EOF | sudo tee -a /etc/hosts

# Kubernetes HA Cluster
10.10.10.6   k8s-api-lb k8s-api-lb.local
10.10.10.7   haproxy-01 haproxy-01.local
10.10.10.8   haproxy-02 haproxy-02.local
10.10.10.10  k8s-master-01 k8s-master-01.local
10.10.10.11  k8s-master-02 k8s-master-02.local
10.10.10.12  k8s-master-03 k8s-master-03.local
10.10.10.13  k8s-worker-01 k8s-worker-01.local
10.10.10.14  k8s-worker-02 k8s-worker-02.local
10.10.10.15  k8s-worker-03 k8s-worker-03.local
10.10.10.16  k8s-worker-04 k8s-worker-04.local
10.10.10.17  k8s-worker-05 k8s-worker-05.local
10.10.10.18  k8s-worker-06 k8s-worker-06.local
10.10.13.19  rancher-mgmt rancher-mgmt.local
EOF

# Verify
cat /etc/hosts
```

### 6. Verify Network Connectivity

```bash
# Test connectivity to all nodes
for ip in 10.10.10.{7,8,10,11,12,13,14,15,16,17,18} 10.10.13.19; do
    echo -n "Pinging $ip: "
    ping -c 1 -W 1 $ip > /dev/null 2>&1 && echo "OK" || echo "FAILED"
done

# Test DNS resolution
for host in k8s-master-01 k8s-master-02 k8s-master-03; do
    echo -n "Resolving $host: "
    host $host > /dev/null 2>&1 && echo "OK" || echo "FAILED"
done

# Check network interface
ip addr show
ip route show
```

### 7. Disable Swap

```bash
# Disable swap immediately
sudo swapoff -a

# Disable swap permanently
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Verify swap is disabled
free -h
swapon --show
# Should show no swap entries

# Remove swap from systemd if exists
sudo systemctl mask swap.target
```

### 8. Disable SELinux (Required for Kubernetes)

```bash
# Check current status
getenforce

# Set to permissive mode immediately
sudo setenforce 0

# Disable permanently
sudo sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config

# Or disable completely (alternative)
sudo sed -i 's/^SELINUX=enforcing$/SELINUX=disabled/' /etc/selinux/config

# Verify
cat /etc/selinux/config | grep SELINUX=

# Note: System reboot required for permanent change
```

### 9. Load Required Kernel Modules

```bash
# Create modules configuration
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
EOF

# Load modules immediately
sudo modprobe overlay
sudo modprobe br_netfilter
sudo modprobe ip_vs
sudo modprobe ip_vs_rr
sudo modprobe ip_vs_wrr
sudo modprobe ip_vs_sh
sudo modprobe nf_conntrack

# Verify modules are loaded
lsmod | grep -E 'overlay|br_netfilter|ip_vs|nf_conntrack'
```

### 10. Configure Kernel Parameters

```bash
# Create sysctl configuration
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
# Bridge netfilter
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1

# IP forwarding
net.ipv4.ip_forward = 1

# Connection tracking
net.netfilter.nf_conntrack_max = 1000000

# Performance tuning
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 3

# Disable IPv6 (optional, if not using IPv6)
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1

# File descriptors
fs.file-max = 2097152
fs.nr_open = 2097152

# IPVS connection timeout
net.ipv4.vs.conn_reuse_mode = 0
net.ipv4.vs.expire_nodest_conn = 1
EOF

# Apply sysctl settings
sudo sysctl --system

# Verify settings
sudo sysctl net.bridge.bridge-nf-call-iptables
sudo sysctl net.ipv4.ip_forward
```

### 11. Configure Firewall Rules

#### Option 1: Disable Firewall (Easier for Initial Setup)

```bash
# Stop and disable firewalld
sudo systemctl stop firewalld
sudo systemctl disable firewalld
sudo systemctl mask firewalld

# Verify
sudo systemctl status firewalld
```

#### Option 2: Configure Firewall Rules (Production Recommended)

**For Master Nodes (10.10.10.10-12):**

```bash
# Kubernetes API Server
sudo firewall-cmd --permanent --add-port=6443/tcp

# etcd server client API
sudo firewall-cmd --permanent --add-port=2379-2380/tcp

# Kubelet API
sudo firewall-cmd --permanent --add-port=10250/tcp

# kube-scheduler
sudo firewall-cmd --permanent --add-port=10259/tcp

# kube-controller-manager
sudo firewall-cmd --permanent --add-port=10257/tcp

# Flannel VXLAN
sudo firewall-cmd --permanent --add-port=8472/udp

# NodePort Services (optional on masters)
sudo firewall-cmd --permanent --add-port=30000-32767/tcp

# Allow all traffic from cluster network
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.10.10.0/24" accept'

# Allow all traffic from pod network
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.244.0.0/16" accept'

# Reload firewall
sudo firewall-cmd --reload

# Verify rules
sudo firewall-cmd --list-all
```

**For Worker Nodes (10.10.10.13-18):**

```bash
# Kubelet API
sudo firewall-cmd --permanent --add-port=10250/tcp

# NodePort Services
sudo firewall-cmd --permanent --add-port=30000-32767/tcp

# Flannel VXLAN
sudo firewall-cmd --permanent --add-port=8472/udp

# Allow all traffic from cluster network
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.10.10.0/24" accept'

# Allow all traffic from pod network
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.244.0.0/16" accept'

# Reload firewall
sudo firewall-cmd --reload

# Verify rules
sudo firewall-cmd --list-all
```

**For HAProxy Nodes (10.10.10.7-8):**

```bash
# Kubernetes API (frontend)
sudo firewall-cmd --permanent --add-port=6443/tcp

# HAProxy stats
sudo firewall-cmd --permanent --add-port=9000/tcp

# VRRP (Keepalived)
sudo firewall-cmd --permanent --add-protocol=vrrp

# Allow traffic from cluster network
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.10.10.0/24" accept'

# Reload firewall
sudo firewall-cmd --reload

# Verify rules
sudo firewall-cmd --list-all
```

### 12. Configure Limits

```bash
# Increase system limits
cat <<EOF | sudo tee /etc/security/limits.d/k8s.conf
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
* soft memlock unlimited
* hard memlock unlimited
EOF

# Verify
ulimit -n
ulimit -u
```

### 13. Verify Prerequisites

```bash
# Create verification script
cat <<'EOF' > /tmp/verify_prereqs.sh
#!/bin/bash
echo "=== System Prerequisites Verification ==="
echo ""

echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/redhat-release)"
echo "Kernel: $(uname -r)"
echo ""

echo "Swap Status:"
free -h | grep -i swap
echo ""

echo "SELinux Status:"
getenforce
echo ""

echo "Loaded Modules:"
lsmod | grep -E 'overlay|br_netfilter|ip_vs'
echo ""

echo "Network Settings:"
sysctl net.bridge.bridge-nf-call-iptables
sysctl net.ipv4.ip_forward
echo ""

echo "Time Sync:"
chronyc tracking | grep "System time"
echo ""

echo "=== Verification Complete ==="
EOF

chmod +x /tmp/verify_prereqs.sh
bash /tmp/verify_prereqs.sh
```

---

## HAProxy & Keepalived Setup

Run these steps on **both HAProxy nodes** (10.10.10.7 and 10.10.10.8).

### 1. Install HAProxy and Keepalived

```bash
# Install packages
sudo dnf install -y haproxy keepalived

# Verify installation
haproxy -v
keepalived -v
```

### 2. Configure HAProxy

```bash
# Backup original configuration
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup

# Create new configuration
sudo tee /etc/haproxy/haproxy.cfg > /dev/null <<'EOF'
#---------------------------------------------------------------------
# Global settings
#---------------------------------------------------------------------
global
    log         127.0.0.1 local2
    chroot      /var/lib/haproxy
    pidfile     /var/run/haproxy.pid
    maxconn     4000
    user        haproxy
    group       haproxy
    daemon

    # Security
    tune.ssl.default-dh-param 2048
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

    # turn on stats unix socket
    stats socket /var/lib/haproxy/stats mode 660 level admin expose-fd listeners
    stats timeout 30s

#---------------------------------------------------------------------
# Common defaults
#---------------------------------------------------------------------
defaults
    mode                    tcp
    log                     global
    option                  tcplog
    option                  dontlognull
    option                  redispatch
    retries                 3
    timeout http-request    10s
    timeout queue           1m
    timeout connect         10s
    timeout client          1m
    timeout server          1m
    timeout http-keep-alive 10s
    timeout check           10s
    maxconn                 3000

#---------------------------------------------------------------------
# HAProxy Statistics
#---------------------------------------------------------------------
listen stats
    bind *:9000
    mode http
    stats enable
    stats uri /stats
    stats realm HAProxy\ Statistics
    stats auth admin:P@ssw0rd123!  # CHANGE THIS PASSWORD!
    stats refresh 10s
    stats show-node
    stats show-legends

#---------------------------------------------------------------------
# Kubernetes API Server Frontend
#---------------------------------------------------------------------
frontend k8s-api-frontend
    bind *:6443
    mode tcp
    option tcplog
    default_backend k8s-api-backend

#---------------------------------------------------------------------
# Kubernetes API Server Backend
#---------------------------------------------------------------------
backend k8s-api-backend
    mode tcp
    balance roundrobin
    option tcp-check
    option log-health-checks
    
    # Health check
    default-server inter 10s downinter 5s rise 2 fall 3 slowstart 60s maxconn 250 maxqueue 256 weight 100

    server k8s-master-01 10.10.10.10:6443 check check-ssl verify none
    server k8s-master-02 10.10.10.11:6443 check check-ssl verify none
    server k8s-master-03 10.10.10.12:6443 check check-ssl verify none
EOF

# Verify configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Set proper permissions
sudo chmod 644 /etc/haproxy/haproxy.cfg
```

### 3. Configure Keepalived

**Important:** Check your network interface name first:
```bash
# Find your network interface name
ip addr show
# Look for the interface with your IP address (likely eth0, ens192, ens3, etc.)
```

**On HAProxy-01 (10.10.10.7) - MASTER:**

```bash
# Create Keepalived configuration
sudo tee /etc/keepalived/keepalived.conf > /dev/null <<'EOF'
global_defs {
    router_id HAPROXY_01
    enable_script_security
    script_user root
}

# Script to check HAProxy health
vrrp_script check_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight 2
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    state MASTER
    interface ens192  # CHANGE THIS to your network interface!
    virtual_router_id 51
    priority 101
    advert_int 1
    
    authentication {
        auth_type PASS
        auth_pass K8sHAP@ss!  # CHANGE THIS PASSWORD!
    }
    
    virtual_ipaddress {
        10.10.10.6/24 dev ens192  # CHANGE interface if needed
    }
    
    track_script {
        check_haproxy
    }
    
    notify_master "/usr/bin/logger -t keepalived 'Transitioned to MASTER state'"
    notify_backup "/usr/bin/logger -t keepalived 'Transitioned to BACKUP state'"
    notify_fault "/usr/bin/logger -t keepalived 'Transitioned to FAULT state'"
}
EOF

# Verify configuration
sudo keepalived -t -f /etc/keepalived/keepalived.conf
```

**On HAProxy-02 (10.10.10.8) - BACKUP:**

```bash
# Create Keepalived configuration
sudo tee /etc/keepalived/keepalived.conf > /dev/null <<'EOF'
global_defs {
    router_id HAPROXY_02
    enable_script_security
    script_user root
}

# Script to check HAProxy health
vrrp_script check_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight 2
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    state BACKUP
    interface ens192  # CHANGE THIS to your network interface!
    virtual_router_id 51
    priority 100
    advert_int 1
    
    authentication {
        auth_type PASS
        auth_pass K8sHAP@ss!  # CHANGE THIS PASSWORD!
    }
    
    virtual_ipaddress {
        10.10.10.6/24 dev ens192  # CHANGE interface if needed
    }
    
    track_script {
        check_haproxy
    }
    
    notify_master "/usr/bin/logger -t keepalived 'Transitioned to MASTER state'"
    notify_backup "/usr/bin/logger -t keepalived 'Transitioned to BACKUP state'"
    notify_fault "/usr/bin/logger -t keepalived 'Transitioned to FAULT state'"
}
EOF

# Verify configuration
sudo keepalived -t -f /etc/keepalived/keepalived.conf
```

### 4. Enable and Start Services

```bash
# Enable services
sudo systemctl enable haproxy
sudo systemctl enable keepalived

# Start services
sudo systemctl start haproxy
sudo systemctl start keepalived

# Check status
sudo systemctl status haproxy
sudo systemctl status keepalived

# Check logs
sudo journalctl -u haproxy -f --no-pager
sudo journalctl -u keepalived -f --no-pager
```

### 5. Verify HAProxy and Keepalived

```bash
# Check VIP (should show on MASTER node)
ip addr show | grep 10.10.10.6

# Check HAProxy stats
curl http://localhost:9000/stats
# Or access via browser: http://10.10.10.7:9000/stats

# Check HAProxy is listening
sudo netstat -tulpn | grep :6443
sudo ss -tulpn | grep :6443

# Test connection (will fail until API server is running, but should connect)
curl -k https://10.10.10.6:6443
# Expected: connection refused or SSL error (normal at this stage)

# Check Keepalived status
sudo systemctl status keepalived
sudo journalctl -u keepalived --no-pager | tail -20

# Verify VRRP messages in logs
sudo tail -f /var/log/messages | grep -i vrrp
```

---

## Control Plane Setup

Run these steps on **all master nodes** (10.10.10.10, 10.10.10.11, 10.10.10.12).

### 1. Install containerd

```bash
# Install containerd
sudo dnf install -y containerd

# Create containerd configuration directory
sudo mkdir -p /etc/containerd

# Generate default configuration
containerd config default | sudo tee /etc/containerd/config.toml

# Enable SystemdCgroup (required for Kubernetes)
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Verify SystemdCgroup is enabled
grep SystemdCgroup /etc/containerd/config.toml

# Enable and start containerd
sudo systemctl enable containerd
sudo systemctl restart containerd
sudo systemctl status containerd

# Verify containerd is running
sudo ctr version
```

### 2. Install Kubernetes Components

```bash
# Add Kubernetes repository
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools kubernetes-cni
EOF

# Install Kubernetes packages
sudo dnf install -y kubelet kubeadm kubectl --disableexcludes=kubernetes

# Enable kubelet
sudo systemctl enable kubelet

# Verify installation
kubeadm version
kubelet --version
kubectl version --client

# Hold packages (prevent auto-update)
sudo dnf versionlock kubelet kubeadm kubectl
```

### 3. Pull Required Images (All Masters)

```bash
# Pull Kubernetes images
sudo kubeadm config images pull

# Verify images
sudo crictl images
```

### 4. Initialize First Master Node (10.10.10.10 ONLY)

```bash
# Create kubeadm configuration file
cat <<EOF | sudo tee /etc/kubernetes/kubeadm-config.yaml
apiVersion: kubeadm.k8s.io/v1beta3
kind: InitConfiguration
localAPIEndpoint:
  advertiseAddress: 10.10.10.10
  bindPort: 6443
nodeRegistration:
  criSocket: unix:///var/run/containerd/containerd.sock
  name: k8s-master-01
  taints:
  - effect: NoSchedule
    key: node-role.kubernetes.io/control-plane
---
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
kubernetesVersion: v1.29.0
controlPlaneEndpoint: "10.10.10.6:6443"
networking:
  podSubnet: 10.244.0.0/16
  serviceSubnet: 10.96.0.0/12
apiServer:
  certSANs:
  - "10.10.10.6"
  - "10.10.10.10"
  - "10.10.10.11"
  - "10.10.10.12"
  - "k8s-api-lb"
  - "k8s-master-01"
  - "k8s-master-02"
  - "k8s-master-03"
  extraArgs:
    audit-log-path: /var/log/kubernetes/audit.log
    audit-log-maxage: "30"
    audit-log-maxbackup: "10"
    audit-log-maxsize: "100"
controllerManager:
  extraArgs:
    bind-address: 0.0.0.0
scheduler:
  extraArgs:
    bind-address: 0.0.0.0
etcd:
  local:
    dataDir: /var/lib/etcd
---
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cgroupDriver: systemd
EOF

# Initialize cluster
sudo kubeadm init --config=/etc/kubernetes/kubeadm-config.yaml --upload-certs

# IMPORTANT: Save the output!
# You will need:
# 1. The kubeadm join command for control-plane nodes
# 2. The certificate key
# 3. The kubeadm join command for worker nodes
```

**Expected Output:**
```
Your Kubernetes control-plane has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

You can now join any number of control-plane nodes by running the following command on each:

  kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash> \
    --control-plane --certificate-key <certificate-key>

You can now join any number of worker nodes by running the following command on each:

  kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash>
```

### 5. Configure kubectl (First Master - 10.10.10.10)

```bash
# Setup kubeconfig for root
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Setup kubeconfig for regular user (optional)
mkdir -p /home/yourusername/.kube
sudo cp -i /etc/kubernetes/admin.conf /home/yourusername/.kube/config
sudo chown yourusername:yourusername /home/yourusername/.kube/config

# Enable kubectl bash completion
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -o default -F __start_kubectl k' >> ~/.bashrc
source ~/.bashrc

# Verify cluster
kubectl cluster-info
kubectl get nodes
kubectl get pods -A
```

### 6. Join Additional Master Nodes (10.10.10.11 and 10.10.10.12)

**If token/certificate-key expired, regenerate on first master:**
```bash
# On first master (10.10.10.10)
kubeadm token create --print-join-command
kubeadm init phase upload-certs --upload-certs
# This will output a new certificate key
```

**On Second Master (10.10.10.11):**
```bash
# Use the join command from step 4, modifying the advertise address
sudo kubeadm join 10.10.10.6:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <certificate-key> \
  --apiserver-advertise-address=10.10.10.11 \
  --cri-socket=unix:///var/run/containerd/containerd.sock

# Setup kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Enable bash completion
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
source ~/.bashrc

# Verify
kubectl get nodes
```

**On Third Master (10.10.10.12):**
```bash
# Use the join command from step 4, modifying the advertise address
sudo kubeadm join 10.10.10.6:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <certificate-key> \
  --apiserver-advertise-address=10.10.10.12 \
  --cri-socket=unix:///var/run/containerd/containerd.sock

# Setup kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Enable bash completion
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
source ~/.bashrc

# Verify
kubectl get nodes
```

### 7. Verify Control Plane

```bash
# Check nodes (run on any master)
kubectl get nodes -o wide

# Check pods
kubectl get pods -A

# Check etcd cluster health
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list

# Check component status
kubectl get cs

# Verify API server is accessible through VIP
kubectl --server=https://10.10.10.6:6443 get nodes
```

---

## Worker Nodes Setup

Run these steps on **all worker nodes** (10.10.10.13-18).

### 1. Install containerd

```bash
# Install containerd
sudo dnf install -y containerd

# Create configuration directory
sudo mkdir -p /etc/containerd

# Generate default configuration
containerd config default | sudo tee /etc/containerd/config.toml

# Enable SystemdCgroup
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Enable and start containerd
sudo systemctl enable containerd
sudo systemctl restart containerd
sudo systemctl status containerd

# Verify
sudo ctr version
```

### 2. Install Kubernetes Components

```bash
# Add Kubernetes repository
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.29/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools kubernetes-cni
EOF

# Install packages
sudo dnf install -y kubelet kubeadm kubectl --disableexcludes=kubernetes

# Enable kubelet
sudo systemctl enable kubelet

# Verify
kubeadm version
kubelet --version
```

### 3. Join Worker Nodes

**If token expired, generate new one on any master:**
```bash
kubeadm token create --print-join-command
```

**On each worker node, run the join command:**
```bash
# Example join command (use yours from above)
sudo kubeadm join 10.10.10.6:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --cri-socket=unix:///var/run/containerd/containerd.sock

# Label worker nodes (optional, from master)
# kubectl label node k8s-worker-01 node-role.kubernetes.io/worker=worker
```

### 4. Verify Worker Nodes (from any master)

```bash
# Check all nodes
kubectl get nodes -o wide

# Should see all 9 nodes (3 masters + 6 workers)
NAME             STATUS     ROLES           AGE   VERSION
k8s-master-01    NotReady   control-plane   10m   v1.29.0
k8s-master-02    NotReady   control-plane   8m    v1.29.0
k8s-master-03    NotReady   control-plane   6m    v1.29.0
k8s-worker-01    NotReady   <none>          2m    v1.29.0
k8s-worker-02    NotReady   <none>          2m    v1.29.0
k8s-worker-03    NotReady   <none>          2m    v1.29.0
k8s-worker-04    NotReady   <none>          2m    v1.29.0
k8s-worker-05    NotReady   <none>          2m    v1.29.0
k8s-worker-06    NotReady   <none>          2m    v1.29.0

# Nodes will be NotReady until CNI is installed (next section)
```

---

## CNI Installation (Flannel)

Run on **any master node**:

### 1. Download and Install Flannel

```bash
# Download Flannel manifest
wget https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# Review the manifest (optional)
less kube-flannel.yml

# Apply Flannel
kubectl apply -f kube-flannel.yml

# Alternatively, apply directly
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

### 2. Verify Flannel Installation

```bash
# Check Flannel pods
kubectl get pods -n kube-flannel -o wide
# All pods should be Running

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=flannel -n kube-flannel --timeout=300s

# Check DaemonSet
kubectl get ds -n kube-flannel

# Check nodes (should now be Ready)
kubectl get nodes
# All nodes should show Ready status
```

### 3. Verify Network Connectivity

```bash
# Create test pods
kubectl run test-1 --image=nginx
kubectl run test-2 --image=nginx

# Wait for pods
kubectl wait --for=condition=ready pod/test-1 --timeout=60s
kubectl wait --for=condition=ready pod/test-2 --timeout=60s

# Get pod IPs
kubectl get pods -o wide

# Test pod-to-pod connectivity
POD1_IP=$(kubectl get pod test-1 -o jsonpath='{.status.podIP}')
kubectl exec test-2 -- ping -c 3 $POD1_IP

# Cleanup
kubectl delete pod test-1 test-2
```

---

## Rancher Installation

Run on **Rancher management node** (10.10.13.19).

### 1. Install Docker

```bash
# Add Docker repository
sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify Docker installation
sudo docker --version
sudo docker run hello-world

# Add user to docker group (optional)
sudo usermod -aG docker $USER
# Logout and login for group changes to take effect
```

### 2. Install Rancher Server

```bash
# Create directory for Rancher data
sudo mkdir -p /opt/rancher

# Run Rancher container
sudo docker run -d \
  --name=rancher \
  --restart=unless-stopped \
  --privileged \
  -p 80:80 \
  -p 443:443 \
  -v /opt/rancher:/var/lib/rancher \
  rancher/rancher:latest

# Check container status
sudo docker ps

# View logs
sudo docker logs -f rancher
```

### 3. Access Rancher UI

```bash
# Get bootstrap password
sudo docker logs rancher 2>&1 | grep "Bootstrap Password:"

# Access Rancher UI
# Open browser: https://10.10.13.19
# Or: https://rancher-mgmt

# Use bootstrap password to login
# Set new admin password
# Configure Rancher URL: https://10.10.13.19
```

### 4. Import Existing Kubernetes Cluster

1. **Login to Rancher** (https://10.10.13.19)
2. **Click "Import Existing"**
3. **Select "Generic"**
4. **Enter cluster name**: `production-k8s-ha`
5. **Copy the kubectl command** provided
6. **Run on any master node**:

```bash
# Example command from Rancher (yours will be different)
curl --insecure -sfL https://10.10.13.19/v3/import/abc123xyz.yaml | kubectl apply -f -

# Verify import
kubectl get pods -n cattle-system
