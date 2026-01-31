# Kafka 4.1.1 KRaft Production Cluster Setup Guide

This document describes a **production-grade Apache Kafka 4.1.1 installation and configuration** for a **3-node KRaft (Kafka Raft) cluster** running on:

* RHEL 9.x
* Oracle Linux 9.x
* Rocky Linux 9.x

The setup is suitable for **VM or bare-metal deployments**, follows **Kafka 4.x best practices**, and is designed for **production environments**.

---

## Overview

This guide covers:

* Java 21 (BellSoft Liberica) installation
* OS tuning for Kafka workloads
* Firewall configuration
* Kafka user and directory layout
* Kafka 4.1.1 installation
* KRaft-mode `server.properties` configuration
* Storage formatting with a shared cluster UUID
* systemd service configuration
* Basic operational validation

---

## Cluster Topology

| Node ID | Hostname | IP Address    | Roles              |
| ------: | -------- | ------------- | ------------------ |
|       1 | kafka1   | 192.168.1.101 | broker, controller |
|       2 | kafka2   | 192.168.1.102 | broker, controller |
|       3 | kafka3   | 192.168.1.103 | broker, controller |

---

## Installed Software

* **Kafka:** 4.1.1
* **Scala:** 2.13
* **Java:** BellSoft Liberica JDK 21.0.10
* **Kafka Home:** `/opt/kafka`
* **Kafka Data:** `/var/kafka`
* **Kafka Logs:** `/var/log/kafka`

---

## Java 21 Installation (BellSoft Liberica)

### Download and Extract

```bash
cd  /opt
wget https://download.bell-sw.com/java/21.0.10+10/bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
tar -xzf bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
mv /opt/jdk-21.0.10+10 /opt/jdk-21.0.10
```

### Configure Environment

Edit `vi ~/.bash_profile`:

```bash
export JAVA_HOME=/opt/jdk-21.0.10
export PATH=$JAVA_HOME/bin:$PATH
```

Reload the profile:

```bash
source ~/.bash_profile
```

Verify:

```bash
java -version
```

---

## Kafka 4.1.1 Installation

### Download and Install

```bash
cd /opt
wget https://downloads.apache.org/kafka/4.1.1/kafka_2.13-4.1.1.tgz
tar -xzf kafka_2.13-4.1.1.tgz
```

Create a dedicated Kafka user:

```bash
useradd -r -s /bin/bash kafka
chown -R kafka:kafka /opt/kafka
```

---

## OS Tuning Summary

Recommended kernel and system settings:

* File descriptors: 100000+
* Swap disabled
* Increased TCP buffer sizes
* Low swappiness
* Optimized dirty ratios

Key limits:

```bash
vi /etc/security/limits.d/kafka.conf

kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
```

---

## Firewall Configuration

Open required ports on all nodes:

| Port | Purpose                   |
| ---- | ------------------------- |
| 9092 | Kafka client traffic      |
| 9094 | KRaft controller quorum   |
| 9999 | JMX monitoring (optional) |

```bash
firewall-cmd --permanent --add-port=9092/tcp
firewall-cmd --permanent --add-port=9094/tcp
firewall-cmd --permanent --add-port=9999/tcp
firewall-cmd --reload
```

---

## Kafka KRaft Configuration Highlights

### Core Settings

```properties
process.roles=broker,controller
node.id=<NODE_ID>
controller.quorum.voters=1@kafka1:9094,2@kafka2:9094,3@kafka3:9094
```

### Listeners

```properties
listeners=PLAINTEXT://<HOSTNAME>:9092,CONTROLLER://<HOSTNAME>:9094
advertised.listeners=PLAINTEXT://<HOSTNAME>:9092
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER
```

### Replication and Durability

```properties
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
```

### Storage

```properties
log.dirs=/var/kafka/logs
metadata.log.dir=/var/kafka/metadata
```

---

## Storage Formatting (KRaft)

Run **once per node** with the same cluster UUID:

```bash
/opt/kafka/bin/kafka-storage.sh format \
  -t <CLUSTER_UUID> \
  -c /opt/kafka/config/server.properties
```

Do not re-run this command on an existing node.

---

## systemd Service Management

Kafka is managed via systemd and runs as the `kafka` user.

Common commands:

```bash
systemctl daemon-reload
systemctl enable kafka
systemctl start kafka
systemctl status kafka
systemctl stop kafka
```

Heap and GC guidelines:

* Heap: `-Xms6g -Xmx6g`
* Garbage Collector: G1GC

---

## Verification Checklist

* Same cluster UUID on all nodes
* All three brokers visible
* Exactly one active controller
* No under-replicated partitions
* Stable service after reboot

---

## Operational Best Practices

* Do not enable auto topic creation in production
* Monitor disk I/O and filesystem latency
* Always stop Kafka before host maintenance
* Use rolling restarts for configuration changes

---

## Recommended Next Steps

* TLS or mTLS listeners
* SCRAM authentication
* Prometheus JMX exporter
* Alertmanager rules for ISR and controller health
* Backup and disaster recovery procedures

---

This Kafka 4.1.1 KRaft setup aligns with modern production standards and is suitable for high-durability, low-latency workloads.
