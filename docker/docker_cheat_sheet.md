### **Docker Commands Cheat Sheet**

---

### Docker Container Management

```bash
docker ps                         # list running containers
docker ps -a                      # list all containers (including stopped)
docker run <image>                # start a new container from an image
docker run -d <image>             # start a container in detached mode
docker run -it <image> /bin/bash  # start a container with interactive terminal
docker exec -it <container> /bin/bash  # execute a command inside a running container
docker stop <container>           # stop a running container
docker start <container>          # start a stopped container
docker restart <container>        # restart a container
docker rm <container>             # remove a container
docker logs <container>           # view container logs
docker inspect <container>        # show detailed container information
```

---

### Docker Image Management

```bash
docker images                     # list all Docker images
docker pull <image>               # download an image from Docker Hub
docker build -t <name> .          # build an image from Dockerfile
docker rmi <image>                # remove a Docker image
docker inspect <image>            # show detailed image information
docker history <image>            # show image build history
```

---

### Docker Volume & Bind Mounts

```bash
docker volume ls                  # list Docker volumes
docker volume create <name>       # create a named Docker volume
docker volume inspect <name>      # inspect a Docker volume
docker volume rm <name>           # remove a Docker volume
```

#### Named Volume Mount

```bash
docker run -v myvol:/data <image>                 # mount named volume to container
docker run -v myvol:/data:ro <image>              # mount named volume as read-only
```

#### Bind Mount (Host Path)

```bash
docker run -v /host/path:/container/path <image>      # bind mount host directory
docker run -v /host/path:/container/path:ro <image>   # bind mount as read-only
```

#### Modern --mount Syntax (Recommended for Production)

```bash
docker run --mount source=myvol,target=/data <image>  # named volume using --mount
docker run --mount type=bind,source=/host/path,target=/data <image>  # bind mount
```

---

### Docker Network Management

```bash
docker network ls               # list Docker networks
docker network create <name>    # create a Docker network
docker network inspect <name>   # inspect a Docker network
docker network rm <name>        # remove a Docker network
```

---

### Miscellaneous Docker Commands

```bash
docker info                     # display Docker system information
docker version                  # show Docker version details
docker stats                    # show container resource usage
docker login                    # log in to Docker Hub
docker logout                   # log out from Docker Hub
```

---

### Quick Rule of Thumb

```bash
-v myvol:/path                  # use for named volumes (Docker-managed)
-v /host/path:/path             # use for bind mounts (host-managed)
--mount                         # preferred for clarity and production
```
