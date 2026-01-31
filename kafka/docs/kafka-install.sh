#!/bin/bash
#############################################################################
# Kafka 3.9.1 KRaft Production Cluster Setup Script
# For RHEL 9.x / Oracle Linux 9.x / Rocky Linux 9.x
#
# Usage: 
#   sudo ./kafka-install.sh <node_number> <cluster_uuid>
#
# Example:
#   Node 1: sudo ./kafka-install.sh 1 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
#   Node 2: sudo ./kafka-install.sh 2 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
#   Node 3: sudo ./kafka-install.sh 3 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g
#
#############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
KAFKA_VERSION="3.9.1"
SCALA_VERSION="2.13"
KAFKA_USER="kafka"
KAFKA_HOME="/opt/kafka"
DATA_DIR="/data/kafka"
LOG_DIR="/var/log/kafka"

# Cluster configuration (MODIFY THESE)
declare -A NODE_IPS=(
    [1]="192.168.1.101"
    [2]="192.168.1.102"
    [3]="192.168.1.103"
)

declare -A NODE_NAMES=(
    [1]="kafka1"
    [2]="kafka2"
    [3]="kafka3"
)

# Parse arguments
if [ "$#" -ne 2 ]; then
    echo -e "${RED}Usage: $0 <node_number> <cluster_uuid>${NC}"
    echo -e "${YELLOW}Example: $0 1 7c9d8f5a-3b2c-4d1e-9f8a-1b2c3d4e5f6g${NC}"
    exit 1
fi

NODE_ID=$1
CLUSTER_UUID=$2
NODE_IP=${NODE_IPS[$NODE_ID]}
NODE_NAME=${NODE_NAMES[$NODE_ID]}

echo -e "${GREEN}=== Kafka Production Setup ===${NC}"
echo -e "Node ID: $NODE_ID"
echo -e "Node Name: $NODE_NAME"
echo -e "Node IP: $NODE_IP"
echo -e "Cluster UUID: $CLUSTER_UUID"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

#############################################################################
# STEP 1: System Preparation
#############################################################################
echo -e "${GREEN}[1/10] Installing prerequisites...${NC}"

# Update hostname
hostnamectl set-hostname $NODE_NAME

# Install Java 17
dnf install -y java-17-openjdk-devel wget tar

# Verify Java
java -version
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk

#############################################################################
# STEP 2: OS Tuning
#############################################################################
echo -e "${GREEN}[2/10] Configuring OS parameters...${NC}"

# Set file limits
cat > /etc/security/limits.d/kafka.conf <<EOF
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
kafka soft memlock unlimited
kafka hard memlock unlimited
EOF

# Kernel parameters
cat >> /etc/sysctl.conf <<EOF

# Kafka Tuning
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65000
net.core.somaxconn = 4096
vm.swappiness = 1
vm.dirty_ratio = 80
vm.dirty_background_ratio = 5
vm.max_map_count = 262144
fs.file-max = 2097152
EOF

sysctl -p

# Disable swap
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

#############################################################################
# STEP 3: Firewall Configuration
#############################################################################
echo -e "${GREEN}[3/10] Configuring firewall...${NC}"

firewall-cmd --permanent --add-port=9092/tcp
firewall-cmd --permanent --add-port=9093/tcp
firewall-cmd --permanent --add-port=9094/tcp
firewall-cmd --permanent --add-port=9999/tcp  # JMX
firewall-cmd --reload

#############################################################################
# STEP 4: Create Kafka User and Directories
#############################################################################
echo -e "${GREEN}[4/10] Creating Kafka user and directories...${NC}"

# Create Kafka user
id -u $KAFKA_USER &>/dev/null || useradd -r -s /bin/bash $KAFKA_USER

# Create directories
mkdir -p $DATA_DIR/logs $DATA_DIR/metadata $LOG_DIR
chown -R $KAFKA_USER:$KAFKA_USER $DATA_DIR $LOG_DIR

#############################################################################
# STEP 5: Download and Install Kafka
#############################################################################
echo -e "${GREEN}[5/10] Downloading and installing Kafka ${KAFKA_VERSION}...${NC}"

cd /tmp
wget -q https://downloads.apache.org/kafka/${KAFKA_VERSION}/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz

# Extract
tar -xzf kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz -C /opt/
rm -rf $KAFKA_HOME
mv /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} $KAFKA_HOME
chown -R $KAFKA_USER:$KAFKA_USER $KAFKA_HOME

# Cleanup
rm kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz

#############################################################################
# STEP 6: Configure Kafka
#############################################################################
echo -e "${GREEN}[6/10] Configuring Kafka server.properties...${NC}"

# Backup original config
cp $KAFKA_HOME/config/server.properties $KAFKA_HOME/config/server.properties.bak

# Generate controller.quorum.voters
QUORUM_VOTERS=""
for i in 1 2 3; do
    if [ $i -eq 1 ]; then
        QUORUM_VOTERS="${i}@${NODE_NAMES[$i]}:9094"
    else
        QUORUM_VOTERS="${QUORUM_VOTERS},${i}@${NODE_NAMES[$i]}:9094"
    fi
done

# Create new server.properties
cat > $KAFKA_HOME/config/server.properties <<EOF
# KRaft Mode Configuration
process.roles=broker,controller
node.id=$NODE_ID
controller.quorum.voters=$QUORUM_VOTERS

# Listeners
listeners=PLAINTEXT://$NODE_NAME:9092,CONTROLLER://$NODE_NAME:9094
advertised.listeners=PLAINTEXT://$NODE_NAME:9092
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER

# Log Directories
log.dirs=$DATA_DIR/logs
metadata.log.dir=$DATA_DIR/metadata

# Cluster Configuration
cluster.id=$CLUSTER_UUID

# Replication & Fault Tolerance
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

# Consumer Offsets
offsets.topic.num.partitions=50
offsets.topic.replication.factor=3
offsets.retention.minutes=10080

# Topic Defaults
num.partitions=3
auto.create.topics.enable=false

# Performance Tuning
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log Retention & Cleanup
log.retention.hours=168
log.retention.check.interval.ms=300000
log.segment.bytes=1073741824
log.cleanup.policy=delete

# Compression
compression.type=lz4

# Monitoring
#kafka.jmx.enable=true
#kafka.jmx.port=9999
EOF

chown $KAFKA_USER:$KAFKA_USER $KAFKA_HOME/config/server.properties

#############################################################################
# STEP 7: Format Storage
#############################################################################
echo -e "${GREEN}[7/10] Formatting Kafka storage...${NC}"

sudo -u $KAFKA_USER $KAFKA_HOME/bin/kafka-storage.sh format \
    -t $CLUSTER_UUID \
    -c $KAFKA_HOME/config/server.properties

#############################################################################
# STEP 8: Create Systemd Service
#############################################################################
echo -e "${GREEN}[8/10] Creating systemd service...${NC}"

cat > /etc/systemd/system/kafka.service <<EOF
[Unit]
Description=Apache Kafka Server (KRaft Mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=$KAFKA_USER
Group=$KAFKA_USER
Environment="JAVA_HOME=/usr/lib/jvm/java-17-openjdk"
Environment="KAFKA_HEAP_OPTS=-Xms6g -Xmx6g"
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M -XX:MinMetaspaceFreeRatio=50 -XX:MaxMetaspaceFreeRatio=80"
Environment="LOG_DIR=$LOG_DIR"
ExecStart=$KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties
ExecStop=$KAFKA_HOME/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10
LimitNOFILE=100000
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable kafka

#############################################################################
# STEP 9: Create Helper Scripts
#############################################################################
echo -e "${GREEN}[9/10] Creating helper scripts...${NC}"

# Health check script
cat > $KAFKA_HOME/bin/health-check.sh <<'EOF'
#!/bin/bash
BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"

BROKERS=$(/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server $BOOTSTRAP 2>/dev/null | grep -c "^kafka")

if [ "$BROKERS" -lt 3 ]; then
  echo "CRITICAL: Only $BROKERS brokers available"
  exit 2
fi

URP=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --under-replicated-partitions 2>/dev/null | grep -c "Topic:")

if [ "$URP" -gt 0 ]; then
  echo "WARNING: $URP under-replicated partitions"
  exit 1
fi

echo "OK: Cluster healthy - $BROKERS brokers, 0 under-replicated partitions"
exit 0
EOF

chmod +x $KAFKA_HOME/bin/health-check.sh

# Status script
cat > $KAFKA_HOME/bin/cluster-status.sh <<'EOF'
#!/bin/bash
BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"

echo "=== Kafka Cluster Status ==="
echo ""
echo "Brokers:"
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server $BOOTSTRAP 2>/dev/null | grep "^kafka"
echo ""
echo "Controller:"
/opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server $BOOTSTRAP describe --status
echo ""
echo "Topics:"
/opt/kafka/bin/kafka-topics.sh --bootstrap-server $BOOTSTRAP --list
EOF

chmod +x $KAFKA_HOME/bin/cluster-status.sh
chown -R $KAFKA_USER:$KAFKA_USER $KAFKA_HOME/bin

#############################################################################
# STEP 10: Update /etc/hosts
#############################################################################
echo -e "${GREEN}[10/10] Updating /etc/hosts...${NC}"

# Backup original
cp /etc/hosts /etc/hosts.bak

# Add Kafka nodes
for i in 1 2 3; do
    if ! grep -q "${NODE_NAMES[$i]}" /etc/hosts; then
        echo "${NODE_IPS[$i]} ${NODE_NAMES[$i]}" >> /etc/hosts
    fi
done

#############################################################################
# COMPLETION
#############################################################################
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Verify cluster UUID is the same on all nodes"
echo "2. Start Kafka service: sudo systemctl start kafka"
echo "3. Check status: sudo systemctl status kafka"
echo "4. View logs: tail -f $LOG_DIR/server.log"
echo "5. Check cluster health: $KAFKA_HOME/bin/health-check.sh"
echo ""
echo -e "${YELLOW}Important Commands:${NC}"
echo "Start Kafka:   sudo systemctl start kafka"
echo "Stop Kafka:    sudo systemctl stop kafka"
echo "Status:        sudo systemctl status kafka"
echo "Logs:          tail -f $LOG_DIR/server.log"
echo "Health Check:  $KAFKA_HOME/bin/health-check.sh"
echo "Cluster Info:  $KAFKA_HOME/bin/cluster-status.sh"
echo ""
echo -e "${GREEN}Installation script completed successfully!${NC}"
