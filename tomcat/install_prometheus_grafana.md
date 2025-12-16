# Install Prometheus and Grafana on RHEL 9.6 (Free/OSS Versions)

## Part 1: Install Prometheus

### Step 1: Create Prometheus User

```bash
# Create system user for Prometheus
sudo useradd --no-create-home --shell /bin/false prometheus
```

### Step 2: Create Directories

```bash
# Create directories for Prometheus
sudo mkdir -p /etc/prometheus
sudo mkdir -p /var/lib/prometheus

# Set ownership
sudo chown prometheus:prometheus /etc/prometheus
sudo chown prometheus:prometheus /var/lib/prometheus
```

### Step 3: Download Prometheus

```bash
# Navigate to tmp directory
cd /tmp

# Download Prometheus (check https://prometheus.io/download/ for latest version)
wget https://github.com/prometheus/prometheus/releases/download/v3.0.1/prometheus-3.0.1.linux-amd64.tar.gz

# Extract
tar -xvzf prometheus-3.0.1.linux-amd64.tar.gz
cd prometheus-3.0.1.linux-amd64
```

### Step 4: Install Prometheus Binaries

```bash
# Copy binaries
sudo cp prometheus /usr/local/bin/
sudo cp promtool /usr/local/bin/

# Set ownership
sudo chown prometheus:prometheus /usr/local/bin/prometheus
sudo chown prometheus:prometheus /usr/local/bin/promtool

# Copy console libraries and files
sudo cp -r consoles /etc/prometheus
sudo cp -r console_libraries /etc/prometheus

# Set ownership
sudo chown -R prometheus:prometheus /etc/prometheus/consoles
sudo chown -R prometheus:prometheus /etc/prometheus/console_libraries
```

### Step 5: Create Prometheus Configuration

```bash
sudo nano /etc/prometheus/prometheus.yml
```

Add this configuration:

```yaml
# Global configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'prometheus-monitor'

# Alertmanager configuration (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Rule files (optional)
rule_files:
  # - "rules/*.yml"

# Scrape configurations
scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Tomcat JMX exporter
  - job_name: 'tomcat'
    static_configs:
      - targets: ['localhost:9104']
        labels:
          instance: 'tomcat-server'
          environment: 'production'
```

Set ownership:

```bash
sudo chown prometheus:prometheus /etc/prometheus/prometheus.yml
```

### Step 6: Create Prometheus systemd Service

```bash
sudo nano /etc/systemd/system/prometheus.service
```

Add this content:

```ini
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
Restart=on-failure
RestartSec=5s
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus/ \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-lifecycle

[Install]
WantedBy=multi-user.target
```

### Step 7: Configure Firewall for Prometheus

```bash
# Open Prometheus port (9090)
sudo firewall-cmd --permanent --add-port=9090/tcp
sudo firewall-cmd --reload
```

### Step 8: Start Prometheus

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable Prometheus to start on boot
sudo systemctl enable prometheus

# Start Prometheus
sudo systemctl start prometheus

# Check status
sudo systemctl status prometheus
```

### Step 9: Verify Prometheus

```bash
# Check if Prometheus is running
sudo ss -tulpn | grep 9090

# Check logs
sudo journalctl -u prometheus -f

# Test Prometheus API
curl http://localhost:9090/api/v1/targets
```

Access Prometheus UI: `http://your-server-ip:9090`

---

## Part 2: Install Grafana (OSS Version)

### Step 1: Create Grafana User

```bash
# Create system user for Grafana
sudo useradd --system --no-create-home --shell /bin/false grafana
```

### Step 2: Download Grafana OSS

```bash
cd /tmp

# Download Grafana OSS binary (check https://grafana.com/grafana/download for latest)
wget https://dl.grafana.com/oss/release/grafana-11.4.0.linux-amd64.tar.gz

# Create installation directory
sudo mkdir -p /opt/grafana

# Extract
sudo tar -zxvf grafana-11.4.0.linux-amd64.tar.gz -C /opt/grafana --strip-components=1
```

### Step 3: Create Required Directories

```bash
# Create directories
sudo mkdir -p /var/lib/grafana
sudo mkdir -p /var/lib/grafana/plugins
sudo mkdir -p /var/log/grafana
sudo mkdir -p /etc/grafana
sudo mkdir -p /etc/grafana/provisioning
sudo mkdir -p /etc/grafana/provisioning/datasources
sudo mkdir -p /etc/grafana/provisioning/dashboards
sudo mkdir -p /var/run/grafana

# Set ownership
sudo chown -R grafana:grafana /opt/grafana
sudo chown -R grafana:grafana /var/lib/grafana
sudo chown -R grafana:grafana /var/log/grafana
sudo chown -R grafana:grafana /etc/grafana
sudo chown -R grafana:grafana /var/run/grafana
```

### Step 4: Create Grafana Configuration

```bash
# Copy default configuration
sudo cp /opt/grafana/conf/defaults.ini /etc/grafana/grafana.ini

# Edit configuration
sudo nano /etc/grafana/grafana.ini
```

Update these settings:

```ini
[paths]
data = /var/lib/grafana
logs = /var/log/grafana
plugins = /var/lib/grafana/plugins
provisioning = /etc/grafana/provisioning

[server]
protocol = http
http_addr = 0.0.0.0
http_port = 3000
domain = localhost
root_url = %(protocol)s://%(domain)s:%(http_port)s/

[database]
type = sqlite3
path = /var/lib/grafana/grafana.db

[security]
admin_user = admin
admin_password = admin

[users]
allow_sign_up = false
allow_org_create = false

[auth.anonymous]
enabled = false

[log]
mode = console file
level = info
```

Set ownership:

```bash
sudo chown grafana:grafana /etc/grafana/grafana.ini
```

### Step 5: Create Prometheus Data Source Provisioning

```bash
sudo nano /etc/grafana/provisioning/datasources/prometheus.yml
```

Add this content:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: true
    jsonData:
      httpMethod: POST
      timeInterval: 15s
```

Set ownership:

```bash
sudo chown -R grafana:grafana /etc/grafana/provisioning
```

### Step 6: Create tmpfiles Configuration

```bash
sudo nano /etc/tmpfiles.d/grafana.conf
```

Add:

```
d /var/run/grafana 0755 grafana grafana -
```

### Step 7: Create Grafana systemd Service

```bash
sudo nano /etc/systemd/system/grafana.service
```

Add this content:

```ini
[Unit]
Description=Grafana OSS
Documentation=https://grafana.com/docs/
Wants=network-online.target
After=network-online.target

[Service]
User=grafana
Group=grafana
Type=simple
Restart=on-failure
RestartSec=5s
WorkingDirectory=/opt/grafana
RuntimeDirectory=grafana
RuntimeDirectoryMode=0750
ExecStart=/opt/grafana/bin/grafana-server \
  --config=/etc/grafana/grafana.ini \
  --pidfile=/var/run/grafana/grafana-server.pid \
  --packaging=binary \
  cfg:default.paths.logs=/var/log/grafana \
  cfg:default.paths.data=/var/lib/grafana \
  cfg:default.paths.plugins=/var/lib/grafana/plugins

[Install]
WantedBy=multi-user.target
```

### Step 8: Configure Firewall for Grafana

```bash
# Open Grafana port (3000)
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload
```

### Step 9: Start Grafana

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable Grafana to start on boot
sudo systemctl enable grafana

# Start Grafana
sudo systemctl start grafana

# Check status
sudo systemctl status grafana
```

### Step 10: Verify Grafana

```bash
# Check if Grafana is running
sudo ss -tulpn | grep 3000

# Check logs
sudo journalctl -u grafana -f

# Or check Grafana log file
sudo tail -f /var/log/grafana/grafana.log
```

Access Grafana UI: `http://your-server-ip:3000`

**Default credentials:**
- Username: `admin`
- Password: `admin`

---

## Part 3: Verify Complete Setup

### Step 1: Check All Services

```bash
# Check Prometheus
sudo systemctl status prometheus

# Check Grafana
sudo systemctl status grafana

# Check all ports
sudo ss -tulpn | grep -E '9090|3000|9104'
```

### Step 2: Verify Prometheus is Scraping Tomcat

1. Open Prometheus UI: `http://your-server-ip:9090`
2. Go to **Status** → **Targets**
3. Verify `tomcat` target shows as **UP**

### Step 3: Verify Grafana Data Source

1. Login to Grafana: `http://your-server-ip:3000`
2. Go to **Connections** → **Data sources**
3. You should see **Prometheus** already configured
4. Click **Test** to verify connection

### Step 4: Test Query in Grafana

1. Go to **Explore** (compass icon)
2. Select **Prometheus** data source
3. Try this query:
   ```promql
   up{job="tomcat"}
   ```
4. You should see data if Tomcat is running

---

## Useful Management Commands

### Prometheus Commands

```bash
# Start/Stop/Restart
sudo systemctl start prometheus
sudo systemctl stop prometheus
sudo systemctl restart prometheus

# View logs
sudo journalctl -u prometheus -f

# Check configuration
promtool check config /etc/prometheus/prometheus.yml

# Reload configuration (if --web.enable-lifecycle is set)
curl -X POST http://localhost:9090/-/reload
```

### Grafana Commands

```bash
# Start/Stop/Restart
sudo systemctl start grafana
sudo systemctl stop grafana
sudo systemctl restart grafana

# View logs
sudo journalctl -u grafana -f
sudo tail -f /var/log/grafana/grafana.log

# Check version
/opt/grafana/bin/grafana-server -v

# Reset admin password
sudo /opt/grafana/bin/grafana-cli admin reset-admin-password newpassword
```

---

## Security Hardening (Optional)

### 1. Restrict Prometheus Access

Edit `/etc/prometheus/prometheus.yml`:

```yaml
# Add basic auth or use reverse proxy
```

### 2. Enable HTTPS for Grafana

Edit `/etc/grafana/grafana.ini`:

```ini
[server]
protocol = https
cert_file = /path/to/cert.pem
cert_key = /path/to/key.pem
```

### 3. SELinux Context (if needed)

```bash
# Check SELinux status
getenforce

# If enforcing, you may need to set contexts
sudo semanage port -a -t http_port_t -p tcp 3000
sudo semanage port -a -t http_port_t -p tcp 9090
```

---

## Backup Recommendations

```bash
# Backup Prometheus data
sudo tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz /var/lib/prometheus

# Backup Grafana database
sudo cp /var/lib/grafana/grafana.db /backup/grafana-$(date +%Y%m%d).db

# Backup configurations
sudo tar -czf prometheus-config-$(date +%Y%m%d).tar.gz /etc/prometheus
sudo tar -czf grafana-config-$(date +%Y%m%d).tar.gz /etc/grafana
```

---

## Quick Access Summary

- **Prometheus UI**: http://your-server-ip:9090
- **Grafana UI**: http://your-server-ip:3000 (admin/admin)
- **Tomcat Metrics**: http://your-server-ip:9104/metrics

Your complete monitoring stack is now installed! 🎉
