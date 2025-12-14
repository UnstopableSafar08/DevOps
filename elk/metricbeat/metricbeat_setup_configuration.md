# Metricbeat Setup and Configurations on RHEL 9.x

**Metricbeat configuration with SSL disabled by default**, plus **comments showing how to enable SSL** using your provided certificate. I’ve added these comments to all relevant config sections.

---

### 1. **metricbeat.yml**

```yaml
metricbeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

setup.template.settings:
  index.number_of_shards: 1
  index.codec: best_compression

setup.kibana:
  host: "http://localhost:5601"
  # To enable SSL for Kibana, uncomment below lines and provide correct CA certificate
  # host: "https://localhost:5601"
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]

output.elasticsearch:
  hosts: ["http://localhost:9200"]
  username: "elastic"
  password: "elastic@123#"
  ssl.enabled: false  # disable SSL
  # To enable SSL, use:
  # hosts: ["https://localhost:9200"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
  # ssl.verification_mode: full  # or none if self-signed

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~
```

---

### 2. **Modules**

#### a) `modules.d/elasticsearch.yml`

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
  # To enable SSL:
  # hosts: ["https://localhost:9200"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

#### b) `modules.d/elasticsearch-xpack.yml`

```yaml
- module: elasticsearch
  xpack.enabled: true
  period: 10s
  hosts: ["http://localhost:9200"]
  username: "elastic"
  password: "elastic@123#"
  ssl.enabled: false
  # To enable SSL:
  # hosts: ["https://localhost:9200"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

#### c) `modules.d/logstash.yml`

```yaml
- module: logstash
  metricsets:
    - node
    - node_stats
  period: 10s
  hosts: ["http://localhost:9600"]
  # To enable SSL for Logstash HTTP API:
  # hosts: ["https://localhost:9600"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

#### d) `modules.d/logstash-xpack.yml`

```yaml
- module: logstash
  xpack.enabled: true
  period: 10s
  hosts: ["http://localhost:9600"]
  # To enable SSL for Logstash X-Pack API:
  # hosts: ["https://localhost:9600"]
  # ssl.enabled: true
  # ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
```

---

### 3. **Notes for enabling SSL**

1. Make sure the certificate exists and is readable:

```bash
ls -l /etc/metricbeat/certs/ca_elk.local.crt
```

2. Change all `http://` to `https://` in the `hosts` section when enabling SSL.
3. Set `ssl.enabled: true` and provide the path to the CA certificate.
4. For self-signed certs, you may use `ssl.verification_mode: none`. For trusted CA, use `full`.

---

