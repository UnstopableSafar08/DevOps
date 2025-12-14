#!/bin/bash

# Author: Sagar Malla
# Email: sagarmalla08@gmail.com
# Date: 13-MAY, 2025
# Script to generate a CA and SAN certificates for a user-specified wildcard DNS
# Used for Elasticsearch cluster, Kibana, and Logstash in a test environment
# Includes SAN certificate verification at the end
# Moves existing ca and elk-cluster directories to a backup directory if they exist

set -e

CERTS_DIR="/etc/elasticsearch/certs"
ELASTICSEARCH_BIN="/usr/share/elasticsearch/bin/elasticsearch-certutil"


# Define character set (include escaped dash)
CHAR_SET='A-Za-z0-9@#%*\-+!$&'

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
echo  "test pass: md8Bx%nc69+_3?2j7gTf"

read -s -p "Enter CA password: " CA_PASS
echo
read -s -p "Enter node cert password: " CERT_PASS
echo
read -s -p "Enter Truststore password: " TRUSTSTORE_PASS
echo

# Step 1: Ensure certs directory exists
sudo mkdir -p "$CERTS_DIR"

# Step 2: Create instances.yml
echo "Creating instances.yml..."
cat <<EOF | sudo tee "$CERTS_DIR/instances.yml" >/dev/null
instances:
  - name: elk-node
    dns:
      - "*.sagar.com.np"
      - "sagar.com.np"
      - "localhost"
    ip:
      - 192.168.121.110
      - 192.168.121.111
      - 192.168.121.112
      - 192.168.121.113
      - 192.168.121.114
      - 127.0.0.1
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
  --out "$CERTS_DIR/elk-node.zip" \
  --pass "$CERT_PASS" \
  --days 3650

# Step 5: Unzip and organize files
echo "Extracting node certificate..."
cd "$CERTS_DIR"
sudo unzip -o elk-node.zip
sudo mv elk-node/* . 
sudo rm -rf elk-node

# Step 6: Extract CRT and KEY files
echo "Extracting CA certificate and key..."
sudo openssl pkcs12 -in "$CERTS_DIR/elastic-stack-ca.p12" -out "$CERTS_DIR/ca.crt" -clcerts -nokeys -passin pass:"$CA_PASS"
sudo openssl pkcs12 -in "$CERTS_DIR/elastic-stack-ca.p12" -out "$CERTS_DIR/ca.key" -nocerts -nodes -passin pass:"$CA_PASS"

echo "Extracting node certificate and key..."
sudo openssl pkcs12 -in "$CERTS_DIR/elk-node.p12" -out "$CERTS_DIR/elk-node.crt" -clcerts -nokeys -passin pass:"$CERT_PASS"
sudo openssl pkcs12 -in "$CERTS_DIR/elk-node.p12" -out "$CERTS_DIR/elk-node.key" -nocerts -nodes -passin pass:"$CERT_PASS"

# Step 7: Generate Truststore (truststore.p12) using keytool
echo "Generating Truststore..."
keytool -import -alias elastic-ca \
  -file "$CERTS_DIR/ca.crt" \
  -keystore "$CERTS_DIR/truststore.p12" \
  -storepass "$TRUSTSTORE_PASS" \
  -noprompt

# Step 8: Set permissions
echo "Fixing permissions..."
sudo chown elasticsearch:elasticsearch "$CERTS_DIR"/*
sudo chmod 640 "$CERTS_DIR"/*.key
sudo chmod 644 "$CERTS_DIR"/*.crt
sudo chmod 640 "$CERTS_DIR/truststore.p12"

echo "✅ All done. Certificates and Truststore are ready in: $CERTS_DIR"
