# HAProxy Migration Guide: CentOS 7 to Oracle Linux/RHEL 9/10

A comprehensive step-by-step guide for migrating HAProxy from CentOS 7 to Oracle Linux or RHEL 9/10 with production-ready configuration.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Version Compatibility Analysis](#version-compatibility-analysis)
- [Phase 1: Pre-Migration Documentation](#phase-1-pre-migration-documentation)
- [Phase 2: Oracle Linux/RHEL 9/10 Preparation](#phase-2-oracle-linuxrhel-910-preparation)
- [Phase 3: System Limits Configuration](#phase-3-system-limits-configuration)
- [Phase 4: Kernel Parameters Configuration](#phase-4-kernel-parameters-configuration)
- [Phase 5: HAProxy Configuration Migration](#phase-5-haproxy-configuration-migration)
- [Phase 6: SSL/TLS Certificate Migration](#phase-6-ssltls-certificate-migration)
- [Phase 7: SELinux Configuration](#phase-7-selinux-configuration)
- [Phase 8: Firewall Configuration](#phase-8-firewall-configuration)
- [Phase 9: Service Deployment](#phase-9-service-deployment)
- [Phase 10: Verification and Testing](#phase-10-verification-and-testing)
- [Phase 11: Performance Tuning](#phase-11-performance-tuning)
- [Phase 12: Production Cutover](#phase-12-production-cutover)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Rollback Procedure](#rollback-procedure)
- [Appendix](#appendix)

---

## Overview

### Migration Scope

This guide covers the complete migration of HAProxy load balancer from CentOS 7 to Oracle Linux or RHEL 9/10.

**Source Environment:**
- Operating System: CentOS 7
- Kernel: 3.10.0-1160.118.1.el7.x86_64
- HAProxy Version: 2.3.12
- OpenSSL Version: 1.0.2k-fips

**Target Environment:**
- Operating System: Oracle Linux 9/10 or RHEL 9/10
- HAProxy Version: 2.8+ or 3.0+ (from official repositories)
- OpenSSL Version: 3.x

**Reference Hardware:**
- CPU: 12 vCPU cores
- RAM: 16 GB
- Network: High-performance network interfaces

### Migration Strategy

**Recommended Approach: Blue-Green Deployment**

1. Build new Oracle Linux/RHEL 9/10 server in parallel
2. Configure and test thoroughly
3. Switch traffic with minimal downtime
4. Keep CentOS 7 system available for quick rollback
5. Monitor new system for 48-72 hours before decommissioning old system

---

## Prerequisites

### Access Requirements

**CentOS 7 Server (Source):**
- Root or sudo access
- SSH access
- Ability to copy files off the server

**Oracle Linux/RHEL 9/10 Server (Target):**
- Root or sudo access
- SSH access
- Internet access for package installation

### Network Requirements

- Source and target servers can communicate (for file transfer)
- Outbound internet access on target server
- Access to firewall/DNS management systems
- Static IP addresses configured

### Backup Requirements

- Minimum 5 GB free disk space on source server
- External storage or SCP/SFTP access for transferring backups
- Documented recovery time objective (RTO) and recovery point objective (RPO)

### Knowledge Requirements

- HAProxy configuration syntax and concepts
- Understanding of load balancing and health checks
- Systemd service management
- Basic Linux networking
- Firewalld and SELinux fundamentals
- SSL/TLS certificate management

---

## Version Compatibility Analysis

### HAProxy Version Changes

**CentOS 7: HAProxy 2.3.12**
- Release Date: July 2008, 2021
- Status: End of Life (Q1 2022)
- No security updates or bug fixes

**Oracle Linux/RHEL 9/10: HAProxy 2.8+ or 3.0+**
- Active development and support
- Security updates available
- Performance improvements
- New features available

### Breaking Changes and Considerations

**Configuration Syntax:**
- Most HAProxy 2.3.x configurations are compatible with 2.8+/3.0+
- Some deprecated directives may need updates
- New recommended practices for certain configurations

**OpenSSL Changes:**
- CentOS 7: OpenSSL 1.0.2k (older cipher suites)
- Oracle Linux/RHEL 9/10: OpenSSL 3.x (modern cipher suites)
- May need to update SSL/TLS configuration
- Legacy cipher support may require explicit configuration

**Module Availability:**
- All standard modules are available
- Some third-party modules may need recompilation

### Decision: Same vs Newer Version

**Option 1: Use Repository Version (RECOMMENDED)**
- Automatic security updates
- Vendor support
- Package management integration
- Regular bug fixes

**Option 2: Compile Specific Version**
- Manual security patching required
- No vendor support
- Dependency management complexity
- Only for specific compatibility requirements

**This guide assumes Option 1: Using repository versions**

---

## Phase 1: Pre-Migration Documentation

### Step 1.1: Document HAProxy Version Information

On the CentOS 7 server, run:

```bash
haproxy -vv
```

Save the complete output to a text file. Record:
- HAProxy version
- OpenSSL version
- Build options
- Feature list
- Compiled modules

### Step 1.2: Document Current System Limits

**Check systemd service limits:**

```bash
systemctl show haproxy | grep -E 'LimitNOFILE|LimitNPROC'
```

Record the output. Expected values might be:
- LimitNOFILE=infinity or specific number
- LimitNPROC=infinity or specific number

**Check runtime limits:**

```bash
cat /proc/$(pidof haproxy | awk '{print $1}')/limits
```

Save the complete output, particularly:
- Max open files (soft and hard limits)
- Max processes (soft and hard limits)

**Check PAM limits:**

```bash
cat /etc/security/limits.conf
cat /etc/security/limits.d/*
```

Save all relevant configurations.

### Step 1.3: Document Systemd Override Files

```bash
ls -la /etc/systemd/system/haproxy.service.d/
cat /etc/systemd/system/haproxy.service.d/*.conf
```

If this directory exists, save all files within it.

### Step 1.4: Backup HAProxy Configuration

**List all HAProxy configuration files:**

```bash
ls -la /etc/haproxy/
```

**Create backup directory:**

```bash
mkdir -p /root/haproxy-migration-backup
cd /root/haproxy-migration-backup
```

**Copy configuration files:**

```bash
cp -r /etc/haproxy/ /root/haproxy-migration-backup/
```

**Validate current configuration:**

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

Ensure it reports "Configuration file is valid"

**Save validation output:**

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg > /root/haproxy-migration-backup/config-validation.txt 2>&1
```

### Step 1.5: Document Current maxconn Settings

```bash
grep -i "maxconn" /etc/haproxy/haproxy.cfg
```

Record all maxconn values found in:
- Global section
- Frontend sections
- Backend sections
- Server definitions

### Step 1.6: Document Kernel Parameters

```bash
sysctl -a | grep -E 'fs.file|net.ipv4|net.core' > /root/haproxy-migration-backup/sysctl-current.txt
```

**Check specific parameters:**

```bash
sysctl fs.file-max
sysctl net.ipv4.ip_nonlocal_bind
sysctl net.ipv4.ip_forward
sysctl net.core.somaxconn
sysctl net.ipv4.tcp_max_syn_backlog
```

**Save sysctl configuration files:**

```bash
cp /etc/sysctl.conf /root/haproxy-migration-backup/
cp -r /etc/sysctl.d/ /root/haproxy-migration-backup/
```

### Step 1.7: Document Network Configuration

**List listening ports:**

```bash
netstat -tulpn | grep haproxy > /root/haproxy-migration-backup/listening-ports.txt
ss -tulpn | grep haproxy >> /root/haproxy-migration-backup/listening-ports.txt
```

**List IP addresses:**

```bash
ip addr show > /root/haproxy-migration-backup/ip-addresses.txt
```

**Check for virtual IPs or floating IPs:**

```bash
ip addr show | grep -E 'inet ' > /root/haproxy-migration-backup/all-ips.txt
```

### Step 1.8: Document Firewall Configuration

**Check firewall status:**

```bash
systemctl status firewalld
firewall-cmd --state
```

**Export firewall rules:**

```bash
firewall-cmd --list-all > /root/haproxy-migration-backup/firewall-config.txt
firewall-cmd --list-all-zones > /root/haproxy-migration-backup/firewall-all-zones.txt
```

**Export iptables rules (if used):**

```bash
iptables-save > /root/haproxy-migration-backup/iptables-rules.txt
```

### Step 1.9: Document SELinux Configuration

**Check SELinux status:**

```bash
getenforce > /root/haproxy-migration-backup/selinux-status.txt
```

**List SELinux contexts:**

```bash
ls -lZ /etc/haproxy/ > /root/haproxy-migration-backup/haproxy-selinux-contexts.txt
```

**List SELinux booleans:**

```bash
getsebool -a | grep haproxy > /root/haproxy-migration-backup/selinux-booleans.txt
```

### Step 1.10: Document SSL/TLS Certificates

**List certificate locations:**

```bash
grep -r "ssl" /etc/haproxy/haproxy.cfg | grep -E 'crt|key|ca-file'
```

**Common certificate locations:**

```bash
find /etc/haproxy/ -type f -name "*.pem" > /root/haproxy-migration-backup/cert-locations.txt
find /etc/haproxy/ -type f -name "*.crt" >> /root/haproxy-migration-backup/cert-locations.txt
find /etc/haproxy/ -type f -name "*.key" >> /root/haproxy-migration-backup/cert-locations.txt
find /etc/pki/tls/ -type f >> /root/haproxy-migration-backup/cert-locations.txt
```

**Backup certificates:**

```bash
mkdir -p /root/haproxy-migration-backup/certificates
```

For each certificate file found, copy to backup directory (adjust paths as needed):

```bash
cp /etc/haproxy/certs/* /root/haproxy-migration-backup/certificates/ 2>/dev/null
cp /etc/pki/tls/certs/*.crt /root/haproxy-migration-backup/certificates/ 2>/dev/null
cp /etc/pki/tls/private/*.key /root/haproxy-migration-backup/certificates/ 2>/dev/null
```

**Document certificate expiration dates:**

```bash
find /etc/haproxy/ -name "*.pem" -o -name "*.crt" | while read cert; do
    echo "Certificate: $cert"
    openssl x509 -in "$cert" -noout -enddate 2>/dev/null
    echo "---"
done > /root/haproxy-migration-backup/certificate-expiry.txt
```

### Step 1.11: Document Service Status

```bash
systemctl status haproxy > /root/haproxy-migration-backup/service-status.txt
systemctl is-enabled haproxy >> /root/haproxy-migration-backup/service-status.txt
```

### Step 1.12: Document Log Configuration

**Check rsyslog configuration for HAProxy:**

```bash
grep -r haproxy /etc/rsyslog.conf /etc/rsyslog.d/ > /root/haproxy-migration-backup/rsyslog-haproxy.txt
```

**Check HAProxy log configuration:**

```bash
grep "log" /etc/haproxy/haproxy.cfg > /root/haproxy-migration-backup/haproxy-log-config.txt
```

### Step 1.13: Document Current File Descriptor Usage

```bash
lsof -u haproxy | wc -l > /root/haproxy-migration-backup/current-fd-usage.txt
cat /proc/sys/fs/file-nr >> /root/haproxy-migration-backup/current-fd-usage.txt
```

### Step 1.14: Create Migration Tarball

```bash
cd /root
tar -czf haproxy-migration-backup-$(date +%Y%m%d-%H%M%S).tar.gz haproxy-migration-backup/
```

**Verify tarball:**

```bash
tar -tzf haproxy-migration-backup-*.tar.gz | head -20
```

**Transfer to safe location:**

```bash
# Option 1: SCP to another server
scp haproxy-migration-backup-*.tar.gz user@backup-server:/backup/path/

# Option 2: Copy to external storage
cp haproxy-migration-backup-*.tar.gz /mnt/backup/

# Option 3: Store locally but verify
ls -lh haproxy-migration-backup-*.tar.gz
md5sum haproxy-migration-backup-*.tar.gz > haproxy-migration-backup.md5
```

---

## Phase 2: Oracle Linux/RHEL 9/10 Preparation

### Step 2.1: Install Oracle Linux/RHEL 9/10

Perform a fresh installation of Oracle Linux 9/10 or RHEL 9/10 following vendor documentation.

**Post-installation verification:**

```bash
cat /etc/os-release
uname -r
```

Expected output for Oracle Linux 10:
```
NAME="Oracle Linux Server"
VERSION="10.0"
```

### Step 2.2: Update System Packages

```bash
dnf update -y
```

**Reboot if kernel was updated:**

```bash
reboot
```

### Step 2.3: Configure Network Settings

**Set hostname:**

```bash
hostnamectl set-hostname your-haproxy-hostname
```

**Configure static IP (if needed):**

Edit the network configuration file:

```bash
vi /etc/sysconfig/network-scripts/ifcfg-<interface-name>
```

Or use nmcli:

```bash
nmcli connection modify <connection-name> ipv4.addresses <IP>/<CIDR>
nmcli connection modify <connection-name> ipv4.gateway <gateway-IP>
nmcli connection modify <connection-name> ipv4.dns <DNS-IP>
nmcli connection modify <connection-name> ipv4.method manual
nmcli connection up <connection-name>
```

**Verify network configuration:**

```bash
ip addr show
ip route show
ping -c 4 8.8.8.8
```

### Step 2.4: Set System Timezone

```bash
timedatectl set-timezone Your/Timezone
timedatectl status
```

### Step 2.5: Configure NTP/Chrony

**Verify chronyd is running:**

```bash
systemctl status chronyd
systemctl enable chronyd
systemctl start chronyd
```

**Check time synchronization:**

```bash
chronyc tracking
chronyc sources
```

### Step 2.6: Install HAProxy

**Search for available HAProxy versions:**

```bash
dnf search haproxy
dnf info haproxy
```

**Install HAProxy:**

```bash
dnf install haproxy -y
```

**Verify installation:**

```bash
haproxy -vv
```

Record the installed version and compare with CentOS 7 version.

**Check installed files:**

```bash
rpm -ql haproxy | grep -E 'haproxy.cfg|haproxy.service'
```

### Step 2.7: Verify Directory Structure

```bash
ls -la /etc/haproxy/
ls -la /var/lib/haproxy/
ls -la /var/log/haproxy/ 2>/dev/null
```

**Create log directory if it doesn't exist:**

```bash
mkdir -p /var/log/haproxy
```

### Step 2.8: Do Not Start HAProxy Yet

**Ensure HAProxy is stopped and disabled:**

```bash
systemctl stop haproxy
systemctl disable haproxy
systemctl status haproxy
```

This prevents HAProxy from starting with default configuration before migration is complete.

---

## Phase 3: System Limits Configuration

### Step 3.1: Understand Limit Requirements

**HAProxy Requirements for High-Concurrency Load Balancer:**
- LimitNOFILE: 100000 (file descriptors for connections)
- LimitNPROC: 9000 (processes/threads)

**Why these values:**
- Each client connection requires 1 file descriptor
- Each backend connection requires 1 file descriptor
- Additional file descriptors for logs, sockets, and configuration files
- Process limit prevents runaway processes

### Step 3.2: Configure PAM User Limits

**Create limits configuration file:**

```bash
vi /etc/security/limits.d/haproxy_limits.conf
```

**Add the following content:**

```
# HAProxy worker user limits
haproxy    soft    nofile    100000
haproxy    hard    nofile    100000
haproxy    soft    nproc     10000
haproxy    hard    nproc     10000

# Root user limits (HAProxy master process runs as root)
root       soft    nofile    100000
root       hard    nofile    100000
root       soft    nproc     10000
root       hard    nproc     10000
```

**Save and exit the file**

**Verify the file was created:**

```bash
cat /etc/security/limits.d/haproxy_limits.conf
```

**Important Note:**
PAM limits apply to interactive login sessions. Services managed by systemd use systemd's own limits, which we configure in the next step.

### Step 3.3: Create Systemd Override Directory

```bash
mkdir -p /etc/systemd/system/haproxy.service.d/
```

**Verify directory creation:**

```bash
ls -la /etc/systemd/system/haproxy.service.d/
```

### Step 3.4: Configure Systemd Service Limits

**Create systemd limits override file:**

```bash
vi /etc/systemd/system/haproxy.service.d/limits.conf
```

**Add the following content:**

```ini
[Service]
LimitNOFILE=100000
LimitNPROC=9000
```

**Save and exit the file**

**Verify the file was created:**

```bash
cat /etc/systemd/system/haproxy.service.d/limits.conf
```

### Step 3.5: Reload Systemd Configuration

```bash
systemctl daemon-reload
```

**Verify the override is loaded:**

```bash
systemctl show haproxy | grep -E 'LimitNOFILE|LimitNPROC'
```

Expected output:
```
LimitNOFILE=100000
LimitNOFILESoft=100000
LimitNPROC=9000
LimitNPROCSoft=9000
```

**Important:** These limits will not show actual values until HAProxy service is started, but the configuration is now in place.

---

## Phase 4: Kernel Parameters Configuration

### Step 4.1: Configure System-Wide File Descriptor Limit

**Create sysctl configuration file:**

```bash
vi /etc/sysctl.d/99-haproxy-fd.conf
```

**Add the following content:**

```
# System-wide maximum file descriptors
fs.file-max = 500000
```

**Save and exit the file**

### Step 4.2: Configure Network Kernel Parameters

**Create network tuning configuration file:**

```bash
vi /etc/sysctl.d/99-haproxy-network.conf
```

**Add the following content:**

```
# Allow HAProxy to bind to non-local IP addresses
net.ipv4.ip_nonlocal_bind = 1

# Enable IP forwarding (if HAProxy needs to forward packets)
net.ipv4.ip_forward = 1

# Enable TCP connection reuse
net.ipv4.tcp_tw_reuse = 1

# Increase socket listen backlog
net.core.somaxconn = 4096

# Increase SYN backlog queue
net.ipv4.tcp_max_syn_backlog = 8192

# Reduce FIN-WAIT-2 timeout
net.ipv4.tcp_fin_timeout = 30

# TCP keepalive settings
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15
```

**Save and exit the file**

### Step 4.3: Apply Kernel Parameters

```bash
sysctl --system
```

This command loads all sysctl configurations from /etc/sysctl.conf and /etc/sysctl.d/

**Alternative - apply specific file:**

```bash
sysctl -p /etc/sysctl.d/99-haproxy-fd.conf
sysctl -p /etc/sysctl.d/99-haproxy-network.conf
```

### Step 4.4: Verify Kernel Parameters

**Check file descriptor limit:**

```bash
sysctl fs.file-max
```

Expected output: `fs.file-max = 500000`

**Check network parameters:**

```bash
sysctl net.ipv4.ip_nonlocal_bind
sysctl net.ipv4.ip_forward
sysctl net.core.somaxconn
sysctl net.ipv4.tcp_max_syn_backlog
```

**View all applied parameters:**

```bash
sysctl -a | grep -E 'fs.file|net.ipv4.ip_nonlocal|net.core.somaxconn'
```

### Step 4.5: Verify Parameters Persist After Reboot

**Optional - Test reboot persistence:**

```bash
# Reboot the system
reboot

# After reboot, verify parameters
sysctl fs.file-max
sysctl net.ipv4.ip_nonlocal_bind
```

---

## Phase 5: HAProxy Configuration Migration

### Step 5.1: Transfer Configuration Files to New Server

**On CentOS 7 server:**

```bash
scp haproxy-migration-backup-*.tar.gz user@new-server-ip:/tmp/
```

**On Oracle Linux/RHEL 9/10 server:**

```bash
cd /tmp
tar -xzf haproxy-migration-backup-*.tar.gz
ls -la haproxy-migration-backup/
```

### Step 5.2: Review CentOS 7 Configuration

```bash
cd /tmp/haproxy-migration-backup/haproxy/
ls -la
cat haproxy.cfg
```

**Review configuration for compatibility issues:**

1. Check for deprecated directives
2. Review SSL/TLS configuration
3. Check for custom module usage
4. Verify backend server addresses are still valid
5. Review timeout values

### Step 5.3: Backup Default Oracle Linux/RHEL Configuration

```bash
cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.original
```

### Step 5.4: Copy CentOS 7 Configuration

```bash
cp /tmp/haproxy-migration-backup/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg
```

**If you have additional configuration files:**

```bash
cp /tmp/haproxy-migration-backup/haproxy/*.cfg /etc/haproxy/
```

### Step 5.5: Review and Update Configuration for New Version

**Open configuration file:**

```bash
vi /etc/haproxy/haproxy.cfg
```

**Key areas to review and potentially update:**

#### A. Global Section Review

Check maxconn alignment with system limits:

```
global
    maxconn 40000
```

**Calculation:**
- LimitNOFILE = 100000
- maxconn should be less than (LimitNOFILE / 2)
- Recommended: maxconn = 40000 to 45000
- This leaves buffer for backend connections and overhead

**If maxconn is too high, adjust it:**

```
global
    maxconn 40000  # Adjust based on your requirements
```

#### B. SSL/TLS Configuration Review

**Old CentOS 7 configuration might have:**

```
bind *:443 ssl crt /etc/haproxy/certs/certificate.pem
```

**May need to update cipher suites for OpenSSL 3.x:**

```
bind *:443 ssl crt /etc/haproxy/certs/certificate.pem ssl-min-ver TLSv1.2 ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
```

**For legacy client support (not recommended for security):**

```
bind *:443 ssl crt /etc/haproxy/certs/certificate.pem ssl-min-ver TLSv1.0
```

#### C. Stats Socket Configuration

Verify the stats socket path exists:

```
global
    stats socket /var/lib/haproxy/stats
```

**Check if directory exists:**

```bash
ls -la /var/lib/haproxy/
```

**If directory doesn't exist, create it:**

```bash
mkdir -p /var/lib/haproxy
chown haproxy:haproxy /var/lib/haproxy
```

#### D. Log Configuration

Update log socket path if needed:

```
global
    log /dev/log local0
    log /dev/log local1 notice
```

**For systemd-journald integration:**

```
global
    log stdout format raw local0
```

### Step 5.6: Set Correct File Permissions

```bash
chown root:root /etc/haproxy/haproxy.cfg
chmod 644 /etc/haproxy/haproxy.cfg
```

**If you have additional configuration files:**

```bash
chown root:root /etc/haproxy/*.cfg
chmod 644 /etc/haproxy/*.cfg
```

### Step 5.7: Validate HAProxy Configuration

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

**Expected output:**

```
Configuration file is valid
```

**If errors occur:**

1. Note the error message and line number
2. Open the configuration file: `vi /etc/haproxy/haproxy.cfg`
3. Go to the indicated line number
4. Fix the syntax error
5. Re-validate: `haproxy -c -f /etc/haproxy/haproxy.cfg`
6. Repeat until validation succeeds

**Common validation errors and fixes:**

**Error: "parsing [/etc/haproxy/haproxy.cfg:X] : unknown keyword 'XXX'"**
- Solution: The directive is deprecated or renamed in newer version
- Check HAProxy documentation for the correct directive name

**Error: "parsing [/etc/haproxy/haproxy.cfg:X] : SSL is not enabled"**
- Solution: HAProxy was not compiled with SSL support (unlikely in repository packages)
- Verify: `haproxy -vv | grep SSL`

**Error: Certificate file not found**
- Solution: Certificates not yet migrated, continue to Phase 6

### Step 5.8: Compare Configuration Differences

**View differences between old and new default configurations:**

```bash
diff /etc/haproxy/haproxy.cfg.original /etc/haproxy/haproxy.cfg
```

**Review the differences to ensure nothing important was missed**

### Step 5.9: Document Configuration Changes

Create a changelog file:

```bash
vi /etc/haproxy/MIGRATION-CHANGELOG.txt
```

Document all changes made to the configuration:

```
Date: YYYY-MM-DD
Migrated from: CentOS 7 HAProxy 2.3.12
Migrated to: Oracle Linux/RHEL 9/10 HAProxy X.X.X

Changes made:
1. Updated maxconn from X to Y (reason)
2. Updated SSL cipher suites for OpenSSL 3.x compatibility
3. Changed log socket to stdout for systemd integration
4. (list all changes)
```

---

## Phase 6: SSL/TLS Certificate Migration

### Step 6.1: Identify Certificate Locations from Backup

```bash
cat /tmp/haproxy-migration-backup/cert-locations.txt
```

Review the list of certificate files.

### Step 6.2: Create Certificate Directory Structure

**Standard location for HAProxy certificates:**

```bash
mkdir -p /etc/haproxy/certs
```

**Set directory permissions:**

```bash
chown root:root /etc/haproxy/certs
chmod 750 /etc/haproxy/certs
```

### Step 6.3: Copy Certificate Files

**From backup location:**

```bash
cp /tmp/haproxy-migration-backup/certificates/*.pem /etc/haproxy/certs/
cp /tmp/haproxy-migration-backup/certificates/*.crt /etc/haproxy/certs/
cp /tmp/haproxy-migration-backup/certificates/*.key /etc/haproxy/certs/
```

**If certificates are in separate .crt and .key files, combine them:**

HAProxy requires certificates in PEM format with the following order:
1. Server certificate
2. Intermediate certificates (if any)
3. Private key

```bash
cat /etc/haproxy/certs/server.crt /etc/haproxy/certs/intermediate.crt /etc/haproxy/certs/server.key > /etc/haproxy/certs/combined.pem
```

### Step 6.4: Set Certificate Permissions

```bash
chown root:root /etc/haproxy/certs/*
chmod 600 /etc/haproxy/certs/*.pem
chmod 600 /etc/haproxy/certs/*.key
chmod 644 /etc/haproxy/certs/*.crt
```

**Security Note:** Private keys should be readable only by root (600 permissions)

### Step 6.5: Verify Certificate Validity

**Check certificate expiration:**

```bash
openssl x509 -in /etc/haproxy/certs/certificate.pem -noout -enddate
```

**Check certificate details:**

```bash
openssl x509 -in /etc/haproxy/certs/certificate.pem -noout -text
```

**Verify certificate chain:**

```bash
openssl verify -CAfile /etc/pki/tls/certs/ca-bundle.crt /etc/haproxy/certs/certificate.pem
```

### Step 6.6: Test Certificate with OpenSSL 3.x

**Verify the certificate works with OpenSSL 3.x:**

```bash
openssl s_server -accept 4433 -cert /etc/haproxy/certs/certificate.pem -key /etc/haproxy/certs/certificate.pem -www
```

**In another terminal, test connection:**

```bash
openssl s_client -connect localhost:4433 -servername yourdomain.com
```

**Press Ctrl+C to stop the test server**

### Step 6.7: Update Certificate Paths in HAProxy Configuration

**Open HAProxy configuration:**

```bash
vi /etc/haproxy/haproxy.cfg
```

**Update certificate paths in bind directives:**

```
bind *:443 ssl crt /etc/haproxy/certs/certificate.pem
```

**If you have multiple certificates:**

```
bind *:443 ssl crt /etc/haproxy/certs/
```

This will load all .pem files from the directory.

**Save and validate configuration:**

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

### Step 6.8: Handle Certificate Renewal Configuration

**If using certbot or ACME client, reinstall and reconfigure:**

```bash
dnf install certbot -y
```

**Configure renewal hooks if needed**

**Document certificate renewal process in:**

```bash
vi /etc/haproxy/CERTIFICATE-RENEWAL.txt
```

---

## Phase 7: SELinux Configuration

### Step 7.1: Check SELinux Status

```bash
getenforce
```

Possible outputs:
- Enforcing: SELinux is active and enforcing policies
- Permissive: SELinux is active but only logging violations
- Disabled: SELinux is disabled

### Step 7.2: Review CentOS 7 SELinux Configuration

```bash
cat /tmp/haproxy-migration-backup/selinux-status.txt
cat /tmp/haproxy-migration-backup/selinux-booleans.txt
```

### Step 7.3: Restore SELinux Contexts

**Restore default contexts for HAProxy files:**

```bash
restorecon -Rv /etc/haproxy/
restorecon -Rv /var/lib/haproxy/
```

**Verify contexts:**

```bash
ls -lZ /etc/haproxy/
ls -lZ /var/lib/haproxy/
```

Expected context types:
- Configuration files: `haproxy_conf_t` or `etc_t`
- Runtime files: `haproxy_var_lib_t`

### Step 7.4: Configure SELinux Booleans

**List HAProxy-related booleans:**

```bash
getsebool -a | grep haproxy
```

**Common boolean needed for HAProxy:**

```bash
setsebool -P haproxy_connect_any 1
```

**Explanation:**
- `haproxy_connect_any`: Allows HAProxy to connect to any TCP port (needed for backend connections)
- `-P`: Makes the change persistent across reboots

**Other potentially needed booleans:**

```bash
# If HAProxy needs to bind to unusual ports
semanage port -a -t haproxy_port_t -p tcp 8080

# If HAProxy reads from NFS
setsebool -P haproxy_use_nfs 1
```

### Step 7.5: Test HAProxy with SELinux Enforcing

**Start HAProxy temporarily to test:**

```bash
systemctl start haproxy
systemctl status haproxy
```

**Check for SELinux denials:**

```bash
ausearch -m avc -ts recent | grep haproxy
```

Or:

```bash
journalctl -t setroubleshoot
```

### Step 7.6: Fix SELinux Denials if Found

**If denials are found, analyze them:**

```bash
ausearch -m avc -ts recent | audit2why
```

**Generate and apply custom policy if needed:**

```bash
ausearch -m avc -ts recent | grep haproxy | audit2allow -M haproxy_custom
semodule -i haproxy_custom.pp
```

**Important:** Only create custom policies if absolutely necessary and after understanding the security implications.

### Step 7.7: Verify SELinux is Not Blocking HAProxy

**Check HAProxy can start:**

```bash
systemctl restart haproxy
systemctl status haproxy
```

**Verify no denials:**

```bash
ausearch -m avc -ts recent | grep haproxy
```

Expected: No output (no denials)

### Step 7.8: Stop HAProxy (Preparation for Next Phase)

```bash
systemctl stop haproxy
```

We will start it properly after firewall configuration.

---

## Phase 8: Firewall Configuration

### Step 8.1: Check Firewalld Status

```bash
systemctl status firewalld
```

**If not running, enable and start:**

```bash
systemctl enable firewalld
systemctl start firewalld
```

### Step 8.2: Review CentOS 7 Firewall Configuration

```bash
cat /tmp/haproxy-migration-backup/firewall-config.txt
```

Note all ports and services that were allowed.

### Step 8.3: List Current Firewall Configuration

```bash
firewall-cmd --list-all
```

### Step 8.4: Configure Standard HTTP/HTTPS Ports

**Add HTTP service:**

```bash
firewall-cmd --permanent --add-service=http
```

**Add HTTPS service:**

```bash
firewall-cmd --permanent --add-service=https
```

**These commands allow:**
- TCP port 80 (HTTP)
- TCP port 443 (HTTPS)

### Step 8.5: Add Custom Ports

**If HAProxy uses custom ports, add them:**

**Example: HAProxy stats page on port 8404:**

```bash
firewall-cmd --permanent --add-port=8404/tcp
```

**Example: Custom backend ports:**

```bash
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --permanent --add-port=8443/tcp
```

**Add multiple ports at once:**

```bash
firewall-cmd --permanent --add-port={8080,8443,8404}/tcp
```

### Step 8.6: Configure Source IP Restrictions (if needed)

**Allow traffic only from specific IP ranges:**

**Example: Allow from office network:**

```bash
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port port="8404" protocol="tcp" accept'
```

**Example: Allow HAProxy stats only from management network:**

```bash
firewall-cmd --permanent --zone=trusted --add-source=10.0.0.0/8
firewall-cmd --permanent --zone=trusted --add-port=8404/tcp
```

### Step 8.7: Reload Firewall Configuration

```bash
firewall-cmd --reload
```

### Step 8.8: Verify Firewall Configuration

**List all active rules:**

```bash
firewall-cmd --list-all
```

**Verify specific ports:**

```bash
firewall-cmd --list-ports
firewall-cmd --list-services
```

**Expected output should include:**
- Services: http, https
- Ports: Any custom ports you added (e.g., 8404/tcp)

### Step 8.9: Test Firewall from External System

**From another server, test connectivity:**

```bash
# Test HTTP
telnet haproxy-server-ip 80

# Test HTTPS
telnet haproxy-server-ip 443

# Test custom port
telnet haproxy-server-ip 8404
```

**Or use nc (netcat):**

```bash
nc -zv haproxy-server-ip 80
nc -zv haproxy-server-ip 443
nc -zv haproxy-server-ip 8404
```

**Note:** At this point, HAProxy is not running, so the connection will be refused. This is expected. We're just verifying the firewall is not blocking.

---

## Phase 9: Service Deployment

### Step 9.1: Final Configuration Validation

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

Ensure output is: `Configuration file is valid`

### Step 9.2: Configure Rsyslog for HAProxy Logging (Optional)

**If HAProxy uses syslog, configure rsyslog:**

**Create rsyslog configuration:**

```bash
vi /etc/rsyslog.d/haproxy.conf
```

**Add the following content:**

```
$ModLoad imudp
$UDPServerRun 514

local0.* /var/log/haproxy/haproxy.log
local1.notice /var/log/haproxy/haproxy-admin.log
```

**Create log directory:**

```bash
mkdir -p /var/log/haproxy
```

**Restart rsyslog:**

```bash
systemctl restart rsyslog
```

**Verify rsyslog is listening:**

```bash
netstat -ulpn | grep 514
```

### Step 9.3: Enable HAProxy Service

```bash
systemctl enable haproxy
```

**Verify it's enabled:**

```bash
systemctl is-enabled haproxy
```

Expected output: `enabled`

### Step 9.4: Start HAProxy Service

```bash
systemctl start haproxy
```

### Step 9.5: Verify Service Status

```bash
systemctl status haproxy
```

**Expected output indicators:**
- Active: active (running)
- Main PID: shows a process ID
- No error messages in the status output

**If service fails to start:**

```bash
journalctl -xeu haproxy
```

Review the error messages and fix configuration issues.

### Step 9.6: Verify HAProxy Process

```bash
ps aux | grep haproxy
```

Expected: Multiple haproxy processes (master and workers)

### Step 9.7: Verify Listening Ports

```bash
ss -tulpn | grep haproxy
```

**Verify all expected ports are listening:**
- Port 80 (HTTP)
- Port 443 (HTTPS)
- Port 8404 (stats, if configured)
- Any other configured ports

### Step 9.8: Check HAProxy Stats Socket

**If stats socket is configured:**

```bash
echo "show info" | socat stdio /var/lib/haproxy/stats
```

**Or use haproxy command line:**

```bash
echo "show info" | nc -U /var/lib/haproxy/stats
```

### Step 9.9: Review Initial Logs

**Check systemd journal:**

```bash
journalctl -u haproxy -n 50
```

**Check syslog (if configured):**

```bash
tail -f /var/log/haproxy/haproxy.log
```

**Look for:**
- No error messages
- Backend servers being marked as UP
- Successful SSL certificate loading

---

## Phase 10: Verification and Testing

### Step 10.1: Verify System Limits Are Applied

**Check systemd configuration:**

```bash
systemctl show haproxy | grep -E 'LimitNOFILE|LimitNPROC'
```

Expected output:
```
LimitNOFILE=100000
LimitNOFILESoft=100000
LimitNPROC=9000
LimitNPROCSoft=9000
```

**Check runtime limits:**

```bash
cat /proc/$(pidof haproxy | awk '{print $1}')/limits
```

**Look for:**
```
Max open files            100000               100000               files
Max processes             9000                 9000                 processes
```

### Step 10.2: Verify Kernel Parameters

```bash
sysctl fs.file-max
sysctl net.ipv4.ip_nonlocal_bind
sysctl net.core.somaxconn
sysctl net.ipv4.tcp_max_syn_backlog
```

**All values should match what was configured in Phase 4**

### Step 10.3: Test HTTP Connectivity

**From the HAProxy server:**

```bash
curl -I http://localhost
```

**From an external system:**

```bash
curl -I http://haproxy-server-ip
```

Expected: HTTP response headers from backend server

### Step 10.4: Test HTTPS Connectivity

**From the HAProxy server:**

```bash
curl -Ik https://localhost
```

**From an external system:**

```bash
curl -Ik https://haproxy-server-ip
```

**Or specify the domain:**

```bash
curl -Ik https://your-domain.com
```

**Test SSL certificate:**

```bash
openssl s_client -connect haproxy-server-ip:443 -servername your-domain.com
```

**Verify:**
- Certificate chain is valid
- Certificate is not expired
- Correct cipher suite is negotiated

### Step 10.5: Test Backend Health Checks

**Access HAProxy stats page (if configured):**

```bash
curl http://haproxy-server-ip:8404/stats
```

**Or via browser:** Open `http://haproxy-server-ip:8404/stats`

**Verify:**
- All backend servers show as UP/green
- No errors in the stats
- Connection counts are incrementing

**Using stats socket:**

```bash
echo "show stat" | socat stdio /var/lib/haproxy/stats
```

### Step 10.6: Test Load Balancing

**Make multiple requests to verify load distribution:**

```bash
for i in {1..10}; do curl -s http://haproxy-server-ip | grep -i "server\|hostname"; done
```

**Verify requests are distributed across backend servers according to your load balancing algorithm**

### Step 10.7: Test SSL/TLS Versions

**Test TLS 1.2:**

```bash
openssl s_client -connect haproxy-server-ip:443 -tls1_2
```

**Test TLS 1.3:**

```bash
openssl s_client -connect haproxy-server-ip:443 -tls1_3
```

**Verify deprecated protocols are disabled:**

```bash
openssl s_client -connect haproxy-server-ip:443 -tls1
```

Expected: Connection should fail if TLS 1.0 is disabled

### Step 10.8: Test with SSL Labs (for public-facing servers)

**Visit:** https://www.ssllabs.com/ssltest/

**Enter your domain name and run the test**

**Expected grade:** A or A+ (depending on your SSL configuration)

### Step 10.9: Verify SELinux is Not Blocking

```bash
ausearch -m avc -ts recent | grep haproxy
```

Expected: No output (no denials)

**If denials exist, review and fix them**

### Step 10.10: Check Resource Usage

**CPU usage:**

```bash
top -p $(pidof haproxy | tr ' ' ',')
```

**Memory usage:**

```bash
ps aux | grep haproxy | grep -v grep
```

**File descriptor usage:**

```bash
lsof -u haproxy | wc -l
cat /proc/$(pidof haproxy | awk '{print $1}')/fd | wc -l
```

**System-wide file descriptor usage:**

```bash
cat /proc/sys/fs/file-nr
```

Format: `<allocated> <unused> <maximum>`

### Step 10.11: Monitor Logs for Errors

**Watch HAProxy logs in real-time:**

```bash
journalctl -u haproxy -f
```

**Or:**

```bash
tail -f /var/log/haproxy/haproxy.log
```

**Look for:**
- No ERROR messages
- Backend health check successes
- Normal connection/disconnection messages

### Step 10.12: Test Application Functionality

**Perform end-to-end application testing:**

1. Log into your application through the load balancer
2. Perform typical user workflows
3. Verify all features work correctly
4. Test with different browsers/clients
5. Verify static and dynamic content loads properly

### Step 10.13: Load Testing (Optional but Recommended)

**Using Apache Bench (ab):**

```bash
dnf install httpd-tools -y
ab -n 1000 -c 100 http://haproxy-server-ip/
```

**Using wrk:**

```bash
dnf install wrk -y
wrk -t12 -c400 -d30s http://haproxy-server-ip/
```

**Monitor during load test:**

```bash
# Terminal 1: Watch resource usage
watch -n 1 'ps aux | grep haproxy | grep -v grep'

# Terminal 2: Watch file descriptors
watch -n 1 'lsof -u haproxy | wc -l'

# Terminal 3: Watch connections
watch -n 1 'ss -s'
```

**Verify:**
- No connection errors
- File descriptor usage stays well below limit
- Response times remain acceptable
- No errors in logs

### Step 10.14: Create Verification Checklist

Document all verification results:

```bash
vi /root/haproxy-migration-verification.txt
```

**Content:**

```
HAProxy Migration Verification Report
Date: YYYY-MM-DD
Performed by: Your Name

1. Service Status: PASS/FAIL
2. System Limits Applied: PASS/FAIL
3. Kernel Parameters: PASS/FAIL
4. HTTP Connectivity: PASS/FAIL
5. HTTPS Connectivity: PASS/FAIL
6. SSL Certificate Valid: PASS/FAIL
7. Backend Health Checks: PASS/FAIL
8. Load Balancing: PASS/FAIL
9. SELinux: PASS/FAIL
10. Firewall: PASS/FAIL
11. Logs Clean: PASS/FAIL
12. Application Testing: PASS/FAIL
13. Load Testing: PASS/FAIL

Notes:
(Add any observations or issues encountered)

Overall Status: PASS/FAIL
```

---

## Phase 11: Performance Tuning

### Step 11.1: Review Current Performance Baseline

**Collect baseline metrics:**

```bash
echo "show info" | socat stdio /var/lib/haproxy/stats | grep -E 'Curr|Max|Rate'
```

**Note current values for:**
- Current connections
- Current SSL connections
- Maximum observed connections
- Connection rate

### Step 11.2: Tune HAProxy maxconn Based on Testing

**Calculate optimal maxconn:**

```
Formula: maxconn = (LimitNOFILE - buffer) / 2
Example: (100000 - 10000) / 2 = 45000

Buffer accounts for:
- Backend connections
- File descriptors for logs
- Stats socket
- Other overhead
```

**Edit configuration:**

```bash
vi /etc/haproxy/haproxy.cfg
```

**Update global maxconn:**

```
global
    maxconn 45000
```

**Update frontend maxconn if needed:**

```
frontend main
    maxconn 45000
```

**Reload configuration:**

```bash
systemctl reload haproxy
```

### Step 11.3: Optimize Timeout Values

**Review current timeouts:**

```bash
grep timeout /etc/haproxy/haproxy.cfg
```

**Recommended baseline timeouts:**

```
defaults
    timeout connect 5s
    timeout client 50s
    timeout server 50s
    timeout http-request 10s
    timeout http-keep-alive 2s
    timeout queue 30s
```

**Adjust based on your application:**

- Long-polling applications: Increase `timeout client` and `timeout server`
- API endpoints: Can reduce timeouts for faster failure detection
- File uploads: May need longer `timeout client`

### Step 11.4: Optimize Backend Configuration

**Review backend configuration:**

```bash
grep -A 20 "backend" /etc/haproxy/haproxy.cfg
```

**Recommended optimizations:**

```
backend app_servers
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    
    # Connection reuse
    option http-server-close
    
    # Health check frequency
    default-server inter 3s fall 3 rise 2
    
    server app1 192.168.1.10:8080 check maxconn 1000
    server app2 192.168.1.11:8080 check maxconn 1000
```

**Explanation:**
- `inter 3s`: Health check every 3 seconds
- `fall 3`: Mark down after 3 failed checks
- `rise 2`: Mark up after 2 successful checks
- `maxconn 1000`: Limit connections per backend server

### Step 11.5: Enable Connection Reuse

**Add to backend configuration:**

```
option http-server-close
```

**Or for HTTP/1.1 keep-alive:**

```
option http-keep-alive
```

**Benefits:**
- Reduces connection overhead
- Improves performance
- Reduces file descriptor usage

### Step 11.6: Optimize SSL/TLS Performance

**Enable SSL session cache:**

```
global
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets
    
    # SSL session cache
    tune.ssl.cachesize 100000
    tune.ssl.lifetime 300
```

**Enable OCSP stapling:**

```
bind *:443 ssl crt /etc/haproxy/certs/ ssl-min-ver TLSv1.2 alpn h2,http/1.1
```

### Step 11.7: Optimize Thread Configuration

**Check current thread count:**

```bash
echo "show info" | socat stdio /var/lib/haproxy/stats | grep thread
```

**Set threads based on CPU cores:**

```
global
    nbthread 12
```

**General rule:**
- Use number of CPU cores for `nbthread`
- For 12 vCPU system: `nbthread 12`
- Don't exceed physical CPU count

**Reload configuration:**

```bash
systemctl reload haproxy
```

### Step 11.8: Enable HTTP/2

**If using HTTPS, enable HTTP/2:**

```
bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1
```

**Verify HTTP/2 is working:**

```bash
curl -I --http2 https://your-domain.com
```

Look for: `HTTP/2 200`

### Step 11.9: Configure Rate Limiting (if needed)

**Protect against abuse:**

```
frontend main
    # Track clients by IP
    stick-table type ip size 100k expire 30s store conn_rate(3s)
    
    # Allow 10 connections per 3 seconds
    tcp-request connection track-sc0 src
    tcp-request connection reject if { sc_conn_rate(0) gt 10 }
```

### Step 11.10: Validate All Changes

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl reload haproxy
```

### Step 11.11: Monitor Performance After Tuning

**Run load test again:**

```bash
wrk -t12 -c400 -d30s http://haproxy-server-ip/
```

**Compare with pre-tuning results:**
- Requests per second
- Latency
- Error rate
- Resource utilization

**Monitor for 24 hours:**

```bash
# Create monitoring script
vi /root/monitor-haproxy.sh
```

**Content:**

```bash
#!/bin/bash
while true; do
    echo "=== $(date) ==="
    echo "Connections:"
    echo "show info" | socat stdio /var/lib/haproxy/stats | grep -E 'Curr|Max'
    echo "File Descriptors:"
    lsof -u haproxy | wc -l
    echo "CPU/Memory:"
    ps aux | grep haproxy | grep -v grep
    echo "---"
    sleep 300  # Every 5 minutes
done
```

```bash
chmod +x /root/monitor-haproxy.sh
nohup /root/monitor-haproxy.sh > /var/log/haproxy-monitor.log 2>&1 &
```

---

## Phase 12: Production Cutover

### Step 12.1: Pre-Cutover Checklist

Verify all items are complete:

- HAProxy service is running and stable
- All tests pass (connectivity, SSL, load balancing)
- System limits are properly configured
- Kernel parameters are applied
- Firewall rules are correct
- SELinux is not blocking operations
- Backend health checks show all servers UP
- Logs show no errors
- Performance testing completed
- Monitoring is in place
- Rollback procedure is documented and tested

### Step 12.2: Schedule Maintenance Window

**Coordinate with stakeholders:**

- Announce maintenance window
- Prepare communication templates
- Have support team on standby
- Document emergency contacts

### Step 12.3: Pre-Cutover Backup

**On new Oracle Linux/RHEL server:**

```bash
tar -czf /root/pre-cutover-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
    /etc/haproxy/ \
    /etc/systemd/system/haproxy.service.d/ \
    /etc/security/limits.d/haproxy_limits.conf \
    /etc/sysctl.d/99-haproxy*.conf
```

**Verify HAProxy configuration one final time:**

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
```

### Step 12.4: DNS/Load Balancer Update

**Option A: DNS Update**

If using DNS for traffic direction:

1. Lower TTL on DNS records several hours before cutover (e.g., 300 seconds)
2. Update A/AAAA records to point to new HAProxy server
3. Wait for DNS propagation
4. Monitor traffic shifting to new server

**Option B: Floating IP/VIP Migration**

If using virtual IP:

1. On CentOS 7 server: Remove virtual IP

```bash
ip addr del <VIP>/32 dev <interface>
```

2. On Oracle Linux/RHEL server: Add virtual IP

```bash
ip addr add <VIP>/32 dev <interface>
```

3. Send gratuitous ARP:

```bash
arping -c 3 -A -I <interface> <VIP>
```

**Option C: Load Balancer Configuration Update**

If behind another load balancer:

1. Add new HAProxy server to upstream load balancer
2. Gradually shift traffic (e.g., 10%, 25%, 50%, 100%)
3. Monitor for issues at each stage

### Step 12.5: Traffic Validation

**Monitor new server receives traffic:**

```bash
watch -n 1 'echo "show stat" | socat stdio /var/lib/haproxy/stats | grep -E "rate|scur"'
```

**Monitor logs:**

```bash
journalctl -u haproxy -f
```

**Check connection counts:**

```bash
watch -n 1 'ss -s'
```

### Step 12.6: Verify Application Functionality

**Perform smoke tests:**

1. Access application through load balancer
2. Test key user workflows
3. Verify all pages load correctly
4. Check no JavaScript errors
5. Verify API endpoints respond correctly

**Use curl to test:**

```bash
curl -I http://your-domain.com
curl -I https://your-domain.com
```

### Step 12.7: Monitor for Issues

**Watch for first 30 minutes:**

- Connection errors
- Backend server failures
- High response times
- SSL/TLS errors
- File descriptor exhaustion
- Memory or CPU issues

**Check metrics:**

```bash
# Every 5 minutes for first hour
echo "show info" | socat stdio /var/lib/haproxy/stats
echo "show stat" | socat stdio /var/lib/haproxy/stats | grep DOWN
```

### Step 12.8: Gradual Load Increase (if applicable)

**If using gradual cutover:**

1. Start with 10% traffic
2. Monitor for 15 minutes
3. Increase to 25% traffic
4. Monitor for 15 minutes
5. Increase to 50% traffic
6. Monitor for 30 minutes
7. Increase to 100% traffic

**At each stage, verify:**
- No errors in logs
- Response times acceptable
- Backend health checks passing
- Resource usage within limits

### Step 12.9: Keep Old Server Running

**Do not decommission CentOS 7 server yet:**

- Keep it running for 48-72 hours
- Monitor new server stability
- Be ready to rollback if needed
- Use for comparison if issues arise

### Step 12.10: Document Cutover

**Create cutover report:**

```bash
vi /root/haproxy-cutover-report.txt
```

**Content:**

```
HAProxy Production Cutover Report

Date: YYYY-MM-DD HH:MM
Duration: X minutes

Cutover Method: [DNS/VIP/Load Balancer]

Pre-Cutover Status:
- All tests: PASS
- System ready: YES
- Backups completed: YES

Cutover Steps:
1. Time HH:MM - DNS updated / VIP migrated
2. Time HH:MM - Traffic observed on new server
3. Time HH:MM - Smoke tests completed
4. Time HH:MM - 100% traffic on new server

Issues Encountered: NONE / [List issues]

Resolution: N/A / [How issues were resolved]

Post-Cutover Verification:
- Application functionality: PASS
- Backend health: PASS
- Logs: CLEAN
- Performance: ACCEPTABLE

Status: SUCCESS / ROLLBACK INITIATED

Notes:
[Additional observations]

Sign-off: [Name]
```

---

## Troubleshooting Guide

### Issue: HAProxy Service Fails to Start

**Symptoms:**

```bash
systemctl status haproxy
# Shows: failed (Result: exit-code)
```

**Diagnosis:**

```bash
journalctl -xeu haproxy
```

**Common Causes and Solutions:**

**1. Configuration syntax error**

```
Solution:
haproxy -c -f /etc/haproxy/haproxy.cfg
Fix the reported error
systemctl start haproxy
```

**2. Port already in use**

```
Diagnosis:
ss -tulpn | grep ':80\|:443'

Solution:
Stop conflicting service or change HAProxy port
systemctl start haproxy
```

**3. Certificate file not found**

```
Diagnosis:
Check error message for missing file path

Solution:
ls -la /etc/haproxy/certs/
Copy missing certificate files
systemctl start haproxy
```

**4. Insufficient permissions**

```
Diagnosis:
ls -lZ /etc/haproxy/haproxy.cfg

Solution:
chown root:root /etc/haproxy/haproxy.cfg
chmod 644 /etc/haproxy/haproxy.cfg
restorecon -v /etc/haproxy/haproxy.cfg
systemctl start haproxy
```

### Issue: Backend Servers Show as DOWN

**Symptoms:**

```bash
echo "show stat" | socat stdio /var/lib/haproxy/stats | grep DOWN
```

**Diagnosis:**

**1. Check backend server is actually running**

```bash
curl http://backend-server-ip:port/
```

**2. Check network connectivity**

```bash
ping backend-server-ip
telnet backend-server-ip port
```

**3. Check health check configuration**

```bash
grep -A 5 "backend" /etc/haproxy/haproxy.cfg | grep httpchk
```

**Solutions:**

**1. Backend server not responding**

```
Start the backend application
Verify it's listening on the correct port
```

**2. Firewall blocking connection**

```
On backend server:
firewall-cmd --add-port=8080/tcp --permanent
firewall-cmd --reload
```

**3. Incorrect health check path**

```
Edit /etc/haproxy/haproxy.cfg
Update health check path to valid endpoint
systemctl reload haproxy
```

**4. Health check too aggressive**

```
backend app_servers
    default-server inter 5s fall 5 rise 2
```

### Issue: SSL/TLS Connection Errors

**Symptoms:**

```
curl: (35) error:1408F10B:SSL routines:ssl3_get_record:wrong version number
```

**Diagnosis:**

```bash
openssl s_client -connect haproxy-server-ip:443 -servername your-domain.com
```

**Common Causes and Solutions:**

**1. Certificate file missing or incorrect**

```
Diagnosis:
ls -la /etc/haproxy/certs/

Solution:
Copy correct certificate file
Ensure it contains: certificate + intermediate certs + private key
chmod 600 /etc/haproxy/certs/*.pem
systemctl reload haproxy
```

**2. Certificate and key mismatch**

```
Diagnosis:
openssl x509 -noout -modulus -in certificate.crt | openssl md5
openssl rsa -noout -modulus -in private.key | openssl md5
# Hashes should match

Solution:
Use matching certificate and key pair
```

**3. Cipher suite incompatibility**

```
Solution:
Add broader cipher support in haproxy.cfg:
ssl-default-bind-ciphers HIGH:!aNULL:!MD5
systemctl reload haproxy
```

**4. Missing intermediate certificates**

```
Diagnosis:
openssl s_client -connect haproxy-server-ip:443 -showcerts

Solution:
Obtain intermediate certificates from CA
Concatenate in order: server cert + intermediate certs + private key
```

### Issue: File Descriptor Exhaustion

**Symptoms:**

```
Log messages: "Cannot allocate memory" or "Too many open files"
```

**Diagnosis:**

```bash
cat /proc/$(pidof haproxy | awk '{print $1}')/limits | grep "Max open files"
lsof -u haproxy | wc -l
```

**Solutions:**

**1. Verify systemd limits are applied**

```bash
systemctl show haproxy | grep LimitNOFILE
# Should show: LimitNOFILE=100000
```

**2. If limits not applied, recreate override:**

```bash
vi /etc/systemd/system/haproxy.service.d/limits.conf
# Add LimitNOFILE=100000
systemctl daemon-reload
systemctl restart haproxy
```

**3. Reduce maxconn if limits are too low:**

```bash
vi /etc/haproxy/haproxy.cfg
# Reduce global maxconn
systemctl reload haproxy
```

**4. Check kernel limit:**

```bash
sysctl fs.file-max
# If too low:
echo "fs.file-max = 500000" >> /etc/sysctl.d/99-haproxy-fd.conf
sysctl -p /etc/sysctl.d/99-haproxy-fd.conf
```

### Issue: SELinux Denials

**Symptoms:**

```
Service fails to start or cannot access resources
```

**Diagnosis:**

```bash
ausearch -m avc -ts recent | grep haproxy
journalctl -t setroubleshoot
```

**Solutions:**

**1. Check and enable HAProxy boolean:**

```bash
getsebool -a | grep haproxy
setsebool -P haproxy_connect_any 1
```

**2. Restore file contexts:**

```bash
restorecon -Rv /etc/haproxy/
restorecon -Rv /var/lib/haproxy/
```

**3. If still blocked, analyze and create policy:**

```bash
ausearch -m avc -ts recent | grep haproxy | audit2allow -M haproxy_custom
semodule -i haproxy_custom.pp
```

**4. Temporary workaround (not recommended for production):**

```bash
setenforce 0
# Test if issue is SELinux-related
# If yes, fix policy properly
setenforce 1
```

### Issue: High CPU Usage

**Symptoms:**

```bash
top
# HAProxy consuming >80% CPU
```

**Diagnosis:**

```bash
echo "show info" | socat stdio /var/lib/haproxy/stats | grep -i cpu
echo "show stat" | socat stdio /var/lib/haproxy/stats
```

**Solutions:**

**1. Too many threads for CPU cores:**

```bash
vi /etc/haproxy/haproxy.cfg
# Reduce nbthread to match CPU cores
global
    nbthread 12
systemctl reload haproxy
```

**2. Inefficient ACLs or rules:**

```
Review complex ACLs in configuration
Simplify or optimize rules
Use stick tables more efficiently
```

**3. SSL overhead too high:**

```
Enable SSL session cache:
tune.ssl.cachesize 100000
tune.ssl.lifetime 300

Consider SSL offloading to dedicated hardware
```

**4. Too many connections:**

```
Reduce maxconn
Implement rate limiting
Add more HAProxy servers and load balance between them
```

### Issue: Inconsistent Load Balancing

**Symptoms:**

One backend server receives more traffic than others

**Diagnosis:**

```bash
echo "show stat" | socat stdio /var/lib/haproxy/stats | grep -E "server|scur|rate"
```

**Solutions:**

**1. Check balance algorithm:**

```bash
grep "balance" /etc/haproxy/haproxy.cfg

Change to:
balance roundrobin  # Equal distribution
balance leastconn   # Connection-based
balance source      # Session persistence
```

**2. Check server weights:**

```
backend app_servers
    server app1 192.168.1.10:8080 weight 100
    server app2 192.168.1.11:8080 weight 100
    # Ensure weights are equal
```

**3. Check maxconn per server:**

```
server app1 192.168.1.10:8080 maxconn 1000
server app2 192.168.1.11:8080 maxconn 1000
# Ensure maxconn is equal
```

**4. Verify all servers are UP:**

```bash
echo "show stat" | socat stdio /var/lib/haproxy/stats | grep -v UP
```

### Issue: Slow Response Times

**Symptoms:**

High latency observed through HAProxy

**Diagnosis:**

```bash
echo "show stat" | socat stdio /var/lib/haproxy/stats | grep -E "qtime|ctime|rtime"
```

**Solutions:**

**1. Check backend server performance:**

```bash
# Bypass HAProxy and test backend directly
curl -w "@curl-format.txt" -o /dev/null -s http://backend-server-ip/
```

**2. Optimize timeouts:**

```
defaults
    timeout connect 5s
    timeout client 50s
    timeout server 50s
    timeout queue 5s  # Don't queue for too long
```

**3. Enable connection reuse:**

```
option http-server-close
or
option http-keep-alive
```

**4. Check queue depth:**

```bash
echo "show stat" | socat stdio /var/lib/haproxy/stats | grep qcur
# High queue depth indicates backend saturation
# Solution: Add more backend servers
```

**5. Optimize SSL:**

```
Enable session cache
Use faster cipher suites
Consider ECDSA certificates (smaller, faster)
```

### Issue: Memory Leaks

**Symptoms:**

HAProxy memory usage grows over time

**Diagnosis:**

```bash
ps aux | grep haproxy
# Monitor over several hours/days
```

**Solutions:**

**1. Update to latest HAProxy version:**

```bash
dnf update haproxy
systemctl restart haproxy
```

**2. Review stick table configuration:**

```
Ensure stick tables have expire times:
stick-table type ip size 100k expire 30s

Don't make stick tables too large
```

**3. Check for configuration that causes memory growth:**

```
Review custom ACLs
Check log format complexity
Review map files size
```

**4. Set memory limit if needed:**

```bash
vi /etc/systemd/system/haproxy.service.d/limits.conf
[Service]
MemoryLimit=4G
systemctl daemon-reload
systemctl restart haproxy
```

---

## Rollback Procedure

### When to Rollback

**Rollback should be initiated if:**

- HAProxy service cannot be stabilized within 30 minutes
- Critical backend servers cannot be reached
- SSL/TLS errors affecting all users
- File descriptor exhaustion cannot be resolved
- Performance is significantly degraded compared to old system
- Data corruption or loss detected
- Security vulnerability exposed

### Rollback Decision Matrix

**Severity Level 1 (Minor):** Single backend server down, partial SSL errors
- **Action:** Troubleshoot on new server, keep in production
- **Time to fix:** 1-2 hours

**Severity Level 2 (Moderate):** Multiple backend servers flapping, intermittent errors
- **Action:** Attempt quick fix (15 minutes), otherwise rollback
- **Time to fix:** 15-30 minutes

**Severity Level 3 (Critical):** Service completely down, all traffic affected
- **Action:** Immediate rollback
- **Time to fix:** Immediate (5 minutes)

### Pre-Rollback Checklist

- Notify stakeholders of rollback decision
- Document issues encountered
- Take snapshot/backup of new server state for post-mortem
- Ensure old CentOS 7 server is still running
- Verify old server configuration hasn't changed
- Confirm rollback authority from change manager

### Rollback Steps

**Step 1: Document Current State**

```bash
# On Oracle Linux/RHEL server
mkdir -p /root/rollback-evidence
journalctl -u haproxy -n 1000 > /root/rollback-evidence/haproxy-logs.txt
echo "show stat" | socat stdio /var/lib/haproxy/stats > /root/rollback-evidence/haproxy-stats.txt
ps aux > /root/rollback-evidence/process-list.txt
ss -s > /root/rollback-evidence/socket-summary.txt
tar -czf /root/rollback-evidence-$(date +%Y%m%d-%H%M%S).tar.gz /root/rollback-evidence/
```

**Step 2: Verify CentOS 7 Server is Ready**

```bash
# On CentOS 7 server
systemctl status haproxy
# Ensure service is running

haproxy -c -f /etc/haproxy/haproxy.cfg
# Ensure configuration is still valid

ss -tulpn | grep haproxy
# Verify ports are listening
```

**Step 3: Traffic Redirection**

**Option A: DNS Rollback**

```
1. Update DNS A/AAAA records back to CentOS 7 IP
2. Wait for propagation (TTL dependent)
3. Monitor traffic returning to old server
```

**Option B: VIP Migration**

```bash
# On Oracle Linux/RHEL server
ip addr del <VIP>/32 dev <interface>

# On CentOS 7 server
ip addr add <VIP>/32 dev <interface>
arping -c 3 -A -I <interface> <VIP>
```

**Option C: Load Balancer Configuration**

```
1. Update upstream load balancer
2. Point traffic back to CentOS 7 server
3. Remove Oracle Linux/RHEL server from pool
```

**Step 4: Verify Rollback Success**

```bash
# Verify traffic on CentOS 7 server
ss -s
netstat -an | grep ESTABLISHED | wc -l

# Check logs
tail -f /var/log/haproxy/haproxy.log

# Test connectivity
curl -I http://your-domain.com
curl -I https://your-domain.com
```

**Step 5: Monitor for Stability**

```
Monitor for 30 minutes:
- Connection counts
- Backend health
- Error rates
- Response times
- Resource usage
```

**Step 6: Communication**

```
Notify stakeholders:
- Rollback completed at HH:MM
- Service restored to previous state
- Investigation of issues in progress
- Timeline for next migration attempt
```

**Step 7: Post-Rollback Actions**

**On Oracle Linux/RHEL server:**

```bash
# Stop HAProxy to prevent confusion
systemctl stop haproxy
systemctl disable haproxy

# Leave server running for analysis
# Do not delete - needed for troubleshooting
```

**Create post-mortem document:**

```bash
vi /root/migration-postmortem.txt
```

**Content:**

```
HAProxy Migration Rollback Post-Mortem

Date: YYYY-MM-DD
Rollback Time: HH:MM
Duration in Production: X hours

Issues Encountered:
1. [Describe issue 1]
2. [Describe issue 2]

Root Causes:
1. [Root cause analysis]

Why Rollback Was Necessary:
[Explanation]

What Worked:
- [List successful elements]

What Didn't Work:
- [List failures]

Corrective Actions:
1. [Action item 1] - Owner: [Name] - Due: [Date]
2. [Action item 2] - Owner: [Name] - Due: [Date]

Recommendations for Next Attempt:
1. [Recommendation 1]
2. [Recommendation 2]

Timeline for Next Migration:
[Proposed date and preparation plan]

Lessons Learned:
- [Lesson 1]
- [Lesson 2]
```

### Post-Rollback Analysis

**1. Log Analysis**

```bash
# On Oracle Linux/RHEL server
grep -i error /var/log/haproxy/* | sort | uniq -c | sort -rn
journalctl -u haproxy | grep -i error
ausearch -m avc -ts today | grep haproxy
```

**2. Configuration Review**

```bash
diff /tmp/haproxy-migration-backup/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg
```

**3. Performance Comparison**

Compare metrics between old and new servers to identify bottlenecks

**4. Root Cause Identification**

Identify the primary cause of failure and develop remediation plan

**5. Updated Migration Plan**

Create improved migration plan addressing identified issues

---

## Appendix

### A. HAProxy Configuration Compatibility Matrix

**HAProxy 2.3 to 2.8+/3.0 Changes:**

**Compatible without changes:**
- Basic frontend/backend configuration
- Most timeout settings
- Standard ACLs
- Health check configuration
- Basic load balancing algorithms

**May require updates:**
- SSL cipher suites (OpenSSL 3.x compatibility)
- Some deprecated keywords
- Advanced stick-table configurations
- Certain lua scripts (API changes)

**New features available:**
- Improved HTTP/2 support
- Native HTTP/3 support (HAProxy 3.0+)
- Enhanced observability options
- Better performance metrics
- Improved threading model

### B. System Limits Reference

**Recommended Limits for HAProxy:**

```
User Limits (/etc/security/limits.d/haproxy_limits.conf):
- haproxy: nofile 100000, nproc 10000
- root: nofile 100000, nproc 10000

Systemd Limits (/etc/systemd/system/haproxy.service.d/limits.conf):
- LimitNOFILE=100000
- LimitNPROC=9000

Kernel Limits (/etc/sysctl.d/):
- fs.file-max = 500000
- net.core.somaxconn = 4096
- net.ipv4.tcp_max_syn_backlog = 8192
```

**Calculation Reference:**

```
maxconn calculation:
maxconn = (LimitNOFILE - overhead) / 2
Example: (100000 - 10000) / 2 = 45000

Overhead includes:
- Backend connections
- Log file descriptors
- Stats socket
- Configuration files
- System overhead
```

### C. Useful HAProxy Commands

**Service Management:**

```bash
systemctl start haproxy
systemctl stop haproxy
systemctl restart haproxy
systemctl reload haproxy  # Graceful reload, no connection loss
systemctl status haproxy
systemctl enable haproxy
systemctl disable haproxy
```

**Configuration Validation:**

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
haproxy -vv  # Show version and build options
```

**Stats Socket Commands:**

```bash
echo "show info" | socat stdio /var/lib/haproxy/stats
echo "show stat" | socat stdio /var/lib/haproxy/stats
echo "show errors" | socat stdio /var/lib/haproxy/stats
echo "show pools" | socat stdio /var/lib/haproxy/stats
echo "show sess" | socat stdio /var/lib/haproxy/stats
echo "disable server backend/server1" | socat stdio /var/lib/haproxy/stats
echo "enable server backend/server1" | socat stdio /var/lib/haproxy/stats
echo "set server backend/server1 weight 50" | socat stdio /var/lib/haproxy/stats
```

**Debugging:**

```bash
journalctl -u haproxy -f  # Follow logs
journalctl -u haproxy -n 100  # Last 100 lines
journalctl -u haproxy --since "10 minutes ago"
journalctl -u haproxy --until "2024-01-01 12:00:00"
```

### D. Monitoring Commands

**Resource Usage:**

```bash
# CPU and memory
top -p $(pidof haproxy | tr ' ' ',')
ps aux | grep haproxy

# File descriptors
lsof -u haproxy | wc -l
cat /proc/$(pidof haproxy | awk '{print $1}')/fd | wc -l
cat /proc/sys/fs/file-nr

# Network connections
ss -s
ss -tulpn | grep haproxy
netstat -an | grep ESTABLISHED | wc -l
```

**HAProxy Metrics:**

```bash
# Connection stats
echo "show info" | socat stdio /var/lib/haproxy/stats | grep -E 'Curr|Max|Rate'

# Backend status
echo "show stat" | socat stdio /var/lib/haproxy/stats | column -t -s ','

# Error counts
echo "show errors" | socat stdio /var/lib/haproxy/stats
```

### E. Common File Locations

**Oracle Linux/RHEL 9/10:**

```
Configuration:
/etc/haproxy/haproxy.cfg - Main configuration file
/etc/haproxy/conf.d/ - Additional configuration files (if using)

Service:
/usr/lib/systemd/system/haproxy.service - Service unit file (don't modify)
/etc/systemd/system/haproxy.service.d/ - Override directory (modify here)

Runtime:
/var/lib/haproxy/ - Runtime files and stats socket
/run/haproxy.pid - PID file

Logs:
/var/log/haproxy/ - Log directory (if configured)
journalctl -u haproxy - Systemd journal

Certificates:
/etc/haproxy/certs/ - SSL/TLS certificates (common location)
/etc/pki/tls/ - System certificate location

Documentation:
/usr/share/doc/haproxy/ - Documentation and examples
```

### F. Performance Tuning Quick Reference

**Global Section:**

```
global
    maxconn 45000  # Based on LimitNOFILE calculation
    nbthread 12  # Match CPU core count
    tune.ssl.cachesize 100000  # SSL session cache
    tune.ssl.lifetime 300  # SSL cache lifetime
    tune.ssl.default-dh-param 2048  # DH parameter size
```

**Timeout Recommendations:**

```
defaults
    timeout connect 5s  # Backend connection
    timeout client 50s  # Client inactivity
    timeout server 50s  # Server inactivity
    timeout http-request 10s  # HTTP request completion
    timeout http-keep-alive 2s  # Keep-alive timeout
    timeout queue 30s  # Queue timeout
```

**Backend Optimization:**

```
backend app_servers
    balance roundrobin
    option httpchk GET /health
    option http-server-close  # Connection reuse
    default-server inter 3s fall 3 rise 2  # Health check timing
```

### G. Migration Timeline Template

**Week 1: Planning and Preparation**
- Day 1-2: Review documentation, plan migration
- Day 3-4: Build Oracle Linux/RHEL server
- Day 5: Complete pre-migration documentation

**Week 2: Configuration and Testing**
- Day 1: Configure system limits and kernel parameters
- Day 2: Migrate HAProxy configuration
- Day 3: SSL/TLS and SELinux configuration
- Day 4: Testing and validation
- Day 5: Performance tuning

**Week 3: Production Readiness**
- Day 1-2: Load testing and final adjustments
- Day 3: Rollback procedure testing
- Day 4: Documentation review
- Day 5: Go/No-Go decision

**Week 4: Cutover and Monitoring**
- Day 1: Production cutover
- Day 2-7: Intensive monitoring
- Post-cutover: 48-72 hour observation period

### H. Checklist Template

**Pre-Migration Checklist:**

- Documentation completed
- Backup created and verified
- New server built and patched
- System limits configured
- Kernel parameters set
- HAProxy installed
- Configuration migrated
- SSL certificates copied
- SELinux configured
- Firewall rules set
- Testing completed
- Rollback procedure documented
- Stakeholders notified
- Maintenance window scheduled

**Cutover Checklist:**

- All pre-migration items complete
- Backup taken immediately before cutover
- Support team on standby
- Monitoring tools ready
- Communication templates prepared
- Rollback procedure ready
- Configuration validated one final time

**Post-Cutover Checklist:**

- Service status verified
- All backends UP
- Traffic flowing correctly
- No errors in logs
- SSL/TLS working
- Application functionality verified
- Performance acceptable
- Monitoring shows healthy metrics
- No SELinux denials
- Stakeholders notified of success

### I. Contact Information Template

```
Migration Team Contacts:

Project Lead: [Name] - [Phone] - [Email]
System Administrator: [Name] - [Phone] - [Email]
Network Engineer: [Name] - [Phone] - [Email]
Security Team: [Name] - [Phone] - [Email]
Application Team: [Name] - [Phone] - [Email]

Escalation Path:
Level 1: [Name/Team]
Level 2: [Name/Team]
Level 3: [Name/Team]

Vendor Support:
Oracle Support: [Contact info]
Red Hat Support: [Contact info]

Emergency Contacts:
After Hours: [Phone]
Emergency Email: [Email]
```

### J. Additional Resources

**Official Documentation:**

- HAProxy Documentation: https://docs.haproxy.org/
- Oracle Linux Documentation: https://docs.oracle.com/en/operating-systems/oracle-linux/
- Red Hat Documentation: https://access.redhat.com/documentation/
- SELinux Project: https://selinuxproject.org/

**HAProxy Configuration:**

- HAProxy Configuration Manual: https://www.haproxy.com/documentation/
- HAProxy Blog: https://www.haproxy.com/blog/
- HAProxy Community: https://discourse.haproxy.org/

**Tools:**

- HAProxy Stats: Built-in stats page
- HATop: Terminal-based HAProxy monitoring tool
- Prometheus HAProxy Exporter: For metrics collection
- Grafana: For metrics visualization

**Security:**

- SSL Labs: https://www.ssllabs.com/
- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
- Let's Encrypt: https://letsencrypt.org/

---
