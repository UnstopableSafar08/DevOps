# System Limits Configuration for HAProxy, Apache, and Keepalived

A production-ready guide for configuring user and systemd limits for critical load-balancer services on Oracle Linux / RHEL / CentOS systems.

---

## Table of Contents

- [Purpose](#purpose)
- [Concepts](#concepts)
- [User-Level Limits](#user-level-limits)
- [Systemd Service Overrides](#systemd-service-overrides)
  - [HAProxy Configuration](#haproxy-configuration)
  - [Apache Configuration](#apache-configuration)
  - [Keepalived Configuration](#keepalived-configuration)
- [Verification](#verification)
- [Kernel Alignment](#kernel-alignment)
- [Best Practices](#best-practices)
- [License](#license)

---

## Purpose

This document describes the recommended configuration for **file descriptor and process/thread limits** for critical services on a load-balancer node. It ensures **stability, performance, and safety** for services handling high concurrency.

**Target Environment:**
- **OS:** Oracle Linux / RHEL / CentOS
- **Hardware:** 12 vCPU cores, 16 GB RAM

---

## Concepts

| Parameter     | Meaning                                 | Notes                                                    |
| ------------- | --------------------------------------- | -------------------------------------------------------- |
| `LimitNOFILE` | Maximum number of open file descriptors | Controls connection capacity (TCP sockets, files, pipes) |
| `LimitNPROC`  | Maximum number of processes/threads     | Controls concurrency and prevents runaway processes      |
| Soft limit    | Default limit applied to the process    | Can be raised up to the hard limit by the process itself |
| Hard limit    | Maximum allowed limit                   | Only root/systemd can increase beyond this               |

**Important:**

- PAM limits (`/etc/security/limits.d/*.conf`) apply to interactive sessions
- Systemd service limits **override PAM limits** for managed services
- Always use systemd overrides for services managed by systemd

---

## User-Level Limits

### Configuration File

Create `/etc/security/limits.d/service_limits.conf`:

```conf
# Apache HTTPD user
apache     soft    nofile    65536
apache     hard    nofile    65536
apache     soft    nproc     5000
apache     hard    nproc     5000

# Root user (for HAProxy and Keepalived master processes, and system operations)
root       soft    nofile    100000
root       hard    nofile    100000
root       soft    nproc     10000
root       hard    nproc     10000
```

> **Note:** These limits are applied at login via PAM. Services managed by systemd will not use these unless PAM is explicitly configured. HAProxy and Keepalived run as root, so their limits come from the root user configuration and systemd overrides.

---

## Systemd Service Overrides

### Recommended Limits Summary

| Service    | LimitNOFILE | LimitNPROC | Process Owner | Purpose                           |
| ---------- | ----------- | ---------- | ------------- | --------------------------------- |
| HAProxy    | 100000      | 9000       | root (master) | High concurrency load balancing   |
| Apache     | 65536       | 5000       | apache        | Moderate web server workload      |
| Keepalived | 4096        | 256        | root          | Low overhead control-plane service|

> **Note:** HAProxy and Keepalived run their master processes as root (for privileged port binding and VRRP). Worker processes may drop to unprivileged users, but systemd limits apply to the service as a whole.

---

### HAProxy Configuration

**File:** `/etc/systemd/system/haproxy.service.d/limits.conf`

```ini
[Service]
LimitNOFILE=100000
LimitNPROC=9000
```

**Apply Changes:**

```bash
mkdir -p /etc/systemd/system/haproxy.service.d/
# Create the limits.conf file above
systemctl daemon-reload
systemctl restart haproxy
```

**Additional Consideration:**

Ensure HAProxy's `maxconn` parameter in `/etc/haproxy/haproxy.cfg` aligns with the NOFILE limit.

---

### Apache Configuration

**File:** `/etc/systemd/system/httpd.service.d/limits.conf`

```ini
[Service]
LimitNOFILE=65536
LimitNPROC=5000
```

**Apply Changes:**

```bash
mkdir -p /etc/systemd/system/httpd.service.d/
# Create the limits.conf file above
systemctl daemon-reload
systemctl restart httpd
```

**Additional Consideration:**

Adjust these values based on your Apache MPM (prefork/worker/event) configuration and expected concurrent connections.

---

### Keepalived Configuration

**File:** `/etc/systemd/system/keepalived.service.d/limits.conf`

```ini
[Service]
LimitNOFILE=4096
LimitNPROC=256
```

**Apply Changes:**

```bash
mkdir -p /etc/systemd/system/keepalived.service.d/
# Create the limits.conf file above
systemctl daemon-reload
systemctl restart keepalived
```

---

## Verification

### Check Systemd Configuration

```bash
systemctl show haproxy | grep -E 'LimitNOFILE|LimitNPROC'
systemctl show httpd | grep -E 'LimitNOFILE|LimitNPROC'
systemctl show keepalived | grep -E 'LimitNOFILE|LimitNPROC'
```

### Check Runtime Limits

```bash
# Using process ID
cat /proc/$(pidof haproxy)/limits | grep "Max open files"

# Or using systemd's main PID
cat /proc/$(systemctl show -p MainPID --value haproxy)/limits | grep "Max open files"
```

### Check Current File Descriptor Usage

```bash
# For a specific service
lsof -u haproxy | wc -l

# System-wide
cat /proc/sys/fs/file-nr
```

---

## Kernel Alignment

Ensure the system's maximum file descriptors support these limits:

**Check Current Value:**

```bash
sysctl fs.file-max
```

**Set Recommended Value:**

```bash
echo "fs.file-max = 500000" > /etc/sysctl.d/99-fd.conf
sysctl --system
```

**Verify:**

```bash
sysctl fs.file-max
```

---

## Best Practices

1. **Never modify vendor service files** (`/usr/lib/systemd/system/*.service`) directly
   - Always use drop-in overrides in `/etc/systemd/system/<service>.service.d/`
   - This ensures your changes survive package updates

2. **Keep HAProxy NOFILE high** for high concurrency scenarios
   - Each client connection requires at least one file descriptor
   - Backend connections require additional file descriptors

3. **Align Apache limits with MPM settings**
   - Calculate based on: `MaxRequestWorkers × ThreadsPerChild`
   - Add buffer for file operations and connections

4. **Keep Keepalived limits conservative**
   - It's a control-plane service with minimal resource needs
   - High limits can mask configuration issues

5. **Always verify limits after changes**
   - Check both systemd configuration and runtime limits
   - Verify after system reboots

6. **Monitor file descriptor usage**
   - Set up monitoring for file descriptor exhaustion
   - Alert before reaching 80% of limits

7. **Document your changes**
   - Add comments in override files explaining why limits were set
   - Track changes in version control

8. **Use infinity sparingly**
   - While `LimitNOFILE=infinity` is valid, explicit limits help catch issues early

---
