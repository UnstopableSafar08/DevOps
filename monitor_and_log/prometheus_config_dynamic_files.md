# Splitting Prometheus Configuration into Multiple Files

A comprehensive guide on how to organize Prometheus scrape configurations into separate modular files for better maintainability and scalability.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Directory Structure](#directory-structure)
- [Configuration Files](#configuration-files)
  - [Main Configuration](#main-configuration)
  - [Node Exporter Configuration](#node-exporter-configuration)
  - [Process Exporter Configuration](#process-exporter-configuration)
  - [Tomcat JMX Exporter Configuration](#tomcat-jmx-exporter-configuration)
- [Implementation Steps](#implementation-steps)
- [Validation and Reload](#validation-and-reload)
- [Verification](#verification)
- [Adding New Exporters](#adding-new-exporters)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Overview

As your Prometheus monitoring setup grows, managing all scrape configurations in a single `prometheus.yml` file becomes difficult. Prometheus 2.43+ introduced `scrape_config_files` directive, which allows you to split configurations into multiple files.

**Note:** Prometheus 3.x requires a slightly different file format where each external file must contain a `scrape_configs` key wrapping the job definitions.

### Benefits

- Modular and organized configuration
- Easier version control and change tracking
- Team-friendly (different teams can manage different files)
- Simplified debugging and maintenance
- Scalable for large environments

## Prerequisites

- Prometheus version 2.43 or higher (this guide uses Prometheus 3.x syntax)
- Root or sudo access to the Prometheus server
- Basic understanding of YAML syntax

### Check Prometheus Version

```bash
prometheus --version
```

Expected output:

```
prometheus, version 3.x.x (branch: HEAD, revision: ...)
```

## Directory Structure

```
/etc/prometheus/
├── prometheus.yml
└── scrape_configs/
    ├── node_exporter.yml
    ├── process_exporter.yml
    ├── tomcat.yml
    └── blackbox_exporter.yml    # (optional)
```

## Configuration Files

### Main Configuration

**File:** `/etc/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 10s
  evaluation_interval: 10s

  external_labels:
    cluster: 'production'
    region: 'us-east-1'

# Load scrape configurations from separate files
scrape_config_files:
  - "scrape_configs/*.yml"

# Prometheus self-monitoring
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          env: 'monitoring'
          module: 'prometheus'
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

### Tomcat JMX Exporter Configuration

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

## Implementation Steps

### Step 1: Backup Current Configuration

```bash
sudo cp /etc/prometheus/prometheus.yml /etc/prometheus/prometheus.yml.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 2: Create Directory Structure

```bash
sudo mkdir -p /etc/prometheus/scrape_configs
```

### Step 3: Create Node Exporter Configuration

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

### Step 4: Create Process Exporter Configuration

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

### Step 5: Create Tomcat Configuration

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

### Step 6: Create Main Configuration

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  scrape_interval: 10s
  evaluation_interval: 10s

  external_labels:
    cluster: 'production'
    region: 'us-east-1'

scrape_config_files:
  - "scrape_configs/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          env: 'monitoring'
          module: 'prometheus'
EOF
```

### Step 7: Set Permissions

```bash
sudo chown -R prometheus:prometheus /etc/prometheus/
sudo chmod 644 /etc/prometheus/prometheus.yml
sudo chmod 644 /etc/prometheus/scrape_configs/*.yml
sudo chmod 755 /etc/prometheus/scrape_configs/
```

## Validation and Reload

### Validate Configuration

```bash
promtool check config /etc/prometheus/prometheus.yml
```

Expected output:

```
Checking /etc/prometheus/prometheus.yml
  SUCCESS: X scrape configs found
```

### Reload Prometheus

Choose one of the following methods:

**Method 1: Systemd Reload**

```bash
sudo systemctl reload prometheus
```

**Method 2: HTTP API**

```bash
curl -X POST http://localhost:9090/-/reload
```

**Method 3: Kill Signal**

```bash
sudo kill -HUP $(pgrep prometheus)
```

### Check Service Status

```bash
sudo systemctl status prometheus --no-pager
```

## Verification

### List Active Targets

```bash
curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job) - \(.labels.instance) - \(.health)"'
```

### Count Targets by Job

```bash
curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets | group_by(.labels.job) | .[] | "\(.[0].labels.job): \(length) targets"'
```

### Check for Down Targets

```bash
curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | select(.health=="down") | "\(.labels.job) - \(.labels.instance) - \(.lastError)"'
```

### View Loaded Configuration

```bash
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | head -50
```

## Adding New Exporters

To add a new exporter, create a new file in the `scrape_configs` directory.

### Example: Adding Blackbox Exporter

```bash
sudo tee /etc/prometheus/scrape_configs/blackbox_exporter.yml > /dev/null <<'EOF'
scrape_configs:
  - job_name: 'blackbox_http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://example.com
          - https://api.example.com
          - https://app.example.com
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9115

  - job_name: 'blackbox_icmp'
    metrics_path: /probe
    params:
      module: [icmp]
    static_configs:
      - targets:
          - 192.168.1.1
          - 192.168.1.254
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9115
EOF
```

Then validate and reload:

```bash
promtool check config /etc/prometheus/prometheus.yml
sudo systemctl reload prometheus
```

## Troubleshooting

### Common Errors

#### Error: cannot unmarshal !!seq into config.ScrapeConfigs

This error occurs in Prometheus 3.x when the external file format is incorrect.

**Wrong format:**

```yaml
- job_name: 'node_exporter'
  static_configs:
    - targets: ['192.168.1.10:9100']
```

**Correct format for Prometheus 3.x:**

```yaml
scrape_configs:
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['192.168.1.10:9100']
```

#### Error: YAML syntax error

Check for:

- Incorrect indentation (use spaces, not tabs)
- Missing colons after keys
- Improper quoting of strings

Validate YAML syntax:

```bash
python3 -c "import yaml; yaml.safe_load(open('/etc/prometheus/scrape_configs/node_exporter.yml'))"
```

#### Configuration not loading after reload

Check Prometheus logs:

```bash
sudo journalctl -u prometheus -n 100 --no-pager
```

### Debugging Commands

```bash
# Check file permissions
ls -la /etc/prometheus/scrape_configs/

# Check for hidden characters
file /etc/prometheus/scrape_configs/*.yml

# View first 5 lines of each config
head -n 5 /etc/prometheus/scrape_configs/*.yml

# Check for tabs in files
grep -P '\t' /etc/prometheus/scrape_configs/*.yml
```

## Best Practices

1. **Naming Convention**: Use descriptive file names that indicate the exporter type (e.g., `node_exporter.yml`, `mysql_exporter.yml`).

2. **Consistent Labels**: Use consistent label names across all configurations (`env`, `module`, `node`, etc.).

3. **Version Control**: Keep all configuration files in a Git repository for tracking changes.

4. **Backup Before Changes**: Always backup configurations before making changes.

5. **Validate Before Reload**: Always run `promtool check config` before reloading Prometheus.

6. **Documentation**: Add comments in YAML files to explain the purpose of each job.

7. **Group Related Jobs**: Keep related scrape jobs in the same file (e.g., all Kafka-related exporters in `kafka.yml`).

8. **Testing**: Test configuration changes in a staging environment before applying to production.

## Version Compatibility

| Prometheus Version | File Format | Directive |
|---|---|---|
| 2.43 - 2.x | Direct list starting with `- job_name:` | `scrape_config_files` |
| 3.x | Wrapped with `scrape_configs:` key | `scrape_config_files` |
| All versions | N/A | `file_sd_configs` (for targets only) |

## References

- [Prometheus Configuration Documentation](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Prometheus GitHub Repository](https://github.com/prometheus/prometheus)
- [Prometheus Exporters](https://prometheus.io/docs/instrumenting/exporters/)

---
