# Jenkins Master-Agent Setup Guide (RHEL 9.6)

Complete guide for installing Jenkins with Java 21, custom home directory, and SSH-based agent connection.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Java 21 Installation](#java-21-installation)
3. [Jenkins Master Installation](#jenkins-master-installation)
4. [Jenkins Agent Setup](#jenkins-agent-setup)
5. [SSH Key Configuration](#ssh-key-configuration)
6. [Adding Agent to Jenkins](#adding-agent-to-jenkins)
7. [Migration Guide](#migration-guide)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS**: RHEL 9.6
- **RAM**: Minimum 2GB (4GB+ recommended for master)
- **Java**: OpenJDK 21
- **User**: `jenkin` (custom user with home at `/home/jenkin`)
- **Jenkins Home**: `/home/jenkin/.jenkins`

### Initial System Setup

```bash
# Update system
yum update -y

# Enable EPEL and CodeReady Builder repos
subscription-manager repos --enable codeready-builder-for-rhel-$(rpm -E %rhel)-$(arch)-rpms
dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm

# Install essential utilities
yum install -y tar curl vim wget telnet traceroute net-tools unzip zip \
               rsync bind-utils htop httpd-tools yum-utils dnf-utils

# Install fonts required for Jenkins
dnf install -y fontconfig dejavu-sans-fonts dejavu-serif-fonts dejavu-sans-mono-fonts
```

---

## Java 21 Installation

**Perform on both Master and Agent nodes**

### Option 1: Manual Installation (Recommended)

```bash
# Switch to jenkin user
su - jenkin

# Download and extract Java 21
wget -O /home/jenkin/jdk-21_linux-x64_bin.tar.gz \
    "https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.tar.gz"

tar xzf jdk-21_linux-x64_bin.tar.gz
mv jdk-21_linux-x64_bin.tar.gz /tmp/
mv jdk-21* java21

# Set JAVA_HOME for jenkin user
echo -e 'export JAVA_HOME=~/java21\nexport PATH=$JAVA_HOME/bin:$PATH' >> ~/.bash_profile
source ~/.bash_profile

# Verify installation
java -version
```

### System-wide Java Configuration

```bash
# As root user - set Java globally
echo 'export JAVA_HOME=/home/jenkin/java21' > /etc/profile.d/java.sh
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> /etc/profile.d/java.sh
chmod +x /etc/profile.d/java.sh
source /etc/profile.d/java.sh
```

### Alternative: Symlink Method

```bash
# Option for global Java access (run as root)
ln -s /home/jenkin/java21/bin/java /usr/local/bin/java
```

---

## Jenkins Master Installation

### Step 1: Create Jenkins User

```bash
# Create jenkin user with home directory
sudo adduser -m -d /home/jenkin -s /bin/bash jenkin

# Optional: Set password for interactive login
sudo passwd jenkin
```

### Step 2: Install Jenkins Package

```bash
# Add Jenkins repository
sudo wget -O /etc/yum.repos.d/jenkins.repo \
    https://pkg.jenkins.io/redhat-stable/jenkins.repo

# Import Jenkins GPG key
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key

# Install Jenkins
sudo dnf install -y jenkins
```

### Step 3: Configure Jenkins Service

#### Edit Jenkins Configuration File

```bash
sudo vi /etc/sysconfig/jenkins
```

**Update the following parameters:**

```properties
JENKINS_USER="jenkin"
JENKINS_GROUP="jenkin"
JENKINS_HOME="/home/jenkin/.jenkins"
JENKINS_JAVA_CMD="/home/jenkin/java21/bin/java"
JENKINS_PORT="8080"
```

```bash
# Set correct permissions
sudo chmod 644 /etc/sysconfig/jenkins
sudo chown root:root /etc/sysconfig/jenkins
```

#### Create Jenkins Home Directory

```bash
# Create and set permissions
sudo mkdir -p /home/jenkin/.jenkins
sudo chown -R jenkin:jenkin /home/jenkin/.jenkins
sudo chmod -R u+rwX /home/jenkin/.jenkins

# Fix existing Jenkins directories
sudo chown -R jenkin:jenkin /var/lib/jenkins
sudo chown -R jenkin:jenkin /var/cache/jenkins
sudo chown -R jenkin:jenkin /var/log/jenkins
```

### Step 4: Configure SystemD Service

**Backup original service file:**

```bash
sudo cp /usr/lib/systemd/system/jenkins.service \
        /usr/lib/systemd/system/jenkins.service.bak
```

**Edit service configuration:**

```bash
sudo systemctl edit --full jenkins
```

**Replace with this configuration:**

```ini
[Unit]
Description=Jenkins Continuous Integration Server
Requires=network.target
After=network.target
StartLimitBurst=5
StartLimitIntervalSec=5m

[Service]
Type=notify
NotifyAccess=main
ExecStart=/usr/bin/jenkins
Restart=on-failure
SuccessExitStatus=143
User=jenkin
Group=jenkin
Environment="JENKINS_HOME=/home/jenkin/.jenkins"
WorkingDirectory=/home/jenkin/.jenkins
Environment="JENKINS_WEBROOT=%C/jenkins/war"
Environment="JAVA_OPTS=-Djava.awt.headless=true"
Environment="JENKINS_PORT=8080"

[Install]
WantedBy=multi-user.target
```

### Step 5: Start Jenkins

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start Jenkins
sudo systemctl enable jenkins
sudo systemctl start jenkins

# Check status
sudo systemctl status jenkins

# Verify port binding
ss -ltn | grep 8080
```

### Step 6: Initial Setup

```bash
# Get initial admin password
cat /home/jenkin/.jenkins/secrets/initialAdminPassword
```

**Access Jenkins UI:**
```
http://<MASTER_SERVER_IP>:8080
```

Example: `http://10.13.133.178:8080`

---

## Jenkins Agent Setup

### Step 1: Create Jenkins User on Agent

```bash
# On agent server
sudo adduser -m -d /home/jenkin -s /bin/bash jenkin
sudo passwd jenkin  # Optional
```

### Step 2: Install Java 21 on Agent

```bash
# Follow the same Java installation steps as Master
# See "Java 21 Installation" section above
```

### Step 3: Configure SSH (Agent Side)

```bash
# As root on agent server
vi /etc/ssh/sshd_config
```

**Ensure these settings are enabled:**

```bash
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
```

```bash
# Restart SSH service
sudo systemctl restart sshd
```

---

## SSH Key Configuration

### Step 1: Generate SSH Key on Master

```bash
# On master server, switch to jenkin user
su - jenkin

# Generate SSH key pair (no passphrase for automation)
ssh-keygen -t rsa -b 4096 -C "jenkins-agent" -f /home/jenkin/.ssh/id_rsa -N ""

# View the generated keys
ls -la ~/.ssh/
```

### Step 2: Copy Public Key to Agent

#### Method 1: Using ssh-copy-id (Recommended)

```bash
# From master as jenkin user
ssh-copy-id -i /home/jenkin/.ssh/id_rsa.pub -p 32122 jenkin@<AGENT_IP>
```

When prompted, enter the agent password: `32122`

#### Method 2: Manual Copy

```bash
# On master - copy public key content
cat /home/jenkin/.ssh/id_rsa.pub
```

**On agent server:**

```bash
# Switch to jenkin user
su - jenkin

# Create .ssh directory
mkdir -p /home/jenkin/.ssh
chmod 700 /home/jenkin/.ssh

# Add master's public key
vi /home/jenkin/.ssh/authorized_keys
# Paste the public key content here

# Set correct permissions
chmod 600 /home/jenkin/.ssh/authorized_keys
chown -R jenkin:jenkin /home/jenkin/.ssh
```

### Step 3: Test SSH Connection

```bash
# From master as jenkin user
ssh -p 32122 jenkin@<AGENT_IP> "hostname"

# Should connect without password prompt
```

---

## Adding Agent to Jenkins

### Step 1: Add SSH Credentials in Jenkins

1. Navigate to: **Dashboard → Manage Jenkins → Credentials**
2. Click on **(global)** domain
3. Click **Add Credentials**
4. Configure:
   - **Kind**: `SSH Username with private key`
   - **Scope**: `Global`
   - **ID**: `jenkins-agent-ssh-key`
   - **Description**: `SSH key for Jenkins agents`
   - **Username**: `jenkin`
   - **Private Key**: Select **Enter directly**

5. Copy private key from master:

```bash
# On master server
cat /home/jenkin/.ssh/id_rsa
```

6. Paste the entire private key content (including BEGIN/END lines)
7. Click **Create**

### Step 2: Configure Agent Node

1. Navigate to: **Manage Jenkins → Nodes**
2. Click **New Node**
3. Configuration:
   - **Node name**: `agent-01` (or your preferred name)
   - **Type**: Select **Permanent Agent**
   - Click **Create**

4. Node Configuration:
   - **Number of executors**: `2` (adjust based on CPU cores)
   - **Remote root directory**: `/home/jenkin/jenkins`
   - **Labels**: `linux rhel agent` (space-separated)
   - **Usage**: `Use this node as much as possible`
   - **Launch method**: `Launch agents via SSH`
   - **Host**: `<AGENT_IP>` (e.g., 10.13.133.179)
   - **Credentials**: Select `jenkins-agent-ssh-key`
   - **Host Key Verification Strategy**: `Manually trusted key verification strategy`
   - **Port**: `32122` (if using custom SSH port)
   - **JavaPath**: `/home/jenkin/java21/bin/java`

5. Click **Save**

### Step 3: Verify Connection

- Jenkins will automatically attempt to launch the agent
- Check the agent's log for connection status
- Status should show **"Agent is connected and online"**

---

## Migration Guide

### Migrating Users, Roles, and Credentials

#### Prerequisites

```bash
# Ensure same user exists on both servers
# Transfer Java and Gradle installations
scp -P 32122 -rp jdk-* gradle-* jenkin@<NEW_MASTER_IP>:/home/jenkin/.
```

#### Step 1: Migrate Users and Roles

```bash
# From old master to new master
scp -P 32122 -rp /home/jenkin/.jenkins/users/ \
    jenkin@<NEW_MASTER_IP>:/home/jenkin/.jenkins/users/

scp -P 32122 -rp /home/jenkin/.jenkins/roles/ \
    jenkin@<NEW_MASTER_IP>:/home/jenkin/.jenkins/roles/
```

#### Step 2: Migrate Credentials

```bash
# Copy credentials file
scp -P 32122 -rp /home/jenkin/.jenkins/credentials.xml \
    jenkin@<NEW_MASTER_IP>:/home/jenkin/.jenkins/credentials.xml

# Copy secrets directory
scp -P 32122 -rp /home/jenkin/.jenkins/secrets/ \
    jenkin@<NEW_MASTER_IP>:/home/jenkin/.jenkins/secrets/
```

#### Step 3: Migrate Global Configuration

```bash
# Copy main config (includes RBAC settings)
scp -P 32122 -rp /home/jenkin/.jenkins/config.xml \
    jenkin@<NEW_MASTER_IP>:/home/jenkin/.jenkins/config.xml
```

#### Step 4: Verify RBAC Configuration

```bash
# Check Role-Based Authorization Strategy settings
grep -A 50 '<authorizationStrategy class="com.michelin.cio.hudson.plugins.rolestrategy.RoleBasedAuthorizationStrategy"' \
    /home/jenkin/.jenkins/config.xml
```

#### Step 5: Restart Jenkins

```bash
# On new master
ssh -p 32122 jenkin@<NEW_MASTER_IP> "sudo systemctl restart jenkins"

# Or locally
sudo systemctl restart jenkins
```

### Quick Reinstall Script

If you need to reinstall Jenkins:

```bash
#!/bin/bash
# Save as: reinstall-jenkins.sh

systemctl stop jenkins
yum remove jenkins -y

# Backup existing Jenkins home
mv /home/jenkin/.jenkins /home/jenkin/.jenkins_bak_$(date +%F_%T)

# Reinstall
dnf install -y jenkins

# Prepare new home
mkdir -p /home/jenkin/.jenkins
chown -R jenkin:jenkin /home/jenkin/.jenkins

# Start service
systemctl daemon-reload
systemctl enable jenkins
systemctl start jenkins

# Wait and show initial password
sleep 10
systemctl status jenkins
echo ""
echo "Initial Admin Password:"
cat /home/jenkin/.jenkins/secrets/initialAdminPassword
```

```bash
# Make executable and run
chmod +x reinstall-jenkins.sh
sudo ./reinstall-jenkins.sh
```

---

## Troubleshooting

### Jenkins Won't Start

```bash
# Check service status
sudo systemctl status jenkins

# Check logs
sudo journalctl -u jenkins -f

# Check Jenkins log
tail -f /home/jenkin/.jenkins/jenkins.log

# Verify Java
java -version
/home/jenkin/java21/bin/java -version
```

### SSH Connection Issues

```bash
# Test SSH manually
ssh -vvv -p 32122 jenkin@<AGENT_IP>

# Check agent SSH logs
sudo tail -f /var/log/secure

# Verify permissions on agent
ls -la /home/jenkin/.ssh/
cat /home/jenkin/.ssh/authorized_keys
```

### Permission Issues

```bash
# Fix Jenkins home permissions
sudo chown -R jenkin:jenkin /home/jenkin/.jenkins
sudo chmod -R u+rwX /home/jenkin/.jenkins

# Fix SSH permissions
chmod 700 /home/jenkin/.ssh
chmod 600 /home/jenkin/.ssh/authorized_keys
chmod 600 /home/jenkin/.ssh/id_rsa
chmod 644 /home/jenkin/.ssh/id_rsa.pub
```

### Port Already in Use

```bash
# Check what's using port 8080
sudo ss -tlnp | grep 8080
sudo lsof -i :8080

# Kill process or change Jenkins port in /etc/sysconfig/jenkins
```

### Agent Offline

```bash
# Check agent logs in Jenkins UI
# Verify network connectivity
ping <AGENT_IP>
telnet <AGENT_IP> 32122

# Check firewall
sudo firewall-cmd --list-all
sudo firewall-cmd --add-port=32122/tcp --permanent
sudo firewall-cmd --reload
```

---

## Quick Reference

### Important Paths

| Component | Path |
|-----------|------|
| Jenkins Home | `/home/jenkin/.jenkins` |
| Java Home | `/home/jenkin/java21` |
| Initial Password | `/home/jenkin/.jenkins/secrets/initialAdminPassword` |
| Service Config | `/etc/sysconfig/jenkins` |
| SystemD Service | `/usr/lib/systemd/system/jenkins.service` |
| SSH Private Key | `/home/jenkin/.ssh/id_rsa` |
| SSH Public Key | `/home/jenkin/.ssh/id_rsa.pub` |

### Common Commands

```bash
# Service management
sudo systemctl start jenkins
sudo systemctl stop jenkins
sudo systemctl restart jenkins
sudo systemctl status jenkins

# View logs
sudo journalctl -u jenkins -f
tail -f /home/jenkin/.jenkins/jenkins.log

# Check port
ss -ltn | grep 8080

# Switch user
su - jenkin
```

### Default Ports

- **Jenkins Master**: 8080
- **SSH (Custom)**: 32122
- **SSH (Default)**: 22

---

## Security Best Practices

1. **Change Default Port**: Consider changing Jenkins from port 8080
2. **Enable HTTPS**: Configure SSL/TLS for Jenkins
3. **Firewall Rules**: Restrict access to Jenkins and SSH ports
4. **SSH Keys**: Never commit private keys to version control
5. **User Passwords**: Use strong passwords for the `jenkin` user
6. **Regular Updates**: Keep Jenkins and plugins updated
7. **Backup**: Regular backups of `/home/jenkin/.jenkins`

---

## Next Steps

1. Install required Jenkins plugins
2. Configure security realm and authorization
3. Set up build jobs
4. Configure webhooks for Git integration
5. Set up backup strategy
6. Monitor Jenkins performance

---

**Documentation Version**: 1.0  
**Last Updated**: December 2025  
**Tested On**: RHEL 9.6
