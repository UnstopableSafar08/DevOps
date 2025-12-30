# Docker Image Transfer Guide (CentOS 7)

This guide shows how to save, transfer, and load the CentOS 7 Docker image between servers.

```bash
# 1. Pull the image
docker pull --platform linux/amd64 centos:7

# 2. Save the image as a tar file
docker save -o centos-7.tar centos:7

# 3. Transfer the tar file to another server (example using scp)
scp centos-7.tar user@<target-server-ip>:/path/to/destination/

# 4. Load the image on the target server
docker load -i /path/to/centos-7.tar

# 5. Verify the image
docker images | grep centos

# 6. (Optional) Tag the image
docker tag centos:7 centos7:latest
```
