# Jenkins Daily Backup  
 
### 1. Use a “Hot Backup” (No Downtime)

You can safely back up Jenkins while it is running by **excluding cache and temporary folders**.

Create this script:

```
vi /opt/jenkins_hot_backup.sh
```

Content:

```
#!/bin/bash

DATE=$(date +"%Y-%m-%d")
BACKUP_DIR="/opt/jenkins_backup"
JENKINS_HOME="/var/lib/jenkins"
TARGET="$BACKUP_DIR/jenkins-$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

tar --exclude="$JENKINS_HOME/war" \
    --exclude="$JENKINS_HOME/cache" \
    --exclude="$JENKINS_HOME/tmp" \
    --exclude="$JENKINS_HOME/logs" \
    -czf "$TARGET" "$JENKINS_HOME"

find "$BACKUP_DIR" -mtime +7 -type f -delete
```

Make it executable:

```
chmod +x /opt/jenkins_hot_backup.sh
```

This performs a **live backup** without touching running processes.

---

### 2. Schedule Daily Backup (No Service Restart Needed)

```
crontab -e
```

Add:

```
0 2 * * * /opt/jenkins_hot_backup.sh >/opt/jenkins_backup.log 2>&1
```

---

### 3. Important Notes for Live Backup

This backup includes:

* Jobs
* Configurations
* Credentials
* Plugins
* Pipelines
* Secrets
* Node configs

It excludes only non-persistent items (war, cache, tmp).

This is a **production-safe backup method** used in high-availability Jenkins setups.

---

### 4. Safer Method (If Consistency Required) – Use Jenkins ThinBackup Plugin

You can also use:

**Manage Jenkins → Manage Plugins → Install: “ThinBackup”**

Features:

* No downtime
* Scheduled backups inside Jenkins
* Includes jobs, configs, user data
* Supports incremental and full backups

After installing:
**Manage Jenkins → ThinBackup**

Configure:

* Backup directory
* Schedule
* What to include/exclude

---

### 5. If you want the most Enterprise-grade method

I can also help you set up:

* Snapshot backup via LVM
* Snapshot backup from VM hypervisor
* S3/MinIO remote replicated backups
* Jenkins high availability with zero-downtime failover

Just tell me what environment you are using, Boss.
