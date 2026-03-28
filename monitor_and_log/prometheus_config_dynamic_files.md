# Splitting Prometheus Configuration into Multiple Files

A comprehensive guide on how to organize Prometheus scrape configurations into separate modular files for better maintainability and scalability.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Option 1: Without file_sd_configs](#option-1-without-file_sd_configs)
  - [Directory Structure](#directory-structure)
  - [Configuration Files](#configuration-files)
  - [Implementation Steps](#implementation-steps)
  - [Validation and Reload](#validation-and-reload)
- [Option 2: With file_sd_configs](#option-2-with-file_sd_configs)
  - [Directory Structure](#directory-structure-1)
  - [Configuration Files](#configuration-files-1)
  - [Implementation Steps](#implementation-steps-1)
  - [Adding New Targets](#adding-new-targets)
- [Comparison](#comparison)
- [Verification Commands](#verification-commands)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Overview

As your Prometheus monitoring setup grows, managing all scrape configurations in a single `prometheus.yml` file becomes difficult. This guide covers two approaches to split configurations:

- **Option 1**: Static configuration split using `scrape_config_files` (manual reload required)
- **Option 2**: Dynamic target management using `file_sd_configs` (auto-reload for targets)

## Prerequisites

- Prometheus version 2.43 or higher (this guide uses Prometheus 3.x syntax)
- Root or sudo access to the Prometheus server
- Basic understanding of YAML syntax

### Check Prometheus Version

```bash
prometheus --version
```

---

## Option 1: Without file_sd_configs

This approach splits job configurations into separate files. All changes require manual reload.

### Directory Structure

```
/etc/prometheus/
├── prometheus.yml
└── scrape_configs/
    ├── node_exporter.yml
    ├── process_exporter.yml
    └── tomcat.yml
```

### Configuration Files

#### Main Configuration

**File:** `/etc/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s

scrape_config_files:
  - "scrape_configs/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

#### Node Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/node_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    static_configs:
      - targets: ['192.168.1.10:9100']
        labels:
          env: 'production'
          module: 'web-server'
          node: 'web-01'

      - targets: ['192.168.1.11:9100']
        labels:
          env: 'production'
          module: 'web-server'
          node: 'web-02'

      - targets: ['192.168.1.20:9100']
        labels:
          env: 'production'
          module: 'database'
          node: 'db-01'

      - targets: ['192.168.1.30:9100']
        labels:
          env: 'staging'
          module: 'application'
          node: 'app-staging-01'

      - targets: ['192.168.1.40:9100']
        labels:
          env: 'production'
          module: 'cache'
          node: 'redis-01'
```

#### Process Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/process_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'process-exporter'
    static_configs:
      - targets: ['192.168.1.20:9256']
        labels:
          env: 'production'
          module: 'database'
          node: 'db-01'

      - targets: ['192.168.1.10:9256']
        labels:
          env: 'production'
          module: 'web-server'
          node: 'web-01'
```

#### Tomcat Configuration

**File:** `/etc/prometheus/scrape_configs/tomcat.yml`

```yaml
scrape_configs:
  - job_name: 'tomcat'
    static_configs:
      - targets: ['192.168.1.50:9104']
        labels:
          env: 'production'
          module: 'user-service'
          node: 'tomcat-01'

      - targets: ['192.168.1.51:9104']
        labels:
          env: 'production'
          module: 'payment-service'
          node: 'tomcat-02'

      - targets: ['192.168.1.52:9104']
        labels:
          env: 'production'
          module: 'order-service'
          node: 'tomcat-03'

      - targets: ['192.168.1.60:9104']
        labels:
          env: 'staging'
          module: 'user-service'
          node: 'tomcat-staging-01'
```

### Implementation Steps

#### Step 1: Backup Current Configuration

```bash
sudo cp /etc/prometheus/prometheus.yml /etc/prometheus/prometheus.yml.backup.$(date +%Y%m%d_%H%M%S)
```

#### Step 2: Create Directory Structure

```bash
sudo mkdir -p /etc/prometheus/scrape_configs
```

#### Step 3: Create Main Configuration

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  scrape_interval: 10s
  evaluation_interval: 10s

scrape_config_files:
  - "scrape_configs/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF
```

#### Step 4: Create Node Exporter Configuration

```bash
sudo tee /etc/prometheus/scrape_configs/node_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    static_configs:
      - targets: ['192.168.1.10:9100']
        labels:
          env: 'production'
          module: 'web-server'
          node: 'web-01'

      - targets: ['192.168.1.11:9100']
        labels:
          env: 'production'
          module: 'web-server'
          node: 'web-02'

      - targets: ['192.168.1.20:9100']
        labels:
          env: 'production'
          module: 'database'
          node: 'db-01'

      - targets: ['192.168.1.30:9100']
        labels:
          env: 'staging'
          module: 'application'
          node: 'app-staging-01'

      - targets: ['192.168.1.40:9100']
        labels:
          env: 'production'
          module: 'cache'
          node: 'redis-01'
EOF
```

#### Step 5: Create Process Exporter Configuration

```bash
sudo tee /etc/prometheus/scrape_configs/process_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'process-exporter'
    static_configs:
      - targets: ['192.168.1.20:9256']
        labels:
          env: 'production'
          module: 'database'
          node: 'db-01'

      - targets: ['192.168.1.10:9256']
        labels:
          env: 'production'
          module: 'web-server'
          node: 'web-01'
EOF
```

#### Step 6: Create Tomcat Configuration

```bash
sudo tee /etc/prometheus/scrape_configs/tomcat.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'tomcat'
    static_configs:
      - targets: ['192.168.1.50:9104']
        labels:
          env: 'production'
          module: 'user-service'
          node: 'tomcat-01'

      - targets: ['192.168.1.51:9104']
        labels:
          env: 'production'
          module: 'payment-service'
          node: 'tomcat-02'

      - targets: ['192.168.1.52:9104']
        labels:
          env: 'production'
          module: 'order-service'
          node: 'tomcat-03'

      - targets: ['192.168.1.60:9104']
        labels:
          env: 'staging'
          module: 'user-service'
          node: 'tomcat-staging-01'
EOF
```

#### Step 7: Set Permissions

```bash
sudo chown -R prometheus:prometheus /etc/prometheus/
sudo chmod 644 /etc/prometheus/prometheus.yml
sudo chmod 644 /etc/prometheus/scrape_configs/*.yml
sudo chmod 755 /etc/prometheus/scrape_configs/
```

### Validation and Reload

```bash
# Validate configuration
promtool check config /etc/prometheus/prometheus.yml

# Reload Prometheus (choose one method)
sudo systemctl reload prometheus
# OR
curl -X POST http://localhost:9090/-/reload
# OR
sudo kill -HUP $(pgrep prometheus)

# Check service status
sudo systemctl status prometheus --no-pager
```

---

## Option 2: With file_sd_configs

This approach separates job definitions from target lists. Target changes auto-reload without manual intervention.

### Directory Structure

```
/etc/prometheus/
├── prometheus.yml
├── scrape_configs/
│   ├── node_exporter.yml
│   ├── process_exporter.yml
│   └── tomcat.yml
└── targets/
    ├── node_exporter/
    │   ├── production.yml
    │   └── staging.yml
    ├── process_exporter/
    │   └── production.yml
    └── tomcat/
        ├── production.yml
        └── staging.yml
```

### Configuration Files

#### Main Configuration

**File:** `/etc/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s

scrape_config_files:
  - "scrape_configs/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

#### Node Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/node_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/node_exporter/*.yml'
        refresh_interval: 30s
```

#### Process Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/process_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'process-exporter'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/process_exporter/*.yml'
        refresh_interval: 1m
```

#### Tomcat Configuration

**File:** `/etc/prometheus/scrape_configs/tomcat.yml`

```yaml
scrape_configs:
  - job_name: 'tomcat'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/tomcat/*.yml'
        refresh_interval: 30s
```

#### Target Files

**File:** `/etc/prometheus/targets/node_exporter/production.yml`

```yaml
- targets:
    - 192.168.1.10:9100
    - 192.168.1.11:9100
    - 192.168.1.20:9100
    - 192.168.1.40:9100
  labels:
    env: production
```

**File:** `/etc/prometheus/targets/node_exporter/staging.yml`

```yaml
- targets:
    - 192.168.1.30:9100
  labels:
    env: staging
```

**File:** `/etc/prometheus/targets/process_exporter/production.yml`

```yaml
- targets:
    - 192.168.1.20:9256
  labels:
    env: production
    module: database
    node: db-01

- targets:
    - 192.168.1.10:9256
  labels:
    env: production
    module: web-server
    node: web-01
```

**File:** `/etc/prometheus/targets/tomcat/production.yml`

```yaml
- targets:
    - 192.168.1.50:9104
  labels:
    env: production
    module: user-service
    node: tomcat-01

- targets:
    - 192.168.1.51:9104
  labels:
    env: production
    module: payment-service
    node: tomcat-02

- targets:
    - 192.168.1.52:9104
  labels:
    env: production
    module: order-service
    node: tomcat-03
```

**File:** `/etc/prometheus/targets/tomcat/staging.yml`

```yaml
- targets:
    - 192.168.1.60:9104
  labels:
    env: staging
    module: user-service
    node: tomcat-staging-01
```

### Implementation Steps

#### Step 1: Backup Current Configuration

```bash
sudo cp /etc/prometheus/prometheus.yml /etc/prometheus/prometheus.yml.backup.$(date +%Y%m%d_%H%M%S)
```

#### Step 2: Create Directory Structure

```bash
sudo mkdir -p /etc/prometheus/scrape_configs
sudo mkdir -p /etc/prometheus/targets/node_exporter
sudo mkdir -p /etc/prometheus/targets/process_exporter
sudo mkdir -p /etc/prometheus/targets/tomcat
```

#### Step 3: Create Main Configuration

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  scrape_interval: 10s
  evaluation_interval: 10s

scrape_config_files:
  - "scrape_configs/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF
```

#### Step 4: Create Scrape Configurations

```bash
# Node Exporter
sudo tee /etc/prometheus/scrape_configs/node_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/node_exporter/*.yml'
        refresh_interval: 30s
EOF

# Process Exporter
sudo tee /etc/prometheus/scrape_configs/process_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'process-exporter'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/process_exporter/*.yml'
        refresh_interval: 1m
EOF

# Tomcat
sudo tee /etc/prometheus/scrape_configs/tomcat.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'tomcat'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/tomcat/*.yml'
        refresh_interval: 30s
EOF
```

#### Step 5: Create Target Files

```bash
# Node Exporter Production Targets
sudo tee /etc/prometheus/targets/node_exporter/production.yml > /dev/null <<'EOF'
- targets:
    - 192.168.1.10:9100
    - 192.168.1.11:9100
    - 192.168.1.20:9100
    - 192.168.1.40:9100
  labels:
    env: production
EOF

# Node Exporter Staging Targets
sudo tee /etc/prometheus/targets/node_exporter/staging.yml > /dev/null <<'EOF'
- targets:
    - 192.168.1.30:9100
  labels:
    env: staging
EOF

# Process Exporter Targets
sudo tee /etc/prometheus/targets/process_exporter/production.yml > /dev/null <<'EOF'
- targets:
    - 192.168.1.20:9256
  labels:
    env: production
    module: database
    node: db-01

- targets:
    - 192.168.1.10:9256
  labels:
    env: production
    module: web-server
    node: web-01
EOF

# Tomcat Production Targets
sudo tee /etc/prometheus/targets/tomcat/production.yml > /dev/null <<'EOF'
- targets:
    - 192.168.1.50:9104
  labels:
    env: production
    module: user-service
    node: tomcat-01

- targets:
    - 192.168.1.51:9104
  labels:
    env: production
    module: payment-service
    node: tomcat-02

- targets:
    - 192.168.1.52:9104
  labels:
    env: production
    module: order-service
    node: tomcat-03
EOF

# Tomcat Staging Targets
sudo tee /etc/prometheus/targets/tomcat/staging.yml > /dev/null <<'EOF'
- targets:
    - 192.168.1.60:9104
  labels:
    env: staging
    module: user-service
    node: tomcat-staging-01
EOF
```

#### Step 6: Set Permissions

```bash
sudo chown -R prometheus:prometheus /etc/prometheus/
sudo chmod 644 /etc/prometheus/prometheus.yml
sudo chmod 644 /etc/prometheus/scrape_configs/*.yml
sudo chmod -R 644 /etc/prometheus/targets/*/*.yml
sudo chmod 755 /etc/prometheus/scrape_configs/
sudo chmod -R 755 /etc/prometheus/targets/
```

#### Step 7: Validate and Reload

```bash
# Validate configuration
promtool check config /etc/prometheus/prometheus.yml

# Reload Prometheus (only needed once for initial setup)
sudo systemctl reload prometheus

# Check service status
sudo systemctl status prometheus --no-pager
```

### Adding New Targets

With file_sd_configs, adding new targets requires no manual reload.

```bash
# Add a new server to node_exporter targets
sudo tee -a /etc/prometheus/targets/node_exporter/production.yml > /dev/null <<'EOF'

- targets:
    - 192.168.1.99:9100
  labels:
    env: production
    module: new-service
    node: new-server-01
EOF

# No reload needed - Prometheus auto-detects within refresh_interval (30s)
```

---

## Comparison

| Feature | Option 1 (Static) | Option 2 (file_sd_configs) |
|---------|-------------------|---------------------------|
| Target Auto-Reload | No | Yes |
| Manual Reload Required | Always | Only for job config changes |
| Directory Complexity | Simple | More directories |
| Target Management | Edit scrape config files | Edit target files |
| Error Handling | Fails on bad config | Skips bad target files |
| Best For | Stable environments | Dynamic environments |
| Refresh Interval | N/A | Configurable (default 5m) |

### When to Use Each Option

**Use Option 1 when:**

- Your infrastructure is stable
- Targets rarely change
- You prefer simpler directory structure
- You have a small number of targets

**Use Option 2 when:**

- Targets change frequently
- You want zero-downtime target updates
- You manage many targets
- You use automation tools for target management
- Different teams manage different target lists

---

## Verification Commands

### Check Service Status

```bash
sudo systemctl status prometheus --no-pager
```

### List All Active Targets

```bash
curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job) - \(.labels.instance) - \(.health)"'
```

### Count Targets by Job

```bash
curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets | group_by(.labels.job) | .[] | "\(.[0].labels.job): \(length) targets"'
```

### Check for Down Targets

```bash
curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | select(.health=="down") | "\(.labels.job) - \(.labels.instance)"'
```

### View Configuration

```bash
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | head -50
```

### Check Prometheus Logs

```bash
sudo journalctl -u prometheus -n 100 --no-pager
```

---

## Troubleshooting

### Error: cannot unmarshal !!seq into config.ScrapeConfigs

This error occurs in Prometheus 3.x when external files have incorrect format.

**Wrong format:**

```yaml
- job_name: 'node_exporter'
  static_configs:
    - targets: ['192.168.1.10:9100']
```

**Correct format:**

```yaml
scrape_configs:
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['192.168.1.10:9100']
```

### Configuration Validation Failed

```bash
# Check detailed error
promtool check config /etc/prometheus/prometheus.yml

# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('/etc/prometheus/scrape_configs/node_exporter.yml'))"
```

### Targets Not Appearing (file_sd_configs)

```bash
# Check file permissions
ls -la /etc/prometheus/targets/node_exporter/

# Check for YAML errors in target files
python3 -c "import yaml; yaml.safe_load(open('/etc/prometheus/targets/node_exporter/production.yml'))"

# Check Prometheus logs for file_sd errors
sudo journalctl -u prometheus -n 100 | grep -i "file_sd\|error"
```

### Reload Not Working

```bash
# Check if lifecycle API is enabled
curl -s http://localhost:9090/-/healthy

# Check Prometheus startup flags
ps aux | grep prometheus | grep -o "\-\-web.enable-lifecycle"

# Enable lifecycle API if needed (add to systemd unit or startup script)
# --web.enable-lifecycle
```

---

## Best Practices

1. **Always validate before reload**: Run `promtool check config` before applying changes.

2. **Backup configurations**: Create backups before making changes.

3. **Use consistent labels**: Maintain consistent label naming across all configurations.

4. **Version control**: Keep configurations in a Git repository.

5. **Set appropriate refresh intervals**: Balance between responsiveness and load.

6. **Monitor configuration health**: Watch `prometheus_config_last_reload_successful` metric.

7. **Document your setup**: Maintain documentation for your configuration structure.

8. **Test in staging first**: Validate changes in non-production environment.

---

## References

- [Prometheus Configuration Documentation](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Prometheus File-Based Service Discovery](https://prometheus.io/docs/guides/file-sd/)
- [Prometheus GitHub Repository](https://github.com/prometheus/prometheus)

---
