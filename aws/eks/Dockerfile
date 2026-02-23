# Use Ubuntu 22.04 as the base image
FROM ubuntu:22.04

# Image Metadata (Author)
LABEL org.opencontainers.image.authors="Sagar Malla <sagarmalla08gmail.com>" \
      org.opencontainers.image.description="Ubuntu 22.04 image with AWS CLI v2, kubectl and Helm preinstalled" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="Local Build" \
      org.opencontainers.image.vendor="Sagar Malla"

# Set environment variables to non-interactive (this prevents some prompts)
ENV DEBIAN_FRONTEND=noninteractive

# Define the Kubernetes version as a build argument with a default value
ARG KUBE_VERSION=latest

# Run updates and install prerequisites including jq
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    jq \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

# Unzip AWS CLI v2
RUN unzip awscliv2.zip

# Install AWS CLI v2
RUN ./aws/install

# Cleanup AWS CLI installer
RUN rm -f awscliv2.zip

# Install kubectl using the specified version or fetch the latest
RUN if [ "${KUBE_VERSION}" = "latest" ]; then \
        KUBE_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt); \
    fi && \
    curl -LO "https://dl.k8s.io/release/${KUBE_VERSION}/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (latest stable version)
RUN curl https://get.helm.sh/helm-v3.10.2-linux-amd64.tar.gz -o helm.tar.gz \
    && tar -zxvf helm.tar.gz \
    && mv linux-amd64/helm /usr/local/bin/helm \
    && rm -rf linux-amd64 helm.tar.gz

# Cleanup and final touches
RUN apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set default command
CMD ["bash"]
