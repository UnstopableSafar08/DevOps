# EKS Remote Access Setup Guide

Step-by-step guide to configure a remote Linux server to access and manage an AWS EKS cluster using AWS CLI, kubectl, and Helm — all running inside the aws-k8s-helm Docker container.

---

## Contents

- [Prerequisites](#prerequisites)
- [Step 1 - Install Docker](#step-1---install-docker)
- [Step 2 - Configure AWS Credentials (~/.aws)](#step-2---configure-aws-credentials-aws)
- [Step 3 - Connect to EKS and Generate Kubeconfig (~/.kube)](#step-3---connect-to-eks-and-generate-kubeconfig-kube)
- [Step 4 - Helm Directories (~/.helm, ~/.config/helm, ~/.cache/helm)](#step-4---helm-directories)
- [Step 5 - Build the Docker Image](#step-5---build-the-docker-image)
- [Step 6 - Set the Alias](#step-6---set-the-alias)
- [Step 7 - Verify Everything](#step-7---verify-everything)
- [IAM Permissions Reference](#iam-permissions-reference)
- [Common Errors](#common-errors)

---

## Prerequisites

- A remote Linux server (RHEL / Ubuntu / Amazon Linux 2)
- An AWS account with an existing EKS cluster
- An IAM user or IAM role with EKS permissions
- AWS Access Key ID and Secret Access Key for that IAM user

---

## Step 1 - Install Docker

### Amazon Linux 2 / RHEL

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

### Verify Docker

```bash
docker --version
# Docker version 24.x.x
```

---

## Step 2 - Configure AWS Credentials (~/.aws)

This creates `~/.aws/credentials` and `~/.aws/config`.

### Option A - Interactive setup (recommended for first time)

```bash
# Install AWS CLI temporarily on the host just to configure credentials
# Or run it via the container after building the image

mkdir -p ~/.aws

# Create credentials file manually
cat > ~/.aws/credentials << 'CREDS'
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
CREDS

# Create config file
cat > ~/.aws/config << 'CONF'
[default]
region = us-east-1
output = json
CONF

# Lock down permissions
chmod 600 ~/.aws/credentials
chmod 600 ~/.aws/config
```

Replace `YOUR_ACCESS_KEY_ID` and `YOUR_SECRET_ACCESS_KEY` with your actual IAM credentials.

### Where to get AWS Access Keys

1. Log in to the AWS Console
2. Go to IAM -> Users -> Select your user
3. Click "Security credentials" tab
4. Under "Access keys" click "Create access key"
5. Copy the Access Key ID and Secret Access Key (shown only once)

### Option B - Using named profiles (for multiple AWS accounts)

```bash
cat >> ~/.aws/credentials << 'CREDS'

[production]
aws_access_key_id = PROD_ACCESS_KEY_ID
aws_secret_access_key = PROD_SECRET_ACCESS_KEY

[staging]
aws_access_key_id = STG_ACCESS_KEY_ID
aws_secret_access_key = STG_SECRET_ACCESS_KEY
CREDS

cat >> ~/.aws/config << 'CONF'

[profile production]
region = us-east-1
output = json

[profile staging]
region = ap-southeast-1
output = json
CONF
```

Use a named profile:
```bash
export AWS_PROFILE=production
```

### Verify AWS credentials

```bash
docker run --rm -i \
  -v $HOME/.aws:/root/.aws \
  aws-k8s-helm bash -c "aws sts get-caller-identity"
```

Expected output:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

---

## Step 3 - Connect to EKS and Generate Kubeconfig (~/.kube)

The `~/.kube/config` file tells kubectl which cluster to connect to and how to authenticate.

### Create the directory

```bash
mkdir -p ~/.kube
chmod 700 ~/.kube
```

### List available EKS clusters

```bash
docker run --rm -i \
  -v $HOME/.aws:/root/.aws \
  aws-k8s-helm bash -c "aws eks list-clusters --region us-east-1"
```

Output example:
```json
{
    "clusters": [
        "my-production-cluster",
        "my-staging-cluster"
    ]
}
```

### Generate kubeconfig for your cluster

```bash
docker run --rm -i \
  -v $HOME/.aws:/root/.aws \
  -v $HOME/.kube:/root/.kube \
  aws-k8s-helm bash -c \
  "aws eks update-kubeconfig --region us-east-1 --name my-production-cluster"
```

This writes `~/.kube/config` on your host automatically via the volume mount.

### For a named profile

```bash
docker run --rm -i \
  -v $HOME/.aws:/root/.aws \
  -v $HOME/.kube:/root/.kube \
  aws-k8s-helm bash -c \
  "aws eks update-kubeconfig --region us-east-1 --name my-production-cluster --profile production"
```

### Verify kubeconfig

```bash
docker run --rm -i \
  -v $HOME/.aws:/root/.aws \
  -v $HOME/.kube:/root/.kube \
  aws-k8s-helm bash -c "kubectl get nodes"
```

---

## Step 4 - Helm Directories

Helm creates these automatically on first run. You can also create them manually.

```bash
mkdir -p ~/.helm
mkdir -p ~/.config/helm
mkdir -p ~/.cache/helm
chmod 700 ~/.helm ~/.config/helm ~/.cache/helm
```

### Initialize Helm and add common repos

```bash
docker run --rm -i \
  -v $HOME/.aws:/root/.aws \
  -v $HOME/.kube:/root/.kube \
  -v $HOME/.helm:/root/.helm \
  -v $HOME/.config/helm:/root/.config/helm \
  -v $HOME/.cache/helm:/root/.cache/helm \
  aws-k8s-helm bash -c "
    helm repo add stable https://charts.helm.sh/stable
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo update
    helm repo list
  "
```

---

## Step 5 - Build the Docker Image

```bash
# Clone or copy the project files into a directory
mkdir -p ~/aws-k8s-helm && cd ~/aws-k8s-helm
# Place Dockerfile and build.sh here

chmod +x build.sh
./build.sh
```

---

## Step 6 - Set the Alias

Add the alias to your shell profile so it persists across sessions:

```bash
cat >> ~/.bashrc << 'ALIAS'

# aws-k8s-helm container alias
alias aws='docker run --rm -it \
  -v ~/.aws:/root/.aws \
  -v ~/.kube:/root/.kube \
  -v ~/.helm:/root/.helm \
  -v ~/.config/helm:/root/.config/helm \
  -v ~/.cache/helm:/root/.cache/helm \
  aws-k8s-helm'
ALIAS

source ~/.bashrc
```

---

## Step 7 - Verify Everything

Run each check in order:

```bash
# 1. AWS CLI version
aws --version

# 2. AWS identity (confirms credentials work)
aws sts get-caller-identity

# 3. List EKS clusters
aws eks list-clusters --region us-east-1

# 4. kubectl version
aws kubectl version --client

# 5. List nodes (confirms EKS connectivity)
aws kubectl get nodes

# 6. List all pods
aws kubectl get pods -A

# 7. Helm version
aws helm version --short

# 8. List Helm repos
aws helm repo list
```

All commands should return output without errors.

---

## IAM Permissions Reference

The IAM user needs the following minimum permissions to manage EKS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters",
        "eks:ListNodegroups",
        "eks:DescribeNodegroup",
        "eks:AccessKubernetesApi"
      ],
      "Resource": "*"
    }
  ]
}
```

To attach this policy in the AWS Console:
1. Go to IAM -> Users -> Select your user
2. Click "Add permissions" -> "Attach policies directly"
3. Create a new inline policy with the JSON above
4. Or attach the AWS managed policy `AmazonEKSClusterPolicy`

Also ensure your IAM user is added to the EKS `aws-auth` ConfigMap. Ask your cluster admin to run:

```bash
kubectl edit configmap aws-auth -n kube-system
```

And add:
```yaml
mapUsers:
  - userarn: arn:aws:iam::123456789012:user/your-username
    username: your-username
    groups:
      - system:masters
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Unable to locate credentials` | ~/.aws not configured | Complete Step 2 |
| `Error loading config file` | ~/.kube/config missing or corrupt | Re-run `eks update-kubeconfig` |
| `Unauthorized` | IAM user not in aws-auth | Ask admin to add user to aws-auth ConfigMap |
| `cluster not found` | Wrong region or cluster name | Run `eks list-clusters` to check |
| `You must be logged in to the server` | kubeconfig token expired | Re-run `eks update-kubeconfig` |
| `cannot get nodes at the cluster scope` | Insufficient RBAC permissions | Check aws-auth ConfigMap groups |
| `Image not found` | Image not built | Run `./build.sh` |

---

## Directory Summary

| Directory | Purpose | Created By |
|-----------|---------|------------|
| `~/.aws` | AWS credentials and region config | You (Step 2) |
| `~/.kube` | Kubeconfig for EKS cluster access | `eks update-kubeconfig` (Step 3) |
| `~/.helm` | Helm release data | Helm on first run (Step 4) |
| `~/.config/helm` | Helm configuration | Helm on first run (Step 4) |
| `~/.cache/helm` | Helm chart cache | Helm on first run (Step 4) |
