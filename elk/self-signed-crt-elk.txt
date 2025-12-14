━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Install java on both the servers. (in case of elk-tarball setup it has preinstalled java on it).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Install Java-jdk 17 or later.
# download link : https://bell-sw.com/pages/downloads/?version=java-21&os=linux&bitness=64&package=jdk
```bash
cd /opt/
wget "https://download.bell-sw.com/java/21.0.7+9/bellsoft-jdk21.0.7+9-linux-amd64.tar.gz" # for X86_64
# wget "https://download.bell-sw.com/java/21.0.7+9/bellsoft-jdk21.0.7+9-linux-aarch64.tar.gz" # for ARM(aarch64) architecture AmazonLinux
tar xvzf bellsoft-jdk21*.tar.gz
mv jdk-21.0.7 jdk21 # path is /opt/jdk21

# JAVA_HOME Set.
echo -e 'export JAVA_HOME=/opt/jdk21\nexport PATH=$JAVA_HOME/bin:$PATH' >> ~/.bash_profile && source ~/.bash_profile
java -version
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ELasticsearch Self Signed-SSL setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Download and install elasticsearch from rpm
wget "https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.18.0-x86_64.rpm"
sudo rpm -ivf elasticsearch-8.18.0-x86_64.rpm
Do not start the service.


### ELK SELF Signed Certificates Generations.
http.p12 --> this is a private key of a elasicsearch
http_ca.crt --> this a certificate authority that sign the private key.

Self sign cerificate generate (ON ELASTICSEARCH NODE ONLY).
A. first generate a CA certificate.
    1. using this CA --> generate a elasticsearch SSL ceriticate
    2. using this CA --> generate a kibana SSL certificate.


## Self sign cerificate generate.
### A. first generate a CA certificate.
/usr/share/elasticsearch/bin/elasticsearch-certutil ca --pem --out /etc/elasticsearch/certs/ca.zip
cd /etc/elasticsearch/certs/
unzip ca.zip

### 1. Using this CA --> generate a elasticsearch SSL ceriticate
/usr/share/elasticsearch/bin/elasticsearch-certutil cert \
    --out /etc/elasticsearch/certs/elastic.zip \
    --name elastic \
    --ca-cert /etc/elasticsearch/certs/ca/ca.crt \
    --ca-key /etc/elasticsearch/certs/ca/ca.key \
    --ip 192.168.121.110 \
    --pem;
cd /etc/elasticsearch/certs/;
unzip elastic.zip


### 2. Using this CA --> generate a kibana SSL certificate.
### this kibana cerificate generates on elasticsearch node, copy this to kibana server later.
/usr/share/elasticsearch/bin/elasticsearch-certutil cert \
    --out /etc/elasticsearch/certs/kibana.zip \
    --name elastic \
    --ca-cert /etc/elasticsearch/certs/ca/ca.crt \
    --ca-key /etc/elasticsearch/certs/ca/ca.key \
    --ip 192.168.121.110 \
    --pem;
cd /etc/elasticsearch/certs/;
unzip kibana.zip

ES: 
# Edit the elasticsearch.yml file
##### elasticsearch.yml #####
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
##### elasticsearch.yml end here #####
```
### Proper file permission.
chown -R elasticsearch:elasticsearch /etc/elasticsearch \
sudo chown -R elasticsearch:elasticsearch /etc/elasticsearch /var/lib/elasticsearch /var/log/elasticsearch
sudo chmod -R 750 /etc/elasticsearch/certs

### Service restart.
systemctl daemon-reload
systemctl enable elasticsearch
systemctl start elasticsearch

### default user password reset
Note: if you install elasticsearch using tarball then default username and password will be `elastic`:`elastic`.
/usr/share/elasticsearch/bin/elasticsearch-reset-password -i -u elastic # elastic@123#
/usr/share/elasticsearch/bin/elasticsearch-reset-password -i -u kibana_system # kibana@123#
### new password: elastic@123#

# auto password generate for all services
# The following commands will generates the passwords for the user: elastic, kibana_system, kibana, beats_system, logstash_system etc.
/usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto 

### check the SSL works or not.
curl -X GET -u elastic:elastic@123# https://192.168.121.110:9200 --cacert /etc/elasticsearc/cert/ca/ca.crt


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## KIBANA SETUP With Self-signed SSL.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Install Java JDK21.
Install kibana
  wget https://artifacts.elastic.co/downloads/kibana/kibana-8.18.0-x86_64.rpm
  sudo rpm -ivh kibana-8.18.0-x86_64.rpm
  Do not start the service.

Copy the self-signed certificate that generated earlier on elasticsearch server to kibana server 
certificate path: /etc/kibana/certs/

### change the Certificate ownership to kibana
chown -R kibana:kibana /etc/kibana /var/lib/kibana /var/log/kibana

Create Service Token
  Run this command on the `Elasticsearch server`: 
  /usr/share/elasticsearch/bin/elasticsearch-service-tokens create elastic/kibana kibana-token
  Copy the token that you see.

Run this command on the Kibana server: 
  /usr/share/kibana/bin/kibana add elasticsearch.serviceAccountToken  # this will not works on newer version of elk.
  Press Enter.
  < Paste in the token after the prompt.>

vi /etc/kibana/kibana.yml
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

systemctl enable kibana;
systemctl start kibana;
check the logs.



# uninstall
# 1. Stop Elasticsearch service
systemctl stop elasticsearch
systemctl disable elasticsearch

# 2. Remove Elasticsearch package
yum remove -y elasticsearch

# 3. Delete Elasticsearch directories
rm -rf /etc/elasticsearch
rm -rf /var/lib/elasticsearch
rm -rf /var/log/elasticsearch
rm -rf /usr/share/elasticsearch
rm -rf /opt/elasticsearch*  # If you manually installed it here
rm -rf /etc/systemd/system/elasticsearch.service
rm -rf /etc/sysconfig/elasticsearch  # Optional config dir
# rm -rf /tmp/elasticsearch*           # Clean any temp files

# 4. Remove elasticsearch user and group (if dedicated)
userdel -r elasticsearch 2>/dev/null
groupdel elasticsearch 2>/dev/null

# 5. Reload systemd to clean up lingering service units
systemctl daemon-reload

# 6. Optionally clean up firewall and SELinux rules (if you added any)
# Example (only if you did it manually):
# firewall-cmd --permanent --remove-port=9200/tcp
# firewall-cmd --permanent --remove-port=9300/tcp
# firewall-cmd --reload






############################## new test ###########################################

# Enable encryption for HTTP API client connections, such as Kibana, Logstash, and Agents
xpack.security.http.ssl:
  enabled: true
  # keystore.path: certs/http.p12

# Enable encryption and mutual authentication between cluster nodes
xpack.security.transport.ssl:
  enabled: true
  verification_mode: certificate
  keystore.path: certs/transport.p12
  truststore.path: certs/transport.p12





# HTTP (for browser/API clients)
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.key: /etc/elasticsearch/certs/private.key
xpack.security.http.ssl.certificate: /etc/elasticsearch/certs/full.crt

# Transport (between nodes)
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.key: /etc/elasticsearch/certs/private.key
xpack.security.transport.ssl.certificate: /etc/elasticsearch/certs/full.crt
xpack.security.transport.ssl.certificate_authorities: [ "/etc/elasticsearch/certs/full.crt" ]










####
## Self sign cerificate generate.
### A. first generate a CA certificate.
/usr/share/elasticsearch/bin/elasticsearch-certutil ca --pem --out /etc/elasticsearch/certs/ca.zip
cd /etc/elasticsearch/certs/
unzip ca.zip

### 1. Using this CA --> generate a elasticsearch SSL ceriticate
/usr/share/elasticsearch/bin/elasticsearch-certutil cert \
    --out /etc/elasticsearch/certs/elastic.zip \
    --name elastic \
    --ca-cert /etc/elasticsearch/certs/ca/ca.crt \
    --ca-key /etc/elasticsearch/certs/ca/ca.key \
    --ip 192.168.121.110 \
    --pem;
cd /etc/elasticsearch/certs/;
unzip elastic.zip



/usr/share/elasticsearch/bin/elasticsearch-certutil cert \
  --name elastic \
  --ca-cert /etc/elasticsearch/certs/ca/ca.crt \
  --ca-key /etc/elasticsearch/certs/ca/ca.key \
  --dns your-hostname \
  --ip your.ip.address \
  --out /etc/elasticsearch/certs/elastic-bundle.p12


chown elasticsearch:elasticsearch /etc/elasticsearch/certs/elastic-bundle.p12
chmod 600 /etc/elasticsearch/certs/elastic-bundle.p12


# 
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.key: /etc/elasticsearch/certs/elk-cluster/elk-cluster.key
xpack.security.http.ssl.certificate: /etc/elasticsearch/certs/elk-cluster/elk-cluster.crt
xpack.security.http.ssl.certificate_authorities: [ "/etc/elasticsearch/certs/ca/ca.crt" ]

xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.key: /etc/elasticsearch/certs/elk-cluster/elk-cluster.key
xpack.security.transport.ssl.certificate: /etc/elasticsearch/certs/elk-cluster/elk-cluster.crt
xpack.security.transport.ssl.certificate_authorities: [ "/etc/elasticsearch/certs/ca/ca.crt" ]
# 


# 
xpack.security.enabled: true

xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.keystore.path: /etc/elasticsearch/certs/elastic-bundle.p12
xpack.security.transport.ssl.truststore.path: /etc/elasticsearch/certs/elastic-bundle.p12
xpack.security.transport.ssl.client_authentication: required

xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: /etc/elasticsearch/certs/elastic-bundle.p12
xpack.security.http.ssl.truststore.path: /etc/elasticsearch/certs/elastic-bundle.p12
xpack.security.http.ssl.verification_mode: certificate
# 



systemctl restart elasticsearch






scp /etc/elasticsearch/certs/ca/ca.crt root@<kibana-host>:/etc/kibana/certs/ca.crt

mkdir -p /etc/kibana/certs
chown -R kibana:kibana /etc/kibana/certs
chmod 600 /etc/kibana/certs/ca.crt



elasticsearch.hosts: ["https://<elasticsearch-ip>:9200"]
elasticsearch.ssl.certificateAuthorities: ["/etc/kibana/certs/ca.crt"]
elasticsearch.ssl.verificationMode: certificate

elasticsearch.username: "kibana_system"
elasticsearch.password: "<password>"

server.ssl.enabled: false  # set to true if you want HTTPS for Kibana UI too

elasticsearch.serviceAccountToken: "YOUR_TOKEN"


/etc/logstash/conf.d/logs.conf
output {
  elasticsearch {
    hosts => ["https://<elasticsearch-ip>:9200"]
    user => "elastic"
    password => "<password>"
    ssl => true
    cacert => "/etc/logstash/certs/ca.crt"
  }
}
api_key => "id:xxx==,api_key:yyy=="
