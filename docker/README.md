# Docker Installation Guide

Complete step-by-step installation instructions for Docker on various Linux distributions.

## Table of Contents

- [Ubuntu / Debian-based Systems](#ubuntu--debian-based-systems)
- [RHEL / CentOS / Rocky Linux / AlmaLinux](#rhel--centos--rocky-linux--almalinux)
- [Oracle Linux](#oracle-linux)
- [AWS Amazon Linux 2023](#aws-amazon-linux-2023)
- [AWS Amazon Linux 2](#aws-amazon-linux-2)
- [Post-Installation Verification](#post-installation-verification)
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

### Install Required Packages
```bash
sudo yum install -y yum-utils
```

### Add Docker Repository
```bash
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
```

### Install Docker Engine
```bash
sudo yum -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Post-Installation Steps
```bash
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

### Install Required Packages
```bash
sudo yum install -y yum-utils
```

### Add Docker Repository
```bash
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
```

### Install Docker Engine
```bash
sudo yum -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Post-Installation Steps
```bash
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

### Update System Packages
```bash
sudo yum update -y
```

### Install Docker
```bash
sudo yum install -y docker
```

### Post-Installation Steps
```bash
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

### Update System Packages
```bash
sudo yum update -y
```

### Install Docker
```bash
sudo yum install -y docker
```

### Post-Installation Steps
```bash
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

## Important Notes

1. **Logout Required**: After adding your user to the docker group, you must log out and log back in (or reboot) for the changes to take effect.

2. **Firewall Configuration**: Ensure your firewall allows Docker traffic if needed.

3. **SELinux**: On RHEL-based systems with SELinux enabled, you may need to configure SELinux policies for Docker.

4. **Docker Compose Plugin vs Standalone**: Modern Docker installations include docker compose as a plugin (use `docker compose` instead of `docker-compose`). The standalone installation is still available for compatibility.

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
