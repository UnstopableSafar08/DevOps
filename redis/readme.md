# Redis on Oracle Linux 9 — Install, Config & Sizing Guide.

Target version: **Redis 8.10** (latest stable, GA July 2026). Adjust module/stream versions below if repo lags.

## Table of Contents

1. [Online Install (Remi/EPEL repo)](#1-online-install-remiepel-repo)
2. [Offline Install (airgapped, via Remi/EPEL)](#2-offline-install-airgapped-via-remiepel)
3. [Minimal Config — explained](#3-minimal-config--explained)
4. [Production Config — explained](#4-production-config--explained)
5. [Production Checklist](#5-production-checklist)
6. [OS-Level Tuning](#6-os-level-tuning)
7. [Resource Allocation Sizing](#7-resource-allocation-sizing)

---

## 1. Online Install — Option A: Redis official repo

For boxes with direct internet access. Fastest path to true latest-stable, since Redis's own repo tracks upstream releases immediately — no waiting on downstream packagers.

```bash
sudo tee /etc/yum.repos.d/redis.repo > /dev/null <<EOF
[Redis]
name=Redis
baseurl=https://packages.redis.io/rpm/rockylinux9
enabled=1
gpgcheck=1
gpgkey=https://packages.redis.io/gpg
EOF

sudo rpm --import https://packages.redis.io/gpg
sudo dnf install -y redis
sudo systemctl enable --now redis
redis-server --version
```

Config: `/etc/redis/redis.conf` · Service unit: `redis`

---

## 1b. Online Install — Option B: Remi/EPEL repo

Alternative when you'd rather standardize on Remi across your RHEL/OL fleet (e.g. already using Remi for PHP or other packages), or the official repo is blocked by policy/firewall. Still requires direct internet access — this is not the offline path.

```bash
# EPEL + Remi repo RPMs
dnf install -y epel-release
curl -O https://rpms.remirepo.net/enterprise/remi-release-9.rpm
dnf install -y remi-release-9.rpm

# Check which Redis stream Remi currently ships (may lag upstream — verify against target version)
dnf module list redis

dnf module reset redis -y
dnf module enable redis:remi-8.10 -y   # substitute actual available stream from the list above

dnf install -y redis
systemctl enable --now redis
redis-server --version
```

Note: Remi's module streams trail Redis upstream releases by days to weeks. If `redis:remi-8.10` isn't listed yet, either wait for the stream, or use Option A (official repo) for true latest-stable.

Config: `/etc/redis/redis.conf` · Service unit: `redis`

---

## 2. Offline Install (airgapped, via Remi/EPEL)

Use when target server has zero internet path — download on a connected staging box, transfer, install locally. Confirm the Remi module stream number matches 8.10 (or nearest available — Remi lags upstream by weeks; check `dnf module list redis` on the connected box first).

```bash
# ----- On Internet-Connected RHEL/OL9 Server -----

mkdir -p /tmp/remi-setup
cd /tmp/remi-setup
curl -O https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
curl -O https://rpms.remirepo.net/enterprise/remi-release-9.rpm

dnf install -y epel-release-latest-9.noarch.rpm remi-release-9.rpm

# Check available Redis streams, pick the one matching latest stable
dnf module list redis

dnf module reset redis -y
dnf module enable redis:remi-8.10 -y   # substitute actual available stream

mkdir -p /tmp/redis-offline
dnf install --downloadonly --downloaddir=/tmp/redis-offline redis

# Transfer both dirs to offline server (scp, or your internal `transfer` utility)
scp -r /tmp/remi-setup /tmp/redis-offline user@offline-server:/tmp/


# ----- On Offline (Airgapped) Server -----

cd /tmp/remi-setup
dnf install -y epel-release-latest-9.noarch.rpm remi-release-9.rpm

cd /tmp/redis-offline
dnf install -y *.rpm

redis-server -v
systemctl enable redis --now
systemctl status redis

# Secure baseline
vi /etc/redis/redis.conf
#   bind 127.0.0.1
#   requirepass StrongPasswordHere
#   protected-mode yes

systemctl restart redis
redis-cli -a StrongPasswordHere ping
```

Note: `epel-release` and `remi-release` are just repo-definition RPMs (small, metadata only) — `dnf install *.rpm` on the offline box works because all Redis deps were captured by `--downloadonly` on the connected box in the same dnf transaction.

---

## 3. Minimal Config — explained

```conf
bind 127.0.0.1        # only accept local connections — no network exposure
port 6379              # default Redis port
protected-mode no      # for dev and lower env.
daemonize no            # let systemd manage the process (supervised mode below handles this)
supervised systemd      # tells Redis to notify systemd on ready/stop — cleaner service control

dir /var/lib/redis      # working dir for RDB snapshot files
dbfilename dump.rdb     # snapshot filename

logfile /var/log/redis/redis.log
loglevel notice          # notice = balanced verbosity (skip debug noise, keep warnings/events)

maxmemory 256mb           # hard cap — prevents Redis eating all host RAM
maxmemory-policy noeviction  # reject writes at cap instead of silently dropping keys — safe default for dev

save 900 1               # snapshot if ≥1 key changed in 900s
save 300 10               # snapshot if ≥10 keys changed in 300s
```
Important Part : `bind`, `port`, `protected-mode`  <br>
**Use case:** local dev, single instance, no auth (safe only because bound to loopback).

---

## 4. Production Config — explained

```conf
################## NETWORK ##################
bind 0.0.0.0 -::1        # scope this to your actual internal iface/VLAN — never leave literal 0.0.0.0 in real prod
port 6379
protected-mode yes         # refuses remote connections if no password/bind set — safety net
tcp-backlog 511            # OS-level pending-connection queue size, matches high-concurrency default
tcp-keepalive 300           # probe idle connections every 300s, detects dead peers/NAT timeouts
timeout 0                   # 0 = never idle-disconnect clients (app manages its own connection lifecycle)

################## GENERAL ##################
daemonize no
supervised systemd
pidfile /run/redis/redis.pid
loglevel notice
logfile /var/log/redis/redis.log
databases 16               # number of logical DBs (SELECT 0-15) — legacy feature, fine to keep default

################## SECURITY ##################
requirepass CHANGE_ME_STRONG_PASSWORD   # mandatory in prod — blank password = anyone with network access has full control
# ACL preferred over requirepass for multi-user / least-privilege setups:
# user default on nopass ~* &* +@all
# aclfile /etc/redis/users.acl

rename-command FLUSHALL ""              # disable — prevents accidental/malicious full wipe
rename-command FLUSHDB ""               # disable — same, scoped to one DB
rename-command CONFIG "CONFIG_9f3a7"    # obscure instead of disable — ops still need it occasionally
rename-command SHUTDOWN "SHUTDOWN_9f3a7"

################## MEMORY ##################
maxmemory 4gb                    # cap tuned to instance RAM (see sizing section below)
maxmemory-policy allkeys-lru      # evict least-recently-used keys once at cap — right choice for cache workloads
maxmemory-samples 5               # LRU approximation sample size — 5 is a good accuracy/CPU tradeoff

################## PERSISTENCE ##################
# RDB — point-in-time snapshots
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes   # halt writes if disk fills/snapshot fails — surfaces the problem instead of silent data loss risk
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# AOF — append-only log, finer-grained durability than RDB alone
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec              # fsync once/sec — good balance of durability vs write throughput (vs always=slow, no=risky)
no-appendfsync-on-rewrite no      # don't skip fsync during AOF rewrite — keep durability even under rewrite load
auto-aof-rewrite-percentage 100   # trigger AOF compaction when file doubles in size
auto-aof-rewrite-min-size 64mb    # ...but only after it's at least this big, avoids rewrite thrashing on small files
aof-use-rdb-preamble yes          # AOF file starts with RDB snapshot — faster restart/reload

################## REPLICATION (if this node is a replica) ##################
# replicaof <master-ip> 6379
# masterauth CHANGE_ME_STRONG_PASSWORD
replica-read-only yes             # prevent writes hitting replica directly — enforces single source of truth
repl-diskless-sync yes            # stream RDB over socket instead of writing to disk first — faster initial sync
repl-diskless-sync-delay 5        # wait 5s for more replicas to join before starting diskless sync (batches multiple replica syncs)
repl-backlog-size 16mb            # buffer for partial resync after brief disconnect — avoids full resync on network blips

################## CLIENTS / LIMITS ##################
maxclients 10000                  # concurrent connection ceiling — protects against fd exhaustion

################## SLOW LOG ##################
slowlog-log-slower-than 10000     # log commands taking >10ms (microseconds unit) — surfaces perf problems
slowlog-max-len 128                # ring buffer size for slow log entries

################## LATENCY MONITOR ##################
latency-monitor-threshold 100     # track events >100ms for `LATENCY` command diagnostics

################## TLS (recommended given your internal mTLS/PKI setup) ##################
# port 0                          # disable plaintext port entirely once TLS confirmed working
# tls-port 6379
# tls-cert-file /etc/redis/certs/redis.crt
# tls-key-file /etc/redis/certs/redis.key
# tls-ca-cert-file /etc/redis/certs/ca.crt
# tls-auth-clients yes            # require client cert — mutual TLS, fits your existing mTLS infra
```

---

## 5. Production Checklist

- [ ] `requirepass` / ACL set — never blank in prod
- [ ] `bind` scoped to internal interface, not public
- [ ] `protected-mode yes`
- [ ] Dangerous commands renamed/disabled (`FLUSHALL`, `FLUSHDB`, `CONFIG`, `SHUTDOWN`, `DEBUG`)
- [ ] `maxmemory` matched to workload + eviction policy (`allkeys-lru` for cache, `noeviction` if Redis is source-of-truth)
- [ ] AOF enabled if durability matters (`appendfsync everysec` = good balance)
- [ ] Firewall: only app subnet + replica IPs allowed on 6379
- [ ] `vm.overcommit_memory = 1` set (avoid bgsave fork failure under memory pressure)
- [ ] Transparent Hugepages (THP) disabled — causes latency spikes
- [ ] File descriptor limit raised via systemd override
- [ ] Monitoring wired: `INFO`, slowlog, `redis-cli --latency`
- [ ] TLS/mTLS enabled instead of plaintext, given your existing PKI

---

## 6. OS-Level Tuning

```bash
# Disable Transparent Hugepages
echo never > /sys/kernel/mm/transparent_hugepage/enabled

# Memory overcommit — required for safe background saves
sysctl vm.overcommit_memory=1
echo 'vm.overcommit_memory = 1' >> /etc/sysctl.conf

# Raise file descriptor limit for the service
sudo systemctl edit redis
# add:
# [Service]
# LimitNOFILE=65536
```

---

## 7. Resource Allocation Sizing

Redis is single-threaded for command execution (I/O threading in 8.x helps network I/O, not command logic) — so more cores help mainly with OS overhead, background AOF/RDB writes, and multiple instances, not raw single-instance throughput.

### 2 Core / 4GB RAM — small/medium workload

```conf
maxmemory 2560mb          # ~65% of total RAM — leaves headroom for OS, fork() copy-on-write during bgsave/AOF rewrite, and client buffers
maxmemory-policy allkeys-lru
io-threads 2               # match core count for network I/O parallelism
io-threads-do-reads yes
tcp-backlog 511
maxclients 5000
```
Fits: single-app cache, session store, small pub/sub, low-to-moderate write rate.
Risk: bgsave/AOF rewrite on a nearly-full dataset can spike memory 2x briefly (COW) — don't push `maxmemory` past ~65% on small RAM boxes.

### 4 Core / 8GB RAM — general production workload

```conf
maxmemory 5120mb           # ~65% of total RAM, same COW-headroom logic, more absolute slack
maxmemory-policy allkeys-lru
io-threads 4
io-threads-do-reads yes
tcp-backlog 1024
maxclients 10000
```
Fits: moderate-traffic API cache, primary/replica pair, Kafka-adjacent dedup/state store, session store for larger user base.
Room for: AOF + RDB both enabled without tight memory pressure; more concurrent clients before fd/backlog tuning needed.

### General sizing rule of thumb

| Factor | Guidance |
|---|---|
| `maxmemory` vs total RAM | Cap at 60–70% of host RAM. Redis fork()'s for RDB/AOF rewrite — copy-on-write can transiently double memory use on high-churn datasets. |
| Cores | Matter for `io-threads`, TLS handshake overhead, and running multiple Redis instances per host — not for single-command execution speed. |
| Swap | Disable, or set `vm.swappiness=1`. Swapped Redis = latency cliff. |
| Persistence overhead | AOF+RDB together cost extra disk I/O and periodic CPU/memory spikes during rewrite — factor into core/RAM headroom, not just steady-state load. |
| Network | 1 Redis instance rarely saturates 1Gbps, but check `repl-backlog-size` and replica count if replicating across DCs. |
