# Image Pull Secrets for a DockerHub.

---

## 1. Create Docker Hub ImagePullSecret

Use **Docker Hub credentials** (username + password or access token).

### Recommended: Use Docker Hub Access Token

Generate a token in Docker Hub
→ `Account Settings` → `Security` → `New Access Token`

### Command

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<dockerhub-username> \
  --docker-password=<dockerhub-access-token-or-password> \
  --docker-email=<email> \
  -n default
```

### Example

```bash
# for a default namespace
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=sagarmalla \
  --docker-password=xxxxxxxxxxxxxxxx \
  --docker-email=sagar@example.com \
  -n default
```

### Verify

```bash
kubectl get secret dockerhub-secret -n default
```

---

## 2. Add Secret to Deployment YAML

### Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      imagePullSecrets:
        - name: dockerhub-secret
      containers:
        - name: my-app
          image: sagarmalla/my-private-image:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8080
```

Apply:

```bash
kubectl apply -f deployment.yaml
```

---

## 3. Recommended (Best Practice): Attach to ServiceAccount

If **many deployments** pull from Docker Hub, attach once.

### Patch default ServiceAccount
Backup the Service Account yaml file.
```bash
kubectl get serviceaccount default -n <namespace> -o yaml > default-sa-backup.yaml
```

Patching a Service Account yaml.
```bash
# for default namespace
kubectl patch serviceaccount default \
  -p '{"imagePullSecrets":[{"name":"dockerhub-secret"}]}'

# specific namespace.
kubectl patch serviceaccount default \
  -n <namespace> \
  -p '{"imagePullSecrets":[{"name":"dockerhub-secret"}]}'
```

Then **remove** `imagePullSecrets` from deployments.

---

## 4. Validation & Debug

### Check Pod Status

```bash
kubectl get pods
```

### If ImagePullBackOff

```bash
kubectl describe pod <pod-name>
```

Typical errors:

* `unauthorized: incorrect username or password`
* `pull access denied`
* `repository does not exist`

---

## 5. Important Notes (Docker Hub Specific)

1. **Public images**

   * No secret required
2. **Private images**

   * Secret is mandatory
3. **Rate limits**

   * Authenticated pulls increase rate limits
4. **Namespace matters**

   * Secret and Deployment must be in the same namespace

---

## 6. Quick One-Liner (CI/CD Friendly)

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=$DOCKER_USER \
  --docker-password=$DOCKER_TOKEN \
  --docker-email=$DOCKER_EMAIL
```

---
