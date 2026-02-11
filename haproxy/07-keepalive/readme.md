---

## Topology (Clear Mapping).

| Role   | Hostname   | IP              |
| ------ | ---------- | --------------- |
| MASTER | extlb-01   | `10.150.160.30` |
| BACKUP | extlb-02   | `10.150.160.31` |
| VIP    | ext-lb-VIP | `10.150.160.32` |

You are using **unicast VRRP**, which is correct for most data-center / cloud networks.

---

## Recommended Improvements (Important)

Before jumping to configs, two **best-practice fixes**:

1. **Do NOT use `killall -0 haproxy`**

   * It can give false positives if multiple processes exist.
   * Use `pidof` or `systemctl is-active`.

2. **Use `nopreempt` on BACKUP**

   * Prevents flapping when MASTER comes back online.

---

## HAProxy Health Check Script (Recommended)

Create once on **both nodes**:

```bash
cat << 'EOF' > /etc/keepalived/chk_haproxy.sh
#!/bin/bash
systemctl is-active --quiet haproxy
EOF

chmod +x /etc/keepalived/chk_haproxy.sh
```

---

## MASTER: extlb-01 (`10.150.160.30`)

```conf
vrrp_script chk_haproxy {
    script "/etc/keepalived/chk_haproxy.sh"
    interval 2
    fall 2
    rise 1
}

vrrp_instance LB_VIP {
    state MASTER
    interface ens192
    virtual_router_id 50
    priority 101
    advert_int 1

    unicast_src_ip 10.150.160.30
    unicast_peer {
        10.150.160.31
    }

    authentication {
        auth_type PASS
        auth_pass 12345678
    }

    virtual_ipaddress {
        10.150.160.32/32
    }

    track_script {
        chk_haproxy
    }
}
```

---

## BACKUP: extlb-02 (`10.150.160.31`)

```conf
vrrp_script chk_haproxy {
    script "/etc/keepalived/chk_haproxy.sh"
    interval 2
    fall 2
    rise 1
}

vrrp_instance LB_VIP {
    state BACKUP
    interface ens192
    virtual_router_id 50
    priority 100
    advert_int 1
    nopreempt

    unicast_src_ip 10.150.160.31
    unicast_peer {
        10.150.160.30
    }

    authentication {
        auth_type PASS
        auth_pass 12345678
    }

    virtual_ipaddress {
        10.150.160.32/32
    }

    track_script {
        chk_haproxy
    }
}
```
---

The **default vs acceptable vs recommended values** for **Keepalived VRRP**.


### Keepalived VRRP – Default & Acceptable Values (Quick Reference)

| Parameter           | Default   | Acceptable Range  | Recommended (Prod)  | Notes                       |
| ------------------- | --------- | ----------------- | ------------------- | --------------------------- |
| `advert_int`        | `1`       | `1–3` sec         | `1`                 | Failover ≈ `3 × advert_int` |
| `priority`          | `100`     | `1–254`           | `101 (M) / 100 (B)` | Higher wins                 |
| `virtual_router_id` | None      | `1–255`           | `50`                | Must match on both nodes    |
| `auth_type`         | None      | `PASS`            | `PASS`              | Always enable               |
| `auth_pass`         | None      | `1–8 chars`       | `******`            | Plaintext only              |
| `interval` (script) | `1`       | `1–5` sec         | `2`                 | Health-check frequency      |
| `fall`              | `1`       | `1–10`            | `2`                 | Failures before DOWN        |
| `rise`              | `1`       | `1–10`            | `1`                 | Successes before UP         |
| `nopreempt`         | Disabled  | Enabled/Disabled  | Enabled (Backup)    | Prevents VIP flap           |
| `unicast`           | Multicast | Unicast/Multicast | Unicast             | Preferred in prod           |
| `virtual_ipaddress` | None      | Valid IP          | `VIP/32`            | Clean ARP behavior          |
| `interface`         | None      | Valid NIC         | `enp0s3`            | Must exist on both          |

---

### Legend

* **M** = Master
* **B** = Backup

This table reflects **safe defaults**, **RFC-aligned behavior**, and **real-world production usage** for HAProxy + Keepalived.

---

## How Failover Works (Exactly)

1. **Normal**

   * extlb-01 owns `10.150.160.32`
2. **HAProxy stops on MASTER**

   * `chk_haproxy` fails
   * Priority drops
   * BACKUP takes VIP in ~2 seconds
3. **MASTER comes back**

   * VIP **does NOT move back** (because of `nopreempt`)
   * Zero traffic flap
4. **Manual switch back**

   ```bash
   systemctl restart keepalived
   ```

---

## Validation Commands

```bash
ip a show enp0s3 | grep 10.150.160.32
journalctl -u keepalived -f
```

---

## Production Notes (Very Important)

* Ensure **firewalld allows VRRP (protocol 112)** or explicitly allows unicast traffic
* Both nodes must use:

  * Same `virtual_router_id`
  * Same `auth_pass`
* Interface name must be **identical on both nodes**

---

If you want, next we can:

* Add **email / webhook alerts**
* Implement **scripted maintenance mode**
* Integrate **Keepalived + HAProxy stats-based failover**
* Review **best failover testing strategy for prod**

Just say the word, Boss.
