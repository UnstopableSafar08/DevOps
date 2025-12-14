#### User password update via elastisearch api
curl -k -X PUT -u elastic:'elastic@123#' \
  "https://localhost:9200/_security/user/logstash_system/_password" \
  -H 'Content-Type: application/json' \
  -d '{
    "password" : "logstash@123#"
  }'


#### Verify the User update password via elastisearch api
curl -k -u logstash_system:'logstash@123#' https://10.68.2.61:9200/_security/_authenticate?pretty



#### Default Credentials
Username          Password
----------------------------------
elastic           elastic@123#
kibana_system     kibana@123#
logstash_system   logstash@123#



#### Hostmap
[root@elastic-product-node1 ~]# cat /etc/hosts
10.68.2.61 es-product-node1.sagar.com.np kibana-product-node1.sagar.com.np logstash-product-node1.sagar.com.np
10.68.2.62 es-product-node2.sagar.com.np kibana-product-node2.sagar.com.np logstash-product-node2.sagar.com.np
10.68.2.63 es-product-node3.sagar.com.np kibana-product-node3.sagar.com.np logstash-product-node3.sagar.com.np
[root@elastic-product-node1 ~]#


#### Elasticsearch
[root@elastic-product-node1 ~]# cat /etc/elasticsearch/elasticsearch.yml
cluster.name: elk
node.name: node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: es-product-node1.sagar.com.np
http.port: 9200
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  keystore.path: certs/http.p12
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12
discovery.seed_hosts: ["10.68.2.61:9300", "10.68.2.62:9300", "10.68.2.63:9300"]





[root@elastic-product-node2 ~]# grep -vE '^\s*#|^\s*$' /etc/elasticsearch/elasticsearch.yml
cluster.name: elk
node.name: node-2
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: es-product-node2.sagar.com.np
http.port: 9200
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  keystore.path: certs/http.p12
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12
discovery.seed_hosts: ["10.68.2.61:9300", "10.68.2.62:9300", "10.68.2.63:9300"]
http.host: 0.0.0.0
transport.host: 0.0.0.0




[root@elastic-product-node3 ~]# grep -vE '^\s*#|^\s*$' /etc/elasticsearch/elasticsearch.yml
cluster.name: elk
node.name: node-3
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: es-product-node3.sagar.com.np
http.port: 9200
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  keystore.path: certs/http.p12
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12
discovery.seed_hosts: ["10.68.2.61:9300", "10.68.2.62:9300", "10.68.2.63:9300"]
http.host: 0.0.0.0
transport.host: 0.0.0.0




#### Kibana
[root@elastic-product-node1 ~]# cat /etc/kibana/kibana.yml
http.host: 0.0.0.0
server.port: 5601
server.host: 0.0.0.0
elasticsearch.hosts: ["https://10.68.2.61:9200","https://10.68.2.62:9200","https://10.68.2.63:9200"]
elasticsearch.username: "kibana_system"
elasticsearch.password: "kibana@123#"
elasticsearch.ssl.verificationMode: none   # optional for self-signed certs
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




#### Logstash
[root@elastic-product-node1 ~]# cat /etc/logstash/logstash.yml
# ======================== Logstash Settings ========================

# Path to pipeline configs
path.config: "/etc/logstash/conf.d/*.conf"

# Pipeline settings
pipeline.workers: 2
pipeline.batch.size: 125
pipeline.batch.delay: 5

# Path to logs
path.logs: "/var/log/logstash"

# Queue settings
queue.type: persisted
queue.page_capacity: 64mb
queue.max_bytes: 1024mb

# Dead letter queue
dead_letter_queue.enable: true
dead_letter_queue.max_bytes: 1024mb

# HTTP API
http.host: "0.0.0.0"
http.port: 9600-9700

# Node settings
node.name: "logstash-node-1"

# Elasticsearch output SSL
xpack.monitoring.enabled: true
xpack.monitoring.elasticsearch.username: "logstash_system"
xpack.monitoring.elasticsearch.password: "new_logstash_password@123"
xpack.monitoring.elasticsearch.hosts: ["https://10.68.2.61:9200","https://10.68.2.62:9200","https://10.68.2.63:9200"]
xpack.monitoring.elasticsearch.ssl.verification_mode: none


# /etc/logstash/conf.d/*.conf
output {
  elasticsearch {
    hosts => ["https://10.68.2.61:9200","https://10.68.2.62:9200","https://10.68.2.63:9200"]
    user => "logstash_system"
    password => "new_logstash_password@123"
    ssl => true
    ssl_certificate_verification => false
    index => "logstash-%{+YYYY.MM.dd}"
  }
}
