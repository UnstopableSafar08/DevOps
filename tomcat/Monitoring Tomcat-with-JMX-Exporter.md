# Monitoring Tomcat with JMX Exporter

I'll guide you through setting up JMX monitoring for Tomcat using Prometheus JMX Exporter.

## Step 1: Download JMX Exporter

Download the JMX Exporter JAR file:

```bash
cd /home/user1/tomcat/lib
wget https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/1.0.1/jmx_prometheus_javaagent-1.0.1.jar
```

## Step 2: Create JMX Configuration File

Create a configuration file for the JMX exporter:

```bash
nano /home/user1/tomcat/conf/jmx_exporter_config.yaml
```

Add this configuration:

```yaml
---
startDelaySeconds: 0
ssl: false
lowercaseOutputName: false
lowercaseOutputLabelNames: false
includeObjectNames:
  - "Catalina:type=GlobalRequestProcessor,*"
  - "Catalina:type=ThreadPool,*"
  - "java.lang:type=Memory"
  - "java.lang:type=MemoryPool,*"
  - "java.lang:type=GarbageCollector,*"
  - "java.lang:type=Threading"
  - "java.lang:type=OperatingSystem"
  - "java.lang:type=Runtime"
  - "Catalina:type=Manager,*"
  - "Catalina:type=Connector,*"
  - "Catalina:type=DataSource,*"

rules:
  # Tomcat specific metrics
  - pattern: 'Catalina<type=GlobalRequestProcessor, name=\"(\w+-\w+)-(\d+)\"><>(\w+):'
    name: tomcat_$3_total
    labels:
      port: "$2"
      protocol: "$1"
    help: Tomcat global $3
    type: COUNTER
  
  - pattern: 'Catalina<type=ThreadPool, name="(\w+-\w+)-(\d+)"><>(currentThreadCount|currentThreadsBusy|keepAliveCount|connectionCount|acceptCount|maxThreads):'
    name: tomcat_threadpool_$3
    labels:
      port: "$2"
      protocol: "$1"
    help: Tomcat threadpool $3
    type: GAUGE
  
  # Memory metrics
  - pattern: 'java.lang<type=Memory><HeapMemoryUsage>(\w+):'
    name: jvm_memory_heap_$1_bytes
    type: GAUGE
  
  - pattern: 'java.lang<type=Memory><NonHeapMemoryUsage>(\w+):'
    name: jvm_memory_nonheap_$1_bytes
    type: GAUGE
  
  # GC metrics
  - pattern: 'java.lang<type=GarbageCollector, name=(\w+)><>CollectionCount:'
    name: jvm_gc_collection_count_total
    labels:
      gc: "$1"
    type: COUNTER
  
  - pattern: 'java.lang<type=GarbageCollector, name=(\w+)><>CollectionTime:'
    name: jvm_gc_collection_time_ms_total
    labels:
      gc: "$1"
    type: COUNTER
```

## Step 3: Configure Tomcat to Use JMX Exporter

Edit the Tomcat startup script:

```bash
nano /home/user1/tomcat/bin/setenv.sh
```

Add the following content:

```bash
#!/bin/bash

# JMX Exporter configuration
CATALINA_OPTS="$CATALINA_OPTS -javaagent:/home/user1/tomcat/lib/jmx_prometheus_javaagent-1.0.1.jar=9104:/home/user1/tomcat/conf/jmx_exporter_config.yaml"

# Optional: Additional JVM settings for monitoring
CATALINA_OPTS="$CATALINA_OPTS -Dcom.sun.management.jmxremote"
CATALINA_OPTS="$CATALINA_OPTS -Dcom.sun.management.jmxremote.ssl=false"
CATALINA_OPTS="$CATALINA_OPTS -Dcom.sun.management.jmxremote.authenticate=false"

export CATALINA_OPTS
```

Make the script executable:

```bash
chmod +x /home/user1/tomcat/bin/setenv.sh
chown user1:user1 /home/user1/tomcat/bin/setenv.sh
```

## Step 4: Set Proper Permissions

Ensure all files have correct ownership:

```bash
chown user1:user1 /home/user1/tomcat/lib/jmx_prometheus_javaagent-1.0.1.jar
chown user1:user1 /home/user1/tomcat/conf/jmx_exporter_config.yaml
```

## Step 5: Restart Tomcat

```bash
# Stop Tomcat
sudo -u user1 /home/user1/tomcat/bin/shutdown.sh

# Start Tomcat
sudo -u user1 /home/user1/tomcat/bin/startup.sh
```

## Step 6: Verify JMX Exporter is Working

Check if the metrics endpoint is accessible:

```bash
curl http://localhost:9104/metrics
```

You should see Prometheus-formatted metrics output.

## Step 7: Configure Prometheus (for later)

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'tomcat'
    static_configs:
      - targets: ['localhost:9104']
        labels:
          instance: 'tomcat-server'
```

## Key Metrics to Monitor

The configuration will export these important metrics:

- **Request metrics**: `tomcat_requestcount_total`, `tomcat_errorcount_total`
- **Thread pool**: `tomcat_threadpool_currentthreadsbusy`, `tomcat_threadpool_maxthreads`
- **Memory**: `jvm_memory_heap_*`, `jvm_memory_nonheap_*`
- **GC**: `jvm_gc_collection_count_total`, `jvm_gc_collection_time_ms_total`
- **Sessions**: Session count and activity

## Troubleshooting

**If port 9104 is already in use:**
```bash
netstat -tulpn | grep 9104
```

**Check Tomcat logs:**
```bash
tail -f /home/user1/tomcat/logs/catalina.out
```

**Verify JMX agent loaded:**
Look for this line in catalina.out when Tomcat starts:
```
INFO: JMX exporter started at port 9104
```

That's it! Your Tomcat instance is now ready to be monitored via Prometheus and visualized in Grafana.
