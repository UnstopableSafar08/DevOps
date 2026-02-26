# Keepalived + HAProxy High Availability Setup

Production-ready Keepalived VRRP configuration for HAProxy using **unicast VRRP** with fast, stable failover.

---

## Topology

| Role   | Hostname   | IP              |
|--------|------------|-----------------|
| MASTER | extlb-01   | 10.150.160.30   |
| BACKUP | extlb-02   | 10.150.160.31   |
| VIP    | ext-lb-VIP | 10.150.160.32   |

- VRRP mode: **Unicast**
- Failover trigger: **HAProxy health check**

---

## Design Decisions

### Why Unicast VRRP
- Multicast is often blocked in DC / cloud networks
- Predictable peer communication
- Easier firewall control

| Topic | Multicast | Unicast |
|---|---|---|
| How it works | Sends heartbeats to group address `224.0.0.18` | Sends heartbeats directly to peer IP `10.150.160.31` |
| Who receives the heartbeat | Every device on the subnet | Only the peer node |
| Requires multicast support | Yes | No |
| Works in cloud networks (AWS, Azure) | No | Yes |
| Works in VMware / virtual switches | Often blocked | Yes |
| Works in datacenter networks | Often blocked | Yes |
| Firewall control | Harder, subnet-wide | Easy, only between two IPs |
| Predictability | Less predictable | Fully predictable |
| Configuration complexity | Simpler | Slightly more explicit |
| Production safe | Not always | Yes |

### Best Practices Applied
- No `killall -0 haproxy`
- HAProxy health verified via `systemctl`
- `nopreempt` enabled on BACKUP to avoid traffic flaps
- VIP assigned as `/32` for clean ARP behavior

---

## HAProxy Health Check Script

Create this script on **both nodes**:

```bash
cat << 'EOF' > /etc/keepalived/chk_haproxy.sh
#!/bin/bash
systemctl is-active --quiet haproxy
EOF

chmod +x /etc/keepalived/chk_haproxy.sh
```

---

## Keepalived Configuration

### MASTER — extlb-01 (10.150.160.30)

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
    # preempt_delay 10 # wait 10 sec to get VIP
    
    unicast_src_ip 10.150.160.30    # This node's own IP (MASTER)
    unicast_peer {
        10.150.160.31               # BACKUP node IP — send heartbeats directly here
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

### BACKUP — extlb-02 (10.150.160.31)

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
    # nopreempt # if this enable, the VIP does not move to MASTER automatically.

    unicast_src_ip 10.150.160.31    # This node's own IP (MASTER)
    unicast_peer {
        10.150.160.30               # BACKUP node IP — send heartbeats directly here
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

## VRRP Defaults and Recommended Values

| Parameter           | Default   | Acceptable Range  | Recommended (Prod)  | Notes |
|---------------------|-----------|-------------------|---------------------|------|
| advert_int          | 1         | 1–3 sec           | 1                   | Failover ≈ 3 × advert_int |
| priority            | 100       | 1–254             | 101 / 100           | Higher wins |
| virtual_router_id   | None      | 1–255             | 50                  | Must match |
| auth_type           | None      | PASS              | PASS                | Always enable |
| auth_pass           | None      | 1–8 chars         | ******              | Plaintext |
| script interval     | 1         | 1–5 sec           | 2                   | Health check |
| fall                | 1         | 1–10              | 2                   | Failures before DOWN |
| rise                | 1         | 1–10              | 1                   | Successes before UP |
| nopreempt           | Disabled  | Enabled/Disabled  | Enabled (Backup)    | Prevents VIP flap |
| VRRP mode           | Multicast | Unicast/Multicast | Unicast             | Prod safe |
| virtual_ipaddress   | None      | Valid IP          | VIP/32              | Clean ARP |
| interface           | None      | Valid NIC         | ens192              | Must exist |

---

## Failover Behavior

1. Normal  
   - extlb-01 owns the VIP

2. HAProxy stops on MASTER  
   - Health check fails  
   - Priority drops  
   - BACKUP takes VIP (~2–3 seconds)

3. MASTER recovers  
   - VIP does not move back (nopreempt)  
   - No traffic interruption

4. Manual failback  

```bash
systemctl restart keepalived
```

---

## Validation

```bash
ip a show ens192 | grep 10.150.160.32
journalctl -u keepalived -f
```

---

## Production Notes

- Allow VRRP protocol 112 or required unicast traffic in firewalld
- Both nodes must have:
  - Same virtual_router_id
  - Same auth_pass
  - Same network interface name
- Test failover before production cutover




## Preempt Behavior Scenarios

| Scenario | Config | MASTER Down | MASTER Recovers | Disruptions | Best For |
|---|---|---|---|---|---|
| **Default (Preempt)** | No `nopreempt`, no `preempt_delay` | VIP moves to BACKUP | VIP moves back to MASTER immediately | 2x | Dev/test environments |
| **Preempt Delay** | `preempt_delay 30` on MASTER | VIP moves to BACKUP | VIP moves back after 30s grace period | 2x (delayed) | When you want auto failback with a buffer |
| **No Preempt (BACKUP only)** | `nopreempt` on BACKUP only | VIP moves to BACKUP | VIP moves back to MASTER (BACKUP won't fight back) | 2x | Misleading — same as default |
| **No Preempt (both nodes)** | `nopreempt` on both | VIP moves to BACKUP | VIP stays on BACKUP | 1x | Production recommended |
| **No Preempt + Manual Failback** | `nopreempt` on both + `systemctl restart keepalived` on BACKUP | VIP moves to BACKUP | VIP returns to MASTER only on manual trigger | Controlled | Production with change control |

---

## Key Takeaway

| Priority | `nopreempt` on MASTER | `nopreempt` on BACKUP | Result |
|---|---|---|---|
| 101 / 100 | No | No | VIP always follows highest priority |
| 101 / 100 | No | Yes | VIP still returns to MASTER (MASTER forces it) |
| 101 / 100 | Yes | No | VIP stays on BACKUP |
| 101 / 100 | Yes | Yes | VIP stays wherever it is — safest production config |

---

## Status

RFC 5798 aligned, production safe, and flap resistant.
