# NGINX Setup on RHEL for AWS S3 Proxy

This document details the setup of NGINX on a Red Hat Enterprise Linux (RHEL) server with the `ngx_http_perl_module` to proxy encrypted log files to an AWS S3 bucket. It covers installation, configuration, and troubleshooting steps performed in June 2025. The NGINX user is created before setting permissions, and the `.env` file is configured before enabling and reloading the NGINX service.

## Prerequisites

- RHEL system with root access.
- AWS S3 bucket (`logging-nginx`) and credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
- Internet access for downloading packages and NGINX source.
- Basic familiarity with Linux commands, NGINX, and AWS.

## System Preparation

1. **Register System with Subscription Manager**:

   ```bash
   sudo subscription-manager register
   ```

   - Registers the system to access RHEL repositories.

2. **Update System**:

   ```bash
   sudo dnf update -y
   ```

3. **Install Required Tools**:

   ```bash
   sudo dnf install -y wget
   sudo dnf groupinstall -y "Development Tools"
   sudo dnf install -y pcre-devel openssl-devel zlib-devel perl-devel perl-ExtUtils-Embed ca-certificates perl-Digest-SHA
   ```

   - Installs `wget`, development tools, and dependencies for NGINX compilation (PCRE, OpenSSL, zlib, Perl) and Perl modules (`Digest::SHA`).

## NGINX Installation

1. **Download NGINX Source**:

   ```bash
   cd /opt
   wget https://nginx.org/download/nginx-1.26.0.tar.gz
   tar xvzf nginx-1.26.0.tar.gz
   rm -rvf nginx-1.26.0.tar.gz
   cd nginx-1.26.0
   ```

2. **Create NGINX User**:

   ```bash
   sudo useradd --system --no-create-home --shell /sbin/nologin nginx
   ```

   - Creates a system user `nginx` for running the NGINX process, ensuring it has no home directory or login shell.

3. **Create Directories**:

   ```bash
   mkdir -p /var/lib/nginx/body
   mkdir -p /var/lib/nginx/proxy
   mkdir -p /var/log/nginx
   mkdir -p /usr/lib/nginx/modules
   mkdir -p /var/cache/nginx/client_temp
   mkdir -p /etc/nginx/run
   ```

   - Set ownership and permissions:

     ```bash
     chown -R nginx:nginx /var/lib/nginx /var/log/nginx /var/cache/nginx /etc/nginx/run
     chmod -R 755 /var/cache/nginx /var/log/nginx /etc/nginx/run
     chmod 755 /var/cache/nginx/client_temp
     ```

4. **Configure NGINX**:

   ```bash
   ./configure \
     --prefix=/etc/nginx \
     --sbin-path=/usr/sbin/nginx \
     --conf-path=/etc/nginx/nginx.conf \
     --pid-path=/etc/nginx/run/nginx.pid \
     --lock-path=/var/lock/nginx.lock \
     --modules-path=/usr/lib/nginx/modules \
     --http-log-path=/var/log/nginx/access.log \
     --error-log-path=/var/log/nginx/error.log \
     --http-client-body-temp-path=/var/lib/nginx/body \
     --http-proxy-temp-path=/var/lib/nginx/proxy \
     --with-http_perl_module=dynamic \
     --with-http_ssl_module \
     --with-compat
   ```

   - Enables dynamic Perl module and SSL support for HTTPS proxying to S3.

5. **Compile and Install**:

   ```bash
   make -j$(nproc)
   sudo make install
   ```

6. **Verify Perl Module**:

   ```bash
   ls /usr/lib/nginx/modules/ngx_http_perl_module.so
   nginx -V 2>&1 | grep perl
   ```

## NGINX Service Setup

1. **Create Systemd Service**:

   ```bash
   sudo vi /etc/systemd/system/nginx.service
   ```

   Content:

   ```ini
   [Unit]
   Description=A high performance web server and a reverse proxy server
   After=network.target

   [Service]
   Type=forking
   PIDFile=/etc/nginx/run/nginx.pid
   EnvironmentFile=/etc/nginx/.env
   ExecStartPre=/usr/sbin/nginx -t -c /etc/nginx/nginx.conf
   ExecStart=/usr/sbin/nginx -c /etc/nginx/nginx.conf
   ExecReload=/usr/sbin/nginx -s reload
   ExecStop=/usr/sbin/nginx -s quit
   PrivateTmp=true

   [Install]
   WantedBy=multi-user.target
   ```

2. **Set Up Environment Variables**:

   ```bash
   sudo vi /etc/nginx/.env
   ```

   Example content:

   ```
   AWS_S3_BUCKET=logging-nginx
   AWS_REGION=eu-north-1
   AWS_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxx
   AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxx
   ```

   - Set permissions:

     ```bash
     sudo chown nginx:nginx /etc/nginx/.env
     sudo chmod 600 /etc/nginx/.env
     ```

3. **Enable and Start Service**:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable nginx
   sudo systemctl start nginx
   sudo systemctl status nginx
   ```

4. **Reload Configuration**:

   ```bash
   nginx -t
   nginx -s reload
   ```

## NGINX Configuration

1. **Edit Configuration**:

   ```bash
   sudo vi /etc/nginx/nginx.conf
   ```

   ```
   load_module /usr/lib/nginx/modules/ngx_http_perl_module.so;

   env AWS_S3_BUCKET;
   env AWS_REGION;
   env AWS_ACCESS_KEY_ID;
   env AWS_SECRET_ACCESS_KEY;

   user nginx;
   worker_processes auto;
   worker_rlimit_nofile 200000;
   pcre_jit on;

   error_log /var/log/nginx/error.log warn;
   pid /etc/nginx/run/nginx.pid;

   events {
      worker_connections 10240;
      multi_accept on;
      use epoll;
   }

   http {
      include /etc/nginx/mime.types;
      default_type application/json;

      resolver 8.8.8.8 1.1.1.1;


      log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                     '$status $body_bytes_sent "$http_referer" '
                     '"$http_user_agent" "$http_x_forwarded_for"';

      log_format custom
         '[$time_local] '
         '$remote_addr - $remote_user - $server_name to: $upstream_addr '
         '$request '
         'upstream_response_time $upstream_response_time '
         'msec $msec '
         'request_time $request_time '
         'status $upstream_status';
      access_log /var/log/nginx/nginx-to-bucket.log custom;

      access_log /var/log/nginx/access.log main;
      server_tokens off;
      sendfile on;
      add_header Cache-Control no-cache;
      keepalive_timeout 65;
      gzip on;
      gzip_vary on;

      client_max_body_size 10G;
      client_body_timeout 300s;
      client_body_buffer_size 128k;
      client_body_temp_path /var/cache/nginx/client_temp 1 2;

      # AWS Configuration
      perl_set $aws_s3_bucket 'sub { return $ENV{"AWS_S3_BUCKET"}; }';
      perl_set $aws_region 'sub { return $ENV{"AWS_REGION"}; }';
      perl_set $aws_access_key_id 'sub { return $ENV{"AWS_ACCESS_KEY_ID"}; }';
      perl_set $aws_secret_access_key 'sub { return $ENV{"AWS_SECRET_ACCESS_KEY"}; }';

      perl_set $aws_s3_key 'sub {
            my $r = shift;
            my $uri = $r->uri;
            my $folder = $r->variable("log_folder") || "logs";
            $uri =~ s/^\/+//;
            return "$folder/" . $uri;
      }';

      perl_set $aws_s3_endpoint 'sub {
         my $r = shift;
         return $r->variable("aws_s3_bucket").".s3.".$r->variable("aws_region").".amazonaws.com";
      }';

      perl_set $x_amz_date 'sub {
         use POSIX qw(strftime);
         return strftime "%Y%m%dT%H%M%SZ", gmtime;
      }';

      perl_set $x_amz_content_sha256 'sub {
         my $r = shift;
         my $client_sha256 = $r->header_in("X-Content-SHA256");
         if ($client_sha256) {
               return $client_sha256;
         }
         use Digest::SHA qw(sha256_hex);
         my $body = $r->request_body;
         return sha256_hex($body);
      }';

      perl_set $aws_authorization_header 'sub {
         use Digest::SHA qw(hmac_sha256 hmac_sha256_hex);
         use POSIX qw(strftime);
         use Encode qw(encode_utf8);

         my $r = shift;
         my $aws_access_key_id = $r->variable("aws_access_key_id");
         my $aws_secret_access_key = $r->variable("aws_secret_access_key");
         my $aws_region = $r->variable("aws_region");
         my $aws_s3_bucket = $r->variable("aws_s3_bucket");
         my $aws_s3_key = $r->variable("aws_s3_key");
         my $x_amz_date = $r->variable("x_amz_date");
         my $x_amz_acl = "public-read";
         my $x_amz_content_sha256 = $r->variable("x_amz_content_sha256");
         my $content_type = $r->variable("content_type");
         my $host = $aws_s3_bucket.".s3.".$aws_region.".amazonaws.com";

         my $canonical_request = "PUT\n"
                                 . "/$aws_s3_key\n"
                                 . "\n"
                                 . "content-type:$content_type\n"
                                 . "host:$host\n"
                                 . "x-amz-content-sha256:$x_amz_content_sha256\n"
                                 . "x-amz-date:$x_amz_date\n"
                                 . "\n"
                                 . "content-type;host;x-amz-content-sha256;x-amz-date\n"
                                 . "$x_amz_content_sha256";

         my $datestamp = substr($x_amz_date, 0, 8);
         my $credential_scope = "$datestamp/$aws_region/s3/aws4_request";
         my $canonical_request_hex = sha256_hex(encode_utf8($canonical_request));
         my $string_to_sign = "AWS4-HMAC-SHA256\n"
                              . "$x_amz_date\n"
                              . "$credential_scope\n"
                              . "$canonical_request_hex";

         my $signing_key = hmac_sha256(encode_utf8("aws4_request"),
                           hmac_sha256(encode_utf8("s3"),
                           hmac_sha256(encode_utf8($aws_region),
                           hmac_sha256(encode_utf8($datestamp),
                           encode_utf8("AWS4$aws_secret_access_key")))));

         my $signature = hmac_sha256_hex(encode_utf8($string_to_sign), $signing_key);

         return "AWS4-HMAC-SHA256 "
               . "Credential=$aws_access_key_id/$credential_scope,"
               . "SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date,"
               . "Signature=$signature";
      }';

      server {
         listen 8081 default_server;

         location /check {
               return 200 '{ "service": "files", "status": "healthy", "version": "1.3.0" }';
         }

         location / {
               set $log_folder $http_x_log_folder;
               if ($log_folder = "") {
                  set $log_folder "logs";
               }

               if ($request_method != POST) {
                  return 404;
               }

               if ($request_uri !~ \.gpg$) {
                  return 400 '{"error": "Only password protected gpg files are accepted."}';
               }

               if ($content_type !~ (application/octet-stream)) {
                  return 415 '{"error": "Unsupported content type. Use application/octet-stream."}';
               }

               #client_max_body_size 0;
               proxy_request_buffering off;
               proxy_buffering off;
               proxy_no_cache $x_amz_date;
               proxy_method PUT;
               proxy_set_header Authorization $aws_authorization_header;
               proxy_set_header x-amz-content-sha256 $x_amz_content_sha256;
               proxy_set_header x-amz-date $x_amz_date;
               proxy_hide_header x-amz-id-2;
               proxy_hide_header x-amz-request-id;
               proxy_pass "https://$aws_s3_endpoint/$aws_s3_key";

               proxy_connect_timeout 300s;
               proxy_send_timeout 1800s;
               proxy_read_timeout 1800s;
         }
      }
   }
   ```

   Key features:

   - Loads `ngx_http_perl_module` dynamically.
   - Proxies POST requests with `.gpg` files to S3 using AWS v4 signatures.
   - Uses Perl to set AWS headers (`Authorization`, `x-amz-content-sha256`, `x-amz-date`).
   - Custom log format for S3 uploads.
   - Listens on port 8081 with a health check endpoint (`/check`).
   - Uses resolver `8.8.8.8 1.1.1.1` for DNS.
   - See provided `nginx.conf` for full details.

2. **Test Configuration**:

   ```bash
   nginx -t
   nginx -s reload
   curl localhost:8081/check
   ```


## Log Upload Script

1. **Create Script**:

   ```bash
   mkdir -p /opt/scripts
   cd /opt/scripts
   vi logs-s3.sh
   ```

   ```
   #!/bin/bash

   # empty the trace log each time of script runs.
   > trace.log

   # Get the hostname
   hostname=$HOSTNAME # user-01.esewa.com.np


   tmpDir="/home" # Temp path for the newly create tar and gpg file.

   # Extract full host part before the first dot
   host_part=$(echo "$HOSTNAME" | cut -d'.' -f1) # user-01
   host_module=$(echo "$host_part" | cut -d'-' -f1) # user
   log_path="/var/log"
   timestamp=$(date +"%Y-%m-%d-%H%M%S")

   # Determine the host based on the prefix
   if [[ "$hostname" == ip-* ]]; then
      env_hostname="cloud-vm"
      echo "$host"
   elif [[ "$hostname" == kub-* ]]; then
      env_hostname="prod-k3s"
      echo "$host"
   else
      env_hostname="prod-vm"
      echo "$host"
   fi

   echo "Detected host type: $env_hostname"
   # Input parameters
   FOLDER_PATH="$log_path" # path of the source logs
   FOLDER_NAME="$host_part"
   NEW_NAME="$1"

   # Filenames
   TAR_NAME="$tmpDir/${FOLDER_NAME}_${timestamp}.tar"
   GPG_NAME="$tmpDir/${NEW_NAME:-${FOLDER_NAME}_${timestamp}.tar.gpg}"
   UPLOAD_NAME=$(basename "$GPG_NAME")
   PROXY_SERVER_URL="http://localhost:8081"
   SERVER_URL="$PROXY_SERVER_URL/$UPLOAD_NAME"

   echo -e "----------------------------------------\n"
   echo "[INFO] TIMESTAMP: $timestamp"
   echo "[INFO] MODULE_NAME: $host_part"
   echo "[INFO] HOST_MODULE: $host_module"
   echo "[INFO] LOGPATH: $log_path"
   echo "[INFO] TEMP_PROCESSING_DIR: $tmpDir"
   echo "[INFO] TAR_NAME: $TAR_NAME"
   echo "[INFO] GPG_NAME: $GPG_NAME"
   echo "[INFO] UPLOAD_NAME: $UPLOAD_NAME"
   echo "[INFO] PROXY_SERVER_URL: $PROXY_SERVER_URL"
   echo "[INFO] SERVER_URL: $SERVER_URL"
   echo -e "----------------------------------------\n"


   # Validate folder exists
   if [ ! -d "$FOLDER_PATH" ]; then
      echo "Error: Folder '$FOLDER_PATH' does not exist."
      exit 1
   fi

   echo "Creating tar archive: $TAR_NAME ..."
   tar -cf "$TAR_NAME" -C "$(dirname "$FOLDER_PATH")" "$(basename "$FOLDER_PATH")"
   echo "TAR archive created."

   echo "Encrypting tar with GPG: $GPG_NAME ..."
   echo "$host_part" | TMPDIR=$tmpDir gpg --batch --yes --passphrase-fd 0 \
      --symmetric --cipher-algo AES256 -o "$GPG_NAME" "$TAR_NAME"
   echo "GPG encryption complete."

   echo "Cleaning up tar file: $TAR_NAME ..."
   rm -f "$TAR_NAME"

   echo "Calculating SHA256 hash ..."
   SHA256_HASH=$(sha256sum "$GPG_NAME" | awk '{print $1}')
   echo "SHA256: $SHA256_HASH"

   echo "Uploading $GPG_NAME to $SERVER_URL ..."
   curl -w "@curl-format" -o /dev/null -X POST \
      -4 \
      -H "X-Log-Folder: $env_hostname/$host_module/$FOLDER_NAME" \
      -H "X-Content-SHA256: $SHA256_HASH" \
      -H "Content-Type: application/octet-stream" \
      --upload-file "$GPG_NAME" \
      --verbose \
      --trace-time \
      "$SERVER_URL"
   echo -e "\nUpload complete."

   echo "Removing the GPG file: $GPG_NAME ..."
   rm -rvf $GPG_NAME

   echo "Done."
   ``` 

   - The `logs-s3.sh` script:
     - Creates a tar archive of `/var/log`.
     - Encrypts it with GPG using AES256.
     - Calculates SHA256 hash.
     - Uploads to NGINX (port 8081) with `X-Log-Folder` header (`prod-vm/localhost/localhost`).
     - See provided `logs-s3.sh` for details.

2. **Create Curl Format File**:

   ```bash
   vi curl-format
   ```

   ```
   \n\n
         content_type: %{content_type}\n
   filename_effective: %{filename_effective}\n
      ftp_entry_path: %{ftp_entry_path}\n
            http_code: %{http_code}\n
         http_connect: %{http_connect}\n
            local_ip: %{local_ip}\n
         local_port: %{local_port}\n
         num_connects: %{num_connects}\n
      num_redirects: %{num_redirects}\n
         redirect_url: %{redirect_url}\n
            remote_ip: %{remote_ip}\n
         remote_port: %{remote_port}\n
      size_download: %{size_download}\n
         size_header: %{size_header}\n
         size_request: %{size_request}\n
         size_upload: %{size_upload}\n
      speed_download: %{speed_download}\n
         speed_upload: %{speed_upload}\n
   ssl_verify_result: %{ssl_verify_result}\n
      url_effective: %{url_effective}\n
   \n\n
      time_namelookup: %{time_namelookup}\n
         time_connect: %{time_connect}\n
      time_appconnect: %{time_appconnect}\n
   time_pretransfer: %{time_pretransfer}\n
      time_redirect: %{time_redirect}\n
   time_starttransfer: %{time_starttransfer}\n
                     -------\n
         time_total: %{time_total}\n
   \n
   ```

   - Defines the output format for `curl` in `logs-s3.sh` to log detailed request metrics (e.g., `http_code`, `time_total`).
   - See provided `curl-format` for details.

3. **Set Permissions**:

   ```bash
   chmod 744 logs-s3.sh
   ```

4. **Run Script**:

   ```bash
   ./logs-s3.sh
   ```

5. **Check Logs**:

   ```bash
   cat /var/log/nginx/error.log
   cat /var/log/nginx/access.log
   cat /var/log/nginx/nginx-to-bucket.log
   ```

## Optional: SELinux Configuration

1. **Check SELinux Status**:

   ```bash
   sestatus
   ```

2. **Disable SELinux (Optional)**:

   - If SELinux causes issues (e.g., permission denied errors), disable it:

     ```bash
     sudo vi /etc/selinux/config
     ```

     Set:

     ```
     SELINUX=disabled
     ```

     Reboot:

     ```bash
     reboot
     ```

   - Note: Disabling SELinux is not always recommended. Consider setting `SELINUX=permissive` or configuring specific SELinux policies instead.

## Troubleshooting

1. **Common Errors**:

   - **Invalid URL prefix** (e.g., `invalid URL prefix in "https://logging-nginx.s3.eu-north-1.amazonaws.com/..."`):
     - Ensure `$aws_s3_key` matches the AWS signature in `aws_authorization_header`.
     - If using `URI::Encode`, add `uri_decode` in `aws_authorization_header`:

       ```nginx
       use URI::Encode qw(uri_decode);
       my $aws_s3_key = uri_decode($r->variable("aws_s3_key"));
       ```

   - **Uninitialized `log_folder` warning**:
     - Ensure `$log_folder` is set early:

       ```nginx
       set $log_folder $http_x_log_folder;
       set $log_folder logs if ($log_folder = "");
       ```

2. **Debugging**:

   - Enable debug logging:

     ```nginx
     access_log /var/log/nginx/debug.log debug;
     log_format debug '$remote_addr - $http_x_log_folder - $log_folder - $request_uri';
     ```

   - Check logs:

     ```bash
     cat /var/log/nginx/error.log
     cat /var/log/nginx/access.log
     cat /var/log/nginx/nginx-to-bucket.log
     ```

3. **Verify S3 Access**:

   ```bash
   export AWS_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxx
   export AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxx
   aws s3 cp test.gpg s3://logging-nginx/prod-vm/test.gpg
   ```

4. **Rebuild NGINX (if needed)**:

   ```bash
   cd /opt/nginx-1.26.0
   ./configure ... # (same as above)
   make && sudo make install
   sudo systemctl restart nginx
   ```

## Notes

- The setup proxies `.gpg` files to S3 with paths like `prod-vm/localhost/localhost/filename.gpg`.
- The `logs-s3.sh` script uses `X-Log-Folder` header for S3 path construction.
- The configuration was tested on NGINX 1.26.0 with `nginx:stable-perl` as a reference.
- Ensure consistent header case (`X-Log-Folder` in `logs-s3.sh` and `$http_x_log_folder` in `nginx.conf`).
- The `.env` file is set before enabling the NGINX service to ensure environment variables are available.

## References

- [NGINX Documentation](https://nginx.org/en/docs/)
- [AWS S3 Signature v4 Documentation](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-header-based-auth.html)
- [RHEL Documentation](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/)
