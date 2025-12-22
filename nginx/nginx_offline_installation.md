# NGINX 1.28 Offline Installation Guide for RHEL 9.6

This comprehensive guide explains how to install the latest stable NGINX Open Source (version 1.28) on a **RHEL 9.6 production server without internet access**. The process uses a second **online RHEL 9.6 server** to download all necessary packages and dependencies.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Diagram](#architecture-diagram)
4. [Part A: Online Server Setup](#part-a-online-server-setup)
5. [Part B: Offline Server Installation](#part-b-offline-server-installation)
6. [Part C: Optional Local Repository Setup](#part-c-optional-local-repository-setup)
7. [Post-Installation Configuration](#post-installation-configuration)
8. [Verification and Testing](#verification-and-testing)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance and Updates](#maintenance-and-updates)

---

## Overview

### Why Offline Installation?

Production environments often have restricted or no internet access due to:
- Security policies
- Air-gapped networks
- DMZ configurations
- Compliance requirements
- Network isolation

### What This Guide Covers

- Downloading NGINX 1.28 and all dependencies from an online server
- Packaging RPMs for transfer
- Installing on an offline server without repository access
- Creating an optional local repository for easier management

### Why NGINX 1.28 from nginx.org?

The official NGINX repository provides the latest stable releases, whereas RHEL AppStream modules typically contain older versions. As of late 2024, nginx.org offers version 1.28.x while RHEL AppStream may only have 1.20 or 1.22.

---

## Prerequisites

### Online Server (Download Machine)
- RHEL 9.6 (same major version as offline server)
- Root or sudo privileges
- Internet connectivity
- Sufficient disk space (~50-100 MB)

### Offline Server (Production Machine)
- RHEL 9.6 (matching OS version)
- Root or sudo privileges
- No internet access required
- Sufficient disk space (~50-100 MB)

### Transfer Method
One of the following:
- SCP/SSH access between servers
- USB drive
- Shared network storage
- Physical media

### Important Version Matching

> ⚠️ **Critical:** Both servers must run the same RHEL version (9.6) to ensure RPM compatibility. Check version with:
```bash
cat /etc/redhat-release
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ONLINE RHEL 9.6 SERVER                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Add nginx.org repository                          │  │
│  │  2. Download NGINX 1.28 + all dependencies           │  │
│  │  3. Package RPMs into tarball                        │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Transfer tarball
                            │ (SCP/USB/Network)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   OFFLINE RHEL 9.6 SERVER                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Extract tarball                                   │  │
│  │  2. Install RPMs without repositories                │  │
│  │  3. Configure and start NGINX                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Part A: Online Server Setup

Perform these steps on the **online RHEL 9.6 server** that has internet access.

### Step 1: Create NGINX Stable Repository

Create the official NGINX repository configuration:

```bash
sudo cat > /etc/yum.repos.d/nginx.repo <<'EOF'
[nginx-stable]
name=NGINX Stable Repository
baseurl=https://nginx.org/packages/rhel/9/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF
```

**What this does:**
- Creates a repository file pointing to nginx.org official packages
- Enables GPG signature verification for security
- `module_hotfixes=true` prevents conflicts with RHEL AppStream modules
- Uses RHEL 9 packages optimized for your architecture

**Verify the repository file:**
```bash
cat /etc/yum.repos.d/nginx.repo
```

### Step 2: Clean Metadata and Verify Repository

```bash
# Clear all cached repository data
sudo dnf clean all

# Regenerate repository cache
sudo dnf makecache

# Verify NGINX repository is available
sudo dnf repolist | grep nginx
```

**Expected output:**
```
nginx-stable    NGINX Stable Repository
```

**Check available NGINX versions:**
```bash
sudo dnf list available nginx --showduplicates
```

**Expected output:**
```
Available Packages
nginx.x86_64    1.28.0-1.el9.ngx    nginx-stable
nginx.x86_64    1.28.1-1.el9.ngx    nginx-stable
```

### Step 3: Create Download Directory

```bash
# Create directory for storing downloaded RPMs
mkdir -p ~/nginx-offline
cd ~/nginx-offline
```

**What this does:**
- Creates a clean workspace for downloaded packages
- Keeps downloads organized and easy to package

### Step 4: Download NGINX and All Dependencies

```bash
# Download NGINX and all required dependencies
sudo dnf install --downloadonly --downloaddir=. nginx
```

**What this does:**
- `--downloadonly`: Downloads packages without installing them
- `--downloaddir=.`: Saves RPMs to current directory
- Downloads NGINX plus all dependencies (OpenSSL, PCRE, zlib, etc.)

**Verify downloaded packages:**
```bash
ls -lh
```

**Expected output (example):**
```
-rw-r--r--. 1 root root 1.2M nginx-1.28.0-1.el9.ngx.x86_64.rpm
-rw-r--r--. 1 root root  89K nginx-filesystem-1.28.0-1.el9.ngx.noarch.rpm
-rw-r--r--. 1 root root 512K openssl-libs-3.0.7-16.el9.x86_64.rpm
... (other dependencies)
```

**Count downloaded RPMs:**
```bash
ls -1 *.rpm | wc -l
```

Typically, you'll have 3-10 RPM files depending on what's already installed on your system.

### Step 5: Package RPMs into Tarball

```bash
# Create compressed archive of all RPMs
tar -czvf nginx-offline-rpms.tar.gz *.rpm

# Verify tarball was created
ls -lh nginx-offline-rpms.tar.gz
```

**What this does:**
- Creates a compressed archive containing all RPM files
- Makes transfer easier and faster
- Preserves file permissions

**Optional: Create checksum for verification:**
```bash
sha256sum nginx-offline-rpms.tar.gz > nginx-offline-rpms.sha256
cat nginx-offline-rpms.sha256
```

### Step 6: Transfer Tarball to Offline Server

Choose your transfer method based on your environment:

#### Method 1: SCP Transfer (Network Access)

```bash
# Transfer to offline server via SCP
scp nginx-offline-rpms.tar.gz root@prod-server:/tmp/

# Optional: Transfer checksum file
scp nginx-offline-rpms.sha256 root@prod-server:/tmp/
```

**Replace:** `prod-server` with your offline server's hostname or IP address.

#### Method 2: USB Drive Transfer

```bash
# Mount USB drive
sudo mount /dev/sdb1 /mnt/usb

# Copy tarball to USB
sudo cp nginx-offline-rpms.tar.gz /mnt/usb/

# Safely unmount
sudo umount /mnt/usb
```

Then physically move the USB drive to the offline server.

#### Method 3: Network Share Transfer

```bash
# Mount network share
sudo mount -t cifs //fileserver/share /mnt/share -o username=user

# Copy tarball
sudo cp nginx-offline-rpms.tar.gz /mnt/share/

# Unmount
sudo umount /mnt/share
```

---

## Part B: Offline Server Installation

Perform these steps on the **offline RHEL 9.6 production server**.

### Step 1: Verify Tarball Transfer

```bash
# Check if file exists
ls -lh /tmp/nginx-offline-rpms.tar.gz

# Optional: Verify checksum (if you transferred .sha256 file)
cd /tmp
sha256sum -c nginx-offline-rpms.sha256
```

**Expected output:**
```
nginx-offline-rpms.tar.gz: OK
```

### Step 2: Extract the Tarball

```bash
# Navigate to /tmp
cd /tmp

# Extract all RPMs
tar -xzvf nginx-offline-rpms.tar.gz

# Optional: Create dedicated directory
mkdir -p nginx-offline
tar -xzvf nginx-offline-rpms.tar.gz -C nginx-offline/
cd nginx-offline/
```

**Verify extraction:**
```bash
ls -lh *.rpm
```

### Step 3: Install RPMs Without Internet Repositories

```bash
# Install all RPMs using local files only
sudo dnf install *.rpm --disablerepo="*"
```

**What this does:**
- `--disablerepo="*"`: Disables all configured repositories
- Forces installation from local RPM files only
- Resolves dependencies from downloaded packages

**Expected output:**
```
Dependencies resolved.
================================================================================
 Package              Architecture  Version             Repository      Size
================================================================================
Installing:
 nginx                x86_64        1.28.0-1.el9.ngx    @commandline    1.2 M
Installing dependencies:
 nginx-filesystem     noarch        1.28.0-1.el9.ngx    @commandline     89 k

Transaction Summary
================================================================================
Install  2 Packages

Total size: 1.3 M
Installed size: 3.2 M
Is this ok [y/N]: y
```

**If you encounter dependency conflicts:**
```bash
sudo dnf install *.rpm --disablerepo="*" --allowerasing
```

**What `--allowerasing` does:**
- Allows DNF to remove conflicting packages
- Useful if older versions exist
- Use with caution in production

### Step 4: Enable and Start NGINX Service

```bash
# Enable NGINX to start on boot
sudo systemctl enable nginx

# Start NGINX service
sudo systemctl start nginx

# Check service status
sudo systemctl status nginx
```

**Expected output:**
```
● nginx.service - nginx - high performance web server
     Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled; preset: disabled)
     Active: active (running) since Mon 2024-12-23 10:00:00 UTC; 5s ago
       Docs: http://nginx.org/en/docs/
    Process: 12345 ExecStart=/usr/sbin/nginx -c /etc/nginx/nginx.conf (code=exited, status=0/SUCCESS)
   Main PID: 12346 (nginx)
      Tasks: 2 (limit: 23456)
     Memory: 2.5M
        CPU: 10ms
     CGroup: /system.slice/nginx.service
             ├─12346 "nginx: master process /usr/sbin/nginx -c /etc/nginx/nginx.conf"
             └─12347 "nginx: worker process"

Dec 23 10:00:00 prod-server systemd[1]: Starting nginx - high performance web server...
Dec 23 10:00:00 prod-server systemd[1]: Started nginx - high performance web server.
```

### Step 5: Verify NGINX Version

```bash
nginx -v
```

**Expected output:**
```
nginx version: nginx/1.28.0
```

**View full version info with compile options:**
```bash
nginx -V
```

---

## Part C: Optional Local Repository Setup

Creating a local repository on the offline server provides easier package management for future updates or reinstalls.

### Step 1: Install createrepo Tool

If `createrepo` is not already installed, you need to download it from the online server first.

**On the online server:**
```bash
cd ~/nginx-offline
sudo dnf install --downloadonly --downloaddir=. createrepo_c
tar -czvf createrepo-rpms.tar.gz createrepo*.rpm
scp createrepo-rpms.tar.gz prod-server:/tmp/
```

**On the offline server:**
```bash
cd /tmp
tar -xzvf createrepo-rpms.tar.gz
sudo dnf install createrepo*.rpm --disablerepo="*"
```

### Step 2: Create Repository Metadata

```bash
# Navigate to directory containing RPMs
cd /tmp/nginx-offline

# Create repository metadata
sudo createrepo .
```

**What this does:**
- Creates `repodata/` directory with repository metadata
- Allows DNF to treat this directory as a repository
- Enables dependency resolution

**Verify repository creation:**
```bash
ls -la repodata/
```

**Expected files:**
```
drwxr-xr-x. 2 root root  repodata
-rw-r--r--. 1 root root  repomd.xml
-rw-r--r--. 1 root root  primary.xml.gz
-rw-r--r--. 1 root root  filelists.xml.gz
-rw-r--r--. 1 root root  other.xml.gz
```

### Step 3: Create Local Repository Configuration

```bash
sudo tee /etc/yum.repos.d/local-nginx.repo > /dev/null <<'EOF'
[local-nginx]
name=Local NGINX Repository
baseurl=file:///tmp/nginx-offline
enabled=1
gpgcheck=0
EOF
```

**What this does:**
- Creates a repository configuration pointing to local directory
- `baseurl=file://` uses local filesystem
- `gpgcheck=0` disables signature checking (packages already verified)
- `enabled=1` makes repository active

### Step 4: Verify Local Repository

```bash
# Clear cache
sudo dnf clean all

# Regenerate cache
sudo dnf makecache

# List repositories
sudo dnf repolist
```

**Expected output:**
```
repo id                repo name
local-nginx            Local NGINX Repository
```

### Step 5: Test Installation from Local Repository

```bash
# List available packages
sudo dnf list available --repo=local-nginx

# Install NGINX from local repo (if not already installed)
sudo dnf install nginx --disablerepo="*" --enablerepo=local-nginx
```

### Step 6: Make Repository Permanent (Optional)

```bash
# Move RPMs to permanent location
sudo mkdir -p /opt/local-repos/nginx
sudo mv /tmp/nginx-offline/*.rpm /opt/local-repos/nginx/
sudo createrepo /opt/local-repos/nginx/

# Update repository configuration
sudo sed -i 's|file:///tmp/nginx-offline|file:///opt/local-repos/nginx|' /etc/yum.repos.d/local-nginx.repo

# Verify
sudo dnf repolist
```

---

## Post-Installation Configuration

### Configure Firewall

```bash
# Check firewall status
sudo firewall-cmd --state

# Allow HTTP traffic
sudo firewall-cmd --permanent --add-service=http

# Allow HTTPS traffic
sudo firewall-cmd --permanent --add-service=https

# Reload firewall
sudo firewall-cmd --reload

# Verify rules
sudo firewall-cmd --list-all
```

### Configure SELinux

```bash
# Check SELinux status
getenforce

# Set proper context for web content
sudo semanage fcontext -a -t httpd_sys_content_t "/usr/share/nginx/html(/.*)?"
sudo restorecon -Rv /usr/share/nginx/html

# Allow NGINX network connections (if needed)
sudo setsebool -P httpd_can_network_connect 1
```

### Create Test Page

```bash
# Create custom test page
sudo tee /usr/share/nginx/html/index.html > /dev/null <<'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>NGINX 1.28 - Offline Installation Success</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #009639; }
        .info { background: #e8f5e9; padding: 15px; border-radius: 4px; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✓ NGINX Successfully Installed</h1>
        <div class="info">
            <p><strong>Version:</strong> NGINX 1.28</p>
            <p><strong>Installation Type:</strong> Offline</p>
            <p><strong>OS:</strong> RHEL 9.6</p>
            <p><strong>Server:</strong> Production Environment</p>
        </div>
        <h2>Installation Details</h2>
        <p>This NGINX server was installed using offline RPM packages downloaded from <code>nginx.org</code> repository.</p>
        <h2>Next Steps</h2>
        <ul>
            <li>Configure virtual hosts</li>
            <li>Set up SSL/TLS certificates</li>
            <li>Configure reverse proxy or load balancing</li>
            <li>Implement security hardening</li>
        </ul>
    </div>
</body>
</html>
EOF

# Reload NGINX
sudo systemctl reload nginx
```

### Basic NGINX Configuration

```bash
# Test configuration syntax
sudo nginx -t

# View main configuration
sudo cat /etc/nginx/nginx.conf

# View default server configuration
sudo cat /etc/nginx/conf.d/default.conf
```

---

## Verification and Testing

### System-Level Verification

```bash
# Check NGINX version
nginx -v

# Verify NGINX is running
sudo systemctl is-active nginx

# Check if NGINX is enabled on boot
sudo systemctl is-enabled nginx

# View NGINX process
ps aux | grep nginx

# Check listening ports
sudo ss -tlnp | grep nginx
```

**Expected output for listening ports:**
```
LISTEN 0      511          0.0.0.0:80        0.0.0.0:*    users:(("nginx",pid=12346,fd=6))
LISTEN 0      511             [::]:80           [::]:*    users:(("nginx",pid=12346,fd=7))
```

### Local Testing

```bash
# Test from localhost
curl http://localhost

# Test with headers
curl -I http://localhost

# Test specific file
curl http://localhost/index.html
```

**Expected output:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>NGINX 1.28 - Offline Installation Success</title>
...
```

### Remote Testing

```bash
# From another machine
curl http://prod-server-ip

# Or test in browser
firefox http://prod-server-ip
```

### Log Verification

```bash
# View access log
sudo tail -f /var/log/nginx/access.log

# View error log
sudo tail -f /var/log/nginx/error.log

# Check for any errors
sudo grep -i error /var/log/nginx/error.log
```

### Configuration Test

```bash
# Test configuration without reloading
sudo nginx -t

# Verify all configuration files
sudo nginx -T | less
```

---

## Troubleshooting

### Issue 1: RPM Installation Fails with Dependency Errors

**Error message:**
```
Error: Problem: conflicting requests
  - nothing provides libxxx.so.1 needed by nginx-1.28.0
```

**Solution:**

The dependency wasn't downloaded on the online server. Go back to the online server:

```bash
cd ~/nginx-offline
rm -rf *.rpm

# Download with additional verbosity
sudo dnf install --downloadonly --downloaddir=. nginx -y --verbose

# Verify all dependencies are present
ls -lh

# Recreate tarball
tar -czvf nginx-offline-rpms.tar.gz *.rpm

# Transfer again
scp nginx-offline-rpms.tar.gz prod-server:/tmp/
```

### Issue 2: NGINX Won't Start

**Check status:**
```bash
sudo systemctl status nginx -l
```

**Check logs:**
```bash
sudo journalctl -xeu nginx.service
sudo tail -50 /var/log/nginx/error.log
```

**Common causes:**

1. **Port already in use:**
```bash
# Check what's using port 80
sudo ss -tlnp | grep :80

# Kill conflicting process
sudo kill $(sudo lsof -t -i:80)
```

2. **Configuration syntax error:**
```bash
sudo nginx -t
```

3. **SELinux blocking:**
```bash
sudo ausearch -m avc -ts recent | grep nginx
```

### Issue 3: Permission Denied Errors

**Fix ownership:**
```bash
sudo chown -R nginx:nginx /usr/share/nginx/html
sudo chmod -R 755 /usr/share/nginx/html
```

**Fix SELinux context:**
```bash
sudo restorecon -Rv /usr/share/nginx/html
```

### Issue 4: 403 Forbidden Error

**Check permissions:**
```bash
ls -laZ /usr/share/nginx/html/
```

**Ensure index file exists:**
```bash
ls -la /usr/share/nginx/html/index.html
```

**Check NGINX error log:**
```bash
sudo tail -20 /var/log/nginx/error.log
```

### Issue 5: Cannot Access from Network

**Checklist:**
1. ✓ Firewall allows HTTP/HTTPS
2. ✓ NGINX is running
3. ✓ Server IP is correct
4. ✓ SELinux contexts are correct

**Verify firewall:**
```bash
sudo firewall-cmd --list-all | grep services
```

**Test from server itself:**
```bash
curl http://localhost
```

**Test from network:**
```bash
curl http://server-ip
```

### Issue 6: Checksum Verification Fails

**Error:**
```
nginx-offline-rpms.tar.gz: FAILED
```

**Solution:**

The file was corrupted during transfer. Re-transfer from online server:

```bash
# On online server - regenerate checksum
sha256sum nginx-offline-rpms.tar.gz > nginx-offline-rpms.sha256

# Transfer both files again
scp nginx-offline-rpms.tar.gz nginx-offline-rpms.sha256 prod-server:/tmp/

# On offline server - verify again
cd /tmp
sha256sum -c nginx-offline-rpms.sha256
```

---

## Maintenance and Updates

### Updating NGINX

When a new version is released:

**On online server:**
```bash
cd ~/nginx-offline
rm -rf *.rpm

# Download new version
sudo dnf install --downloadonly --downloaddir=. nginx

# Package and transfer
tar -czvf nginx-offline-rpms-v1.28.1.tar.gz *.rpm
scp nginx-offline-rpms-v1.28.1.tar.gz prod-server:/tmp/
```

**On offline server:**
```bash
cd /tmp
tar -xzvf nginx-offline-rpms-v1.28.1.tar.gz

# Update NGINX
sudo dnf update nginx*.rpm --disablerepo="*"

# Restart service
sudo systemctl restart nginx

# Verify new version
nginx -v
```

### Backup Current Installation

```bash
# Backup NGINX configuration
sudo tar -czvf nginx-config-backup-$(date +%Y%m%d).tar.gz \
    /etc/nginx/ \
    /usr/share/nginx/html/

# Backup RPMs
sudo cp /tmp/nginx-offline/*.rpm /opt/backups/nginx-rpms/

# List installed NGINX packages
rpm -qa | grep nginx > installed-nginx-packages.txt
```

### Rollback to Previous Version

```bash
# List available versions
ls -lh /opt/backups/nginx-rpms/

# Downgrade to specific version
sudo dnf downgrade /opt/backups/nginx-rpms/nginx-1.26.0-*.rpm --disablerepo="*"

# Restart service
sudo systemctl restart nginx
```

### Update Local Repository

After adding new RPMs to your local repository:

```bash
# Add new RPMs to repository directory
sudo cp new-package.rpm /opt/local-repos/nginx/

# Update repository metadata
sudo createrepo --update /opt/local-repos/nginx/

# Clear DNF cache
sudo dnf clean all
sudo dnf makecache

# Verify
sudo dnf list available --repo=local-nginx
```

---

## Best Practices

### Security Recommendations

1. **Remove tarball after installation:**
```bash
sudo rm -f /tmp/nginx-offline-rpms.tar.gz
```

2. **Restrict NGINX configuration access:**
```bash
sudo chmod 640 /etc/nginx/nginx.conf
sudo chown root:nginx /etc/nginx/nginx.conf
```

3. **Hide NGINX version:**
```bash
# Add to /etc/nginx/nginx.conf in http block
server_tokens off;
```

4. **Regular security updates:**
- Monitor nginx.org for security advisories
- Download and install security patches promptly
- Test in non-production first

### Documentation

Maintain documentation for your offline environment:

```bash
# Create installation record
sudo tee /root/nginx-installation-record.txt > /dev/null <<EOF
NGINX Installation Record
=========================
Installation Date: $(date)
NGINX Version: $(nginx -v 2>&1)
RHEL Version: $(cat /etc/redhat-release)
Installed By: $(whoami)
Source: Offline installation from nginx.org packages
RPM Location: /tmp/nginx-offline/
Local Repository: /opt/local-repos/nginx/

Installed Packages:
$(rpm -qa | grep nginx)

Configuration Files:
- /etc/nginx/nginx.conf
- /etc/nginx/conf.d/*.conf

Service Status:
$(systemctl status nginx --no-pager)
EOF
```

### Disaster Recovery

Keep these items in a secure location:

1. ✓ Original nginx-offline-rpms.tar.gz
2. ✓ Installation documentation
3. ✓ Configuration backups
4. ✓ Custom scripts and tools
5. ✓ SSL/TLS certificates (if used)

---

## Summary Checklist

### Online Server Tasks
- [x] Create NGINX stable repository
- [x] Download NGINX and dependencies
- [x] Create tarball
- [x] Generate checksum
- [x] Transfer to offline server

### Offline Server Tasks
- [x] Extract tarball
- [x] Install RPMs without repositories
- [x] Enable and start NGINX
- [x] Verify installation
- [x] Configure firewall
- [x] Configure SELinux
- [x] Test access

### Optional Tasks
- [x] Create local repository
- [x] Setup permanent repository location
- [x] Create custom test page
- [x] Document installation
- [x] Setup backup strategy

---

## Conclusion

You have successfully installed NGINX 1.28 on an offline RHEL 9.6 server. This installation is:

✅ **Repository-independent** - No internet required
✅ **Production-ready** - Fully functional and secure
✅ **Maintainable** - Easy to update and backup
✅ **Documented** - Complete installation record

### Next Steps

1. Configure virtual hosts for your applications
2. Setup SSL/TLS certificates
3. Implement reverse proxy or load balancing
4. Configure monitoring and logging
5. Perform security hardening
6. Setup automated backups

For additional NGINX configuration examples, refer to the main "NGINX Installation Guide for RHEL" documentation.

---

## Additional Resources

- Official NGINX Documentation: https://nginx.org/en/docs/
- NGINX Configuration Examples: https://www.nginx.com/resources/wiki/start/
- RHEL 9 Documentation: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9

**Note:** Keep the downloaded tarball in a secure backup location for future reinstalls or disaster recovery scenarios.
