#!/bin/bash

# Author: Sagar Malla
# Email: sagarmalla08@gmail.com
# Date: 13-MAY, 2025
# Script to generate a CA and SAN certificates for a user-specified wildcard DNS
# Used for Elasticsearch cluster, Kibana, and Logstash in a test/Prod environment
# Includes SAN certificate verification at the end
# Moves existing ca and elk-cluster directories to a backup directory if they exist

set -e

# Ask for domain name
read -p "Enter your base domain (e.g. sagar.com.np or sagar.com): " USER_DOMAIN
WILDCARD="*.$USER_DOMAIN"
echo "✅ Will create certificates for $WILDCARD and $USER_DOMAIN"

CERTS_DIR="/etc/elasticsearch/certs"
ELASTICSEARCH_BIN="/usr/share/elasticsearch/bin/elasticsearch-certutil"

# Define character set (include escaped dash)
CHAR_SET='A-Za-z0-9@#*\-+!'

# Generate 20-character random string
RANDOM_PASS=$(tr -dc "$CHAR_SET" </dev/urandom | head -c 20)

# Get current timestamp
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

# Save to pass.txt
echo "$TIMESTAMP - $RANDOM_PASS" >> pass.txt

# Output to console
echo "Generated password: $RANDOM_PASS"
echo -e "# Saved to pass.txt as: $TIMESTAMP - $RANDOM_PASS\n\n"

# Step 0: Prompt for passwords
# read -s -p "Enter CA password: " CA_PASS = $RANDOM_PASS
# echo
# read -s -p "Enter node cert password: " CERT_PASS= $RANDOM_PASS
# echo
# read -s -p "Enter Truststore password: " TRUSTSTORE_PASS= $RANDOM_PASS
# echo

CA_PASS="$RANDOM_PASS"
CERT_PASS="$RANDOM_PASS"
TRUSTSTORE_PASS="$RANDOM_PASS"

# Step 1: Ensure certs directory exists
sudo mkdir -p "$CERTS_DIR"

# Step 2: Create instances.yml without IPs
# you must have to map the ips to the test domains on hosts file.
echo "Creating instances.yml..."
cat <<EOF | sudo tee "$CERTS_DIR/instances.yml" >/dev/null
instances:
  - name: "$USER_DOMAIN"
    dns:
      - "$WILDCARD"
      - "$USER_DOMAIN"
      - "localhost"
EOF

# Step 3: Create CA if not exists
if [ ! -f "$CERTS_DIR/elastic-stack-ca.p12" ]; then
  echo "Creating CA (valid 10 years)..."
  sudo "$ELASTICSEARCH_BIN" ca --days 3650 --out "$CERTS_DIR/elastic-stack-ca.p12" --pass "$CA_PASS"
else
  echo "CA already exists. Skipping CA generation."
fi

# Step 4: Generate node certificate
echo "Generating node certificate..."
sudo "$ELASTICSEARCH_BIN" cert \
  --ca "$CERTS_DIR/elastic-stack-ca.p12" \
  --ca-pass "$CA_PASS" \
  --in "$CERTS_DIR/instances.yml" \
  --out "$CERTS_DIR/$USER_DOMAIN.zip" \
  --pass "$CERT_PASS" \
  --days 3650

# Step 5: Unzip and organize files
echo "Extracting node certificate..."
cd "$CERTS_DIR"
sudo unzip -o "$USER_DOMAIN.zip"
sudo mv $USER_DOMAIN/* .
sudo rm -rf $USER_DOMAIN

# Step 6: Extract CRT and KEY files
echo "Extracting CA certificate and key..."
sudo openssl pkcs12 -in "$CERTS_DIR/elastic-stack-ca.p12" -out "$CERTS_DIR/ca_$USER_DOMAIN.crt" -clcerts -nokeys -passin pass:"$CA_PASS"
sudo openssl pkcs12 -in "$CERTS_DIR/elastic-stack-ca.p12" -out "$CERTS_DIR/ca_$USER_DOMAIN.key" -nocerts -nodes -passin pass:"$CA_PASS"

echo "Extracting node certificate and key..."
sudo openssl pkcs12 -in "$CERTS_DIR/$USER_DOMAIN.p12" -out "$CERTS_DIR/$USER_DOMAIN.crt" -clcerts -nokeys -passin pass:"$CERT_PASS"
sudo openssl pkcs12 -in "$CERTS_DIR/$USER_DOMAIN.p12" -out "$CERTS_DIR/$USER_DOMAIN.key" -nocerts -nodes -passin pass:"$CERT_PASS"

# Step 7: Generate Truststore (truststore.p12) using keytool
echo "Generating Truststore..."
keytool -import -alias elastic-ca \
  -file "$CERTS_DIR/$USER_DOMAIN.crt" \
  -keystore "$CERTS_DIR/truststore.p12" \
  -storepass "$TRUSTSTORE_PASS" \
  -noprompt

# Step 8: Set permissions
echo "Fixing permissions..."
sudo chown elasticsearch:elasticsearch "$CERTS_DIR"/*
sudo chmod 640 "$CERTS_DIR"/*.key
sudo chmod 644 "$CERTS_DIR"/*.crt
sudo chmod 640 "$CERTS_DIR/truststore.p12"


# # step 9: keystore update.
echo -e "\n\nNow You can Remove and Add the existing xpack keystore, truststore password from elasticsearch keystore to apply the new certificate."
echo -e "\n# # Remove existing SSL-related secure passwords
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.http.ssl.keystore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.http.ssl.truststore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.keystore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.truststore.secure_password"

echo -e "\n# # Add new secure passwords interactively
echo '"$RANDOM_PASS"' | sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add --stdin --force xpack.security.http.ssl.keystore.secure_password
echo '"$RANDOM_PASS"' | sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add --stdin --force xpack.security.http.ssl.truststore.secure_password
echo '"$RANDOM_PASS"' | sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add --stdin --force xpack.security.transport.ssl.keystore.secure_password
echo '"$RANDOM_PASS"' | sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add --stdin --force xpack.security.transport.ssl.truststore.secure_password"

echo -e "\n# Verify keystore passwords (use cautiously in production)
/usr/share/elasticsearch/bin/elasticsearch-keystore show autoconfiguration.password_hash
/usr/share/elasticsearch/bin/elasticsearch-keystore show keystore.seed
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.http.ssl.keystore.secure_password
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.http.ssl.truststore.secure_password
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.transport.ssl.keystore.secure_password
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.transport.ssl.truststore.secure_password"
echo "✅ All done. Certificates and Truststore are ready in: $CERTS_DIR"
