# Access and Manage the EKS Cluster via remote Server.

A lightweight Docker image that bundles AWS CLI v2, kubectl, and Helm into a single container. Designed to manage AWS EKS clusters without installing any tools directly on the host machine.

---

## Contents

- [Overview](#overview)
- [Tools Included](#tools-included)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Author](#author)

---

## Overview

Instead of installing AWS CLI, kubectl, and Helm on your host, this project wraps all three tools inside a Docker container. The host's AWS credentials, kubeconfig, and Helm configuration are mounted as volumes so the container behaves exactly like a locally installed toolchain.

A shell alias makes the container transparent — you type `aws`, `kubectl`, or `helm` commands as normal and they run inside the container.

---

## Tools Included

| Tool       | Purpose                                      |
|------------|----------------------------------------------|
| AWS CLI v2 | Interact with AWS services (EKS, S3, IAM...) |
| kubectl    | Manage Kubernetes clusters on EKS            |
| Helm       | Deploy and manage Kubernetes applications    |

---

## Requirements

- Docker installed and running on the host
- `~/.aws/credentials` configured with valid AWS keys
- `~/.kube/config` pointing to a valid EKS cluster
- Linux or macOS host

---

## Project Structure

```
.
├── Dockerfile      # Builds the aws-k8s-helm image
├── build.sh        # Builds the image and runs verification checks
└── README.md       # This file
```

---

## Setup

### 1. Clone or copy the project files

```bash
mkdir aws-k8s-helm && cd aws-k8s-helm
# Place Dockerfile and build.sh here
```

### 2. Build the image

```bash
chmod +x build.sh
./build.sh
```

The script will build the image and automatically verify AWS CLI, kubectl, Helm, your AWS identity, and EKS node connectivity.

### 3. Add the alias to your shell

Add the following to your `~/.bashrc` or `~/.bash_profile`:

```bash
alias aws='docker run --rm -it \
  -v ~/.aws:/root/.aws \
  -v ~/.kube:/root/.kube \
  -v ~/.helm:/root/.helm \
  -v ~/.config/helm:/root/.config/helm \
  -v ~/.cache/helm:/root/.cache/helm \
  aws-k8s-helm'
```

Reload your shell:

```bash
source ~/.bashrc
```

---

## Usage

Once the alias is set, use the tools exactly as you normally would:

```bash
# AWS CLI
aws sts get-caller-identity
aws eks list-clusters --region us-east-1

# Connect to an EKS cluster
aws eks update-kubeconfig --region us-east-1 --name my-cluster

# kubectl
aws kubectl get nodes
aws kubectl get pods -A
aws kubectl describe node <node-name>

# Helm
aws helm list
aws helm repo add stable https://charts.helm.sh/stable
aws helm install my-release stable/nginx
```

---

## How It Works

```
Host                          Container (aws-k8s-helm)
----                          ------------------------
~/.aws          ----------->  /root/.aws       (AWS credentials)
~/.kube         ----------->  /root/.kube      (kubeconfig / EKS access)
~/.helm         ----------->  /root/.helm      (Helm data)
~/.config/helm  ----------->  /root/.config/helm  (Helm config)
~/.cache/helm   ----------->  /root/.cache/helm   (Helm cache)
```

The container starts, runs the command, and exits. No state is stored inside the container — everything is read from and written to the host via mounted volumes.

---

## Troubleshooting

| Problem | Cause | Fix |
|--------|-------|-----|
| `Unable to locate credentials` | AWS not configured | Run `aws configure` on the host |
| `Unable to find image locally` | Image not built | Run `./build.sh` |
| `kubectl: no such file` | Wrong entrypoint | Ensure `bash -c` is used in docker run |
| `~/.helm` invalid volume name | Tilde not expanded | Use `$HOME` instead of `~` in scripts |
| `error: You must be logged in` | Expired kubeconfig token | Re-run `eks update-kubeconfig` |
| `Unauthorized` | IAM lacks EKS permissions | Attach `eks:DescribeCluster` policy to IAM user |

---

## Author

| Field   | Details        |
|---------|----------------|
| Author  | DevOps Team    |
| Created | 2024           |
| Version | 1.0.0          |
