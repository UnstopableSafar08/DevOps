# Elasticsearch Index Cleanup Script - Complete Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Configuration Options](#configuration-options)
3. [Usage Examples](#usage-examples)
4. [Security Best Practices](#security-best-practices)
5. [Automation with Cron](#automation-with-cron)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Quick Start

### 1. Download and Setup
```bash
# Make the script executable
chmod +x elasticsearch_index_cleanup.sh

# View help
./elasticsearch_index_cleanup.sh --help
```

### 2. Configure Credentials
```bash
# Option A: Environment variable (recommended)
export ES_PASS="your_password"

# Option B: Command line argument
./elasticsearch_index_cleanup.sh --password="your_password" --dry-run

# Option C: Edit the script directly (less secure)
# Change: ES_PASS="${ES_PASS:-CHANGE_ME}"
# To:     ES_PASS="${ES_PASS:-your_actual_password}"
```

### 3. Test First
```bash
# Always run dry-run first to preview what will be deleted
./elasticsearch_index_cleanup.sh --dry-run
```

### 4. Execute
```bash
# If dry-run looks good, run for real
./elasticsearch_index_cleanup.sh
```

---

## Configuration Options

### Command Line Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--dry-run` | Preview deletions without executing | `--dry-run` |
| `--password=<pass>` | Elasticsearch password | `--password="mypass123"` |
| `--retention-days=<n>` | Days to retain (default: 2) | `--retention-days=7` |
| `--pattern=<pattern>` | Index pattern to match | `--pattern=".ds-metricbeat-*"` |
| `--verbose` | Enable debug output | `--verbose` |
| `--help` | Show help message | `--help` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_URL` | `https://localhost:9200` | Elasticsearch URL |
| `ES_USER` | `elastic` | Elasticsearch username |
| `ES_PASS` | `CHANGE_ME` | Elasticsearch password |
| `INDEX_PATTERN` | `.ds-heartbeat-8.11.0-*` | Index pattern |
| `RETENTION_DAYS` | `2` | Days to retain |

---

## Usage Examples

### Example 1: Basic Dry Run
```bash
export ES_PASS="mypassword"
./elasticsearch_index_cleanup.sh --dry-run
```

**Output:**
```
╔═══════════════════════════════════════════╗
║  Elasticsearch Index Cleanup Script      ║
╚═══════════════════════════════════════════╝

⚠ DRY-RUN MODE - No indices will be deleted
[INFO] Configuration:
[INFO]   Elasticsearch URL: https://localhost:9200
[INFO]   Username: elastic
[INFO]   Index pattern: .ds-heartbeat-8.11.0-*
[INFO]   Retention days: 2
[INFO]   Cutoff date: 2026.02.14

[INFO] Testing Elasticsearch connection...
[SUCCESS] Connected to Elasticsearch

[INFO] Fetching indices matching pattern: .ds-heartbeat-8.11.0-*
[SUCCESS] Found 5 indices

[DRY-RUN] Would delete: .ds-heartbeat-8.11.0-2026.02.10-000001 (2026.02.10)
[DRY-RUN] Would delete: .ds-heartbeat-8.11.0-2026.02.11-000002 (2026.02.11)

========================================
        CLEANUP SUMMARY
========================================
Total indices processed: 5
Would delete:            2
Kept (newer):            3
Skipped (no date):       0
========================================
```

### Example 2: Delete MetricBeat Indices Older Than 7 Days
```bash
ES_PASS="secret" ./elasticsearch_index_cleanup.sh \
  --pattern=".ds-metricbeat-8.11.0-*" \
  --retention-days=7
```

### Example 3: Multiple Patterns (via script wrapper)
```bash
#!/bin/bash
# cleanup_all.sh

PATTERNS=(
    ".ds-heartbeat-8.11.0-*"
    ".ds-metricbeat-8.11.0-*"
    ".ds-filebeat-8.11.0-*"
)

for pattern in "${PATTERNS[@]}"; do
    echo "Processing pattern: $pattern"
    ./elasticsearch_index_cleanup.sh --pattern="$pattern" --retention-days=7
    echo ""
done
```

### Example 4: Verbose Mode for Debugging
```bash
./elasticsearch_index_cleanup.sh --dry-run --verbose
```

### Example 5: Different Elasticsearch Cluster
```bash
ES_URL="https://prod-cluster.example.com:9200" \
ES_USER="admin" \
ES_PASS="admin_password" \
./elasticsearch_index_cleanup.sh --retention-days=30
```

---

## Security Best Practices

### 1. Use Password File (Most Secure for Automation)
```bash
# Create password file with restricted permissions
echo "your_secure_password" > /etc/elasticsearch/.es_password
chmod 600 /etc/elasticsearch/.es_password
chown root:root /etc/elasticsearch/.es_password

# Use in script
export ES_PASS=$(cat /etc/elasticsearch/.es_password)
./elasticsearch_index_cleanup.sh --dry-run
```

### 2. Use HashiCorp Vault
```bash
# Fetch password from Vault
export ES_PASS=$(vault kv get -field=password secret/elasticsearch/cleanup)
./elasticsearch_index_cleanup.sh
```

### 3. Use AWS Secrets Manager
```bash
# Fetch from AWS Secrets Manager
export ES_PASS=$(aws secretsmanager get-secret-value \
  --secret-id elasticsearch/password \
  --query SecretString \
  --output text)
./elasticsearch_index_cleanup.sh
```

### 4. Use Environment File
```bash
# Create .env file
cat > /etc/elasticsearch/cleanup.env <<EOF
ES_URL=https://localhost:9200
ES_USER=elastic
ES_PASS=your_password
RETENTION_DAYS=7
EOF

chmod 600 /etc/elasticsearch/cleanup.env

# Source and run
source /etc/elasticsearch/cleanup.env
./elasticsearch_index_cleanup.sh
```

### 5. Use TLS Certificates Instead of -k Flag

Update the script to use proper certificates:
```bash
# In the script, replace:
# curl -k ...
# With:
# curl --cacert /path/to/ca.crt ...

# Or set environment variable
export CURL_CA_BUNDLE=/path/to/ca-bundle.crt
```

---

## Automation with Cron

### Example 1: Daily Cleanup at 2 AM
```bash
# Edit crontab
crontab -e

# Add this line
0 2 * * * ES_PASS=$(cat /etc/elasticsearch/.es_password) /usr/local/bin/elasticsearch_index_cleanup.sh >> /var/log/es_cleanup.log 2>&1
```

### Example 2: Weekly Cleanup on Sundays
```bash
# Run every Sunday at 3 AM
0 3 * * 0 ES_PASS=$(cat /etc/elasticsearch/.es_password) /usr/local/bin/elasticsearch_index_cleanup.sh --retention-days=30 >> /var/log/es_cleanup.log 2>&1
```

### Example 3: Cleanup Script with Logging and Notifications
```bash
#!/bin/bash
# /usr/local/bin/es_cleanup_wrapper.sh

LOGFILE="/var/log/elasticsearch/cleanup_$(date +%Y%m%d_%H%M%S).log"
ES_PASS=$(cat /etc/elasticsearch/.es_password)

{
    echo "=== Cleanup started at $(date) ==="
    
    export ES_PASS
    /usr/local/bin/elasticsearch_index_cleanup.sh --retention-days=7
    
    EXIT_CODE=$?
    
    echo "=== Cleanup finished at $(date) with exit code: ${EXIT_CODE} ==="
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Cleanup failed!" | mail -s "Elasticsearch Cleanup Failed" admin@example.com
    fi
    
} >> "$LOGFILE" 2>&1

# Keep only last 30 days of logs
find /var/log/elasticsearch/ -name "cleanup_*.log" -mtime +30 -delete
```

### Example 4: Systemd Timer (Alternative to Cron)
```bash
# Create service file: /etc/systemd/system/es-cleanup.service
cat > /etc/systemd/system/es-cleanup.service <<'EOF'
[Unit]
Description=Elasticsearch Index Cleanup
After=network.target

[Service]
Type=oneshot
User=elasticsearch
EnvironmentFile=/etc/elasticsearch/cleanup.env
ExecStart=/usr/local/bin/elasticsearch_index_cleanup.sh --retention-days=7
StandardOutput=journal
StandardError=journal
EOF

# Create timer file: /etc/systemd/system/es-cleanup.timer
cat > /etc/systemd/system/es-cleanup.timer <<'EOF'
[Unit]
Description=Run Elasticsearch cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable es-cleanup.timer
systemctl start es-cleanup.timer

# Check status
systemctl list-timers es-cleanup.timer
```

---

## Troubleshooting

### Problem 1: Authentication Failed (401)
```
[ERROR] Authentication failed (HTTP 401)
```

**Solutions:**
1. Verify password is correct
2. Check if user has necessary permissions
3. Verify Elasticsearch is using the expected authentication method

```bash
# Test authentication manually
curl -k -u elastic:your_password https://localhost:9200/_cluster/health

# If using API key instead
curl -k -H "Authorization: ApiKey YOUR_API_KEY" https://localhost:9200/_cluster/health
```

### Problem 2: Connection Failed (000)
```
[ERROR] Connection failed - cannot reach https://localhost:9200
```

**Solutions:**
1. Check if Elasticsearch is running: `systemctl status elasticsearch`
2. Verify URL is correct
3. Check firewall rules: `netstat -tlnp | grep 9200`
4. Check Elasticsearch logs: `tail -f /var/log/elasticsearch/elasticsearch.log`

### Problem 3: SSL Certificate Issues
```
curl: (60) SSL certificate problem
```

**Solutions:**
```bash
# Option 1: Use proper CA certificate
curl --cacert /path/to/ca.crt -u elastic:password https://localhost:9200/_cluster/health

# Option 2: Disable certificate verification (not recommended for production)
# The script already uses -k flag

# Option 3: Add CA to system trust store
sudo cp /path/to/ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

### Problem 4: No Indices Found
```
[WARN] No indices found matching pattern: .ds-heartbeat-8.11.0-*
```

**Solutions:**
```bash
# List all indices to find the correct pattern
curl -k -u elastic:password "https://localhost:9200/_cat/indices?v"

# Test pattern
curl -k -u elastic:password "https://localhost:9200/_cat/indices/.ds-heartbeat-*?v"

# Update script with correct pattern
./elasticsearch_index_cleanup.sh --pattern=".ds-heartbeat-8.12.0-*" --dry-run
```

### Problem 5: Permission Denied
```
[ERROR] Failed to delete index (HTTP 403)
```

**Solutions:**
1. Check user permissions in Elasticsearch
2. Verify user has `delete_index` privilege

```bash
# Check user privileges
curl -k -u elastic:password "https://localhost:9200/_security/user/elastic"

# Create role with delete privileges
curl -k -u elastic:password -X POST "https://localhost:9200/_security/role/index_cleanup" \
  -H 'Content-Type: application/json' -d'
{
  "indices": [
    {
      "names": [ ".ds-heartbeat-*", ".ds-metricbeat-*" ],
      "privileges": [ "delete_index", "view_index_metadata" ]
    }
  ]
}'
```

---

## Advanced Usage

### Using ILM (Index Lifecycle Management) - Better Alternative

Instead of using this script, consider using Elasticsearch ILM:

```bash
# Create ILM policy
curl -k -u elastic:password -X PUT "https://localhost:9200/_ilm/policy/cleanup_policy" \
  -H 'Content-Type: application/json' -d'
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_age": "1d",
            "max_size": "50gb"
          }
        }
      },
      "delete": {
        "min_age": "7d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'

# Apply to index template
curl -k -u elastic:password -X PUT "https://localhost:9200/_index_template/heartbeat_template" \
  -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["heartbeat-*"],
  "template": {
    "settings": {
      "index.lifecycle.name": "cleanup_policy"
    }
  }
}'
```

### Monitoring Script Execution

```bash
# Add to script for Prometheus monitoring
cat >> /var/lib/node_exporter/textfile_collector/es_cleanup.prom <<EOF
# HELP es_cleanup_deleted_indices Number of indices deleted
# TYPE es_cleanup_deleted_indices gauge
es_cleanup_deleted_indices{pattern="${INDEX_PATTERN}"} ${deleted_count}

# HELP es_cleanup_last_run_timestamp Last cleanup run timestamp
# TYPE es_cleanup_last_run_timestamp gauge
es_cleanup_last_run_timestamp $(date +%s)
EOF
```

### Integration with Slack/Email Notifications

```bash
# Add function to script
send_slack_notification() {
    local message="$1"
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"${message}\"}" \
      https://hooks.slack.com/services/YOUR/WEBHOOK/URL
}

# Use in main function
if [[ $deleted_count -gt 0 ]]; then
    send_slack_notification " Elasticsearch cleanup: Deleted ${deleted_count} indices"
fi
```

---

## Performance Optimization

For large deployments with thousands of indices:

```bash
# Batch deletion using _bulk API
# Modify script to collect index names and delete in batches

delete_indices_bulk() {
    local indices=("$@")
    local body=""
    
    for index in "${indices[@]}"; do
        body+="{\"delete\":{\"_index\":\"${index}\"}}\n"
    done
    
    echo -e "$body" | curl -k -s -u "${ES_USER}:${ES_PASS}" \
      -X POST "${ES_URL}/_bulk" \
      -H 'Content-Type: application/x-ndjson' \
      --data-binary @-
}
```

---

## Support and Contributing

For issues or questions:
1. Check Elasticsearch logs: `/var/log/elasticsearch/`
2. Run with `--verbose` flag for detailed output
3. Test individual curl commands manually
4. Check Elasticsearch documentation: https://www.elastic.co/guide/

---

**Version:** 2.0  
**Last Updated:** February 2026  
**Compatibility:** Elasticsearch 7.x, 8.x
