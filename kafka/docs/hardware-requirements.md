# Hardware Requirements
## What Servers Do You Need?

---

##  Overview

This guide helps you understand what hardware you need for a production Kafka cluster handling financial transactions.

**Bottom Line Up Front:**
- **Servers Needed:** 3 identical servers
- **Estimated Cost:** $15,000 - $45,000 (depending on specifications)
- **Minimum Investment:** ~$15,000 for basic production
- **Recommended Investment:** ~$30,000 for solid production
- **Premium Investment:** ~$45,000+ for high-performance

---

##  Server Specifications

### Minimum Production Configuration (Start Here)

**Per Server:**
| Component | Specification | Why This Matters |
|-----------|--------------|------------------|
| **CPU** | 8 cores (16 threads) @ 2.4 GHz | Handles network I/O and compression |
| **RAM** | 32 GB | 6 GB for Kafka, 24 GB for OS page cache |
| **Storage** | 500 GB SSD | Stores topic data |
| **Network** | 1 Gbps | Communication between servers |

**Total for 3 Servers:** ~$15,000

**Good For:**
- Development and testing
- Low to medium transaction volumes (<10,000 TPS)
- Non-critical workloads
- Learning and training

**Limitations:**
- Limited scalability
- Slower performance
- Less headroom for growth

---

### Recommended Production Configuration (Best Balance)

**Per Server:**
| Component | Specification | Why This Matters |
|-----------|--------------|------------------|
| **CPU** | 16-24 cores (32-48 threads) @ 2.8 GHz | Better throughput and lower latency |
| **RAM** | 64 GB | 6 GB Kafka, 54 GB page cache = faster reads |
| **Storage** | 1-2 TB NVMe SSD | Fast writes, more retention |
| **Network** | 10 Gbps | High-speed cluster communication |

**Total for 3 Servers:** ~$30,000

**Good For:**
- Financial transaction processing
- High-volume workloads (10,000-100,000 TPS)
- Mission-critical systems
- Room to grow

**Benefits:**
- Excellent performance
- Good scalability
- Reliable under load
- Future-proof

---

### Premium Production Configuration (Maximum Performance)

**Per Server:**
| Component | Specification | Why This Matters |
|-----------|--------------|------------------|
| **CPU** | 24+ cores (48+ threads) @ 3.0 GHz | Maximum throughput |
| **RAM** | 128 GB | 10 GB Kafka, 110+ GB page cache |
| **Storage** | 2-4 TB NVMe RAID 10 | Ultra-fast, redundant storage |
| **Network** | 25 Gbps | Zero network bottlenecks |

**Total for 3 Servers:** ~$45,000+

**Good For:**
- High-frequency trading
- Extreme transaction volumes (100,000+ TPS)
- Ultra-low latency requirements (<1ms)
- Enterprise-scale deployments

**Benefits:**
- Maximum performance
- Unlimited scalability
- Premium reliability
- Zero compromises

---

##  Detailed Component Breakdown

### CPU (Processor)

**What Kafka Uses CPU For:**
- Network request handling
- Compression/decompression
- Replication
- Partition management

**Recommendations:**

**Minimum:** Intel Xeon E-2288G (8 cores) or AMD EPYC 7262 (8 cores)
- **Cost:** ~$500 per CPU
- **Performance:** Good for light workloads
- **Limitation:** May become bottleneck under heavy load

**Recommended:** Intel Xeon Gold 6226R (16 cores) or AMD EPYC 7402 (24 cores)
- **Cost:** ~$1,500 per CPU
- **Performance:** Excellent for most workloads
- **Sweet Spot:** Best price/performance ratio

**Premium:** Intel Xeon Platinum 8380 (40 cores) or AMD EPYC 7763 (64 cores)
- **Cost:** ~$4,000+ per CPU
- **Performance:** Maximum throughput
- **Use Case:** High-frequency trading, extreme loads

**Simple Explanation:**
Think of CPU cores like checkout lanes at a supermarket. More lanes = more customers served simultaneously. For Kafka, more cores = more messages processed per second.

---

### RAM (Memory)

**What Kafka Uses RAM For:**
- JVM heap (Kafka process memory): 6-10 GB
- OS page cache (recently accessed data): Remaining RAM
- Network buffers
- Compression buffers

**Memory Allocation Example (64 GB server):**
```
Total RAM: 64 GB
├── Kafka JVM Heap: 6 GB      (10%)
├── OS Page Cache: 54 GB      (84%)
└── OS + Other: 4 GB          (6%)
```

**Why Page Cache Matters:**
- **Page cache** = RAM used to cache recently read data from disk
- **Benefit:** Reads from RAM (microseconds) instead of disk (milliseconds)
- **Impact:** 1000x faster reads!
- **Rule:** More RAM = more data in cache = faster performance

**Recommendations:**

**Minimum: 32 GB**
- Heap: 6 GB
- Page Cache: 24 GB
- Good for: Light workloads

**Recommended: 64 GB**
- Heap: 6 GB
- Page Cache: 54 GB
- Good for: Most production workloads

**Premium: 128 GB**
- Heap: 10 GB
- Page Cache: 110 GB
- Good for: High-performance requirements

**Simple Explanation:**
Kafka needs RAM for two things: (1) its own working memory (heap), and (2) caching data for fast reads (page cache). The more page cache, the faster Kafka runs.

**Formula for Estimating RAM Needs:**
```
Required RAM = write_throughput_MB/s × 30 seconds + 6 GB heap + 4 GB OS

Example:
100 MB/s throughput × 30 sec = 3 GB cache needed
3 GB + 6 GB heap + 4 GB OS = 13 GB minimum
Recommendation: 32 GB (2.5x buffer for peak loads)
```

---

### Storage (Disk)

**What Kafka Uses Storage For:**
- Topic data (messages): Most space
- Metadata logs: Small (~10 GB)
- System logs: Small (~5 GB)

**Storage Calculation:**
```
Storage Needed = daily_data × retention_days × safety_margin

Example:
- Daily data: 100 GB/day
- Retention: 7 days
- Safety margin: 2x
Result: 100 × 7 × 2 = 1,400 GB = 1.4 TB
```

**Storage Types (Performance Comparison):**

**HDD (Hard Disk Drive) - NOT RECOMMENDED**
- Speed: ~100-200 IOPS (slow!)
- Latency: 10-15 ms (high!)
- Cost: $0.03/GB (cheap but not worth it)
- **Issue:** Too slow for Kafka. Will cause problems.

**SATA SSD (Solid State Drive) - Minimum**
- Speed: ~50,000 IOPS
- Latency: 0.5-1 ms
- Cost: $0.15/GB
- **Use:** Development/testing only

**NVMe SSD (M.2 or PCIe) - Recommended**
- Speed: ~500,000 IOPS
- Latency: 0.05-0.1 ms
- Cost: $0.30/GB
- **Use:** Production workloads

**NVMe RAID 10 - Premium**
- Speed: ~1,000,000 IOPS
- Latency: 0.03-0.05 ms
- Cost: $0.50/GB (requires 4 drives)
- **Use:** High-performance, mission-critical

**Recommendations:**

**Minimum: 500 GB NVMe SSD**
- Cost: ~$150
- Good for: Light workloads, 3-7 days retention

**Recommended: 1-2 TB NVMe SSD**
- Cost: ~$300-600
- Good for: Production, 7-14 days retention

**Premium: 2-4 TB NVMe RAID 10**
- Cost: ~$2,000-4,000
- Good for: High-performance, 30+ days retention

**Simple Explanation:**
Kafka writes and reads from disk constantly. Slow disk = slow Kafka. NVMe SSDs are 10-50x faster than hard drives. Always use SSDs for production.

**RAID Configuration:**
- **RAID 0:** Fast but dangerous (no redundancy) - DON'T USE
- **RAID 1:** Safe but expensive (50% usable space)
- **RAID 10:** Fast AND safe (50% usable, 2x performance) - BEST CHOICE
- **No RAID:** Kafka handles replication - ACCEPTABLE (we have 3 copies anyway)

---

### Network

**What Kafka Uses Network For:**
- Client connections (producers/consumers)
- Inter-broker replication
- Controller communication
- Monitoring traffic

**Network Calculation:**
```
Network Needed = (writes × replication_factor) + reads

Example:
- Writes: 500 MB/s
- Replication factor: 3
- Reads: 500 MB/s
Result: (500 × 3) + 500 = 2,000 MB/s = 16 Gbps peak
Recommendation: 25 Gbps (1.5x headroom)
```

**Network Speeds:**

**1 Gbps (1 Gigabit per second) - Minimum**
- **Throughput:** ~125 MB/s
- **Good for:** Development, light workloads
- **Limitation:** Can become bottleneck quickly

**10 Gbps - Recommended**
- **Throughput:** ~1,250 MB/s
- **Good for:** Production workloads
- **Sweet spot:** Best for most use cases

**25 Gbps - Premium**
- **Throughput:** ~3,125 MB/s
- **Good for:** High-frequency trading, extreme loads
- **Benefit:** Never network-limited

**Requirements:**
- **Latency:** <1ms between brokers (same datacenter)
- **Dedicated:** Separate network for Kafka traffic (best practice)
- **Redundant:** Dual network cards (NIC bonding) for reliability

**Simple Explanation:**
Network is the highway that data travels on. Faster highway = more data moving. 10 Gbps is usually enough; 25 Gbps is for very heavy traffic.

---

##  Server Form Factors

### Rack Servers (Recommended for Production)

**Examples:** Dell PowerEdge R650, HP ProLiant DL360, Supermicro SYS-1029U

**Pros:**
- Datacenter-optimized
- Easy to rack and manage
- Good airflow/cooling
- Redundant power supplies

**Cons:**
- Requires datacenter/rack
- Higher upfront cost

**Cost:** $5,000-15,000 per server

---

### Tower Servers (Budget Option)

**Examples:** Dell PowerEdge T450, HP ProLiant ML350

**Pros:**
- Lower cost
- Can run in office environment
- Easy to set up

**Cons:**
- Takes more space
- Less enterprise features
- Noisier

**Cost:** $3,000-8,000 per server

---

### Cloud Instances (Pay-as-you-go)

**AWS Examples:**
- **Minimum:** m5.2xlarge (8 vCPU, 32 GB RAM) - $280/month
- **Recommended:** m5.4xlarge (16 vCPU, 64 GB RAM) - $560/month
- **Premium:** m5.8xlarge (32 vCPU, 128 GB RAM) - $1,120/month

**Total for 3 instances (Recommended):**
- **Monthly:** $1,680
- **Yearly:** $20,160
- **3 Years:** $60,480

**Add storage (1 TB SSD per instance):** +$300/month = $3,600/year

**Pros:**
- No upfront cost
- Scalable
- Managed hardware
- High availability

**Cons:**
- Expensive over 3+ years
- Network latency between zones
- Less control

**Break-Even Point:** ~2 years (cloud becomes more expensive than owned hardware)

---

##  Total Cost of Ownership (TCO)

### On-Premises (3 Years)

**Hardware (3 servers @ $10,000 each):** $30,000  
**Datacenter/Colocation:** $3,000/year × 3 = $9,000  
**Power:** $1,200/year × 3 = $3,600  
**Internet:** $1,200/year × 3 = $3,600  
**Maintenance:** $2,000/year × 3 = $6,000  

**Total 3-Year Cost:** $52,200  
**Cost per Month:** $1,450

---

### Cloud (3 Years)

**Compute (3 × m5.4xlarge):** $1,680/month  
**Storage (3 × 1TB SSD):** $300/month  
**Network Transfer:** $200/month  
**Backups:** $100/month  

**Total per Month:** $2,280  
**Total 3-Year Cost:** $82,080

---

### Comparison

| Cost Factor | On-Premises | Cloud | Winner |
|-------------|-------------|-------|---------|
| **Initial Investment** | $30,000 | $0 | Cloud |
| **Monthly Cost** | $1,450 | $2,280 | On-Prem |
| **3-Year Total** | $52,200 | $82,080 | On-Prem |
| **5-Year Total** | $68,400 | $136,800 | On-Prem |
| **Flexibility** | Low | High | Cloud |
| **Performance** | High | Medium | On-Prem |

**Recommendation:**
- **Short-term (<1 year):** Cloud (testing, evaluation)
- **Long-term (3+ years):** On-Premises (better economics)
- **Hybrid:** On-prem for steady load, cloud for bursts

---

##  Deployment Considerations

### Same Datacenter (Recommended)

**Benefits:**
- Low latency (<1ms)
- High bandwidth
- Reliable connections
- Easier management

**Use Case:** 99% of deployments

---

### Multi-Datacenter (Advanced)

**Challenges:**
- Higher latency (50-100ms)
- Network partitions
- Complexity
- Cost

**Use Case:** Disaster recovery only (use MirrorMaker 2)

**Recommendation:** AVOID running a single Kafka cluster across multiple datacenters. Instead, run separate clusters and replicate with MirrorMaker 2.

---

##  Pre-Purchase Checklist

Before buying hardware, verify:

**Requirements Documented:**
- [ ] Expected message volume (messages/second)
- [ ] Expected data volume (GB/day)
- [ ] Retention requirements (days)
- [ ] Peak load estimates
- [ ] Growth projections (2-3 years)

**Budget Approved:**
- [ ] Hardware costs
- [ ] Datacenter/colocation costs
- [ ] Network costs
- [ ] Support/maintenance costs

**Infrastructure Ready:**
- [ ] Rack space available
- [ ] Power capacity (30A per rack minimum)
- [ ] Cooling capacity
- [ ] Network infrastructure (10 Gbps switches)
- [ ] Physical security

**Compatibility Verified:**
- [ ] OS compatibility (RHEL 9 certified)
- [ ] BIOS/firmware current
- [ ] Network cards supported
- [ ] Storage controllers supported

---

##  Recommendations by Use Case

### Development/Testing
- **Servers:** 3 × tower servers
- **CPU:** 8 cores
- **RAM:** 32 GB
- **Storage:** 500 GB SSD
- **Network:** 1 Gbps
- **Cost:** ~$15,000

### Financial Transactions (Your Case)
- **Servers:** 3 × rack servers
- **CPU:** 16-24 cores
- **RAM:** 64 GB
- **Storage:** 1-2 TB NVMe
- **Network:** 10 Gbps
- **Cost:** ~$30,000

### High-Frequency Trading
- **Servers:** 3 × premium rack servers
- **CPU:** 24+ cores
- **RAM:** 128 GB
- **Storage:** 2-4 TB NVMe RAID 10
- **Network:** 25 Gbps
- **Cost:** ~$45,000+

---

##  Quick Reference Table

| Component | Minimum | Recommended | Premium |
|-----------|---------|-------------|---------|
| **Servers** | 3 | 3 | 3 |
| **CPU/Server** | 8 cores | 16-24 cores | 24+ cores |
| **RAM/Server** | 32 GB | 64 GB | 128 GB |
| **Storage/Server** | 500 GB SSD | 1-2 TB NVMe | 2-4 TB RAID 10 |
| **Network** | 1 Gbps | 10 Gbps | 25 Gbps |
| **Total Cost** | ~$15K | ~$30K | ~$45K+ |
| **TPS Capacity** | 10K | 100K | 500K+ |

---

##  Next Steps

1. **Calculate Your Needs:**
   - Estimate daily data volume
   - Determine retention period
   - Calculate required throughput

2. **Choose Configuration:**
   - Start with "Recommended" for financial transactions
   - Scale up if needed for extreme loads
   - Can start smaller for testing

3. **Get Quotes:**
   - Dell, HP, Supermicro
   - Compare on-premises vs. cloud
   - Factor in 3-year TCO

4. **Plan Infrastructure:**
   - Datacenter/colocation space
   - Network connectivity
   - Power and cooling

5. **Proceed to Installation:**
   - [Step-by-Step Installation Guide](../03-installation/step-by-step-guide.md)

---

**Questions?** See [FAQ](../../README.md#common-questions) or ask your vendor for sizing assistance.
