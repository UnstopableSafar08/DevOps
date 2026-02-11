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

### FYI : If You used a nginx as a LB.
```bash
cat << 'EOF' > /etc/keepalived/chk_haproxy.sh
#!/bin/bash
systemctl is-active --quiet nginx
EOF

chmod +x /etc/keepalived/chk_nginx.sh
```

---

## Keepalived Configuration

### MASTER — extlb-01 (10.150.160.30)

```conf
vrrp_script chk_health {
    script "/etc/keepalived/chk_haproxy.sh"
    # script "/etc/keepalived/chk_nginx.sh"
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
    preempt_delay 10 # MASTER must be healthy for 10 seconds then the VIP reclaim.

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
        chk_health
    }
}
```

---

### BACKUP — extlb-02 (10.150.160.31)

```conf
vrrp_script chk_health {
    script "/etc/keepalived/chk_haproxy.sh"
    # script "/etc/keepalived/chk_nginx.sh"
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
    # nopreempt    # VIP does not move back due to option - nopreempt

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
        chk_health
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
   - MASTER owns the VIP

2. HAProxy stops on MASTER  
   - Health check fails  
   - Priority drops  
   - BACKUP takes VIP (~2–3 seconds)

3. MASTER recovers  
    - MASTER sees it has higher priority (101 > 100)
    - MASTER reclaims VIP
    - BACKUP drops VIP
      Failback time: Approximately 1–3 seconds (based on advert_int)
    
    ***Important Production Warning.***
    Automatic failback from BACKUP to MASTER can cause:    
    - Brief traffic interruption
    - TCP resets
    - Session drops (if not using stick tables or shared state)
    - Double failover if MASTER is unstable
    - This is why many production environments intentionally use nopreempt.

    **If You Want Safer Automatic Failback.**

    You can delay failback using:
    Add this to MASTER:
    ```bash
    preempt_delay 10
    ```
    **That means:**
    - MASTER must be healthy for 10 seconds
    - Then it reclaims VIP
    - This prevents flap storms.
    
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
```bash
firewall-cmd --permanent --add-protocol=vrrp
# firewall-cmd --permanent --add-protocol=112
firewall-cmd --reload
```
- Both nodes must have:
  - Same virtual_router_id
  - Same auth_pass
  - Same network interface name
- Test failover before production cutover

---

## Status

RFC 5798 aligned, production safe, and flap resistant.
