# **Metricbeat Full Installation & Configuration (RHEL 9.6)**

A **full, production-ready setup for Metricbeat on RHEL 9.6**, including installation, main configuration, and all requested module configs with SSL disabled by default and commented options for SSL. You can copy and deploy directly.

---

## **1. Install Metricbeat**

```bash
# Download Metricbeat RPM
curl -L -O https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-9.1.2-x86_64.rpm

# Install RPM
rpm -vi metricbeat-*.rpm

# Verify installation
metricbeat version
```

---

## **2. Enable Modules**

```bash
metricbeat modules enable system
metricbeat modules enable elasticsearch
metricbeat modules enable elasticsearch-xpack
metricbeat modules enable logstash
metricbeat modules enable logstash-xpack
```

---

## **3. Metricbeat Main Configuration: `metricbeat.yml`**

```yaml
metricbeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

setup.template.settings:
  index.number_of_shards: 1
  index.codec: best_compression

setup.kibana:
  host: "http://localhost:5601"
  # SSL option:
  # host: "https://localhost:5601"
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]

output.elasticsearch:
  hosts: ["http://localhost:9200"]
  username: "elastic"
  password: "elastic@123#"
  ssl.enabled: false
  # SSL option:
  # hosts: ["https://localhost:9200"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
  # ssl.verification_mode: full

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~
```

---

## **4. Modules Configuration**

### **a) System Module: `modules.d/system.yml`**

```yaml
- module: system
  period: 10s
  metricsets:
    - cpu
    - load
    - memory
    - network
    - process
    - process_summary
    - socket_summary
  process.include_top_n:
    by_cpu: 5
    by_memory: 5

- module: system
  period: 1m
  metricsets:
    - filesystem
    - fsstat
  processors:
    - drop_event.when.regexp:
        system.filesystem.mount_point: '^/(sys|cgroup|proc|dev|etc|host|lib|snap)($|/)'
   # - drop_event.when.equals:
   #     system.filesystem.mount_point: "/var"

- module: system
  period: 15m
  metricsets:
    - uptime

# SSL option for monitoring remote hostfs:
# hostfs: "/hostfs"
# ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```
Check the COnfigurations;
```bash
metricbeat test modules system
metricbeat test config

# restart
systemctl restart metricbeat
systemctl status metricbeat
```
---

### **b) Elasticsearch Module: `modules.d/elasticsearch.yml`**

```yaml
- module: elasticsearch
  metricsets:
    - cluster_stats
    - node_stats
  period: 10s
  hosts: ["http://localhost:9200"]
  username: "elastic"
  password: "elastic@123#"
  ssl.enabled: false
  # SSL option:
  # hosts: ["https://localhost:9200"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

---

### **c) Elasticsearch X-Pack Module: `modules.d/elasticsearch-xpack.yml`**

```yaml
- module: elasticsearch
  xpack.enabled: true
  period: 10s
  hosts: ["http://localhost:9200"]
  username: "elastic"
  password: "elastic@123#"
  ssl.enabled: false
  # SSL option:
  # hosts: ["https://localhost:9200"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

---

### **d) Logstash Module: `modules.d/logstash.yml`**

```yaml
- module: logstash
  metricsets:
    - node
    - node_stats
  period: 10s
  hosts: ["http://localhost:9600"]
  # SSL option:
  # hosts: ["https://localhost:9600"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

---

### **e) Logstash X-Pack Module: `modules.d/logstash-xpack.yml`**

```yaml
- module: logstash
  xpack.enabled: true
  period: 10s
  hosts: ["http://localhost:9600"]
  # SSL option:
  # hosts: ["https://localhost:9600"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

---

## **5. Verify Configuration**

```bash
# Test config
metricbeat test config

# List enabled modules
metricbeat modules list
```

---

## **6. Start Metricbeat Service**

```bash
systemctl enable metricbeat
systemctl start metricbeat

# Check status
systemctl status metricbeat
```

---

## ✅ **Notes**

1. SSL is **disabled by default**; you can enable it by changing `ssl.enabled: true` and updating hosts to `https://`.
2. All modules (`system`, `elasticsearch`, `elasticsearch-xpack`, `logstash`, `logstash-xpack`) are configured.
3. The system module monitors CPU, memory, network, processes, filesystem, and uptime.
4. The configuration is ready for **RHEL 9.6** and can be copied to other nodes directly.

---

