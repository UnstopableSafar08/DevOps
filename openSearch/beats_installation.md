# Guide: Installing Beats (Filebeat, Metricbeat, Heartbeat) via RPM on OpenSearch 3.4.0 for RHEL/Oracle Linux 9.6

## Prerequisites
- OpenSearch 3.4.0 on localhost:9200.
- Credentials: admin / openSearch@123#.
- HTTPS with self-signed cert (use -k for curl).

## Step 1: Download OSS Beats RPMs (Version 8.15.2)
```
wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-oss-8.15.2-x86_64.rpm
wget https://artifacts.elastic.co/downloads/beats/metricbeat/metricbeat-oss-8.15.2-x86_64.rpm
wget https://artifacts.elastic.co/downloads/beats/heartbeat/heartbeat-oss-8.15.2-x86_64.rpm
```

## Step 2: Install RPMs
```
sudo rpm -i filebeat-oss-8.15.2-x86_64.rpm
sudo rpm -i metricbeat-oss-8.15.2-x86_64.rpm
sudo rpm -i heartbeat-oss-8.15.2-x86_64.rpm
```

## Step 3: Configure Each Beat
Edit `/etc/<beat>/<beat>.yml` (replace `<beat>`):
```
output.elasticsearch:
  hosts: ["https://localhost:9200"]
  username: "admin"
  password: "openSearch@123#"
  ssl.verification_mode: none
```
Enable modules as needed (e.g., `metricbeat modules enable system`).

## Step 4: Setup and Start
For each:
```
sudo <beat> setup
sudo systemctl start <beat>
sudo systemctl enable <beat>
```

## Verification
```
curl -X GET https://localhost:9200/_cat/indices -u admin:openSearch@123# -k
```

## Troubleshooting
- Check logs: `/var/log/<beat>/<beat>.log`.
- SSL issues: Verify config.
- Compatibility: Use OSS Beats 8.x for OpenSearch 3.x.
