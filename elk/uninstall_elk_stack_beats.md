# ELK Stack and Beats Uninstall Guide

**Author:** Sagar Malla  
**Date:** 02-03-2026  
**Scope:** Elasticsearch, Kibana, Logstash, Filebeat, Metricbeat, Packetbeat, Heartbeat, Auditbeat  
**Platform:** RHEL / CentOS / Rocky Linux / AlmaLinux (RPM-based systems)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Before You Begin](#before-you-begin)
3. [Uninstall Elasticsearch](#uninstall-elasticsearch)
4. [Uninstall Kibana](#uninstall-kibana)
5. [Uninstall Logstash](#uninstall-logstash)
6. [Uninstall Filebeat](#uninstall-filebeat)
7. [Uninstall Metricbeat](#uninstall-metricbeat)
8. [Uninstall Packetbeat](#uninstall-packetbeat)
9. [Uninstall Heartbeat](#uninstall-heartbeat)
10. [Uninstall Auditbeat](#uninstall-auditbeat)
11. [Remove the Elastic YUM Repository](#remove-the-elastic-yum-repository)
12. [Remove GPG Key](#remove-gpg-key)
13. [Verify Complete Removal](#verify-complete-removal)
14. [Post-Removal Checklist](#post-removal-checklist)

---

## Prerequisites

- Root or sudo access on the target machine.
- All running services should be identified before removal to avoid disrupting dependent applications.
- Take a snapshot or backup of any data you may need before proceeding.

To confirm you are running as root:

```bash
whoami
```

If not root, prefix all commands with `sudo` or switch to root:

```bash
sudo -i
```

## Shell script file.
```bash
#!/bin/bash
# =================================================================================
# Author       : Sagar Malla
# Email        : sagarmalla08
# Date         : 02-03-2026
# Description  : Interactive uninstall of Elasticsearch, Kibana, Logstash, Beats
#                with pre-uninstall backup of configs, data, and logs
# =================================================================================

# -----------------------------
# Color Definitions
# -----------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
print_backup()  { echo -e "${CYAN}[BACKUP]${NC} $1"; }

# -----------------------------
# Root Check
# -----------------------------
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root. Use: sudo $0"
    exit 1
fi

# -----------------------------
# Backup Base Directory
# -----------------------------
BACKUP_BASE_DIR="/var/backups/elk_uninstall"

mkdir -p "$BACKUP_BASE_DIR" || {
    print_error "Failed to create backup base directory: $BACKUP_BASE_DIR"
    exit 1
}

# -----------------------------
# Backup Function
# -----------------------------
# Usage: backup_component <svc_name>
# Archives /etc/<svc>, /var/lib/<svc>, /var/log/<svc> into a single tar.gz
# Named: <svc>_YYYYMMDD_HHMMSS.tar.gz
# -----------------------------
backup_component() {
    local svc="$1"
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local archive_name="${svc}_${timestamp}.tar.gz"
    local archive_path="${BACKUP_BASE_DIR}/${archive_name}"

    # Collect only directories that actually exist
    local dirs_to_backup=()
    for dir in "/etc/$svc" "/var/lib/$svc" "/var/log/$svc"; do
        if [ -d "$dir" ]; then
            dirs_to_backup+=("$dir")
        else
            print_warning "Backup: $dir not found, skipping from archive."
        fi
    done

    if [ ${#dirs_to_backup[@]} -eq 0 ]; then
        print_warning "No directories found to back up for $svc. Skipping backup."
        return 1
    fi

    print_backup "Creating backup: $archive_path"
    print_backup "Including: ${dirs_to_backup[*]}"

    if tar -czf "$archive_path" "${dirs_to_backup[@]}" 2>/dev/null; then
        local size
        size=$(du -sh "$archive_path" | cut -f1)
        print_success "Backup created: $archive_path (${size})"
        return 0
    else
        print_error "Backup failed for $svc. Aborting uninstall of $svc to protect data."
        return 1
    fi
}

# -----------------------------
# Tools Map
# rpm package name  =>  service/dir name
# -----------------------------
declare -A tool_map=(
    ["elasticsearch"]="elasticsearch"
    ["kibana"]="kibana"
    ["logstash"]="logstash"
    ["filebeat"]="filebeat"
    ["metricbeat"]="metricbeat"
    ["packetbeat"]="packetbeat"
    ["heartbeat-elastic"]="heartbeat"
    ["auditbeat"]="auditbeat"
)

# -----------------------------
# Interactive Uninstall
# -----------------------------
echo "============================================================"
print_info  "ELK Stack and Beats Interactive Uninstaller"
print_info  "Backups will be stored in: $BACKUP_BASE_DIR"
echo "============================================================"
echo ""

for pkg in "${!tool_map[@]}"; do
    svc="${tool_map[$pkg]}"

    # Check if installed via rpm
    if rpm -q "$pkg" &>/dev/null; then

        read -rp "Would you like to remove $pkg? (yes/no): " answer
        if [[ "$answer" == "yes" ]]; then

            # ----------------------------
            # Step 1 — Backup before removal
            # ----------------------------
            echo ""
            print_backup "Starting backup for $svc before uninstall..."
            if ! backup_component "$svc"; then
                read -rp "Backup failed for $svc. Proceed with uninstall anyway? (yes/no): " force
                if [[ "$force" != "yes" ]]; then
                    print_warning "Skipping uninstall of $pkg due to failed backup."
                    echo "-----------------------------------------------------------"
                    continue
                fi
                print_warning "Proceeding with uninstall of $pkg without a backup."
            fi

            # ----------------------------
            # Step 2 — Stop and disable service
            # ----------------------------
            print_info "Stopping and disabling $svc..."
            systemctl stop "$svc" 2>/dev/null
            systemctl disable "$svc" 2>/dev/null

            # ----------------------------
            # Step 3 — Remove package
            # ----------------------------
            print_info "Removing package $pkg..."
            if dnf remove -y "$pkg"; then
                print_success "$pkg package removed."
            else
                print_error "Failed to remove $pkg package."
            fi

            # ----------------------------
            # Step 4 — Remove config, data, log, and share dirs
            # ----------------------------
            print_info "Removing configs, data, and logs for $svc..."
            for dir in "/etc/$svc" "/var/lib/$svc" "/var/log/$svc" "/usr/share/$svc"; do
                if [ -d "$dir" ]; then
                    rm -rf "$dir" && print_success "Removed $dir"
                else
                    print_warning "$dir does not exist, skipping."
                fi
            done

            # ----------------------------
            # Step 5 — Remove custom systemd unit file (if present)
            # ----------------------------
            print_info "Checking for custom systemd unit file..."
            unit_file="/etc/systemd/system/${svc}.service"
            if [ -f "$unit_file" ]; then
                rm -f "$unit_file" && print_success "Removed $unit_file"
            else
                print_warning "$unit_file does not exist, skipping."
            fi

            # ----------------------------
            # Step 6 — Remove service user
            # ----------------------------
            print_info "Removing system user $svc..."
            if id "$svc" &>/dev/null; then
                userdel -r "$svc" && print_success "User $svc removed."
            else
                print_warning "User $svc does not exist, skipping."
            fi

            print_success "$pkg has been completely uninstalled."
            echo "-----------------------------------------------------------"

        else
            print_info "Skipping $pkg as per user choice."
            echo "-----------------------------------------------------------"
        fi

    else
        print_info "$pkg is not installed, skipping."
        echo "-----------------------------------------------------------"
    fi

done

# ----------------------------
# Reload systemd once after all removals
# ----------------------------
print_info "Reloading systemd daemon..."
systemctl daemon-reload
print_success "systemd daemon reloaded."

# ----------------------------
# Backup Summary
# ----------------------------
echo ""
echo "============================================================"
print_backup "Backup Summary — files stored in: $BACKUP_BASE_DIR"
echo "------------------------------------------------------------"
if ls "$BACKUP_BASE_DIR"/*.tar.gz &>/dev/null; then
    ls -lh "$BACKUP_BASE_DIR"/*.tar.gz | awk '{print $5, $9}'
else
    print_warning "No backup files found in $BACKUP_BASE_DIR."
fi
echo "============================================================"
echo ""

print_success "Interactive ELK/Beats uninstall completed."
```



---

## Before You Begin

Check which ELK and Beats packages are currently installed on the system:

```bash
rpm -qa | grep -E "elasticsearch|kibana|logstash|filebeat|metricbeat|packetbeat|heartbeat|auditbeat"
```

Check the status of all related services:

```bash
systemctl status elasticsearch kibana logstash filebeat metricbeat packetbeat heartbeat-elastic auditbeat
```

List all data, config, and log directories that will be removed:

```bash
ls /etc/elasticsearch /etc/kibana /etc/logstash /etc/filebeat \
   /var/lib/elasticsearch /var/lib/kibana /var/lib/logstash \
   /var/log/elasticsearch /var/log/kibana /var/log/logstash 2>/dev/null
```

---

## Uninstall Elasticsearch

### Step 1 — Stop and disable the service

```bash
systemctl stop elasticsearch
systemctl disable elasticsearch
```

### Step 2 — Remove the package

```bash
dnf remove -y elasticsearch
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/elasticsearch
rm -rf /var/lib/elasticsearch
rm -rf /var/log/elasticsearch
rm -rf /usr/share/elasticsearch
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/elasticsearch.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r elasticsearch
```

---

## Uninstall Kibana

### Step 1 — Stop and disable the service

```bash
systemctl stop kibana
systemctl disable kibana
```

### Step 2 — Remove the package

```bash
dnf remove -y kibana
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/kibana
rm -rf /var/lib/kibana
rm -rf /var/log/kibana
rm -rf /usr/share/kibana
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/kibana.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r kibana
```

---

## Uninstall Logstash

### Step 1 — Stop and disable the service

```bash
systemctl stop logstash
systemctl disable logstash
```

### Step 2 — Remove the package

```bash
dnf remove -y logstash
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/logstash
rm -rf /var/lib/logstash
rm -rf /var/log/logstash
rm -rf /usr/share/logstash
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/logstash.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r logstash
```

---

## Uninstall Filebeat

### Step 1 — Stop and disable the service

```bash
systemctl stop filebeat
systemctl disable filebeat
```

### Step 2 — Remove the package

```bash
dnf remove -y filebeat
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/filebeat
rm -rf /var/lib/filebeat
rm -rf /var/log/filebeat
rm -rf /usr/share/filebeat
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/filebeat.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r filebeat
```

---

## Uninstall Metricbeat

### Step 1 — Stop and disable the service

```bash
systemctl stop metricbeat
systemctl disable metricbeat
```

### Step 2 — Remove the package

```bash
dnf remove -y metricbeat
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/metricbeat
rm -rf /var/lib/metricbeat
rm -rf /var/log/metricbeat
rm -rf /usr/share/metricbeat
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/metricbeat.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r metricbeat
```

---

## Uninstall Packetbeat

### Step 1 — Stop and disable the service

```bash
systemctl stop packetbeat
systemctl disable packetbeat
```

### Step 2 — Remove the package

```bash
dnf remove -y packetbeat
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/packetbeat
rm -rf /var/lib/packetbeat
rm -rf /var/log/packetbeat
rm -rf /usr/share/packetbeat
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/packetbeat.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r packetbeat
```

---

## Uninstall Heartbeat

Note: The RPM package name for Heartbeat is `heartbeat-elastic`, but the service and directory names use `heartbeat`.

### Step 1 — Stop and disable the service

```bash
systemctl stop heartbeat-elastic
systemctl disable heartbeat-elastic
```

### Step 2 — Remove the package

```bash
dnf remove -y heartbeat-elastic
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/heartbeat
rm -rf /var/lib/heartbeat
rm -rf /var/log/heartbeat
rm -rf /usr/share/heartbeat
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/heartbeat-elastic.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r heartbeat
```

---

## Uninstall Auditbeat

### Step 1 — Stop and disable the service

```bash
systemctl stop auditbeat
systemctl disable auditbeat
```

### Step 2 — Remove the package

```bash
dnf remove -y auditbeat
```

### Step 3 — Remove configuration, data, and log directories

```bash
rm -rf /etc/auditbeat
rm -rf /var/lib/auditbeat
rm -rf /var/log/auditbeat
rm -rf /usr/share/auditbeat
```

### Step 4 — Remove the systemd unit file (if custom)

```bash
rm -f /etc/systemd/system/auditbeat.service
systemctl daemon-reload
```

### Step 5 — Remove the system user

```bash
userdel -r auditbeat
```

---

## Remove the Elastic YUM Repository

Once all packages are removed, clean up the Elastic repository file to prevent future inadvertent installs or update checks.

Check if the repo file exists:

```bash
ls /etc/yum.repos.d/ | grep elastic
```

Remove the repository file:

```bash
rm -f /etc/yum.repos.d/elasticsearch.repo
```

Clean the DNF cache:

```bash
dnf clean all
```

---

## Remove GPG Key

List installed GPG keys and locate the Elastic key:

```bash
rpm -qa gpg-pubkey* --qf "%{name}-%{version}-%{release} --> %{summary}\n" | grep -i elastic
```

Remove the Elastic GPG key. Replace `<key-id>` with the identifier returned in the output above:

```bash
rpm -e gpg-pubkey-<key-id>
```

---

## Verify Complete Removal

Run each of the following checks to confirm nothing was left behind.

Check that no packages remain:

```bash
rpm -qa | grep -E "elasticsearch|kibana|logstash|filebeat|metricbeat|packetbeat|heartbeat|auditbeat"
```

Expected output: no output (empty).

Check that no residual directories remain:

```bash
ls /etc/elasticsearch /etc/kibana /etc/logstash /etc/filebeat \
   /var/lib/elasticsearch /var/lib/kibana /var/lib/logstash \
   /var/log/elasticsearch /var/log/kibana /var/log/logstash 2>&1
```

Expected output: errors stating the directories do not exist.

Check that no related services remain in systemd:

```bash
systemctl list-units --all | grep -E "elasticsearch|kibana|logstash|filebeat|metricbeat|packetbeat|heartbeat|auditbeat"
```

Expected output: no output (empty).

Check that no related users remain:

```bash
id elasticsearch
id kibana
id logstash
id filebeat
id metricbeat
id packetbeat
id heartbeat
id auditbeat
```

Expected output: errors stating the users do not exist.

---

## Post-Removal Checklist

Use this checklist to confirm the uninstall is fully complete before closing out the task.

| Component        | Service Stopped | Package Removed | Dirs Cleaned | User Removed |
|------------------|-----------------|-----------------|--------------|--------------|
| Elasticsearch    |                 |                 |              |              |
| Kibana           |                 |                 |              |              |
| Logstash         |                 |                 |              |              |
| Filebeat         |                 |                 |              |              |
| Metricbeat       |                 |                 |              |              |
| Packetbeat       |                 |                 |              |              |
| Heartbeat        |                 |                 |              |              |
| Auditbeat        |                 |                 |              |              |
| Elastic YUM Repo |                 |                 |              |              |
| Elastic GPG Key  |                 |                 |              |              |

---

*End of ELK Stack and Beats Uninstall Guide.*
