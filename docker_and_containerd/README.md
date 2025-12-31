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
