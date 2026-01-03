Set up Passbolt in a Docker container with a self-signed SSL certificate. Here's a complete guide:

## Prerequisites
- Docker and Docker Compose installed
- `openssl` for generating SSL certificates

## Step-by-Step Setup

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
openssl req -x509 -nodes -days 1825 -newkey rsa:2048 \
  -keyout ssl/passbolt.local.key \
  -out ssl/passbolt.local.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=passbolt.local"
```

### 3. Create Docker Compose File

Create a `docker-compose.yml`:

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
      MYSQL_PASSWORD: "P@ssw0rd123"  # Change this!
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - passbolt_network

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
      DATASOURCES_DEFAULT_PASSWORD: "P@ssw0rd123"  # Match DB password
      DATASOURCES_DEFAULT_DATABASE: "passbolt"
      EMAIL_DEFAULT_FROM: "sagarmalla08@gmail.com" # change this
      EMAIL_TRANSPORT_DEFAULT_HOST: "localhost"  # Configure SMTP if needed
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
    command: >
      /bin/bash -c "
      if [ ! -f /etc/passbolt/gpg/serverkey_private.asc ]; then
        /usr/share/php/passbolt/bin/cake passbolt create_jwt_keys &&
        /usr/share/php/passbolt/bin/cake passbolt install --force;
      fi &&
      /docker-entrypoint.sh"

volumes:
  db_data:
  gpg_data:
  jwt_data:

networks:
  passbolt_network:
    driver: bridge
```

### 4. Configure NGINX for SSL (Alternative Approach)

If you want more control over SSL, create an `nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name passbolt.local;

    ssl_certificate /etc/ssl/certs/passbolt.crt;
    ssl_certificate_key /etc/ssl/certs/passbolt.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location / {
        proxy_pass http://passbolt:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}

server {
    listen 80;
    server_name passbolt.local;
    return 301 https://$server_name$request_uri;
}
```

### 5. Update /etc/hosts

Add Passbolt domain to your hosts file:

```bash
sudo vi /etc/hosts
```

Add this line:
```
127.0.0.1   passbolt.local
```

### 6. Start Passbolt

```bash
# Start containers
docker-compose up -d

# Check logs
docker-compose logs -f passbolt
```

### 7. Create Admin User

```bash
# Wait for containers to be ready (30-60 seconds)
# Then create admin user
docker exec passbolt_app su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt register_user \
  -u sagarmalla08@gmail.com \
  -f Sagar \
  -l Malla \
  -r admin" \
  -s /bin/sh www-data
```

This will output a registration URL. Copy and open it in your browser.

### 8. Access Passbolt

1. Navigate to `https://passbolt.local`
2. Your browser will warn about the self-signed certificate - accept it
3. Complete the setup wizard with the registration link
4. Install the Passbolt browser extension
5. Complete your account setup

### 9. Useful Commands

```bash
# Stop containers
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Backup
docker exec passbolt_app su -m -c \
  "/usr/share/php/passbolt/bin/cake passbolt backup" \
  -s /bin/sh www-data
```

## Important Notes

1. **Change default passwords** in the docker-compose.yml
2. For production, configure proper SMTP settings for email
3. The self-signed certificate will show browser warnings - this is expected
4. Keep your GPG keys backed up (they're in the `gpg_data` volume)
