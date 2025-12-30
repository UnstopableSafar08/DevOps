# Jenkins Installation on Docker with Git and Docker Support

This guide explains how to install and run Jenkins using Docker with **Git and Docker installed inside the container**.

---

## 1. Dockerfile for Jenkins with Git and Docker

```dockerfile
FROM jenkins/jenkins:lts

# Switch to root to install packages
USER root

# Install Docker, Git, and other dependencies
RUN apt-get update && \
    apt-get install -y git apt-transport-https ca-certificates curl gnupg lsb-release && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && \
    usermod -aG docker jenkins && \
    rm -rf /var/lib/apt/lists/*

# Switch back to jenkins user
USER jenkins

# Expose Jenkins ports
EXPOSE 8080 50000
```

---

## 2. Build and Run Jenkins Container

```bash
# Build the custom Jenkins image
docker build -t jenkins-with-docker:latest .

# Run the container with Docker socket mounted
docker run -d \
  --name jenkins-docker \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins-with-docker:latest
```

- Mounting `/var/run/docker.sock` allows Jenkins to run Docker commands.
- Jenkins user is added to the Docker group.
- Git is installed for repository access.

---

## 3. Access Jenkins

- Open your browser: `http://<server-ip>:8080`
- Retrieve the initial admin password:

```bash
docker exec jenkins-docker cat /var/jenkins_home/secrets/initialAdminPassword
```
- Follow the setup wizard to install plugins and create the first admin user.

---

## 4. Optional: Docker Compose Setup

Create a `docker-compose.yml`:

```yaml
version: "3"
services:
  jenkins:
    build: .
    container_name: jenkins-docker
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
volumes:
  jenkins_home:
```
  
  
Explanation of your docker-compose.yml:

- version: "3" → Compose file format version.
- services: jenkins → Defines the Jenkins container.
- build: . → Builds image from the local Dockerfile (includes Git & Docker).
- container_name: jenkins-docker → Names the running container.
- ports:
    - 8080:8080 → Jenkins Web UI
    - 50000:50000 → Jenkins agent connections

- volumes:
    - jenkins_home:/var/jenkins_home → Persist Jenkins data
    - /var/run/docker.sock:/var/run/docker.sock → Allow Jenkins to run Docker commands on the host
- volumes: jenkins_home → Named volume managed by Docker.

In short: This Compose file builds and runs a Jenkins container with persistent data, Git and Docker installed, exposes necessary ports, and enables Docker-in-Docker functionmallaty.


Then run:

```bash
docker-compose up -d
```

---

**Notes:**

- Ensure Docker has at least **2GB RAM** for Jenkins.
- For production, consider using a **reverse proxy with SSL** for secure access.
- This setup allows Jenkins to build Docker images and interact with Git repositories inside pipelines.
