# Production Server Troubleshooting Guide

Quick-reference for diagnosing prod Linux issues. Check top-to-bottom: system → resource → service → network.

---

## 1. First 60 Seconds — Triage

```bash
uptime                  # load avg
w                        # who's on, load
dmesg -T | tail -50      # kernel errors, OOM kills
journalctl -p err -b     # errors since boot
last reboot              # unexpected restarts?
```

---

## 2. CPU

```bash
top -o %CPU              # or: htop
mpstat 1 5                # per-core, 5 samples
pidstat -p <PID> 1        # per-process CPU over time
ps -eo pid,ppid,cmd,%cpu --sort=-%cpu | head -20
```
**High load, low CPU%?** → check iowait (`vmstat 1`, col `wa`) — disk/IO bound, not CPU bound.

---

## 3. Memory

```bash
free -h
vmstat 1 5                # si/so columns = swapping = bad
ps -eo pid,cmd,%mem,rss --sort=-%mem | head -20
dmesg -T | grep -i "out of memory"   # OOM killer fired?
cat /proc/<PID>/status | grep -i vm  # per-process detail
```
**OOM killed a process?** `journalctl -k | grep -i "killed process"`

---

## 4. Disk / Filesystem

```bash
df -h                     # space per mount
df -i                     # inode exhaustion (silent killer)
du -sh /* 2>/dev/null | sort -rh | head -10   # biggest dirs
iostat -xz 1 5             # disk IO, %util, await
```
**df/du mismatch (disk full but du says less)?** → deleted-but-open files. See#8.

---

## 5. Network

```bash
ss -tulnp                  # listening ports + owning PID
ss -s                       # socket summary stats
netstat -antp | grep ESTABLISHED | wc -l    # conn count
ip -s link                  # errors/drops per NIC
ping -c4 <gateway/target>
traceroute <target>
mtr <target>                 # continuous trace + loss%
tcpdump -i eth0 host <ip> -n # live capture
```
**Port not reachable?** Check firewall: `iptables -L -n -v` or `firewall-cmd --list-all`

---

## 6. Service / Process Health

```bash
systemctl status <service>
systemctl --failed              # all failed units
journalctl -u <service> -f      # live logs
journalctl -u <service> --since "10 min ago"
ps aux | grep <process>
kill -0 <PID>                   # check process alive (no signal sent)
```

---

## 7. Application / Logs

```bash
tail -f /var/log/<app>/*.log
grep -i error /var/log/<app>/*.log | tail -50
find /var/log -mmin -15 -name "*.log"   # recently touched logs
journalctl --since "1 hour ago" -p warning
```

---

## 8. Deleted-but-Open Files (space leak)

```bash
# with lsof
lsof +L1 | grep deleted

# without lsof (pure /proc)
for pid in /proc/[0-9]*; do
  for fd in $pid/fd/*; do
    link=$(readlink "$fd" 2>/dev/null)
    [[ "$link" == *"(deleted)"* ]] && echo "$pid $fd -> $link"
  done
done 2>/dev/null
```
Fix: `systemctl restart <service>` or `> /proc/<PID>/fd/<FD>` to truncate without killing.

---

## 9. Load Spike / Zombie / Runaway Processes

```bash
ps aux | awk '$8=="Z"'          # zombies
ps -eo pid,ppid,stat,cmd | grep -w D    # uninterruptible sleep = stuck IO
pstree -p <PID>                 # process tree
kill -9 <PID>                   # last resort
```

---

## 10. Kubernetes / k3s (if applicable)

```bash
kubectl get pods -A --field-selector=status.phase!=Running
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns> --previous     # crashed container's last logs
kubectl top pod -n <ns>                    # if metrics-server present
kubectl get events -A --sort-by='.lastTimestamp' | tail -30
```

---

## 11. Certificates / TLS (mTLS environments)

```bash
openssl x509 -in cert.pem -noout -dates      # expiry check
openssl s_client -connect host:port -servername host </dev/null 2>/dev/null | openssl x509 -noout -dates
echo | openssl s_client -connect host:port 2>&1 | grep -i verify
```

---

## 12. Escalation Checklist (before paging / handing off)

- [ ] Captured `dmesg`, `journalctl -p err`, top offending process
- [ ] Noted exact timestamp of onset
- [ ] Checked recent deploys/changes (`git log`, Jenkins build history, config diffs)
- [ ] Confirmed scope: single node vs cluster-wide
- [ ] Ruled out upstream/downstream dependency (DB, Kafka, LB health)
- [ ] Saved relevant logs before rotation/restart wipes them

---

*Quick rule of thumb: CPU → `top`/`mpstat`. Memory → `free`/`vmstat`. Disk → `df`/`iostat`. Network → `ss`/`tcpdump`. Always confirm with `journalctl`/`dmesg` for kernel-level truth.*
