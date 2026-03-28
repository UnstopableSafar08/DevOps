# Splitting Prometheus Configuration into Multiple Files

A comprehensive guide on how to organize Prometheus scrape configurations into separate modular files for better maintainability and scalability.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Directory Structure](#directory-structure)
- [Option 1: Without file_sd_configs](#option-1-without-file_sd_configs)
  - [Main Configuration](#main-configuration)
  - [Node Exporter Configuration](#node-exporter-configuration)
  - [Process Exporter Configuration](#process-exporter-configuration)
  - [Tomcat Configuration](#tomcat-configuration)
  - [Implementation Commands](#implementation-commands)
- [Option 2: With file_sd_configs](#option-2-with-file_sd_configs)
  - [Main Configuration](#main-configuration-1)
  - [Node Exporter Configuration](#node-exporter-configuration-1)
  - [Process Exporter Configuration](#process-exporter-configuration-1)
  - [Tomcat Configuration](#tomcat-configuration-1)
  - [Implementation Commands](#implementation-commands-1)
  - [Adding New Targets](#adding-new-targets)
- [Comparison](#comparison)
- [Validation and Reload](#validation-and-reload)
- [Verification Commands](#verification-commands)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Overview

As Prometheus monitoring setup grows, managing all scrape configurations in a single `prometheus.yml` file becomes difficult. This guide covers two approaches to split configurations:

- **Option 1**: Using `static_configs` - targets defined inside scrape config files (manual reload required for any change)
- **Option 2**: Using `file_sd_configs` - targets defined inside scrape config files but with auto-reload capability

Both options use the same directory structure. The difference is how targets are defined within the configuration files.

## Prerequisites

- Prometheus version 2.43 or higher (this guide uses Prometheus 3.x syntax)
- Root or sudo access to the Prometheus server
- Basic understanding of YAML syntax

### Check Prometheus Version

```bash
prometheus --version
```

## Directory Structure

Both options use the same directory structure:

```
/etc/prometheus/
├── prometheus.yml
└── scrape_configs/
    ├── node_exporter.yml
    ├── process_exporter.yml
    └── tomcat.yml
```

---

## Option 1: Without file_sd_configs

This approach uses `static_configs` to define targets directly inside each scrape configuration file. Any change to targets requires a manual Prometheus reload.

### Main Configuration

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

### Node Exporter Configuration

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

### Process Exporter Configuration

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

### Tomcat Configuration

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

### Implementation Commands

```bash
# Backup current configuration
sudo cp /etc/prometheus/prometheus.yml /etc/prometheus/prometheus.yml.backup.$(date +%Y%m%d_%H%M%S)

# Create directory structure
sudo mkdir -p /etc/prometheus/scrape_configs

# Create main configuration
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

# Create node exporter configuration
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

# Create process exporter configuration
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

# Create tomcat configuration
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

# Set permissions
sudo chown -R prometheus:prometheus /etc/prometheus/
sudo chmod 644 /etc/prometheus/prometheus.yml
sudo chmod 644 /etc/prometheus/scrape_configs/*.yml
sudo chmod 755 /etc/prometheus/scrape_configs/

# Validate configuration
promtool check config /etc/prometheus/prometheus.yml

# Reload Prometheus
sudo systemctl reload prometheus
```

---

## Option 2: With file_sd_configs

This approach uses `file_sd_configs` to define targets inside the same scrape configuration files. The key difference is that target changes are automatically detected and reloaded without manual intervention.

### Main Configuration

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

### Node Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/node_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/node_exporter.yml'
        refresh_interval: 30s
    # Targets defined below will be auto-reloaded when changed

- targets:
    - 192.168.1.10:9100
    - 192.168.1.11:9100
  labels:
    env: production
    module: web-server

- targets:
    - 192.168.1.20:9100
  labels:
    env: production
    module: database
    node: db-01

- targets:
    - 192.168.1.30:9100
  labels:
    env: staging
    module: application
    node: app-staging-01

- targets:
    - 192.168.1.40:9100
  labels:
    env: production
    module: cache
    node: redis-01
```

**Note:** The above approach of combining job config and targets in the same file with file_sd_configs pointing to itself does not work correctly. For file_sd_configs to work properly, you need separate target files.

### Corrected Approach for Option 2

For `file_sd_configs` to work properly within the same directory structure, create target definition files alongside scrape configs:

**Directory Structure:**

```
/etc/prometheus/
├── prometheus.yml
└── scrape_configs/
    ├── node_exporter.yml
    ├── node_exporter_targets.yml
    ├── process_exporter.yml
    ├── process_exporter_targets.yml
    ├── tomcat.yml
    └── tomcat_targets.yml
```

### Node Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/node_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/node_exporter_targets.yml'
        refresh_interval: 30s
```

**File:** `/etc/prometheus/scrape_configs/node_exporter_targets.yml`

```yaml
- targets:
    - 192.168.1.10:9100
    - 192.168.1.11:9100
  labels:
    env: production
    module: web-server

- targets:
    - 192.168.1.20:9100
  labels:
    env: production
    module: database
    node: db-01

- targets:
    - 192.168.1.30:9100
  labels:
    env: staging
    module: application
    node: app-staging-01

- targets:
    - 192.168.1.40:9100
  labels:
    env: production
    module: cache
    node: redis-01
```

### Process Exporter Configuration

**File:** `/etc/prometheus/scrape_configs/process_exporter.yml`

```yaml
scrape_configs:
  - job_name: 'process-exporter'
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/process_exporter_targets.yml'
        refresh_interval: 1m
```

**File:** `/etc/prometheus/scrape_configs/process_exporter_targets.yml`

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

### Tomcat Configuration

**File:** `/etc/prometheus/scrape_configs/tomcat.yml`

```yaml
scrape_configs:
  - job_name: 'tomcat'
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/tomcat_targets.yml'
        refresh_interval: 30s
```

**File:** `/etc/prometheus/scrape_configs/tomcat_targets.yml`

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

- targets:
    - 192.168.1.60:9104
  labels:
    env: staging
    module: user-service
    node: tomcat-staging-01
```

### Implementation Commands

```bash
# Backup current configuration
sudo cp /etc/prometheus/prometheus.yml /etc/prometheus/prometheus.yml.backup.$(date +%Y%m%d_%H%M%S)

# Create directory structure
sudo mkdir -p /etc/prometheus/scrape_configs

# Create main configuration
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

# Create node exporter configuration
sudo tee /etc/prometheus/scrape_configs/node_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'node_exporter'
    scrape_interval: 15s
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/node_exporter_targets.yml'
        refresh_interval: 30s
EOF

# Create node exporter targets
sudo tee /etc/prometheus/scrape_configs/node_exporter_targets.yml > /dev/null <<'EOF'
- targets:
    - 192.168.1.10:9100
    - 192.168.1.11:9100
  labels:
    env: production
    module: web-server

- targets:
    - 192.168.1.20:9100
  labels:
    env: production
    module: database
    node: db-01

- targets:
    - 192.168.1.30:9100
  labels:
    env: staging
    module: application
    node: app-staging-01

- targets:
    - 192.168.1.40:9100
  labels:
    env: production
    module: cache
    node: redis-01
EOF

# Create process exporter configuration
sudo tee /etc/prometheus/scrape_configs/process_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'process-exporter'
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/process_exporter_targets.yml'
        refresh_interval: 1m
EOF

# Create process exporter targets
sudo tee /etc/prometheus/scrape_configs/process_exporter_targets.yml > /dev/null <<'EOF'
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

# Create tomcat configuration
sudo tee /etc/prometheus/scrape_configs/tomcat.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'tomcat'
    file_sd_configs:
      - files:
          - '/etc/prometheus/scrape_configs/tomcat_targets.yml'
        refresh_interval: 30s
EOF

# Create tomcat targets
sudo tee /etc/prometheus/scrape_configs/tomcat_targets.yml > /dev/null <<'EOF'
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

- targets:
    - 192.168.1.60:9104
  labels:
    env: staging
    module: user-service
    node: tomcat-staging-01
EOF

# Set permissions
sudo chown -R prometheus:prometheus /etc/prometheus/
sudo chmod 644 /etc/prometheus/prometheus.yml
sudo chmod 644 /etc/prometheus/scrape_configs/*.yml
sudo chmod 755 /etc/prometheus/scrape_configs/

# Validate configuration
promtool check config /etc/prometheus/prometheus.yml

# Reload Prometheus (only needed once for initial setup)
sudo systemctl reload prometheus
```

### Adding New Targets

With file_sd_configs, adding new targets requires no manual reload:

```bash
# Add a new server to node exporter targets
sudo tee -a /etc/prometheus/scrape_configs/node_exporter_targets.yml > /dev/null <<'EOF'

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

| Feature | Option 1 (static_configs) | Option 2 (file_sd_configs) |
|---------|---------------------------|---------------------------|
| Files per exporter | 1 | 2 |
| Target auto-reload | No | Yes |
| Manual reload required | Always | Only for job config changes |
| Add new server | Edit file + reload | Edit targets file only |
| Error handling | Fails on bad config | Skips bad target entries |
| Best for | Stable environments | Dynamic environments |
| Refresh interval | N/A | Configurable (default 5m) |

### Directory Structure Comparison

**Option 1:**

```
/etc/prometheus/scrape_configs/
├── node_exporter.yml           # Contains job config AND targets
├── process_exporter.yml
└── tomcat.yml
```

**Option 2:**

```
/etc/prometheus/scrape_configs/
├── node_exporter.yml           # Contains job config only
├── node_exporter_targets.yml   # Contains targets only (auto-reload)
├── process_exporter.yml
├── process_exporter_targets.yml
├── tomcat.yml
└── tomcat_targets.yml
```

### When to Use Each Option

**Use Option 1 when:**

- Your infrastructure is stable
- Targets rarely change
- You prefer fewer files
- Manual reload is acceptable

**Use Option 2 when:**

- Targets change frequently
- You want zero-downtime target updates
- Automation tools manage your targets
- Different teams manage different target lists

---

## Validation and Reload

### Validate Configuration

```bash
promtool check config /etc/prometheus/prometheus.yml
```

### Reload Prometheus

Choose one of the following methods:

```bash
# Method 1: Systemd reload
sudo systemctl reload prometheus

# Method 2: HTTP API
curl -X POST http://localhost:9090/-/reload

# Method 3: Kill signal
sudo kill -HUP $(pgrep prometheus)
```

### Check Service Status

```bash
sudo systemctl status prometheus --no-pager
```

---

## Verification Commands

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

### View Loaded Configuration

```bash
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | head -50
```

### Check Prometheus Logs

```bash
sudo journalctl -u prometheus -n 100 --no-pager
```

### Check file_sd_configs Errors (Option 2)

```bash
sudo journalctl -u prometheus -n 100 | grep -i "file_sd\|error"
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

### Targets Not Appearing (Option 2)

```bash
# Check file permissions
ls -la /etc/prometheus/scrape_configs/

# Check for YAML errors in target files
python3 -c "import yaml; yaml.safe_load(open('/etc/prometheus/scrape_configs/node_exporter_targets.yml'))"

# Check Prometheus logs for file_sd errors
sudo journalctl -u prometheus -n 100 | grep -i "file_sd\|error"
```

### file_sd_configs Error Handling

When using Option 2, if a target file has errors:

| Scenario | Prometheus Behavior |
|----------|---------------------|
| Invalid YAML syntax | Ignores the broken file, keeps last valid config |
| Target file deleted | Removes those targets from scraping |
| Empty target file | Treats as zero targets (no error) |
| File permission denied | Logs error, continues with existing targets |
| Invalid target format | Skips invalid entries, loads valid ones |

---

## Best Practices

1. **Always validate before reload**: Run `promtool check config` before applying changes.

2. **Backup configurations**: Create backups before making changes.

3. **Use consistent labels**: Maintain consistent label naming across all configurations.

4. **Version control**: Keep configurations in a Git repository.

5. **Set appropriate refresh intervals**: For Option 2, balance between responsiveness and resource usage.

6. **Monitor configuration health**: Watch `prometheus_config_last_reload_successful` metric.

7. **Document your setup**: Maintain documentation for your configuration structure.

8. **Test in staging first**: Validate changes in non-production environment.

9. **Use meaningful file names**: Name files clearly to indicate their purpose.

10. **Separate by environment**: Consider separate target files for production and staging.

---

## References

- [Prometheus Configuration Documentation](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Prometheus File-Based Service Discovery](https://prometheus.io/docs/guides/file-sd/)
- [Prometheus GitHub Repository](https://github.com/prometheus/prometheus)

---
