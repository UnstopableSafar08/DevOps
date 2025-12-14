# Tomcat Configuration Metrics - Quick Reference

## Server & Listeners

| Setting | Purpose | Recommendation |
|---------|---------|----------------|
| **`port="8005"`** | Shutdown command port | Production: `-1` or custom port |
| **VersionLoggerListener** | Logs version info at startup | Keep enabled |
| **AprLifecycleListener** | Enables APR native library for better SSL/performance | Keep if APR installed |
| **JreMemoryLeakPreventionListener** | Prevents JVM memory leaks | Keep on 8GB+, optional on 4GB |
| **GlobalResourcesLifecycleListener** | Required for JNDI resources (DB pools) | Always keep |
| **ThreadLocalLeakPreventionListener** | Prevents ThreadLocal memory leaks | Always keep |

---

## Executor (Thread Pool)

| Parameter | Description | Formula | 4C/8GB | 2C/4GB |
|-----------|-------------|---------|--------|--------|
| **maxThreads** | Max concurrent request threads | 50 × CPU cores | 200 | 100 |
| **minSpareThreads** | Always-alive idle threads | 25% of maxThreads | 50 | 25 |
| **maxIdleTime** | Kill idle threads after (ms) | - | 60000 | 60000 |
| **prestartminSpareThreads** | Create spare threads at startup | Production: true | true | true |
| **maxQueueSize** | Request queue when all threads busy | 0.5-1 × maxThreads | 100 | 50 |

**Key Points:**
- Each thread uses ~1MB RAM
- CPU-bound apps: 25-50 × cores | I/O-bound: 50-100 × cores
- Too many threads = context switching overhead
- Too few threads = slow response times

---

## Connector (HTTP/HTTPS)

### Essential Settings

| Parameter | Description | 4C/8GB | 2C/4GB |
|-----------|-------------|--------|--------|
| **port** | HTTP port | 8080 | 8080 |
| **protocol** | Connector type | Http11NioProtocol (recommended) | Http11NioProtocol |
| **maxThreads** | From Executor or inline | 200 | 100 |
| **maxConnections** | Total TCP connections | 1000 | 250 |
| **acceptCount** | Queue when maxConnections reached | 100 | 50 |
| **connectionTimeout** | Wait for request (ms) | 20000 | 20000 |
| **keepAliveTimeout** | Keep connection open (ms) | 60000 | 30000 |
| **maxKeepAliveRequests** | Requests per persistent connection | 100 | 50 |

### Protocol Options
- **Http11NioProtocol** - Non-blocking I/O (best for most cases)
- **Http11Nio2Protocol** - NIO2 with async (for Servlet 3.1+)
- **Http11AprProtocol** - Native library (fastest, requires APR)

### Compression Settings

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **compression** | `on` | Enable gzip (saves 70-85% bandwidth) |
| **compressionMinSize** | `2048` | Compress responses >2KB |
| **compressibleMimeType** | `text/html,text/css,text/javascript,application/json` | Text content only |

**Compression Savings:**
- HTML/CSS/JS: 70-85%
- JSON/XML: 60-75%
- Images: Don't compress (already compressed)

### Security & Performance

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **enableLookups** | `false` | Skip DNS lookups (saves 10-100ms/request) |
| **disableUploadTimeout** | `true` | Use standard timeout for uploads |
| **URIEncoding** | `UTF-8` | Handle international characters |
| **maxParameterCount** | `1000` | Prevent hash collision attacks |
| **maxPostSize** | `2097152` (2MB) | Limit POST body size |
| **maxHttpHeaderSize** | `8192` (8KB) | Limit header size |

**Tuning Tips:**
- **APIs**: maxPostSize=5MB, keepAliveTimeout=15s
- **File Uploads**: maxPostSize=100MB, connectionTimeout=120s
- **High Traffic**: maxConnections=1500, compression=on
- **Low RAM**: Reduce all max values by 50%

---

## Connection Formulas

```
maxConnections = maxThreads × 2-5 (with keep-alive)
acceptCount = 50-100 (traffic spikes buffer)
keepAliveTimeout = 60s (high RAM) or 15-30s (low RAM)
```

**NIO vs BIO:**
- NIO can handle 5-10× more connections than threads
- BIO limited to maxThreads connections

---

## Host & Deployment

| Parameter | Value | When |
|-----------|-------|------|
| **unpackWARs** | `true` | Better runtime performance |
| **autoDeploy** | `false` | Production (controlled deploys) |
| **autoDeploy** | `true` | Development (hot deploy) |
| **deployOnStartup** | `true` | Always (apps ready at startup) |

---

## Valves

### Access Log
```xml
<Valve className="org.apache.catalina.valves.AccessLogValve" 
       directory="logs"
       pattern="%h %l %u %t &quot;%r&quot; %s %b %D"
       maxDays="30" />
```

**Pattern Variables:**
- `%h` - Client IP
- `%t` - Timestamp
- `%r` - Request (GET /path HTTP/1.1)
- `%s` - Status code (200, 404, 500)
- `%b` - Bytes sent
- `%D` - Processing time (microseconds)
- `%{User-Agent}i` - User agent header

### Error Report
```xml
<Valve className="org.apache.catalina.valves.ErrorReportValve"
       showReport="false"
       showServerInfo="false" />
```
Production: Hide stack traces and version info

### Remote IP (Behind Load Balancer)
```xml
<Valve className="org.apache.catalina.valves.RemoteIpValve"
       remoteIpHeader="X-Forwarded-For"
       protocolHeader="X-Forwarded-Proto" />
```
Required when behind proxy/LB to get real client IP

---

## Quick Tuning Guide

### By Application Type

| Type | maxThreads | maxConnections | keepAlive | Notes |
|------|------------|----------------|-----------|-------|
| **Website** | 200-300 | 1000-1500 | 60s | Enable compression |
| **REST API** | 100-200 | 400-800 | 15-30s | Short keep-alive |
| **Microservice** | 50-100 | 200-400 | 30s | Light footprint |
| **File Upload** | 50 | 100 | 120s | High timeouts |
| **Low RAM (2GB)** | 50 | 100 | 15s | Minimize everything |

### By System Resources

| System | Heap (Xmx) | maxThreads | maxConnections | minSpareThreads |
|--------|-----------|------------|----------------|-----------------|
| **4C/8GB** | 4096m | 200 | 1000 | 50 |
| **2C/4GB** | 2048m | 100 | 250 | 25 |
| **1C/2GB** | 1024m | 50 | 100 | 10 |

---

## Memory Allocation

```
Total RAM: 8GB
├── JVM Heap: 4GB (50%)
├── Metaspace: 512MB (6%)
├── Thread Stacks: 200MB (200 threads × 1MB)
└── OS/Buffer: 3.3GB (41%)

Total RAM: 4GB
├── JVM Heap: 2GB (50%)
├── Metaspace: 256MB (6%)
├── Thread Stacks: 100MB (100 threads × 1MB)
└── OS/Buffer: 1.6GB (40%)
```

---

## Monitoring Commands

```bash
# Active threads
jstack <pid> | grep "catalina-exec" | wc -l

# Active connections
netstat -an | grep :8080 | grep ESTABLISHED | wc -l

# Memory usage
jmap -heap <pid>

# GC monitoring
jstat -gcutil <pid> 1000

# Check system limits
ulimit -n    # file descriptors (should be 65536+)
ulimit -u    # processes
```

---

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| "Connection refused" | maxConnections + acceptCount too low | Increase both or scale horizontally |
| High CPU | Too many threads or CPU-heavy code | Reduce threads, optimize code |
| OutOfMemory | Heap too small or memory leak | Increase -Xmx, fix leaks, reduce threads |
| Slow responses | Thread starvation or DB bottleneck | Increase threads, optimize DB |
| "Too many open files" | OS file descriptor limit | `ulimit -n 65536` |
| Threads exhausted | Blocking I/O or slow endpoints | Use async processing, increase threads |

---

## Critical Relationships

```
maxConnections > maxThreads    (connections can wait)
acceptCount = spike buffer     (50-100 typical)
maxThreads × 1MB = thread RAM
keepAliveTimeout ↑ = more connections held
compression ON = 70-85% less bandwidth, 2-5% more CPU
```

---

## AJP Connector (Remove if Not Used)

```xml
<!-- Only keep if using Apache/Nginx with mod_jk/mod_proxy_ajp -->
<Connector port="8009" protocol="AJP/1.3" redirectPort="8443" />
```

**Remove if:**
- Using HTTP proxy
- Direct Tomcat access
- Cloud environments
- Not using Apache httpd

**Keep if:**
- Using mod_jk or mod_proxy_ajp
- 10-15% better performance than HTTP proxy

---

## Production Checklist

✅ Set `autoDeploy="false"`  
✅ Set `showReport="false"` and `showServerInfo="false"`  
✅ Enable compression for text content  
✅ Set `enableLookups="false"`  
✅ Configure access logging with rotation  
✅ Remove AJP connector if unused  
✅ Use executor for thread pooling  
✅ Set appropriate `maxPostSize` limits  
✅ Configure `RemoteIpValve` if behind LB  
✅ Set `ulimit -n 65536`  
✅ Monitor GC logs and thread dumps  

---

## One-Line Formulas

```bash
maxThreads = 50 × CPU_cores
minSpareThreads = maxThreads × 0.25
maxConnections = maxThreads × 3 (with keep-alive)
JVM_Heap = Total_RAM × 0.5
acceptCount = 100 (standard)
keepAliveTimeout = 60000 (8GB) or 30000 (4GB)
```
