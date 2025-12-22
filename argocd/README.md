# ArgoCD Local User & RBAC Implementation  
ArgoCD is a GitOps-based, declarative continuous delivery platform for Kubernetes. Creating multiple users within ArgoCD improves security, governance, and team collaboration by enforcing Role-Based Access Control (RBAC) and the principle of least privilege.

Key advantages of using multiple users with RBAC:
- Granular Access Control: Assign specific permissions to users based on their responsibilities, ensuring precise control over resources.
- Enhanced Security: Restricts users to only the resources and actions they require, reducing the potential for accidental or malicious changes.
- Auditable Activity: Every user action is logged, providing traceability for compliance, debugging, and incident investigation.
- Environment Isolation: Teams or projects can work in segregated environments, preventing changes in one area from affecting others.
- Streamlined Collaboration: Users can contribute to deployments independently while adhering to access policies, improving team efficiency.

Prerequisites:
* An existing K8S cluster.
* ArgoCD installed and running.
* Admin credentials for ArgoCD to configure users and roles.

By creating users and assigning roles, organizations can securely manage application access and maintain operational compliance in their GitOps workflows.

---
Step-by-step guide to enable ArgoCD admin access, create local users (`qa_user`, `devops_user`), assign roles and permissions, reset passwords, and automate configuration using `kubectl patch`. Includes a deep dive into RBAC syntax for policy rules.

---

> [!IMPORTANT]
> Remember to make a backup of the default argocd configmap in case you need to rollback.
```bash
# Backup argocd-cm
kubectl get cm argocd-cm -n argocd -o yaml > argocd-cm-backup.yaml
# Backup argocd-rbac-cm
kubectl get cm argocd-rbac-cm -n argocd -o yaml > argocd-rbac-cm-backup.yaml
```

---
## 1. Enable Admin User and Add Local Accounts

By default, ArgoCD may have the `admin` account disabled.  
You can enable it and add new local users in **two ways**:

### Option A — Manual Edit

```bash
kubectl edit configmap argocd-cm -n argocd
```

Add or modify the `data:` section:

```yaml
kind: ConfigMap
data:
  admin.enabled: "true"
  accounts.admin: login, apiKey
  accounts.qa_user: login, apiKey
  accounts.devops_user: login, apiKey
```

Then restart deployments:

```bash
kubectl rollout restart deployment argocd-server -n argocd
```

### Option B — Using `kubectl patch` (Automated, safer in CI/CD)

```bash
kubectl patch cm argocd-cm -n argocd --type merge -p '
{"data":{
  "admin.enabled":"true",
  "accounts.qa_user":"login,apiKey",
  "accounts.devops_user":"login,apiKey"
}}'
```

This adds `qa_user` and `devops_user` accounts with **login + API key** capability  
(API key allows CLI authentication and integration pipelines).

*Note : update the user(s)' name and roles accordingly.*

---

## 2. Reset Passwords for New Accounts

Get Argo CD Admin Password, The Argo CD auto-generates the admin password as a secret.
```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d; echo
```

After creating the accounts, use the **admin** account to set passwords:

#### Install the argocd cli tool.
```bash
# Install argocdcli on master server or remote server.
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd
argocd version
```

We can update or set a user’s password using the Argo CD CLI tool or from inside the Argo CD pod. In both cases, the following commands work fine.
for e.g.
```bash
##### ---- VM/remote server(argocd-cli)---- #####
[root@k8s-master argocd]# argocd version
argocd: v3.2.0+66b2f30
  BuildDate: 2025-11-04T15:21:01Z
  GitCommit: 66b2f302d91a42cc151808da0eec0846bbe1062c
  GitTreeState: clean
  GoVersion: go1.25.0
  Compiler: gc
  Platform: linux/amd64
argocd-server: v3.2.0+66b2f30
  BuildDate: 2025-11-04T14:51:35Z
  GitCommit: 66b2f302d91a42cc151808da0eec0846bbe1062c
  GitTreeState: clean
  GoVersion: go1.25.0
  Compiler: gc
  Platform: linux/amd64
  Kustomize Version: v5.7.0 2025-06-28T07:00:07Z
  Helm Version: v3.18.4+gd80839c
  Kubectl Version: v0.34.0
  Jsonnet Version: v0.21.0
[root@k8s-master argocd]#


##### ---- inside the pod ---- #####
[root@k8s-master argocd]# kubectl get pods -n argocd | grep argocd-server
argocd-server-57d9cc9bcf-rcvjm                      1/1     Running   0             61m
[root@k8s-master argocd]#
[root@k8s-master argocd]# kubectl exec -it argocd-server-57d9cc9bcf-rcvjm -n argocd -- /bin/sh
$
$ argocd version
argocd: v3.2.0+66b2f30
  BuildDate: 2025-11-04T14:51:35Z
  GitCommit: 66b2f302d91a42cc151808da0eec0846bbe1062c
  GitTreeState: clean
  GoVersion: go1.25.0
  Compiler: gc
  Platform: linux/amd64
argocd-server: v3.2.0+66b2f30
  BuildDate: 2025-11-04T14:51:35Z
  GitCommit: 66b2f302d91a42cc151808da0eec0846bbe1062c
  GitTreeState: clean
  GoVersion: go1.25.0
  Compiler: gc
  Platform: linux/amd64
  Kustomize Version: v5.7.0 2025-06-28T07:00:07Z
  Helm Version: v3.18.4+gd80839c
  Kubectl Version: v0.34.0
  Jsonnet Version: v0.21.0
```

### Set Password for a newly create user(s).

```bash
# Log in as admin
argocd login <argocd-server-ip>:30080 --username admin --password <admin-password> --insecure

# Now set passwords for new users
argocd account update-password --account qa_user \
  --current-password <admin-password> --new-password MyStrongQaPass123

argocd account update-password --account devops_user \
  --current-password <admin-password> --new-password MyStrongDevOpsPass123
```

**Key Points:**
- Admin can update any local user's password using their own current password (--current-password).
- Works for `initial setup`, ``updates``, or `resets` (no need to know the user's old password).
- `--insecure` skips TLS verification (use only if self-signed cert or HTTP).
- Applies only to local accounts (not SSO/LDAP users).


output:
```bash
[root@k8s-master argocd]# kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d; echo
n4vtzIpW4r0ILcYp
[root@k8s-master argocd]# # Log in as admin
argocd login 192.168.121.111:30080 --username admin --password 'n4vtzIpW4r0ILcYp' --insecure
'admin:login' logged in successfully
Context '192.168.121.111:30080' updated
[root@k8s-master argocd]#
[root@k8s-master argocd]# # Now set passwords for new users
argocd account update-password --account qa_user \
  --current-password 'n4vtzIpW4r0ILcYp' --new-password MyPass123
Password updated
[root@k8s-master argocd]# argocd account update-password --account devops_user \
  --current-password 'n4vtzIpW4r0ILcYp' --new-password MyPass123
Password updated
[root@k8s-master argocd]#
```
Here, `192.168.121.111` is my k8s master server ip.

<br>

---

<br>

> [!INFO] 
#### (Optional) For Your Knowledge.
### 1. Admin set/update the user's password.
```bash
argocd login <argocd-server-ip>:30080 --username admin --password '<admin_password>' --insecure && \
argocd account update-password --account qa_user --new-password 'MyStrongPass123' --server<argocd-server-ip>:30080 --insecure
argocd account update-password --account devops_user_user --new-password 'MyStrongPass123' --server<argocd-server-ip>:30080 --insecure
```
- Admin sets or resets any user's password
- Admin login password needed.
- Admin does NOT need the user's current password
Output:
```bash
[root@k8s-master argocd]# # using admin user set/update the password of user
[root@k8s-master argocd]# argocd login 192.168.121.111:30080 --username admin --password '<admin_password>' --insecure && \
argocd account update-password --account qa_user --new-password 'MyStrongPass123' --server 192.168.121.111:30080 --insecure
'admin:login' logged in successfully
Context '192.168.121.111:30080' updated
*** Enter password of currently logged in user (admin):
Password updated
[root@k8s-master argocd]#
``` 
### 2. User own password update.
```bash
argocd login <argocd-server-ip>:30080 --username qa_user --password 'MyStrongQaPass123' --insecure && \
argocd account update-password --new-password 'MyStrongPass123'
```
- User changes their own password
- User must log in first using current password
output:
```bash
[root@k8s-master argocd]# argocd login 192.168.121.111:30080 --username qa_user --password 'MyStrongQaPass123' --insecure && argocd account update-password --new-password 'MyStrongPass123'
'qa_user:login' logged in successfully
Context '192.168.121.111:30080' updated
*** Enter password of currently logged in user (qa_user): MyStrongQaPass123
Password updated
Context '192.168.121.111:30080' updated
[root@k8s-master argocd]# 
``` 


---

## 3. Configure RBAC Policy Rules

You can manage user permissions in the ConfigMap `argocd-rbac-cm`.

### Option A — Manual Edit

```bash
kubectl edit configmap argocd-rbac-cm -n argocd
```

Paste the following under `data:`:

```yaml
apiVersion: v1
data:
  policy.default: role:none
  policy.csv: |
    # QA user - read-only, but can sync applications (my-app)
    p, role:qa, applications, get, */my-app, allow       # view my-app
    p, role:qa, applications, list, */my-app, allow      # list my-app
    p, role:qa, applications, sync, */my-app, allow      # sync my-app
    p, role:qa, projects, get, *, allow                        # view projects (needed for UI)
    g, qa_user, role:qa                            # assign role to qa_user

    # Maintainer role - full control over apps, projects, repos, appsets
    # syntax : policy_type, <role>, <resource>, <object>, <action>, <effect>
    p, role:maintainer, applications, *, *, allow
    p, role:maintainer, projects, *, *, allow
    p, role:maintainer, repositories, *, *, allow
    p, role:maintainer, applicationsets, *, *, allow
    g, devops_user, role:maintainer

    # DevOps role (extra: clusters + accounts)
    # p, role:devops, clusters, *, *, allow
    # p, role:devops, accounts, *, *, allow
    # g, devops_user, role:devops
kind: ConfigMap
```
> [!NOTE] 
> The configuration above is merely an example.

### Option B — Using `kubectl patch` (Automated)

```bash
kubectl patch cm argocd-rbac-cm -n argocd --type merge -p '
{"data":{
  "policy.default": "role:none",
  "policy.csv": "# Built-in readonly for qa\ng, qa_user, role:readonly\n\n# Maintainer role (apps, projects, repos, appsets)\np, role:maintainer, applications, *, *, allow\np, role:maintainer, projects, *, *, allow\np, role:maintainer, repositories, *, *, allow\np, role:maintainer, applicationsets, *, *, allow\ng, devops_user, role:maintainer\n\n# DevOps role (extra: clusters + accounts)\np, role:devops, clusters, *, *, allow\np, role:devops, accounts, *, *, allow\ng, devops_user, role:devops\n"
}}'
```
*Note : update the user(s)' name and roles accordingly.*

Then restart RBAC components:

```bash
kubectl rollout restart deployment argocd-server -n argocd
```

---

## 4. RBAC Syntax Explained

ArgoCD uses **Casbin-style** policy rules.  
Each line defines either a **permission** (`p`) or **group mapping** (`g`).

### 4.1 Permission Rules (`p`)

**Format:**
```
p, <role>, <resource>, <object>, <action>, <effect>
```

| Field | Description | Example |
|--------|--------------|----------|
| `p` | Policy rule type | Always starts with `p` |
| `<role>` | Logical role name | `role:maintainer` |
| `<resource>` | ArgoCD resource type (`applications`, `projects`, `repositories`, `clusters`, `accounts`, etc.) | `applications` |
| `<object>` | Specific object or wildcard (`*`) | `*` for all |
| `<action>` | Operation (e.g. `get`, `create`, `update`, `delete`, `sync`, `*`) | `*` (all actions) |
| `<effect>` | Allow or deny | `allow` |

**Example:**
```text
p, role:maintainer, applications, *, *, allow
```
→ Grants **maintainer** role full control (`*`) over all ArgoCD **applications**.

### 4.2 Group Rules (`g`)

**Format:**
```
g, <user>, <role>
```

| Field | Description | Example |
|--------|--------------|----------|
| `g` | Group mapping type | Always starts with `g` |
| `<user>` | Username or group name | `devops_user` |
| `<role>` | Role assigned | `role:maintainer` |

**Example:**
```text
g, devops_user, role:maintainer
```
→ Assigns the **maintainer** role to the user **devops_user**.

---

### Combined Example

```text
p, role:maintainer, applications, *, *, allow
g, devops_user, role:maintainer
```

**Meaning:**  
1. The role `maintainer` has full access to all applications.  
2. The user `devops_user` inherits that permission set by being bound to `role:maintainer`.

---

## 5. Verify Configuration

### List all ArgoCD accounts:
```bash
argocd account list
```

Output:

```bash
[root@k8s-master argocd]# argocd account list
NAME         ENABLED  CAPABILITIES
admin        true     login, login, apiKey
devops_user  true     login, apiKey
qa_user      true     login, apiKey
[root@k8s-master argocd]#
```

### Test user access:
```bash
argocd admin settings rbac can qa_user applications get my-app allow
argocd admin settings rbac can devops_user clusters create * allow
```

---

## 6. Quick Reference Table

| User | Role | Permissions | Description |
|------|------|-------------|--------------|
| **admin** | role:admin | Full access | Superuser account |
| **qa_user** | role:readonly | View-only | Can view and sync apps only |
| **devops_user** | role:maintainer + role:devops | Manage all | Full control over apps, projects, clusters |


## 7. Remove users from argocd-cm (delete the accounts)
#### Deletes the qa_user and devops_user accounts from ArgoCD.

```bash
kubectl patch cm argocd-cm -n argocd --type merge -p '
{"data":{
  "accounts.qa_user": null,
  "accounts.devops_user": null
}}'
```

#### Remove roles from argocd-rbac-cm (delete RBAC policies)
```bash
kubectl patch cm argocd-rbac-cm -n argocd --type merge -p '
{"data":{
  "policy.csv": "\
# Maintainer and DevOps roles removed\n\
# QA role removed\n"
}}'
```
This removes all the role assignments for qa_user and devops_user.
You can keep other roles intact if needed.


#### Restarting ArgoCD server to apply changes
```bash
kubectl rollout restart deployment -n argocd
```

## Benefits of This Approach
- Delegates responsibilities without giving full admin access.
- Ensures users can only access what they need (least privilege).
- Reduces risk of accidental or malicious changes to critical resources.
- Provides clear separation between development (qa_user) and operational (devops_user) responsibilities.


## Conclusion:
By carefully defining roles, binding users to those roles, and using ArgoCD’s RBAC system, teams can safely manage applications, clusters, and user accounts while maintaining strong security practices. This approach is essential for scaling ArgoCD in production environments.


## References
- <a href="https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/" target="_blank">Official Documentaion of ArgoCD</a>
- <a href="https://medium.com/@mohitbishesh7/create-users-in-argocd-and-assigning-rbac-role-based-access-control-45721183a360" target="_blank">Create ArgoCD Users & Assigning RBAC: Role Based Access Control over AWS EKS Cluster.</a>

