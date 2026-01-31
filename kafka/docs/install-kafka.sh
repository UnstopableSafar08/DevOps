#!/bin/bash
################################################################################
# Kafka 4.1.1 KRaft Cluster - Automated Installation Script
# For RHEL 9.x / Oracle Linux 9.x / Rocky Linux 9.x
#
# PURPOSE:
# This script automates the installation of a 3-node Kafka cluster.
# It handles all the tedious setup tasks automatically.
#
# WHAT THIS SCRIPT DOES:
# 1. Installs Java 21 LTS
# 2. Creates Kafka user and directories
# 3. Optimizes operating system settings
# 4. Downloads and installs Kafka
# 5. Configures Kafka for your node
# 6. Sets up systemd service
# 7. Prepares cluster for first start
#
# USAGE:
#   Step 1: Generate cluster UUID (run ONCE on any server):
#           /opt/kafka/bin/kafka-storage.sh random-uuid
#           Save the output!
#
#   Step 2: Run this script on each server:
#           sudo ./install-kafka.sh <node_number> <cluster_uuid>
#
#   Examples:
#           On kafka1: sudo ./install-kafka.sh 1 abc123-def456-ghi789
#           On kafka2: sudo ./install-kafka.sh 2 abc123-def456-ghi789
#           On kafka3: sudo ./install-kafka.sh 3 abc123-def456-ghi789
#
# REQUIREMENTS:
# - Root/sudo access
# - Internet connection (to download Kafka)
# - 3 servers that can communicate with each other
# - Firewall ports 9092, 9093, 9094 open between servers
#
# TIME REQUIRED: ~10-15 minutes per server
#
################################################################################

# Enable strict error handling
# This makes the script stop if any command fails
set -e

################################################################################
# CONFIGURATION - Modify these if needed
################################################################################

# Kafka version to install
KAFKA_VERSION="4.1.1"
SCALA_VERSION="2.13"

# System users and directories
KAFKA_USER="kafka"
KAFKA_HOME="/opt/kafka"
DATA_DIR="/data/kafka"
LOG_DIR="/var/log/kafka"

# Server IP addresses and hostnames
# IMPORTANT: Modify these to match your actual servers!
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

################################################################################
# COLOR CODES for pretty output
################################################################################
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# HELPER FUNCTIONS
################################################################################

# Print colored messages
print_success() {
    echo -e "${GREEN} $1${NC}"
}

print_error() {
    echo -e "${RED} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

print_step() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
}

################################################################################
# VALIDATE INPUT
################################################################################

print_step "STEP 0: Validating Input"

# Check if correct number of arguments provided
if [ "$#" -ne 2 ]; then
    print_error "Wrong number of arguments!"
    echo ""
    echo "Usage: $0 <node_number> <cluster_uuid>"
    echo ""
    echo "Example:"
    echo "  $0 1 abc123-def456-ghi789"
    echo ""
    echo "Steps:"
    echo "  1. Generate UUID: /opt/kafka/bin/kafka-storage.sh random-uuid"
    echo "  2. Run this script on each server with that UUID"
    exit 1
fi

# Parse arguments
NODE_ID=$1
CLUSTER_UUID=$2

# Validate node ID
if [[ ! "$NODE_ID" =~ ^[1-3]$ ]]; then
    print_error "Node ID must be 1, 2, or 3"
    exit 1
fi

# Validate cluster UUID format (basic check)
if [ ${#CLUSTER_UUID} -lt 10 ]; then
    print_error "Cluster UUID seems too short. Did you copy it correctly?"
    exit 1
fi

# Get node information
NODE_IP=${NODE_IPS[$NODE_ID]}
NODE_NAME=${NODE_NAMES[$NODE_ID]}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Display configuration
echo ""
print_success "Configuration validated!"
echo "  Node ID:       $NODE_ID"
echo "  Node Name:     $NODE_NAME"
echo "  Node IP:       $NODE_IP"
echo "  Cluster UUID:  $CLUSTER_UUID"
echo "  Kafka Version: $KAFKA_VERSION"
echo ""

read -p "Is this correct? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    print_error "Installation cancelled"
    exit 1
fi

################################################################################
# STEP 1: Update System and Install Prerequisites
################################################################################

print_step "STEP 1/10: Installing System Prerequisites"
print_info "This installs Java 21 LTS and other required tools..."

# Update hostname
print_info "Setting hostname to $NODE_NAME..."
hostnamectl set-hostname $NODE_NAME
print_success "Hostname set to $NODE_NAME"

# Install Java 21 LTS and utilities
print_info "Installing prerequisites (wget, tar, etc.)..."
dnf install -y wget tar vim net-tools > /dev/null 2>&1

print_info "Installing BellSoft JDK 21 LTS..."
cd /opt
wget -q https://download.bell-sw.com/java/21.0.10+10/bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
tar -xzf bellsoft-jdk21.0.10+10-linux-amd64.tar.gz
mv /opt/jdk-21.0.10+10 /opt/jdk-21.0.10
export JAVA_HOME=/opt/jdk-21.0.10
export PATH=$JAVA_HOME/bin:$PATH
print_success "Java 21 LTS installed"

# Verify Java installation
JAVA_VER=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
print_success "Java version: $JAVA_VER"

# Set JAVA_HOME
export JAVA_HOME=/opt/jdk-21.0.10
print_success "JAVA_HOME set to $JAVA_HOME"

################################################################################
# STEP 2: System Optimization
################################################################################

print_step "STEP 2/10: Optimizing System Settings"
print_info "This configures kernel parameters and system limits for Kafka..."

# Set file descriptor limits
print_info "Increasing file descriptor limits..."
cat > /etc/security/limits.d/kafka.conf <<EOF
kafka soft nofile 100000
kafka hard nofile 100000
kafka soft nproc 32768
kafka hard nproc 32768
kafka soft memlock unlimited
kafka hard memlock unlimited
EOF
print_success "File limits configured"

# Configure kernel parameters
print_info "Optimizing kernel parameters..."
cat >> /etc/sysctl.conf <<'EOF'

# Kafka Performance Tuning (added by install script)
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

sysctl -p > /dev/null 2>&1
print_success "Kernel parameters optimized"

# Disable swap
print_info "Disabling swap (required for Kafka performance)..."
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab
print_success "Swap disabled"

################################################################################
# STEP 3: Firewall Configuration
################################################################################

print_step "STEP 3/10: Configuring Firewall"
print_info "Opening required ports for Kafka..."

firewall-cmd --permanent --add-port=9092/tcp > /dev/null 2>&1  # Client connections
firewall-cmd --permanent --add-port=9093/tcp > /dev/null 2>&1  # SSL connections
firewall-cmd --permanent --add-port=9094/tcp > /dev/null 2>&1  # Controller communication
firewall-cmd --permanent --add-port=9999/tcp > /dev/null 2>&1  # JMX monitoring
firewall-cmd --reload > /dev/null 2>&1

print_success "Firewall configured (ports 9092, 9093, 9094, 9999)"

################################################################################
# STEP 4: Create Kafka User and Directories
################################################################################

print_step "STEP 4/10: Creating Kafka User and Directories"

# Create Kafka user if it doesn't exist
if id "$KAFKA_USER" &>/dev/null; then
    print_warning "User $KAFKA_USER already exists"
else
    print_info "Creating user: $KAFKA_USER..."
    useradd -r -s /bin/bash $KAFKA_USER
    print_success "User $KAFKA_USER created"
fi

# Create directories
print_info "Creating Kafka directories..."
mkdir -p $DATA_DIR/logs $DATA_DIR/metadata $LOG_DIR
chown -R $KAFKA_USER:$KAFKA_USER $DATA_DIR $LOG_DIR
chmod -R 755 $DATA_DIR $LOG_DIR
print_success "Directories created:"
print_success "  Data: $DATA_DIR"
print_success "  Logs: $LOG_DIR"

################################################################################
# STEP 5: Download and Install Kafka
################################################################################

print_step "STEP 5/10: Downloading and Installing Kafka"
print_info "Downloading Kafka $KAFKA_VERSION (this may take a few minutes)..."

cd /tmp

# Download Kafka
KAFKA_FILENAME="kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"
KAFKA_URL="https://downloads.apache.org/kafka/${KAFKA_VERSION}/${KAFKA_FILENAME}"

if [ ! -f "$KAFKA_FILENAME" ]; then
    wget -q --show-progress $KAFKA_URL
    print_success "Kafka downloaded"
else
    print_warning "Kafka file already exists, using cached version"
fi

# Extract Kafka
print_info "Extracting Kafka..."
tar -xzf $KAFKA_FILENAME -C /opt/

# Remove old Kafka installation if exists
if [ -d "$KAFKA_HOME" ]; then
    print_warning "Removing old Kafka installation..."
    rm -rf $KAFKA_HOME
fi

# Move and rename
mv /opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION} $KAFKA_HOME
chown -R $KAFKA_USER:$KAFKA_USER $KAFKA_HOME
print_success "Kafka installed to $KAFKA_HOME"

# Cleanup
rm -f $KAFKA_FILENAME
print_success "Temporary files cleaned up"

################################################################################
# STEP 6: Configure Kafka
################################################################################

print_step "STEP 6/10: Configuring Kafka"
print_info "Creating server.properties for node $NODE_ID..."

# Build controller quorum voters string
QUORUM_VOTERS="1@${NODE_NAMES[1]}:9094,2@${NODE_NAMES[2]}:9094,3@${NODE_NAMES[3]}:9094"

# Create server.properties
cat > $KAFKA_HOME/config/server.properties <<EOF
# Apache Kafka Configuration - Node $NODE_ID
# Generated by install script on $(date)

########################### KRaft Mode Configuration ###########################
process.roles=broker,controller
node.id=$NODE_ID
controller.quorum.voters=$QUORUM_VOTERS

########################### Network Configuration ###########################
listeners=PLAINTEXT://$NODE_NAME:9092,CONTROLLER://$NODE_NAME:9094
advertised.listeners=PLAINTEXT://$NODE_NAME:9092
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER

########################### Storage Configuration ###########################
log.dirs=$DATA_DIR/logs
metadata.log.dir=$DATA_DIR/metadata

########################### Cluster Identity ###########################
cluster.id=$CLUSTER_UUID

########################### Replication Configuration ###########################
default.replication.factor=3
min.insync.replicas=2
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2

########################### Consumer Offset Configuration ###########################
offsets.topic.num.partitions=50
offsets.topic.replication.factor=3
offsets.retention.minutes=10080

########################### Topic Defaults ###########################
num.partitions=3
auto.create.topics.enable=false

########################### Performance Settings ###########################
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

########################### Log Retention ###########################
log.retention.hours=168
log.retention.check.interval.ms=300000
log.segment.bytes=1073741824
log.cleanup.policy=delete

########################### Compression ###########################
compression.type=lz4
EOF

chown $KAFKA_USER:$KAFKA_USER $KAFKA_HOME/config/server.properties
print_success "Kafka configuration created"

################################################################################
# STEP 7: Format Storage
################################################################################

print_step "STEP 7/10: Formatting Kafka Storage"
print_info "Initializing storage directories with cluster UUID..."

sudo -u $KAFKA_USER $KAFKA_HOME/bin/kafka-storage.sh format \
    -t $CLUSTER_UUID \
    -c $KAFKA_HOME/config/server.properties

print_success "Storage formatted and ready"

################################################################################
# STEP 8: Create Systemd Service
################################################################################

print_step "STEP 8/10: Creating Systemd Service"
print_info "Setting up Kafka as a system service..."

cat > /etc/systemd/system/kafka.service <<'EOF'
[Unit]
Description=Apache Kafka Server (KRaft Mode)
Documentation=https://kafka.apache.org/documentation/
After=network.target

[Service]
Type=simple
User=kafka
Group=kafka
Environment="JAVA_HOME=/opt/jdk-21.0.10"
Environment="KAFKA_HEAP_OPTS=-Xms6g -Xmx6g"
Environment="KAFKA_JVM_PERFORMANCE_OPTS=-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M"
Environment="LOG_DIR=/var/log/kafka"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10
LimitNOFILE=100000
LimitNPROC=32768

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable kafka > /dev/null 2>&1

print_success "Systemd service created and enabled"

################################################################################
# STEP 9: Update /etc/hosts
################################################################################

print_step "STEP 9/10: Updating /etc/hosts"
print_info "Adding Kafka cluster nodes to hosts file..."

# Backup original hosts file
cp /etc/hosts /etc/hosts.backup-$(date +%Y%m%d)

# Add Kafka nodes if not already present
for i in 1 2 3; do
    if ! grep -q "${NODE_NAMES[$i]}" /etc/hosts; then
        echo "${NODE_IPS[$i]} ${NODE_NAMES[$i]}" >> /etc/hosts
        print_success "Added ${NODE_NAMES[$i]} to /etc/hosts"
    else
        print_warning "${NODE_NAMES[$i]} already in /etc/hosts"
    fi
done

################################################################################
# STEP 10: Create Helper Scripts
################################################################################

print_step "STEP 10/10: Creating Helper Scripts"

# Create health check script
cat > $KAFKA_HOME/bin/health-check.sh <<'HEALTHSCRIPT'
#!/bin/bash
BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"

echo "Checking Kafka cluster health..."
BROKERS=$(/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server $BOOTSTRAP 2>/dev/null | grep -c "^kafka")
echo "Active Brokers: $BROKERS/3"

URP=$(/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server $BOOTSTRAP \
  --describe --under-replicated-partitions 2>/dev/null | grep -c "Topic:")
echo "Under-Replicated Partitions: $URP"

if [ "$BROKERS" -eq 3 ] && [ "$URP" -eq 0 ]; then
  echo " Cluster is HEALTHY"
  exit 0
else
  echo " Cluster has ISSUES"
  exit 1
fi
HEALTHSCRIPT

chmod +x $KAFKA_HOME/bin/health-check.sh
chown $KAFKA_USER:$KAFKA_USER $KAFKA_HOME/bin/health-check.sh
print_success "Health check script created: $KAFKA_HOME/bin/health-check.sh"

# Create cluster status script
cat > $KAFKA_HOME/bin/cluster-status.sh <<'STATUSSCRIPT'
#!/bin/bash
BOOTSTRAP="kafka1:9092,kafka2:9092,kafka3:9092"

echo "=== Kafka Cluster Status ==="
echo ""
echo "Brokers:"
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server $BOOTSTRAP 2>/dev/null | grep "^kafka"
echo ""
echo "Controller:"
/opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server $BOOTSTRAP describe --status 2>/dev/null
STATUSSCRIPT

chmod +x $KAFKA_HOME/bin/cluster-status.sh
chown $KAFKA_USER:$KAFKA_USER $KAFKA_HOME/bin/cluster-status.sh
print_success "Status script created: $KAFKA_HOME/bin/cluster-status.sh"

################################################################################
# INSTALLATION COMPLETE
################################################################################

print_step " INSTALLATION COMPLETE! "

echo ""
print_success "Kafka $KAFKA_VERSION installed successfully on node $NODE_ID ($NODE_NAME)"
echo ""

print_info "Next Steps:"
echo ""
echo "1. Repeat this installation on the other nodes:"
echo "    Node 1: sudo ./install-kafka.sh 1 $CLUSTER_UUID"
echo "    Node 2: sudo ./install-kafka.sh 2 $CLUSTER_UUID"
echo "    Node 3: sudo ./install-kafka.sh 3 $CLUSTER_UUID"
echo ""
echo "2. After all nodes are installed, start Kafka on each node:"
echo "   sudo systemctl start kafka"
echo ""
echo "3. Check Kafka status:"
echo "   sudo systemctl status kafka"
echo ""
echo "4. View logs:"
echo "   tail -f /var/log/kafka/server.log"
echo ""
echo "5. Verify cluster health (after all nodes started):"
echo "   $KAFKA_HOME/bin/health-check.sh"
echo ""

print_warning "Important Reminders:"
echo "   Start nodes ONE AT A TIME (wait 30 seconds between each)"
echo "   Check logs for any errors during startup"
echo "   Ensure all nodes can communicate (ping kafka1, kafka2, kafka3)"
echo "   Firewall ports 9092, 9093, 9094 must be open between nodes"
echo ""

print_info "Useful Commands:"
echo "  Start Kafka:   sudo systemctl start kafka"
echo "  Stop Kafka:    sudo systemctl stop kafka"
echo "  Status:        sudo systemctl status kafka"
echo "  Logs:          tail -f /var/log/kafka/server.log"
echo "  Health Check:  $KAFKA_HOME/bin/health-check.sh"
echo ""

print_success "Installation completed at $(date)"
echo ""
