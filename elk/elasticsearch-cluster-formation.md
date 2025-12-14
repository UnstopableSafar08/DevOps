***
# Elasticsearch Cluster Formation
***
### Configurations Explanation
```yml
# ===================== Cluster Basics =====================

cluster.name: elk-cluster           # Name of the Elasticsearch cluster
node.name: node-1                         # Unique name for this node
node.roles: [ master ]                    # This node acts as a master only. Avaliable values: master, data, ingest etc.

# ===================== Paths ==============================

path.data: /var/lib/elasticsearch         # Directory where data (shards) is stored
path.logs: /var/log/elasticsearch         # Directory for Elasticsearch logs

# ===================== Networking =========================

network.host: 192.168.121.110               # Node's private IP address
http.port: 9200                           # REST API access port
transport.port: 9300                      # Internal cluster communication port

# ===================== Discovery ==========================

discovery.seed_hosts:                     # IPs of all nodes (used for cluster discovery)
  - 192.168.121.110                         # This node
  - 192.168.121.111                        # Another node
  - 192.168.121.112                        # Another node

# Required ONLY during initial cluster boot, 
# Once the cluster is up and running, Comments/remove this line from all nodes' configs to avoid startup issues in the future.
cluster.initial_master_nodes:            
  - node-1                               # Node name (not IP)
  - node-2
  - node-3

# ===================== Security (X-Pack) ==================

xpack.security.enabled: true              # Enables authentication and encryption

xpack.security.http.ssl:                  # HTTPS for REST API (e.g. Kibana)
  enabled: true
  keystore.path: certs/http.p12           # PKCS#12 keystore with HTTPS certificate

xpack.security.transport.ssl:             # Encryption for node-to-node communication
  enabled: true
  verification_mode: certificate          # Verifies certs via truststore
  keystore.path: certs/transport.p12      # Node's own transport cert
  truststore.path: certs/transport.p12    # Certs of other trusted nodes

# ===================== Optional Enhancements ==============

http.host: 0.0.0.0                         # Allow REST API from any interface (secure only with HTTPS)
transport.host: 0.0.0.0                    # Allow internal traffic from any local IP

# ===================== Monitoring / Enrollment ============

xpack.security.enrollment.enabled: false  # Disable auto-enrollment after setup
```


***
# Dummy elasicsearch.yml
***
```yml
cluster.name: elk
node.name: node1

path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch

network.host: 192.168.121.110 # or 0.0.0.0, accessiable only by ip from the outside
http.port: 9200
transport.port: 9300

xpack.security.enabled: true
xpack.security.enrollment.enabled: true

xpack.security.http.ssl:
  enabled: true
  key: /etc/elasticsearch/certs/elastic/elastic.key
  certificate: /etc/elasticsearch/certs/elastic/elastic.crt
  certificate_authorities: /etc/elasticsearch/certs/ca/ca.crt
#  keystore.path: certs/http.p12

xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: /etc/elasticsearch/certs/transport.p12
  truststore.path: /etc/elasticsearch/certs/transport.p12

cluster.initial_master_nodes: ["node1"] # node.name
http.host: 192.168.121.110 # or 0.0.0.0, accessiable only by ip from the outside
transport.host: 0.0.0.0

```

***
> [!NOTE]
> System Configurations : <a href="https://github.com/UnstopableSafar08/elk/blob/main/README.md" target="_blank">ELK Setup Guide.</a>
***

### Install Java-jdk 17 or later.
Download link : <a href="https://bell-sw.com/pages/downloads/?version=java-21&os=linux&bitness=64&package=jdk" target="_blank">Link</a>

```bash
# Download and install Java
cd /opt/
wget "https://download.bell-sw.com/java/21.0.7+9/bellsoft-jdk21.0.7+9-linux-amd64.tar.gz" # for X86_64
# wget "https://download.bell-sw.com/java/21.0.7+9/bellsoft-jdk21.0.7+9-linux-aarch64.tar.gz" # for ARM(aarch64) architecture AmazonLinux
tar xvzf bellsoft-jdk21*.tar.gz
mv jdk-21.0.7 jdk21 # path is /opt/jdk21

# JAVA_HOME Set.
echo -e 'export JAVA_HOME=/opt/jdk21\nexport PATH=$JAVA_HOME/bin:$PATH' >> ~/.bash_profile && source ~/.bash_profile
java -version
```

### Download and install elasticsearch from rpm (for all nodes)
```bash
# Import GPG key.
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

# Download and install elasticsearch.
wget "https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.18.0-x86_64.rpm"
sudo rpm -ivf elasticsearch-8.18.0-x86_64.rpm
```

# I have node1, node2, node3, node4, node5.
Install the elasticsearch using rpm repo or using tarball.
    same installation for all the nodes.
    do not start at all.

Default Configuration of yml file
```yml    
cluster.name: elk
node.name: node1
network.host: 192.168.121.110
http.port: 9200
transport.port: 9300
cluster.initial_master_nodes: ["node1"] # this is required durig cluster setup, if the cluster formed, comment this line.
http.host: 192.168.121.110 # or 0.0.0.0, accessiable only by ip from the outside
transport.host: 0.0.0.0
```

### Daemon reload, enable and start the elasticsearch
```bash
# Troubleshooting Tips: Start and view the logs instant.
sudo systemctl daemon-reexec ; sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch -v

systemctl enable elasticsearch
systemctl start elasticsearch
```
Check the status of elasticsearch  | Check the logs /var/log/elasticsearch/

### Reset the elastic user password on node-1.
```bash
### default user password reset
# Note: if you install elasticsearch using tarball then default username and password will be `elastic`:`elastic`.
/usr/share/elasticsearch/bin/elasticsearch-reset-password -i -u elastic # password: elastic@123#
/usr/share/elasticsearch/bin/elasticsearch-reset-password -i -u kibana_system # kibana@123#

# auto password generate for all services
# The following commands will generates the passwords for the user: elastic, kibana_system, kibana, beats_system, logstash_system etc.
/usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto 

### check the SSL works or not.
curl -X GET -u elastic:elastic@123# https://192.168.121.110:9200 --cacert /etc/elasticsearc/cert/ca/ca.crt
```

### verification
```bash
curl -X GET -k -u elastic:elastic@123# https://192.168.121.110:9200
curl -X GET -k -u elastic:elastic@123# https://192.168.121.110:9200/_cluster/health?pretty
curl -X GET -k -u elastic:elastic@123# https://192.168.121.110:9200/_cat/nodes?pretty
curl -X GET -k -u elastic:elastic@123# https://192.168.121.110:9200/_cat/master?pretty
```

### create a enrollment token (ON node1) 
- this token will be expired on 30min, 
- so joins cluster with in 30 min.
- or after that the 30min you have to regenerate the new tokens to join the remaining nodes to cluster.
```bash
/usr/share/elasticsearch/bin/elasticsearch-create-enrollment-token -s node
```

<mark>### Node-2,3,4,5</mark> <br>
Joining a cluster(ON node2,3,4,5).
```bash
/usr/share/elasticsearch/bin/elasticsearch-reconfigure-node --enrollment-token <paste the token>
```
> [!INFO]
> if the elasticsearch Node already initialized | reused/re-IP:<br>
`/usr/share/elasticsearch/bin/elasticsearch --reconfigure-node`<br><br>
> if the elasticsearch Brand-new node | never started:<br>
`/usr/share/elasticsearch/bin/elasticsearch --enrollment-token` <paste-token-here>

<br>

| Command                                                                 | Purpose                                                                 | When to Use                                              | Output/Behavior                                                                  |
|-------------------------------------------------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------|----------------------------------------------------------------------------------|
| `/usr/share/elasticsearch/bin/elasticsearch --reconfigure-node`        | Reconfigures an existing node’s identity (CA, certs, node name, etc.)  | When changing cluster name, node name, or rejoining clean | Re-initializes the node settings; may delete old identity files or certs        |
| `/usr/share/elasticsearch/bin/elasticsearch --enrollment-token <token>`| Joins a new node to an existing secured cluster using a token          | When bootstrapping a **new node** into a secure cluster  | Uses the token to fetch CA certs and auto-configures security settings          |

### Daemon reload, enable and start the elasticsearch
```bash
# Troubleshooting Tips: Start and view the logs instant.
sudo systemctl daemon-reexec ; sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch -v

systemctl enable elasticsearch
systemctl start elasticsearch
```
> [!WARNING]
> At a time only one node can joins the cluster(master-node). so do the above step one by one each nodes. **Don't try simultaneously.**

### Starting Cluster Formation.
Once the cluster formed, we can update the self-signed certificates or public certificate on the cluster nodes.
- Generates the self-signed CA and SSL certificates on the elasticsearch first node with the help of cert-utils tools.
- Copy the CA certificates to all the nodes path `/etc/elasticsearch/certs/`.
- On node2(and 3,4,5) - generate the certificates by using the copied CA certificate, this will sighed the SSL Certificates.
- now change the ownership of certs and provide the file permission to the certs.
    `chown -R elasticsearch:elasticsearch /etc/elasticsearch/certs`
    `chmod -R 750 /etc/elasticsearch/certs`
Daemon reload, enable and start the elasticsearch


<mark>### node2 and node3...node5 setup commands.</mark>
```bash
sudo rpm -ivh elasticsearch-8.18.0-x86_64.rpm # or yum install elasticsearch -y
```
> [!NOTE] 
> - The enrollmet-token generated by node1 only validate for 30mins, after the 30min this will not works.
> - If the token is not expired, then it will used to join a cluster for all the other node2,3,4,5 within the 30 mins.
> - If the token is expired (show the error like: ...with exit code 69) then, new node cant join the cluster. In such a case goto node and regenerate the token and join.

Joining Cluster with a enrollment-tokens.
```bash
/usr/share/elasticsearch/bin/elasticsearch-reconfigure-node --enrollment-token eyJ2ZXIiOiI4LjE0LjAiLCJhZHIiOlsiMTkyLjE2OC4xMjEuMTEwOjkyMDAiXSwiZmdyIjoiZWViZGJjZTI5OWVkMThiYzFhNzkzODA5NjRjNGIzMThiZWZlMGZmMWI4ZTJkMTc5ZGI3NWIwYWJjOTg5Mzk5YSIsImtleSI6IjI4SnpqSllCcDdZTXVsdWhpWFVMOlBPTHpoZ0hzRDVhQWY0MWlqX1hSaUEifQ==
```
JVM Options:
Assign a half of the Total RAM to jvm options. In my case total ram is : 8GB
```bash
echo "-Xms4g" >> /etc/elasticsearch/jvm.options
echo "-Xmx4g" >> /etc/elasticsearch/jvm.options
```
### Elasticsearch Service commands.
```bash
# Troubleshooting Tips: Start and view the logs instant.
sudo systemctl daemon-reexec ; sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch -v

systemctl enable elasticsearch
systemctl start elasticsearch
systemctl status elasticsearch
systemctl stop elasticsearch
```

#### Get the config only form the yml file.
```bash
grep -v '^\s*#' /etc/elasticsearch/elasticsearch.yml | grep -v '^\s*$'  # get config
```


### The configurations of the nodes during the cluster formation.
```bash
vi /etc/elasticsearch/elasticsearch.yml
```

## node1:
```yml
cluster.name: elk
node.name: node1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.110
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
cluster.initial_master_nodes: ["node1"]
http.host: 0.0.0.0
```


## node2:
```yml
cluster.name: elk
node.name: node1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.112
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
discovery.seed_hosts: ["192.168.121.110:9300"]
http.host: 0.0.0.0
transport.host: 0.0.0.0
```

## Node3 (do same for node4,5):
```yml
cluster.name: elk
node.name: node1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.111
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
discovery.seed_hosts: ["192.168.121.110:9300", "192.168.121.112:9300"]
http.host: 0.0.0.0
transport.host: 0.0.0.0
```

### Update he configurations of the nodes during the cluster formation.
comment the following line if existing on the each nodes.
  `cluster.initial_master_nodes: ["node1"]`

add/verify the ips/dns/hostname of all clustre nodes to the following line
 
 - `transport.host: 0.0.0.0`
 - `discovery.seed_hosts: ["192.168.121.110:9300", "192.168.121.112:9300","192.168.121.111:9300"]`


### updated config of elasticsearch
CMD:  `grep -v '^\s*#' /etc/elasticsearch/elasticsearch.yml | grep -v '^\s*$'  # get config`

## Node1:
```yml
cluster.name: elk
node.name: node1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.110
http.port: 9200
discovery.seed_hosts: ["192.168.121.110:9300", "192.168.121.112:9300", "192.168.121.111:9300"]
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
http.host: 0.0.0.0
transport.host: 0.0.0.0
```

## Node2:
```yml
cluster.name: elk
node.name: node2
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.112
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
discovery.seed_hosts: ["192.168.121.110:9300", "192.168.121.112:9300", "192.168.121.111:9300"]
http.host: 0.0.0.0
transport.host: 0.0.0.0
```

## Node3 (same for node4,5):
```yml
cluster.name: elk
node.name: node3
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.111
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
discovery.seed_hosts: ["192.168.121.110:9300", "192.168.121.112:9300", "192.168.121.111:9300"]
http.host: 0.0.0.0
transport.host: 0.0.0.0
```

### self-signed cert
## Node1: 
```yml
cluster.name: elk
node.name: node1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.110
http.port: 9200
http.host: 0.0.0.0
transport.host: 0.0.0.0
discovery.seed_hosts:
  - 192.168.121.110:9300
  - 192.168.121.112:9300
  - 192.168.121.111:9300
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  certificate: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.110.crt
  key: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.110.key
  certificate_authorities:
    - /etc/elasticsearch/certs/ca/ca.crt
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  certificate: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.110.crt
  key: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.110.key
  certificate_authorities:
    - /etc/elasticsearch/certs/ca/ca.crt
```

## Node2:
```yml
cluster.name: elk
node.name: node2
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.112
http.port: 9200
http.host: 0.0.0.0
transport.host: 0.0.0.0
discovery.seed_hosts:
  - 192.168.121.110:9300
  - 192.168.121.112:9300
  - 192.168.121.111:9300
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  certificate: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.112.crt
  key: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.112.key
  certificate_authorities:
    - /etc/elasticsearch/certs/ca/ca.crt
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  certificate: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.112.crt
  key: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.112.key
  certificate_authorities:
    - /etc/elasticsearch/certs/ca/ca.crt
```

## Node3 (same for node4,5):
```yml
cluster.name: elk
node.name: node3
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 192.168.121.111
http.port: 9200
http.host: 0.0.0.0
transport.host: 0.0.0.0
discovery.seed_hosts:
  - 192.168.121.110:9300
  - 192.168.121.112:9300
  - 192.168.121.111:9300
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.http.ssl:
  enabled: true
  certificate: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.111.crt
  key: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.111.key
  certificate_authorities:
    - /etc/elasticsearch/certs/ca/ca.crt
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  certificate: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.111.crt
  key: /etc/elasticsearch/certs/elastic/elasticsearch/192.168.121.111.key
  certificate_authorities:
    - /etc/elasticsearch/certs/ca/ca.crt
```

## Kibana:
```yml
server.name: kibana.elk.local
server.host: "192.168.121.110" # or 0.0.0.0
server.publicBaseUrl: "https://192.168.121.110:5601"  # kibana Public URL, not required for selfsigned SSL cerificate.
server.port: 5601
server.ssl.enabled: true
server.ssl.certificate: /etc/kibana/certs/elastic/elasticsearch/192.168.121.110.crt
server.ssl.key: /etc/kibana/certs/elastic/elasticsearch/192.168.121.110.key
elasticsearch.hosts: ["https://192.168.121.110:9200"]
elasticsearch.ssl.certificateAuthorities: [ "/etc/kibana/certs/ca/ca.crt" ]
elasticsearch.ssl.verificationMode: certificate
elasticsearch.serviceAccountToken: "AAEAAWVsYXN0aWMva2liYW5hL2tpYmFuYS10b2tlbjpqNG9jdElNVVIzYVMyWmxJRzFKajR3"
```


### ERROR:
> ERROR: Aborting enrolling to cluster. This node does not appear to be auto-configured for security. 
Expected configuration is missing from elasticsearch.yml., with exit code 64

Solutions:
### uninstall the elasticsearch completely.

```bash
# Delete the cluster-nodes files.
rm -rf /var/lib/elasticsearch/node*
```

```bash  
# OR Completely uninstall,
systemctl stop elasticsearch
systemctl disable elasticsearch
yum remove -y elasticsearch
rm -rf /etc/elasticsearch
rm -rf /var/lib/elasticsearch
rm -rf /var/log/elasticsearch
rm -rf /usr/share/elasticsearch
# rm -rf /opt/elasticsearch*  # If you manually installed it here
rm -rf /etc/systemd/system/elasticsearch.service
rm -rf /etc/sysconfig/elasticsearch  # Optional config dir
rm -rf /tmp/elasticsearch*           # Clean any temp files
userdel -r elasticsearch 2>/dev/null
groupdel elasticsearch 2>/dev/null
rpm -qa | grep elastic*
systemctl daemon-reload
```
- reboot the server.
- reinstall the elasticsearch.
- rejoin the cluster by < -reconfigure-node --enrollment-token > with the newly created token by node1


### ERROR
**ERROR:** Aborting enrolling to cluster. 
Could not communicate with the node on any of the addresses from the enrollment token. 
All of [192.168.121.110:9200] were attempted., with exit code 69

**Solutions:**
Check the API of the node1
  curl -k https://192.168.121.110:9200 , if get respond then ok.
  check the yml config of node1.
  
rejoin the cluster by < -reconfigure-node --enrollment-token >
  `elasticsearch-reconfigure-node --enrollment-token <token with the newly created token by node1>`

### Daemon reload and service restart
```bash
# Troubleshooting Tips: Start and view the logs instant.
sudo systemctl daemon-reexec ; sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch -v

systemctl restart elasticsearch
```

### Final Check
```bash
curl -k -u elastic:elastic@123# -X GET "https://192.168.121.112:9200/_cat/nodes?pretty"
192.168.121.112 53 90 68 0.99 0.43 0.16 cdfhilmrstw - node2
192.168.121.111 53 83 35 0.55 0.26 0.09 cdfhilmrstw - node3
192.168.121.110 48 93  3 0.26 0.21 0.09 cdfhilmrstw * node1
```

### ERROR
If the cluster_uuid doesnt match, then delete the nodes folder in the data node server,
  `rm -rf /var/lib/elasticsearch/nodes`

and restart
  `sudo service elasticsearch restart`

Check again the cluster health for the correct value
  `curl -XGET 'http://localhost:9200/_cluster/health?pretty'`

***

# Kibana install and setup
- install java - same as above
- add elastic repo
- add elastic GPG key.

### Install kibana rpm # or yum install kibana -y
```bash
# Import GPG key.
sudo rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch

# Download and install kibana
wget https://artifacts.elastic.co/downloads/kibana/kibana-8.18.0-x86_64.rpm
sudo rpm -ivh kibana-8.18.0-x86_64.rpm
```  
> [!CAUTION]
> Do not start the service. 

**Copy the self-signed certificate that generated earlier on elasticsearch server to kibana server** 
**certificate path: /etc/kibana/certs/**
```bash
mkdir -p /etc/kibana/certs/
```

### change the Certificate ownership to kibana
```bash
chown -R kibana:kibana /etc/kibana /var/lib/kibana /var/log/kibana
chown -R kibana:kibana /etc/kibana/certs
chmod -R 750 /etc/kibana/certs
```
### Create Service Token
Run this command on the `Elasticsearch server`: 
```bash
/usr/share/elasticsearch/bin/elasticsearch-service-tokens create elastic/kibana kibana-token
```
Copy the generated token. **This token will be valid for 30 min only**, after that it will be expired.

### Run this command on the Kibana server: 
```bash
/usr/share/kibana/bin/kibana add elasticsearch.serviceAccountToken 
```
- Press Enter.
- < Paste in the token after the prompt.>

### Kibana configuration.
```bash
vi /etc/kibana/kibana.yml
```

Kibana.yml
```yml
# configurations
server.port: 5601
server.host: 0.0.0.0 # or host ip
server.publicBaseUrl: "https://192.168.121.110:5601"  # kibana url, not required for selfsigned SSL cerificate.
server.ssl.enabled: true
server.ssl.key: /etc/kibana/certs/kibana/kibana.key
server.ssl.certificate: /etc/kibana/certs/kibana/kibana.crt
server.ssl.certificateAuthorities: /etc/kibana/certs/ca/ca.crt
elasticsearch.hosts: ["https://192.168.121.110:9200"] # elasticsearch API URL with port.
elasticsearch.ssl.verificationMode: full
elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/ca/ca.crt"]
elasticsearch.serviceAccountToken: "elasticsearch kibana-service token here"
```

```bash
systemctl daemon-reload
systemctl enable kibana;
systemctl start kibana;
```

> Browser: https://192.168.121.110:5601


#  Kibana Cluster formation
```bash
vi /etc/kibana/kibana.yml
```
add `elasticsearch.hosts: ["https://192.168.121.110:9200", "https://192.168.121.112:9200", "https://192.168.121.112:9200"]` on kibana.yml 
```yml
# configurations
server.port: 5601
server.host: 0.0.0.0 # or host ip
server.publicBaseUrl: "https://192.168.121.110:5601"  # kibana url, not required for selfsigned SSL cerificate.
server.ssl.enabled: true
server.ssl.key: /etc/kibana/certs/kibana/kibana.key
server.ssl.certificate: /etc/kibana/certs/kibana/kibana.crt
server.ssl.certificateAuthorities: /etc/kibana/certs/ca/ca.crt
elasticsearch.hosts: ["https://192.168.121.110:9200", "https://192.168.121.112:9200", "https://192.168.121.112:9200"] # elasticsearch API URL with port.
elasticsearch.ssl.verificationMode: full
elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/ca/ca.crt"]
elasticsearch.serviceAccountToken: "elasticsearch kibana-service token here"
```

```bash
#   Troubleshooting : Start and check the logs.
sudo systemctl daemon-reexec ; sudo -u kibana /usr/share/kibana/bin/kibana

# OR
systemctl enable kibana
systemctl start kibana
```

> Browser: https://192.168.121.110:5601


### complete uninstall
```bash
#!/bin/bash

echo "Stopping Kibana service..."
sudo systemctl stop kibana

echo "Removing Kibana via yum..."
sudo yum remove -y kibana

echo "Deleting Kibana directories..."
sudo rm -rf /etc/kibana
sudo rm -rf /var/log/kibana
sudo rm -rf /var/lib/kibana

echo "Reloading systemd and resetting failed units..."
sudo systemctl daemon-reload
#sudo systemctl reset-failed

echo "Kibana has been completely uninstalled."
```

### create a new user with superuser roles
```bash
./elasticsearch-users useradd admin -p 'elastic@123#' -r superuser
```
