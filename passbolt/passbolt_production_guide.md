# Passbolt Docker Setup Guide

A comprehensive guide for deploying Passbolt password manager using Docker and Docker Compose.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start (Development)](#quick-start-development)
- [Production Setup](#production-setup)
- [Creating Admin User](#creating-admin-user)
- [Configuration Options](#configuration-options)
- [Backup and Restore](#backup-and-restore)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Production Best Practices](#production-best-practices)
- [Security Considerations](#security-considerations)

---

## Overview

Passbolt is an open-source password manager designed for team collaboration. This guide covers both development (HTTP) and production (HTTPS) deployment scenarios.

**⚠️ Warning**: The development setup uses HTTP and is NOT suitable for production use.

---

## Prerequisites

- Docker (20.10 or later)
- Docker Compose (2.0 or later)
- Minimum 2GB RAM
- Minimum 10GB disk space
- Domain name (for production)
- SMTP server access (optional, for email notifications)

### Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
sudo yum install docker docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**macOS/Windows:**
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop)

---

## Quick Start (Development)

This setup is for **local development and testing only** (HTTP, no SSL).

### 1. Create Project Directory

```bash
mkdir passbolt-docker
cd passbolt-docker
```

### 2. Create docker-compose.yml

```yaml
version: '3.9'

services:
  db:
    image: mariadb:10.11
    container_name: passbolt_db
    restart: unless-stopped
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: "true"
      MYSQL_DATABASE: "passbolt"
      MYSQL_USER: "passbolt"
      MYSQL_PASSWORD: "your_secure_password_here"  # Change this!
    volumes:
      - database_volume:/var/lib/mysql
    networks:
      - passbolt_network

  passbolt:
    image: passbolt/passbolt:latest-ce
    container_name: passbolt_app
    restart: unless-stopped
    depends_on:
      - db
    environment:
      APP_FULL_BASE_URL: "http://passbolt.local"
      DATASOURCES_DEFAULT_HOST: "db"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "your_secure_password_here"  # Must match DB password
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_DEFAULT_FROM: "no-reply@passbolt.local"
      EMAIL_TRANSPORT_DEFAULT_HOST: "localhost"
      EMAIL_TRANSPORT_DEFAULT_PORT: "25"
      PASSBOLT_SSL_FORCE: "false"
    volumes:
      - gpg_volume:/etc/passbolt/gpg
      - jwt_volume:/etc/passbolt/jwt
    command:
      [
        "/usr/bin/wait-for.sh",
        "-t",
        "0",
        "db:3306",
        "--",
        "/docker-entrypoint.sh",
      ]
    ports:
      - "80:80"
    networks:
      - passbolt_network

volumes:
  database_volume:
  gpg_volume:
  jwt_volume:

networks:
  passbolt_network:
    driver: bridge
```

### 3. Configure Hosts File

**Linux/macOS:**
```bash
sudo nano /etc/hosts
```

**Windows:**
```bash
notepad C:\Windows\System32\drivers\etc\hosts
```

Add this line:
```
127.0.0.1   passbolt.local
```

### 4. Start Services

```bash
# Start containers
docker-compose up -d

# Check logs
docker-compose logs -f
```

Wait 30-60 seconds for services to initialize.

### 5. Verify Installation

```bash
# Check container status
docker-compose ps

# Check passbolt health
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt healthcheck" \
  -s /bin/sh www-data
```

### 6. Create Admin User

See [Creating Admin User](#creating-admin-user) section below.

### 7. Access Passbolt

Navigate to: `http://passbolt.local`

---

## Production Setup

This setup uses **HTTPS with SSL/TLS** for production environments.

### Option A: Using Let's Encrypt (Recommended)

#### 1. Prerequisites
- A registered domain name pointing to your server
- Ports 80 and 443 open in firewall
- Valid email address for Let's Encrypt notifications

#### 2. Create Project Structure

```bash
mkdir -p passbolt-production/{nginx,certbot/conf,certbot/www}
cd passbolt-production
```

#### 3. Create docker-compose.yml

```yaml
version: '3.9'

services:
  db:
    image: mariadb:10.11
    container_name: passbolt_db
    restart: unless-stopped
    environment:
      MYSQL_RANDOM_ROOT_PASSWORD: "true"
      MYSQL_DATABASE: "passbolt"
      MYSQL_USER: "passbolt"
      MYSQL_PASSWORD: "${DB_PASSWORD}"  # Use environment variable
    volumes:
      - database_volume:/var/lib/mysql
    networks:
      - passbolt_network
    command: --default-authentication-plugin=mysql_native_password

  passbolt:
    image: passbolt/passbolt:latest-ce
    container_name: passbolt_app
    restart: unless-stopped
    depends_on:
      - db
    environment:
      APP_FULL_BASE_URL: "https://${DOMAIN_NAME}"
      DATASOURCES_DEFAULT_HOST: "db"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "${DB_PASSWORD}"
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_DEFAULT_FROM: "${EMAIL_FROM}"
      EMAIL_TRANSPORT_DEFAULT_HOST: "${SMTP_HOST}"
      EMAIL_TRANSPORT_DEFAULT_PORT: "${SMTP_PORT}"
      EMAIL_TRANSPORT_DEFAULT_USERNAME: "${SMTP_USERNAME}"
      EMAIL_TRANSPORT_DEFAULT_PASSWORD: "${SMTP_PASSWORD}"
      EMAIL_TRANSPORT_DEFAULT_TLS: "true"
      PASSBOLT_GPG_SERVER_KEY_FINGERPRINT: "${GPG_FINGERPRINT}"
    volumes:
      - gpg_volume:/etc/passbolt/gpg
      - jwt_volume:/etc/passbolt/jwt
    command:
      [
        "/usr/bin/wait-for.sh",
        "-t",
        "0",
        "db:3306",
        "--",
        "/docker-entrypoint.sh",
      ]
    networks:
      - passbolt_network

  nginx:
    image: nginx:alpine
    container_name: passbolt_nginx
    restart: unless-stopped
    depends_on:
      - passbolt
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/passbolt.conf:/etc/nginx/conf.d/default.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    networks:
      - passbolt_network

  certbot:
    image: certbot/certbot
    container_name: passbolt_certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  database_volume:
  gpg_volume:
  jwt_volume:

networks:
  passbolt_network:
    driver: bridge
```

#### 4. Create .env File

```bash
cat > .env << EOF
# Domain Configuration
DOMAIN_NAME=passbolt.example.com

# Database Configuration
DB_PASSWORD=$(openssl rand -base64 32)

# Email Configuration
EMAIL_FROM=no-reply@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password

# GPG Configuration (will be generated on first run)
GPG_FINGERPRINT=
EOF
```

**⚠️ Important**: Update the `.env` file with your actual values.

#### 5. Create NGINX Configuration

**nginx/nginx.conf:**
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;

    include /etc/nginx/conf.d/*.conf;
}
```

**nginx/passbolt.conf:**
```nginx
server {
    listen 80;
    server_name ${DOMAIN_NAME};
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN_NAME};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://passbolt:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
}
```

Replace `${DOMAIN_NAME}` with your actual domain in the nginx configuration files.

#### 6. Obtain SSL Certificate

```bash
# First, start with a temporary nginx config for certificate generation
docker-compose up -d nginx

# Obtain certificate
docker-compose run --rm certbot certonly --webroot \
  --webroot-path /var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d passbolt.example.com

# Restart nginx to load certificates
docker-compose restart nginx
```

#### 7. Start All Services

```bash
docker-compose up -d
```

### Option B: Using Self-Signed Certificate (Not Recommended for Production)

```bash
# Create SSL directory
mkdir -p ssl

# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/passbolt.key \
  -out ssl/passbolt.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=passbolt.example.com"

# Add volumes to docker-compose.yml
volumes:
  - ./ssl/passbolt.crt:/etc/ssl/certs/passbolt.crt:ro
  - ./ssl/passbolt.key:/etc/ssl/certs/passbolt.key:ro
```

---

## Creating Admin User

After Passbolt is running, create an admin user:

```bash
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt register_user \
  -u admin@example.com \
  -f Admin \
  -l User \
  -r admin" \
  -s /bin/sh www-data
```

**Output:**
```
User saved successfully.
To start registration follow the link provided in your mailbox or here:
https://passbolt.example.com/setup/install/...
```

**For development (HTTP):** Change `https://` to `http://` in the URL.

### Complete Registration

1. Open the registration link in your browser
2. Install the Passbolt browser extension
   - [Chrome/Edge](https://chrome.google.com/webstore/detail/passbolt/didegimhafipceonhjepacocaffmoppf)
   - [Firefox](https://addons.mozilla.org/firefox/addon/passbolt/)
3. Follow the setup wizard
4. Generate or import your GPG key
5. Set your passphrase
6. Complete account setup

---

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_FULL_BASE_URL` | Full URL to access Passbolt | - | Yes |
| `DATASOURCES_DEFAULT_HOST` | Database host | `db` | Yes |
| `DATASOURCES_DEFAULT_USERNAME` | Database username | `passbolt` | Yes |
| `DATASOURCES_DEFAULT_PASSWORD` | Database password | - | Yes |
| `DATASOURCES_DEFAULT_DATABASE` | Database name | `passbolt` | Yes |
| `EMAIL_DEFAULT_FROM` | Default sender email | - | Yes |
| `EMAIL_TRANSPORT_DEFAULT_HOST` | SMTP host | - | For emails |
| `EMAIL_TRANSPORT_DEFAULT_PORT` | SMTP port | `587` | For emails |
| `EMAIL_TRANSPORT_DEFAULT_USERNAME` | SMTP username | - | For emails |
| `EMAIL_TRANSPORT_DEFAULT_PASSWORD` | SMTP password | - | For emails |
| `EMAIL_TRANSPORT_DEFAULT_TLS` | Use TLS | `true` | For emails |
| `PASSBOLT_SSL_FORCE` | Force HTTPS | `true` | No |

### SMTP Configuration Examples

**Gmail:**
```yaml
EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.gmail.com"
EMAIL_TRANSPORT_DEFAULT_PORT: "587"
EMAIL_TRANSPORT_DEFAULT_USERNAME: "your-email@gmail.com"
EMAIL_TRANSPORT_DEFAULT_PASSWORD: "your-app-password"
EMAIL_TRANSPORT_DEFAULT_TLS: "true"
```

**AWS SES:**
```yaml
EMAIL_TRANSPORT_DEFAULT_HOST: "email-smtp.us-east-1.amazonaws.com"
EMAIL_TRANSPORT_DEFAULT_PORT: "587"
EMAIL_TRANSPORT_DEFAULT_USERNAME: "your-smtp-username"
EMAIL_TRANSPORT_DEFAULT_PASSWORD: "your-smtp-password"
EMAIL_TRANSPORT_DEFAULT_TLS: "true"
```

**SendGrid:**
```yaml
EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.sendgrid.net"
EMAIL_TRANSPORT_DEFAULT_PORT: "587"
EMAIL_TRANSPORT_DEFAULT_USERNAME: "apikey"
EMAIL_TRANSPORT_DEFAULT_PASSWORD: "your-sendgrid-api-key"
EMAIL_TRANSPORT_DEFAULT_TLS: "true"
```

---

## Backup and Restore

### Backup

#### Complete Backup Script

Create `backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/passbolt_backup_$DATE"

mkdir -p "$BACKUP_PATH"

echo "Starting Passbolt backup..."

# Backup database
echo "Backing up database..."
docker-compose exec -T db mysqldump -u passbolt -ppassbolt passbolt > "$BACKUP_PATH/database.sql"

# Backup GPG keys
echo "Backing up GPG keys..."
docker-compose exec -T passbolt tar czf - /etc/passbolt/gpg > "$BACKUP_PATH/gpg.tar.gz"

# Backup JWT keys
echo "Backing up JWT keys..."
docker-compose exec -T passbolt tar czf - /etc/passbolt/jwt > "$BACKUP_PATH/jwt.tar.gz"

# Backup Passbolt
echo "Backing up Passbolt data..."
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt backup --file /tmp/passbolt-backup.tar.gz" \
  -s /bin/sh www-data
docker-compose cp passbolt:/tmp/passbolt-backup.tar.gz "$BACKUP_PATH/"

# Create archive
cd "$BACKUP_DIR"
tar czf "passbolt_backup_$DATE.tar.gz" "passbolt_backup_$DATE"
rm -rf "passbolt_backup_$DATE"

echo "Backup completed: $BACKUP_DIR/passbolt_backup_$DATE.tar.gz"
```

Make it executable:
```bash
chmod +x backup.sh
```

Run backup:
```bash
./backup.sh
```

#### Automated Backups with Cron

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/passbolt-docker && ./backup.sh >> /var/log/passbolt-backup.log 2>&1
```

### Restore

```bash
#!/bin/bash

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup-file.tar.gz>"
    exit 1
fi

# Extract backup
RESTORE_DIR="./restore_temp"
mkdir -p "$RESTORE_DIR"
tar xzf "$BACKUP_FILE" -C "$RESTORE_DIR"
BACKUP_PATH=$(ls -d "$RESTORE_DIR"/passbolt_backup_*)

# Stop services
docker-compose down

# Restore database
echo "Restoring database..."
docker-compose up -d db
sleep 10
docker-compose exec -T db mysql -u passbolt -ppassbolt passbolt < "$BACKUP_PATH/database.sql"

# Restore GPG keys
echo "Restoring GPG keys..."
docker-compose up -d passbolt
docker-compose exec -T passbolt tar xzf - -C / < "$BACKUP_PATH/gpg.tar.gz"

# Restore JWT keys
echo "Restoring JWT keys..."
docker-compose exec -T passbolt tar xzf - -C / < "$BACKUP_PATH/jwt.tar.gz"

# Restart services
docker-compose restart

# Cleanup
rm -rf "$RESTORE_DIR"

echo "Restore completed!"
```

---

## Maintenance

### Common Commands

```bash
# View logs
docker-compose logs -f passbolt

# View specific service logs
docker-compose logs -f db

# Check container status
docker-compose ps

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Start services
docker-compose up -d

# Update Passbolt
docker-compose pull
docker-compose up -d

# Access container shell
docker-compose exec passbolt /bin/bash

# Run healthcheck
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt healthcheck" \
  -s /bin/sh www-data
```

### User Management

```bash
# List all users
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt list_users" \
  -s /bin/sh www-data

# Delete user
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt delete_user -u user@example.com" \
  -s /bin/sh www-data

# Make user admin
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt make_admin -u user@example.com" \
  -s /bin/sh www-data
```

### Database Maintenance

```bash
# Access MySQL
docker-compose exec db mysql -u passbolt -ppassbolt passbolt

# Optimize database
docker-compose exec db mysqlcheck -u passbolt -ppassbolt --optimize passbolt

# Check database size
docker-compose exec db mysql -u passbolt -ppassbolt -e \
  "SELECT table_schema AS 'Database', 
   ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' 
   FROM information_schema.TABLES 
   WHERE table_schema = 'passbolt';"
```

### Update SSL Certificate

```bash
# Manual renewal
docker-compose run --rm certbot renew

# Restart nginx
docker-compose restart nginx
```

---

## Troubleshooting

### Common Issues

#### 1. Cannot Connect to Database

**Symptoms:** Passbolt shows database connection errors

**Solution:**
```bash
# Check database logs
docker-compose logs db

# Verify database is running
docker-compose ps db

# Test database connection
docker-compose exec db mysql -u passbolt -ppassbolt -e "SHOW DATABASES;"
```

#### 2. GPG Key Issues

**Symptoms:** Cannot decrypt passwords or registration fails

**Solution:**
```bash
# Regenerate GPG keys
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt create_gpg_keys" \
  -s /bin/sh www-data

# Check GPG key
docker-compose exec passbolt su -m -c \
  "gpg --list-keys" \
  -s /bin/sh www-data
```

#### 3. Email Not Sending

**Symptoms:** Registration emails or notifications not received

**Solution:**
```bash
# Test email configuration
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt send_test_email -r recipient@example.com" \
  -s /bin/sh www-data

# Check logs
docker-compose logs passbolt | grep -i email
```

#### 4. Browser Extension Issues

**Symptoms:** Extension cannot connect or shows errors

**Solution:**
- Ensure URL matches `APP_FULL_BASE_URL`
- Check browser console for errors
- Try reinstalling extension
- Clear browser cache and cookies
- Verify SSL certificate is valid (for HTTPS)

#### 5. High CPU/Memory Usage

**Solution:**
```bash
# Check resource usage
docker stats

# Limit resources in docker-compose.yml
services:
  passbolt:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M
```

#### 6. Permission Issues

**Solution:**
```bash
# Fix volume permissions
docker-compose exec passbolt chown -R www-data:www-data /etc/passbolt

# Check file permissions
docker-compose exec passbolt ls -la /etc/passbolt
```

### Logs Location

```bash
# Application logs
docker-compose logs passbolt

# Database logs
docker-compose logs db

# Nginx logs (if using)
docker-compose logs nginx

# Export logs to file
docker-compose logs > passbolt-logs.txt
```

### Health Check

Run comprehensive health check:

```bash
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt healthcheck --verbose" \
  -s /bin/sh www-data
```

---

## Production Best Practices

### 1. Security

#### Strong Passwords
```bash
# Generate strong database password
openssl rand -base64 32

# Store in .env file, never in docker-compose.yml
echo "DB_PASSWORD=$(openssl rand -base64 32)" >> .env
```

#### Environment Variables
```bash
# Use .env file for sensitive data
# Add .env to .gitignore
echo ".env" >> .gitignore
```

#### Regular Updates
```bash
# Update containers monthly
docker-compose pull
docker-compose up -d
```

#### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

#### Fail2ban Protection
```bash
# Install fail2ban
sudo apt install fail2ban

# Create Passbolt filter
sudo nano /etc/fail2ban/filter.d/passbolt.conf
```

```ini
[Definition]
failregex = ^<HOST> .* "POST /auth/login\.json HTTP.*" 401
ignoreregex =
```

```bash
# Configure jail
sudo nano /etc/fail2ban/jail.local
```

```ini
[passbolt]
enabled = true
port = http,https
filter = passbolt
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600
```

### 2. Performance Optimization

#### Database Optimization

Add to `docker-compose.yml`:

```yaml
services:
  db:
    command:
      - --innodb_buffer_pool_size=1G
      - --max_connections=500
      - --innodb_log_file_size=256M
      - --query_cache_size=64M
      - --query_cache_type=1
```

#### Resource Limits

```yaml
services:
  passbolt:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
  
  db:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

#### Enable Caching

Add Redis to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    networks:
      - passbolt_network

  passbolt:
    environment:
      CACHE_DEFAULT_SERVER: "redis"
```

### 3. Monitoring

#### Prometheus + Grafana

Create `monitoring/docker-compose.monitoring.yml`:

```yaml
version: '3.9'

services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - passbolt_network

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "admin"
    networks:
      - passbolt_network

  node-exporter:
    image: prom/node-exporter
    ports:
      - "9100:9100"
    networks:
      - passbolt_network

volumes:
  prometheus_data:
  grafana_data:

networks:
  passbolt_network:
    external: true
```

#### Log Aggregation

Use ELK Stack or Loki for centralized logging:

```yaml
services:
  loki:
    image: grafana/loki
    ports:
      - "3100:3100"
    networks:
      - passbolt_network

  promtail:
    image: grafana/promtail
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./promtail-config.yml:/etc/promtail/config.yml
    networks:
      - passbolt_network
```

### 4. High Availability

#### Database Replication

Use MariaDB master-slave replication:

```yaml
services:
  db-master:
    image: mariadb:10.11
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_REPLICATION_MODE: master
      MYSQL_REPLICATION_USER: repl_user
      MYSQL_REPLICATION_PASSWORD: repl_password

  db-slave:
    image: mariadb:10.11
    environment:
      MYSQL_REPLICATION_MODE: slave
      MYSQL_MASTER_HOST: db-master
      MYSQL_REPLICATION_USER: repl_user
      MYSQL_REPLICATION_PASSWORD: repl_password
```

#### Load Balancing

Use HAProxy or Nginx for load balancing multiple Passbolt instances:

```nginx
upstream passbolt_backend {
    least_conn;
    server passbolt1:80;
    server passbolt2:80;
    server passbolt3:80;
}

server {
    listen 443 ssl http2;
    location / {
        proxy_pass http://passbolt_backend;
    }
}
```

### 5. Backup Strategy

#### Automated Backup with Retention

Create `backup-with-retention.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups/passbolt"
RETENTION_DAYS=30

# Create backup
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/passbolt_$DATE"

mkdir -p "$BACKUP_PATH"

# Backup database
docker-compose exec -T db mysqldump -u passbolt -p$DB_PASSWORD passbolt \
  > "$BACKUP_PATH/database.sql"

# Backup volumes
docker-compose exec -T passbolt tar czf - /etc/passbolt/gpg \
  > "$BACKUP_PATH/gpg.tar.gz"

docker-compose exec -T passbolt tar czf - /etc/passbolt/jwt \
  > "$BACKUP_PATH/jwt.tar.gz"

# Create archive
cd "$BACKUP_DIR"
tar czf "passbolt_$DATE.tar.gz" "passbolt_$DATE"
rm -rf "passbolt_$DATE"

# Remove old backups
find "$BACKUP_DIR" -name "passbolt_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR/passbolt_$DATE.tar.gz"
```

#### Off-site Backup

Upload to S3:

```bash
# Install AWS CLI
pip3 install awscli

# Configure AWS
aws configure

# Add to backup script
aws s3 cp "$BACKUP_DIR/passbolt_$DATE.tar.gz" \
  s3://your-bucket/passbolt-backups/ \
  --storage-class STANDARD_IA
```

### 6. Disaster Recovery

Create a disaster recovery plan:

1. **Regular Testing**: Test restore procedures quarterly
2. **Documentation**: Document all configurations
3. **Monitoring**: Set up alerts for failures
4. **RTO/RPO**: Define Recovery Time Objective and Recovery Point Objective
5. **Runbook**: Create step-by-step recovery procedures

#### Recovery Runbook Template

```markdown
## Passbolt Disaster Recovery

### Pre-requisites
- Latest backup file
- Docker and Docker Compose installed
- Access to production environment

### Recovery Steps
1. Stop production instance (if running)
2. Restore database from backup
3. Restore GPG/JWT keys
4. Update DNS (if needed)
5. Start services
6. Verify functionality
7. Monitor for 24 hours

### Verification Checklist
- [ ] Can login with admin account
- [ ] Can access existing passwords
- [ ] Email notifications working
- [ ] Browser extension connecting
- [ ] SSL certificate valid
```

### 7. Compliance

#### GDPR Compliance

```bash
# Data export for user
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt export_user_data \
  -u user@example.com -o /tmp/user_data.json" \
  -s /bin/sh www-data

# Data deletion
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt delete_user \
  -u user@example.com" \
  -s /bin/sh www-data
```

#### Audit Logging

Enable detailed logging:

```yaml
services:
  passbolt:
    environment:
      DEBUG: "false"
      PASSBOLT_LOG_LEVEL: "info"
      PASSBOLT_SECURITY_AUDIT_ENABLED: "true"
```

### 8. Scaling Checklist

When scaling to production:

- [ ] Use managed database (RDS, Cloud SQL)
- [ ] Implement CDN for static assets
- [ ] Use external Redis/Memcached
- [ ] Set up load balancing
- [ ] Implement database read replicas
- [ ] Configure auto-scaling
- [ ] Set up distributed logging
- [ ] Implement health checks
- [ ] Configure rate limiting
- [ ] Set up DDoS protection
- [ ] Use managed SSL certificates
- [ ] Implement automated backups
- [ ] Configure monitoring and alerting
- [ ] Document runbooks
- [ ] Train operations team

---

## Security Considerations

### 1. Network Security

- Use private networks for database
- Implement firewall rules
- Use VPN for administrative access
- Enable DDoS protection
- Implement rate limiting

### 2. Data Protection

- Encrypt backups
- Use encrypted volumes for sensitive data
- Implement key rotation
- Use secrets management (Vault, AWS Secrets Manager)
- Enable encryption at rest

### 3. Access Control

- Implement 2FA for all users
- Use strong password policies
- Regular access audits
- Principle of least privilege
- Segregation of duties

### 4. Vulnerability Management

- Regular security updates
- Vulnerability scanning
- Penetration testing
- Security audits
- Incident response plan

### 5. Compliance

- GDPR compliance
- SOC 2 requirements
- ISO 27001 standards
- HIPAA (if applicable)
- Regular compliance audits

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This guide is provided as-is under MIT License.

## Support

- [Passbolt Official Documentation](https://www.passbolt.com/docs)
- [Passbolt Community Forum](https://community.passbolt.com/)
- [GitHub Issues](https://github.com/passbolt/passbolt_docker/issues)

---

## Changelog

### v1.0.0 (2024-01-03)
- Initial release
- Development and production setups
- Backup and restore procedures
- Production best practices
- Security guidelines

---

**⚠️ Important Reminders:**

1. **Never use HTTP in production** - Always use HTTPS with valid SSL certificates
2. **Change default passwords** - Use strong, unique passwords
3. **Regular backups** - Automate and test your backup procedures
4. **Keep updated** - Regularly update Docker images and dependencies
5. **Monitor** - Implement comprehensive monitoring and alerting
6. **Document** - Keep your configurations and procedures documented
7. **Test** - Test disaster recovery procedures regularly

---
