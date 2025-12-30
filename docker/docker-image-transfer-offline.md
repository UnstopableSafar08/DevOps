## Docker Image Transfer Guide

In offline or secure environments where servers can’t access Docker Hub, Docker images are manually saved and transferred as tar files. This ensures consistent, reliable builds without depending on internet connectivity.

This guide shows how to save, transfer, and load a Docker image between servers.


#### 1. Pull the image
```bash
docker pull --platform linux/amd64 eclipse-temurin:21-jdk-alpine
```

#### 2. Save the image as a tar file
```bash
docker save -o eclipse-temurin-21-jdk-alpine.tar eclipse-temurin:21-jdk-alpine
```
#### 3. Transfer the tar file to another server (example using scp)
```bash
# copy the tar file to the another server
# you can either scp or rsync
scp eclipse-temurin-21-jdk-alpine.tar user@<target-server-ip>:/path/to/destination/
```
#### 4. Load the image on the target server
```bash
docker load -i /path/to/eclipse-temurin-21-jdk-alpine.tar
```
#### 5. Verify the image
```bash
docker images | grep eclipse-temurin
```
#### 6. (Optional) Tag the image
```bash
docker tag eclipse-temurin:21-jdk-alpine temurin:21
```

---

## Docker Image Transfer Guide (CentOS 7)

This guide shows how to save, transfer, and load the CentOS 7 Docker image between servers.

```bash
#### 1. Pull the image
```bash
docker pull --platform linux/amd64 centos:7
```
#### 2. Save the image as a tar file
```bash
docker save -o centos-7.tar centos:7
```
#### 3. Transfer the tar file to another server (example using scp)
```bash
# copy the tar file to the another server
# you can either scp or rsync
scp centos-7.tar user@<target-server-ip>:/path/to/destination/
```
#### 4. Load the image on the target server
```bash
docker load -i /path/to/centos-7.tar
```
#### 5. Verify the image
```bash
docker images | grep centos
```
#### 6. (Optional) Tag the image
```bash
docker tag centos:7 centos7:latest
```
