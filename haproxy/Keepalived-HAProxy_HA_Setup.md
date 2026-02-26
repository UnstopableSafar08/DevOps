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

---

## Status

RFC 5798 aligned, production safe, and flap resistant.
