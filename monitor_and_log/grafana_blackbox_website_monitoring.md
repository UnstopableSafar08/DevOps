# BlackBox Exporter Website Monitoring Guide

## Overview

Blackbox Exporter is a Prometheus exporter that probes external endpoints
over HTTP, HTTPS, TCP, ICMP, and DNS. It reports whether the endpoint is
reachable, the response time, the HTTP status code, SSL certificate expiry,
and other probe metrics. These metrics are scraped by Prometheus and
visualized in Grafana.

This guide covers installation, configuration, and Grafana dashboard setup
for monitoring 10 application endpoints using a dedicated blackbox server.

---

## Table of Contents

- [Architecture](#architecture)
- [Server Details](#server-details)
- [How Blackbox Exporter Works](#how-blackbox-exporter-works)
- [Step 1: Install Blackbox Exporter](#step-1-install-blackbox-exporter)
- [Step 2: Configure Blackbox Exporter](#step-2-configure-blackbox-exporter)
- [Step 3: Configure Prometheus to Scrape Blackbox](#step-3-configure-prometheus-to-scrape-blackbox)
- [Step 4: Verify Probes are Working](#step-4-verify-probes-are-working)
- [Step 5: Visualize in Grafana](#step-5-visualize-in-grafana)
- [Step 6: Set Up Alerting](#step-6-set-up-alerting)
- [Troubleshooting](#troubleshooting)
- [Metrics Reference](#metrics-reference)

---

## Architecture

```
+--------------------------------------------------------------+
|  Blackbox Server: 10.10.10.100                               |
|                                                              |
|  Blackbox Exporter :9115                                     |
|  Prometheus        :9090                                     |
|  Grafana           :3000                                     |
+------+------------------+------------------------------------+
       |                  |
       | 1. Prometheus     | 2. Prometheus instructs Blackbox
       |    scrapes        |    to probe each app endpoint
       |    Blackbox       |    every 3 seconds
       |    metrics        |
       v                  v
+------+------------------+------------------------------------+
|  Probe targets                                               |
|                                                              |
|  10.10.10.101:80/echo      10.10.10.106:80/echo             |
|  10.10.10.102:80/echo      10.10.10.107:80/echo             |
|  10.10.10.103:80/echo      10.10.10.108:80/echo             |
|  10.10.10.104:80/echo      10.10.10.109:80/echo             |
|  10.10.10.105:80/echo      10.10.10.110:80/echo             |
+--------------------------------------------------------------+
```

### Probe Flow Explained

```
Prometheus                Blackbox Exporter           Target App
    |                           |                         |
    |  GET /probe?target=       |                         |
    |  10.10.10.101/echo        |                         |
    |  &module=http_2xx         |                         |
    |-------------------------->|                         |
    |                           |  HTTP GET /echo         |
    |                           |------------------------>|
    |                           |                         |
    |                           |  HTTP 200 OK            |
    |                           |<------------------------|
    |                           |                         |
    |  probe_success=1          |                         |
    |  probe_duration_seconds   |                         |
    |  probe_http_status_code   |                         |
    |<--------------------------|                         |
```

Prometheus does not probe the targets directly. It tells Blackbox Exporter
which target to probe via query parameters. Blackbox then performs the
actual HTTP request and returns the result as Prometheus metrics.

---

## Server Details

| Role | IP | Ports |
|---|---|---|
| Blackbox + Prometheus + Grafana | 10.10.10.100 | 9115, 9090, 3000 |
| App Node 01 | 10.10.10.101 | 80 (health: /echo) |
| App Node 02 | 10.10.10.102 | 80 (health: /echo) |
| App Node 03 | 10.10.10.103 | 80 (health: /echo) |
| App Node 04 | 10.10.10.104 | 80 (health: /echo) |
| App Node 05 | 10.10.10.105 | 80 (health: /echo) |
| App Node 06 | 10.10.10.106 | 80 (health: /echo) |
| App Node 07 | 10.10.10.107 | 80 (health: /echo) |
| App Node 08 | 10.10.10.108 | 80 (health: /echo) |
| App Node 09 | 10.10.10.109 | 80 (health: /echo) |
| App Node 10 | 10.10.10.110 | 80 (health: /echo) |

Health check path: `/echo`
Expected response: HTTP 200
Health check interval: 3 seconds

---

## How Blackbox Exporter Works

Blackbox Exporter exposes a single HTTP endpoint at `/probe`. Prometheus
scrapes this endpoint with two query parameters:

- `target` : the URL or host to probe
- `module` : which probe configuration to use (defined in blackbox.yml)

Each probe returns a set of metrics. The most important ones are:

| Metric | Value | Meaning |
|---|---|---|
| `probe_success` | 1 | Endpoint is up and returned expected response |
| `probe_success` | 0 | Endpoint is down or returned unexpected response |
| `probe_duration_seconds` | float | Total time taken for the probe |
| `probe_http_status_code` | int | HTTP status code returned |
| `probe_http_ssl` | 1 or 0 | Whether SSL was used |
| `probe_ssl_earliest_cert_expiry` | unix timestamp | SSL cert expiry time |

---

## Step 1: Install Blackbox Exporter

Run all commands on the **blackbox server (10.10.10.100)**.

**Create user and directories**

```bash
sudo useradd --no-create-home --shell /bin/false blackbox_exporter
sudo mkdir -p /etc/blackbox_exporter
```

**Download and install Blackbox Exporter**

```bash
cd /tmp
wget https://github.com/prometheus/blackbox_exporter/releases/download/v0.25.0/blackbox_exporter-0.25.0.linux-amd64.tar.gz
tar xf blackbox_exporter-0.25.0.linux-amd64.tar.gz
cd blackbox_exporter-0.25.0.linux-amd64
sudo mv blackbox_exporter /usr/local/bin/
sudo chown blackbox_exporter:blackbox_exporter /usr/local/bin/blackbox_exporter
```

**Verify installation**

```bash
blackbox_exporter --version
```

**Create Blackbox Exporter systemd service**

```bash
sudo tee /etc/systemd/system/blackbox_exporter.service > /dev/null <<'EOF'
[Unit]
Description=Blackbox Exporter
After=network.target

[Service]
User=blackbox_exporter
Group=blackbox_exporter
ExecStart=/usr/local/bin/blackbox_exporter \
  --config.file=/etc/blackbox_exporter/blackbox.yml \
  --web.listen-address=0.0.0.0:9115
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=blackbox_exporter

LimitNOFILE=16384

[Install]
WantedBy=multi-user.target
EOF
```

**Open firewall**

```bash
sudo firewall-cmd --permanent --add-port=9115/tcp
sudo firewall-cmd --reload
```

---

## Step 2: Configure Blackbox Exporter

The `blackbox.yml` file defines probe modules. Each module specifies the
protocol, expected response codes, timeouts, and other validation rules.

```bash
sudo tee /etc/blackbox_exporter/blackbox.yml > /dev/null <<'EOF'
modules:

  # -------------------------------------------------------
  # http_2xx
  # Basic HTTP probe that expects any 2xx response code.
  # Used for the /echo health check endpoint.
  # -------------------------------------------------------
  http_2xx:
    prober: http
    # Timeout per probe. Must be less than scrape_timeout in Prometheus.
    # Set to 2s here because health check interval is 3s.
    timeout: 2s
    http:
      # Accept HTTP 200 as success
      valid_status_codes: [200]
      # Use GET method
      method: GET
      # Follow redirects up to 3 times
      follow_redirects: true
      preferred_ip_protocol: ip4
      ip_protocol_fallback: false
      # Fail the probe if the response takes longer than timeout
      # even if the server eventually responds
      fail_if_not_ssl: false

  # -------------------------------------------------------
  # http_2xx_ssl
  # Same as http_2xx but requires HTTPS.
  # Use this if your /echo endpoint is served over TLS.
  # -------------------------------------------------------
  http_2xx_ssl:
    prober: http
    timeout: 2s
    http:
      valid_status_codes: [200]
      method: GET
      follow_redirects: true
      preferred_ip_protocol: ip4
      fail_if_not_ssl: true
      tls_config:
        insecure_skip_verify: false

  # -------------------------------------------------------
  # http_post_2xx
  # HTTP POST probe. Use if your health check requires POST.
  # -------------------------------------------------------
  http_post_2xx:
    prober: http
    timeout: 2s
    http:
      valid_status_codes: [200]
      method: POST
      preferred_ip_protocol: ip4

  # -------------------------------------------------------
  # tcp_connect
  # Raw TCP connection probe.
  # Useful for checking if a port is open without HTTP.
  # -------------------------------------------------------
  tcp_connect:
    prober: tcp
    timeout: 2s
    tcp:
      preferred_ip_protocol: ip4

  # -------------------------------------------------------
  # icmp_ping
  # ICMP ping probe.
  # Requires Blackbox Exporter to run with elevated privileges
  # or with net.ipv4.ping_group_range set in sysctl.
  # -------------------------------------------------------
  icmp_ping:
    prober: icmp
    timeout: 2s
    icmp:
      preferred_ip_protocol: ip4
EOF
```

**Set permissions**

```bash
sudo chown blackbox_exporter:blackbox_exporter /etc/blackbox_exporter/blackbox.yml
sudo chmod 640 /etc/blackbox_exporter/blackbox.yml
```

**Validate the configuration**

```bash
blackbox_exporter \
  --config.file=/etc/blackbox_exporter/blackbox.yml \
  --config.check
# Expected: SUCCESS
```

**Start and enable Blackbox Exporter**

```bash
sudo systemctl daemon-reload
sudo systemctl start blackbox_exporter
sudo systemctl enable blackbox_exporter
sudo systemctl status blackbox_exporter
```

**Test a manual probe**

```bash
# Probe one of your app nodes manually
# This tells Blackbox to probe 10.10.10.101/echo using the http_2xx module
curl -s "http://10.10.10.100:9115/probe?target=http://10.10.10.101/echo&module=http_2xx" | \
  grep -E "probe_success|probe_duration|probe_http_status_code"
```

Expected output:

```
probe_duration_seconds 0.003521
probe_http_status_code 200
probe_success 1
```

If `probe_success 1` is returned, Blackbox can reach the target and it
returned HTTP 200.

---

## Step 3: Configure Prometheus to Scrape Blackbox

This is the most important configuration step. Prometheus uses a special
relabeling technique to instruct Blackbox which target to probe. Each
target in the `targets` list becomes the `target` query parameter in the
`/probe` request to Blackbox.

```bash
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  # Default scrape interval for all jobs
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

scrape_configs:

  # -------------------------------------------------------
  # Prometheus self-monitoring
  # -------------------------------------------------------
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  # -------------------------------------------------------
  # Blackbox Exporter self-monitoring
  # -------------------------------------------------------
  - job_name: "blackbox_exporter"
    static_configs:
      - targets: ["localhost:9115"]

  # -------------------------------------------------------
  # Website health checks via Blackbox Exporter
  #
  # scrape_interval: 3s  -- matches your required check interval
  # scrape_timeout: 2s   -- must be less than scrape_interval
  #
  # How the relabeling works:
  #   1. Each entry in targets becomes the __address__ label
  #   2. __param_target is set to the full URL of the app endpoint
  #   3. __address__ is then replaced with the Blackbox Exporter address
  #      so Prometheus scrapes Blackbox, not the app directly
  #   4. instance label is set to the original target URL for readability
  # -------------------------------------------------------
  - job_name: "blackbox_http_probe"
    scrape_interval: 3s
    scrape_timeout: 2s
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - http://10.10.10.101/echo
          - http://10.10.10.102/echo
          - http://10.10.10.103/echo
          - http://10.10.10.104/echo
          - http://10.10.10.105/echo
          - http://10.10.10.106/echo
          - http://10.10.10.107/echo
          - http://10.10.10.108/echo
          - http://10.10.10.109/echo
          - http://10.10.10.110/echo
    relabel_configs:
      # Set the target URL as the probe target parameter
      - source_labels: [__address__]
        target_label: __param_target

      # Set the instance label to the target URL for display in Grafana
      - source_labels: [__param_target]
        target_label: instance

      # Replace the scrape address with Blackbox Exporter address
      # Prometheus will scrape Blackbox, not the app directly
      - target_label: __address__
        replacement: 10.10.10.100:9115

EOF
```

**Reload Prometheus configuration**

```bash
# If Prometheus is already running, reload without restart
curl -s -X POST http://localhost:9090/-/reload

# Or restart
sudo systemctl restart prometheus
```

**Verify targets are visible in Prometheus**

Open `http://10.10.10.100:9090/targets` in a browser.

You should see the `blackbox_http_probe` job with all 10 targets listed.
Each target should show state `UP`.

You can also check via the API:

```bash
curl -s http://10.10.10.100:9090/api/v1/targets | \
  python3 -m json.tool | grep -A3 "blackbox_http_probe"
```

---

## Step 4: Verify Probes are Working

**Check probe success for all targets**

```bash
# Query Prometheus for probe_success across all targets
curl -s -G "http://10.10.10.100:9090/api/v1/query" \
  --data-urlencode 'query=probe_success{job="blackbox_http_probe"}' | \
  python3 -m json.tool
```

Expected output shows value 1 for all targets:

```json
{
  "data": {
    "result": [
      {"metric": {"instance": "http://10.10.10.101/echo"}, "value": [timestamp, "1"]},
      {"metric": {"instance": "http://10.10.10.102/echo"}, "value": [timestamp, "1"]},
      ...
    ]
  }
}
```

**Check response times**

```bash
curl -s -G "http://10.10.10.100:9090/api/v1/query" \
  --data-urlencode 'query=probe_duration_seconds{job="blackbox_http_probe"}' | \
  python3 -m json.tool
```

**Check HTTP status codes**

```bash
curl -s -G "http://10.10.10.100:9090/api/v1/query" \
  --data-urlencode 'query=probe_http_status_code{job="blackbox_http_probe"}' | \
  python3 -m json.tool
```

**Manually probe a single target**

```bash
# Full metrics output for a single probe
curl -s "http://10.10.10.100:9115/probe?target=http://10.10.10.101/echo&module=http_2xx"
```

---

## Step 5: Visualize in Grafana

### 5.1 Add Prometheus as a Data Source

1. Open Grafana at `http://10.10.10.100:3000`
2. Go to Connections > Data Sources > Add new data source
3. Select Prometheus
4. Set the following:

```
Name:           Prometheus
Prometheus URL: http://10.10.10.100:9090
```

5. Click Save and Test

### 5.2 Import Pre-built Blackbox Dashboard

The Grafana community dashboard ID **7587** is the most widely used
Blackbox Exporter dashboard. It shows uptime, response time, status codes,
and SSL certificate expiry out of the box.

1. Go to Dashboards > New > Import
2. Enter dashboard ID: `7587`
3. Click Load
4. Select your Prometheus data source
5. Click Import

### 5.3 Create a Custom Website Monitoring Dashboard

If you prefer a custom dashboard tailored to your setup, follow these steps.

Go to Dashboards > New > New Dashboard > Add visualization.

---

#### Panel 1: Website Up or Down Status (All Nodes at a Glance)

This panel shows a green or red status for each of the 10 app nodes.

```
Visualization type: Stat

Query (Prometheus):
probe_success{job="blackbox_http_probe"}

Panel options:
  Title: Website Status
  Value options > Fields: All fields

Thresholds:
  0 = Red  (down)
  1 = Green (up)

Value mappings:
  0 --> Down
  1 --> Up

Stat display:
  Show: Last value
  Color mode: Background
```

---

#### Panel 2: HTTP Response Time per Node (Time Series)

This panel plots the probe duration over time for all 10 nodes.

```
Visualization type: Time series

Query (Prometheus):
probe_duration_seconds{job="blackbox_http_probe"}

Legend: {{instance}}

Panel options:
  Title: HTTP Response Time (seconds)
  Unit: seconds (s)

Thresholds (optional visual reference lines):
  0.5s = Yellow (slow)
  1.0s = Red    (very slow)
```

---

#### Panel 3: HTTP Status Code per Node

This panel shows the current HTTP status code being returned by each node.

```
Visualization type: Stat

Query (Prometheus):
probe_http_status_code{job="blackbox_http_probe"}

Legend: {{instance}}

Panel options:
  Title: HTTP Status Code

Value mappings:
  200 --> OK (Green)
  500 --> Server Error (Red)
  404 --> Not Found (Orange)
  0   --> No Response (Red)
```

---

#### Panel 4: Overall Uptime Percentage (Last 24 Hours)

This panel shows what percentage of probes were successful over the last
24 hours for each node.

```
Visualization type: Stat

Query (Prometheus):
avg_over_time(probe_success{job="blackbox_http_probe"}[24h]) * 100

Legend: {{instance}}

Panel options:
  Title: Uptime % (Last 24h)
  Unit: Percent (0-100)

Thresholds:
  99   = Green  (healthy)
  95   = Yellow (degraded)
  0    = Red    (critical)
```

---

#### Panel 5: Probe Success Rate Over Time (Time Series)

This panel shows when nodes went down and came back up over time.

```
Visualization type: Time series

Query (Prometheus):
probe_success{job="blackbox_http_probe"}

Legend: {{instance}}

Panel options:
  Title: Probe Success Over Time
  Y-axis: 0 to 1

Value mappings:
  1 = Up
  0 = Down
```

---

#### Panel 6: Average Response Time Across All Nodes

A single number showing the average response time across all 10 nodes.

```
Visualization type: Stat

Query (Prometheus):
avg(probe_duration_seconds{job="blackbox_http_probe"})

Panel options:
  Title: Average Response Time
  Unit: seconds (s)

Thresholds:
  0.3  = Green
  0.5  = Yellow
  1.0  = Red
```

---

#### Panel 7: Nodes Currently Down (Count)

A large red number showing how many nodes are currently down.

```
Visualization type: Stat

Query (Prometheus):
count(probe_success{job="blackbox_http_probe"} == 0)
  or
vector(0)

Panel options:
  Title: Nodes Currently Down
  Unit: none

Thresholds:
  0 = Green
  1 = Red
```

The `or vector(0)` part ensures the panel shows 0 instead of "No data"
when all nodes are up.

---

#### Panel 8: SSL Certificate Expiry (If Using HTTPS)

This panel shows how many days until each SSL certificate expires.

```
Visualization type: Stat

Query (Prometheus):
(probe_ssl_earliest_cert_expiry{job="blackbox_http_probe"} - time()) / 86400

Legend: {{instance}}

Panel options:
  Title: SSL Certificate Expiry (Days)
  Unit: days

Thresholds:
  30   = Green  (plenty of time)
  14   = Yellow (renew soon)
  7    = Red    (urgent)
```

---

#### Suggested Dashboard Layout

```
+----------------------------+----------------------------+
|  Panel 1: Status           |  Panel 7: Nodes Down       |
|  (All 10 nodes up/down)    |  (Count)                   |
+----------------------------+----------------------------+
|  Panel 4: Uptime % 24h                                  |
|  (All 10 nodes)                                         |
+----------------------------+----------------------------+
|  Panel 2: Response Time Over Time                       |
|  (Time series, all nodes)                               |
+---------------------------------------------------------+
|  Panel 5: Probe Success Over Time                       |
|  (Time series, all nodes)                               |
+----------------------------+----------------------------+
|  Panel 3: HTTP Status Code |  Panel 6: Avg Response     |
|  (All 10 nodes)            |  (Single number)           |
+----------------------------+----------------------------+
|  Panel 8: SSL Expiry                                    |
|  (If HTTPS is used)                                     |
+---------------------------------------------------------+
```

---

## Step 6: Set Up Alerting

### 6.1 Create Prometheus Alerting Rules

```bash
sudo mkdir -p /etc/prometheus/rules

sudo tee /etc/prometheus/rules/blackbox_alerts.yml > /dev/null <<'EOF'
groups:
  - name: blackbox_website_alerts
    # Evaluate rules every 3 seconds to match probe interval
    interval: 3s
    rules:

      # Alert when any node has been down for more than 9 seconds
      # 9s = 3 consecutive failed probes at 3s interval
      - alert: WebsiteDown
        expr: probe_success{job="blackbox_http_probe"} == 0
        for: 9s
        labels:
          severity: critical
        annotations:
          summary: "Website is down"
          description: "Endpoint {{ $labels.instance }} has been unreachable for more than 9 seconds."

      # Alert when response time exceeds 1 second
      - alert: WebsiteSlowResponse
        expr: probe_duration_seconds{job="blackbox_http_probe"} > 1
        for: 30s
        labels:
          severity: warning
        annotations:
          summary: "Website responding slowly"
          description: "Endpoint {{ $labels.instance }} response time is {{ $value | humanizeDuration }}."

      # Alert when HTTP status code is not 200
      - alert: WebsiteUnexpectedStatusCode
        expr: probe_http_status_code{job="blackbox_http_probe"} != 200
        for: 9s
        labels:
          severity: warning
        annotations:
          summary: "Unexpected HTTP status code"
          description: "Endpoint {{ $labels.instance }} returned HTTP {{ $value }} instead of 200."

      # Alert when SSL certificate expires in less than 14 days
      - alert: SSLCertificateExpiringSoon
        expr: (probe_ssl_earliest_cert_expiry{job="blackbox_http_probe"} - time()) / 86400 < 14
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL certificate expiring soon"
          description: "SSL certificate for {{ $labels.instance }} expires in {{ $value | humanize }} days."

      # Alert when SSL certificate expires in less than 7 days
      - alert: SSLCertificateExpiryCritical
        expr: (probe_ssl_earliest_cert_expiry{job="blackbox_http_probe"} - time()) / 86400 < 7
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "SSL certificate expiry critical"
          description: "SSL certificate for {{ $labels.instance }} expires in {{ $value | humanize }} days."

EOF
```

**Reference the rules file in prometheus.yml**

```bash
# Add rule_files section to prometheus.yml
sudo tee -a /etc/prometheus/prometheus.yml > /dev/null <<'EOF'

rule_files:
  - /etc/prometheus/rules/blackbox_alerts.yml
EOF
```

**Reload Prometheus**

```bash
curl -s -X POST http://localhost:9090/-/reload
```

**Verify rules are loaded**

```bash
curl -s http://10.10.10.100:9090/api/v1/rules | python3 -m json.tool | grep "name"
```

### 6.2 Set Up Grafana Alerting for WebsiteDown

1. Open the Status panel (Panel 1) in edit mode
2. Go to the Alert tab
3. Click Create alert rule
4. Configure as follows:

```
Rule name: Website Down Alert
Condition: probe_success{job="blackbox_http_probe"} == 0
Evaluate every: 3s
For: 9s
```

5. Add notification channel (email, Slack, PagerDuty, etc.) under
   Alerting > Notification channels

---

## Troubleshooting

### Probe Returns probe_success 0

```bash
# Test the probe manually with verbose output
curl -v "http://10.10.10.100:9115/probe?target=http://10.10.10.101/echo&module=http_2xx"

# Check if the app node is reachable from blackbox server
curl -v http://10.10.10.101/echo

# Check if firewall is blocking
sudo firewall-cmd --list-all
telnet 10.10.10.101 80
```

### Target Shows as DOWN in Prometheus

```bash
# Check if Blackbox Exporter is running
sudo systemctl status blackbox_exporter

# Check Blackbox logs
sudo journalctl -u blackbox_exporter -f

# Verify Prometheus can reach Blackbox
curl -s http://10.10.10.100:9115/metrics | head -10

# Check Prometheus scrape errors
curl -s http://10.10.10.100:9090/api/v1/targets | \
  python3 -m json.tool | grep -A5 "lastError"
```

### Scrape Timeout Errors

```bash
# Check if scrape_timeout is less than scrape_interval
# scrape_interval: 3s  and  scrape_timeout: 2s  is correct
# If scrape_timeout >= scrape_interval, Prometheus will report errors

grep -E "scrape_interval|scrape_timeout" /etc/prometheus/prometheus.yml

# Also check that blackbox.yml timeout is less than scrape_timeout
# blackbox.yml timeout: 2s  and  prometheus scrape_timeout: 2s  is correct
# blackbox.yml timeout must be <= prometheus scrape_timeout
grep timeout /etc/blackbox_exporter/blackbox.yml
```

### Config File Changes Not Taking Effect

```bash
# Validate blackbox.yml after any changes
blackbox_exporter \
  --config.file=/etc/blackbox_exporter/blackbox.yml \
  --config.check

# Blackbox Exporter supports live config reload via SIGHUP
sudo kill -HUP $(pgrep blackbox_exporter)

# Or restart the service
sudo systemctl restart blackbox_exporter

# Reload Prometheus config without restart
curl -s -X POST http://localhost:9090/-/reload
```

### No Data in Grafana

```bash
# Confirm data exists in Prometheus first
curl -s -G "http://10.10.10.100:9090/api/v1/query" \
  --data-urlencode 'query=probe_success' | python3 -m json.tool

# Check the Prometheus data source in Grafana is pointing to correct URL
# Connections > Data Sources > Prometheus > URL should be:
# http://10.10.10.100:9090

# Check time range in Grafana is not set to a future or very old period
# Set to "Last 15 minutes" and confirm data appears
```

---

## Metrics Reference

Full list of metrics exposed by Blackbox Exporter per probe.

| Metric | Type | Description |
|---|---|---|
| `probe_success` | Gauge | 1 if probe succeeded, 0 if failed |
| `probe_duration_seconds` | Gauge | Total time taken for probe |
| `probe_http_status_code` | Gauge | HTTP response status code |
| `probe_http_content_length` | Gauge | Length of response body in bytes |
| `probe_http_redirects` | Gauge | Number of redirects followed |
| `probe_http_ssl` | Gauge | 1 if SSL was used, 0 if not |
| `probe_http_version` | Gauge | HTTP protocol version (1.1, 2.0) |
| `probe_ssl_earliest_cert_expiry` | Gauge | Unix timestamp of earliest SSL cert expiry |
| `probe_ssl_last_chain_info` | Gauge | Info about the last SSL chain |
| `probe_dns_lookup_time_seconds` | Gauge | Time for DNS lookup |
| `probe_ip_protocol` | Gauge | IP protocol used (4 or 6) |
| `probe_failed_due_to_regex` | Gauge | 1 if probe failed due to regex mismatch |

### Useful PromQL Queries

```promql
# Current up/down status for all nodes
probe_success{job="blackbox_http_probe"}

# Nodes that are currently down
probe_success{job="blackbox_http_probe"} == 0

# Average response time over last 5 minutes per node
avg_over_time(probe_duration_seconds{job="blackbox_http_probe"}[5m])

# Uptime percentage over last 24 hours
avg_over_time(probe_success{job="blackbox_http_probe"}[24h]) * 100

# Count of currently down nodes
count(probe_success{job="blackbox_http_probe"} == 0)

# Count of currently up nodes
count(probe_success{job="blackbox_http_probe"} == 1)

# 95th percentile response time over last 1 hour
histogram_quantile(0.95,
  rate(probe_duration_seconds{job="blackbox_http_probe"}[1h])
)

# Days until SSL certificate expires
(probe_ssl_earliest_cert_expiry{job="blackbox_http_probe"} - time()) / 86400

# HTTP status codes that are not 200
probe_http_status_code{job="blackbox_http_probe"} != 200
```

---

## Services Port Reference

| Service | Port | URL |
|---|---|---|
| Blackbox Exporter | 9115 | http://10.10.10.100:9115/metrics |
| Blackbox Probe endpoint | 9115 | http://10.10.10.100:9115/probe |
| Prometheus | 9090 | http://10.10.10.100:9090 |
| Grafana | 3000 | http://10.10.10.100:3000 |
