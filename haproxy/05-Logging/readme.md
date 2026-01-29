# HAProxy Logging and Rotation Documentation

This document outlines the configuration for HAProxy logging via `rsyslog` and automatic log management using `logrotate` on Linux (EL9).

## 1. Overview

* **HAProxy Version:** 2.8.x
* **Log Destination:** `/var/log/haproxy/`
* **Access Logs:** `/var/log/haproxy/access.log` (Severity: info)
* **Error Logs:** `/var/log/haproxy/error.log` (Severity: notice / warning / err)
* **Rotation Naming:** `filename-YYYYMMDD-HHMMSS.gz`

---

## 2. HAProxy Configuration

**File Path:** `/etc/haproxy/haproxy.cfg`

The `global` section is configured to send logs to the local syslog socket. The `defaults` section enables HTTP logging.

```haproxy
global
    log /dev/log local0

defaults
    log global
    mode http
    option httplog
```

---

## 3. Rsyslog Routing

**File Path:** `/etc/rsyslog.d/haproxy.conf`

Rsyslog filters incoming messages from the `haproxy` program and splits them based on severity.

```text
# Create directory permissions
$FileCreateMode 0640
$DirCreateMode 0755

# Route Errors (Severity 0-5: Emerg, Alert, Crit, Err, Warn, Notice)
if $programname == 'haproxy' and $syslogseverity <= 5 then /var/log/haproxy/error.log

# Route Access Logs (Severity 6-7: Info, Debug)
if $programname == 'haproxy' and $syslogseverity > 5 then /var/log/haproxy/access.log

# Stop processing to prevent logs from appearing in /var/log/messages
if $programname == 'haproxy' then stop
```

---

## 4. Logrotate Configuration

**File Path:** `/etc/logrotate.d/haproxy`

Handles daily rotation, compression, and specific naming conventions.

```text
/var/log/haproxy/*.log {
    daily
    missingok
    rotate 10
    compress
    notifempty
    create 0640 root root
    sharedscripts

    # Custom naming: filename-YYYYMMDD-HHMMSS
    dateext
    dateformat -%Y%m%d-%H%M%S

    postrotate
        /usr/bin/systemctl kill -s HUP rsyslog.service >/dev/null 2>&1 || true
    endscript
}
```

---

## 5. Maintenance Commands

### Restart Services

After modifying configurations, restart the services to apply changes:

```bash
systemctl restart rsyslog
systemctl restart haproxy
```

### Manual Log Rotation (Testing)

To force a rotation immediately (ignoring the daily schedule):

```bash
logrotate -f /etc/logrotate.d/haproxy
```

### Debugging Logrotate

To see what logrotate would do without actually changing any files:

```bash
logrotate -d /etc/logrotate.d/haproxy
```

### Monitoring Logs

```bash
# View live access logs
tail -f /var/log/haproxy/access.log

# View live error logs
tail -f /var/log/haproxy/error.log
```

---

## 6. Directory Structure

```text
/var/log/haproxy/
├── access.log                      # Current active access logs
├── access.log-20260129-153000.gz   # Archived access logs
├── error.log                       # Current active error logs
└── error.log-20260129-153000.gz    # Archived error logs
```

---
