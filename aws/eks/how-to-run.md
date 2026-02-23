# How to Guide.

### Download/Copy the  build.sh and Dockerfile on the server.
```bash
chmod +x build.sh
```
Run the `build.sh` cmd
```bash
./build.sh
```

OUTPUT:
```bash
Building aws-k8s-helm:latest ...
[+] Building 1.1s (13/13) FINISHED                                                                                                             docker:default
 => [internal] load .dockerignore                                                                                                                        0.0s
 => => transferring context: 2B                                                                                                                          0.0s
 => [internal] load build definition from Dockerfile                                                                                                     0.0s
 => => transferring dockerfile: 1.46kB                                                                                                                   0.0s
 => [internal] load metadata for docker.io/library/ubuntu:22.04                                                                                          1.1s
 => [1/9] FROM docker.io/library/ubuntu:22.04@sha256:3ba65aa20f86a0fad9df2b2c259c613df006b2e6d0bfcc8a146afb8c525a9751                                    0.0s
 => CACHED [2/9] RUN apt-get update && apt-get install -y     curl     unzip     jq     ca-certificates     && rm -rf /var/lib/apt/lists/*               0.0s
 => CACHED [3/9] RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"                                                   0.0s
 => CACHED [4/9] RUN unzip awscliv2.zip                                                                                                                  0.0s
 => CACHED [5/9] RUN ./aws/install                                                                                                                       0.0s
 => CACHED [6/9] RUN rm -f awscliv2.zip                                                                                                                  0.0s
 => CACHED [7/9] RUN if [ "latest" = "latest" ]; then         KUBE_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt);     fi &&     curl -LO "  0.0s
 => CACHED [8/9] RUN curl https://get.helm.sh/helm-v3.10.2-linux-amd64.tar.gz -o helm.tar.gz     && tar -zxvf helm.tar.gz     && mv linux-amd64/helm /u  0.0s
 => CACHED [9/9] RUN apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*                                                                      0.0s
 => exporting to image                                                                                                                                   0.0s
 => => exporting layers                                                                                                                                  0.0s
 => => writing image sha256:bb13fcd352b0319b6324b7efcfc4b30d4a8ae2dc7ef3804a68435eede733f3ab                                                             0.0s
 => => naming to docker.io/library/aws-k8s-helm:latest                                                                                                   0.0s

Build complete!

Quick verification:

--- AWS CLI ---
aws-cli/2.33.27 Python/3.13.11 Linux/3.10.0-1160.36.2.el7.x86_64 exe/x86_64.ubuntu.22

--- kubectl ---
Client Version: v1.35.1
Kustomize Version: v5.7.1

--- Helm ---
v3.10.2+g50f003e

--- AWS Identity ---
{
    "UserId": "XXXXXXXXXXXXXXXXXXXX",
    "Account": "XXXXXXXXXXXXXXXXXXXX",
    "Arn": "arn:aws:iam::XXXXXXXXXXXXXXXXXXXX:user/devops"
}

--- EKS Nodes ---
NAME                                               STATUS   ROLES    AGE   VERSION
ip-*.ap-southeast-1.compute.internal   Ready    <none>   71d   v1.32.9-eks-ecaa3a6
ip-*.ap-southeast-1.compute.internal   Ready    <none>   29d   v1.32.9-eks-ecaa3a6
```
