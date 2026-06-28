# curl_hop_check.sh

A bash script that repeatedly hits an HTTPS endpoint N times (default 100) and records **TLS handshake timing**, **HTTP status codes**, **connection errors**, and **per-hop timestamps** — all written to a timestamped output directory with a raw log and CSV file.

Built for diagnosing intermittent TLS flaps, connection timeouts, and latency spikes on production endpoints.

---

## Requirements

| Tool | Notes |
|------|-------|
| `bash` 4.0+ | Associative arrays required |
| `curl` | Any recent version |
| `awk` | Standard gawk/mawk |
| `date` | GNU coreutils (`date +%s%3N` for ms precision) |

> On CentOS/Oracle Linux: all present by default.  
> On macOS: install GNU coreutils via `brew install coreutils` and use `gdate`.

---

## Usage

```bash
chmod +x curl_hop_check.sh

# Default: 100 hops to the built-in URL
./curl_hop_check.sh

# Custom URL, 100 hops
./curl_hop_check.sh "https://your-endpoint.example.com/api/path"

# Custom URL + hop count
./curl_hop_check.sh "https://your-endpoint.example.com/api/path" 50

# With Bearer token auth
./curl_hop_check.sh "https://your-endpoint.example.com/api/path" 100 "eyJhbGci..."
```

### Arguments

| Position | Variable | Default | Description |
|----------|----------|---------|-------------|
| `$1` | `URL` | Built-in default URL | Target HTTPS endpoint |
| `$2` | `HOPS` | `100` | Number of curl requests to fire |
| `$3` | `AUTH_TOKEN` | _(empty)_ | Bearer token — injected as `Authorization: Bearer <token>` |

---

## What It Measures Per Hop

Each curl request captures the following via `-w` write-out format:

| Field | curl variable | Description |
|-------|--------------|-------------|
| `HTTP` | `%{http_code}` | HTTP response status code (`200`, `403`, `000` on failure) |
| `TCP` | `%{time_connect}` | Time to complete TCP 3-way handshake |
| `TLS` | `%{time_appconnect}` | Time until TLS handshake completed (includes TCP) |
| `TTFB` | `%{time_starttransfer}` | Time to first byte — server processing time visible here |
| `Total` | `%{time_total}` | Full round-trip time |
| `SSL verify` | `%{ssl_verify_result}` | `0` = cert OK, `19` = self-signed/untrusted CA, other = error code |
| `start` | `date` before curl | Wall clock timestamp when request was fired |
| `end` | `date` after curl | Wall clock timestamp when curl returned |
| `wall` | epoch ms diff | Actual elapsed ms including curl process overhead |

> **Why `wall` matters on failures:** when curl times out, `Total=0.000000s` — but `wall=15013ms` reveals the full 15-second blocking wait that the script experienced.

---

## Error Classification

When curl exits non-zero, the connection never completed. The script maps the exit code to a human-readable label:

| curl exit | Label | Meaning |
|-----------|-------|---------|
| `6` | `DNS_RESOLVE_FAIL` | Could not resolve hostname |
| `7` | `CONN_REFUSED` | Server actively refused TCP connection |
| `28` | `TIMEOUT` | Hit `--max-time` / `--connect-timeout` limit |
| `35` | `TLS_HANDSHAKE_ERROR` | SSL/TLS negotiation failed |
| `51` | `TLS_CERT_MISMATCH` | Cert hostname does not match |
| `52` | `EMPTY_RESPONSE` | Server closed connection with no response |
| `56` | `RECV_ERROR` | Failure receiving network data |
| `60` | `TLS_CERT_VERIFY_FAIL` | CA cert verification failed (`-s` skips this; use without `-s` to catch) |
| other | `CURL_ERR_N` | Unknown curl error N |

Failed hops are recorded as `HTTP=000` and are **excluded from timing averages** so they do not skew your min/max/avg stats.

---

## Output

### Terminal (live, color-coded)

```
╔══════════════════════════════════════════════════════╗
║           curl TLS + Status Hop Checker             ║
╚══════════════════════════════════════════════════════╝

  URL    : https://resources.geniustv.geniussystems.com.np
  Hops   : 100
  Timeout: 15s per hop
  Auth   :
  Output : ./curl_results_20260625_152230

Hop   1 | HTTP=200 | TCP= 0.016613s | TLS= 0.466508s | TTFB= 0.469260s | Total= 0.469299s | TLS_OK                | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=492ms
Hop   2 | HTTP=200 | TCP= 0.017179s | TLS= 0.021412s | TTFB= 0.024013s | Total= 0.024042s | TLS_OK                | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=32ms
Hop   3 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | TIMEOUT               | start=2026-06-25 15:22:30  end=2026-06-25 15:22:45  wall=15013ms
Hop   4 | HTTP=000 | TCP= 0.019800s | TLS= 0.000000s | TTFB= 0.000000s | Total= 15.001s   | TLS_HANDSHAKE_ERROR   | start=2026-06-25 15:22:45  end=2026-06-25 15:23:00  wall=15021ms
Hop   5 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | DNS_RESOLVE_FAIL      | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=9ms
Hop   6 | HTTP=000 | TCP= 0.003100s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.031200s | TLS_CERT_VERIFY_FAIL  | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=34ms
Hop   7 | HTTP=200 | TCP= 0.002900s | TLS= 0.007100s | TTFB= 0.009700s | Total= 0.009800s | TLS_WARN(19)          | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=18ms
Hop   8 | HTTP=403 | TCP= 0.003200s | TLS= 0.007600s | TTFB= 0.010300s | Total= 0.010400s | TLS_OK                | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=19ms
Hop   9 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | CONN_REFUSED          | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=5ms
Hop  10 | HTTP=200 | TCP= 0.003000s | TLS= 0.006900s | TTFB= 0.009300s | Total= 0.009400s | TLS_OK                | start=2026-06-25 15:23:00  end=2026-06-25 15:23:00  wall=17ms
...
```

**Color coding:**

| Color | Meaning |
|-------|---------|
| 🟢 Green | `2xx` — success |
| 🟡 Yellow | `3xx` — redirect |
| 🔴 Red | `4xx` / `5xx` — client/server error |
| 🟣 Magenta | `000` — connection or TLS failure (never reached server) |

### Summary Block

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Successful hops:       95 / 100
  Failed hops:           5 / 100

  HTTP Status Distribution:
    HTTP 200     : 94 / 100
    HTTP 403     : 1  / 100
    HTTP 000     : 5  / 100

  Connection / TLS Error Breakdown:
    TIMEOUT                    : 2 times
    TLS_HANDSHAKE_ERROR        : 1 times
    DNS_RESOLVE_FAIL           : 1 times
    CONN_REFUSED               : 1 times

  Timing (successful hops only):
    TCP Connect:     avg= 0.0072s   min= 0.0050s   max= 0.0620s
    TLS Handshake:   avg= 0.0905s   min= 0.0760s   max= 0.3710s
    TTFB:            avg= 0.1028s
    Total:           avg= 0.1028s

  Output files:
    Raw log : ./curl_results_20260625_152230/raw.log
    CSV     : ./curl_results_20260625_152230/summary.csv
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

> The error breakdown section only appears when at least one hop fails — on a clean run it is omitted.

---

## Output Files

Every run creates a timestamped directory: `./curl_results_YYYYMMDD_HHMMSS/`

```
curl_results_20260625_152230/
├── raw.log        # Human-readable log of every hop + summary
└── summary.csv    # Machine-readable CSV for import into Excel / Grafana / etc.
```

### raw.log

```
=== curl TLS + Status Hop Checker ===
URL    : https://resources.geniustv.geniussystems.com.np
Hops   : 100
Started: Wed Jun 25 15:22:30 +0545 2026

Hop   1 | HTTP=200 | TCP=0.016613s | TLS=0.466508s | TTFB=0.469260s | Total=0.469299s | TLS_OK                | reason=-                    | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=492ms
Hop   2 | HTTP=200 | TCP=0.017179s | TLS=0.021412s | TTFB=0.024013s | Total=0.024042s | TLS_OK                | reason=-                    | start=2026-06-25 15:22:30  end=2026-06-25 15:22:30  wall=32ms
Hop   3 | HTTP=000 | TCP=0.000000s | TLS=0.000000s | TTFB=0.000000s | Total=0.000000s | TIMEOUT               | reason=TIMEOUT              | start=2026-06-25 15:22:30  end=2026-06-25 15:22:45  wall=15013ms
...

=== SUMMARY ===
Completed : Wed Jun 25 15:24:01 +0545 2026
Successful: 95 / 100
Failed    : 5 / 100

HTTP Status Distribution:
  HTTP 200  : 94 / 100
  HTTP 403  : 1  / 100
  HTTP 000  : 5  / 100

Error Breakdown:
  TIMEOUT                       : 2
  TLS_HANDSHAKE_ERROR           : 1
  DNS_RESOLVE_FAIL              : 1
  CONN_REFUSED                  : 1

Timing (successful hops only):
  TCP Connect  : avg=0.0072s  min=0.0050s  max=0.0620s
  TLS Handshake: avg=0.0905s  min=0.0760s  max=0.3710s
  TTFB         : avg=0.1028s
  Total        : avg=0.1028s
```

### summary.csv

```csv
hop,status_code,error_reason,tcp_connect_s,tls_handshake_s,ttfb_s,total_s,ssl_verify_result,start_time,end_time,wall_time
1,200,-,0.016613,0.466508,0.469260,0.469299,0,2026-06-25 15:22:30,2026-06-25 15:22:30,492ms
2,200,-,0.017179,0.021412,0.024013,0.024042,0,2026-06-25 15:22:30,2026-06-25 15:22:30,32ms
3,000,TIMEOUT,0.000000,0.000000,0.000000,0.000000,28,2026-06-25 15:22:30,2026-06-25 15:22:45,15013ms
4,000,TLS_HANDSHAKE_ERROR,0.019800,0.000000,0.000000,15.001300,35,2026-06-25 15:22:45,2026-06-25 15:23:00,15021ms
5,000,DNS_RESOLVE_FAIL,0.000000,0.000000,0.000000,0.000000,6,2026-06-25 15:23:00,2026-06-25 15:23:00,9ms
6,403,-,0.003200,0.007600,0.010300,0.010400,0,2026-06-25 15:23:00,2026-06-25 15:23:00,19ms
```

CSV columns:

| Column | Description |
|--------|-------------|
| `hop` | Sequence number (1 to N) |
| `status_code` | HTTP status, or `000` for connection failures |
| `error_reason` | `-` on success, or the error label (e.g. `TIMEOUT`) |
| `tcp_connect_s` | TCP connect time in seconds |
| `tls_handshake_s` | TLS handshake completion time in seconds |
| `ttfb_s` | Time to first byte in seconds |
| `total_s` | Total curl time in seconds |
| `ssl_verify_result` | `0` = OK, other = OpenSSL/NSS error code |
| `start_time` | Wall clock timestamp before curl fired |
| `end_time` | Wall clock timestamp after curl returned |
| `wall_time` | Actual elapsed time in ms (reliable even on timeout) |

---

## Reading the Results

### Healthy endpoint (all 200, stable TLS)

```
Hop   1 | HTTP=200 | TCP= 0.003100s | TLS= 0.007400s | TTFB= 0.009800s | Total= 0.009900s | TLS_OK   | start=... wall=17ms
Hop   2 | HTTP=200 | TCP= 0.002900s | TLS= 0.006900s | TTFB= 0.009200s | Total= 0.009300s | TLS_OK   | start=... wall=16ms
```

TCP ~3ms, TLS ~7ms, steady — everything nominal.

### TLS resumption visible on hop 1

The first hop often shows a much higher TLS time (e.g. `0.4665s`) because it performs a **full TLS handshake**. Subsequent hops reuse the session via TLS session tickets, dropping to `~7ms`. If hop 1 is always slow and the rest are fast, this is expected behaviour — not a problem.

### Intermittent timeout

```
Hop  47 | HTTP=000 | TCP= 0.000000s | TLS= 0.000000s | TTFB= 0.000000s | Total= 0.000000s | TIMEOUT  | start=2026-06-25 15:22:47  end=2026-06-25 15:23:02  wall=15013ms
```

TCP never connected — possible upstream load balancer dropping connections, firewall conntrack table full, or server overloaded. The `start`/`end` timestamps let you correlate with server logs.

### TLS handshake failure (TCP OK, TLS failed)

```
Hop  83 | HTTP=000 | TCP= 0.019800s | TLS= 0.000000s | TTFB= 0.000000s | Total= 15.001s   | TLS_HANDSHAKE_ERROR | start=... wall=15021ms
```

TCP connected (`TCP=0.0198s`) but TLS negotiation failed and hit the timeout. Common causes: cipher mismatch, expired cert, SNI misconfiguration, or HAProxy SSL offload issue.

### Self-signed / internal CA cert (`TLS_WARN(19)`)

```
Hop   7 | HTTP=200 | TCP= 0.002900s | TLS= 0.007100s | TTFB= 0.009700s | Total= 0.009800s | TLS_WARN(19) | ...
```

The request succeeded (`HTTP=200`) but the cert could not be verified against the system CA bundle. Script uses `-sk` (skip verify) so it continues. This is normal when hitting endpoints signed by an internal CA (e.g. F1Soft Root CA) from a machine that does not have the internal CA installed in its trust store.

---

## Timeouts Configuration

Two timeout values are hard-coded at the top of the script:

```bash
TIMEOUT=15          # --max-time: total curl operation limit
CONNECT_TIMEOUT=10  # --connect-timeout: TCP connect limit
```

Adjust these for faster or slower networks before running.

---

## Tips

**Run in background for long hop counts:**
```bash
nohup ./curl_hop_check.sh "https://your-url.com" 500 > run.log 2>&1 &
```

**Watch live while logging:**
```bash
./curl_hop_check.sh "https://your-url.com" 100 | tee live_output.txt
```

**Import CSV into quick analysis:**
```bash
# Average TLS handshake across successful hops
awk -F',' 'NR>1 && $2 != "000" {sum+=$5; n++} END{printf "avg TLS: %.4fs\n", sum/n}' summary.csv

# Count timeouts
grep -c "TIMEOUT" summary.csv
```

---

## Author

Ocean (Sagar Malla) — DevOps / Infrastructure Engineer  
GitHub: [UnstopableSafar08](https://github.com/UnstopableSafar08)  
Blog: [blogs.sagarmalla.info.np](https://blogs.sagarmalla.info.np)
