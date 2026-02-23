#!/bin/bash
# =============================================================
#
# Author      : Sagar Malla
# Email       : sagarmalla08@gmail.com
# Date        : 23 Feb, 2026

# Script Name  : build.sh
# Description  : Builds the aws-k8s-helm Docker image locally
#                and verifies AWS CLI, kubectl, and Helm tools
#                are functional inside the container.
#
# Tools Included:
#   - AWS CLI v2   : Interact with AWS services
#   - kubectl      : Manage Kubernetes (EKS) clusters
#   - Helm         : Deploy and manage Kubernetes packages
#
# Usage        : ./build.sh
# Requirements : Docker must be running on the host
#                ~/.aws/credentials must be configured
#                ~/.kube/config must point to a valid EKS cluster
#
# Volumes Mounted (host -> container):
#   ~/.aws          -> /root/.aws          (AWS credentials)
#   ~/.kube         -> /root/.kube         (kubeconfig)
#   ~/.helm         -> /root/.helm         (Helm data)
#   ~/.config/helm  -> /root/.config/helm  (Helm config)
#   ~/.cache/helm   -> /root/.cache/helm   (Helm cache)
#
# Author       : DevOps Team
# Created      : 2024
# Version      : 1.0.0
# =============================================================
set -e

IMAGE_NAME="aws-k8s-helm"
IMAGE_TAG="latest"

echo "Building ${IMAGE_NAME}:${IMAGE_TAG} ..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo ""
echo "Build complete!"
echo ""
echo "Quick verification:"
echo ""

# Reusable docker run wrapper function
# Mounts all required host directories into the container
# and executes the given command via bash -c
drun() {
  docker run --rm -i \
    -v $HOME/.aws:/root/.aws \
    -v $HOME/.kube:/root/.kube \
    -v $HOME/.helm:/root/.helm \
    -v $HOME/.config/helm:/root/.config/helm \
    -v $HOME/.cache/helm:/root/.cache/helm \
    ${IMAGE_NAME}:${IMAGE_TAG} \
    bash -c "$1"
}

echo "--- AWS CLI ---"
drun "aws --version"

echo ""
echo "--- kubectl ---"
drun "kubectl version --client"

echo ""
echo "--- Helm ---"
drun "helm version --short"

echo ""
echo "--- AWS Identity ---"
drun "aws sts get-caller-identity"

echo ""
echo "--- EKS Nodes ---"
drun "kubectl get nodes"
