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



# Visualizing Tomcat Metrics in Grafana

## Step 1: Add Prometheus as Data Source

1. **Login to Grafana** (default: http://localhost:3000)
   - Default credentials: admin/admin

2. **Add Prometheus Data Source**
   - Click on the **☰** menu (hamburger menu) → **Connections** → **Data sources**
   - Click **"Add data source"**
   - Select **"Prometheus"**
   - Configure:
     - **Name**: Prometheus
     - **URL**: `http://localhost:9090` (or your Prometheus server URL)
     - Click **"Save & Test"** - you should see "Data source is working"

## Step 2: Import a Pre-built Tomcat Dashboard

The easiest way is to use a community dashboard:

1. **Go to Dashboards**
   - Click **☰** menu → **Dashboards**
   - Click **"New"** → **"Import"**

2. **Import Dashboard by ID**
   - Enter one of these dashboard IDs:
     - **11401** - Tomcat Dashboard (comprehensive)
     - **9731** - JVM (Micrometer)
     - **8563** - JMX Overview
   
3. **Configure Import**
   - Select your **Prometheus** data source
   - Click **"Import"**

## Step 3: Create a Custom Tomcat Dashboard

If you want to create your own dashboard:

1. **Create New Dashboard**
   - Click **☰** → **Dashboards** → **New Dashboard**
   - Click **"Add visualization"**
   - Select your **Prometheus** data source

2. **Add Key Panels** - Here are essential visualizations:

### Panel 1: Request Rate (Requests per second)

```promql
rate(tomcat_requestcount_total[5m])
```

- **Visualization**: Time series graph
- **Title**: "HTTP Requests per Second"
- **Unit**: reqps (requests per second)

### Panel 2: Error Rate

```promql
rate(tomcat_errorcount_total[5m])
```

- **Visualization**: Time series graph
- **Title**: "HTTP Errors per Second"
- **Unit**: errors/sec

### Panel 3: Thread Pool Usage

```promql
tomcat_threadpool_currentthreadsbusy
```

```promql
tomcat_threadpool_maxthreads
```

- **Visualization**: Time series graph
- **Title**: "Thread Pool - Busy vs Max"
- **Legend**: {{protocol}}-{{port}}

### Panel 4: Thread Pool Usage Percentage

```promql
(tomcat_threadpool_currentthreadsbusy / tomcat_threadpool_maxthreads) * 100
```

- **Visualization**: Gauge
- **Title**: "Thread Pool Usage %"
- **Unit**: percent (0-100)
- **Thresholds**: Green (0-70), Yellow (70-85), Red (85-100)

### Panel 5: JVM Heap Memory Usage

```promql
jvm_memory_heap_used_bytes
```

```promql
jvm_memory_heap_max_bytes
```

- **Visualization**: Time series graph
- **Title**: "JVM Heap Memory"
- **Unit**: bytes (IEC)

### Panel 6: JVM Heap Usage Percentage

```promql
(jvm_memory_heap_used_bytes / jvm_memory_heap_max_bytes) * 100
```

- **Visualization**: Gauge
- **Title**: "Heap Memory Usage %"
- **Unit**: percent (0-100)
- **Thresholds**: Green (0-75), Yellow (75-90), Red (90-100)

### Panel 7: Garbage Collection Rate

```promql
rate(jvm_gc_collection_count_total[5m])
```

- **Visualization**: Time series graph
- **Title**: "GC Collections per Second"
- **Legend**: {{gc}}

### Panel 8: GC Time

```promql
rate(jvm_gc_collection_time_ms_total[5m])
```

- **Visualization**: Time series graph
- **Title**: "GC Time (ms/sec)"
- **Legend**: {{gc}}

### Panel 9: Active Sessions

```promql
tomcat_sessions_active_current_sessions
```

- **Visualization**: Stat
- **Title**: "Active Sessions"

### Panel 10: Response Time (if available)

```promql
rate(tomcat_processingtime_total[5m]) / rate(tomcat_requestcount_total[5m])
```

- **Visualization**: Time series graph
- **Title**: "Average Response Time (ms)"
- **Unit**: milliseconds

## Step 4: Dashboard Layout Example

Create a dashboard with this structure:

```
Row 1: Overview
+------------------+------------------+------------------+
| Requests/sec     | Errors/sec       | Active Sessions  |
| (Time series)    | (Time series)    | (Stat)          |
+------------------+------------------+------------------+

Row 2: Thread Pool
+------------------+------------------+
| Thread Pool Usage (Time series)    |
+------------------+------------------+
| Thread Pool % (Gauge)              |
+------------------------------------+

Row 3: Memory
+------------------+------------------+
| Heap Memory (Time series)          |
+------------------+------------------+
| Heap Usage % (Gauge)               |
+------------------------------------+

Row 4: Garbage Collection
+------------------+------------------+
| GC Rate          | GC Time          |
| (Time series)    | (Time series)    |
+------------------+------------------+
```

## Step 5: Configure Dashboard Settings

1. **Set Time Range**
   - Top right corner → Select "Last 1 hour" or "Last 6 hours"
   - Enable auto-refresh: 30s or 1m

2. **Add Variables (Optional)**
   - Dashboard settings (gear icon) → **Variables** → **Add variable**
   - **Name**: `instance`
   - **Type**: Query
   - **Query**: `label_values(tomcat_requestcount_total, instance)`
   - Use in queries: `{instance="$instance"}`

3. **Save Dashboard**
   - Click **Save** icon (top right)
   - Give it a name: "Tomcat Monitoring"
   - Add tags: tomcat, jmx, monitoring

## Step 6: Set Up Alerts (Optional)

Create alerts for critical metrics:

### Alert 1: High Thread Pool Usage

1. Edit the "Thread Pool Usage %" panel
2. Click **Alert** tab
3. Create alert rule:
   - **Condition**: `WHEN max() OF query(A, 5m, now) IS ABOVE 85`
   - **Alert name**: High Thread Pool Usage
   - **For**: 5m
   - **Annotations**: Thread pool usage is above 85% for 5 minutes

### Alert 2: High Heap Memory Usage

1. Edit the "Heap Memory Usage %" panel
2. Create alert:
   - **Condition**: `WHEN max() OF query(A, 5m, now) IS ABOVE 90`
   - **Alert name**: High Heap Memory Usage
   - **For**: 5m

### Alert 3: High Error Rate

1. Create alert for errors:
   - **Condition**: `WHEN avg() OF query(rate(tomcat_errorcount_total[5m])) IS ABOVE 10`
   - **Alert name**: High Error Rate
   - **For**: 2m

## Quick Import Dashboard JSON

Alternatively, here's a complete dashboard JSON you can import:

1. Go to **Dashboards** → **New** → **Import**
2. Click **"Upload JSON file"** or paste JSON
3. Select Prometheus data source
4. Click **Import**

You can save this as a file and import it directly into Grafana for a ready-to-use Tomcat monitoring dashboard.

## Verification

After setup, you should see:
- ✅ Real-time request rates and errors
- ✅ Thread pool utilization
- ✅ JVM memory usage
- ✅ Garbage collection activity
- ✅ Active sessions
