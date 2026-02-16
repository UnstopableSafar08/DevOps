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

Main script;
```bash
#!/usr/bin/env bash
#===============================================================================
# Script Name: elasticsearch_index_cleanup.sh
# Description: Delete Elasticsearch indices older than specified retention period
# Author: DevOps Team
# Version: 2.1
# Usage: ./elasticsearch_index_cleanup.sh [OPTIONS]
# Options:
#   --dry-run              : Preview what would be deleted without actually deleting
#   --password=<pass>      : Provide password via command line
#   --retention-days=<n>   : Override default retention days
#   --pattern=<pattern>    : Override default index pattern
#   --help                 : Show this help message
#===============================================================================

set -euo pipefail

############################################
# DEFAULT CONFIGURATION
############################################
ES_URL="${ES_URL:-https://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASS="${ES_PASS:-CHANGE_ME}"
INDEX_PATTERN="${INDEX_PATTERN:-.ds-heartbeat-8.11.0-*}"
RETENTION_DAYS="${RETENTION_DAYS:-2}"

# Optional: Use certificate bundle instead of -k
# ES_CACERT="/path/to/ca.crt"

############################################
# COLORS
############################################
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m"

############################################
# FLAGS
############################################
DRY_RUN=false
VERBOSE=false

############################################
# FUNCTIONS
############################################

show_help() {
    cat << EOF
${BOLD}Elasticsearch Index Cleanup Script${NC}

${BOLD}USAGE:${NC}
    $0 [OPTIONS]

${BOLD}OPTIONS:${NC}
    --dry-run                    Preview deletions without executing
    --password=<password>        Elasticsearch password (overrides ES_PASS)
    --retention-days=<days>      Days to retain (default: ${RETENTION_DAYS})
    --pattern=<pattern>          Index pattern (default: ${INDEX_PATTERN})
    --verbose                    Enable verbose output
    --help                       Show this help message

${BOLD}ENVIRONMENT VARIABLES:${NC}
    ES_URL                       Elasticsearch URL (default: https://localhost:9200)
    ES_USER                      Elasticsearch username (default: elastic)
    ES_PASS                      Elasticsearch password
    INDEX_PATTERN                Index pattern to match
    RETENTION_DAYS               Days to retain indices

${BOLD}EXAMPLES:${NC}
    # Dry run with default settings
    $0 --dry-run

    # Delete indices older than 7 days
    $0 --retention-days=7

    # Use specific pattern and password
    $0 --pattern=".ds-metricbeat-*" --password="mypass"

    # Using environment variables
    ES_PASS="secret" $0 --dry-run

${BOLD}SECURITY:${NC}
    For production use, avoid passing passwords via command line.
    Use environment variables or password files:
    
    export ES_PASS=\$(cat /secure/path/.es_password)
    $0 --dry-run

EOF
    exit 0
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if $VERBOSE; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

check_dependencies() {
    local missing_deps=()
    
    for cmd in curl date; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        log_warn "jq is not installed. JSON error messages may not be parsed properly."
    fi
}

validate_config() {
    if [[ "${ES_PASS}" == "CHANGE_ME" ]]; then
        log_error "Password not configured!"
        echo ""
        echo "Please set password using one of these methods:"
        echo "  1. Environment variable: export ES_PASS='your_password'"
        echo "  2. Command line: $0 --password='your_password'"
        echo "  3. Edit ES_PASS in the script"
        echo ""
        exit 1
    fi
    
    if [[ ! "${RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
        log_error "RETENTION_DAYS must be a positive integer: ${RETENTION_DAYS}"
        exit 1
    fi
    
    if [[ "${RETENTION_DAYS}" -lt 1 ]]; then
        log_error "RETENTION_DAYS must be at least 1"
        exit 1
    fi
}

test_elasticsearch_connection() {
    log_info "Testing Elasticsearch connection..."
    log_verbose "URL: ${ES_URL}"
    log_verbose "User: ${ES_USER}"
    
    local response
    local http_code
    
    response=$(curl -k -s -w "\n%{http_code}" \
        -u "${ES_USER}:${ES_PASS}" \
        "${ES_URL}/_cluster/health" 2>&1)
    
    http_code=$(echo "$response" | tail -n1)
    
    case "${http_code}" in
        200)
            log_success "Connected to Elasticsearch"
            if command -v jq >/dev/null 2>&1; then
                local cluster_name=$(echo "$response" | sed '$d' | jq -r '.cluster_name // "unknown"')
                local status=$(echo "$response" | sed '$d' | jq -r '.status // "unknown"')
                log_verbose "Cluster: ${cluster_name}, Status: ${status}"
            fi
            return 0
            ;;
        401)
            log_error "Authentication failed (HTTP 401)"
            log_error "Please check ES_USER and ES_PASS credentials"
            return 1
            ;;
        000)
            log_error "Connection failed - cannot reach ${ES_URL}"
            log_error "Please check if Elasticsearch is running and URL is correct"
            return 1
            ;;
        *)
            log_error "Unexpected response (HTTP ${http_code})"
            echo "$response" | sed '$d'
            return 1
            ;;
    esac
}

fetch_indices() {
    local temp_file
    temp_file=$(mktemp)
    trap 'rm -f ${temp_file}' RETURN
    
    log_info "Fetching indices matching pattern: ${INDEX_PATTERN}"
    
    local response
    response=$(curl -k -s -w "\n%{http_code}" -o "${temp_file}" \
        -u "${ES_USER}:${ES_PASS}" \
        "${ES_URL}/_cat/indices/${INDEX_PATTERN}?h=index,status,health,docs.count,store.size&s=index")
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "${http_code}" != "200" ]]; then
        log_error "Failed to fetch indices (HTTP ${http_code})"
        if command -v jq >/dev/null 2>&1 && [[ -s "${temp_file}" ]]; then
            jq -r '.error.reason // .' "${temp_file}" 2>/dev/null || cat "${temp_file}"
        else
            cat "${temp_file}"
        fi
        return 1
    fi
    
    cat "${temp_file}"
}

extract_date_from_index() {
    local index="$1"
    
    # Try to match YYYY.MM.DD pattern
    if [[ "${index}" =~ ([0-9]{4}\.[0-9]{2}\.[0-9]{2}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    
    # Try to match YYYY-MM-DD pattern
    if [[ "${index}" =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        # Convert to YYYY.MM.DD for consistent comparison
        echo "${BASH_REMATCH[1]///-/.}"
        return 0
    fi
    
    return 1
}

list_found_indices() {
    local indices_data="$1"
    local cutoff_date="$2"
    
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  FOUND INDICES${NC}"
    echo -e "${BOLD}========================================${NC}"
    printf "%-50s %-15s %-10s\n" "INDEX NAME" "DATE" "ACTION"
    echo "----------------------------------------"
    
    while IFS= read -r line; do
        # Skip empty lines
        [[ -z "${line}" ]] && continue
        
        # Extract index name (first column)
        local index
        index=$(echo "$line" | awk '{print $1}')
        
        # Extract date from index name
        local index_date
        local action
        if ! index_date=$(extract_date_from_index "${index}"); then
            index_date="NO_DATE"
            action="${YELLOW}SKIP${NC}"
        elif [[ "${index_date}" < "${cutoff_date}" ]]; then
            action="${RED}DELETE${NC}"
        else
            action="${GREEN}KEEP${NC}"
        fi
        
        printf "%-50s %-15s " "${index}" "${index_date}"
        echo -e "${action}"
        
    done <<< "${indices_data}"
    
    echo "----------------------------------------"
    echo ""
}

delete_index() {
    local index="$1"
    
    local response
    response=$(curl -k -s -w "\n%{http_code}" -o /dev/null \
        -u "${ES_USER}:${ES_PASS}" \
        -X DELETE "${ES_URL}/${index}")
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "${http_code}" == "200" ]]; then
        log_success "Deleted: ${index}"
        return 0
    else
        log_error "Failed to delete ${index} (HTTP ${http_code})"
        return 1
    fi
}

process_indices() {
    local indices_data="$1"
    local cutoff_date="$2"
    
    local total_count=0
    local deleted_count=0
    local skipped_count=0
    local kept_count=0
    local error_count=0
    
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  PROCESSING INDICES${NC}"
    echo -e "${BOLD}========================================${NC}"
    
    while IFS= read -r line; do
        # Skip empty lines
        [[ -z "${line}" ]] && continue
        
        ((total_count++))
        
        # Extract index name (first column)
        local index
        index=$(echo "$line" | awk '{print $1}')
        
        log_verbose "Processing: ${index}"
        
        # Extract date from index name
        local index_date
        if ! index_date=$(extract_date_from_index "${index}"); then
            log_warn "Skipping (no valid date found): ${index}"
            ((skipped_count++))
            continue
        fi
        
        log_verbose "  Date extracted: ${index_date}"
        log_verbose "  Cutoff date: ${cutoff_date}"
        
        # Compare dates (lexicographic comparison works for YYYY.MM.DD format)
        if [[ "${index_date}" < "${cutoff_date}" ]]; then
            if $DRY_RUN; then
                echo -e "${GREEN}[DRY-RUN]${NC} Would delete: ${index} (${index_date})"
                ((deleted_count++))
            else
                log_info "Deleting: ${index} (${index_date})"
                if delete_index "${index}"; then
                    ((deleted_count++))
                    # Small delay to avoid overwhelming Elasticsearch
                    sleep 0.3
                else
                    ((error_count++))
                fi
            fi
        else
            log_verbose "  Keeping (newer than cutoff): ${index} (${index_date})"
            ((kept_count++))
        fi
        
    done <<< "${indices_data}"
    
    # Return counts as space-separated string
    echo "${total_count} ${deleted_count} ${kept_count} ${skipped_count} ${error_count}"
}

print_summary() {
    local total=$1
    local deleted=$2
    local kept=$3
    local skipped=$4
    local errors=$5
    
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}        CLEANUP SUMMARY${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo -e "Total indices processed: ${CYAN}${total}${NC}"
    
    if $DRY_RUN; then
        echo -e "Would delete:            ${GREEN}${deleted}${NC}"
    else
        echo -e "Deleted:                 ${GREEN}${deleted}${NC}"
    fi
    
    echo -e "Kept (newer):            ${BLUE}${kept}${NC}"
    echo -e "Skipped (no date):       ${YELLOW}${skipped}${NC}"
    
    if [[ $errors -gt 0 ]]; then
        echo -e "Errors:                  ${RED}${errors}${NC}"
    fi
    
    echo -e "${BOLD}========================================${NC}"
}

############################################
# ARGUMENT PARSING
############################################
for arg in "$@"; do
    case "$arg" in
        --help|-h)
            show_help
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --verbose|-v)
            VERBOSE=true
            ;;
        --password=*)
            ES_PASS="${arg#*=}"
            ;;
        --retention-days=*)
            RETENTION_DAYS="${arg#*=}"
            ;;
        --pattern=*)
            INDEX_PATTERN="${arg#*=}"
            ;;
        *)
            log_error "Unknown argument: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

############################################
# MAIN EXECUTION
############################################
main() {
    echo "========================================"
    echo "  Elasticsearch Index Cleanup Script"
    echo "========================================"
    echo ""
    
    # Pre-flight checks
    check_dependencies
    validate_config
    
    # Display configuration
    if $DRY_RUN; then
        echo -e "${YELLOW}${BOLD}DRY-RUN MODE - No indices will be deleted${NC}"
    fi
    
    log_info "Configuration:"
    log_info "  Elasticsearch URL: ${ES_URL}"
    log_info "  Username: ${ES_USER}"
    log_info "  Index pattern: ${INDEX_PATTERN}"
    log_info "  Retention days: ${RETENTION_DAYS}"
    
    # Calculate cutoff date
    local cutoff_date
    cutoff_date=$(date -d "-${RETENTION_DAYS} days" +"%Y.%m.%d")
    log_info "  Cutoff date: ${cutoff_date}"
    log_info "  (Indices older than this will be deleted)"
    echo ""
    
    # Test connection
    if ! test_elasticsearch_connection; then
        exit 1
    fi
    echo ""
    
    # Fetch indices
    local indices_data
    if ! indices_data=$(fetch_indices); then
        exit 1
    fi
    
    if [[ -z "${indices_data}" ]]; then
        log_warn "No indices found matching pattern: ${INDEX_PATTERN}"
        exit 0
    fi
    
    local index_count
    index_count=$(echo "${indices_data}" | wc -l)
    log_success "Found ${index_count} indices"
    
    # List all found indices
    list_found_indices "${indices_data}" "${cutoff_date}"
    
    # Process indices
    local counts
    counts=$(process_indices "${indices_data}" "${cutoff_date}")
    
    # Parse counts
    local total deleted kept skipped errors
    read -r total deleted kept skipped errors <<< "${counts}"
    
    # Print summary
    print_summary "${total}" "${deleted}" "${kept}" "${skipped}" "${errors}"
    
    # Exit with error if there were failures
    if [[ ${errors:-0} -gt 0 ]] && [[ $DRY_RUN == false ]]; then
        exit 1
    fi
    
    exit 0
}

# Run main function
main
```

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

**Output:--dry-run**
```bash
[root@elk-monitoring script]# ./elasticsearch_index_cleanup.sh --dry-run
========================================
  Elasticsearch Index Cleanup Script
========================================

[WARN] jq is not installed. JSON error messages may not be parsed properly.
DRY-RUN MODE - No indices will be deleted
[INFO] Configuration:
[INFO]   Elasticsearch URL: https://localhost:9200
[INFO]   Username: elastic
[INFO]   Index pattern: .ds-heartbeat-8.11.0-*
[INFO]   Retention days: 2
[INFO]   Cutoff date: 2026.02.14
[INFO]   (Indices older than this will be deleted)

[INFO] Testing Elasticsearch connection...
[SUCCESS] Connected to Elasticsearch

[SUCCESS] Found 15 indices

========================================
  FOUND INDICES
========================================
INDEX NAME                                         DATE            ACTION
----------------------------------------
[INFO]                                  NO_DATE         SKIP
.ds-heartbeat-8.11.0-2026.02.10-001843             2026.02.10      DELETE
.ds-heartbeat-8.11.0-2026.02.10-001856             2026.02.10      DELETE
.ds-heartbeat-8.11.0-2026.02.10-001857             2026.02.10      DELETE
.ds-heartbeat-8.11.0-2026.02.11-001858             2026.02.11      DELETE
.ds-heartbeat-8.11.0-2026.02.11-001859             2026.02.11      DELETE
.ds-heartbeat-8.11.0-2026.02.11-001860             2026.02.11      DELETE
.ds-heartbeat-8.11.0-2026.02.12-001861             2026.02.12      DELETE
.ds-heartbeat-8.11.0-2026.02.12-001862             2026.02.12      DELETE
.ds-heartbeat-8.11.0-2026.02.12-001863             2026.02.12      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001864             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001865             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001866             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001867             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.15-001868             2026.02.15      KEEP
----------------------------------------


========================================
        CLEANUP SUMMARY
========================================
Total indices processed:
Would delete:
Kept (newer):
Skipped (no date):
========================================
[root@elk-monitoring script]#
[root@elk-monitoring script]#
```

**Output:clean-indices**
```bash
[root@elk-monitoring script]# ./elasticsearch_index_cleanup.sh
========================================
  Elasticsearch Index Cleanup Script
========================================

[WARN] jq is not installed. JSON error messages may not be parsed properly.
[INFO] Configuration:
[INFO]   Elasticsearch URL: https://localhost:9200
[INFO]   Username: elastic
[INFO]   Index pattern: .ds-heartbeat-8.11.0-*
[INFO]   Retention days: 2
[INFO]   Cutoff date: 2026.02.14
[INFO]   (Indices older than this will be deleted)

[INFO] Testing Elasticsearch connection...
[SUCCESS] Connected to Elasticsearch

[SUCCESS] Found 15 indices

========================================
  FOUND INDICES
========================================
INDEX NAME                                         DATE            ACTION
----------------------------------------
[INFO]                                  NO_DATE         SKIP
.ds-heartbeat-8.11.0-2026.02.10-001843             2026.02.10      DELETE
.ds-heartbeat-8.11.0-2026.02.10-001856             2026.02.10      DELETE
.ds-heartbeat-8.11.0-2026.02.10-001857             2026.02.10      DELETE
.ds-heartbeat-8.11.0-2026.02.11-001858             2026.02.11      DELETE
.ds-heartbeat-8.11.0-2026.02.11-001859             2026.02.11      DELETE
.ds-heartbeat-8.11.0-2026.02.11-001860             2026.02.11      DELETE
.ds-heartbeat-8.11.0-2026.02.12-001861             2026.02.12      DELETE
.ds-heartbeat-8.11.0-2026.02.12-001862             2026.02.12      DELETE
.ds-heartbeat-8.11.0-2026.02.12-001863             2026.02.12      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001864             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001865             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001866             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.13-001867             2026.02.13      DELETE
.ds-heartbeat-8.11.0-2026.02.15-001868             2026.02.15      KEEP
----------------------------------------


========================================
        CLEANUP SUMMARY
========================================
Total indices processed:
Deleted:
Kept (newer):
Skipped (no date):
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
