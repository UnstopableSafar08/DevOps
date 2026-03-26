# Harbor SSL Certificate Renewal Guide

## Overview

This guide covers updating an expired or soon-to-expire SSL certificate on a Docker-based Harbor registry.

---

## Prerequisites

- Access to the Harbor host as `root`
- New certificate files ready:
  - `harbor.crt` — full chain certificate
  - `harbor.key` — private key
- Harbor installed at `/root/harbor` (adjust paths as needed)

---

## Step 1 — Verify Current Certificate Expiry

```bash
# Check cert file directly
openssl x509 -in /root/harbor/cert/root/harbor.crt -noout -dates

# Check live cert over TLS
echo | openssl s_client -connect <harbor-hostname>:443 2>/dev/null \
  | openssl x509 -noout -dates
```

---

## Step 2 — Inspect Current harbor.yml Config

```bash
grep -A5 'https:' /root/harbor/root/harbor.yml
```

Expected output:

```yaml
https:
  port: 443
  certificate: /root/harbor/cert/root/harbor.crt
  private_key: /root/harbor/cert/root/harbor.key
```

Note the exact paths — you will replace the files at these locations.

---

## Step 3 — Back Up Old Certificates

```bash
cd /root/harbor/cert
cp harbor.crt harbor.crt.bak.$(date +%Y%m%d)
cp harbor.key harbor.key.bak.$(date +%Y%m%d)
```

---

## Step 4 — Replace Certificate Files

```bash
# Copy new cert files into place
cp /path/to/new/root/harbor.crt /root/harbor/cert/root/harbor.crt
cp /path/to/new/root/harbor.key /root/harbor/cert/root/harbor.key

# Set correct permissions
chmod 644 /root/harbor/cert/root/harbor.crt
chmod 600 /root/harbor/cert/root/harbor.key
```

---

## Step 5 — Reconfigure and Restart Harbor

```bash
cd /root/harbor

# Stop all Harbor containers
docker compose down

# Re-run prepare to regenerate nginx config with updated cert
./prepare

# Start Harbor
docker compose up -d
```

---

## Step 6 — Verify New Certificate

```bash
# Verify expiry of live cert
echo | openssl s_client -connect <harbor-hostname>:443 2>/dev/null \
  | openssl x509 -noout -dates

# Verify cert file directly
openssl x509 -in /root/harbor/cert/root/harbor.crt -noout -dates

# Check Harbor containers are all up
docker compose ps
```

---

## Step 7 — Update Docker Clients (All Nodes)

Every node that pulls from Harbor must trust the new CA cert.

```bash
# On each Docker client node
mkdir -p /etc/docker/certs.d/<harbor-hostname>/
cp /path/to/ca.crt /etc/docker/certs.d/<harbor-hostname>/ca.crt
systemctl reload docker
```

### Ansible Playbook — Push CA Cert to All Nodes

```yaml
- name: Distribute Harbor CA cert to all nodes
  hosts: all
  become: true
  tasks:
    - name: Ensure certs.d directory exists
      file:
        path: /etc/docker/certs.d/<harbor-hostname>
        state: directory
        mode: '0755'

    - name: Copy Harbor CA cert
      copy:
        src: /root/harbor/cert/ca.crt
        dest: /etc/docker/certs.d/<harbor-hostname>/ca.crt
        mode: '0644'

    - name: Reload Docker
      systemd:
        name: docker
        state: reloaded
```

---

## Why `./prepare` Is Required

`./prepare` is a Python-based script that **generates all internal configuration files** for Harbor's containers before they start. Harbor containers do not read `harbor.yml` directly.

### The Flow

```
harbor.yml  ──►  ./prepare  ──►  generated configs  ──►  docker compose up
```

Harbor's containers (nginx, core, jobservice, etc.) each have their own config files. `./prepare` reads `harbor.yml` and renders those configs from Jinja2 templates.

### What It Actually Does

| Action | Detail |
|---|---|
| Reads `harbor.yml` | Your cert paths, hostname, DB passwords, etc. |
| Renders templates from `common/config/` | Generates nginx.conf, core config, jobservice config, registryctl config, etc. |
| Copies cert files into the nginx config volume | Puts `harbor.crt` and `harbor.key` where the nginx container can read them |
| Writes rendered configs to `common/config/` | These are bind-mounted into the containers at runtime |

### Why It's Required After a Cert Change

When you replace cert files on disk and skip `./prepare`, the nginx container still has the old cert baked into its config volume. The new files on your host are never picked up.

```bash
# Without ./prepare:
docker compose down
docker compose up -d
# nginx still serves the OLD cert — nothing changed inside the container
```

```bash
# With ./prepare:
docker compose down
./prepare          # re-renders nginx.conf, copies new cert into config volume
docker compose up -d
# nginx now serves the NEW cert
```

### Where You Can See the Output

```bash
# After running ./prepare, rendered configs land here:
ls -la /root/harbor/common/config/

# Your cert gets copied here — this is what nginx actually uses:
ls -la /root/harbor/common/config/nginx/cert/
```

The nginx container bind-mounts `/root/harbor/common/config/nginx/` — so whatever `./prepare` writes there is what nginx uses at runtime.

> **TL;DR** — `harbor.yml` is the source of truth, but Harbor containers never read it directly. `./prepare` is the translator that converts it into actual runtime configs. Skipping it means your changes never reach the containers.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `certificate has expired` on docker pull | Client still has old CA cert | Re-push CA cert to client node |
| Harbor nginx not starting | Bad cert/key mismatch | Verify with `openssl x509 -noout -modulus -in harbor.crt \| md5sum` vs `openssl rsa -noout -modulus -in harbor.key \| md5sum` |
| `./prepare` fails | Wrong cert path in harbor.yml | Re-check `https.certificate` and `https.private_key` paths |
| 502 Bad Gateway after restart | Container still starting up | Wait ~30s and retry; check `docker compose logs nginx` |

---

## Certificate / Key Mismatch Check

```bash
openssl x509 -noout -modulus -in /root/harbor/cert/root/harbor.crt | md5sum
openssl rsa  -noout -modulus -in /root/harbor/cert/root/harbor.key | md5sum
# Both md5 hashes must match
```

---

## Self-Signed Certificate (Optional)

If renewing a self-signed cert:

```bash
HARBOR_HOST=<harbor-hostname>

# Generate new CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -sha512 -days 3650 \
  -subj "/CN=${HARBOR_HOST}" \
  -key ca.key -out ca.crt

# Generate server key and CSR
openssl genrsa -out harbor.key 4096
openssl req -sha512 -new \
  -subj "/CN=${HARBOR_HOST}" \
  -key harbor.key -out harbor.csr

# Create SAN config
cat > v3.ext <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=${HARBOR_HOST}
EOF

# Sign the certificate
openssl x509 -req -sha512 -days 365 \
  -extfile v3.ext \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -in harbor.csr -out harbor.crt
```

---
