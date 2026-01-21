# Nginx Container Log Nullify - Automated Cleanup
`Cases:`
> 1. If there is no volume mapped for logs
> 2. If you cant restart your container.

Automated solution to monitor and truncate nginx container log files that exceed 50MB, preventing disk space issues.

## Overview

This setup creates a cron job on the host machine that automatically checks nginx container logs every minute and truncates any log files >= 50MB.

## Prerequisites

- Docker installed and running
- Nginx container running (e.g., `rraj4/nginx-more:latest`)
- Root or sudo access on the host machine

## Setup Instructions

### Step 1: Verify Your Container

```bash
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                     COMMAND                  CREATED         STATUS         PORTS                                                                      NAMES
58f23865229b   rraj4/nginx-more:latest   "nginx -g 'daemon of…"   15 months ago   Up 15 months   0.0.0.0:80->80/tcp, :::80->80/tcp, 0.0.0.0:443->443/tcp, :::443->443/tcp   nginx-proxy
```

### Step 2: Create Log Cleanup Script Inside Container

Enter the container:
```bash
docker exec -it nginx-proxy /bin/bash
```

Create the cleanup script:
```bash
vi /usr/bin/log_clear.sh
```

Add the following content:
```bash
#!/bin/bash
# truncate-large-logs.sh

echo "Finding log files >= 50MB in /var/log/nginx..."
echo ""

# Store files in an array
files=()
while IFS= read -r -d '' file; do
    files+=("$file")
done < <(find /var/log/nginx -type f -name "*.log" -size +50M -print0)

# Check if any files found
if [ ${#files[@]} -eq 0 ]; then
    echo "No log files >= 50MB found."
    exit 0
fi

# List all files first
echo "Found ${#files[@]} file(s) >= 50MB:"
echo "----------------------------------------"
for file in "${files[@]}"; do
    size=$(du -h "$file" | cut -f1)
    echo "  $file ($size)"
done
echo "----------------------------------------"
echo ""

# Truncate files
echo "Truncating files..."
for file in "${files[@]}"; do
    truncate -s 0 "$file"
    echo "  ✓ Truncated: $file"
done

echo ""
echo "Cleanup complete!"
```

Make the script executable:
```bash
chmod +x /usr/bin/log_clear.sh
```

Exit the container:
```bash
exit
```

### Step 3: Test the Script Manually

```bash
docker exec nginx-proxy sh -c '/usr/bin/log_clear.sh'
```

Expected output if no large logs:
```
Finding log files >= 50MB in /var/log/nginx...

No log files >= 50MB found.
```

Or if large logs are found:
```
Finding log files >= 50MB in /var/log/nginx...

Found 3 file(s) >= 50MB:
----------------------------------------
  /var/log/nginx/error.log (3.4G)
  /var/log/nginx/access.log (205M)
  /var/log/nginx/rc-gateway_error.log (11G)
----------------------------------------

Truncating files...
  ✓ Truncated: /var/log/nginx/error.log
  ✓ Truncated: /var/log/nginx/access.log
  ✓ Truncated: /var/log/nginx/rc-gateway_error.log

Cleanup complete!
```

### Step 4: Set Up Cron Job on Host

Open crontab editor:
```bash
crontab -e
```

Add this line (runs every minute):
```bash
# This job will clear the nginx container logs, if the logs size >= 50 MB
*/1 * * * * docker exec nginx-proxy sh -c '/usr/bin/log_clear.sh' >> /var/log/cronjob_log.log 2>&1
```

Save and exit.

### Step 5: Create Log File with Proper Permissions

```bash
touch /var/log/cronjob_log.log
chmod 644 /var/log/cronjob_log.log
```

### Step 6: Verify Cron Job

Check if the cron job is installed:
```bash
crontab -l
```

Monitor the cron execution logs:
```bash
tail -f /var/log/cronjob_log.log
```

Expected output:
```
Finding log files >= 50MB in /var/log/nginx...

No log files >= 50MB found.
Finding log files >= 50MB in /var/log/nginx...

No log files >= 50MB found.
```

## Configuration Options

### Adjust File Size Threshold

To change the size threshold from 50MB to another value, modify this line in the script:
```bash
find /var/log/nginx -type f -name "*.log" -size +50M -print0
```

Examples:
- `+100M` - Files larger than 100MB
- `+1G` - Files larger than 1GB
- `+500M` - Files larger than 500MB

### Adjust Cron Schedule

Modify the cron schedule as needed:

```bash
*/1 * * * *   # Every 1 minute
*/5 * * * *   # Every 5 minutes
*/15 * * * *  # Every 15 minutes
0 * * * *     # Every hour
0 */6 * * *   # Every 6 hours
0 0 * * *     # Every day at midnight
```

## Monitoring and Troubleshooting

### Check Container Logs

```bash
docker logs nginx-proxy
```

### Check Disk Usage Inside Container

```bash
docker exec nginx-proxy du -sh /var/log/nginx
docker exec nginx-proxy du -sch /var/log/nginx/*.log
```

### View Cron Execution History

```bash
# View last 50 lines
tail -50 /var/log/cronjob_log.log

# Follow in real-time
tail -f /var/log/cronjob_log.log

# Search for specific dates
grep "$(date +%Y-%m-%d)" /var/log/cronjob_log.log
```

### Check System Cron Logs

```bash
# On most Linux systems
sudo tail -f /var/log/cron

# On Ubuntu/Debian
sudo tail -f /var/log/syslog | grep CRON
```

### Verify Cron Service is Running

```bash
# CentOS/RHEL
sudo systemctl status crond

# Ubuntu/Debian
sudo systemctl status cron
```

## Manual Execution

To manually run the cleanup:

```bash
docker exec nginx-proxy sh -c '/usr/bin/log_clear.sh'
```

## Uninstallation

### Remove Cron Job

```bash
crontab -e
# Delete the line with log_clear.sh
```

Or use this command:
```bash
crontab -l | grep -v log_clear.sh | crontab -
```

### Remove Script from Container

```bash
docker exec nginx-proxy rm /usr/bin/log_clear.sh
```

### Remove Log File

```bash
sudo rm /var/log/cronjob_log.log
```

## Important Notes

1. **Data Loss**: This script permanently deletes log content. Ensure you have proper log forwarding or backup if you need log retention.

2. **Active Logging**: Nginx will continue writing to the truncated files immediately after truncation.

3. **No Nginx Restart**: The script does not restart or reload nginx. Log file descriptors remain open and nginx continues logging normally.

4. **Performance**: Running every minute has minimal performance impact but can be adjusted based on your needs.

5. **Container Restarts**: The script inside the container will persist across container restarts, but will be lost if the container is removed and recreated.

## Best Practices

1. **Log Rotation**: Consider implementing proper log rotation using `logrotate` for long-term log management.

2. **Log Forwarding**: Send logs to a centralized logging system (ELK, Splunk, CloudWatch, etc.) before truncation.

3. **Monitoring**: Set up alerts for when logs reach threshold sizes.

4. **Backup**: Ensure important logs are backed up before implementing automated truncation.

## Alternative Solutions

### Using Docker's Built-in Log Management

Configure Docker to limit log size:
```bash
docker run --log-opt max-size=50m --log-opt max-file=3 ...
```

### Using Logrotate Inside Container

Install and configure logrotate for automatic rotation with compression and retention.
