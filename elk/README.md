# ELK Stack 8.xx Setup with Self-Signed SAN Certificates

This guide details the setup of ELK Stack (Elasticsearch, Logstash, Kibana, Filebeat, Metricbeat, Heartbeat) version 8.xx on a RHEL/CentOS 8 server with 8GB RAM, 4 cores, 500GB HDD, and network `192.168.121.0/24`. It includes Java 21 (BellSoft JDK 21.0.7) installation, RPM package downloads using `wget`, self-signed SAN certificates (wildcard `*.elk.local`, IPs `192.168.121.110-114`) in `.p12` format with passwords, TLS for HTTP and transport layers, Elasticsearch keystore management for certificates, host mappings using domain names (`es.elk.local`, `kibana.elk.local`, `logstash.elk.local`), and system configuration. Long commands are formatted as multiline for readability.

## System Requirements
- **Hardware**: 8GB RAM, 4 cores, 500GB HDD
- **OS**: RHEL/CentOS 8
- **Network**: `192.168.121.0/24`
- **Ports**: 9200 (Elasticsearch HTTP), 9300 (transport), 5601 (Kibana), 5044 (Logstash Beats)
- **Nodes**:
  - Elasticsearch: `192.168.121.110` (`es.elk.local`)
  - Kibana: `192.168.121.111` (`kibana.elk.local`)
  - Logstash, Filebeat, Metricbeat, Heartbeat: `192.168.121.112` (`logstash.elk.local`)

## Best Practices
- Run Elasticsearch as the primary service.
- Enable TLS for all communications.
- Restrict certificate permissions (`660`, `elasticsearch:elasticsearch`).
- Disable swap, set `vm.max_map_count=262144`.
- Allow only necessary ports in the firewall.
- Monitor with Metricbeat/Heartbeat.
- Secure keystore passwords and avoid exposing them in logs.
- Ensure `/etc/hosts` mappings are consistent across nodes.

## System Configuration
1. **JVM Heap**:
   - Elasticsearch: `-Xms4g -Xmx4g` in `/etc/elasticsearch/jvm.options`
2. **Swap**:
   ```bash
   swapoff -a
   # Comment out swap in /etc/fstab
   ```
3. **Virtual Memory**:
   ```bash
   echo "vm.max_map_count=262144" >> /etc/sysctl.conf
   sysctl -p
   ```
4. **Limits**:
   ```bash
   echo "elasticsearch soft nofile 65535" >> /etc/security/limits.conf
   echo "elasticsearch hard nofile 65535" >> /etc/security/limits.conf
   ```
5. **Sysctl**:
   ```bash
   cat << EOF >> /etc/sysctl.conf
   # elasticsearch config
   vm.max_map_count=262144
   vm.swappiness=1
   
   # optional
   # net.core.netdev_max_backlog=4096
   # net.core.rmem_default=262144
   # net.core.rmem_max=67108864
   # net.ipv4.udp_rmem_min=131072
   # net.ipv4.udp_mem=2097152 4194304 8388608
   EOF
   sysctl -p
   ```
6. **Firewall**:
   ```bash
   firewall-cmd --add-port={9200,9300,5601,5044}/tcp --permanent
   firewall-cmd --reload
   ```

Expanation:

| Role        | Ports Required       | Description                             |
|-------------|----------------------|-----------------------------------------|
| **Master**  | 9300 (required)       | Cluster coordination                    |
| **Data**    | 9300, 9200            | Stores data and responds to API queries |
| **Client/Coord** | 9200, 9300         | Forwards queries to master/data nodes   |
| **Kibana**  | 5601                  | Access via browser                      |
| **Logstash**| 5044, 5000, 9600      | Accepts logs and monitors performance   |

7. **Host Mappings**:
   ```bash
   cat << EOF >> /etc/hosts
   192.168.121.110 es.elk.local
   192.168.121.111 kibana.elk.local
   192.168.121.112 logstash.elk.local
   EOF
   ```

## Installation
1. **Install Java 21 (BellSoft JDK 21.0.7 or OpenJDK)**:
   ```bash
   cd /opt/
   wget "https://download.bell-sw.com/java/21.0.7+9/bellsoft-jdk21.0.7+9-linux-amd64.tar.gz"
   
   tar xvzf bellsoft-jdk21*.tar.gz
   mv jdk-21.0.7 jdk21
  
   echo -e 'export JAVA_HOME=/opt/jdk21\nexport PATH=$JAVA_HOME/bin:$PATH' >> ~/.bash_profile && source ~/.bash_profile
   # echo "JAVA_HOME=/opt/jdk21" >> /etc/environment
   java -version
   ```
   *Note*: For ARM (e.g., Amazon Linux on aarch64), use `wget https://download.bell-sw.com/java/21.0.7+9/bellsoft-jdk21.0.7+9-linux-aarch64.tar.gz` instead.
2. **Download and Install RPM Packages**:
   ```bash
   # Download the RPM files.
   cd /tmp
   wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.17.0-x86_64.rpm
   wget https://artifacts.elastic.co/downloads/logstash/logstash-8.17.0-x86_64.rpm
   wget https://artifacts.elastic.co/downloads/kibana/kibana-8.17.0-x86_64.rpm
   wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.17.0-x86_64.rpm
   wget https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-8.17.0-x86_64.rpm
   wget https://artifacts.elastic.co/downloads/beats/heartbeat/heartbeat-8.17.0-x86_64.rpm
   
   # Installation 
   rpm -ivh elasticsearch-8.17.0-x86_64.rpm
   rpm -ivh logstash-8.17.0-x86_64.rpm
   rpm -ivh kibana-8.17.0-x86_64.rpm
   rpm -ivh filebeat-8.17.0-x86_64.rpm
   rpm -ivh metricbeat-8.17.0-x86_64.rpm
   rpm -ivh heartbeat-8.17.0-x86_64.rpm
   ```
3. **Set Java Path for Elasticsearch**:
   ```bash
   echo "-Djava.home=/opt/jdk21" >> /etc/elasticsearch/jvm.options.d/java.options
   ```

## Certificate Generation.

Certificate Generator (Automatically steps 2 to 6) : <a href="https://github.com/UnstopableSafar08/elk/blob/main/san-self-signed-cert-generator.sh" target="_blank">LINK</a>

A. **Certificate Architecture**:
   ```bash
   [elastic-stack-ca.p12]
       ├── ca_elk.local.crt   ← used for trust
       └── ca_elk.local.key   ← NEVER shared, only for signing
   
   ↓ Signing ↓
   
   [elk.local.p12]
       ├── elk.local.crt      ← used by Elasticsearch, Kibana, Logstash
       └── elk.local.key
   ```
    
| **File**                 | **Source**               | **Role**                     | **Used By**                        | **Contains**                                  | **Security Notes**                          |
|--------------------------|---------------------------|-------------------------------|------------------------------------|------------------------------------------------|----------------------------------------------|
| `elastic-stack-ca.p12`   | Self-generated CA         | Root Certificate Authority    | Cert signing tool only             | `ca_elk.local.crt` + `ca_elk.local.key`        | 🔒 Never expose or use in TLS directly       |
| `ca_elk.local.crt`       | Extracted from CA         | Trust anchor for clients      | Kibana, Logstash, Browsers, etc.   | Public CA cert                                 | ✅ Safe to share                              |
| `ca_elk.local.key`       | Extracted from CA         | Signs other certs             | `elasticsearch-certutil` only      | Private CA key                                 | ❌ Never share or use as identity            |
| `elk.local.p12`          | Signed using CA           | Identity for a service        | Elasticsearch, Kibana, Logstash    | `elk.local.crt` + `elk.local.key`              | ✅ Use for TLS                                |
| `elk.local.crt`          | Extracted from `.p12`     | Public service certificate    | TLS servers (ES, Kibana, etc.)     | Public cert                                    | ✅ Safe to share                              |
| `elk.local.key`          | Extracted from `.p12`     | Private service key           | TLS servers (ES, Kibana, etc.)     | Private key                                    | 🔒 Must stay protected                        |


1. **Create Directories**:
   ```bash
   # Create a certs dir on each nodes accordingly.   
   mkdir -p /etc/elasticsearch/certs 
   mkdir -p /etc/kibana/certs 
   mkdir -p /etc/logstash/certs 
   mkdir -p /etc/filebeat/certs 
   mkdir -p /etc/metricbeat/certs 
   mkdir -p /etc/heartbeat/certs
   
   # Cert dir ownership and permission.  
   chown -R elasticsearch:elasticsearch /etc/elasticsearch/certs ; chmod 770 /etc/elasticsearch/certs
   chown -R kibana:kibana /etc/kibana/certs ; chmod 770 /ec/kibana/certs
   chown -R logstash:logstash /etc/logstash/certs ; chmod 770 /etc/logstash/certs
   chown -R filebeat:filebeat  /etc/filebeat/certs ; chmod 770 /etc/filebeat/certs 
   chown -R heartbeat:heartbeat  /etc/heartbeat/certs ; chmod 770 /etc/heartbeat/certs
   ```
2. **Generate CA (valid for 10 years)**:
   ```bash
   /usr/share/elasticsearch/bin/elasticsearch-certutil ca \
     --days 3650 \
     --out /etc/elasticsearch/certs/elastic-stack-ca.p12 \
     --pass "changeit"
   
   chmod 660 /etc/elasticsearch/certs/elastic-stack-ca.p12
   chown elasticsearch:elasticsearch /etc/elasticsearch/certs/elastic-stack-ca.p12
   ```
3. **Create instances.yml**:
   ```bash
   # Create instances.yml for SAN configuration
   cat > "/etc/elasticsearch/certs/instances.yml" <<EOF
   instances:
     - name: elk.local
       dns:
         - "*.elk.local"
         - "elk.local"
         - "localhost"
   EOF
   ```
4. **Generate Node Certificates**:
   ```bash
   /usr/share/elasticsearch/bin/elasticsearch-certutil cert \
     --ca /etc/elasticsearch/certs/elastic-stack-ca.p12 \
     --ca-pass "changeit" \
     --in /etc/elasticsearch/certs/instances.yml \
     --out /etc/elasticsearch/certs/elk.local.zip \
     --pass "changeit" \
     --days 3650
   
   unzip -o /etc/elasticsearch/certs/elk.local.zip -d /etc/elasticsearch/certs/
   mv /etc/elasticsearch/certs/elk.local/* /etc/elasticsearch/certs/
   rm -r /etc/elasticsearch/certs/elk.local
   
   chmod 660 /etc/elasticsearch/certs/elk.local.p12
   chown elasticsearch:elasticsearch /etc/elasticsearch/certs/elk.local.p12
   ```
5. **Extract CA .crt and .key**:
   ```bash
   openssl pkcs12 -in /etc/elasticsearch/certs/elastic-stack-ca.p12 \
     -out /etc/elasticsearch/certs/ca_elk.local.crt \
     -clcerts -nokeys \
     -passin pass:"changeit"
   
   openssl pkcs12 -in /etc/elasticsearch/certs/elastic-stack-ca.p12 \
     -out /etc/elasticsearch/certs/ca_elk.local.key \
     -nocerts -nodes \
     -passin pass:"changeit"
   
   chmod 660 /etc/elasticsearch/certs/*.crt /etc/elasticsearch/certs/*.key
   chown elasticsearch:elasticsearch /etc/elasticsearch/certs/*.crt /etc/elasticsearch/certs/*.key
   ```
6. **Extract Node .crt and .key**:
   ```bash
   openssl pkcs12 -in /etc/elasticsearch/certs/elk.local.p12 \
     -out /etc/elasticsearch/certs/elk.local.crt \
     -clcerts -nokeys \
     -passin pass:"changeit"
   
   /usr/bin/openssl pkcs12 -in /etc/elasticsearch/certs/elk.local.p12 \
     -out /etc/elasticsearch/certs/elk.local.key \
     -nocerts -nodes \
     -passin pass:"changeit"
   
   chmod 660 /etc/elasticsearch/certs/*.crt /etc/elasticsearch/certs/*.key
   chown elasticsearch:elasticsearch /etc/elasticsearch/certs/*.crt /etc/elasticsearch/certs/*.key
   ```
    ####   Generate a truststore.p12
   ```bash
   keytool -import -alias elastic-ca \
     -file /etc/elasticsearch/certs/elk.local.crt \
     -keystore /etc/elasticsearch/certs/truststore.p12 \
     -storepass "changeit" \
     -noprompt
   ```

   #### Certification Permission.
   ```bash
   chown -R elasticsearch:elasticsearch /etc/elasticsearch
   chmod 770 /etc/elasticsearch/certs
   chmod 660 /etc/elasticsearch/certs/*.p12
   chmod 660 /etc/elasticsearch/certs/*.crt /etc/elasticsearch/certs/*.key
   ```
7. **Copy Certificates**:
   ```bash
    # Copy the certificate using scp or copy to the Kibana etc.
    scp /etc/elasticsearch/certs/elk.local.crt \
        /etc/elasticsearch/certs/elk.local.key \
        /etc/elasticsearch/certs/ca_elk.local.crt \
        root@192.168.121.111:/etc/kibana/certs/.
        
    #  Copy CA, crt and key to Kibana certs path
    cp /etc/elasticsearch/certs/elk.local.crt \
        /etc/elasticsearch/certs/elk.local.key \
        /etc/elasticsearch/certs/ca_elk.local.crt \
        /etc/kibana/certs/.
    
    # Copy CA cert to Metricbeat path.
    cp /etc/elasticsearch/certs/elk.local.crt \
        /etc/elasticsearch/certs/elk.local.key \
        /etc/elasticsearch/certs/ca_elk.local.crt \
        /etc/metricbeat
    
    # file Permision.
    sudo chown -R kibana:kibana /etc/kibana
    chmod 755 /etc/kibana/certs
    chmod 660 /etc/kibana/certs/ca*
   ```

## Configure Elasticsearch
1. **Edit `/etc/elasticsearch/elasticsearch.yml`**:
    ```yaml
    cluster.name: dc-elk
    node.name: dc-elk.elk.local
    
    path.data: /var/lib/elasticsearch
    path.logs: /var/log/elasticsearch
    
    network.host: dc-elk.elk.local
    http.port: 9200
    http.host: 0.0.0.0
    
    discovery.type: single-node
    #cluster.initial_master_nodes: ["dc-elk.elk.local"]
    
    xpack.security.enabled: true
    
    # HTTP SSL (for REST APIs and Kibana)
    xpack.security.http.ssl.enabled: true
    xpack.security.http.ssl.keystore.path: /etc/elasticsearch/certs/elk.local.p12
    # xpack.security.http.ssl.keystore.secure_password: configured via elasticsearch-keystore
    xpack.security.http.ssl.truststore.path: /etc/elasticsearch/certs/truststore.p12
    # xpack.security.http.ssl.truststore.secure_password: configured via     elasticsearch-keystore
    
    # Transport SSL (for node-to-node)
    xpack.security.transport.ssl.enabled: true
    xpack.security.transport.ssl.verification_mode: certificate
    xpack.security.transport.ssl.keystore.path: /etc/elasticsearch/certs/elk.local.p12
    # xpack.security.transport.ssl.keystore.secure_password: configured via     elasticsearch-keystore
    xpack.security.transport.ssl.truststore.path: /etc/elasticsearch/certs/truststore.p12
    # xpack.security.transport.ssl.truststore.secure_password: configured via     elasticsearch-keystore
    ```
2. **Set JVM Options**:
   ```bash
   echo "-Xms6g" >> /etc/elasticsearch/jvm.options
   echo "-Xmx6g" >> /etc/elasticsearch/jvm.options
   ```

  ```bash
  mkdir -p /etc/systemd/system/elasticsearch.service.d
  cat << EOF > /etc/systemd/system/elasticsearch.service.d/override.conf
  [Service]
  Environment="ES_JAVA_OPTS=-Xms6g -Xmx6g"
  MemoryMax=8G
  EOF
  # systemctl daemon-reexec
  # systemctl restart elasticsearch
  ```
   
3. **Manage Elasticsearch Keystore**:
   ```bash
   # List current keystore entries
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore list

   # Remove existing SSL-related secure passwords
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.http.ssl.keystore.secure_password
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.http.ssl.truststore.secure_password
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.keystore.secure_password
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore remove xpack.security.transport.ssl.truststore.secure_password

   # Add new secure passwords interactively
   # Enter the password that used during the certificate create, 
   # Default passord used here is `changeit`
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.http.ssl.keystore.secure_password
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.http.ssl.truststore.secure_password
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.transport.ssl.keystore.secure_password
   sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch-keystore add xpack.security.transport.ssl.truststore.secure_password

   # Verify keystore passwords (use cautiously in production)
   /usr/share/elasticsearch/bin/elasticsearch-keystore show autoconfiguration.password_hash
   /usr/share/elasticsearch/bin/elasticsearch-keystore show keystore.seed
   /usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.http.ssl.keystore.secure_password
   /usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.http.ssl.truststore.secure_password
   /usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.transport.ssl.keystore.secure_password
   /usr/share/elasticsearch/bin/elasticsearch-keystore show xpack.security.transport.ssl.truststore.secure_password
   ```
4. **Start Elasticsearch**:
   ```bash
   # Troubleshooting Tips: Start and view the logs instant.
   sudo systemctl daemon-reexec ; sudo -u elasticsearch /usr/share/elasticsearch/bin/elasticsearch -v

   systemctl enable elasticsearch
   systemctl start elasticsearch
   ```
5. **Set/Reset Passwords**:
   ```bash
   # set password for all users automatically
   /usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto
   
   # OR set the desired password one by one.
   /usr/share/elasticsearch/bin/elasticsearch-reset-password -i -u elastic
   /usr/share/elasticsearch/bin/elasticsearch-reset-password -i -u kibana_system
   ```

## Configure Kibana

#### for Kibana HTTPS
If you want to enable HTTPS for Kibana itself, use:<br>
- Certificate: `/etc/elasticsearch/certs/elk.local.crt`<br>
- Private Key: `/etc/elasticsearch/certs/elk.local.key`<br>
- CA Cert (for trust): `/etc/elasticsearch/certs/ca_elk.local.crt`<br>

**These are sufficient since elk.local.crt is signed by your custom CA.**

#### Kibana service token.
Generate a kibana service token on `elasticsearch node`. <br>
`/usr/share/elasticsearch/bin/elasticsearch-service-tokens create elastic/kibana kibana-token` <br><br>
Add service token on `kibana node` (This will be deprecated on the latest version of elk - OR directly add the token to the kibana.yml file).<br>
`/usr/share/kibana/bin/kibana add elasticsearch.serviceAccountToken`
#### Copy the certificate to the kibana dir.
   ```bash
    # Create a certs dir
    mkdir -p /etc/elasticsearch/certs
    
    # Copy the certs from elasticsearch to kibana
    cp /etc/elasticsearch/certs/ca_elk.local.crt /etc/kibana/certs/.
    cp /etc/elasticsearch/certs/elk.local.key /etc/kibana/certs/.
    cp /etc/elasticsearch/certs/elk.local.crt /etc/kibana/certs/.
    
    sudo chown -R kibana:kibana /etc/kibana
    chmod 755 /etc/kibana/certs
    chmod 660 /etc/kibana/certs/ca.*
    chmod 640 /etc/kibana/certs/elk.local.*
   ```

1. **Edit `/etc/kibana/kibana.yml`**:
   ```yaml
    server.port: 5601
    server.host: "0.0.0.0"
    server.publicBaseUrl: "https://kibana.elk.local:5601"
    server.name: "kibana.elk.local"
    server.ssl.enabled: true
    server.ssl.certificate: /etc/kibana/certs/elk.local.crt
    server.ssl.key: /etc/kibana/certs/elk.local.key
    elasticsearch.hosts: ["https://es.elk.local:9200"]
    
    #elasticsearch.username: "kibana_system"
    #elasticsearch.password: "<kibana_system_password>"
    elasticsearch.serviceAccountToken:     "<Service-token-here>"
    
    elasticsearch.ssl.verificationMode: certificate
    elasticsearch.ssl.certificateAuthorities: [ "/etc/kibana/certs/ca_elk.local.crt" ]
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
    #### Optional : Kibana returns HTTP 500 and continuously shows the popup. fix
    Generate a kibana xpack
    ```bash
    /usr/share/kibana/bin/kibana-encryption-keys generate
    
    # Add this generated xpack to the kibana.yml file
    # =================== System: Elasticsearch (Optional) ===================
    xpack.encryptedSavedObjects.encryptionKey: 0751067f09e94cafd8fc45bc28aaf253
    xpack.reporting.encryptionKey: 5daddd8c8b002f97fb08f5a4932d7bb8
    xpack.security.encryptionKey: 24edf7b01bb79fc176725ecfe2c04b9f
    ```
    #### RAM limit for kibana
    ```bash
    # RAM limit for kibana service.
    mkdir -p /etc/systemd/system/kibana.service.d
    cat << EOF > /etc/systemd/system/kibana.service.d/override.conf
    [Service]
    Environment="NODE_OPTIONS=--max-old-space-size=1024"
    EOF
    ```
   
2. **Start Kibana**:
   ```bash
   #   Troubleshooting : Start and check the logs.
   sudo systemctl daemon-reexec ; sudo -u kibana /usr/share/kibana/bin/kibana
   
   # OR
   systemctl daemon-reexec
   systemctl enable kibana
   systemctl start kibana

   # RAM Limit verify
   cat /proc/$(pgrep -f kibana)/environ | tr '\0' '\n' | grep NODE_OPTIONS
   ps -o pid,rss,vsz,cmd -p $(pgrep -f kibana)
   ```
## Elasticsearch and kibana Dev tools cmds.
   ```bash
   #### elk commands - dev tools
   GET _cluster/health 
   GET /_cat/nodes?v
   GET /_cat/shards?v
   
   
   # Check Elasticsearch Cluster Health
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cluster/health?pretty"
   
   # Get Information About Cluster Nodes
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cat/nodes?v"
   
   # Get Detailed Information About a Specific Node (replace 'your_node_id' with    actual node ID)
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_nodes/your_node_id?pretty"
   
   # Get Information About All Node Roles
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cat/nodeattrs?v"
   
   # List All Indices
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cat/indices?v"
   
   # Get Information About a Specific Index (replace 'your_index' with index    name)
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/your_index?pretty"
   
   # Create an Index (replace 'your_index' with the desired index name)
   curl -u elastic:Ela5Tic@#987 -X PUT "http://es.elk.local:9200/your_index"
   
   # Delete an Index (replace 'your_index' with the index name you want to    delete)
   curl -u elastic:Ela5Tic@#987 -X DELETE    "http://es.elk.local:9200/your_index"
   
   # Get Cluster Nodes Information
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cat/nodes?v"
   
   # Search Data in an Index (replace 'your_index' and 'your_query' with actual    values)
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/your_index/_search?q=your_query&pretty"
   
   # Get Cluster Settings
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cluster/settings?pretty"
   
   # Add a Document to an Index (replace 'your_index' and 'your_document_id'    with actual values)
   curl -u elastic:Ela5Tic@#987 -X POST    "http://es.elk.local:9200/your_index/_doc/your_document_id" -H    'Content-Type: application/json' -d'
   {
     "field1": "value1",
     "field2": "value2"
   }
   '
   
   # Get a Document from an Index (replace 'your_index' and 'your_document_id'    with actual values)
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/your_index/_doc/your_document_id?pretty"
   
   # Delete a Document from an Index (replace 'your_index' and    'your_document_id' with actual values)
   curl -u elastic:Ela5Tic@#987 -X DELETE    "http://es.elk.local:9200/your_index/_doc/your_document_id"
   
   # Update a Document in an Index (replace 'your_index' and 'your_document_id'    with actual values)
   curl -u elastic:Ela5Tic@#987 -X POST    "http://es.elk.local:9200/your_index/_update/your_document_id" -H    'Content-Type: application/json' -d'
   {
     "doc": {
       "field1": "new_value"
     }
   }
   '
   
   # Get Cluster Stats
   curl -u elastic:Ela5Tic@#987 -X GET    "http://es.elk.local:9200/_cluster/stats?pretty"
   
   # Shutdown Elasticsearch Node
   curl -u elastic:Ela5Tic@#987 -X POST "http://es.elk.local:9200/_shutdown"
   ```
## Configure Logstash
1. **Create `/etc/logstash/conf.d/logstash.conf`**:

    Create a certs dir `/etc/logstash/certs` and copy the ca_elk.local.crt from elasticsearch to logstash's certs dir.
   ```yml
   input {
     beats {
       port => 5044
     }
   }
   output {
     elasticsearch {
       hosts => ["https://es.elk.local:9200"]
       cacert => "/etc/logstash/certs/ca_elk.local.crt"
       user => "elastic"
       password: "<elastic_password>"
     }
   }
   ```
2. **Start Logstash**:
   ```bash
   # config check  
   /usr/share/logstash/bin/logstash test \
    config -c /etc/logstash/logstash.yml \
    --path.home /usr/share/logstash \
    --path.data /var/lib/logstash
    
   systemctl enable logstash
   systemctl start logstash
   ```

## Configure Filebeat
1. **Edit `/etc/filebeat/filebeat.yml`**:

    Create a certs dir `/etc/filebeat/certs` and copy the ca_elk.local.crt from elasticsearch to filebeat's certs dir.
   ```yaml
   filebeat.inputs:
   - type: log
     enabled: true
     paths:
       - /var/log/*.log
   output.elasticsearch:
     hosts: ["https://es.elk.local:9200"]
     username: "elastic"
     password: "<elastic_password>"
     ssl.certificate_authorities: ["/etc/filebeat/certs/ca_elk.local.crt"]
   ```
2. **Start Filebeat**:
   ```bash
   # config check  
   /usr/share/filebeat/bin/filebeat test \
    config -c /etc/filebeat/filebeat.yml \
    --path.home /usr/share/filebeat \
    --path.data /var/lib/filebeat
    
   systemctl enable filebeat
   systemctl start filebeat
   ```

## Configure Metricbeat
1. **Edit `/etc/metricbeat/metricbeat.yml`**:
   
    Create a certs dir `/etc/filebeat/certs` and copy the ca_elk.local.crt from elasticsearch to metricbeat's certs dir.
    ```yaml
   metricbeat.modules:
   - module: system
     metricsets: ["cpu", "memory", "network", "diskio"]
     enabled: true
   output.elasticsearch:
     hosts: ["https://es.elk.local:9200"]
     username: "elastic"
     password: "<elastic_password>"
     ssl.certificate_authorities: ["/etc/metricbeat/certs/ca_elk.local.crt"]
   ```
  ### Memory limits
  ```bash
  mkdir -p /etc/systemd/system/metricbeat.service.d
  cat << EOF > /etc/systemd/system/metricbeat.service.d/override.conf
  [Service]
  MemoryMax=512M
  EOF
  ```

   
2. **Start Metricbeat**:
   ```bash
   systemctl daemon-reexec
   systemctl enable metricbeat
   systemctl start metricbeat
   systemctl restart metricbeat
   systemctl show metricbeat --property=MemoryMax
   ps -o pid,rss,vsz,cmd -p $(pgrep metricbeat)
   ```

## Configure Heartbeat
1. **Edit `/etc/heartbeat/heartbeat.yml`**:

    Create a certs dir `/etc/filebeat/certs` and copy the `ca_elk.local.crt` from elasticsearch to heartbeat's certs dir.
    ```yaml
   heartbeat.monitors:
   - type: http
     urls: ["https://es.elk.local:9200"]
     schedule: '@every 10s'
   output.elasticsearch:
     hosts: ["https://es.elk.local:9200"]
     username: "elastic"
     password: "<elastic_password>"
     ssl.certificate_authorities: ["/etc/heartbeat/certs/ca_elk.local.crt"]
   ```
2. **Start Heartbeat**:
   ```bash
   # Check config
   /usr/share/heartbeat/bin/heartbeat test \
    config -c /etc/heartbeat/heartbeat.yml \
    --path.home /usr/share/heartbeat \
    --path.data /var/lib/heartbeat
    
   systemctl enable heartbeat
   systemctl start heartbeat
   ```

## Verification
- **Kibana**: Access `https://kibana.elk.local:5601`
- **Elasticsearch**: `curl --cacert /etc/elasticsearch/certs/ca_elk.local.crt -u elastic https://es.elk.local:9200`
- **Logs**: Check Kibana’s Discover tab.

## References
- Elastic Documentation: https://www.elastic.co/guide/en/elasticsearch/reference/8.17/index.html
- ElastiFlow Docs: https://docs.elastiflow.com
- GoLinuxCloud: https://www.golinuxcloud.com
