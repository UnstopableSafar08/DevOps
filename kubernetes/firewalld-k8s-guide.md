# Firewalld with Kubernetes: Quick Setup Guide

Minimal, working config for running `firewalld` enabled on kubeadm-based clusters (tested: RHEL 9, Flannel CNI, kube-proxy iptables mode).

## The Core Problem

NodePort/pod traffic often needs to be **forwarded** across nodes over the CNI overlay (e.g. Flannel VXLAN). Firewalld's default zone target is `REJECT` on the `FORWARD` chain. Opening ports only affects the `INPUT` chain — it does nothing for forwarded/DNAT'd traffic. This is why a NodePort might work when the pod is local to the node you're hitting, but fail with "No route to host" when the pod lives elsewhere.

## Required Config (run on every node)

**1. Put CNI interfaces in the `trusted` zone**

```bash
firewall-cmd --permanent --zone=trusted --add-interface=cni0
firewall-cmd --permanent --zone=trusted --add-interface=flannel.1
```
> Adjust interface names for your CNI (Calico: `cali+`/`vxlan.calico`, etc).

**2. Enable masquerading** (needed for SNAT on pod-to-external traffic)

```bash
firewall-cmd --permanent --zone=public --add-masquerade
```

**3. Open required ports** — keep your main NIC (e.g. `ens192`) in `public` zone, not `trusted`, and scope ports explicitly:

```bash
# Control-plane only
firewall-cmd --permanent --zone=public --add-port=6443/tcp
firewall-cmd --permanent --zone=public --add-port=2379-2380/tcp
firewall-cmd --permanent --zone=public --add-port=10257/tcp
firewall-cmd --permanent --zone=public --add-port=10259/tcp

# All nodes
firewall-cmd --permanent --zone=public --add-port=10250/tcp
firewall-cmd --permanent --zone=public --add-port=10256/tcp
firewall-cmd --permanent --zone=public --add-port=30000-32767/tcp
firewall-cmd --permanent --zone=public --add-port=30000-32767/udp
firewall-cmd --permanent --zone=public --add-port=8472/udp   # Flannel VXLAN
```

**4. Reload**

```bash
firewall-cmd --reload
```

## Sysctl Prerequisites (independent of firewalld)

```bash
cat <<EOF >/etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
sysctl --system
```

## Security Notes

- **Never** put your main/external-facing NIC in the `trusted` zone — it bypasses all port rules for that interface entirely.
- The NodePort range (`30000-32767`) is open to **anyone who can route to the node** once added to `public` with no source restriction. If NodePort should only be reachable internally or via a load balancer, scope it with a rich rule instead:
  ```bash
  firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="<ALLOWED_CIDR>" port port="30000-32767" protocol="tcp" accept'
  ```
- Avoid adding broad `source=` ranges (e.g. your whole node subnet) to the `trusted` zone unless you intend to bypass port filtering entirely for that range.
- Turn off `--set-log-denied=all` once debugging is done — it's verbose and only meant for troubleshooting.

## Verification

```bash
firewall-cmd --get-active-zones
firewall-cmd --zone=public --list-all
firewall-cmd --zone=trusted --list-all

# From another node, test the NodePort:
curl -I http://<node-ip>:<nodeport>
```

## Quick Checklist

- [ ] CNI interfaces (`cni0`, `flannel.1`, etc.) in `trusted` zone
- [ ] Masquerade enabled on `public`
- [ ] Required K8s ports open on `public` (scoped, not wildcard `trusted`)
- [ ] Main NIC stays in `public`, not `trusted`
- [ ] `net.ipv4.ip_forward` and `bridge-nf-call-iptables` = 1
- [ ] NodePort range restricted by source if external access isn't wanted
- [ ] `set-log-denied` off after debugging
