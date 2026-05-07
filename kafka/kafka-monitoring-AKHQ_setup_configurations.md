### Oracle Linux 9 — Kafka/Redpanda Monitoring UI

AKHQ is a lightweight, open-source web interface for managing and monitoring Apache Kafka clusters. It allows users to easily browse topics, inspect partitions and messages, track consumer groups and lag, and produce or consume messages directly from a browser. Designed for simplicity and operational visibility, AKHQ is commonly used by developers and platform engineers as a convenient alternative to command-line tools for debugging, monitoring, and day-to-day Kafka administration.

## Table of Contents

## 1\. Overview

AKHQ (formerly KafkaHQ) is a web UI for managing and monitoring Apache Kafka clusters. It is Kafka API-compatible and works with Redpanda as well.

**This setup covers:**

**Environment:**

## 2\. Prerequisites

Verify Kafka brokers are reachable from the AKHQ host before starting:

```bash
for ip in 10.10.20.147 10.10.20.148 10.10.20.149; do
  echo -n "Checking $ip:9092 ... "
  timeout 3 bash -c "echo > /dev/tcp/$ip/9092" 2>/dev/null \
    && echo "OK" || echo "UNREACHABLE"
done

```

## 3\. Install Java 17

### Option A — DNF (recommended if internet available)

```bash
sudo dnf install -y java-17-openjdk-headless
java -version

```

### Option B — Manual JDK (offline environments)

```bash
wget https://download.bell-sw.com/java/17.0.19+11/bellsoft-jdk17.0.19+11-linux-amd64.tar.gz
tar xvzf bellsoft-jdk17.0.19+11-linux-amd64.tar.gz -C /opt/ # /opt/jdk-17.0.19

# Export a JAVA_HOME
sudo tee /etc/profile.d/java.sh > /dev/null <<'EOF'
export JAVA_HOME=/opt/jdk-17.0.19
export PATH=$JAVA_HOME/bin:$PATH
EOF

chmod +x /etc/profile.d/java.sh
source /etc/profile.d/java.sh
java -version

# Symlink manually installed JDK to system PATH
sudo ln -s /opt/jdk-17.0.19/bin/java /usr/bin/java
java -version

```

## 4\. Download AKHQ

```bash
AKHQ_VERSION=0.25.1

sudo mkdir -p /opt/akhq
sudo curl -L \
  https://github.com/tchiotludo/akhq/releases/download/${AKHQ_VERSION}/akhq-${AKHQ_VERSION}-all.jar \
  -o /opt/akhq/akhq.jar

ls -lh /opt/akhq/akhq.jar

```

## 5\. Directory Structure

```
/opt/akhq/
└── akhq.jar               # Application JAR

/etc/akhq/
└── application.yml        # Main configuration file

/etc/systemd/system/
└── akhq.service           # systemd service unit

```

Create directories and set ownership:

```bash
sudo mkdir -p /opt/akhq /etc/akhq
sudo useradd -r -s /sbin/nologin -d /opt/akhq akhq
sudo chown -R akhq:akhq /opt/akhq /etc/akhq

```

## 6\. Configuration

Minimal config to get started (no auth):

```yaml
# /etc/akhq/application.yml
akhq:
  connections:
    kafka-cluster:
      properties:
        bootstrap.servers: "10.10.20.147:9092,10.10.20.148:9092,10.10.20.149:9092"

micronaut:
  server:
    port: 8080

```

## 7\. systemd Service

```bash
sudo tee /etc/systemd/system/akhq.service > /dev/null <<'EOF'
[Unit]
Description=AKHQ - Kafka UI
After=network.target

[Service]
Type=simple
User=root
Group=root
Environment="MICRONAUT_CONFIG_FILES=/etc/akhq/application.yml"
ExecStart=/root/.jdk17/bin/java -jar /opt/akhq/akhq.jar
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now akhq
sudo systemctl status akhq

```

## 8\. Firewall

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

```

Access UI at: `http://<server-ip>:8080`

## 9\. RBAC — Users & Groups

### Generate password hash

AKHQ uses SHA256 hashed passwords:

```bash
echo -n "your_password_here" | sha256sum | awk '{print $1}'

```

### Generate JWT secret

```bash
cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 48 | head -n 1

```

## 10\. Group Format — 0.25+ Breaking Change

### Old format (0.24.x) — DO NOT USE

```yaml
# BROKEN in 0.25+
groups:
  reader:
    roles:
      - topic/read
      - topic/data/read
    attributes:
      topics-filter-regexp: ".*"

```

### New format (0.25+) — USE THIS

```yaml
# CORRECT for 0.25+
groups:
  reader:
    - role: reader          # references a built-in or custom role name
      patterns: [ ".*" ]    # resource name patterns (regex)
      clusters: [ ".*" ]    # cluster name patterns (regex)

```

### Three built-in groups (no definition needed)

## 11\. Built-in Roles Reference

### Resource & Action matrix

## 12\. Full Production Config

```bash
# Step 1 — Generate credentials
ADMIN_HASH=$(echo -n 'your_admin_password' | sha256sum | awk '{print $1}')
SRE_HASH=$(echo -n 'your_sre_password' | sha256sum | awk '{print $1}')
JWT_SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 48 | head -n 1)

echo "Admin hash : $ADMIN_HASH"
echo "SRE hash   : $SRE_HASH"
echo "JWT secret : $JWT_SECRET"

```

```bash
# Step 2 — Write config (run in same shell session as Step 1)
sudo tee /etc/akhq/application.yml > /dev/null <<EOF
# ----------------------------------------
# Author: Sagar Malla, sagar.malla@sagarmalla.info.np
# Role: DevOps Engineer
# Project: AKHQ Multi-Cluster Configuration
# Created: 2026-05-06
# Last Updated: 2026-05-07
# Description: Configuration for managing multiple Kafka clusters in AKHQ
# ----------------------------------------
akhq:
  connections:
    DR-Kafka:
      properties:
        bootstrap.servers: "10.10.20.147:9092,10.10.20.148:9092,10.10.20.149:9092"
    DC-Kafka:
      properties:
        bootstrap.servers: "10.10.20.2:9092,10.10.20.13:9092,10.10.20.17:9092"
    NDC-Kafka:
      properties:
        bootstrap.servers: "192.168.2.50:9092,192.168.2.51:9092,192.168.2.52:9092"

  security:
    default-group: no-roles

    basic-auth:
      - username: admin
        password: "${ADMIN_HASH}"
        passwordHash: SHA256
        groups:
          - admin                  # built-in: full access

      - username: sre
        password: "${SRE_HASH}"
        passwordHash: SHA256
        groups:
          - reader                 # built-in: read-only access

  groups:
    reader:
      - role: reader
        patterns: [ ".*" ]
        clusters: [ ".*" ]

micronaut:
  security:
    enabled: true
    authentication: cookie
    intercept-url-map:
      - pattern: /ui/login
        access:
          - isAnonymous()
      - pattern: /ui/assets/**
        access:
          - isAnonymous()
      - pattern: /**
        access:
          - isAuthenticated()
    token:
      jwt:
        signatures:
          secret:
            generator:
              secret: "${JWT_SECRET}"
  server:
    port: 8080
EOF

```

```bash
# Step 3 — Validate YAML
python3 -c "import yaml; yaml.safe_load(open('/etc/akhq/application.yml')); print('YAML OK')"

# Step 4 — Restart
sudo systemctl restart akhq
journalctl -u akhq -f

```

### Adding more users

```bash
# Generate hash
NEW_HASH=$(echo -n 'password' | sha256sum | awk '{print $1}')
echo $NEW_HASH

```

Add under `basic-auth:` in the config:

```yaml
- username: developer
  password: "NEW_HASH"
  passwordHash: SHA256
  groups:
    - reader                 # or admin, or a custom group

```

Then restart: `sudo systemctl restart akhq`

### Custom scoped group example (topic prefix restriction)

```yaml
groups:
  payments-reader:
    - role: reader
      patterns: [ "^payment-.*" ]    # only topics starting with payment-
      clusters: [ ".*" ]

```

Assign to a user:

```yaml
- username: payments-dev
  password: "HASH"
  passwordHash: SHA256
  groups:
    - payments-reader

```

### User permissions summary

## 13\. Nginx Reverse Proxy

Recommended for production — avoids exposing port 8080 directly.

```bash
sudo tee /etc/nginx/conf.d/akhq.conf > /dev/null <<'EOF'
upstream akhq {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name akhq.sagarmalla.info.np;

    location / {
        proxy_pass         http://akhq;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}
EOF

sudo nginx -t && sudo systemctl reload nginx

```

## 14\. Verify & Test

### Check AKHQ is listening

```bash
ss -tlnp | grep 8080

```

### Test login via curl

```bash
# Login and save session cookie
curl -s -c /tmp/akhq.txt \
  -X POST "http://localhost:8080/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password" -L > /dev/null

# Check roles returned for the session
curl -s -b /tmp/akhq.txt http://localhost:8080/api/me | python3 -m json.tool

```

A working response looks like:

```json
{
    "logged": true,
    "username": "admin",
    "roles": [
        {
            "resources": ["TOPIC", "TOPIC_DATA"],
            "actions": ["READ", "CREATE", "UPDATE", "DELETE"],
            "patterns": [".*"],
            "clusters": [".*"]
        }
    ]
}

```

If `roles` is missing from the response, the group is not resolving — see Troubleshooting.

### Check broker connectivity

```bash
for ip in 10.10.20.147 10.10.20.148 10.10.20.149 \
          10.10.20.2 10.10.20.13 10.10.20.17 \
          192.168.2.50 192.168.2.51 192.168.2.52; do
  echo -n "$ip:9092 -> "
  timeout 3 bash -c "echo > /dev/tcp/$ip/9092" 2>/dev/null \
    && echo "REACHABLE" || echo "UNREACHABLE"
done

```

## 15\. Useful Commands

```bash
# Service management
sudo systemctl start akhq
sudo systemctl stop akhq
sudo systemctl restart akhq
sudo systemctl status akhq

# Live logs
journalctl -u akhq -f

# Last 100 log lines
journalctl -u akhq -n 100 --no-pager

# Validate config YAML syntax
python3 -c "import yaml; yaml.safe_load(open('/etc/akhq/application.yml')); print('YAML OK')"

# Generate a new password hash
echo -n "newpassword" | sha256sum | awk '{print $1}'

# Generate a new JWT secret
cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 48 | head -n 1

```

## 16\. Troubleshooting

## Notes
