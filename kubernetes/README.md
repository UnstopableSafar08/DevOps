# Production-Ready Kubernetes Cluster Setup Guide

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Infrastructure Specifications](#3-infrastructure-specifications)
4. [Pre-Installation Steps](#4-pre-installation-steps)
5. [HAProxy & Keepalived Setup](#5-haproxy--keepalived-setup)
6. [Container Runtime (containerd) Installation](#6-container-runtime-containerd-installation)
7. [Kubernetes Installation](#7-kubernetes-installation)
8. [Control Plane Initialization](#8-control-plane-initialization)
9. [Additional Master Nodes Setup](#9-additional-master-nodes-setup)
10. [Worker Nodes Setup](#10-worker-nodes-setup)
11. [CNI (Flannel) Installation](#11-cni-flannel-installation)
12. [Rancher Management Installation](#12-rancher-management-installation)
13. [Production Best Practices](#13-production-best-practices)
14. [Verification & Testing](#14-verification--testing)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Architecture Overview

### Cluster Components

- **Control Plane (HA)**: 3 Master nodes behind HAProxy load balancer
- **Worker Nodes**: 6 Worker nodes for application workloads
- **Load Balancer**: 2 HAProxy nodes with Keepalived for HA
- **CNI**: Flannel for pod networking
- **Management**: Rancher for cluster management and monitoring

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Virtual IP (Keepalived)                  │
│                        10.10.10.6                           │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼─────┐                   ┌────▼─────┐
    │ HAProxy1 │                   │ HAProxy2 │
    │10.10.10.7│                   │10.10.10.8│
    └────┬─────┘                   └────┬─────┘
         │                               │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼─────┐   ┌────▼─────┐   ┌────▼─────┐
    │ Master-1 │   │ Master-2 │   │ Master-3 │
    │10.10.10.│   │10.10.10.│   │10.10.10.│
    │    10    │   │    11    │   │    12    │
    └──────────┘   └──────────┘   └──────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼─────┐   ┌────▼─────┐   ┌────▼─────┐
    │ Worker-1 │   │ Worker-2 │   │ Worker-3 │
    │10.10.10.│   │10.10.10.│   │10.10.10.│
    │    13    │   │    14    │   │    15    │
    └──────────┘   └──────────┘   └──────────┘
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Worker-4 │   │ Worker-5 │   │ Worker-6 │
    │10.10.10.│   │10.10.10.│   │10.10.10.│
    │    16    │   │    17    │   │    18    │
    └──────────┘   └──────────┘   └──────────┘

                 ┌──────────────┐
                 │   Rancher    │
                 │ 10.10.13.19  │
                 └──────────────┘
```

---

## 2. Prerequisites

### Hardware Requirements

| Component | Minimum Spec | Recommended |
|-----------|-------------|-------------|
| Master Nodes | 2 CPU, 4GB RAM, 50GB Disk | 4 CPU, 8GB RAM, 100GB Disk |
| Worker Nodes | 2 CPU, 8GB RAM, 100GB Disk | 8 CPU, 32GB RAM, 500GB Disk |
| HAProxy Nodes | 2 CPU, 2GB RAM, 20GB Disk | 2 CPU, 4GB RAM, 50GB Disk |
| Rancher Node | 4 CPU, 8GB RAM, 100GB Disk | 8 CPU, 16GB RAM, 200GB Disk |

### Software Requirements

- **OS**: RHEL/Oracle Linux 9.x or 10.x
- **Kubernetes Version**: 1.28+ (latest stable)
- **containerd**: 1.7+
- **HAProxy**: 2.4+
- **Keepalived**: 2.2+
- **Rancher**: 2.8+

### Network Requirements

- All nodes must have unique hostnames and MAC addresses
- All nodes must have full network connectivity
- Certain ports must be open (detailed in firewall section)
- Disable swap on all nodes
- Load balancer must be accessible from all nodes

---

## 3. Infrastructure Specifications

### Node Inventory

| Hostname | Role | IP Address | vCPU | RAM | Disk |
|----------|------|------------|------|-----|------|
| haproxy-1 | Load Balancer | 10.10.10.7 | 2 | 4GB | 50GB |
| haproxy-2 | Load Balancer | 10.10.10.8 | 2 | 4GB | 50GB |
| k8s-master-1 | Control Plane | 10.10.10.10 | 4 | 8GB | 100GB |
| k8s-master-2 | Control Plane | 10.10.10.11 | 4 | 8GB | 100GB |
| k8s-master-3 | Control Plane | 10.10.10.12 | 4 | 8GB | 100GB |
| k8s-worker-1 | Worker | 10.10.10.13 | 8 | 32GB | 500GB |
| k8s-worker-2 | Worker | 10.10.10.14 | 8 | 32GB | 500GB |
| k8s-worker-3 | Worker | 10.10.10.15 | 8 | 32GB | 500GB |
| k8s-worker-4 | Worker | 10.10.10.16 | 8 | 32GB | 500GB |
| k8s-worker-5 | Worker | 10.10.10.17 | 8 | 32GB | 500GB |
| k8s-worker-6 | Worker | 10.10.10.18 | 8 | 32GB | 500GB |
| rancher-mgmt | Management | 10.10.13.19 | 8 | 16GB | 200GB |

### Network Configuration

- **Virtual IP (VIP)**: 10.10.10.6
- **Pod Network CIDR**: 10.244.0.0/16 (Flannel default)
- **Service CIDR**: 10.96.0.0/12
- **DNS Domain**: cluster.local

---

## 4. Pre-Installation Steps

### Step 4.1: Set Hostnames (All Nodes)

```bash
# On each node, set appropriate hostname
# HAProxy nodes
sudo hostnamectl set-hostname haproxy-1  # or haproxy-2

# Master nodes
sudo hostnamectl set-hostname k8s-master-1  # or k8s-master-2, k8s-master-3

# Worker nodes
sudo hostnamectl set-hostname k8s-worker-1  # through k8s-worker-6

# Rancher node
sudo hostnamectl set-hostname rancher-mgmt
```

### Step 4.2: Update /etc/hosts (All Nodes)

```bash
sudo tee -a /etc/hosts <<EOF
# HAProxy Load Balancers
10.10.10.6    k8s-api-lb k8s-api
10.10.10.7    haproxy-1
10.10.10.8    haproxy-2

# Kubernetes Master Nodes
10.10.10.10   k8s-master-1
10.10.10.11   k8s-master-2
10.10.10.12   k8s-master-3

# Kubernetes Worker Nodes
10.10.10.13   k8s-worker-1
10.10.10.14   k8s-worker-2
10.10.10.15   k8s-worker-3
10.10.10.16   k8s-worker-4
10.10.10.17   k8s-worker-5
10.10.10.18   k8s-worker-6

# Rancher Management
10.10.13.19   rancher-mgmt
EOF
```

### Step 4.3: Disable Swap (All K8s Nodes)

```bash
# Disable swap immediately
sudo swapoff -a

# Disable swap permanently
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# Verify swap is off
free -h
```

### Step 4.4: Disable SELinux (All K8s Nodes)

```bash
# Set SELinux to permissive mode
sudo setenforce 0
sudo sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config

# Verify
getenforce
```

### Step 4.5: Configure Firewall (All K8s Nodes)

#### Master Nodes Firewall

```bash
# Master node ports
sudo firewall-cmd --permanent --add-port=6443/tcp    # Kubernetes API
sudo firewall-cmd --permanent --add-port=2379-2380/tcp  # etcd
sudo firewall-cmd --permanent --add-port=10250/tcp   # Kubelet API
sudo firewall-cmd --permanent --add-port=10251/tcp   # kube-scheduler
sudo firewall-cmd --permanent --add-port=10252/tcp   # kube-controller-manager
sudo firewall-cmd --permanent --add-port=10257/tcp   # kube-controller-manager (secure)
sudo firewall-cmd --permanent --add-port=10259/tcp   # kube-scheduler (secure)
sudo firewall-cmd --permanent --add-port=8472/udp    # Flannel VXLAN

# Reload firewall
sudo firewall-cmd --reload
```

#### Worker Nodes Firewall

```bash
# Worker node ports
sudo firewall-cmd --permanent --add-port=10250/tcp   # Kubelet API
sudo firewall-cmd --permanent --add-port=30000-32767/tcp  # NodePort Services
sudo firewall-cmd --permanent --add-port=8472/udp    # Flannel VXLAN

# Reload firewall
sudo firewall-cmd --reload
```

#### HAProxy Nodes Firewall

```bash
# HAProxy ports
sudo firewall-cmd --permanent --add-port=6443/tcp    # K8s API proxy
sudo firewall-cmd --permanent --add-port=8404/tcp    # HAProxy stats (optional)
sudo firewall-cmd --permanent --add-protocol=vrrp    # Keepalived VRRP

# Reload firewall
sudo firewall-cmd --reload
```

### Step 4.6: Load Kernel Modules (All K8s Nodes)

```bash
# Load required modules
sudo modprobe overlay
sudo modprobe br_netfilter

# Ensure modules load on boot
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
```

### Step 4.7: Configure Sysctl Parameters (All K8s Nodes)

```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

# Apply sysctl params
sudo sysctl --system
```

### Step 4.8: Update System (All Nodes)

```bash
sudo dnf update -y
sudo reboot
```

---

## 5. HAProxy & Keepalived Setup

### Step 5.1: Install HAProxy and Keepalived (Both HAProxy Nodes)

```bash
sudo dnf install -y haproxy keepalived
```

### Step 5.2: Configure HAProxy (Both HAProxy Nodes)

```bash
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.bak

sudo tee /etc/haproxy/haproxy.cfg <<EOF
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon
    maxconn 4000

defaults
    log     global
    mode    tcp
    option  tcplog
    option  dontlognull
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms

frontend k8s-api-frontend
    bind *:6443
    mode tcp
    option tcplog
    default_backend k8s-api-backend

backend k8s-api-backend
    mode tcp
    balance roundrobin
    option tcp-check
    server k8s-master-1 10.10.10.10:6443 check fall 3 rise 2
    server k8s-master-2 10.10.10.11:6443 check fall 3 rise 2
    server k8s-master-3 10.10.10.12:6443 check fall 3 rise 2

listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 30s
    stats realm HAProxy\ Statistics
    stats auth admin:password123  # Change this password!
EOF
```

### Step 5.3: Configure Keepalived on HAProxy-1 (Primary)

```bash
sudo tee /etc/keepalived/keepalived.conf <<EOF
vrrp_script check_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight 2
}

vrrp_instance VI_1 {
    state MASTER
    interface eth0  # Change to your network interface
    virtual_router_id 51
    priority 101
    advert_int 1
    
    authentication {
        auth_type PASS
        auth_pass K8sHAPass123  # Change this!
    }
    
    virtual_ipaddress {
        10.10.10.6/24
    }
    
    track_script {
        check_haproxy
    }
}
EOF
```

### Step 5.4: Configure Keepalived on HAProxy-2 (Backup)

```bash
sudo tee /etc/keepalived/keepalived.conf <<EOF
vrrp_script check_haproxy {
    script "/usr/bin/killall -0 haproxy"
    interval 2
    weight 2
}

vrrp_instance VI_1 {
    state BACKUP
    interface eth0  # Change to your network interface
    virtual_router_id 51
    priority 100
    advert_int 1
    
    authentication {
        auth_type PASS
        auth_pass K8sHAPass123  # Same password as master!
    }
    
    virtual_ipaddress {
        10.10.10.6/24
    }
    
    track_script {
        check_haproxy
    }
}
EOF
```

### Step 5.5: Start Services (Both HAProxy Nodes)

```bash
# Enable and start HAProxy
sudo systemctl enable haproxy
sudo systemctl start haproxy
sudo systemctl status haproxy

# Enable and start Keepalived
sudo systemctl enable keepalived
sudo systemctl start keepalived
sudo systemctl status keepalived

# Verify VIP is assigned (should show on primary)
ip addr show
```

### Step 5.6: Verify HAProxy

```bash
# Test from any node
nc -zv 10.10.10.6 6443

# Access HAProxy stats (optional)
curl http://10.10.10.7:8404/stats
```

---

## 6. Container Runtime (containerd) Installation

### Step 6.1: Install containerd (All Master and Worker Nodes)

```bash
# Install containerd
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y containerd.io-1.7.*

# Generate default configuration
sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml
```

### Step 6.2: Configure containerd to Use systemd cgroup Driver

```bash
# Edit containerd config to use systemd cgroup driver
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Or manually edit /etc/containerd/config.toml and set:
# [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
#   SystemdCgroup = true
```

### Step 6.3: Restart containerd

```bash
sudo systemctl enable containerd
sudo systemctl restart containerd
sudo systemctl status containerd
```

### Step 6.4: Verify containerd

```bash
sudo ctr version
```

---

## 7. Kubernetes Installation

### Step 7.1: Add Kubernetes Repository (All Master and Worker Nodes)

```bash
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools kubernetes-cni
EOF
```

### Step 7.2: Install Kubernetes Components

```bash
# Install kubelet, kubeadm, and kubectl
sudo dnf install -y kubelet kubeadm kubectl --disableexcludes=kubernetes

# Enable kubelet
sudo systemctl enable kubelet
```

### Step 7.3: Verify Installation

```bash
kubeadm version
kubelet --version
kubectl version --client
```

---

## 8. Control Plane Initialization

### Step 8.1: Initialize First Master Node (k8s-master-1 Only)

```bash
# Create kubeadm config file
cat <<EOF | sudo tee /root/kubeadm-config.yaml
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
kubernetesVersion: stable
controlPlaneEndpoint: "10.10.10.6:6443"
networking:
  podSubnet: "10.244.0.0/16"
  serviceSubnet: "10.96.0.0/12"
apiServer:
  certSANs:
  - "10.10.10.6"
  - "10.10.10.10"
  - "10.10.10.11"
  - "10.10.10.12"
  - "k8s-api-lb"
  - "k8s-master-1"
  - "k8s-master-2"
  - "k8s-master-3"
etcd:
  local:
    dataDir: /var/lib/etcd
---
apiVersion: kubeadm.k8s.io/v1beta3
kind: InitConfiguration
localAPIEndpoint:
  advertiseAddress: "10.10.10.10"
  bindPort: 6443
nodeRegistration:
  criSocket: unix:///var/run/containerd/containerd.sock
  taints:
  - effect: NoSchedule
    key: node-role.kubernetes.io/control-plane
EOF

# Initialize cluster
sudo kubeadm init --config=/root/kubeadm-config.yaml --upload-certs
```

### Step 8.2: Save Join Commands

**IMPORTANT**: Save the output from the previous command. You'll see two join commands:

1. For adding control plane nodes (masters)
2. For adding worker nodes

Example output:
```
# Control plane join command (save this!)
kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash> \
    --control-plane --certificate-key <cert-key>

# Worker node join command (save this!)
kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash>
```

### Step 8.3: Configure kubectl for Root User (k8s-master-1)

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 8.4: Configure kubectl for Regular User (Optional)

```bash
# As regular user
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 8.5: Verify First Master Node

```bash
kubectl get nodes
kubectl get pods -n kube-system
```

---

## 9. Additional Master Nodes Setup

### Step 9.1: Join k8s-master-2 to Cluster

```bash
# On k8s-master-2, run the control plane join command from Step 8.2
sudo kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash> \
    --control-plane --certificate-key <cert-key> \
    --apiserver-advertise-address=10.10.10.11 \
    --cri-socket unix:///var/run/containerd/containerd.sock
```

### Step 9.2: Configure kubectl on k8s-master-2

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 9.3: Join k8s-master-3 to Cluster

```bash
# On k8s-master-3, run the control plane join command
sudo kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash> \
    --control-plane --certificate-key <cert-key> \
    --apiserver-advertise-address=10.10.10.12 \
    --cri-socket unix:///var/run/containerd/containerd.sock
```

### Step 9.4: Configure kubectl on k8s-master-3

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Step 9.5: Verify All Master Nodes (from any master)

```bash
kubectl get nodes
# Should show all 3 master nodes

kubectl get pods -n kube-system -o wide
# Verify etcd pods are running on all masters
```

### Step 9.6: If Join Token Expired

```bash
# Generate new token and print join command (run on k8s-master-1)
kubeadm token create --print-join-command

# For control plane nodes, also need certificate key
kubeadm init phase upload-certs --upload-certs
# This will print a new certificate-key to use
```

---

## 10. Worker Nodes Setup

### Step 10.1: Join Worker Nodes to Cluster

Run the worker join command on each worker node (k8s-worker-1 through k8s-worker-6):

```bash
# On each worker node
sudo kubeadm join 10.10.10.6:6443 --token <token> \
    --discovery-token-ca-cert-hash sha256:<hash> \
    --cri-socket unix:///var/run/containerd/containerd.sock
```

### Step 10.2: Verify Worker Nodes (from master)

```bash
kubectl get nodes
# Should show all 3 masters and 6 workers
# Status will be "NotReady" until CNI is installed
```

### Step 10.3: Label Worker Nodes (Optional, from master)

```bash
# Add worker role label for clarity
kubectl label node k8s-worker-1 node-role.kubernetes.io/worker=worker
kubectl label node k8s-worker-2 node-role.kubernetes.io/worker=worker
kubectl label node k8s-worker-3 node-role.kubernetes.io/worker=worker
kubectl label node k8s-worker-4 node-role.kubernetes.io/worker=worker
kubectl label node k8s-worker-5 node-role.kubernetes.io/worker=worker
kubectl label node k8s-worker-6 node-role.kubernetes.io/worker=worker
```

---

## 11. CNI (Flannel) Installation

### Step 11.1: Download Flannel Manifest (from master)

```bash
wget https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

### Step 11.2: Verify Pod Network CIDR

```bash
# Check that the pod CIDR in the manifest matches our configuration (10.244.0.0/16)
grep -A 1 "net-conf.json" kube-flannel.yml

# The output should show:
#   "Network": "10.244.0.0/16",
```

### Step 11.3: Apply Flannel

```bash
kubectl apply -f kube-flannel.yml
```

### Step 11.4: Verify Flannel Installation

```bash
# Wait for flannel pods to be running
kubectl get pods -n kube-flannel -w

# Check all pods are running
kubectl get pods -n kube-flannel

# Verify nodes are now Ready
kubectl get nodes
```

### Step 11.5: Test Pod Network

```bash
# Create test deployment
kubectl create deployment nginx --image=nginx --replicas=3

# Check pods are distributed and running
kubectl get pods -o wide

# Test connectivity
kubectl run test-pod --image=busybox --rm -it -- sh
# Inside the pod, try: wget -O- <nginx-pod-ip>
```

---

## 12. Rancher Management Installation

### Step 12.1: Install Docker on Rancher Node

```bash
# On rancher-mgmt node
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io

sudo systemctl enable docker
sudo systemctl start docker
```

### Step 12.2: Install Rancher using Docker

```bash
# Run Rancher container
sudo docker run -d --restart=unless-stopped \
  -p 80:80 -p 443:443 \
  --name rancher \
  --privileged \
  -v /opt/rancher:/var/lib/rancher \
  rancher/rancher:latest
```

### Step 12.3: Access Rancher UI

```bash
# Get bootstrap password
sudo docker logs rancher 2>&1 | grep "Bootstrap Password:"

# Access Rancher at: https://10.10.13.19
# Use the bootstrap password to login
```

### Step 12.4: Configure Rancher

1. Access `https://10.10.13.19`
2. Set admin password
3. Configure server URL: `https://10.10.13.19`
4. Complete initial setup

### Step 12.5: Import Existing Cluster to Rancher

1. In Rancher UI, click "Import Existing" cluster
2. Select "Generic" as cluster type
3. Enter cluster name (e.g., "production-k8s")
4. Copy the kubectl command provided
5. Run the command on k8s-master-1:

```bash
# Example command (use the actual command from Rancher UI)
kubectl apply -f https://10.10.13.19/v3/import/xxxxx.yaml
```

### Step 12.6: Verify Cluster Import

```bash
# Check cattle-system namespace
kubectl get pods -n cattle-system

# In Rancher UI, verify cluster appears and is active
```

---

## 13. Production Best Practices

### 13.1: RBAC Configuration

```bash
# Create namespace for production workloads
kubectl create namespace production

# Create service account
kubectl create serviceaccount prod-admin -n production

# Create role binding
kubectl create rolebinding prod-admin-binding \
  --clusterrole=admin \
  --serviceaccount=production:prod-admin \
  --namespace=production
```

### 13.2: Resource Quotas

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
    persistentvolumeclaims: "50"
EOF
```

### 13.3: Network Policies

```bash
# Default deny all ingress traffic
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
EOF
```

### 13.4: Pod Security Standards

```bash
# Label namespace for restricted pod security
kubectl label namespace production \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### 13.5: Configure etcd Backup

```bash
# Create backup script on each master node
sudo tee /usr/local/bin/etcd-backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/etcd"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p ${BACKUP_DIR}

ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save ${BACKUP_DIR}/etcd-snapshot-${TIMESTAMP}.db

# Keep only last 7 days of backups
find ${BACKUP_DIR} -name "etcd-snapshot-*.db" -mtime +7 -delete

echo "etcd backup completed: ${BACKUP_DIR}/etcd-snapshot-${TIMESTAMP}.db"
EOF

# Make script executable
sudo chmod +x /usr/local/bin/etcd-backup.sh

# Create systemd service for automated backups
sudo tee /etc/systemd/system/etcd-backup.service <<EOF
[Unit]
Description=etcd Backup Service
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/etcd-backup.sh
User=root

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer for daily backups at 2 AM
sudo tee /etc/systemd/system/etcd-backup.timer <<EOF
[Unit]
Description=Daily etcd Backup Timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer
sudo systemctl daemon-reload
sudo systemctl enable etcd-backup.timer
sudo systemctl start etcd-backup.timer

# Verify timer is active
sudo systemctl list-timers etcd-backup.timer
```

### 13.6: Install Metrics Server

```bash
# Install metrics server for resource monitoring
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait for metrics server to be ready
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=300s

# Verify metrics server
kubectl top nodes
kubectl top pods -A
```

### 13.7: Configure Log Rotation

```bash
# Configure log rotation for containerd (all nodes)
sudo tee /etc/logrotate.d/containerd <<EOF
/var/log/pods/*/*/*.log {
    rotate 7
    daily
    maxsize 100M
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
EOF

# Configure kubelet log rotation
sudo tee /etc/logrotate.d/kubelet <<EOF
/var/log/kubelet.log {
    rotate 7
    daily
    maxsize 100M
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
EOF
```

### 13.8: Install and Configure Monitoring Stack (Prometheus & Grafana)

```bash
# Create monitoring namespace
kubectl create namespace monitoring

# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack (includes Prometheus, Grafana, and Alertmanager)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword='Admin@123' \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=10Gi

# Verify installation
kubectl get pods -n monitoring

# Access Grafana (create NodePort service)
kubectl patch svc prometheus-grafana -n monitoring -p '{"spec": {"type": "NodePort"}}'

# Get Grafana URL
kubectl get svc prometheus-grafana -n monitoring
```

### 13.9: Install Ingress Controller (NGINX)

```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/baremetal/deploy.yaml

# Wait for ingress controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

# Verify installation
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

### 13.10: Configure Storage Classes

```bash
# Create local-path storage class for development/testing
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
EOF

# For production, consider installing NFS provisioner or other storage solution
# Example: NFS provisioner
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=<NFS_SERVER_IP> \
  --set nfs.path=/exported/path \
  --namespace kube-system
```

### 13.11: Enable Audit Logging

```bash
# Create audit policy (on all master nodes)
sudo mkdir -p /etc/kubernetes/audit

sudo tee /etc/kubernetes/audit/policy.yaml <<EOF
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Don't log requests to the following
  - level: None
    nonResourceURLs:
      - /healthz*
      - /logs
      - /metrics
      - /swagger*
      - /version

  # Limit level to Metadata for resources
  - level: Metadata
    omitStages:
      - RequestReceived
    resources:
      - group: ""
        resources: ["events", "nodes", "nodes/status"]

  # Log everything else at RequestResponse level
  - level: RequestResponse
    omitStages:
      - RequestReceived
EOF

# Update kube-apiserver manifest to enable audit logging
sudo tee -a /etc/kubernetes/manifests/kube-apiserver.yaml <<EOF
# Add these to the command section:
    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml
    - --audit-log-path=/var/log/kubernetes/audit/audit.log
    - --audit-log-maxage=30
    - --audit-log-maxbackup=10
    - --audit-log-maxsize=100

# Add these to volumeMounts:
    - mountPath: /etc/kubernetes/audit
      name: audit-policy
      readOnly: true
    - mountPath: /var/log/kubernetes/audit
      name: audit-logs

# Add these to volumes:
  - hostPath:
      path: /etc/kubernetes/audit
      type: DirectoryOrCreate
    name: audit-policy
  - hostPath:
      path: /var/log/kubernetes/audit
      type: DirectoryOrCreate
    name: audit-logs
EOF

# Create audit log directory
sudo mkdir -p /var/log/kubernetes/audit
```

### 13.12: Install Helm Package Manager

```bash
# Download and install Helm (on master nodes)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installation
helm version

# Add common repositories
helm repo add stable https://charts.helm.sh/stable
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 13.13: Configure Pod Disruption Budgets

```bash
# Example PDB for critical applications
cat <<EOF | kubectl apply -f -
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-app-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-app
EOF
```

### 13.14: Setup Certificate Management (cert-manager)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s

# Create ClusterIssuer for Let's Encrypt (example)
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 13.15: Implement Node Affinity and Taints

```bash
# Add taints to specific nodes for dedicated workloads
kubectl taint nodes k8s-worker-1 workload=database:NoSchedule
kubectl taint nodes k8s-worker-2 workload=database:NoSchedule

# Label nodes for affinity rules
kubectl label nodes k8s-worker-3 disktype=ssd
kubectl label nodes k8s-worker-4 disktype=ssd
kubectl label nodes k8s-worker-5 disktype=hdd
kubectl label nodes k8s-worker-6 disktype=hdd

# Example deployment with node affinity
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database-app
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      tolerations:
      - key: workload
        operator: Equal
        value: database
        effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: disktype
                operator: In
                values:
                - ssd
      containers:
      - name: database
        image: postgres:15
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
EOF
```

### 13.16: Configure Cluster Autoscaling (Manual Setup)

```bash
# Note: This requires cloud provider or custom implementation
# For bare metal, consider cluster-proportional-autoscaler

# Install cluster-proportional-autoscaler
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/cluster-proportional-autoscaler/master/examples/deployment.yaml
```

### 13.17: Setup Backup Strategy for Persistent Volumes

```bash
# Install Velero for backup and disaster recovery
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.1/velero-v1.12.1-linux-amd64.tar.gz
tar -xvf velero-v1.12.1-linux-amd64.tar.gz
sudo mv velero-v1.12.1-linux-amd64/velero /usr/local/bin/

# Configure Velero with file system backup (example)
# You'll need to configure storage backend (S3, MinIO, etc.)
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket velero-backups \
  --secret-file ./credentials-velero \
  --use-volume-snapshots=false \
  --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://minio.velero.svc:9000

# Create backup schedule
velero schedule create daily-backup --schedule="0 2 * * *"
```

### 13.18: Implement Security Best Practices

```bash
# Create PodSecurityPolicy (deprecated in 1.25+, use Pod Security Admission)
# Enable admission controller for pod security

# Create security context constraints
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF

# Install Falco for runtime security
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --namespace falco --create-namespace

# Install OPA Gatekeeper for policy enforcement
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
```

### 13.19: Configure DNS and CoreDNS Tuning

```bash
# Scale CoreDNS for production
kubectl scale deployment coredns --replicas=3 -n kube-system

# Configure CoreDNS cache and optimization
kubectl edit configmap coredns -n kube-system

# Add the following to the Corefile:
# cache 30
# reload
# loadbalance

# Apply custom CoreDNS configuration
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns-custom
  namespace: kube-system
data:
  cache.override: |
    cache {
      success 9984 30
      denial 9984 5
    }
EOF
```

### 13.20: Setup Monitoring Alerts

```bash
# Create PrometheusRule for critical alerts
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
spec:
  groups:
  - name: kubernetes.rules
    interval: 30s
    rules:
    - alert: NodeDown
      expr: up{job="kubernetes-nodes"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Node {{ \$labels.instance }} is down"
        description: "Node {{ \$labels.instance }} has been down for more than 5 minutes."
    
    - alert: PodCrashLooping
      expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ \$labels.namespace }}/{{ \$labels.pod }} is crash looping"
        description: "Pod {{ \$labels.namespace }}/{{ \$labels.pod }} has been restarting frequently."
    
    - alert: HighCPUUsage
      expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage on {{ \$labels.instance }}"
        description: "CPU usage is above 80% for more than 10 minutes."
    
    - alert: HighMemoryUsage
      expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "High memory usage on {{ \$labels.instance }}"
        description: "Memory usage is above 90% for more than 10 minutes."
    
    - alert: DiskSpaceLow
      expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Low disk space on {{ \$labels.instance }}"
        description: "Disk space is below 10% on {{ \$labels.mountpoint }}."
EOF
```

---

## 14. Verification & Testing

### 14.1: Verify Cluster Health

```bash
# Check all nodes
kubectl get nodes -o wide

# Check all system pods
kubectl get pods -A

# Check component health
kubectl get componentstatuses

# Check cluster info
kubectl cluster-info

# Verify etcd cluster
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list

# Check API server endpoints
kubectl get endpoints kubernetes -n default
```

### 14.2: Test High Availability

```bash
# Stop one master node and verify cluster continues to work
# On master-2, run:
sudo shutdown -h now

# From master-1, verify cluster is still operational
kubectl get nodes
kubectl get pods -A

# Create a test deployment
kubectl create deployment ha-test --image=nginx --replicas=5

# Verify deployment succeeds
kubectl get deployment ha-test
kubectl get pods -l app=ha-test -o wide

# Power on master-2 and verify it rejoins
kubectl get nodes

# Cleanup
kubectl delete deployment ha-test
```

### 14.3: Test Load Balancer Failover

```bash
# Check which HAProxy node holds the VIP
ip addr show | grep 10.10.10.6

# Stop HAProxy on the active node
sudo systemctl stop haproxy

# Verify VIP moves to backup node
# On the other HAProxy node:
ip addr show | grep 10.10.10.6

# Test API connectivity
kubectl get nodes

# Restart HAProxy
sudo systemctl start haproxy
```

### 14.4: Network Connectivity Tests

```bash
# Deploy test pods
kubectl run test-pod-1 --image=busybox --command -- sleep 3600
kubectl run test-pod-2 --image=busybox --command -- sleep 3600

# Get pod IPs
kubectl get pods -o wide

# Test pod-to-pod connectivity
kubectl exec test-pod-1 -- ping -c 3 <test-pod-2-ip>

# Test service discovery
kubectl create deployment nginx-test --image=nginx
kubectl expose deployment nginx-test --port=80
kubectl exec test-pod-1 -- wget -O- nginx-test

# Test external connectivity
kubectl exec test-pod-1 -- ping -c 3 8.8.8.8
kubectl exec test-pod-1 -- nslookup google.com

# Cleanup
kubectl delete pod test-pod-1 test-pod-2
kubectl delete deployment nginx-test
kubectl delete service nginx-test
```

### 14.5: Storage Tests

```bash
# Create PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

# Create pod using PVC
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: test-storage-pod
spec:
  containers:
  - name: test
    image: nginx
    volumeMounts:
    - name: storage
      mountPath: /data
  volumes:
  - name: storage
    persistentVolumeClaim:
      claimName: test-pvc
EOF

# Verify PVC is bound
kubectl get pvc test-pvc

# Write data to persistent volume
kubectl exec test-storage-pod -- sh -c "echo 'test data' > /data/test.txt"

# Delete and recreate pod to verify persistence
kubectl delete pod test-storage-pod
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-storage-pod
spec:
  containers:
  - name: test
    image: nginx
    volumeMounts:
    - name: storage
      mountPath: /data
  volumes:
  - name: storage
    persistentVolumeClaim:
      claimName: test-pvc
EOF

# Verify data persisted
kubectl exec test-storage-pod -- cat /data/test.txt

# Cleanup
kubectl delete pod test-storage-pod
kubectl delete pvc test-pvc
```

### 14.6: Performance Benchmarking

```bash
# Install cluster-loader for load testing
git clone https://github.com/kubernetes/perf-tests.git
cd perf-tests/clusterloader2

# Run basic load test
go run cmd/clusterloader.go \
  --testconfig=testing/load/config.yaml \
  --provider=local \
  --kubeconfig=$HOME/.kube/config \
  --nodes=9

# Monitor resource usage during test
kubectl top nodes
kubectl top pods -A
```

### 14.7: Security Validation

```bash
# Run CIS Kubernetes Benchmark using kube-bench
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml

# Check results
kubectl logs -f job/kube-bench

# Run security scanning with Trivy
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm install trivy-operator aqua/trivy-operator --namespace trivy-system --create-namespace

# Scan for vulnerabilities
kubectl get vulnerabilityreports -A
```

### 14.8: Disaster Recovery Test

```bash
# Backup current state
sudo /usr/local/bin/etcd-backup.sh

# Simulate disaster - delete a deployment
kubectl create deployment dr-test --image=nginx --replicas=3
kubectl delete deployment dr-test

# Restore from backup (if needed)
# First, stop kube-apiserver on all masters
sudo mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/

# Restore etcd snapshot
sudo ETCDCTL_API=3 etcdctl snapshot restore /var/backups/etcd/etcd-snapshot-<timestamp>.db \
  --data-dir=/var/lib/etcd-restore

# Move old etcd data
sudo mv /var/lib/etcd /var/lib/etcd-old
sudo mv /var/lib/etcd-restore /var/lib/etcd

# Restart kube-apiserver
sudo mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/

# Verify cluster recovery
kubectl get nodes
kubectl get pods -A
```

### 14.9: Monitoring and Metrics Validation

```bash
# Check metrics server
kubectl top nodes
kubectl top pods -n kube-system

# Access Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Check alert manager
kubectl get svc -n monitoring
```

### 14.10: Application Deployment Test

```bash
# Deploy sample application with all production features
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: sample-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: sample-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - web-app
              topologyKey: kubernetes.io/hostname
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: web-app-svc
  namespace: sample-app
spec:
  type: ClusterIP
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: sample-app
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: web-app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-app-svc
            port:
              number: 80
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: sample-app
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: sample-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF

# Verify deployment
kubectl get all -n sample-app
kubectl get ingress -n sample-app
kubectl get hpa -n sample-app

# Test scaling
kubectl run -it --rm load-generator --image=busybox --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://web-app-svc.sample-app; done"

# Watch HPA in another terminal
kubectl get hpa -n sample-app -w

# Cleanup
kubectl delete namespace sample-app
```

---

## 15. Troubleshooting

### 15.1: Common Issues and Solutions

#### Issue: Nodes in NotReady State

```bash
# Check node status
kubectl describe node <node-name>

# Check kubelet logs
sudo journalctl -u kubelet -f

# Common causes:
# 1. CNI not installed or misconfigured
kubectl get pods -n kube-flannel

# 2. Container runtime issues
sudo systemctl status containerd
sudo journalctl -u containerd -f

# 3. Network connectivity
ping <other-node-ip>

# Restart kubelet
sudo systemctl restart kubelet
```

#### Issue: Pods Stuck in Pending

```bash
# Check pod events
kubectl describe pod <pod-name>

# Common causes:
# 1. Insufficient resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# 2. Taints and tolerations
kubectl describe node <node-name> | grep Taints

# 3. Pod affinity/anti-affinity
kubectl get pods -o wide

# 4. PVC not bound
kubectl get pvc
```

#### Issue: Pods in CrashLoopBackOff

```bash
# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Common causes:
# 1. Application errors - check logs
# 2. Missing ConfigMaps or Secrets
kubectl get configmap
kubectl get secret

# 3. Liveness probe failing
kubectl describe pod <pod-name> | grep -A 10 Liveness
```

#### Issue: Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints <service-name>

# Check if pods are ready
kubectl get pods -l <label-selector>

# Test service from within cluster
kubectl run test --image=busybox --rm -it -- wget -O- http://<service-name>

# Check kube-proxy
kubectl get pods -n kube-system -l k8s-app=kube-proxy
sudo journalctl -u kube-proxy -f

# Verify iptables rules
sudo iptables-save | grep <service-name>
```

#### Issue: DNS Resolution Failures

```bash
# Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns

# Test DNS from pod
kubectl run test-dns --image=busybox --rm -it -- nslookup kubernetes.default

# Verify CoreDNS ConfigMap
kubectl get configmap coredns -n kube-system -o yaml

# Restart CoreDNS
kubectl rollout restart deployment coredns -n kube-system
```

#### Issue: etcd Cluster Unhealthy

```bash
# Check etcd member health
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health

# Check etcd logs
sudo journalctl -u etcd -f
kubectl logs -n kube-system etcd-<master-node>

# Verify etcd cluster members
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  member list
```

#### Issue: Certificate Errors

```bash
# Check certificate expiration
sudo kubeadm certs check-expiration

# Renew certificates (before expiration)
sudo kubeadm certs renew all

# Restart control plane components
sudo systemctl restart kubelet

# Verify certificates
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -text -noout
```

#### Issue: HAProxy/Keepalived Not Working

```bash
# Check HAProxy status
sudo systemctl status haproxy
sudo journalctl -u haproxy -f

# Check Keepalived status
sudo systemctl status keepalived
sudo journalctl -u keepalived -f

# Verify VIP assignment
ip addr show | grep 10.10.10.6

# Test backend connectivity
nc -zv 10.10.10.10 6443
nc -zv 10.10.10.11 6443
nc -zv 10.10.10.12 6443

# Check HAProxy stats
curl http://10.10.10.7:8404/stats
```

#### Issue: High Resource Usage

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -A --sort-by=cpu
kubectl top pods -A --sort-by=memory

# Identify resource-hungry pods
kubectl get pods -A -o json | jq -r '.items[] | select(.status.phase=="Running") | "\(.metadata.namespace)/\(.metadata.name) CPU:\(.spec.containers[0].resources.requests.cpu // "none") MEM:\(.spec.containers[0].resources.requests.memory // "none")"'

# Check for OOMKilled pods
kubectl get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses != null) | select(.status.containerStatuses[].lastState.terminated.reason=="OOMKilled") | "\(.metadata.namespace)/\(.metadata.name)"'
```

#### Issue: Network Policy Blocking Traffic

```bash
# List network policies
kubectl get networkpolicies -A

# Describe specific policy
kubectl describe networkpolicy <policy-name> -n <namespace>

# Test with policy temporarily removed
kubectl delete networkpolicy <policy-name> -n <namespace>
# Test connectivity
# Recreate policy if needed
```

#### Issue: Flannel Issues

```bash
# Check Flannel pods
kubectl get pods -n kube-flannel

# Check Flannel logs
kubectl logs -n kube-flannel -l app=flannel

# Verify Flannel configuration
kubectl get configmap -n kube-flannel kube-flannel-cfg -o yaml

# Check VXLAN interface
ip -d link show flannel.1

# Restart Flannel
kubectl delete pods -n kube-flannel -l app=flannel
```

### 15.2: Debugging Tools and Commands

```bash
# Get detailed cluster information
kubectl cluster-info dump > cluster-info.txt

# Check API server logs
sudo journalctl -u kube-apiserver -f

# Check scheduler logs
kubectl logs -n kube-system kube-scheduler-<master-node>

# Check controller manager logs
kubectl logs -n kube-system kube-controller-manager-<master-node>

# Run ephemeral debug container
kubectl debug <pod-name> -it --image=busybox

# Copy files from pod for inspection
kubectl cp <pod-name>:/path/to/file ./local-file

# Execute commands in running container
kubectl exec -it <pod-name> -- /bin/bash

# Port forward for debugging
kubectl port-forward <pod-name> 8080:80
```

### 15.3: Performance Troubleshooting

```bash
# Check API server latency
kubectl get --raw /metrics | grep apiserver_request_duration_seconds

# Check etcd performance
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint status --write-out=table

# Check slow disk I/O
sudo iostat -x 1

# Network latency check
for node in 10.10.10.{10..18}; do echo -n "$node: "; ping -c 3 $node | tail -1 | awk '{print $4}' | cut -d '/' -f 2; done
```

### 15.4: Log Collection Script

```bash
# Create log collection script
cat <<'EOF' > /usr/local/bin/k8s-log-collector.sh
#!/bin/bash

LOG_DIR="/tmp/k8s-logs-$(date +%Y%m%d-%H%M%S)"
mkdir -p $LOG_DIR

echo "Collecting Kubernetes logs to $LOG_DIR..."

# Node information
kubectl get nodes -o wide > $LOG_DIR/nodes.txt
kubectl describe nodes > $LOG_DIR/nodes-describe.txt

# Pod information
kubectl get pods -A -o wide > $LOG_DIR/pods.txt
kubectl describe pods -A > $LOG_DIR/pods-describe.txt

# Events
kubectl get events -A --sort-by='.lastTimestamp' > $LOG_DIR/events.txt

# Services and endpoints
kubectl get svc -A > $LOG_DIR/services.txt
kubectl get endpoints -A > $LOG_DIR/endpoints.txt

# System component logs
kubectl logs -n kube-system -l component=kube-apiserver --tail=1000 > $LOG_DIR/apiserver.log
kubectl logs -n kube-system -l component=kube-controller-manager --tail=1000 > $LOG_DIR/controller-manager.log
kubectl logs -n kube-system -l component=kube-scheduler --tail=1000 > $LOG_DIR/scheduler.log
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=1000 > $LOG_DIR/coredns.log
kubectl logs -n kube-system -l k8s-app=kube-proxy --tail=1000 > $LOG_DIR/kube-proxy.log

# Flannel logs
kubectl logs -n kube-flannel -l app=flannel --tail=1000 > $LOG_DIR/flannel.log

# System logs
sudo journalctl -u kubelet --since "1 hour ago" > $LOG_DIR/kubelet.log
sudo journalctl -u containerd --since "1 hour ago" > $LOG_DIR/containerd.log

# Create archive
tar -czf $LOG_DIR.tar.gz $LOG_DIR
echo "Logs collected: $LOG_DIR.tar.gz"
EOF

sudo chmod +x /usr/local/bin/k8s-log-collector.sh
```

---

## 16. Maintenance Procedures

### 16.1: Cluster Upgrade Process

```bash
# Check current version
kubectl version --short

# Plan upgrade (on first master)
sudo kubeadm upgrade plan

# Upgrade kubeadm
sudo dnf install -y kubeadm-1.29.0-0 --disableexcludes=kubernetes

# Verify kubeadm version
kubeadm version

# Apply upgrade on first master
sudo kubeadm upgrade apply v1.29.0

# Drain node
kubectl drain k8s-master-1 --ignore-daemonsets

# Upgrade kubelet and kubectl
sudo dnf install -y kubelet-1.29.0-0 kubectl-1.29.0-0 --disableexcludes=kubernetes

# Restart kubelet
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon node
kubectl uncordon k8s-master-1

# Upgrade other master nodes
# On each additional master:
sudo kubeadm upgrade node
kubectl drain <node-name> --ignore-daemonsets
sudo dnf install -y kubelet-1.29.0-0 kubectl-1.29.0-0 --disableexcludes=kubernetes
sudo systemctl daemon-reload
sudo systemctl restart kubelet
kubectl uncordon <node-name>

# Upgrade worker nodes (one at a time)
kubectl drain k8s-worker-1 --ignore-daemonsets --delete-emptydir-data
# On worker node:
sudo dnf install -y kubeadm-1.29.0-0 --disableexcludes=kubernetes
sudo kubeadm upgrade node
sudo dnf install -y kubelet-1.29.0-0 kubectl-1.29.0-0 --disableexcludes=kubernetes
sudo systemctl daemon-reload
sudo systemctl restart kubelet
# From master:
kubectl uncordon k8s-worker-1

# Verify upgrade
kubectl get nodes
```

### 16.2: Node Maintenance

```bash
# Safely drain node for maintenance
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Perform maintenance (OS updates, hardware changes, etc.)
sudo dnf update -y
sudo reboot

# After maintenance, uncordon node
kubectl uncordon <node-name>

# Verify node is ready
kubectl get nodes
kubectl get pods -o wide | grep <node-name>
```

### 16.3: Certificate Rotation

```bash
# Check certificate expiration
sudo kubeadm certs check-expiration

# Renew all certificates
sudo kubeadm certs renew all

# Restart control plane pods
sudo systemctl restart kubelet

# Verify new certificate dates
sudo kubeadm certs check-expiration

# Update kubeconfig
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
```

### 16.4: etcd Defragmentation

```bash
# Check etcd database size
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint status --write-out=table

# Defragment etcd (one member at a time)
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  defrag

# Verify after defragmentation
sudo ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint status --write-out=table
```

### 16.5: Backup and Restore Procedures

#### Full Cluster Backup

```bash
# Create backup directory
BACKUP_DIR="/var/backups/k8s-full-$(date +%Y%m%d-%H%M%S)"
sudo mkdir -p $BACKUP_DIR

# Backup etcd
sudo /usr/local/bin/etcd-backup.sh

# Backup certificates
sudo cp -r /etc/kubernetes/pki $BACKUP_DIR/

# Backup kubeconfig
sudo cp /etc/kubernetes/admin.conf $BACKUP_DIR/

# Backup manifests
sudo cp -r /etc/kubernetes/manifests $BACKUP_DIR/

# Export all resources
kubectl get all --all-namespaces -o yaml > $BACKUP_DIR/all-resources.yaml
kubectl get pv -o yaml > $BACKUP_DIR/persistent-volumes.yaml
kubectl get pvc --all-namespaces -o yaml > $BACKUP_DIR/persistent-volume-claims.yaml

# Create archive
sudo tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
echo "Backup created: $BACKUP_DIR.tar.gz"
```

#### Restore from Backup

```bash
# Stop API server on all masters
sudo mv /etc/kubernetes/manifests/kube-apiserver.yaml /tmp/

# Restore etcd snapshot
sudo ETCDCTL_API=3 etcdctl snapshot restore \
  /var/backups/etcd/etcd-snapshot-<timestamp>.db \
  --data-dir=/var/lib/etcd-restore

# Replace etcd data directory
sudo mv /var/lib/etcd /var/lib/etcd-backup
sudo mv /var/lib/etcd-restore /var/lib/etcd
sudo chown -R etcd:etcd /var/lib/etcd

# Restore certificates if needed
# sudo cp -r $BACKUP_DIR/pki/* /etc/kubernetes/pki/

# Restart API server
sudo mv /tmp/kube-apiserver.yaml /etc/kubernetes/manifests/

# Wait for cluster to stabilize
sleep 30
kubectl get nodes
```

### 16.6: Adding New Nodes

#### Add New Master Node

```bash
# On existing master, generate new join command
kubeadm token create --print-join-command
kubeadm init phase upload-certs --upload-certs

# On new master node, complete pre-installation steps (section 4)
# Then join as control plane
sudo kubeadm join 10.10.10.6:6443 --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane --certificate-key <cert-key> \
  --apiserver-advertise-address=<new-master-ip> \
  --cri-socket unix:///var/run/containerd/containerd.sock

# Configure kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Verify
kubectl get nodes
```

#### Add New Worker Node

```bash
# On existing master, generate join command if needed
kubeadm token create --print-join-command

# On new worker node, complete pre-installation steps (section 4)
# Then join as worker
sudo kubeadm join 10.10.10.6:6443 --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --cri-socket unix:///var/run/containerd/containerd.sock

# From master, verify and label
kubectl get nodes
kubectl label node <new-worker> node-role.kubernetes.io/worker=worker
```

### 16.7: Removing Nodes

```bash
# Drain node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Delete node from cluster
kubectl delete node <node-name>

# On the node being removed, reset kubeadm
sudo kubeadm reset -f
sudo rm -rf /etc/cni/net.d
sudo rm -rf /var/lib/etcd
sudo rm -rf /var/lib/kubelet
sudo rm -rf /var/lib/dockershim
sudo rm -rf /var/run/kubernetes
sudo rm -rf /etc/kubernetes

# Clean up iptables
sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X

# Restart containerd
sudo systemctl restart containerd
```

---

## 17. Production Deployment Checklist

### 17.1: Pre-Deployment Checklist

- [ ] All nodes meet hardware requirements
- [ ] Network connectivity verified between all nodes
- [ ] DNS resolution working correctly
- [ ] NTP synchronized across all nodes
- [ ] Firewall rules configured correctly
- [ ] SELinux set to permissive or disabled
- [ ] Swap disabled on all nodes
- [ ] Required kernel modules loaded
- [ ] Sysctl parameters configured
- [ ] HAProxy and Keepalived tested and working
- [ ] VIP accessible from all nodes

### 17.2: Installation Checklist

- [ ] containerd installed and configured
- [ ] Kubernetes packages installed (kubeadm, kubelet, kubectl)
- [ ] First master node initialized
- [ ] Additional master nodes joined
- [ ] All worker nodes joined
- [ ] Flannel CNI installed and working
- [ ] All nodes in Ready state
- [ ] CoreDNS pods running
- [ ] Metrics server installed

### 17.3: Security Checklist

- [ ] RBAC enabled and configured
- [ ] Pod Security Standards applied
- [ ] Network policies implemented
- [ ] Secrets encrypted at rest
- [ ] API server audit logging enabled
- [ ] Certificate rotation configured
- [ ] TLS enabled for all components
- [ ] Service accounts properly configured
- [ ] Security scanning tools installed (Falco, kube-bench)

### 17.4: High Availability Checklist

- [ ] Multiple master nodes running
- [ ] etcd cluster healthy
- [ ] HAProxy load balancing working
- [ ] Keepalived VIP failover tested
- [ ] Pod disruption budgets configured
- [ ] Anti-affinity rules for critical apps
- [ ] Backup system configured and tested
- [ ] Disaster recovery plan documented

### 17.5: Monitoring Checklist

- [ ] Prometheus installed and configured
- [ ] Grafana dashboards created
- [ ] Alert rules configured
- [ ] Metrics collection verified
- [ ] Log aggregation configured
- [ ] Resource usage monitoring active
- [ ] Health checks configured
- [ ] Uptime monitoring enabled

### 17.6: Operational Checklist

- [ ] Documentation completed
- [ ] Runbooks created for common issues
- [ ] Backup schedule configured
- [ ] Monitoring alerts configured
- [ ] On-call rotation established
- [ ] Escalation procedures defined
- [ ] Change management process defined
- [ ] Incident response plan documented

---

## 18. Useful Commands Reference

### 18.1: Cluster Management

```bash
# View cluster information
kubectl cluster-info
kubectl get nodes
kubectl get componentstatuses

# View all resources
kubectl get all --all-namespaces

# Get cluster events
kubectl get events --all-namespaces --sort-by='.lastTimestamp'

# View API resources
kubectl api-resources

# View API versions
kubectl api-versions
```

### 18.2: Node Operations

```bash
# Describe node
kubectl describe node <node-name>

# Cordon node (mark unschedulable)
kubectl cordon <node-name>

# Uncordon node
kubectl uncordon <node-name>

# Drain node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Taint node
kubectl taint nodes <node-name> key=value:NoSchedule

# Remove taint
kubectl taint nodes <node-name> key:NoSchedule-

# Label node
kubectl label nodes <node-name> key=value

# Remove label
kubectl label nodes <node-name> key-
```

### 18.3: Pod Operations

```bash
# Get pods
kubectl get pods -A
kubectl get pods -n <namespace>

# Describe pod
kubectl describe pod <pod-name> -n <namespace>

# View pod logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
kubectl logs -f <pod-name> -n <namespace>

# Execute command in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash

# Copy files to/from pod
kubectl cp <pod-name>:/path/to/file ./local-file -n <namespace>
kubectl cp ./local-file <pod-name>:/path/to/file -n <namespace>

# Port forward
kubectl port-forward <pod-name> 8080:80 -n <namespace>

# Delete pod
kubectl delete pod <pod-name> -n <namespace>
```

### 18.4: Deployment Operations

```bash
# Create deployment
kubectl create deployment <name> --image=<image>

# Scale deployment
kubectl scale deployment <name> --replicas=5

# Update deployment image
kubectl set image deployment/<name> <container>=<new-image>

# Rollout status
kubectl rollout status deployment/<name>

# Rollout history
kubectl rollout history deployment/<name>

# Rollback deployment
kubectl rollout undo deployment/<name>

# Restart deployment
kubectl rollout restart deployment/<name>
```

### 18.5: Resource Management

```bash
# View resource usage
kubectl top nodes
kubectl top pods -A
kubectl top pods -n <namespace>

# View resource quotas
kubectl get resourcequota -A

# View limit ranges
kubectl get limitrange -A

# View persistent volumes
kubectl get pv
kubectl get pvc -A

# Describe PV
kubectl describe pv <pv-name>
```

### 18.6: Debugging Commands

```bash
# Run temporary pod
kubectl run test --image=busybox --rm -it -- sh

# Debug running pod
kubectl debug <pod-name> -it --image=busybox

# Get pod YAML
kubectl get pod <pod-name> -o yaml

# Get pod JSON
kubectl get pod <pod-name> -o json

# Watch resources
kubectl get pods -w

# Explain resource
kubectl explain pod
kubectl explain pod.spec.containers
```

---

## 19. Additional Resources

### 19.1: Official Documentation

- Kubernetes Official Documentation: https://kubernetes.io/docs/
- kubeadm Documentation: https://kubernetes.io/docs/reference/setup-tools/kubeadm/
- kubectl Reference: https://kubernetes.io/docs/reference/kubectl/
- containerd Documentation: https://containerd.io/docs/
- Flannel Documentation: https://github.com/flannel-io/flannel
- Rancher Documentation: https://rancher.com/docs/

### 19.2: Best Practices Guides

- Kubernetes Production Best Practices: https://learnk8s.io/production-best-practices
- Security Best Practices: https://kubernetes.io/docs/concepts/security/
- CNCF Security Whitepaper: https://www.cncf.io/reports/

### 19.3: Troubleshooting Resources

- Kubernetes Troubleshooting Guide: https://kubernetes.io/docs/tasks/debug/
- Common Issues: https://kubernetes.io/docs/tasks/debug/debug-cluster/
- Debug Pods: https://kubernetes.io/docs/tasks/debug/debug-application/

### 19.4: Community and Support

- Kubernetes Slack: https://slack.k8s.io/
- Kubernetes Forum: https://discuss.kubernetes.io/
- Stack Overflow: https://stackoverflow.com/questions/tagged/kubernetes
- GitHub Issues: https://github.com/kubernetes/kubernetes/issues

---

## 20. Appendix

### 20.1: Environment Variables

```bash
# Useful environment variables for ~/.bashrc or ~/.profile

export KUBECONFIG=$HOME/.kube/config
export PATH=$PATH:/usr/local/bin

# kubectl aliases
alias k='kubectl'
alias kg='kubectl get'
alias kd='kubectl describe'
alias kl='kubectl logs'
alias kx='kubectl exec -it'
alias kdel='kubectl delete'
alias kaf='kubectl apply -f'

# Common commands
alias kgp='kubectl get pods'
alias kgn='kubectl get nodes'
alias kgs='kubectl get svc'
alias kgd='kubectl get deployments'
alias kga='kubectl get all'

# Namespace-specific
alias kgpa='kubectl get pods -A'
alias kgna='kubectl get nodes -A'
alias kgsa='kubectl get svc -A'

# Watch commands
alias kgpw='kubectl get pods -w'
alias kgnw='kubectl get nodes -w'
```

### 20.2: Helpful Scripts

#### Quick Health Check Script

```bash
#!/bin/bash
# save as: k8s-health-check.sh

echo "=== Kubernetes Cluster Health Check ==="
echo ""

echo "1. Checking Nodes:"
kubectl get nodes
echo ""

echo "2. Checking System Pods:"
kubectl get pods -n kube-system
echo ""

echo "3. Checking Flannel:"
kubectl get pods -n kube-flannel
echo ""

echo "4. Checking ComponentStatus:"
kubectl get cs 2>/dev/null || echo "ComponentStatus deprecated in newer versions"
echo ""

echo "5. Checking Cluster Info:"
kubectl cluster-info
echo ""

echo "6. Checking Recent Events:"
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -20
echo ""

echo "7. Checking Resource Usage:"
kubectl top nodes 2>/dev/null || echo "Metrics server not available"
echo ""

echo "=== Health Check Complete ==="
```

#### Node Resource Summary Script

```bash
#!/bin/bash
# save as: node-resource-summary.sh

echo "=== Node Resource Summary ==="
echo ""

for node in $(kubectl get nodes -o name); do
  echo "Node: $node"
  kubectl describe $node | grep -A 5 "Allocated resources"
  echo ""
done
```

### 20.3: Configuration Templates

#### Sample Pod with Best Practices

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
  namespace: production
  labels:
    app: example
    version: v1
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: nginx:1.25
    imagePullPolicy: IfNotPresent
    ports:
    - containerPort: 8080
      protocol: TCP
    env:
    - name: APP_ENV
      value: "production"
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "200m"
    livenessProbe:
      httpGet:
        path: /health
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /var/cache
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - example
          topologyKey: kubernetes.io/hostname
  tolerations:
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 30
  - key: "node.kubernetes.io/not-ready"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 30
```

### 20.4: Monitoring Queries

#### Useful Prometheus Queries

```promql
# Node CPU usage
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Node memory usage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Pod CPU usage
sum(rate(container_cpu_usage_seconds_total{pod!=""}[5m])) by (pod, namespace)

# Pod memory usage
sum(container_memory_working_set_bytes{pod!=""}) by (pod, namespace)

# API server request rate
sum(rate(apiserver_request_total[5m])) by (verb, code)

# etcd leader changes
rate(etcd_server_leader_changes_seen_total[5m])

# Network traffic
sum(rate(container_network_receive_bytes_total[5m])) by (pod)
sum(rate(container_network_transmit_bytes_total[5m])) by (pod)
```

---

## Conclusion

This guide provides a comprehensive approach to setting up a production-ready Kubernetes cluster with high availability, proper monitoring, security hardening, and operational best practices. 

### Key Achievements

1. **High Availability**: 3 master nodes with HAProxy load balancing and Keepalived failover
2. **Scalability**: 6 worker nodes ready for production workloads
3. **Security**: RBAC, network policies, pod security standards, and audit logging
4. **Monitoring**: Prometheus, Grafana, and comprehensive alerting
5. **Management**: Rancher for centralized cluster management
6. **Disaster Recovery**: Automated backups and documented restore procedures

### Next Steps

1. Deploy your applications using the provided best practices
2. Set up CI/CD pipelines for automated deployments
3. Implement additional storage solutions as needed
4. Configure ingress for external access
5. Set up centralized logging (ELK/EFK stack)
6. Implement service mesh (Istio/Linkerd) for advanced traffic management
7. Regular cluster maintenance and upgrades
8. Continuous monitoring and optimization

### Support and Feedback

For issues, improvements, or contributions to this guide:
- Report issues on GitHub
- Submit pull requests for improvements
- Share your deployment experiences

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Author**: Production Kubernetes Team  
**License**: MIT

---

## Quick Reference Card

### Essential Commands

```bash
# Cluster Health
kubectl get nodes
kubectl get pods -A
kubectl cluster-info

# Resource Usage
kubectl top nodes
kubectl top pods -A

# Logs
kubectl logs -f <pod> -n <namespace>
journalctl -u kubelet -f

# Troubleshooting
kubectl describe pod <pod> -n <namespace>
kubectl get events -A --sort-by='.lastTimestamp'

# etcd Health
ETCDCTL_API=3 etcdctl endpoint health

# HAProxy Status
systemctl status haproxy
curl http://10.10.10.7:8404/stats
```

### Important Files and Directories

```
/etc/kubernetes/manifests/          # Static pod manifests
/etc/kubernetes/admin.conf          # Cluster admin kubeconfig
/etc/kubernetes/pki/                # Certificates
/var/lib/etcd/                      # etcd data directory
/var/lib/kubelet/                   # Kubelet data directory
/etc/containerd/config.toml         # containerd configuration
/var/log/pods/                      # Pod logs
```
---

