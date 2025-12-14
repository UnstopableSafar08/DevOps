Guide to optimized `server.xml` configurations for both scenarios with detailed comments.

## Configuration 1: 4 Core CPU + 8GB RAM (High Performance)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Server port="8005" shutdown="SHUTDOWN">
    
    <!-- Essential Listeners -->
    <Listener className="org.apache.catalina.startup.VersionLoggerListener" />
    <Listener className="org.apache.catalina.core.AprLifecycleListener" SSLEngine="on" />
    <!-- Can be disabled if not experiencing memory leaks -->
    <!-- <Listener className="org.apache.catalina.core.JreMemoryLeakPreventionListener" /> -->
    <Listener className="org.apache.catalina.mbeans.GlobalResourcesLifecycleListener" />
    <Listener className="org.apache.catalina.core.ThreadLocalLeakPreventionListener" />
    
    <GlobalNamingResources>
        <Resource name="UserDatabase" 
                  auth="Container" 
                  type="org.apache.catalina.UserDatabase" 
                  description="User database that can be updated and saved" 
                  factory="org.apache.catalina.users.MemoryUserDatabaseFactory" 
                  pathname="conf/tomcat-users.xml" />
    </GlobalNamingResources>
    
    <Service name="Catalina">
        
        <!-- Thread Pool Executor for better thread management -->
        <Executor name="tomcatThreadPool" 
                  namePrefix="catalina-exec-"
                  maxThreads="200"
                  minSpareThreads="50"
                  maxIdleTime="60000"
                  prestartminSpareThreads="true"
                  maxQueueSize="100"/>
        
        <!-- HTTP/1.1 Connector optimized for 4 cores, 8GB RAM -->
        <Connector executor="tomcatThreadPool"
                   port="8080" 
                   protocol="org.apache.coyote.http11.Http11NioProtocol"
                   connectionTimeout="20000"
                   maxConnections="1000"
                   acceptCount="100"
                   keepAliveTimeout="60000"
                   maxKeepAliveRequests="100"
                   
                   <!-- Compression for bandwidth optimization -->
                   compression="on"
                   compressionMinSize="2048"
                   compressibleMimeType="text/html,text/xml,text/plain,text/css,text/javascript,application/javascript,application/json,application/xml"
                   
                   <!-- Performance tuning -->
                   enableLookups="false"
                   disableUploadTimeout="true"
                   URIEncoding="UTF-8"
                   useBodyEncodingForURI="true"
                   
                   <!-- Security -->
                   maxParameterCount="1000"
                   maxPostSize="2097152"
                   maxHttpHeaderSize="8192"
                   
                   redirectPort="8443" />
        
        <!-- AJP Connector (comment out if not using Apache/Nginx with AJP) -->
        <!-- 
        <Connector port="8009" 
                   protocol="AJP/1.3" 
                   redirectPort="8443"
                   maxThreads="100"
                   minSpareThreads="10"
                   enableLookups="false"
                   connectionTimeout="20000" />
        -->
        
        <Engine name="Catalina" defaultHost="localhost">
            
            <Realm className="org.apache.catalina.realm.LockOutRealm">
                <Realm className="org.apache.catalina.realm.UserDatabaseRealm" 
                       resourceName="UserDatabase"/>
            </Realm>
            
            <Host name="localhost" 
                  appBase="webapps"
                  unpackWARs="true" 
                  autoDeploy="true"
                  deployOnStartup="true">
                
                <!-- Access Log with extended pattern -->
                <Valve className="org.apache.catalina.valves.AccessLogValve" 
                       directory="logs"
                       prefix="localhost_access_log" 
                       suffix=".txt"
                       pattern="%h %l %u %t &quot;%r&quot; %s %b %D %{User-Agent}i"
                       rotatable="true"
                       maxDays="30" />
                
                <!-- Error Report Valve (optional - shows less info to users) -->
                <Valve className="org.apache.catalina.valves.ErrorReportValve"
                       showReport="false"
                       showServerInfo="false" />
                
            </Host>
        </Engine>
    </Service>
</Server>
```

---

## Configuration 2: 2 Core CPU + 4GB RAM (Resource Constrained)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Server port="8005" shutdown="SHUTDOWN">
    
    <!-- Essential Listeners -->
    <Listener className="org.apache.catalina.startup.VersionLoggerListener" />
    <Listener className="org.apache.catalina.core.AprLifecycleListener" SSLEngine="on" />
    <!-- Disabled to save memory -->
    <!-- <Listener className="org.apache.catalina.core.JreMemoryLeakPreventionListener" /> -->
    <Listener className="org.apache.catalina.mbeans.GlobalResourcesLifecycleListener" />
    <Listener className="org.apache.catalina.core.ThreadLocalLeakPreventionListener" />
    
    <GlobalNamingResources>
        <Resource name="UserDatabase" 
                  auth="Container" 
                  type="org.apache.catalina.UserDatabase" 
                  description="User database that can be updated and saved" 
                  factory="org.apache.catalina.users.MemoryUserDatabaseFactory" 
                  pathname="conf/tomcat-users.xml" />
    </GlobalNamingResources>
    
    <Service name="Catalina">
        
        <!-- Thread Pool Executor optimized for 2 cores -->
        <Executor name="tomcatThreadPool" 
                  namePrefix="catalina-exec-"
                  maxThreads="100"
                  minSpareThreads="25"
                  maxIdleTime="60000"
                  prestartminSpareThreads="true"
                  maxQueueSize="50"/>
        
        <!-- HTTP/1.1 Connector optimized for 2 cores, 4GB RAM -->
        <Connector executor="tomcatThreadPool"
                   port="8080" 
                   protocol="org.apache.coyote.http11.Http11NioProtocol"
                   connectionTimeout="20000"
                   maxConnections="250"
                   acceptCount="50"
                   keepAliveTimeout="30000"
                   maxKeepAliveRequests="50"
                   
                   <!-- Compression for bandwidth optimization -->
                   compression="on"
                   compressionMinSize="2048"
                   compressibleMimeType="text/html,text/xml,text/plain,text/css,text/javascript,application/javascript,application/json"
                   
                   <!-- Performance tuning -->
                   enableLookups="false"
                   disableUploadTimeout="true"
                   URIEncoding="UTF-8"
                   useBodyEncodingForURI="true"
                   
                   <!-- Security - reduced limits for smaller server -->
                   maxParameterCount="1000"
                   maxPostSize="1048576"
                   maxHttpHeaderSize="8192"
                   
                   redirectPort="8443" />
        
        <!-- AJP Connector (disabled to save resources) -->
        <!-- 
        <Connector port="8009" 
                   protocol="AJP/1.3" 
                   redirectPort="8443"
                   maxThreads="50"
                   minSpareThreads="5"
                   enableLookups="false"
                   connectionTimeout="20000" />
        -->
        
        <Engine name="Catalina" defaultHost="localhost">
            
            <Realm className="org.apache.catalina.realm.LockOutRealm">
                <Realm className="org.apache.catalina.realm.UserDatabaseRealm" 
                       resourceName="UserDatabase"/>
            </Realm>
            
            <Host name="localhost" 
                  appBase="webapps"
                  unpackWARs="true" 
                  autoDeploy="true"
                  deployOnStartup="true">
                
                <!-- Access Log with basic pattern -->
                <Valve className="org.apache.catalina.valves.AccessLogValve" 
                       directory="logs"
                       prefix="localhost_access_log" 
                       suffix=".txt"
                       pattern="%h %l %u %t &quot;%r&quot; %s %b"
                       rotatable="true"
                       maxDays="15" />
                
                <!-- Error Report Valve -->
                <Valve className="org.apache.catalina.valves.ErrorReportValve"
                       showReport="false"
                       showServerInfo="false" />
                
            </Host>
        </Engine>
    </Service>
</Server>
```

---

## Key Differences Explained

| Setting | 4 Core / 8GB | 2 Core / 4GB | Reasoning |
|---------|--------------|--------------|-----------|
| **maxThreads** | 200 | 100 | ~50 threads per core |
| **minSpareThreads** | 50 | 25 | More ready threads for high load |
| **maxConnections** | 1000 | 250 | Higher connection capacity |
| **acceptCount** | 100 | 50 | Queue size for waiting connections |
| **keepAliveTimeout** | 60000ms | 30000ms | Reduced to free connections faster |
| **maxKeepAliveRequests** | 100 | 50 | Lower persistent connection count |
| **maxPostSize** | 2MB | 1MB | Smaller upload size limit |
| **maxQueueSize** | 100 | 50 | Executor queue size |

---

## Corresponding JVM Settings

### For 4 Core / 8GB - setenv.sh:
```bash
#!/bin/bash

export CATALINA_OPTS="$CATALINA_OPTS -Xms2048m -Xmx4096m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ConcGCThreads=2"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseStringDeduplication"
export CATALINA_OPTS="$CATALINA_OPTS -server"
export CATALINA_OPTS="$CATALINA_OPTS -Djava.net.preferIPv4Stack=true"
```

### For 2 Core / 4GB - setenv.sh:
```bash
#!/bin/bash

export CATALINA_OPTS="$CATALINA_OPTS -Xms1024m -Xmx2048m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=128m -XX:MaxMetaspaceSize=256m"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=2"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ConcGCThreads=1"
export CATALINA_OPTS="$CATALINA_OPTS -server"
export CATALINA_OPTS="$CATALINA_OPTS -Djava.net.preferIPv4Stack=true"
```

---

## Additional Optimizations

### 1. Remove AJP Connector (if not using)
If you're not using Apache httpd or Nginx with AJP protocol in front of Tomcat, **comment out or remove** the AJP connector to save resources:

```xml
<!-- REMOVE THIS if not using Apache/Nginx with AJP -->
<!-- <Connector port="8009" protocol="AJP/1.3" redirectPort="8443" /> -->
```

### 2. Disable autoDeploy in Production
For production servers, disable automatic deployment:

```xml
<Host name="localhost" 
      appBase="webapps"
      unpackWARs="true" 
      autoDeploy="false"
      deployOnStartup="true">
```

### 3. Add Remote IP Valve (if behind load balancer)
If using a load balancer or reverse proxy:

```xml
<Valve className="org.apache.catalina.valves.RemoteIpValve"
       remoteIpHeader="X-Forwarded-For"
       proxiesHeader="X-Forwarded-By"
       protocolHeader="X-Forwarded-Proto" />
```

### 4. Session Timeout (context.xml)
Adjust session timeout to free memory faster:

```xml
<Context>
    <Manager pathname="" />
    <!-- Session timeout in minutes -->
    <session-timeout>30</session-timeout>
</Context>
```

---

## Testing Your Configuration

### 1. Validate XML syntax:
```bash
xmllint --noout /path/to/server.xml
```

### 2. Test startup:
```bash
cd $CATALINA_HOME/bin
./catalina.sh run
```

### 3. Verify settings:
```bash
# Check thread count
ps -eLf | grep java | wc -l

# Check memory
jmap -heap <tomcat_pid>

# Check connections (Linux)
netstat -an | grep 8080 | wc -l
```

### 4. Load test:
```bash
# Apache Bench - 4 Core system
ab -n 10000 -c 100 http://localhost:8080/

# Apache Bench - 2 Core system
ab -n 5000 -c 50 http://localhost:8080/
```

---

## Monitoring Checklist

After applying changes, monitor:

✅ **CPU Usage**: Should stay < 80% under load  
✅ **Memory Usage**: JVM heap should stay < 80% of -Xmx  
✅ **Thread Count**: Should not exceed maxThreads  
✅ **Connection Count**: Should not exceed maxConnections  
✅ **GC Frequency**: Major GC should be < 1/minute  
✅ **Response Time**: Should stay < 500ms for most requests  

---

## Quick Comparison Table

| Metric | 4 Core/8GB | 2 Core/4GB |
|--------|------------|------------|
| Concurrent Users | ~800-1000 | ~200-250 |
| Requests/sec | 500-800 | 150-300 |
| Heap Memory | 4GB | 2GB |
| Worker Threads | 200 | 100 |
| Max Connections | 1000 | 250 |
| Keep-Alive Time | 60s | 30s |

