# MQTT
MQTT stands for MQ Telemetry Transport. The protocol is a set of rules that defines how IoT devices can publish and subscribe to data over the Internet. MQTT is used for messaging and data exchange between IoT and industrial IoT (IIoT) devices, such as embedded devices, sensors, industrial PLCs, etc. The protocol is event driven and connects devices using the publish /subscribe (Pub/Sub) pattern. **The sender (Publisher) and the receiver (Subscriber)** communicate via Topics and are decoupled from each other. The connection between them is handled by the MQTT broker. The MQTT broker filters all incoming messages and distributes themcorrectly to the Subscribers. 

- It requires minimal resources since it is lightweight and efficient <br>
- Supports bi-directional messaging between device and cloud <br>
- Can scale to millions of connected devices <br>
- Supports reliable message delivery through 3 QoS levels <br>
- Works well over unreliable networks <br>
- Security enabled, so it works with TLS and common authentication protocols <br>
***
# EMQX
EMQX is a cloud-native, MQTT-based, IoT messaging platform designed for high reliability and massive scale. EMQX is a tool in the Message Queue category of a tech stack. 
EMQX is currently the most scalable MQTT broker for IoT applications. It processes millions of MQTT messages in a second with sub-millisecond latency and allows messaging among more than 100 million clients within a single cluster. EMQX is compliant with MQTT 5.0 and 3.x. It’s ideal for distributed IoT networks and can run on the cloud, Microsoft Azure, Amazon Web Services, and Google Cloud. The broker can implement MQTT over TLS/SSL and supports several authentication mechanisms like PSK, JWT, and X.509. Unlike Mosquitto, EMQX supports clustering via CLI, HTTP API, and a Dashboard.

***
## Architecture
![emqx-arch](https://github.com/UnstopableSafar08/emqx/blob/main/Assets/architecture_image.f5sZc1A2.png)

## Test Cluster overview
![testArch](https://github.com/UnstopableSafar08/emqx/blob/main/Assets/local-cluster-overview.png)

## EMQX - Installation
```sh 
curl -s https://assets.emqx.com/scripts/install-emqx-rpm.sh | sudo bash
yum install epel-release -y ;
yum install -y openssl11 openssl11-devel ;
sudo yum install emqx -y;

# Start and Status Check
sudo systemctl start emqx
systemctl status emqx

#Port Check (18083, 8083, 1883, 8081, 8883, 8084, 4370, 5370)
ss -ltn 
netstat -tupln | grep emqx

# Reload Daemon and restart emqx after config change
systemctl daemon-reload
systemctl restart emqx

# Admin/Users password reset (not for first-time setup)
emqx ctl admins passwd <Username> <NewPassword>
e.g.: emqx ctl admins passwd admin NewPassword#1234
```
***
## EMQX - Login Dashboard
Web Dashboard: http://IP:18083/ <br>
`In my Case  : http://192.168.121.141:18083` <br>
Default-login: <br>
    Default-username: admin <br>
    Default-password: public <br>
### Login page
![login-dashboard](https://github.com/UnstopableSafar08/emqx/blob/main/Assets/1-login.png)
***
## EMQX - Dashboard
![main-dashboard](https://github.com/UnstopableSafar08/emqx/blob/main/Assets/3-dashboard.png)
***
## EMQX - Performence Tunning
```sh
# ------------------------------ Performance tunning (All Node)---------------------------
sysctl -w fs.file-max=2097152
sysctl -w fs.nr_open=2097152
echo 2097152 > /proc/sys/fs/nr_open
ulimit -n 2097152

echo "fs.file-max = 2097152">>/etc/sysctl.conf
echo "fs.file-max = 2097152">>/etc/sysctl.conf
echo "DefaultLimitNOFILE=2097152">>/etc/systemd/system.conf

vi /usr/lib/systemd/system/emqx.service
LimitNOFILE=2097152

echo -e "*      soft   nofile      2097152
*      hard   nofile      2097152">>/etc/security/limits.conf

systemctl restart emqx
systemctl daemon-reload

### ------------- Network -----------------------------------------
sysctl -w net.core.somaxconn=32768
sysctl -w net.ipv4.tcp_max_syn_backlog=16384
sysctl -w net.core.netdev_max_backlog=16384
sysctl -w net.ipv4.ip_local_port_range='1024 65535'
sysctl -w net.core.rmem_default=262144
sysctl -w net.core.wmem_default=262144
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.core.optmem_max=16777216
#sysctl -w net.ipv4.tcp_mem='16777216 16777216 16777216'
sysctl -w net.ipv4.tcp_rmem='1024 4096 16777216'
sysctl -w net.ipv4.tcp_wmem='1024 4096 16777216'
sysctl -w net.nf_conntrack_max=1000000
sysctl -w net.netfilter.nf_conntrack_max=1000000
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_time_wait=30
sysctl -w net.ipv4.tcp_max_tw_buckets=1048576

# Enabling following option is not recommended. It could cause connection reset under NAT
# sysctl -w net.ipv4.tcp_tw_recycle=1
# sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_fin_timeout=15
vi /etc/emqx/emqx.conf
## Sets the maximum number of simultaneously existing ports for this system
node.max_ports = 2097152
  # node {
  #   name = "emqx@10.13.194.69"
  #   cookie = "emqxsecretcookie"
  #   data_dir = "/var/lib/emqx"
  #   max_ports = 2097152   # this line needed to be add
  # }
echo -e "## TCP Listener
#listeners.tcp.$name.acceptors = 64
#listeners.tcp.$name.max_connections = 1024000" >> /etc/emqx/emqx.conf

systemctl restart emqx
```
***
## EMQX - Uninstall/Remove
```sh
# ----------------- Complete Uninstall ------------
sudo yum remove emqx -y
sudo rm -rf /etc/emqx 
sudo rm -rf /var/lib/emqx 
sudo rm -rf /var/log/emqx

# ----------------- Service Delete ------------
sudo rm /etc/systemd/system/emqx.service
sudo systemctl daemon-reload

# ----------------- User and Group Delete ------------
sudo userdel emqx
sudo groupdel emqx
```



> [!TIP]
>### Read More (Full Documentation): - ![Complete-EMQX-Documentation](https://github.com/UnstopableSafar08/emqx/blob/main/EMQX-by-sagarMalla.pdf) 


