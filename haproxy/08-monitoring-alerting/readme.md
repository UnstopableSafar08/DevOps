# HAProxy + Prometheus + Grafana + Alertmanager — Full VM Install (No Docker)

## Which tool installs on which server

This assumes the standard 2-box split — confirm this matches your actual
topology before following install steps, since every `<HAPROXY_HOST>`
placeholder and every `localhost` reference below depends on it:

| Tool | Installs on | Why |
|---|---|---|
| HAProxy | HAProxy server | Already there |
| HAProxy native Prometheus exporter (`:8404/metrics`, `USE_PROMEX=1`) | HAProxy server | Compiled into the HAProxy binary itself — not separate software |
| grok_exporter (`:9144/metrics`) | HAProxy server | Reads the local access log — that file only exists on this box |
| rsyslog rule (`local0.*` → access.log) | HAProxy server | Same reason — local log file |
| Prometheus | Prometheus+Grafana server | Central scraper, reaches out to `:8404` and `:9144` on the HAProxy server over the network |
| Grafana | Prometheus+Grafana server | Reads from local Prometheus (`localhost:9090`) |
| Alertmanager | Prometheus+Grafana server | Lives next to Prometheus, receives alerts over `localhost:9093` |
| prometheus-msteams | Prometheus+Grafana server | Receives from Alertmanager over `localhost:2000`, forwards to Teams |
| Backend servers | Nothing new | HAProxy already health-checks and routes to them |

Since Prometheus scrapes HAProxy across the network (not `localhost`),
confirm both ports are reachable from the Prometheus box's IP:

```bash
# run on the HAProxy server:
firewall-cmd --add-port=8404/tcp --permanent
firewall-cmd --add-port=9144/tcp --permanent
firewall-cmd --reload
```


Everything below runs as native systemd services on the VM. No containers,
no docker-compose. If you pulled `docker-compose.yml` from an earlier
session in this chat, ignore/delete it — this replaces that approach
entirely for Alertmanager and prometheus-msteams.

All commands assume Oracle Linux 9 / RHEL-family with systemd. Run as root
or with sudo. Replace `<HAPROXY_HOST>`, `yourdomain.com`,
`REPLACE-WITH-YOUR-WORKFLOWS-WEBHOOK-URL`, and SMTP creds throughout with
your real values before starting anything.

---

## Contents / install order

1. Prometheus (binary + systemd)
2. HAProxy config additions (metrics endpoint + logging)
3. Prometheus scrape config + alert rules (down + slow)
4. grok_exporter (binary + systemd) — per-URI metrics
5. Alertmanager (binary + systemd)
6. prometheus-msteams (binary + systemd) — Teams delivery
6.5. Enhanced email + Teams card templates (optional)
7. Grafana (repo install + systemd, likely already have this)
8. Grafana dashboard import
9. End-to-end test sequence
10. What's native vs. what needs extra tooling — scope honesty
11. Troubleshooting

---

## 1. Prometheus — binary install + systemd

Skip this whole section if you already have Prometheus running (per your
existing Grafana/Prometheus observability stack) — just jump to section 3
and merge the scrape config in.

```bash
# Dedicated user, no login shell
useradd --no-create-home --shell /sbin/nologin prometheus

mkdir -p /etc/prometheus /var/lib/prometheus /etc/prometheus/rules
chown prometheus:prometheus /etc/prometheus /var/lib/prometheus /etc/prometheus/rules

cd /tmp
curl -LO https://github.com/prometheus/prometheus/releases/download/v3.0.0/prometheus-3.0.0.linux-amd64.tar.gz
tar xvf prometheus-3.0.0.linux-amd64.tar.gz
cd prometheus-3.0.0.linux-amd64

cp prometheus promtool /usr/local/bin/
chown prometheus:prometheus /usr/local/bin/prometheus /usr/local/bin/promtool

cp -r consoles/ console_libraries/ /etc/prometheus/
chown -R prometheus:prometheus /etc/prometheus

# Minimal starting prometheus.yml — section 3 below adds the real scrape config
cat > /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF
chown prometheus:prometheus /etc/prometheus/prometheus.yml
```

Check version before pulling — v3.0.0 above is a placeholder, confirm
current at `https://github.com/prometheus/prometheus/releases` and swap the
URL/version string accordingly.

```ini
# /etc/systemd/system/prometheus.service
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/var/lib/prometheus/ \
    --web.console.templates=/etc/prometheus/consoles \
    --web.console.libraries=/etc/prometheus/console_libraries \
    --web.listen-address=0.0.0.0:9090
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now prometheus
systemctl status prometheus
curl -s localhost:9090/-/healthy
```

---

## 2. HAProxy config additions

Merge into your existing `/etc/haproxy/haproxy.cfg`:

```
global
    log 127.0.0.1:514 local0
    stats socket /run/haproxy/admin.sock mode 660 level admin

defaults
    mode http
    log global
    # Exact format matters — grok_exporter (step 4) parses Tq/Tw/Tc/Tr/Tt
    # (queue/wait/connect/response/total time, all ms) by position.
    option httplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s

# Prometheus native exporter — frontend/backend/server metrics
frontend prometheus
    bind *:8404
    mode http
    http-request use-service prometheus-exporter if { path /metrics }
    no log

# Your real traffic frontends stay as-is. Just confirm each one inherits
# `log global` + `option httplog` from defaults above — don't override with
# `no log` on those or you lose the access-log data step 4 needs.
```

Validate and reload:

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl reload haproxy
curl -s localhost:8404/metrics | head -30
```

Confirm rsyslog is actually writing to a flat file (needed for step 4) —
path varies by host, check your own `/etc/rsyslog.d/` for the `local0.*`
rule rather than assume a default. If you don't already have this, add:

```
# /etc/rsyslog.d/haproxy.conf
local0.*    /var/log/haproxy/access.log
```

```bash
systemctl restart rsyslog
tail -f /var/log/haproxy/access.log   # generate some traffic, confirm lines appear, Ctrl+C
```

Don't assume the path — run `grep -r 'local0' /etc/rsyslog.d/
/etc/rsyslog.conf` on your own box and use whatever it actually returns in
step 4's config below.

---

## 3. Prometheus scrape config + alert rules

Merge into `/etc/prometheus/prometheus.yml` (replacing the minimal version
from step 1 if you built Prometheus fresh):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'haproxy'
    scrape_interval: 10s
    static_configs:
      - targets: ['<HAPROXY_HOST>:8404']

  - job_name: 'haproxy-uri'
    scrape_interval: 10s
    static_configs:
      - targets: ['<HAPROXY_HOST>:9144']       # grok_exporter, step 4

rule_files:
  - /etc/prometheus/rules/haproxy-down-alerts.yml
  - /etc/prometheus/rules/haproxy-slow-alerts.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

Drop these two rule files into `/etc/prometheus/rules/` (already built —
files `03-haproxy-down-alerts.yml` and `04-haproxy-slow-alerts.yml` from
earlier in this conversation, content reproduced here for completeness):

```yaml
# /etc/prometheus/rules/haproxy-down-alerts.yml
groups:
  - name: haproxy-down-alerts
    rules:
      - alert: HAProxyServerDown
        expr: haproxy_server_status{state="DOWN"} == 1
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Server {{ $labels.server }} in backend {{ $labels.proxy }} is DOWN"
          description: "Health check failing 30s+ for {{ $labels.server }} ({{ $labels.proxy }})."

      - alert: HAProxyBackendNoActiveServers
        expr: haproxy_backend_active_servers == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Backend {{ $labels.proxy }} has ZERO active servers — total outage"
          description: "No server in {{ $labels.proxy }} can serve traffic."

      - alert: HAProxyProcessDown
        expr: up{job="haproxy"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Prometheus can't scrape HAProxy on {{ $labels.instance }}"
          description: "Either HAProxy is down or the exporter frontend (8404) is unreachable — different from a backend-server alert, this means the LB itself may be gone."
```

```yaml
# /etc/prometheus/rules/haproxy-slow-alerts.yml
#
# Note on precision: the *_response_time_average_seconds metrics are running
# AVERAGES HAProxy computes itself, not percentiles — good for "this backend
# got slow," not precise for one-off spikes. Real percentiles come from
# grok_exporter's histogram (step 4), not these.
groups:
  - name: haproxy-slow-alerts
    rules:
      - alert: HAProxyBackendSlowResponse
        expr: haproxy_backend_response_time_average_seconds > 2
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Backend {{ $labels.proxy }} average response time > 2s"
          description: "Currently {{ $value }}s average. Sustained 1m+."

      - alert: HAProxyServerSlowResponse
        expr: haproxy_server_response_time_average_seconds > 2
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Server {{ $labels.server }} ({{ $labels.proxy }}) average response time > 2s"
          description: "Currently {{ $value }}s. Sustained 1m+."

      - alert: HAProxyBackendQueueBuildup
        expr: haproxy_backend_current_queue > 20
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Backend {{ $labels.proxy }} has {{ $value }} requests queued"
          description: "Servers may still show UP while queue grows — often the earlier signal before an actual DOWN. Investigate before it escalates."
```

`> 2s` and `> 20` are starting points, not measured-for-you numbers — tune
after watching real traffic for a week.

```bash
chown -R prometheus:prometheus /etc/prometheus/rules
promtool check config /etc/prometheus/prometheus.yml
promtool check rules /etc/prometheus/rules/*.yml
systemctl reload prometheus
# Confirm in browser or curl: http://localhost:9090/rules — both groups green
```

---

## 4. grok_exporter — per-URI metrics (binary + systemd)

HAProxy's native exporter does NOT break metrics down by URL path — only
per-proxy/per-server. Per-URI data lives in the access log, not the stats
socket. grok_exporter reads that log and turns it into real Prometheus
series, including a proper histogram (so you get actual p95/p99, unlike the
average-only native metrics).

```bash
useradd --no-create-home --shell /sbin/nologin grok_exporter
mkdir -p /opt/grok_exporter
cd /tmp
curl -LO https://github.com/fstab/grok_exporter/releases/download/v1.0.0.RC5/grok_exporter-1.0.0.RC5.linux-amd64.zip
unzip grok_exporter-1.0.0.RC5.linux-amd64.zip
cp -r grok_exporter-1.0.0.RC5.linux-amd64/* /opt/grok_exporter/
chown -R grok_exporter:grok_exporter /opt/grok_exporter
```

Confirm current release version at
`https://github.com/fstab/grok_exporter/releases` before pulling — the
above is a placeholder.

Config file (already built earlier — `05-grok-exporter-config.yml` — full
content here for completeness):

```yaml
# /opt/grok_exporter/config.yml
global:
    config_version: 2

input:
    type: file
    path: /var/log/haproxy/access.log   # confirmed path — check your own /etc/rsyslog.d/haproxy.conf for the local0.* target if different
    readall: false
    fail_on_missing_logfile: false

grok:
    patterns_dir: ./patterns
    additional_patterns:
        # (?!stats\b) excludes lines where the frontend is literally "stats" — health
        # checks and admin-stats polling hit that frontend constantly and would
        # otherwise flood the per-URI dashboard with a fake "backend." Rename "stats"
        # here if your own stats frontend uses a different name. Verified against a
        # real access.log line — matched correctly on both real traffic and the
        # stats-frontend exclusion case.
        - 'HAPROXY_LOG %{SYSLOGTIMESTAMP:timestamp} %{HOSTNAME:host} haproxy\[%{NUMBER:pid}\]: %{IP:client_ip}:%{NUMBER:client_port} \[%{HTTPDATE:accept_date}\] (?!stats\b)%{WORD:frontend} %{NOTSPACE:backend_server} %{NUMBER:Tq}/%{NUMBER:Tw}/%{NUMBER:Tc}/%{NUMBER:Tr}/%{NUMBER:Tt} %{NUMBER:status} %{NUMBER:bytes} %{DATA:captured_req_cookie} %{DATA:captured_res_cookie} %{DATA:termination_state} %{DATA:actconn}/%{DATA:feconn}/%{DATA:beconn}/%{DATA:srvconn}/%{DATA:retries} %{DATA:srv_queue}/%{DATA:backend_queue} "%{WORD:method} %{URIPATHPARAM:request_path} HTTP/%{NUMBER:http_version}"'
        - 'HTTPDATE %{MONTHDAY}/%{MONTH}/%{YEAR}:%{TIME}'
        - "URIPATHPARAM %{URIPATH}(?:\\?%{URIPARAM})?"
        - "URIPATH [A-Za-z0-9\\-._~!$&'()*+,;=:@/]+"
        - "URIPARAM [A-Za-z0-9\\-._~!$&'()*+,;=:@/?%]*"

metrics:
    - type: counter
      name: haproxy_uri_requests_total
      help: Total requests per URI path, method, and status code
      match: '%{HAPROXY_LOG}'
      labels:
          path: '{{.request_path}}'
          method: '{{.method}}'
          status: '{{.status}}'
          backend: '{{.backend_server}}'

    - type: histogram
      name: haproxy_uri_response_time_seconds
      help: Response time (Tt, total time) per URI — real histogram, gives actual p50/p95/p99
      match: '%{HAPROXY_LOG}'
      value: '{{divide .Tt 1000}}'
      buckets: [0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10]
      labels:
          path: '{{.request_path}}'
          backend: '{{.backend_server}}'

server:
    protocol: http
    port: 9144
```

**Cardinality warning — read before running against a real access log.** If
your URIs contain IDs (`/order/98721`, `/user/12345`), every unique value
becomes its own Prometheus time series. This grows unbounded and will hurt
Prometheus performance over time. Normalize dynamic segments
(`/order/98721` → `/order/:id`) before running in production — either via a
second grok pattern with a regex substitution, or a small preprocessing
step. Test on a sample log first:

```bash
sudo -u grok_exporter /opt/grok_exporter/grok_exporter -config /opt/grok_exporter/config.yml &
sleep 5
curl -s localhost:9144/metrics | grep haproxy_uri | wc -l
# If this number looks like it's tracking unique order/user IDs rather than
# distinct endpoints, stop and fix the pattern before going further.
kill %1
```

```ini
# /etc/systemd/system/grok_exporter.service
[Unit]
Description=grok_exporter - HAProxy per-URI metrics from access log
After=network.target haproxy.service rsyslog.service
Wants=haproxy.service

[Service]
Type=simple
User=grok_exporter
WorkingDirectory=/opt/grok_exporter
ExecStart=/opt/grok_exporter/grok_exporter -config /opt/grok_exporter/config.yml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now grok_exporter
systemctl status grok_exporter
curl -s localhost:9144/metrics | grep haproxy_uri_requests_total | head
```

**"Configuration version 2 found... recommend updating to version 3"** — this
prints on every start, it's cosmetic. Version 2 (the `grok:` section wrapper
used in this config) is still fully supported. If you want to migrate to v3
later (`grok_patterns:` as a flat list instead), run:
```bash
grok_exporter -config /opt/grok_exporter/config.yml -showconfig
```
which auto-converts and prints the v3 equivalent to stdout — review before
overwriting the working v2 file.

**If you hit `Invalid metric configuration: 'metrics.value' cannot be used
for counter metrics`** on a version of this config with a third metric block
(`haproxy_uri_errors_total`) — that block was removed from the current file
for exactly this reason and doesn't need to be re-added. The precise cause
wasn't `value:` itself (counters do support a `value:` template per
grok_exporter's own CONFIG.md) — it was `cumulative: true` combined with it,
and `cumulative` is only a documented field on `gauge` metrics, not
`counter`. Get the same 4xx/5xx breakdown that block was trying to provide
from the existing `haproxy_uri_requests_total` metric instead, filtering on
its `status` label in PromQL:
```
sum by (path) (rate(haproxy_uri_requests_total{status=~"4..|5.."}[5m]))
```
This is exactly what the Grafana dashboard's "Top URIs by Error Rate" panel
already does.

Note: the user directive here is `grok_exporter`, not `root` — earlier in
this conversation the systemd unit ran as root; tightening to a dedicated
user with read access to the log is the safer default for a VM install.

**On this host specifically**, `/var/log/haproxy/access.log` is owned
`root:root` mode `640` (confirmed via `ls -la`) — a plain `usermod -aG`
won't help since regular users shouldn't be added to the `root` group.
Two real options:

```bash
# Option A — loosen the file's group ownership to something grok_exporter
# can join. Do this in the rsyslog config so it survives log rotation,
# not as a one-off chown that gets reset on the next rotate:
#
# In /etc/rsyslog.d/haproxy.conf, if using an $outchannel or omfile action,
# add fileGroup + fileCreateMode directives so new log files are created
# with a usable group from the start. Simplest version — add this line
# right after the existing local0.* rule:
#
# $FileGroup adm
# $FileCreateMode 0640
#
usermod -aG adm grok_exporter
systemctl restart rsyslog

# Option B — if you'd rather not touch rsyslog's file-creation permissions,
# grant read via ACL instead, which also survives rotation if your logrotate
# config preserves ACLs (check `man logrotate` — `su`/`create` directives):
setfacl -m u:grok_exporter:r /var/log/haproxy/access.log
setfacl -d -m u:grok_exporter:r /var/log/haproxy/   # default ACL for future rotated files
```

Confirm access actually works before moving on:

```bash
sudo -u grok_exporter cat /var/log/haproxy/access.log | tail -1
# should print a log line, not "Permission denied"
```

**If you just ran `usermod -aG`** and this still shows "Permission
denied," it's usually not a config problem — group membership changes
don't apply retroactively to already-running shells or cached login
sessions. `sudo -u <user> <command>` per-command usually re-reads
`/etc/group` fine, but if it doesn't on your system (some hardened OL9
setups with nscd/sssd caching), confirm the membership actually landed
before troubleshooting anything else:
```bash
sudo -u grok_exporter groups
# should show: grok_exporter adm
```
If it still only shows `grok_exporter`, try `sudo -u grok_exporter -i` (a
full login shell instead of a bare command) or restart whatever caching
daemon is in play.

---

## 5. Alertmanager — binary install + systemd

```bash
useradd --no-create-home --shell /sbin/nologin alertmanager
mkdir -p /etc/alertmanager /var/lib/alertmanager
chown alertmanager:alertmanager /etc/alertmanager /var/lib/alertmanager

cd /tmp
curl -LO https://github.com/prometheus/alertmanager/releases/download/v0.28.0/alertmanager-0.28.0.linux-amd64.tar.gz
tar xvf alertmanager-0.28.0.linux-amd64.tar.gz
cd alertmanager-0.28.0.linux-amd64

cp alertmanager amtool /usr/local/bin/
chown alertmanager:alertmanager /usr/local/bin/alertmanager /usr/local/bin/amtool
```

Confirm current version at
`https://github.com/prometheus/alertmanager/releases` before pulling.

Config file (built earlier as `08-alertmanager.yml`, reproduced here):

```yaml
# /etc/alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alertmanager@yourdomain.com'
  smtp_auth_username: 'alertmanager@yourdomain.com'
  smtp_auth_password: 'your-app-password'
  smtp_require_tls: true

route:
  receiver: 'default'
  group_by: ['alertname', 'proxy']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h
  routes:
    - match:
        severity: critical
      receiver: 'haproxy-critical'
      repeat_interval: 1h

    - match:
        severity: warning
      receiver: 'haproxy-warning'
      repeat_interval: 6h

receivers:
  - name: 'default'
    email_configs:
      - to: 'ocean@yourdomain.com'
        send_resolved: true

  - name: 'haproxy-critical'
    email_configs:
      - to: 'ocean@yourdomain.com'
        send_resolved: true
    webhook_configs:
      - url: 'http://localhost:2000/alertmanager'   # prometheus-msteams, step 6
        send_resolved: true

  - name: 'haproxy-warning'
    email_configs:
      - to: 'ocean@yourdomain.com'
        send_resolved: true
    webhook_configs:
      - url: 'http://localhost:2000/alertmanager'
        send_resolved: true
```

```bash
chown alertmanager:alertmanager /etc/alertmanager/alertmanager.yml
amtool check-config /etc/alertmanager/alertmanager.yml
```

```ini
# /etc/systemd/system/alertmanager.service
[Unit]
Description=Alertmanager
Wants=network-online.target
After=network-online.target

[Service]
User=alertmanager
Group=alertmanager
Type=simple
ExecStart=/usr/local/bin/alertmanager \
    --config.file=/etc/alertmanager/alertmanager.yml \
    --storage.path=/var/lib/alertmanager/ \
    --web.listen-address=0.0.0.0:9093
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now alertmanager
systemctl status alertmanager
curl -s localhost:9093/-/healthy
```

---

## 6. prometheus-msteams — binary install + systemd

Alertmanager's generic `webhook_configs` doesn't speak Teams' card format
on its own — this is the translator. Official binary distribution exists
(not container-only), needs the binary plus its template file in the same
working directory.

```bash
useradd --no-create-home --shell /sbin/nologin prometheus-msteams
mkdir -p /opt/prometheus-msteams
cd /tmp
curl -LO https://github.com/prometheus-msteams/prometheus-msteams/releases/latest/download/prometheus-msteams-linux-amd64
curl -LO https://raw.githubusercontent.com/prometheus-msteams/prometheus-msteams/master/default-message-card.tmpl

mv prometheus-msteams-linux-amd64 /opt/prometheus-msteams/prometheus-msteams
mv default-message-card.tmpl /opt/prometheus-msteams/
chmod +x /opt/prometheus-msteams/prometheus-msteams
chown -R prometheus-msteams:prometheus-msteams /opt/prometheus-msteams
```

Confirm the exact release asset naming at
`https://github.com/prometheus-msteams/prometheus-msteams/releases` — asset
filenames occasionally change between versions, adjust the curl URL if
`latest/download/...` 404s.

**Do not put the webhook URL directly in `ExecStart=`.** Real Workflows
webhook URLs contain `%` characters (URL-encoded query params like
`sp=%2Ftriggers%2Fmanual%2Frun`), and systemd treats `%` in unit file values
as the start of a specifier (`%h`, `%i`, etc) — an inline URL with `%` in it
breaks the unit with `Failed to resolve unit specifiers` or `Invalid slot`
and the service won't start at all. Use an `EnvironmentFile` instead so the
URL is never parsed by systemd's specifier logic:

```bash
mkdir -p /etc/prometheus-msteams
cat > /etc/prometheus-msteams/webhook.env << 'EOF'
TEAMS_WEBHOOK_URL=REPLACE-WITH-YOUR-REAL-WEBHOOK-URL
EOF
chmod 600 /etc/prometheus-msteams/webhook.env
chown prometheus-msteams:prometheus-msteams /etc/prometheus-msteams/webhook.env
```

```ini
# /etc/systemd/system/prometheus-msteams.service
[Unit]
Description=prometheus-msteams - forwards Alertmanager alerts to Teams
After=network.target alertmanager.service

[Service]
Type=simple
User=prometheus-msteams
WorkingDirectory=/opt/prometheus-msteams
EnvironmentFile=/etc/prometheus-msteams/webhook.env
ExecStart=/opt/prometheus-msteams/prometheus-msteams \
    -teams-request-uri alertmanager \
    -teams-incoming-webhook-url "${TEAMS_WEBHOOK_URL}"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Teams webhook URL note**: classic Office 365 Connectors
(`webhook.office.com`) were fully retired in Microsoft's May 2026 rollout —
if you have an old `webhook.office.com` URL anywhere (this unit, an old
`.env`, or `alertmanager.yml`'s own `webhook_configs`), it will silently
time out (`dial tcp ...:443: i/o timeout`) rather than error clearly, so
grep for it if notifications seem to be failing without an obvious cause:
```bash
grep -rn "webhook.office.com" /etc/alertmanager/ /etc/prometheus-msteams/ /etc/systemd/system/prometheus-msteams.service
```
Current webhook URLs are generated from Teams: channel → **Workflows** app
→ **Create from blank** → trigger **"When a Teams webhook request is
received"** (search this exact phrase in the trigger panel's search box —
the older named template **"Post to a channel when a webhook request is
received"** has been unreliable/missing on some tenants) → action **"Post
card in a chat or channel"** → pick Team + Channel → copy the generated URL
from the trigger step. The MessageCard JSON payload format prometheus-msteams
sends is unchanged and confirmed still compatible with current webhooks.

```bash
systemctl daemon-reload
systemctl enable --now prometheus-msteams
systemctl status prometheus-msteams

# Test the webhook URL directly before trusting the full pipeline:
curl -H "Content-Type: application/json" \
     -d '{"text": "test from prometheus-msteams setup"}' \
     "REPLACE-WITH-YOUR-WORKFLOWS-WEBHOOK-URL"
```

---

## 6.5. Enhanced email + Teams card templates (optional)

Two template files (`09-email-template.tmpl`, `10-teams-card-template.tmpl`)
provide a modern card-style HTML email and an enhanced MessageCard Teams
layout — color-coded by firing/resolved status, structured per-alert facts,
and an action button linking back to Alertmanager. Neither file requires
editing `alertmanager.yml`'s routing/receiver logic; they only change how
notifications look once wired in.

**Email template placement** — copy onto the Alertmanager host:
```bash
mkdir -p /etc/alertmanager/templates
cp 09-email-template.tmpl /etc/alertmanager/templates/haproxy-email.tmpl
chown alertmanager:alertmanager /etc/alertmanager/templates/haproxy-email.tmpl
```
Placing the file here does nothing by itself — it only activates once
`alertmanager.yml` references it. To wire it in, add a top-level
`templates:` entry and change the `email_configs` block's `html:` field:
```yaml
templates:
  - '/etc/alertmanager/templates/haproxy-email.tmpl'

# inside the relevant email_configs entry:
    html: '{{ template "haproxy.email.html" . }}'
```
After adding this, reload (not a full restart — Alertmanager supports
config reload):
```bash
systemctl reload alertmanager
```

**Teams card placement** — copy onto the HAProxy host, into
prometheus-msteams' working directory, **overwriting** the file it already
points at by default:
```bash
# back up the original first, in case you want to revert:
cp /opt/prometheus-msteams/default-message-card.tmpl /opt/prometheus-msteams/default-message-card.tmpl.bak

cp 10-teams-card-template.tmpl /opt/prometheus-msteams/default-message-card.tmpl
chown prometheus-msteams:prometheus-msteams /opt/prometheus-msteams/default-message-card.tmpl
systemctl restart prometheus-msteams
```
Unlike the email template, this one takes effect immediately on restart —
no `alertmanager.yml` reference needed, since prometheus-msteams reads its
template file independently of Alertmanager's own templating system.

**Restart scope — don't restart the wrong service.** These two templates
belong to two entirely separate services:
- Teams card change → restart **prometheus-msteams** (`systemctl restart
  prometheus-msteams`). Alertmanager doesn't need to be touched at all.
- Email template change → only matters once referenced in
  `alertmanager.yml`, at which point **Alertmanager** needs a `reload` (not
  prometheus-msteams).
An unreferenced template file sitting in either directory does nothing —
there's nothing to reload until something actually points at it.

---

## 7. Grafana

You almost certainly already have this running per your existing
Grafana/Prometheus observability stack — skip to the datasource step below.
If not:

```bash
cat > /etc/yum.repos.d/grafana.repo << 'EOF'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF

dnf install -y grafana
systemctl daemon-reload
systemctl enable --now grafana-server
```

### Add Prometheus as a datasource — screen by screen

1. Log into Grafana — `http://<grafana-server-ip>:3000` (default first
   login `admin`/`admin` unless already changed).
2. Left sidebar → **Connections** → **Data sources**.
3. **Add data source** (top right).
4. Search/click **Prometheus**.
5. **URL field** — Prometheus and Grafana are on the same box in this
   split, so:
   ```
   http://localhost:9090
   ```
   If they're ever split across machines, use that machine's real
   IP/hostname instead.
6. Leave everything else default — this setup has no auth/TLS on
   Prometheus itself.
7. Scroll down → **Save & test**.
8. Expect a green "Successfully queried the Prometheus API" confirmation.
   **Stop here and fix it if this fails** — nothing in step 8 works without
   this passing first.

**Common failure**: "Bad Gateway" usually means Prometheus itself isn't
running:
```bash
systemctl status prometheus
curl -s localhost:9090/-/healthy
```

---

## 8. Grafana dashboard import — screen by screen

File `07-grafana-dashboard.json` (already built). The dashboard uses a
templated datasource variable (`${DS_PROMETHEUS}`) so it's portable across
different Grafana instances — Grafana prompts you at import time for which
real datasource to map that variable to, rather than hardcoding one.

**This requires the JSON to contain a `__inputs`/`__requires` block, or the
prompt never appears.** The current file has this block (added after an
earlier version shipped without it — see the note at the end of this
section if you're troubleshooting a "datasource not found" error on an
older copy of the file).

1. Left sidebar → **Dashboards**.
2. **New** (top right) → **Import**.
3. **Upload dashboard JSON file** → browse to `07-grafana-dashboard.json`.
   Use the file upload, not paste-JSON-text — some panel strings are
   multi-line and easy to mangle by hand.
4. Grafana parses the file and shows an import screen with:
   - **Name** — pre-filled from the JSON (`HAProxy - Full Traffic and
     Health`). Change if you want.
   - **Folder** — pick one or leave General.
   - **A dropdown labeled "Prometheus"** — this is `${DS_PROMETHEUS}`
     being resolved. Select the Prometheus datasource created in step 7.
5. **Import**.
6. Dashboard opens:
   - Panels 1–11 (backend status, active servers, connections, response
     time, queue depth) should show data immediately — they pull from
     `:8404/metrics`.
   - Panels 21–23 (per-URI: top URIs, top errors, p95 response time)
     should also show data if grok_exporter (step 4) is live and the
     `haproxy-uri` scrape job is in Prometheus's config.
   - The `$proxy` variable at the top filters to specific backends,
     defaults to "All."

**If panels show "No data":**

- Check the time range picker (top right, default `now-1h`) — widen it if
  your traffic/testing happened outside that window.
- Confirm data actually exists in Prometheus directly, bypassing Grafana:
  ```bash
  curl -s 'localhost:9090/api/v1/query?query=haproxy_backend_status'
  ```
  Real values in `result` means Prometheus has data and the problem is
  Grafana-side (datasource mapping, panel query). An empty `result: []`
  means the problem is upstream — scrape config, or the exporter itself.
- For panels 21–23 specifically: confirm grok_exporter is running as a
  **systemd service**, not a backgrounded terminal job — a job started
  with `&` in a shell dies the moment that terminal session ends, so data
  silently stops flowing.

**If you get "datasource ${DS_PROMETHEUS} was not found" with red `!`
icons on every panel**: this means the JSON file is missing the
`__inputs`/`__requires` block — Grafana had nothing to prompt you for, so
it treated the variable as a literal (nonexistent) datasource UID. This
happened during initial testing of this dashboard and was fixed by adding:

```json
"__inputs": [
  {
    "name": "DS_PROMETHEUS",
    "label": "Prometheus",
    "description": "",
    "type": "datasource",
    "pluginId": "prometheus",
    "pluginName": "Prometheus"
  }
],
"__requires": [
  { "type": "grafana", "id": "grafana", "name": "Grafana", "version": "10.0.0" },
  { "type": "datasource", "id": "prometheus", "name": "Prometheus", "version": "1.0.0" }
],
```

right after the opening `{` of the dashboard JSON. The current
`07-grafana-dashboard.json` already has this — if you're hitting this
error, delete the broken dashboard from Grafana first (Dashboards → find
it → Settings gear → Delete), then re-import the current file rather than
re-importing on top of the broken one.

Panels 21–23 (per-URI: top URIs by traffic, top URIs by error rate, per-URI
p95 response time) stay empty until step 4 (grok_exporter) is actually
producing data. Everything else populates as soon as step 3's scrape
config is live.

---

## 9. End-to-end test sequence

Run in this order — each step confirms the previous one actually worked
before you build on top of it:

```bash
# 1. HAProxy exposing metrics
curl -s localhost:8404/metrics | grep haproxy_backend_status

# 2. Prometheus scraping HAProxy
curl -s 'localhost:9090/api/v1/query?query=up{job="haproxy"}' | grep -o '"value":\[.*\]'

# 3. Prometheus rules loaded and evaluating
curl -s localhost:9090/api/v1/rules | grep -o '"name":"HAProxy[A-Za-z]*"'

# 4. grok_exporter producing per-URI data
curl -s localhost:9144/metrics | grep haproxy_uri_requests_total | head -3

# 5. Alertmanager reachable from Prometheus
curl -s localhost:9093/-/healthy

# 6. prometheus-msteams reachable, Teams webhook works
curl -H "Content-Type: application/json" -d '{"text":"pipeline test"}' \
     "REPLACE-WITH-YOUR-WORKFLOWS-WEBHOOK-URL"

# 7. Force a real alert to fire end-to-end — stop a backend server
#    (or systemctl stop on whatever service backs one HAProxy server entry),
#    wait ~30s, then check:
curl -s localhost:9090/api/v1/alerts | grep -A2 '"alertname":"HAProxyServerDown"'
# Should show state "firing" — then check Teams channel and email inbox
# for the notification within a minute or two. Restart the backend service
# afterward and confirm the "resolved" notification also arrives
# (send_resolved: true is set throughout).
```

---

## 10. Scope honesty — native vs. extra tooling

**Native (HAProxy's built-in Prometheus exporter)**: frontend, backend, and
per-server status/connections/sessions/response-time-average/errors. Zero
extra software beyond Prometheus + Grafana + Alertmanager.

**Per-URI (needs grok_exporter)**: HAProxy does not natively break metrics
down by URL path — its exporter reports per-proxy/per-server only, never
per-endpoint. "Which API is slow," "which URI is erroring" — that data
lives in the access log, not the stats socket. Real, working, but it's a
separate tool with its own failure surface (log format changes, log
rotation interaction, cardinality) to keep an eye on.

**What "success/error/failed" maps to, concretely:**

- **Success** → `haproxy_backend_http_responses_total{code="2xx"}`
- **Client error** → `code="4xx"` (bad request, not found — not the
  backend's fault)
- **Server error** → `code="5xx"` (backend actually broke)
- **Failed / never got a response** →
  `haproxy_backend_connection_errors_total`,
  `haproxy_backend_response_errors_total` — connection-level failures,
  distinct from HTTP status codes, since the backend never returned a
  status at all. Dashboard panel 7 covers the first three, panel 8 covers
  this one — don't merge them into one "errors" number, they mean
  different things when debugging.

---

## 11. Troubleshooting

**`curl localhost:8404/metrics` returns nothing / connection refused** —
HAProxy didn't reload cleanly. Check `haproxy -c -f
/etc/haproxy/haproxy.cfg` for syntax errors first, then `journalctl -u
haproxy -n 50`.

**Prometheus targets page (`/targets`) shows haproxy job as DOWN** —
usually a firewall/SELinux issue if Prometheus and HAProxy are on different
hosts. `firewall-cmd --add-port=8404/tcp --permanent && firewall-cmd
--reload` on the HAProxy host.

**grok_exporter runs but `/metrics` shows zero `haproxy_uri_*` series** —
almost always a log format mismatch. Grab one real line from your
access.log and manually check it against the grok pattern — easiest way is
the grok_exporter `-config` flag has no dry-run, so temporarily set
`readall: true` in config.yml, point `path` at a small test file with 2–3
known log lines, run in foreground (`./grok_exporter -config config.yml`),
watch stdout for parse errors. If you have Python available, `pip install
pygrok --break-system-packages` and testing the regex directly against a
copy-pasted real log line is faster than iterating through grok_exporter
restarts — confirms the pattern before touching the actual service.

**All lines seem to match except the ones you expect** — if you added the
`(?!stats\b)` exclusion for your stats frontend and traffic still isn't
showing up, double check the frontend name in the exclusion actually
matches your `frontend` block name in haproxy.cfg exactly (case-sensitive,
word-boundary — `(?!stats\b)` won't accidentally exclude a frontend named
`statsapi` or similar, but confirm your naming doesn't collide).

**Alertmanager shows the alert firing but Teams never gets it** — check
`journalctl -u prometheus-msteams -n 50` first. Most common cause: the
webhook URL changed (Teams Workflows URLs can be regenerated/revoked) or a
typo in the systemd unit's `-teams-incoming-webhook-url` flag. Re-test with
the raw curl command from section 6.

**Alerts fire repeatedly even though nothing changed** — check `for:`
duration in the rule isn't too short for a genuinely flapping metric, and
confirm `group_interval`/`repeat_interval` in alertmanager.yml are set the
way you expect — a short `repeat_interval` will re-send the same
still-firing alert far more often than feels necessary.

**systemctl status shows a service repeatedly restarting** — check
`journalctl -u <service> -n 50 --no-pager` for the actual error before
assuming it's a config problem; often it's a permissions issue (dedicated
user can't read a file it needs — check ownership/group membership on
config paths and, for grok_exporter specifically, the log file itself).
