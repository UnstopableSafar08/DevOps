# MinIO Migration Guide: CentOS 7 to Oracle Linux 9.7

This guide provides a comprehensive workflow for migrating a legacy MinIO instance (RELEASE.2020-02-27T00-23-05Z) from CentOS 7 to Oracle Linux 9.7.

---

## Prerequisites & Environment Summary

Source OS: CentOS 7  
Destination OS: Oracle Linux 9.7  
MinIO Version: RELEASE.2020-02-27T00-23-05Z  
Data Root: /minio  
Execution User: root  

---

## Recommended Server Resource Allocation

For a production deployment running on a server with 4 CPU cores and 8 GB RAM, the following resource allocations and limits are recommended.

| Resource | Recommended Value | Description |
|---|---|---|
| CPU | 4 vCPU | Dedicated CPU cores for object storage operations |
| Memory | 8 GB RAM | Allows caching and metadata operations |
| File Descriptors (soft limit) | 65536 | Required for high concurrent object access |
| File Descriptors (hard limit) | 131072 | Prevents descriptor exhaustion |
| Max Open Files | 65536 | Required for large bucket workloads |
| TasksMax | infinity | Prevents process thread limitation |
| Network Ports | 9000/tcp | MinIO API endpoint |
| Disk Type | SSD recommended | Improves object read/write latency |

### Apply File Descriptor Limits

Edit the following file:

```
/etc/security/limits.conf
```

```
root soft nofile 65536
root hard nofile 131072
```

Verify limits.

```bash
ulimit -n
```

---

## Source System Preparation (CentOS)

Before transferring data, identify the current configuration and credentials.

### Identify Credentials & Aliases

Retrieve the current Access and Secret keys used by the MinIO client.

```bash
mc config host list
```

Locate the `myminio` alias and record the AccessKey and SecretKey.

### Stop MinIO Service

Stopping the service ensures data consistency during migration.

```bash
systemctl stop minio
```

---

## File and Configuration Transfer

Multiple transfer approaches can be used depending on dataset size, network stability, and tooling availability. Choose the method that best fits the environment.

```bash
# rsync - incremental sync with compression and progress (recommended)
rsync -avzP -e "ssh -p 32121" root@10.13.222.102:/minio /minio
rsync -avzP -e "ssh -p 32121" root@10.13.222.102:/etc/default/minio /etc/default/
rsync -avzP -e "ssh -p 32121" root@10.13.222.102:/etc/systemd/system/minio.service /etc/systemd/system/
rsync -avzP -e "ssh -p 32121" root@10.13.222.102:/root/.mc /root/
rsync -avzP -e "ssh -p 32121" root@10.13.222.102:/root/.minio /root/

# scp - secure copy over SSH
scp -r -P 32121 root@10.13.222.102:/minio /
scp -P 32121 root@10.13.222.102:/etc/default/minio /etc/default/
scp -P 32121 root@10.13.222.102:/etc/systemd/system/minio.service /etc/systemd/system/
scp -r -P 32121 root@10.13.222.102:/root/.mc /root/
scp -r -P 32121 root@10.13.222.102:/root/.minio /root/

# sftp - interactive secure file transfer
sftp -P 32121 root@10.13.222.102

# tar over SSH - archive and stream directly
ssh -p 32121 root@10.13.222.102 "tar czf - /minio" | tar xzf - -C /

# dd over SSH - low-level block copy
ssh -p 32121 root@10.13.222.102 "dd if=/dev/sda" | dd of=/dev/sda

# nc (netcat) - raw fast transfer on local network
nc -l 9999 | tar xzf -                          # receiver
tar czf - /minio | nc 10.13.222.102 9999        # sender

# wget - pull files over HTTP/FTP
wget -r -np http://10.13.222.102/minio/

# curl - transfer with URL syntax
curl -u user:pass ftp://10.13.222.102/minio/ -O

# rclone - cloud and remote storage sync
rclone sync /minio remote:bucket --progress

# lftp - advanced FTP/SFTP with mirror support
lftp -e "mirror -R /minio /remote/minio" sftp://root@10.13.222.102
```

---

## Destination System Setup (Oracle Linux 9.7)

### Disable SELinux

Oracle Linux 9.7 uses strict SELinux policies which may block older MinIO binaries.

```bash
setenforce 0
sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
```

---

### Verify Binary Compatibility

Ensure the MinIO binary works with the system GLIBC version.

```bash
/usr/local/bin/minio --version
```

---

## Configuration & Permissions

### Systemd Service File

Ensure the following file exists.

```
/etc/systemd/system/minio.service
```

Service configuration.

```ini
[Unit]
Description=MinIO
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
WorkingDirectory=/minio
User=root
Group=root
ProtectProc=invisible
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES
Restart=always
RestartSec=5
LimitNOFILE=65536
TasksMax=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
```

---

### Fix Ownership and Permissions

```bash
chown -R root:root /minio
chmod -R 700 /minio
```

---

## Service Activation

Reload systemd and start the MinIO service.

```bash
systemctl daemon-reload
systemctl enable minio
systemctl start minio
```

Verify service status.

```bash
systemctl status minio
```

---

## IAM and Bucket Verification

Register the MinIO client alias.

```bash
mc config host add myminio http://localhost:9000 <ACCESS_KEY> <SECRET_KEY>
```

Verify buckets.

```bash
mc ls myminio
```

Verify users.

```bash
mc admin user list myminio
```

Verify policies.

```bash
mc admin policy list myminio
```

---

## Troubleshooting

Empty user list.

Ensure the metadata directory exists.

```
/minio/.minio.sys
```

This directory stores IAM users, policies, and metadata.

Service startup failure.

```bash
journalctl -u minio -f
```

Network access configuration.

```bash
firewall-cmd --permanent --add-port=9000/tcp
firewall-cmd --reload
```

---

## Summary of Migrated Paths

| Path | Description |
|---|---|
| /minio/ | Object data and `.minio.sys` metadata |
| /etc/default/minio | Environment variables |
| /etc/systemd/system/minio.service | Systemd unit configuration |
| /root/.mc | MinIO client configuration |
| /root/.minio/certs | SSL certificates if configured |
