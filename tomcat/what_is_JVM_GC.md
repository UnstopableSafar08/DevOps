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


## Default JVM & GC Settings Table

| **Java Version** | **Default Initial Heap (-Xms)** | **Default Max Heap (-Xmx)** | **Default GC** | **Metaspace/PermGen** | **Thread Stack (-Xss)** | **Code Cache** |
|------------------|--------------------------------|----------------------------|----------------|-----------------------|------------------------|----------------|
| **Java 8** | 1/64 of RAM (~256MB for 16GB) | 1/4 of RAM (~4GB for 16GB) | **Parallel GC** | PermGen: **Unlimited** (MaxPermSize not set) | **1MB** | 240MB |
| **Java 20** | 1/64 of RAM (~256MB for 16GB) | 1/4 of RAM (~4GB for 16GB) | **G1GC** | Metaspace: **Unlimited**  | **1MB** | 240MB |
| **Java 21** | 1/64 of RAM (~256MB for 16GB) | 1/4 of RAM (~4GB for 16GB) | **G1GC** | Metaspace: **Unlimited**  | **1MB** | 240MB |

### ** Critical Default Problems:**
- **Metaspace/PermGen unlimited** = Will consume all native memory → Crashes
- **Initial heap too small** (256MB) = Frequent resizing, poor performance
- **Thread stack 1MB** = Wastes memory with many threads

---

## Production Environment Thumb Rules

### **Rule 1: Heap Size Allocation**

| **Physical RAM** | **Heap Size (-Xms/-Xmx)** | **Percentage** | **Reasoning** |
|------------------|---------------------------|----------------|---------------|
| **4 GB** | 1.5 - 2 GB | 37-50% | Leave room for OS + non-heap memory |
| **8 GB** | 3 - 4 GB | 37-50% | Balanced for medium apps |
| **16 GB** | 6 - 8 GB | 37-50% | Safe for enterprise apps |
| **32 GB** | 12 - 16 GB | 37-50% | Large apps, careful GC tuning needed |
| **64 GB+** | 20 - 32 GB | 31-50% | Consider ZGC or Shenandoah |

**Formula:** `Heap = Physical RAM × 0.4 to 0.5`

---

### **Rule 2: GC Selection by Heap Size**

| **Heap Size** | **Recommended GC** | **GC Parameters** | **Use Case** |
|---------------|-------------------|-------------------|--------------|
| **< 2 GB** | **Parallel GC** | `-XX:+UseParallelGC` | Small apps, throughput priority |
| **2 - 8 GB** | **G1GC** | `-XX:+UseG1GC -XX:MaxGCPauseMillis=200` | Most production apps (default choice) |
| **8 - 32 GB** | **G1GC** | `-XX:+UseG1GC -XX:MaxGCPauseMillis=100` | Large apps, tune pause times |
| **> 32 GB** | **ZGC or Shenandoah** | `-XX:+UseZGC` or `-XX:+UseShenandoahGC` | Ultra-low latency requirements |

**Default choice for production:** **G1GC** (works well 90% of the time)

---

### **Rule 3: Metaspace/PermGen Limits**

| **Application Type** | **MetaspaceSize** | **MaxMetaspaceSize** | **Reasoning** |
|----------------------|-------------------|----------------------|---------------|
| **Small app (< 100 classes)** | 128M | 256M | Minimal framework usage |
| **Medium app (Spring Boot)** | 256M | 512M | Standard frameworks |
| **Large app (Microservices)** | 512M | 1G | Many dependencies, frameworks |
| **Very large (Heavy frameworks)** | 512M | 2G | Extensive class loading |

**⚠️ NEVER leave unlimited in production!**

---

### **Rule 4: Thread Stack Size**

| **Thread Count** | **Stack Size (-Xss)** | **Total Stack Memory** | **Reasoning** |
|------------------|-----------------------|------------------------|---------------|
| **< 50 threads** | 1024k (1MB) | < 50 MB | Default is fine |
| **50 - 200 threads** | 512k | 25 - 100 MB | Reduce to save memory |
| **200 - 500 threads** | 256k | 50 - 125 MB | High concurrency apps |
| **> 500 threads** | 256k | > 125 MB | Consider async/reactive patterns |

**Formula:** `Total Stack Memory = Thread Count × Stack Size`

---

### **Rule 5: Direct Memory & Code Cache**

| **Setting** | **Small App** | **Medium App** | **Large App** |
|-------------|---------------|----------------|---------------|
| **MaxDirectMemorySize** | 256M | 512M - 1G | 1 - 2G |
| **ReservedCodeCacheSize** | 128M | 240M | 512M |

---

## Complete Production Configuration Matrix

### **Java 8 Production Settings**

| **RAM** | **Complete Configuration** |
|---------|---------------------------|
| **4 GB** | `-Xms1536M -Xmx1536M -XX:PermSize=256M -XX:MaxPermSize=256M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=512M` |
| **8 GB** | `-Xms3G -Xmx3G -XX:PermSize=256M -XX:MaxPermSize=512M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` |
| **16 GB** | `-Xms6G -Xmx6G -XX:PermSize=512M -XX:MaxPermSize=1G -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` |

### **Java 21 Production Settings**

| **RAM** | **Complete Configuration** |
|---------|---------------------------|
| **4 GB** | `-Xms1536M -Xmx1536M -XX:MetaspaceSize=256M -XX:MaxMetaspaceSize=256M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=512M` |
| **8 GB** | `-Xms4G -Xmx4G -XX:MetaspaceSize=256M -XX:MaxMetaspaceSize=512M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` |
| **16 GB** | `-Xms8G -Xmx8G -XX:MetaspaceSize=512M -XX:MaxMetaspaceSize=768M -Xss512k -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:MaxDirectMemorySize=1G` |

---

## Production Thumb Rules Checklist

### **1. Memory Allocation**
```
Set -Xms = -Xmx (avoid resizing)
Heap = 40-50% of physical RAM
ALWAYS cap Metaspace (never unlimited)
Leave 25-40% RAM for OS + buffers
```

### **2. GC Selection**
```
Heap < 8GB → Use G1GC
Heap > 8GB → Use G1GC with tuning or consider ZGC
Set MaxGCPauseMillis (100-200ms is typical)
Monitor GC logs in production
```

### **3. Thread & Native Memory**
```
Reduce thread stack if > 100 threads
Cap DirectMemory (don't leave unlimited)
Reserve code cache appropriately
```

### **4. Monitoring & Safety**
```
Enable GC logging
Enable heap dump on OOM
Set up monitoring (Prometheus, AppDynamics, etc.)
Test under production-like load
```

---

## Quick Decision Tree for Production

```
START
  |
  ├─ RAM size?
  │   ├─ 4GB  → Heap: 1.5G, Metaspace: 256M, G1GC
  │   ├─ 8GB  → Heap: 4G, Metaspace: 512M, G1GC
  │   └─ 16GB → Heap: 8G, Metaspace: 768M, G1GC
  |
  ├─ Thread count?
  │   ├─ < 100   → -Xss1024k
  │   └─ > 100   → -Xss512k
  |
  ├─ Java version?
  │   ├─ Java 8  → Use PermSize/MaxPermSize
  │   └─ Java 21 → Use MetaspaceSize/MaxMetaspaceSize
  |
  └─ DONE → Test, monitor, adjust
```

---

## Your Specific Case (16GB, Java 21, Production)

### **Recommended Configuration:**

```bash
#!/bin/bash
# /home/abc-mi/abc-mi/bin/setenv.sh

# Heap settings
export CATALINA_OPTS="-Xms8G -Xmx8G"

# Metaspace (CRITICAL - cap it!)
export CATALINA_OPTS="$CATALINA_OPTS -XX:MetaspaceSize=512M"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxMetaspaceSize=768M"

# Thread optimization (you have 200+ threads)
export CATALINA_OPTS="$CATALINA_OPTS -Xss512k"

# Native memory limits
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxDirectMemorySize=1G"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ReservedCodeCacheSize=240M"

# G1GC settings
export CATALINA_OPTS="$CATALINA_OPTS -XX:+UseG1GC"
export CATALINA_OPTS="$CATALINA_OPTS -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ParallelGCThreads=4"
export CATALINA_OPTS="$CATALINA_OPTS -XX:ConcGCThreads=2"

# GC Logging (Java 21 format)
export CATALINA_OPTS="$CATALINA_OPTS -Xlog:gc*:file=/home/abc-mi/abc-mi/logs/gc.log:time,uptime,level,tags:filecount=5,filesize=100M"

# Safety net
export CATALINA_OPTS="$CATALINA_OPTS -XX:+HeapDumpOnOutOfMemoryError"
export CATALINA_OPTS="$CATALINA_OPTS -XX:HeapDumpPath=/home/abc-mi/abc-mi/logs/"
export CATALINA_OPTS="$CATALINA_OPTS -XX:+ExitOnOutOfMemoryError"

# Print settings on startup
export CATALINA_OPTS="$CATALINA_OPTS -XX:+PrintCommandLineFlags"
```

This configuration will solve your "Not enough space" crashes and give you stable, predictable production performance.
