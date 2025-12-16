You can organize your Nginx configuration files into separate folders while maintaining proper structure. Here's how to set this up:

### 1. Directory Structure

```
/etc/nginx/
├── nginx.conf
├── conf.d/
│   └── vhosts/
│       ├── app1/
│       │   ├── app1.conf
│       │   └── ssl/
│       │       ├── fullchain.pem
│       │       └── privkey.pem
│       ├── app2/
│       │   ├── app2.conf
│       │   └── ssl/
│       │       ├── fullchain.pem
│       │       └── privkey.pem
│       └── backend/
│           └── backend.conf
```

### 2. Main nginx.conf Configuration

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    # Include all vhosts
    include /etc/nginx/conf.d/vhosts/*.conf;
    
    # Include SSL configuration
    include /etc/nginx/conf.d/vhosts/ssl/*.conf;
    
    # Optional: Include specific app configurations
    include /etc/nginx/conf.d/vhosts/app1/*.conf;
    include /etc/nginx/conf.d/vhosts/app2/*.conf;
    include /etc/nginx/conf.d/vhosts/backend/*.conf;
    
    # Other http settings
    server_names_hash_max_size 512;
    server_names_hash_bucket_size 64;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    
    # SSL session settings
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
}
```

### 3. App1 Configuration File

**/etc/nginx/conf.d/vhosts/app1/app1.conf:**
```nginx
server {
    listen 443 ssl http2;
    server_name app1.yourdomain.com;
    
    # SSL certificate paths
    ssl_certificate /etc/nginx/ssl/app1/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/app1/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Proxy settings
    location / {
        proxy_pass http://k8s-node1:30011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. App2 Configuration File

**/etc/nginx/conf.d/vhosts/app2/app2.conf:**
```nginx
server {
    listen 443 ssl http2;
    server_name app2.yourdomain.com;
    
    # SSL certificate paths
    ssl_certificate /etc/nginx/ssl/app2/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/app2/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Proxy settings
    location / {
        proxy_pass http://k8s-node2:30011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Backend Configuration File

**/etc/nginx/conf.d/vhosts/backend/backend.conf:**
```nginx
server {
    listen 443 ssl http2;
    server_name backend.yourdomain.com;
    
    # SSL certificate paths
    ssl_certificate /etc/nginx/ssl/backend/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/backend/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Proxy settings
    location / {
        proxy_pass http://k8s-node3:30011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. SSL Configuration Files (Optional)

Create separate SSL configuration files for consistency:

**/etc/nginx/conf.d/vhosts/ssl/app1-ssl.conf:**
```nginx
ssl_certificate /etc/nginx/ssl/app1/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/app1/privkey.pem;
```

**/etc/nginx/conf.d/vhosts/ssl/app2-ssl.conf:**
```nginx
ssl_certificate /etc/nginx/ssl/app2/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/app2/privkey.pem;
```

### 7. Verification Steps

1. **Test Configuration:**
   ```bash
   nginx -t
   ```

2. **Reload Nginx:**
   ```bash
   systemctl reload nginx
   ```

3. **Check SSL Certificates:**
   ```bash
   openssl x509 -in /etc/nginx/ssl/app1/fullchain.pem -noout -subject
   ```

### 8. Security Considerations

- **File Permissions:**
  ```bash
  chmod 644 /etc/nginx/ssl/*.pem
  chmod 600 /etc/nginx/ssl/*/*.pem
  chown root:nginx /etc/nginx/ssl/*
  ```

- **Directory Permissions:**
  ```bash
  chmod 755 /etc/nginx/conf.d/vhosts/
  chmod 755 /etc/nginx/conf.d/vhosts/app1/
  chmod 755 /etc/nginx/conf.d/vhosts/app2/
  chmod 755 /etc/nginx/conf.d/vhosts/backend/
  ```

This structure allows you to:
- Keep configuration files organized by application
- Easily manage SSL certificates per application
- Scale to multiple applications with similar patterns
- Maintain consistent security practices across applications

Would you like me to add any specific features like rate limiting, caching, or health checks?
