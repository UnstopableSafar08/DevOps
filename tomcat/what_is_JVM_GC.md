## What is JVM? (Java Virtual Machine)

Think of JVM as a **translator and manager** for Java programs.

**Simple analogy:**
- You write a letter in English
- Your friend only reads Spanish
- You need a translator in the middle
- **JVM is that translator** - it translates Java code into language your computer understands

**What JVM does:**
1. Runs your Java application
2. Manages memory (RAM) for your application
3. Makes sure your app works on Windows, Linux, Mac (same code, different computers)

---

## What is GC? (Garbage Collector)

Think of GC as an **automatic janitor** for your computer's memory.

**Real-world analogy:**

Imagine you're cooking in a kitchen:
- You use plates, bowls, utensils
- After you're done eating, you have dirty dishes
- Someone needs to **clean up and wash the dishes**
- Otherwise, you'll run out of clean plates!

**In computer terms:**
- Your app creates data (objects) in memory
- After using them, they become "garbage" (not needed anymore)
- **GC automatically finds and removes this garbage**
- This frees up memory for new data

---

## Why Do We Need GC?

### **Without GC (Old way - like C/C++):**
```
Programmer's job:
1. Create data → use memory
2. Use the data
3. MANUALLY delete data → free memory
4. If you forget step 3 → MEMORY LEAK (disaster!)
```

**Problem:** If programmers forget to clean up, the application eats all memory and **crashes**.

### **With GC (Java way):**
```
Programmer's job:
1. Create data → use memory
2. Use the data
3. Done! GC automatically cleans up

No memory leaks (mostly)!
```

---

## Why Does GC Matter for Your Problem?

Remember your error:
```
"Not enough space" - Native memory allocation failed
```

**What happened:**
1. Your app kept creating objects (data)
2. Memory filled up
3. GC tried to clean up, but there were limits
4. Eventually ran out of memory → **CRASH**

**The fix:**
- Tell JVM: "You can use THIS MUCH memory and NO MORE"
- `-Xmx6G` means: "Maximum 6GB for application data"
- GC will clean up within this limit
- Won't eat all 16GB and crash the server

---

## Simple Summary

| **What** | **Simple Explanation** | **Why You Care** |
|----------|------------------------|------------------|
| **JVM** | The engine that runs Java apps | Without it, Java won't run |
| **GC** | Automatic memory cleaner | Prevents memory from filling up and crashing |
| **-Xmx6G** | "You can use maximum 6GB" | Prevents app from eating all RAM |
| **MaxMetaspaceSize** | Limit for "behind-the-scenes" memory | Same - prevents unlimited growth |

---

## Visual Example

**Your 16GB Server:**

```
WITHOUT PROPER SETTINGS:
┌─────────────────────────────────────┐
│  16GB RAM                           │
│                                     │
│  Java app keeps growing...          │
│  ███████████████████████████████    │ ← App using 15GB!
│  ▓ (OS needs memory too!)           │ ← OS squeezed out
│                                     │
│  CRASH! Not enough space            │
└─────────────────────────────────────┘

WITH PROPER SETTINGS (-Xmx6G):
┌─────────────────────────────────────┐
│  16GB RAM                           │
│                                     │
│  Java app limited to 6GB:           │
│  ████████                           │ ← App (6GB max)
│  ░░░░░░░░░░                         │ ← OS + buffers (8GB)
│  ▓▓                                 │ ← Other stuff (2GB)
│                                     │
│  Everything runs smoothly ✓         │
└─────────────────────────────────────┘
```

---

## The "Garbage Collection" Process

**Think of your app like a restaurant:**

1. **Lunch rush** (12-2 PM):
   - Many customers (data created)
   - Many dirty plates pile up (old data)
   
2. **GC kicks in** (dishwasher):
   - Finds plates no longer needed
   - Washes them (frees memory)
   - Makes room for dinner rush
   
3. **If dishwasher is too slow**:
   - Plates pile up faster than cleaning
   - Run out of clean plates
   - Restaurant stops → **APP CRASHES**

**Solution:** 
- Bigger dishwasher (more GC power)
- Fewer plates overall (limit memory)
- Both → Your app runs smoothly!

---

## Bottom Line for Your Case

**Problem:** Your app had unlimited memory growth → crashed

**Solution:** Set limits:
```bash
-Xmx6G              ← "Use maximum 6GB for app data"
-XX:MaxMetaspaceSize=512M  ← "Use maximum 512MB for system data"
```

**Result:** App stays within limits, GC keeps things clean, no crashes!

---


## Default JVM & GC Settings

| **Java Version** | **Default Heap (16GB RAM)** | **% of Physical RAM** | **Default GC** | **Metaspace/PermGen** | **Thread Stack** |
|------------------|----------------------------|-----------------------|----------------|-----------------------|------------------|
| Java 8 | Initial: 256MB, Max: 4GB | Initial: 1.6%, Max: 25% | Parallel GC | PermGen: Unlimited | 1MB per thread |
| Java 20 | Initial: 256MB, Max: 4GB | Initial: 1.6%, Max: 25% | G1GC | Metaspace: Unlimited | 1MB per thread |
| Java 21 | Initial: 256MB, Max: 4GB | Initial: 1.6%, Max: 25% | G1GC | Metaspace: Unlimited | 1MB per thread |

**Critical Problem:** Unlimited Metaspace/PermGen causes native memory exhaustion and crashes.

---

## Production Thumb Rules

### 1. Heap Size Formula
```
Heap = Physical RAM × 40-50%
Always set: -Xms = -Xmx (avoid resizing)
```

| **Physical RAM** | **Recommended Heap** | **% of Physical RAM** |
|------------------|---------------------|-----------------------|
| 4 GB | 1.5 - 2 GB | 37 - 50% |
| 8 GB | 3 - 4 GB | 37 - 50% |
| 16 GB | 6 - 8 GB | 37 - 50% |
| 32 GB | 12 - 16 GB | 37 - 50% |

### 2. GC Selection
```
Heap < 8GB:  Use G1GC
Heap > 8GB:  Use G1GC (or ZGC for ultra-low latency)
```

### 3. Metaspace Limits (Critical)

| **Application Type** | **Metaspace Size** | **% of Physical RAM** |
|----------------------|-------------------|-----------------------|
| Small apps | 256 - 512MB | 1.6 - 3.2% (16GB server) |
| Medium apps | 512MB - 1GB | 3.2 - 6.25% (16GB server) |
| Large apps | 1 - 2GB | 6.25 - 12.5% (16GB server) |

**NEVER leave unlimited**

### 4. Thread Stack

| **Thread Count** | **Stack Size** | **Total Stack Memory** | **% of Physical RAM (16GB)** |
|------------------|----------------|------------------------|------------------------------|
| < 100 threads | -Xss1024k (1MB) | < 100MB | < 0.6% |
| 100-200 threads | -Xss512k | 50-100MB | 0.3 - 0.6% |
| > 200 threads | -Xss256k | Variable | 0.2%+ |

### 5. Direct Memory

| **Application Type** | **Direct Memory** | **% of Physical RAM (16GB)** |
|----------------------|-------------------|-----------------------------|
| Small apps | 256 - 512MB | 1.6 - 3.2% |
| Medium apps | 512MB - 1GB | 3.2 - 6.25% |
| Large apps | 1 - 2GB | 6.25 - 12.5% |

---

## Complete Production Configurations

### Java 8

| **RAM** | **Configuration** | **Heap %** | **Metaspace %** | **Total JVM %** |
|---------|-------------------|-----------|-----------------|-----------------|
| **4GB** | `-Xms1536M -Xmx1536M -XX:PermSize=256M -XX:MaxPermSize=256M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=512M` | 37.5% | 6.25% | ~60% |
| **8GB** | `-Xms3G -Xmx3G -XX:PermSize=256M -XX:MaxPermSize=512M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` | 37.5% | 6.25% | ~62% |
| **16GB** | `-Xms6G -Xmx6G -XX:PermSize=512M -XX:MaxPermSize=1G -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` | 37.5% | 6.25% | ~53% |

### Java 21

| **RAM** | **Configuration** | **Heap %** | **Metaspace %** | **Total JVM %** |
|---------|-------------------|-----------|-----------------|-----------------|
| **4GB** | `-Xms1536M -Xmx1536M -XX:MetaspaceSize=256M -XX:MaxMetaspaceSize=256M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=512M` | 37.5% | 6.25% | ~60% |
| **8GB** | `-Xms4G -Xmx4G -XX:MetaspaceSize=256M -XX:MaxMetaspaceSize=512M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` | 50% | 6.25% | ~75% |
| **16GB** | `-Xms8G -Xmx8G -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=768M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` | 50% | 4.7% | ~62% |

---

## Memory Breakdown for 16GB Server (Java 21 Production Config)

| **Component** | **Size** | **% of 16GB RAM** |
|---------------|----------|-------------------|
| Heap (-Xmx) | 8GB | 50% |
| Metaspace | 768MB | 4.7% |
| Thread Stacks (200 threads × 512k) | 100MB | 0.6% |
| Direct Memory | 1GB | 6.25% |
| Code Cache | 240MB | 1.5% |
| JVM Internals | ~200MB | 1.25% |
| **Total JVM** | **~10.3GB** | **~64%** |
| **OS + Buffers** | **~5.7GB** | **~36%** |

---

## setenv.sh Configuration Files

### Java 8 - 4GB RAM

**File:** `/path/to/tomcat/bin/setenv.sh`

```bash
#!/bin/bash

# Heap settings (37.5% of 4GB = 1.5GB)
export CATALINA_OPTS="-Xms1536M -Xmx1536M"

# PermGen settings (Java 8)
export CATALINA_OPTS="$CATALINA_OPTS -XX:PermSize=256M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxPermSize=256M"

# Thread stack
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=512M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=2"

# GC Logging (Java 8)
export CATALINA_OPTS="$CATALINA_OPTS -Xloggc:/path/to/tomcat/logs/gc.log"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintGCDetails"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintGCDateStamps"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseGCLogFileRotation"
export CATALINA_OPTS="$CATALINA_OPTS -XX:NumberOfGCLogFiles=5"
export CATALINA_OPTS="$CATALINA_OPTS -XX:GCLogFileSize=100M"

# Heap dump on OOM
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/path/to/tomcat/logs/"

# Print configuration
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

### Java 8 - 8GB RAM

**File:** `/path/to/tomcat/bin/setenv.sh`

```bash
#!/bin/bash

# Heap settings (37.5% of 8GB = 3GB)
export CATALINA_OPTS="-Xms3G -Xmx3G"

# PermGen settings (Java 8)
export CATALINA_OPTS="$CATALINA_OPTS -XX:PermSize=256M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxPermSize=512M"

# Thread stack
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=1G"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"

# GC Logging (Java 8)
export CATALINA_OPTS="$CATALINA_OPTS -Xloggc:/path/to/tomcat/logs/gc.log"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintGCDetails"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintGCDateStamps"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseGCLogFileRotation"
export CATALINA_OPTS="$CATALINA_OPTS -XX:NumberOfGCLogFiles=5"
export CATALINA_OPTS="$CATALINA_OPTS -XX:GCLogFileSize=100M"

# Heap dump on OOM
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/path/to/tomcat/logs/"

# Print configuration
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

### Java 8 - 16GB RAM

**File:** `/path/to/tomcat/bin/setenv.sh`

```bash
#!/bin/bash

# Heap settings (37.5% of 16GB = 6GB)
export CATALINA_OPTS="-Xms6G -Xmx6G"

# PermGen settings (Java 8)
export CATALINA_OPTS="$CATALINA_OPTS -XX:PermSize=512M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxPermSize=1G"

# Thread stack
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=1G"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"

# GC Logging (Java 8)
export CATALINA_OPTS="$CATALINA_OPTS -Xloggc:/path/to/tomcat/logs/gc.log"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintGCDetails"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintGCDateStamps"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseGCLogFileRotation"
export CATALINA_OPTS="$CATALINA_OPTS -XX:NumberOfGCLogFiles=5"
export CATALINA_OPTS="$CATALINA_OPTS -XX:GCLogFileSize=100M"

# Heap dump on OOM
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/path/to/tomcat/logs/"

# Print configuration
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

---

### Java 21 - 4GB RAM

**File:** `/path/to/tomcat/bin/setenv.sh`

```bash
#!/bin/bash

# Heap settings (37.5% of 4GB = 1.5GB)
export CATALINA_OPTS="-Xms1536M -Xmx1536M"

# Metaspace settings (Java 21)
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=256M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxMetaspaceSize=256M"

# Thread stack
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=512M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=2"

# GC Logging (Java 21)
export CATALINA_OPTS="$CATALINA_OPTS -Xlog:gc*:file=/path/to/tomcat/logs/gc.log:time,uptime,level,tags:filecount=5,filesize=100M"

# Heap dump on OOM
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/path/to/tomcat/logs/"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+ExitOnOutOfMemoryError"

# Print configuration
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

### Java 21 - 8GB RAM

**File:** `/path/to/tomcat/bin/setenv.sh`

```bash
#!/bin/bash

# Heap settings (50% of 8GB = 4GB)
export CATALINA_OPTS="-Xms4G -Xmx4G"

# Metaspace settings (Java 21)
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=256M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxMetaspaceSize=512M"

# Thread stack
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=1G"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"

# GC Logging (Java 21)
export CATALINA_OPTS="$CATALINA_OPTS -Xlog:gc*:file=/path/to/tomcat/logs/gc.log:time,uptime,level,tags:filecount=5,filesize=100M"

# Heap dump on OOM
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/path/to/tomcat/logs/"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+ExitOnOutOfMemoryError"

# Print configuration
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

### Java 21 - 16GB RAM (YOUR CASE)

**File:** `/home/tomcat-user/tomcat/bin/setenv.sh`

```bash
#!/bin/bash

# Heap settings (50% of 16GB = 8GB)
export CATALINA_OPTS="-Xms8G -Xmx8G"

# Metaspace settings (Java 21)
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=512M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxMetaspaceSize=768M"

# Thread stack (you have 200+ threads)
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=1G"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ConcGCThreads=2"

# GC Logging (Java 21)
export CATALINA_OPTS="$CATALINA_OPTS -Xlog:gc*:file=/home/tomcat-user/tomcat/logs/gc.log:time,uptime,level,tags:filecount=5,filesize=100M"

# Heap dump on OOM
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/home/tomcat-user/tomcat/logs/"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+ExitOnOutOfMemoryError"

# Print configuration
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

---

## Installation Instructions

### 1. Create setenv.sh file

```bash
# Navigate to Tomcat bin directory
cd /home/tomcat-user/tomcat/bin

# Create the file (use appropriate template from above)
nano setenv.sh

# Paste the appropriate configuration
# Save and exit (Ctrl+O, Enter, Ctrl+X)
```

### 2. Set permissions

```bash
# Make executable
chmod +x setenv.sh

# Set correct ownership
chown tomcat:tomcat setenv.sh
```

### 3. Verify configuration

```bash
# Check file exists and is executable
ls -l setenv.sh

# Expected output:
# -rwxr-xr-x 1 tomcat tomcat 1234 Feb 06 14:00 setenv.sh
```

### 4. Restart Tomcat

```bash
# Stop Tomcat
/home/tomcat-user/tomcat/bin/shutdown.sh

# Wait a few seconds
sleep 5

# Start Tomcat
/home/tomcat-user/tomcat/bin/startup.sh
```

### 5. Verify settings applied

```bash
# Check running process
ps aux | grep java | grep Xmx

# Should see: -Xms8G -Xmx8G -XX:MaxMetaspaceSize=768M etc.
```

---

## Production Checklist

After creating setenv.sh:

- Verify file permissions (executable)
- Verify ownership (correct user)
- Update log paths in configuration
- Restart Tomcat
- Check startup logs for errors
- Verify JVM settings with ps command
- Monitor GC logs
- Monitor heap usage with jstat or monitoring tools
