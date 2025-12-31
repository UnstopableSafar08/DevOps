# Docker Installation Guide

Complete step-by-step installation instructions for Docker on various Linux distributions.

## Table of Contents

- [Ubuntu / Debian-based Systems](#ubuntu--debian-based-systems)
- [RHEL / CentOS / Rocky Linux / AlmaLinux](#rhel--centos--rocky-linux--almalinux)
- [Oracle Linux](#oracle-linux)
- [AWS Amazon Linux 2023](#aws-amazon-linux-2023)
- [AWS Amazon Linux 2](#aws-amazon-linux-2)
- [Post-Installation Verification](#post-installation-verification)
- [Production-Ready Best Practices](#production-ready-best-practices)
  - [Security Hardening](#security-hardening)
  - [Resource Management](#resource-management)
  - [Logging and Monitoring](#logging-and-monitoring)
  - [Storage Configuration](#storage-configuration)
  - [Network Configuration](#network-configuration)
  - [Backup and Recovery](#backup-and-recovery)
- [Uninstall Docker](#uninstall-docker)
  - [Ubuntu / Debian Uninstall](#ubuntu--debian-uninstall)
  - [RHEL / CentOS / Rocky / AlmaLinux / Oracle Linux Uninstall](#rhel--centos--rocky--almalinux--oracle-linux-uninstall)
  - [AWS Amazon Linux Uninstall](#aws-amazon-linux-uninstall)
- [Important Notes](#important-notes)
- [Troubleshooting](#troubleshooting)

---

## Ubuntu / Debian-based Systems

```bash
# Update package index
apt update -y

# Install dependencies
apt install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine, CLI, and Compose
apt update -y
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Add current user to docker group (optional)
usermod -aG docker $USER

# Verify Docker
docker --version
docker run hello-world
```

---

## RHEL / CentOS / Rocky Linux / AlmaLinux

```bash
# Install required packages
sudo yum install -y yum-utils

# Add Docker repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker Engine
sudo yum -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add users to docker group
sudo usermod -aG docker $(whoami)
sudo usermod -aG docker root

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
sudo docker -v
```

### Install Docker Compose (Standalone)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Oracle Linux

```bash
# Install required packages
sudo yum install -y yum-utils

# Add Docker repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker Engine
sudo yum -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add users to docker group
sudo usermod -aG docker $(whoami)
sudo usermod -aG docker root

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
sudo docker -v
```

### Install Docker Compose (Standalone)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## AWS Amazon Linux 2023

```bash
# Update system packages
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Add current user to docker group
sudo usermod -aG docker $(whoami)

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
sudo docker --version
```

### Install Docker Compose (Standalone)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## AWS Amazon Linux 2

```bash
# Update system packages
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Add users to docker group
sudo usermod -aG docker $(whoami)
sudo usermod -aG docker ec2-user

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
sudo docker --version
```

### Install Docker Compose (Standalone)
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Post-Installation Verification

After installation on any distribution, verify Docker is working correctly:

```bash
# Test Docker installation
docker run hello-world

# Check Docker service status
sudo systemctl status docker

# View Docker information
docker info
```

---

## Production-Ready Best Practices

### Security Hardening

#### 1. Enable Docker Content Trust
```bash
# Enable Docker Content Trust to verify image signatures
export DOCKER_CONTENT_TRUST=1
echo 'export DOCKER_CONTENT_TRUST=1' >> ~/.bashrc
```

#### 2. Configure Docker Daemon Security Options
Create or edit `/etc/docker/daemon.json`:
```bash
cat > /etc/docker/daemon.json <<EOF
{
  "icc": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp.json",
  "userns-remap": "default"
}
EOF

# Restart Docker to apply changes
systemctl restart docker
```

#### 3. Run Docker Bench Security
```bash
# Clone Docker Bench Security
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security

# Run security audit
sudo sh docker-bench-security.sh
```

#### 4. Limit Container Resources
Always set resource limits in production:
```bash
# Example: Run container with resource limits
docker run -d \
  --memory="512m" \
  --memory-swap="1g" \
  --cpus="1.0" \
  --pids-limit=100 \
  --restart=unless-stopped \
  your-image:tag
```

#### 5. Use Non-Root User in Containers
```dockerfile
# In your Dockerfile
RUN useradd -r -u 1000 appuser
USER appuser
```

#### 6. Keep Docker Updated
```bash
# Ubuntu/Debian
apt update && apt upgrade docker-ce docker-ce-cli containerd.io

# RHEL/CentOS/Oracle
yum update docker-ce docker-ce-cli containerd.io
```

---

### Resource Management

#### 1. Configure Docker Storage Driver
For production, use overlay2 storage driver (default in modern installations):
```bash
# Verify storage driver
docker info | grep "Storage Driver"

# If needed, configure in /etc/docker/daemon.json
{
  "storage-driver": "overlay2"
}
```

#### 2. Set Up Log Rotation
```bash
# Configure in /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5",
    "compress": "true"
  }
}
```

#### 3. Enable Live Restore
Keeps containers running during Docker daemon updates:
```bash
# Add to /etc/docker/daemon.json
{
  "live-restore": true
}
```

#### 4. Configure Default Resource Limits
```bash
# Add to /etc/docker/daemon.json
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

---

### Logging and Monitoring

#### 1. Centralized Logging Setup
```bash
# Configure Docker to use syslog
{
  "log-driver": "syslog",
  "log-opts": {
    "syslog-address": "tcp://192.168.1.100:514",
    "tag": "{{.Name}}/{{.ID}}"
  }
}
```

#### 2. Install cAdvisor for Monitoring
```bash
docker run -d \
  --name=cadvisor \
  --restart=always \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  --detach=true \
  gcr.io/cadvisor/cadvisor:latest
```

#### 3. Enable Prometheus Metrics
```bash
# Add to /etc/docker/daemon.json
{
  "metrics-addr": "127.0.0.1:9323",
  "experimental": true
}
```

#### 4. Set Up Log Aggregation
```bash
# Example with Fluentd
docker run -d \
  --name fluentd \
  --restart=always \
  -p 24224:24224 \
  -v /data/fluentd:/fluentd/log \
  fluent/fluentd:latest
```

---

### Storage Configuration

#### 1. Use Separate Partition for Docker
```bash
# Create dedicated partition for Docker (recommended: 100GB+)
mkfs.ext4 /dev/sdb1
mkdir -p /var/lib/docker
mount /dev/sdb1 /var/lib/docker

# Add to /etc/fstab for persistence
echo '/dev/sdb1 /var/lib/docker ext4 defaults 0 0' >> /etc/fstab
```

#### 2. Configure Data Root Directory
```bash
# Add to /etc/docker/daemon.json
{
  "data-root": "/mnt/docker-data"
}
```

#### 3. Clean Up Unused Resources Regularly
```bash
# Create cleanup script
cat > /usr/local/bin/docker-cleanup.sh <<'EOF'
#!/bin/bash
docker system prune -af --volumes
docker image prune -af
EOF

chmod +x /usr/local/bin/docker-cleanup.sh

# Add to cron (weekly cleanup)
echo "0 2 * * 0 /usr/local/bin/docker-cleanup.sh" | crontab -
```

#### 4. Set Up Volume Backup
```bash
# Backup Docker volumes
docker run --rm \
  -v volume_name:/source:ro \
  -v /backup:/backup \
  alpine tar czf /backup/volume_backup_$(date +%Y%m%d).tar.gz -C /source .
```

---

### Network Configuration

#### 1. Create Custom Bridge Network
```bash
# Create isolated network for production containers
docker network create \
  --driver bridge \
  --subnet=172.20.0.0/16 \
  --ip-range=172.20.240.0/20 \
  --gateway=172.20.0.1 \
  prod-network
```

#### 2. Configure Docker Daemon Network Settings
```bash
# Add to /etc/docker/daemon.json
{
  "bip": "192.168.1.1/24",
  "fixed-cidr": "192.168.1.0/25",
  "default-address-pools": [
    {
      "base": "172.80.0.0/16",
      "size": 24
    }
  ]
}
```

#### 3. Enable IPv6 (if needed)
```bash
# Add to /etc/docker/daemon.json
{
  "ipv6": true,
  "fixed-cidr-v6": "2001:db8:1::/64"
}
```

#### 4. Configure Firewall Rules
```bash
# UFW example (Ubuntu)
ufw allow 2376/tcp  # Docker daemon TLS
ufw allow 2377/tcp  # Swarm cluster management
ufw allow 7946/tcp  # Container network discovery
ufw allow 7946/udp
ufw allow 4789/udp  # Overlay network traffic

# Firewalld example (RHEL/CentOS)
firewall-cmd --permanent --add-port=2376/tcp
firewall-cmd --permanent --add-port=2377/tcp
firewall-cmd --permanent --add-port=7946/tcp
firewall-cmd --permanent --add-port=7946/udp
firewall-cmd --permanent --add-port=4789/udp
firewall-cmd --reload
```

---

### Backup and Recovery

#### 1. Backup Docker Volumes
```bash
# Create backup script
cat > /usr/local/bin/backup-docker-volumes.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/docker-volumes"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

for volume in $(docker volume ls -q); do
  docker run --rm \
    -v $volume:/source:ro \
    -v $BACKUP_DIR:/backup \
    alpine tar czf /backup/${volume}_${DATE}.tar.gz -C /source .
done
EOF

chmod +x /usr/local/bin/backup-docker-volumes.sh
```

#### 2. Backup Docker Images
```bash
# Save critical images
docker save -o /backup/images/myapp_latest.tar myapp:latest

# Or save all images
docker images --format "{{.Repository}}:{{.Tag}}" | \
  xargs -I {} docker save -o /backup/images/{}.tar {}
```

#### 3. Backup Docker Compose Configurations
```bash
# Backup all compose files and .env files
tar czf /backup/docker-compose_$(date +%Y%m%d).tar.gz \
  /opt/docker-apps/ \
  /etc/docker/
```

#### 4. Create Disaster Recovery Plan
```bash
# Document restoration process
cat > /root/docker-restore.md <<'EOF'
# Docker Disaster Recovery

## Restore Docker Volumes
```bash
docker volume create volume_name
docker run --rm -v volume_name:/target -v /backup:/backup \
  alpine tar xzf /backup/volume_backup.tar.gz -C /target
```

## Restore Docker Images
```bash
docker load -i /backup/images/myapp_latest.tar
```

## Restore Configurations
```bash
tar xzf /backup/docker-compose.tar.gz -C /
systemctl restart docker
```
EOF
```

#### 5. Automated Backup Schedule
```bash
# Add to crontab for automated backups
cat > /etc/cron.d/docker-backup <<'EOF'
# Daily volume backup at 2 AM
0 2 * * * root /usr/local/bin/backup-docker-volumes.sh

# Weekly image backup on Sunday at 3 AM
0 3 * * 0 root /usr/local/bin/backup-docker-images.sh

# Monthly full backup on 1st at 4 AM
0 4 1 * * root /usr/local/bin/full-docker-backup.sh
EOF
```

---

### Additional Production Recommendations

#### 1. Use Docker Secrets for Sensitive Data
```bash
# Initialize Docker Swarm (even for single node)
docker swarm init

# Create secret
echo "my_db_password" | docker secret create db_password -

# Use in service
docker service create \
  --name myapp \
  --secret db_password \
  myapp:latest
```

#### 2. Implement Health Checks
```dockerfile
# In Dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1
```

#### 3. Use Multi-Stage Builds
```dockerfile
# Multi-stage build for smaller images
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/index.js"]
```

#### 4. Scan Images for Vulnerabilities
```bash
# Using Docker Scout
docker scout cves your-image:tag

# Using Trivy
docker run aquasec/trivy image your-image:tag
```

#### 5. Implement Rate Limiting and Quotas
```bash
# Set up Docker registry mirror to avoid rate limits
{
  "registry-mirrors": ["https://mirror.gcr.io"]
}
```

---

## Uninstall Docker

### Ubuntu / Debian Uninstall

```bash
# Stop Docker service
systemctl stop docker
systemctl stop containerd

# Remove Docker packages
apt purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras

# Remove Docker repository
rm /etc/apt/sources.list.d/docker.list
rm /etc/apt/keyrings/docker.gpg

# Remove all Docker data, images, containers, and volumes
rm -rf /var/lib/docker
rm -rf /var/lib/containerd

# Remove Docker group (optional)
groupdel docker

# Clean up unused packages
apt autoremove -y
apt autoclean
```

---

### RHEL / CentOS / Rocky / AlmaLinux / Oracle Linux Uninstall

```bash
# Stop Docker service
systemctl stop docker
systemctl stop containerd

# Remove Docker packages
yum remove -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Remove Docker repository
rm /etc/yum.repos.d/docker-ce.repo

# Remove all Docker data, images, containers, and volumes
rm -rf /var/lib/docker
rm -rf /var/lib/containerd

# Remove Docker Compose standalone (if installed)
rm /usr/local/bin/docker-compose

# Remove Docker group (optional)
groupdel docker

# Clean up
yum clean all
```

---

### AWS Amazon Linux Uninstall

```bash
# Stop Docker service
systemctl stop docker

# Remove Docker package
yum remove -y docker

# Remove all Docker data, images, containers, and volumes
rm -rf /var/lib/docker
rm -rf /var/lib/containerd

# Remove Docker Compose standalone (if installed)
rm /usr/local/bin/docker-compose

# Remove Docker group (optional)
groupdel docker

# Clean up
yum clean all
```

---

## Important Notes

1. **Logout Required**: After adding your user to the docker group, you must log out and log back in (or reboot) for the changes to take effect.

2. **Firewall Configuration**: Ensure your firewall allows Docker traffic if needed.

3. **SELinux**: On RHEL-based systems with SELinux enabled, you may need to configure SELinux policies for Docker.

4. **Docker Compose Plugin vs Standalone**: Modern Docker installations include docker compose as a plugin (use `docker compose` instead of `docker-compose`). The standalone installation is still available for compatibility.

5. **Uninstall Warning**: Uninstalling Docker will permanently delete all images, containers, volumes, and custom configuration files. Make sure to backup any important data before proceeding with uninstallation.

---

## Troubleshooting

### Permission Denied Error
If you get a permission denied error when running docker commands:
```bash
# Re-add user to docker group
sudo usermod -aG docker $(whoami)
# Then logout and login again
```

### Docker Service Not Starting
```bash
# Check service status
sudo systemctl status docker

# View logs
sudo journalctl -u docker

# Restart service
sudo systemctl restart docker
```
