# Passbolt Docker Setup with Self-Signed SSL Certificate

A comprehensive guide for deploying Passbolt password manager using Docker with self-signed SSL certificates.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Guide](#detailed-setup-guide)
- [Gmail SMTP Configuration](#gmail-smtp-configuration)
- [Creating Admin User](#creating-admin-user)
- [Backup and Restore](#backup-and-restore)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Production Considerations](#production-considerations)

---

## Overview

This guide covers setting up Passbolt with a self-signed SSL certificate for development, testing, or internal network use. 

**⚠️ Warning**: Self-signed certificates are NOT recommended for production environments. For production, use Let's Encrypt or a trusted Certificate Authority.

---

## Prerequisites

- Docker (20.10 or later)
- Docker Compose (2.0 or later)
- OpenSSL (for generating certificates)
- Minimum 2GB RAM
- Minimum 10GB disk space

### Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install docker.io docker-compose openssl
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
sudo yum install docker docker-compose openssl
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**macOS:**
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- OpenSSL is pre-installed

**Windows:**
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Install [OpenSSL for Windows](https://slproweb.com/products/Win32OpenSSL.html)

---

## Quick Start

```bash
# Create project directory
mkdir passbolt-docker && cd passbolt-docker

# Generate SSL certificate
mkdir -p ssl
openssl req -x509 -nodes -days 1825 -newkey rsa:2048 \
  -keyout ssl/passbolt.local.key \
  -out ssl/passbolt.local.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=passbolt.local"

# Create docker-compose.yml (see below)
# Update /etc/hosts
echo "127.0.0.1   passbolt.local" | sudo tee -a /etc/hosts

# Start services
docker-compose up -d

# Create admin user
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt register_user \
  -u admin@example.com \
  -f Admin \
  -l User \
  -r admin" \
  -s /bin/sh www-data
```

---

## Detailed Setup Guide

### 1. Create Project Directory

```bash
mkdir passbolt-docker
cd passbolt-docker
```

### 2. Generate Self-Signed SSL Certificate

```bash
# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate (5 years = 1825 days)
openssl req -x509 -nodes -days 1825 -newkey rsa:4096 \
  -keyout ssl/passbolt.local.key \
  -out ssl/passbolt.local.crt \
  -subj "/C=US/ST=California/L=San Francisco/O=My Organization/CN=passbolt.local"
```

**Certificate Options Explained:**
- `-x509`: Generate a self-signed certificate
- `-nodes`: Don't encrypt the private key
- `-days 1825`: Valid for 5 years
- `-newkey rsa:4096`: Generate 4096-bit RSA key
- `-keyout`: Output path for private key
- `-out`: Output path for certificate
- `-subj`: Certificate subject (customize as needed)

**Customize the subject:**
- `C`: Country (2-letter code, e.g., US, UK, NP)
- `ST`: State/Province
- `L`: City/Locality
- `O`: Organization Name
- `CN`: Common Name (must match your domain)

**Interactive Certificate Generation (optional):**
```bash
openssl req -x509 -nodes -days 1825 -newkey rsa:4096 \
  -keyout ssl/passbolt.local.key \
  -out ssl/passbolt.local.crt
```
This will prompt you for certificate details.

### 3. Create Environment File

Create `.env` file for sensitive data:

```bash
cat > .env << 'EOF'
# Database Configuration
DB_PASSWORD=change_this_secure_password_123!

# Email Configuration
EMAIL_FROM=no-reply@passbolt.local

# Gmail SMTP (Optional - see Gmail SMTP section)
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
EOF
```

**Important:** Add `.env` to `.gitignore`:
```bash
echo ".env" >> .gitignore
```

### 4. Create Docker Compose File

Create `docker-compose.yml`:

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
      MYSQL_PASSWORD: "${DB_PASSWORD}"
    volumes:
      - db_data:/var/lib/mysql
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
      APP_FULL_BASE_URL: "https://passbolt.local"
      DATASOURCES_DEFAULT_HOST: "db"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "${DB_PASSWORD}"
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_DEFAULT_FROM: "${EMAIL_FROM}"
      EMAIL_TRANSPORT_DEFAULT_HOST: "localhost"
      EMAIL_TRANSPORT_DEFAULT_PORT: "25"
    volumes:
      - gpg_data:/etc/passbolt/gpg
      - jwt_data:/etc/passbolt/jwt
      - ./ssl/passbolt.local.crt:/etc/ssl/certs/passbolt.crt:ro
      - ./ssl/passbolt.local.key:/etc/ssl/certs/passbolt.key:ro
    ports:
      - "443:443"
      - "80:80"
    networks:
      - passbolt_network
    command:
      [
        "/usr/bin/wait-for.sh",
        "-t",
        "0",
        "db:3306",
        "--",
        "/docker-entrypoint.sh",
      ]

volumes:
  db_data:
  gpg_data:
  jwt_data:

networks:
  passbolt_network:
    driver: bridge
```

### 5. Update Hosts File

Add Passbolt domain to your hosts file:

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

### 6. Start Passbolt

```bash
# Start containers in detached mode
docker-compose up -d

# Check container status
docker-compose ps

# Follow logs
docker-compose logs -f passbolt
```

Wait 30-60 seconds for services to initialize.

### 7. Verify Installation

```bash
# Check health
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt healthcheck" \
  -s /bin/sh www-data

# Check if services are running
docker-compose ps
```

Expected output shows all services as "Up" or "healthy".

---

## Gmail SMTP Configuration

To enable email notifications via Gmail:

### Step 1: Generate Gmail App Password

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google Account Security](https://myaccount.google.com/security)
3. Click **2-Step Verification** → **App passwords**
4. Select **Mail** and **Other (Custom name)**
5. Enter "Passbolt SMTP" and click **Generate**
6. **Copy the 16-character password**

### Step 2: Update Configuration

**Option A: Update .env file (Recommended)**

```bash
# Edit .env
nano .env
```

Add/update these lines:
```bash
# Gmail SMTP Configuration
EMAIL_FROM=your-email@gmail.com
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx  # 16-char app password (no spaces)
```

**Option B: Update docker-compose.yml directly**

Add to passbolt service environment:
```yaml
environment:
  EMAIL_DEFAULT_FROM: "your-email@gmail.com"
  EMAIL_TRANSPORT_DEFAULT_CLASS_NAME: "Smtp"
  EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.gmail.com"
  EMAIL_TRANSPORT_DEFAULT_PORT: "587"
  EMAIL_TRANSPORT_DEFAULT_TLS: "true"
  EMAIL_TRANSPORT_DEFAULT_USERNAME: "your-email@gmail.com"
  EMAIL_TRANSPORT_DEFAULT_PASSWORD: "xxxxxxxxxxxxxxxx"
```

### Step 3: Restart Services

```bash
docker-compose restart passbolt
```

### Step 4: Test Email

```bash
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt send_test_email \
  --recipient test@example.com" \
  -s /bin/sh www-data
```

**Complete docker-compose.yml with Gmail:**

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
      MYSQL_PASSWORD: "${DB_PASSWORD}"
    volumes:
      - db_data:/var/lib/mysql
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
      # Application
      APP_FULL_BASE_URL: "https://passbolt.local"
      
      # Database
      DATASOURCES_DEFAULT_HOST: "db"
      DATASOURCES_DEFAULT_USERNAME: "passbolt"
      DATASOURCES_DEFAULT_PASSWORD: "${DB_PASSWORD}"
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      
      # Gmail SMTP
      EMAIL_DEFAULT_FROM_NAME: "Passbolt"
      EMAIL_DEFAULT_FROM: "${GMAIL_ADDRESS}"
      EMAIL_TRANSPORT_DEFAULT_CLASS_NAME: "Smtp"
      EMAIL_TRANSPORT_DEFAULT_HOST: "smtp.gmail.com"
      EMAIL_TRANSPORT_DEFAULT_PORT: "587"
      EMAIL_TRANSPORT_DEFAULT_TLS: "true"
      EMAIL_TRANSPORT_DEFAULT_USERNAME: "${GMAIL_ADDRESS}"
      EMAIL_TRANSPORT_DEFAULT_PASSWORD: "${GMAIL_APP_PASSWORD}"
      
    volumes:
      - gpg_data:/etc/passbolt/gpg
      - jwt_data:/etc/passbolt/jwt
      - ./ssl/passbolt.local.crt:/etc/ssl/certs/passbolt.crt:ro
      - ./ssl/passbolt.local.key:/etc/ssl/certs/passbolt.key:ro
    ports:
      - "443:443"
      - "80:80"
    networks:
      - passbolt_network
    command:
      [
        "/usr/bin/wait-for.sh",
        "-t",
        "0",
        "db:3306",
        "--",
        "/docker-entrypoint.sh",
      ]

volumes:
  db_data:
  gpg_data:
  jwt_data:

networks:
  passbolt_network:
    driver: bridge
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

**Parameters:**
- `-u`: Email address (will be username)
- `-f`: First name
- `-l`: Last name
- `-r`: Role (`admin` or `user`)

**Output:**
```
User saved successfully.
To start registration follow the link provided in your mailbox or here:
https://passbolt.local/setup/install/...
```

### Complete Registration

1. Copy the registration URL from the output
2. Open it in your browser
3. **Accept the SSL certificate warning** (this is expected with self-signed certificates)
4. Install the Passbolt browser extension:
   - [Chrome/Edge](https://chrome.google.com/webstore/detail/passbolt/didegimhafipceonhjepacocaffmoppf)
   - [Firefox](https://addons.mozilla.org/firefox/addon/passbolt/)
5. Follow the setup wizard:
   - Generate or import GPG key
   - Set your master password
   - Download recovery kit (keep it safe!)
6. Complete account setup

### Access Passbolt

Navigate to: `https://passbolt.local`

**Browser Warning:** Your browser will show a security warning because the certificate is self-signed. This is normal. Click "Advanced" → "Proceed to passbolt.local" (or similar).

**For Chrome:**
1. Click "Advanced"
2. Click "Proceed to passbolt.local (unsafe)"

**For Firefox:**
1. Click "Advanced"
2. Click "Accept the Risk and Continue"

---

## Backup and Restore

### Complete Backup

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
docker-compose exec -T db mysqldump -u passbolt -p"${DB_PASSWORD}" passbolt \
  > "$BACKUP_PATH/database.sql"

# Backup GPG keys
echo "Backing up GPG keys..."
docker-compose exec -T passbolt tar czf - /etc/passbolt/gpg \
  > "$BACKUP_PATH/gpg.tar.gz"

# Backup JWT keys
echo "Backing up JWT keys..."
docker-compose exec -T passbolt tar czf - /etc/passbolt/jwt \
  > "$BACKUP_PATH/jwt.tar.gz"

# Backup SSL certificates
echo "Backing up SSL certificates..."
cp -r ssl "$BACKUP_PATH/"

# Create archive
cd "$BACKUP_DIR"
tar czf "passbolt_backup_$DATE.tar.gz" "passbolt_backup_$DATE"
rm -rf "passbolt_backup_$DATE"

echo "Backup completed: $BACKUP_DIR/passbolt_backup_$DATE.tar.gz"
```

Make executable and run:
```bash
chmod +x backup.sh
./backup.sh
```

### Restore from Backup

Create `restore.sh`:

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
docker-compose exec -T db mysql -u passbolt -p"${DB_PASSWORD}" passbolt \
  < "$BACKUP_PATH/database.sql"

# Restore volumes
echo "Restoring GPG keys..."
docker-compose up -d passbolt
docker-compose exec -T passbolt tar xzf - -C / < "$BACKUP_PATH/gpg.tar.gz"

echo "Restoring JWT keys..."
docker-compose exec -T passbolt tar xzf - -C / < "$BACKUP_PATH/jwt.tar.gz"

# Restore SSL certificates
echo "Restoring SSL certificates..."
cp -r "$BACKUP_PATH/ssl" ./

# Restart services
docker-compose restart

# Cleanup
rm -rf "$RESTORE_DIR"

echo "Restore completed!"
```

Make executable:
```bash
chmod +x restore.sh
```

Run restore:
```bash
./restore.sh backups/passbolt_backup_20240103_120000.tar.gz
```

### Automated Backups

Add to crontab:
```bash
crontab -e
```

Add daily backup at 2 AM:
```
0 2 * * * cd /path/to/passbolt-docker && ./backup.sh >> /var/log/passbolt-backup.log 2>&1
```

---

## Maintenance

### Common Commands

```bash
# View logs
docker-compose logs -f passbolt

# View all logs
docker-compose logs -f

# Check container status
docker-compose ps

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Start services
docker-compose up -d

# Update Passbolt
docker-compose pull passbolt
docker-compose up -d passbolt

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

# Create new user
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt register_user \
  -u user@example.com -f First -l Last -r user" \
  -s /bin/sh www-data

# Delete user
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt delete_user \
  -u user@example.com" \
  -s /bin/sh www-data

# Make user admin
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt make_admin \
  -u user@example.com" \
  -s /bin/sh www-data
```

### Database Maintenance

```bash
# Access MySQL
docker-compose exec db mysql -u passbolt -p"${DB_PASSWORD}" passbolt

# Optimize database
docker-compose exec db mysqlcheck -u passbolt -p"${DB_PASSWORD}" \
  --optimize passbolt

# Check database size
docker-compose exec db mysql -u passbolt -p"${DB_PASSWORD}" -e \
  "SELECT table_schema AS 'Database', 
   ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' 
   FROM information_schema.TABLES 
   WHERE table_schema = 'passbolt';"
```

### SSL Certificate Renewal

If your certificate expires (after 5 years):

```bash
# Regenerate certificate
openssl req -x509 -nodes -days 1825 -newkey rsa:4096 \
  -keyout ssl/passbolt.local.key \
  -out ssl/passbolt.local.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=passbolt.local"

# Restart Passbolt
docker-compose restart passbolt
```

---

## Troubleshooting

### Issue 1: Cannot Access Passbolt

**Symptoms:** Browser cannot reach https://passbolt.local

**Solutions:**

1. **Check if containers are running:**
```bash
docker-compose ps
```

2. **Verify hosts file:**
```bash
cat /etc/hosts | grep passbolt.local
```
Should show: `127.0.0.1   passbolt.local`

3. **Check if ports are in use:**
```bash
sudo netstat -tulpn | grep -E ':(80|443)'
```

4. **Check firewall:**
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443

# CentOS/RHEL
sudo firewall-cmd --list-all
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

### Issue 2: SSL Certificate Errors

**Symptoms:** Browser shows SSL errors or won't proceed

**Solutions:**

1. **Verify certificate files exist:**
```bash
ls -lh ssl/
```

2. **Check certificate validity:**
```bash
openssl x509 -in ssl/passbolt.local.crt -text -noout
```

3. **Verify certificate mounted in container:**
```bash
docker-compose exec passbolt ls -lh /etc/ssl/certs/ | grep passbolt
```

4. **Regenerate certificate:**
```bash
rm ssl/*
openssl req -x509 -nodes -days 1825 -newkey rsa:4096 \
  -keyout ssl/passbolt.local.key \
  -out ssl/passbolt.local.crt \
  -subj "/C=US/ST=State/L=City/O=Org/CN=passbolt.local"
docker-compose restart passbolt
```

### Issue 3: Database Connection Failed

**Symptoms:** Passbolt shows database errors

**Solutions:**

1. **Check database logs:**
```bash
docker-compose logs db
```

2. **Verify database is running:**
```bash
docker-compose ps db
```

3. **Test database connection:**
```bash
docker-compose exec db mysql -u passbolt -p"${DB_PASSWORD}" -e "SHOW DATABASES;"
```

4. **Check password matches:**
```bash
grep DB_PASSWORD .env
```

### Issue 4: GPG Key Issues

**Symptoms:** Cannot decrypt passwords, registration fails

**Solutions:**

1. **Check GPG keys exist:**
```bash
docker-compose exec passbolt ls -lh /etc/passbolt/gpg/
```

2. **Regenerate GPG keys:**
```bash
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt create_gpg_keys" \
  -s /bin/sh www-data
```

3. **Verify GPG keys:**
```bash
docker-compose exec passbolt su -m -c \
  "gpg --list-keys" \
  -s /bin/sh www-data
```

### Issue 5: Email Not Sending

**Symptoms:** Registration emails not received

**Solutions:**

1. **Test email configuration:**
```bash
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt send_test_email \
  -r test@example.com" \
  -s /bin/sh www-data
```

2. **Check email logs:**
```bash
docker-compose logs passbolt | grep -i "mail\|smtp\|email"
```

3. **Verify Gmail settings (if using Gmail):**
   - Ensure 2FA is enabled
   - App password is correct (16 characters, no spaces)
   - Check `.env` file for correct credentials

### Issue 6: Browser Extension Not Working

**Symptoms:** Extension shows connection errors

**Solutions:**

1. **Verify URL matches:**
   - Extension settings should show: `https://passbolt.local`
   - Must match `APP_FULL_BASE_URL` in docker-compose.yml

2. **Clear browser data:**
   - Clear cache and cookies for passbolt.local
   - Restart browser

3. **Reinstall extension:**
   - Remove extension
   - Restart browser
   - Reinstall extension

4. **Check browser console:**
   - Open Developer Tools (F12)
   - Check Console tab for errors

### Issue 7: Permission Denied Errors

**Solutions:**

```bash
# Fix volume permissions
docker-compose exec passbolt chown -R www-data:www-data /etc/passbolt

# Fix SSL certificate permissions
chmod 644 ssl/passbolt.local.crt
chmod 600 ssl/passbolt.local.key
```

### View All Logs

```bash
# Export all logs
docker-compose logs > passbolt-debug.log

# View specific service
docker-compose logs passbolt
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f
```

### Health Check

```bash
# Comprehensive health check
docker-compose exec passbolt su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt healthcheck --verbose" \
  -s /bin/sh www-data
```

---

## Production Considerations

### Why Self-Signed Certificates Are Not Recommended

1. **Browser Warnings:** Users must manually accept certificate warnings
2. **No Trust Chain:** No validation from trusted Certificate Authority
3. **Security Risks:** Susceptible to man-in-the-middle attacks
4. **Mobile Issues:** Mobile devices may not accept self-signed certificates
5. **Extension Problems:** Browser extensions may have issues

### When to Use Self-Signed Certificates

✅ **Acceptable for:**
- Local development
- Testing environments
- Internal networks (intranet)
- Learning/training purposes
- Proof of concept

❌ **NOT acceptable for:**
- Production environments
- Public-facing deployments
- External user access
- Sensitive data (unless on isolated network)

### Migrating to Production SSL

For production use, consider:

1. **Let's Encrypt (Free):**
   - Automated certificate renewal
   - Trusted by all browsers
   - Easy setup with Certbot

2. **Commercial SSL Certificates:**
   - Extended validation options
   - Warranty coverage
   - Customer support

3. **Reverse Proxy:**
   - Use Nginx or Traefik
   - Automated SSL management
   - Load balancing capabilities

**Quick Migration to Let's Encrypt:**

See the [Production Best Practices](#production-best-practices) section in the full guide for Let's Encrypt setup.

---

## Security Best Practices

### 1. Change Default Passwords

```bash
# Generate strong password
openssl rand -base64 32

# Update .env file
DB_PASSWORD=$(openssl rand -base64 32)
```

### 2. Protect Sensitive Files

```bash
# Set proper permissions
chmod 600 .env
chmod 600 ssl/passbolt.local.key
chmod 644 ssl/passbolt.local.crt

# Add to .gitignore
cat >> .gitignore << EOF
.env
ssl/
backups/
*.log
EOF
```

### 3. Regular Updates

```bash
# Update containers monthly
docker-compose pull
docker-compose up -d
```

### 4. Enable Firewall

```bash
# Ubuntu/Debian (UFW)
sudo ufw enable
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 5. Limit Access

Only expose ports on specific interfaces:

```yaml
ports:
  - "127.0.0.1:443:443"  # Only localhost
  - "127.0.0.1:80:80"    # Only localhost
```

Or use a VPN for access to internal deployments.

### 6. Monitor Logs

```bash
# Set up log monitoring
docker-compose logs -f | tee -a /var/log/passbolt.log
```

### 7. Implement Backups

- Automated daily backups
- Off-site backup storage
- Test restore procedures
- 30-day retention minimum

---

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| Start Passbolt | `docker-compose up -d` |
| Stop Passbolt | `docker-compose down` |
| View logs | `docker-compose logs -f passbolt` |
| Restart | `docker-compose restart` |
| Update | `docker-compose pull && docker-compose up -d` |
| Backup | `./backup.sh` |
| Create user | See [Creating Admin User](#creating-admin-user) |
| Health check | See [Maintenance](#maintenance) |

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_FULL_BASE_URL` | Full URL to Passbolt | `https://passbolt.local` |
| `DB_PASSWORD` | Database password | Strong random password |
| `EMAIL_FROM` | Default sender email | `no-reply@passbolt.local` |
| `GMAIL_ADDRESS` | Gmail SMTP username | `your-email@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail app password | 16-char password |

### File Structure

```
passbolt-docker/
├── docker-compose.yml
├── .env
├── .gitignore
├── ssl/
│   ├── passbolt.local.crt
│   └── passbolt.local.key
├── backup.sh
├── restore.sh
└── backups/
    └── passbolt_backup_*.tar.gz
```

---

## Frequently Asked Questions

### Q: Can I use a different domain name?
**A:** Yes, replace `passbolt.local` with your desired domain in:
- SSL certificate generation (`-subj` parameter)
- `/etc/hosts` file
- `APP_FULL_BASE_URL` in docker-compose.yml

### Q: How do I change the database password?
**A:** 
1. Update password in `.env` file
2. Run `docker-compose down`
3. Remove database volume: `docker volume rm passbolt-docker_db_data`
4. Run `docker-compose up -d`

### Q: Can multiple users access Passbolt?
**A:** Yes, create additional users with the register_user command or via the web interface (Admin → Users → Create).

### Q: How do I upgrade Passbolt?
**A:** Run `docker-compose pull` then `docker-compose up -d`

### Q: Is this setup secure enough for my team?
**A:** For internal networks: Yes, if properly configured. For production/internet-facing: No, use Let's Encrypt instead.

### Q: What if I lose my master password?
**A:** Download and store your recovery kit during setup. Without it, passwords cannot be recovered.

### Q: Can I import passwords from other managers?
**A:** Yes, Passbolt supports importing from various formats via the web interface.

---

## Additional Resources

- [Passbolt Official Documentation](https://www.passbolt.com/docs)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Passbolt Community Forum](https://community.passbolt.com/)
- [GitHub Repository](https://github.com/
