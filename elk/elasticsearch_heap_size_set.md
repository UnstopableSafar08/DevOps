### 1. **Calculating heap for 15 GB RAM**

Rules for Elasticsearch:

1. **Heap should be <=50% of total RAM**.
2. **Never exceed 32 GB** (for CompressedOops, memory efficiency).
3. **Leave enough RAM for OS cache and other processes** (Elasticsearch relies heavily on file system cache for performance).

For **15 GB RAM**:

* 50% of 15 GB → **7.5 GB**
* Round down to a safe value → **7 GB** is ideal.

**So, set heap**:

```
-Xms7g
-Xmx7g
```

This leaves **arround 8 GB RAM** for OS cache, Lucene memory-mapped files, and other services (Kibana, Logstash, Beats).

---

### 2. **Why heap configuration is required**

Elasticsearch heap is **critical for performance** because:

1. **JVM heap stores data structures**:

   * Field data, aggregations, in-memory buffers
   * Lucene indexing buffers
2. **Proper sizing avoids GC issues**:

   * Too small → frequent garbage collection → slow queries
   * Too large → less OS cache → slower disk I/O
3. **Fixed heap** gives predictable memory usage:

   * ES recommends setting `Xms = Xmx`
   * Prevents the JVM from resizing heap dynamically → reduces GC pauses
4. **Leaves memory for the OS**:

   * Elasticsearch relies on **OS page cache** to read segments efficiently
   * Only part of RAM should be heap, the rest is OS cache

---

**Rule of thumb summary**:

| Total RAM | Recommended Heap |
| --------- | ---------------- |
| 15 GB     | 7 GB             |
| 23 GB     | 10–11 GB         |
| 32 GB     | 16 GB            |
| ≥64 GB    | 32 GB max        |

---

### Can assign 4 GB heap on a 15 GB RAM node.
- Assigning 4 GB heap is safe but conservative.
- If your workload is light and small indices, 4 GB is fine.
- For medium-to-large production workloads, 7 GB is optimal.


## Where to set heap

* Main file: `/etc/elasticsearch/jvm.options`
  - Default JVM settings shipped with Elasticsearch.
  - You can edit it, but modifying shipped files is not recommended (updates may overwrite).

* Custom file: `/etc/elasticsearch/jvm.options.d/heap.options`
* Recommended way to override heap settings.
* Any `*.options` file in `jvm.options.d` is read after jvm.options, so it takes precedence.


Restart the elsaticsearch and verify
```bash
curl -s http://localhost:9200/_nodes/stats/jvm | jq '.nodes[].jvm.mem.heap_max_in_bytes/1024/1024/1024'
```


### Memory Allocation Table for a single ELK-Stack node.
Let’s create a **memory allocation table for a 15 GB RAM node** running Elasticsearch, Kibana, Logstash, and Metricbeat. I’ll show **two scenarios**: Elasticsearch heap at 4 GB vs 7 GB.

---

### Assumptions

* Total RAM: 15 GB
* No swap configured (optional safety swap can be added)
* Other services share remaining RAM

---

### 1. Memory allocation table

| Component                  | Typical RES Usage | Scenario 1: ES heap 4 GB            | Scenario 2: ES heap 7 GB         | Notes                                                   |
| -------------------------- | ----------------- | ----------------------------------- | -------------------------------- | ------------------------------------------------------- |
| **Elasticsearch**          | Heap + native     | 4 GB heap (~6 GB RES)               | 7 GB heap (~9 GB RES)            | Heap set via `-Xms/-Xmx`; RES includes off-heap buffers |
| **Kibana**                 | 500–600 MB        | 600 MB                              | 600 MB                           | Default heap usually enough                             |
| **Logstash**               | 1–1.5 GB          | 1 GB                                | 1 GB                             | Can tune `-Xms/-Xmx` if needed                          |
| **Metricbeat + OS agents** | 200–300 MB        | 300 MB                              | 300 MB                           | Minimal memory usage                                    |
| **Kernel + FS cache**      | 2–3 GB            | 2.5 GB                              | 2 GB                             | Elasticsearch benefits from OS page cache               |
| **Total used**             | —                 | ~8.4–8.5 GB + 2.5 GB cache → ~11 GB | ~10.9 GB + 2 GB cache → ~12.9 GB | Leaves 3–4 GB available for system & bursts             |
| **Available RAM**          | —                 | ~4 GB                               | ~2 GB                            | Safety margin for spikes                                |

---

### 2. Analysis

* **4 GB heap**:

  * Safer for multi-service environment.
  * More memory for OS cache → faster segment reads.
  * Could **increase GC frequency** under heavy search or aggregation.

* **7 GB heap**:

  * Better for **medium-sized indices and heavy queries**.
  * Slightly less OS cache available → still acceptable for 15 GB node.
  * Leaves ~2 GB RAM for other processes and OS → tight but usually fine.

---

### 3. Recommendation

* If your workload is **moderate with small-to-medium indices**, go with **4 GB heap**.

* If you expect **frequent aggregations, searches, or indexing**, go with **7 GB heap**.

* **Always set Xms = Xmx**.

* Monitor memory and GC:

```bash
curl -s http://localhost:9200/_nodes/stats/jvm | jq '.nodes[].jvm.mem'
```

---

