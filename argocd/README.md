# ArgoCD Installation and Configuration Guide

This comprehensive guide covers installing ArgoCD on Kubernetes with NodePort access, custom admin password setup, node placement configuration, and troubleshooting.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Method 1: Basic Installation](#method-1-basic-installation)
3. [Method 2: Installation with Node Placement](#method-2-installation-with-node-placement)
4. [Custom Admin Password Setup](#custom-admin-password-setup)
5. [Troubleshooting](#troubleshooting)
6. [Verification and Access](#verification-and-access)

---

## Prerequisites

Before starting, ensure you have:
- A running Kubernetes cluster
- `kubectl` configured with cluster access
- Cluster admin privileges
- (Optional) `httpd-tools` package for custom password generation

---

## Method 1: Basic Installation

This method installs ArgoCD with basic configuration and NodePort access.

### Step 1: Create ArgoCD Namespace

```bash
kubectl create namespace argocd
```

**What this does:** Creates a dedicated namespace to isolate ArgoCD components from other workloads.

### Step 2: Install ArgoCD Core Components

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

**What this does:** 
- Installs all ArgoCD components (API server, repo server, application controller, etc.)
- Creates necessary ConfigMaps, Secrets, and Services
- Deploys ArgoCD with default configuration

**Wait for pods to be ready:**
```bash
kubectl get pods -n argocd -o wide
```

Wait until all pods show `Running` status with `1/1` or `2/2` ready containers.

### Step 3: Expose ArgoCD Server via NodePort

```bash
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort", "ports": [{"port": 80, "targetPort": 8080, "nodePort": 30080, "protocol": "TCP", "name": "http"}]}}'
```

**What this does:**
- Changes service type from `ClusterIP` to `NodePort`
- Exposes ArgoCD on port `30080` on all cluster nodes
- Allows external access without LoadBalancer or Ingress

**Verify the service:**
```bash
kubectl get svc argocd-server -n argocd
```

You should see:
```
NAME            TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
argocd-server   NodePort   10.96.123.456   <none>        80:30080/TCP   2m
```

### Step 4: Enable Insecure Access (HTTP)

```bash
kubectl patch configmap argocd-cm -n argocd --type merge -p '{"data": {"server.insecure": "true"}}'
```

**What this does:**
- Disables TLS/HTTPS requirement
- Allows HTTP access (useful for internal networks)
- **Security Note:** Only use in trusted networks. For production, use proper TLS certificates.

### Step 5: Restart ArgoCD Server

```bash
kubectl delete pod -l app.kubernetes.io/name=argocd-server -n argocd
```

**What this does:**
- Deletes the ArgoCD server pod
- Kubernetes automatically recreates it with new configuration
- New pod picks up the insecure mode setting

**Wait for the new pod to be ready:**
```bash
kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server
```

### Step 6: Retrieve Initial Admin Password

```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d && echo
```

**What this does:**
- Extracts the auto-generated admin password from Kubernetes secret
- Decodes the base64-encoded password
- Displays it in your terminal

**Example output:**
```
aBcD1234XyZ789
```

**Save this password!** You'll need it to login as admin.

---

## Method 2: Installation with Node Placement

This method pins ArgoCD pods to specific worker nodes for better resource management and isolation.

### Step 1-5: Follow Basic Installation

Complete Steps 1-5 from Method 1 above.

### Step 6: Label Worker Nodes (Optional)

If you want to label multiple nodes for identification:

```bash
kubectl label node sagar-dr-k8s-worker-01.sagar.com.np node-role.kubernetes.io/worker=worker
kubectl label node sagar-dr-k8s-worker-02.sagar.com.np node-role.kubernetes.io/worker=worker
kubectl label node sagar-dr-k8s-worker-03.sagar.com.np node-role.kubernetes.io/worker=worker
kubectl label node sagar-dr-k8s-worker-04.sagar.com.np node-role.kubernetes.io/worker=worker
kubectl label node sagar-dr-k8s-worker-05.sagar.com.np node-role.kubernetes.io/worker=worker
kubectl label node sagar-dr-k8s-worker-06.sagar.com.np node-role.kubernetes.io/worker=worker
```

**What this does:** Adds a visual label `worker` to worker nodes (cosmetic, helps with `kubectl get nodes`).

### Step 7: Label Target Node for ArgoCD

```bash
kubectl label node sagar-dr-k8s-worker-01.sagar.com.np argocd-node=primary --overwrite
```

**What this does:**
- Adds a custom label `argocd-node=primary` to a specific node
- This label will be used to pin ArgoCD pods to this node
- Use `--overwrite` to update if label already exists

**Replace** `sagar-dr-k8s-worker-01.sagar.com.np` with your actual node name.

**Output:**
```bash
[root@drk8s-master01 ~]# kubectl label node sagar-dr-k8s-worker-01.sagar.com.np node-role.kubernetes.io/worker=worker
node/sagar-dr-k8s-worker-01.sagar.com.np not labeled
[root@drk8s-master01 ~]#
[root@drk8s-master01 ~]#
[root@drk8s-master01 ~]# kubectl label node sagar-dr-k8s-worker-01.sagar.com.np argocd-node=primary --overwrite
node/sagar-dr-k8s-worker-01.sagar.com.np not labeled
[root@drk8s-master01 ~]#
[root@drk8s-master01 ~]#
[root@drk8s-master01 ~]#
[root@drk8s-master01 ~]# kubectl get node sagar-dr-k8s-worker-01.sagar.com.np --show-labels
NAME                                  STATUS   ROLES    AGE   VERSION   LABELS
sagar-dr-k8s-worker-01.sagar.com.np   Ready    worker   88d   v1.34.1   argocd-node=primary,beta.kubernetes.io/arch=amd64,beta.kubernetes.io/os=linux,kubernetes.io/arch=amd64,kubernetes.io/hostname=sagar-dr-k8s-worker-01.sagar.com.np,kubernetes.io/os=linux,node-role.kubernetes.io/worker=worker
[root@drk8s-master01 ~]#
```

> Note: When kubectl returns "not labeled," it typically means the node was found, but no changes were actually made because the node already had the exact label you were trying to apply.

**Get your node names:**
```bash
kubectl get nodes
```

### Step 8: Pin ArgoCD Pods to the Labeled Node

```bash
for kind in deployment statefulset; do
  for name in $(kubectl get $kind -n argocd -o jsonpath='{.items[*].metadata.name}'); do
    kubectl patch $kind $name -n argocd \
      -p '{"spec": {"template": {"spec": {"nodeSelector": {"argocd-node": "primary"}}}}}'
  done
done
```

**What this does:**
- Loops through all Deployments and StatefulSets in the argocd namespace
- Adds a `nodeSelector` to each pod template
- Forces all ArgoCD pods to schedule only on nodes with `argocd-node=primary` label

**Benefits:**
- Resource isolation
- Predictable placement
- Better troubleshooting
- Prevents ArgoCD pods from competing with critical workloads

### Step 9: Verify Pod Placement

```bash
kubectl get pods -n argocd -o wide
```

**Expected output:** All pods should show the same node name in the `NODE` column:
```
NAME                                  READY   STATUS    NODE
argocd-server-xxxxx                   1/1     Running   sagar-dr-k8s-worker-01.sagar.com.np
argocd-repo-server-xxxxx              1/1     Running   sagar-dr-k8s-worker-01.sagar.com.np
argocd-application-controller-xxxxx   1/1     Running   sagar-dr-k8s-worker-01.sagar.com.np
...
```

### Step 10: Get Initial Admin Password

```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d && echo
```

---

## Custom Admin Password Setup

The default admin password is randomly generated. You can set a custom password for better security and memorability.

### Prerequisites

Install `httpd-tools` (for bcrypt password hashing):

**RHEL/CentOS/Rocky Linux:**
```bash
dnf install httpd-tools -y
```

**Debian/Ubuntu:**
```bash
apt-get install apache2-utils -y
```

### Step 1: Generate Bcrypt Hash

```bash
htpasswd -nbBC 10 "" sagar@123 | tr -d ':\n'
```

**What this does:**
- `-n`: Display hash on stdout (don't create file)
- `-b`: Use password from command line (batch mode)
- `-B`: Use bcrypt algorithm
- `-C 10`: Cost factor of 10 (recommended for security)
- `tr -d ':\n'`: Removes colon and newline from output

**Example output:**
```
$2y$10$HAgQxol/owR8P4SzzCcLRuQJSzwJcLAyXPfzp7r//OcddmDIYFofC
```

**Save this hash!** You'll need it in the next step.

**Replace `sagar@123` with your desired password.**

### Step 2: Patch Admin Password Secret

```bash
kubectl -n argocd patch secret argocd-secret \
  -p '{"stringData": {
    "admin.password": "$2y$10$HAgQxol/owR8P4SzzCcLRuQJSzwJcLAyXPfzp7r//OcddmDIYFofC",
    "admin.passwordMtime": "'$(date +%FT%T%Z)'"
  }}'
```

**What this does:**
- Updates the `argocd-secret` with your new password hash
- Sets password modification time to current timestamp
- ArgoCD uses bcrypt to verify passwords securely

**Important:** Replace the hash with your generated hash from Step 1.

### Step 3: Restart ArgoCD Server

```bash
kubectl delete pod -l app.kubernetes.io/name=argocd-server -n argocd
```

**Wait for pod to restart:**
```bash
kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-server
```

### Step 4: Test Login

```bash
# Login with new password
argocd login <node-ip>:30080 --username admin --password 'sagar@123' --insecure
```

Replace `<node-ip>` with any node's IP address in your cluster.

---

## Troubleshooting

### Issue: Pods in CrashLoopBackOff

**Symptoms:**
- ArgoCD repo-server pod keeps restarting
- Pod status shows `CrashLoopBackOff` or `Error`

**Common causes:**
- Insufficient resources (CPU/Memory)
- Probe timeouts
- Node resource constraints

**Solution: Adjust Resource Limits and Probes**

```bash
kubectl patch deployment argocd-repo-server -n argocd -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "argocd-repo-server",
          "resources": {
            "requests": {"cpu": "100m", "memory": "256Mi"},
            "limits": {"cpu": "500m", "memory": "512Mi"}
          },
          "livenessProbe": {
            "httpGet": {"path": "/healthz", "port": 8081},
            "initialDelaySeconds": 15,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "failureThreshold": 10
          },
          "readinessProbe": {
            "httpGet": {"path": "/healthz", "port": 8081},
            "initialDelaySeconds": 15,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "failureThreshold": 10
          }
        }]
      }
    }
  }
}'
```

**What this does:**
- **Resource Requests:** Guarantees minimum resources (100m CPU, 256Mi RAM)
- **Resource Limits:** Caps maximum usage (500m CPU, 512Mi RAM)
- **Liveness Probe:** Checks if container is alive, restarts if unhealthy
- **Readiness Probe:** Checks if container can accept traffic
- **initialDelaySeconds: 15:** Waits 15s before first probe (gives app time to start)
- **failureThreshold: 10:** Allows 10 failures before taking action (more tolerant)

**Restart the pod:**
```bash
kubectl delete pod -l app.kubernetes.io/name=argocd-repo-server -n argocd
```

**Monitor the pod:**
```bash
kubectl get pods -n argocd -w
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-repo-server
```

### Other Common Issues

#### Issue: Cannot Access UI

**Check service:**
```bash
kubectl get svc argocd-server -n argocd
```

**Check if NodePort is open:**
```bash
# On cluster node
curl http://localhost:30080
```

**Check firewall rules:**
```bash
# Allow port 30080 on firewall
firewall-cmd --permanent --add-port=30080/tcp
firewall-cmd --reload
```

#### Issue: Pods Not Scheduling on Target Node

**Check node labels:**
```bash
kubectl get nodes --show-labels | grep argocd-node
```

**Check node resources:**
```bash
kubectl describe node sagar-dr-k8s-worker-01.sagar.com.np
```

**Remove nodeSelector if needed:**
```bash
kubectl patch deployment <deployment-name> -n argocd --type json \
  -p='[{"op": "remove", "path": "/spec/template/spec/nodeSelector"}]'
```

#### Issue: Initial Admin Secret Not Found

**Check if secret exists:**
```bash
kubectl get secret argocd-initial-admin-secret -n argocd
```

**If missing, reset admin password manually:**
```bash
# Generate new hash
htpasswd -nbBC 10 "" YourNewPassword123 | tr -d ':\n'

# Patch secret
kubectl -n argocd patch secret argocd-secret \
  -p '{"stringData": {"admin.password": "<your-hash>", "admin.passwordMtime": "'$(date +%FT%T%Z)'"}}'

# Restart server
kubectl delete pod -l app.kubernetes.io/name=argocd-server -n argocd
```

---

## Verification and Access

### Access ArgoCD UI

**URL:** `http://<node-ip>:30080`

**Example:**
- `http://192.168.1.100:30080`
- `http://worker-01.example.com:30080`

**Login credentials:**
- **Username:** `admin`
- **Password:** Initial password or custom password you set

### Install ArgoCD CLI (Optional)

**Linux/Mac:**
```bash
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd
sudo mv argocd /usr/local/bin/
```

**Verify installation:**
```bash
argocd version
```

### Login via CLI

```bash
argocd login <node-ip>:30080 --username admin --password '<your-password>' --insecure
```

### Verify Installation

```bash
# Check all ArgoCD components
kubectl get all -n argocd

# Check pods status
kubectl get pods -n argocd

# Check service
kubectl get svc argocd-server -n argocd

# Check logs
kubectl logs -n argocd deployment/argocd-server
```

### Create Your First Application

**Via UI:**
1. Login to ArgoCD UI
2. Click "New App"
3. Fill in application details
4. Click "Create"

**Via CLI:**
```bash
argocd app create guestbook \
  --repo https://github.com/argoproj/argocd-example-apps.git \
  --path guestbook \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default
```

---

## Post-Installation Recommendations

### 1. Delete Initial Admin Secret

After setting a custom password, remove the initial secret for security:

```bash
kubectl delete secret argocd-initial-admin-secret -n argocd
```

### 2. Enable RBAC

Configure user accounts and permissions (see separate RBAC guide).

### 3. Setup TLS/HTTPS

For production, configure proper TLS certificates:

```bash
kubectl create secret tls argocd-server-tls \
  --cert=/path/to/cert.crt \
  --key=/path/to/cert.key \
  -n argocd
```

### 4. Configure Ingress (Alternative to NodePort)

For production, use Ingress instead of NodePort:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server-ingress
  namespace: argocd
spec:
  rules:
  - host: argocd.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 80
```

### 5. Setup Monitoring

Monitor ArgoCD with Prometheus and Grafana for production deployments.

### 6. Backup ArgoCD Configuration

Regularly backup ArgoCD ConfigMaps, Secrets, and Applications:

```bash
kubectl get applications -n argocd -o yaml > argocd-apps-backup.yaml
kubectl get secrets -n argocd -o yaml > argocd-secrets-backup.yaml
```

---

## Summary

You have successfully:
- ✅ Installed ArgoCD on Kubernetes
- ✅ Exposed ArgoCD via NodePort on port 30080
- ✅ Configured insecure (HTTP) access
- ✅ (Optional) Pinned ArgoCD pods to specific nodes
- ✅ Set custom admin password
- ✅ Troubleshot common issues
- ✅ Verified installation and access

**Next steps:**
- Configure RBAC for team members
- Deploy your first application
- Setup Git repositories
- Configure SSO (if needed)
- Implement backup strategy

For RBAC configuration, refer to the "ArgoCD RBAC Configuration Guide".
