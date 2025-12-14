***
# ELK with the publically signed CERTS.
***
<br>

***
####  OPTIONS 1: Directly use the certificate-chain and private key.
***

Get the configurations only.

```bash
grep -v '^\s*#' /etc/elasticsearch/elasticsearch.yml | grep -v '^\s*$'  # get es
```
## ELASTICSEARCH CONFIGURATION.
elasticsearch.yml file content.
```yml
cluster.name: elk
node.name: elk.sagar.com.np
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: elk.sagar.com.np
http.port: 9200
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  certificate: /etc/elasticsearch/certs/full.crt
  key: /etc/elasticsearch/certs/private.key

# xpack.security.http.ssl.verification_mode: certificate # to fix the error: java.security.cert.CertificateException: No subject alternative names matching IP address 192.168.121.113 found
# xpack.security.http.ssl.verification_mode: full # enable this after password reset or not leave it as comment.

xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12
cluster.initial_master_nodes: ["elk.sagar.com.np"]
http.host: 0.0.0.0
```

Options of : xpack.security.http.ssl.verification_mode

| Mode          | Meaning                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| `full`        | 🔒 **Strictest** — verifies certificate **trust AND hostname/IP (SAN)** |
| `certificate` | ✅ Verifies certificate **trust only**, skips hostname/IP check          |
| `none`        | ⚠️ No verification at all (⚠️ **Not secure**)                           |




#### KIBANA CONFIGURATION.
```bash
grep -v '^\s*#' /etc/kibana/kibana.yml | grep -v '^\s*$'  # get kibana
```
kibana.yml file content.
```yml
server.port: 5601
server.host: "0.0.0.0"
server.publicBaseUrl: "http://kibana.sagar.com.np:5601"
server.name: "kibana-server"
server.ssl.enabled: true
server.ssl.certificate: /etc/kibana/certs/full.crt
server.ssl.key: /etc/kibana/certs/private.key
elasticsearch.hosts: ["https://elk.sagar.com.np:9200"]
# elasticsearch.username: "kibana_system"
# elasticsearch.password: "elastic@123#"
elasticsearch.serviceAccountToken: "<serviceAccountToken-here>"

elasticsearch.ssl.verificationMode: full
elasticsearch.ssl.certificateAuthorities: [ "/etc/kibana/certs/full.crt" ]
logging:
  appenders:
    file:
      type: file
      fileName: /var/log/kibana/kibana.log
      layout:
        type: json
  root:
    appenders:
      - default
      - file
pid.file: /run/kibana/kibana.pid
```



***
####  OPTIONS 2: using .p12 certificates.
***

#### Certificate Files Used
Extracted from STAR_sagar_com_np.zip:
  - STAR_sagar_com_np.crt — Domain certificate
  - sagar_com_np.key — Private key
  - AAACertificateServices.crt
  - USERTrustRSAAAACA.crt
  - SectigoRSADomainValidationSecureServerCA.crt

#### Create a full chain certificate.
```bash
cat AAACertificateServices.crt USERTrustRSAAAACA.crt SectigoRSADomainValidationSecureServerCA.crt > full-chain.crt
```

#### Creating PKCS#12 Keystore (sagar.p12)
```bash
openssl pkcs12 -export \
  -in STAR_sagar_com_np.crt \
  -inkey sagar_com_np.key \
  -certfile full-chain.crt \
  -out sagar.p12 \
  -password pass:changeit

  # one-line cmd
  # openssl pkcs12 -export -in STAR_sagar_com_np.crt -inkey sagar_com_np.key -certfile full-chain.crt -out sagar.p12 -password pass:'changeit'
```

#### Generate a Truststore (truststore.p12)
```bash
keytool -importcert \
  -alias sectigo-root \
  -file full-chain.crt \
  -keystore truststore.p12 \
  -storetype PKCS12 \
  -storepass changeit \
  -noprompt

  # OR
  # Generate a Truststore (truststore.p12)
  # keytool -importcert -alias sectigo-root -file full-chain.crt -keystore truststore.p12 -storetype PKCS12 -storepass 'changeit' -nopromp
```

#### Elasticsearch Keystore Management.
```bash
#### elasticsearch keystore view, remove and add new for public certificate.
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore list

#### remove
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.http.ssl.keystore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.keystore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.truststore.secure_password

#### add
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.http.ssl.keystore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.transport.ssl.keystore.secure_password
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.transport.ssl.truststore.secure_password

#### password view
/usr/share/elasticsearch/bin/elasticsearch-keystore show autoconfiguration.password_hash
/usr/share/elasticsearch/bin/elasticsearch-keystore show keystore.seed
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.http.ssl.keystore.secure_password
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.transport.ssl.keystore.secure_password
/usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.transport.ssl.truststore.secure_password
```

#### Update permissions.
```bash
sudo chown -R elasticsearch:elasticsearch /etc/elasticsearch
chmod 640 /etc/elasticsearch/certs/sagar-crts/*.p12
```
#### elasticsearch.yml
```yml
cluster.name: elk
node.name: elk.sagar.com.np
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: elk.sagar.com.np
http.port: 9200
http.host: 0.0.0.0
xpack.security.enabled: true
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: /etc/elasticsearch/certs/sagar-crts/sagar.p12
#### xpack.security.http.ssl.verification_mode: certificate # to fix the error: java.security.cert.CertificateException: No subject alternative names matching IP address 192.168.121.113 found
#### xpack.security.http.ssl.verification_mode: full # enable this after password reset or leave it as comment.

xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.keystore.path: /etc/elasticsearch/certs/sagar-crts/sagar.p12
xpack.security.transport.ssl.truststore.path: /etc/elasticsearch/certs/sagar-crts/truststore.p12
cluster.initial_master_nodes: ["elk.sagar.com.np"]
```

#### restart
```bash
sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch -v # this is the best way to check the logs
sudo systemctl restart elasticsearch
```

####  Copy the certificates to kibana/certs path
```bash
cp /etc/elasticsearch/certs/sagar-crts/STAR_sagar_com_np.crt \
  /etc/elasticsearch/certs/sagar-crts/sagar_com_np.key \  
  /etc/elasticsearch/certs/sagar-crts/full-chain.crt  \
  /etc/kibana/certs/.
```

#### update permission
```bash
mkdir -p /etc/kibana/certs
sudo chown kibana:kibana /etc/kibana/certs/*
chmod 640 /etc/kibana/certs/*
```

#### kibana.yml
```yml
config kibana
server.port: 5601
server.host: "0.0.0.0"
server.publicBaseUrl: "https://kibana.sagar.com.np:5601"
server.name: "kibana.sagar.com.np"
server.ssl.enabled: true
server.ssl.certificate: /etc/kibana/certs/STAR_sagar_com_np.crt
server.ssl.key: /etc/kibana/certs/sagar_com_np.key
elasticsearch.hosts: ["https://elk.sagar.com.np:9200"]
elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/full-chain.crt"]
elasticsearch.ssl.verificationMode: full
elasticsearch.serviceAccountToken: "<serviceAccountToken-here>"
logging:
  appenders:
    file:
      type: file
      fileName: /var/log/kibana/kibana.log
      layout:
        type: json
  root:
    appenders:
      - default
      - file
pid.file: /run/kibana/kibana.pid
```


#### restart the kibana
```bash
sudo -u kibana /usr/share/kibana/bin/kibana # this is the best way to check the logs
systemctl restart kibana
```

#### certificate verification
```bash
openssl s_client -connect elk.sagar.com.np:9200 -showcerts

openssl x509 -noout -modulus -in /etc/kibana/certs/STAR_sagar_com_np.crt | openssl md5
openssl rsa -noout -modulus -in /etc/kibana/certs/sagar_com_np.key | openssl md5
#### output must be same.
```


#### Setup Metricbeat.
```bash
cd /tmp
wget https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-8.17.0-x86_64.rpm
sudo rpm -ivh metricbeat-8.17.0-x86_64.rpm
cp metricbeat.yml  metricbeat.yml_20250411
```

```bash
sudo vim /etc/metricbeat/metricbeat.yml
```  
Metricbeat config.
```yml
metricbeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false
setup.template.settings:
  index.number_of_shards: 1
  index.codec: best_compression
setup.kibana:
  host: "kibana.sagar.com.np:5601"
output.elasticsearch:
  hosts: ["https://elk.sagar.com.np:9200"]
  preset: balanced
  protocol: "https"
  username: "elastic"
  password: "<elasticsearch_password>"
processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~
```

```bash
sudo metricbeat modules enable system
sudo metricbeat setup --dashboards

sudo systemctl enable metricbeat
sudo systemctl start metricbeat
```
Logs check.
```bash
journalctl -u metricbeat -f
```



#### api generate
```json
curl -u elastic:Ela5Tic@#987 -X POST "http://elk.sagar.com.np:9200/_security/api_key" -H 'Content-Type: application/json' -d '{
  "name": "metricbeat-api-key",
  "role_descriptors": {
    "metricbeat_writer": {
      "cluster": ["monitor", "read_ilm"],
      "index": [
        {
          "names": ["metricbeat-*"],
          "privileges": ["write", "create_index"]
        }
      ]
    }
  }
}'
```

#### kibana
```json
POST /_security/api_key
{
  "name": "metricbeat-api-key",
  "role_descriptors": {
    "metricbeat_writer": {
      "cluster": ["monitor", "read_ilm"],
      "index": [
        {
          "names": ["metricbeat-*"],
          "privileges": ["write", "create_index"]
        }
      ]
    }
  }
}
```

#### output
```json
{
  "id": "7psRv5YBoEGT3O3BrBqD",
  "name": "metricbeat-api-key",
  "api_key": "YtfMfJsiSSeUVZV_EYQ0JA",
  "encoded": "N3BzUnY1WUJvRUdUM08zQnJCcUQ6WXRmTWZKc2lTU2VVVlpWX0VZUTBKQQ=="
}
```
