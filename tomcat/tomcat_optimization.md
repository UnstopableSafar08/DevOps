# Optimize Tomcat for your 4-core, ~8GB RAM system. Here's a practical optimization guide:

## 1. JVM Memory Settings

Create or edit `setenv.sh` (Linux/Mac) or `setenv.bat` (Windows) in `TOMCAT_HOME/bin/`:

**For Linux/Mac (setenv.sh):**
```bash
export CATALINA_OPTS="$CATALINA_OPTS -Xms2048m"
export CATALINA_OPTS="$CATALINA_OPTS -Xmx4096m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=256m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxMetaspaceSize=512m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ConcGCThreads=2"
export CATALINA_OPTS="$CATALINA_OPTS -server"
```

**For Windows (setenv.bat):**
```batch
set CATALINA_OPTS=%CATALINA_OPTS% -Xms2048m -Xmx4096m
set CATALINA_OPTS=%CATALINA_OPTS% -XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m
set CATALINA_OPTS=%CATALINA_OPTS% -XX:+UseG1GC
set CATALINA_OPTS=%CATALINA_OPTS% -XX:MaxGCPauseMillis=200
set CATALINA_OPTS=%CATALINA_OPTS% -server
```

**Why these values?**
- **-Xms2048m**: Initial heap size (2GB)
- **-Xmx4096m**: Maximum heap size (4GB) - leaves ~3.5GB for OS and other processes
- **MetaspaceSize**: For class metadata (Java 8+)
- **G1GC**: Best garbage collector for your heap size

## 2. Connector Optimization (server.xml)

Edit `TOMCAT_HOME/conf/server.xml`:

```xml
<Connector port="8080" protocol="org.apache.coyote.http11.Http11NioProtocol"
           maxThreads="200"
           minSpareThreads="25"
           maxConnections="500"
           acceptCount="100"
           connectionTimeout="20000"
           keepAliveTimeout="60000"
           maxKeepAliveRequests="100"
           compression="on"
           compressionMinSize="2048"
           compressibleMimeType="text/html,text/xml,text/plain,text/css,text/javascript,application/javascript,application/json"
           URIEncoding="UTF-8"
           enableLookups="false"
           redirectPort="8443"/>
```

**Key parameters explained:**
- **maxThreads="200"**: Maximum worker threads (50 per core is a good rule of thumb)
- **maxConnections="500"**: Max simultaneous connections
- **acceptCount="100"**: Queue size when all threads are busy
- **compression="on"**: Compress text responses to reduce bandwidth

## 3. Thread Pool Configuration (Optional but Recommended)

Add this **before** the Connector in `server.xml`:

```xml
<Executor name="tomcatThreadPool" 
          namePrefix="catalina-exec-"
          maxThreads="200" 
          minSpareThreads="25"
          maxIdleTime="60000"
          prestartminSpareThreads="true"/>
```

Then modify your Connector to use it:
```xml
<Connector executor="tomcatThreadPool"
           port="8080" 
           protocol="HTTP/1.1"
           connectionTimeout="20000"
           .../>
```

## 4. Additional Performance Tuning

### Disable session persistence (if not needed)
Edit `TOMCAT_HOME/conf/context.xml`:
```xml
<Context>
    <!-- Disable session persistence across restarts -->
    <Manager pathname="" />
</Context>
```

### Enable parallel deployment (Tomcat 7+)
In `TOMCAT_HOME/conf/server.xml`, add to the Host element:
```xml
<Host name="localhost" appBase="webapps"
      unpackWARs="true" autoDeploy="true"
      deployOnStartup="true" 
      parallelDeployment="true">
```

## 5. OS-Level Optimization

### Linux File Descriptors
Add to `/etc/security/limits.conf`:
```
tomcat soft nofile 65536
tomcat hard nofile 65536
tomcat soft nproc 4096
tomcat hard nproc 4096
```

### Verify limits:
```bash
ulimit -n  # file descriptors
ulimit -u  # processes
```

## 6. Monitoring Your Configuration

After applying changes, verify:

```bash
# Check Tomcat process memory
ps aux | grep tomcat

# View JVM settings
jinfo <tomcat_pid>

# Monitor garbage collection
jstat -gcutil <tomcat_pid> 1000

# Check thread count
jstack <tomcat_pid> | grep "java.lang.Thread.State" | wc -l
```

## 7. Quick Reference Table

| Resource | Setting | Value | Reason |
|----------|---------|-------|--------|
| Heap Min | -Xms | 2048m | Avoid resizing overhead |
| Heap Max | -Xmx | 4096m | ~50% of total RAM |
| Metaspace | -XX:MaxMetaspaceSize | 512m | Class metadata |
| GC | -XX:+UseG1GC | enabled | Best for 2GB+ heaps |
| Threads | maxThreads | 200 | 50 × CPU cores |
| Connections | maxConnections | 500 | Buffer for spikes |

## 8. Startup Script Example

Complete `setenv.sh` for production:

```bash
#!/bin/bash

# Memory settings
export CATALINA_OPTS="$CATALINA_OPTS -Xms2048m -Xmx4096m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m"

# Garbage Collection
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ConcGCThreads=2"

# Performance tuning
export CATALINA_OPTS="$CATALINA_OPTS -server"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseStringDeduplication"
export CATALINA_OPTS="$CATALINA_OPTS -Djava.net.preferIPv4Stack=true"

# GC Logging (adjust path as needed)
export CATALINA_OPTS="$CATALINA_OPTS -Xlog:gc*:file=/var/log/tomcat/gc.log:time,uptime:filecount=5,filesize=10M"

# Encoding
export CATALINA_OPTS="$CATALINA_OPTS -Dfile.encoding=UTF-8"
```

Make it executable:
```bash
chmod +x $TOMCAT_HOME/bin/setenv.sh
```

## 9. Testing Your Configuration

1. **Restart Tomcat:**
   ```bash
   ./shutdown.sh && ./startup.sh
   ```

2. **Verify JVM is using your settings:**
   ```bash
   ps aux | grep java | grep Xmx
   ```

3. **Load test** (using Apache Bench):
   ```bash
   ab -n 1000 -c 50 http://localhost:8080/
   ```

## Common Adjustments Based on Usage

**High traffic websites:**
- Increase `maxThreads` to 300-400
- Increase `maxConnections` to 1000

**Memory-intensive applications:**
- Increase `-Xmx` to 5120m (5GB)
- Reduce `maxThreads` to 150

**API servers:**
- Reduce `keepAliveTimeout` to 15000
- Increase `maxThreads` to 300

