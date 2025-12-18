# OpenSearch

OpenSearch is an **open-source distributed search and analytics engine** designed for **search, log analytics, metrics, and observability workloads**. It originated as a **community-driven fork of Elasticsearch 7.10.2 and Kibana**, and today it is governed by the **OpenSearch Software Foundation** with strong backing from AWS and the open-source community.

---

## What OpenSearch Is, in Practical Terms

OpenSearch allows you to:

* **Index and search large volumes of data** in near real time
* **Run complex queries and aggregations** at scale
* **Analyze logs, metrics, and traces** (observability)
* **Build dashboards and visualizations** using OpenSearch Dashboards
* **Operate in production without licensing restrictions**

It is commonly used as a **drop-in replacement for Elasticsearch** in logging stacks, monitoring platforms, and search-heavy applications.

---

## Core Components

### 1. OpenSearch Engine

* Distributed, REST-based search engine
* JSON documents and schema-free indexing
* Horizontal scalability (shards and replicas)
* Near real-time search performance

### 2. OpenSearch Dashboards

* Visualization and analytics UI (Kibana fork)
* Dashboards, saved searches, alerts
* Observability and security plugins built-in

### 3. Plugin-Based Architecture

Key built-in plugins include:

* Security (RBAC, TLS, auth)
* Alerting
* Anomaly Detection
* Index State Management (ISM)
* SQL and PPL query support
* Observability (logs, metrics, traces)

---

## Typical Use Cases

* **Centralized logging** (ELK replacement: OpenSearch + Fluent Bit/Filebeat)
* **Application and infrastructure monitoring**
* **APM and observability**
* **Full-text search** for applications
* **Security analytics and SIEM**
* **Time-series analytics**

Given your background with ELK, Prometheus, Grafana, and Kubernetes, OpenSearch fits naturally into your existing observability stack.

---

## Key Technical Characteristics

| Feature           | Description                               |
| ----------------- | ----------------------------------------- |
| Data Model        | JSON documents                            |
| Query Language    | OpenSearch Query DSL, SQL, PPL            |
| Scalability       | Horizontal (sharding & replication)       |
| Consistency       | Near real-time (eventual consistency)     |
| Storage           | Local disk, EBS, NVMe                     |
| Deployment        | Bare metal, VM, Docker, Kubernetes        |
| API Compatibility | Largely compatible with Elasticsearch 7.x |

---

## Why OpenSearch Exists

* Elasticsearch moved to **SSPL / Elastic License** (not fully open source)
* OpenSearch remained **Apache 2.0 licensed**
* Ensures long-term **vendor neutrality**
* No feature paywalls for security or alerting

---

## OpenSearch vs ELK (High-Level)

* **No licensing cost**
* **Security features included by default**
* **Faster innovation on observability plugins**
* **Strong Kubernetes and cloud-native focus**

---

## When You Should Choose OpenSearch

Choose OpenSearch if you:

* Want a **100% open-source search stack**
* Need **enterprise-grade security without licensing**
* Are replacing or modernizing an **ELK stack**
* Run **large-scale logging or monitoring** workloads
* Want **full control over deployment and data**

---
