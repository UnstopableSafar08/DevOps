A **complete, production-ready guide** for installing **OpenSearch Dashboards 3.4.0** on **RHEL 9.6 / Oracle Linux 9.6**, including **installation, configuration, resource limits, security, and verification**. This guide assumes your **OpenSearch 3.4.0** is already running on `localhost:9200` with basic auth.

---

# OpenSearch Dashboards 3.4.0 Installation Guide

## 1. Version Compatibility

| Component             | Version |
| --------------------- | ------- |
| OpenSearch            | 3.4.0   |
| OpenSearch Dashboards | 3.4.0   |

> **Note:** Dashboards version must match OpenSearch version to avoid API/plugin errors.

---

## 2. Download the RPM

Create a working directory:

```bash
mkdir -p /opt/opensearch-rpm
cd /opt/opensearch-rpm
```

Download the RPM:

```bash
wget https://artifacts.opensearch.org/releases/bundle/opensearch-dashboards/3.4.0/opensearch-dashboards-3.4.0-linux-x64.rpm
```

**Why RPM:** native systemd service, proper filesystem layout, easier upgrades.

---

## 3. Install Dashboards

```bash
rpm -ivh opensearch-dashboards-3.4.0-linux-x64.rpm
```

Verify:

```bash
rpm -qa | grep opensearch-dashboards
```

---

## 4. Configure Dashboards

Edit the configuration file:

```bash
vi /etc/opensearch-dashboards/opensearch_dashboards.yml
```

### Minimal Production Configuration

```yaml
server.host: "0.0.0.0"
server.port: 5601

opensearch.hosts: ["https://localhost:9200"]
opensearch.username: "admin"
opensearch.password: "openSearch@123#"

opensearch.ssl.verificationMode: none
```

**Why these settings matter:**

| Setting                  | Reason                          |
| ------------------------ | ------------------------------- |
| `server.host`            | Allow external access           |
| `opensearch.hosts`       | HTTPS endpoint of OpenSearch    |
| `verificationMode: none` | Avoid CA mismatch during setup  |
| Auth credentials         | Required due to Security plugin |

---

## 5. Resource Limits (RAM + CPU)

**Production-safe limits**: 512 MB RAM, 0.5 CPU

### 5.1 Create Systemd Override

```bash
systemctl edit opensearch-dashboards
```

Add:

```ini
[Service]
MemoryMax=512M
CPUQuota=50%
```

### 5.2 Optional Node.js Heap Limit

```bash
echo 'NODE_OPTIONS="--max-old-space-size=400"' >> /etc/sysconfig/opensearch-dashboards
```

* Keeps Node.js heap within RAM limits

---

## 6. Enable and Start Dashboards

```bash
systemctl daemon-reexec
systemctl enable opensearch-dashboards
systemctl start opensearch-dashboards
systemctl status opensearch-dashboards
```

---

## 7. Firewall Configuration

Open port 5601 if firewall is active:

```bash
firewall-cmd --add-port=5601/tcp --permanent
firewall-cmd --reload
```

---

## 8. Verify Installation

From server:

```bash
curl http://localhost:5601
```

From browser:

```
http://<server-ip>:5601
```

Login with:

* **Username:** admin
* **Password:** openSearch@123#

---

## 9. Integration Verification

* Go to **Stack Management → Index Management**
* Confirm indices from Beats (filebeat-*, metricbeat-*, heartbeat-*) appear
* Test dashboards connectivity

---

## 10. Optional Production Hardening

| Step                                | Reason                          |
| ----------------------------------- | ------------------------------- |
| Enable TLS (`server.ssl.*`)         | Secure Dashboards traffic       |
| Use least-privilege OpenSearch user | Minimize risk                   |
| Deploy NGINX reverse proxy          | Load balancing + extra security |
| Restrict access by IP               | Network isolation               |
| Tune Node.js heap                   | Avoid OOM on low-RAM systems    |
| Enable logs rotation                | Prevent disk exhaustion         |

---

## 11. Directory Layout

| Path                               | Purpose           |
| ---------------------------------- | ----------------- |
| `/usr/share/opensearch-dashboards` | Application files |
| `/etc/opensearch-dashboards`       | Config files      |
| `/var/log/opensearch-dashboards`   | Logs              |
| `/var/lib/opensearch-dashboards`   | Runtime data      |

---

## 12. Verification Commands

```bash
systemctl status opensearch-dashboards
systemctl show opensearch-dashboards | grep -E 'MemoryMax|CPUQuota'
systemd-cgtop
```

---

## 13. Summary

* Dashboards 3.4.0 matches OpenSearch 3.4.0
* RPM installation ensures clean systemd management
* RAM & CPU limited safely for constrained environments
* Secure connections possible via TLS + reverse proxy
* Verified integration with Beats indices

---
