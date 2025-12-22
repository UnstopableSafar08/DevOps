# ArgoCD RBAC Configuration Guide

This guide walks you through setting up Role-Based Access Control (RBAC) in ArgoCD with multiple users and different permission levels.

## Overview

We'll create two types of users:
- **QA Users**: Limited access to specific applications (read-only + sync)
- **Maintainer Users**: Full control over applications, projects, repositories, and application sets

## Prerequisites

- ArgoCD installed in your Kubernetes cluster
- `kubectl` configured to access your cluster
- `argocd` CLI installed
- Admin access to ArgoCD

## Step 1: Create User Accounts

First, we'll create user accounts in ArgoCD by patching the `argocd-cm` ConfigMap.

```bash
kubectl patch cm argocd-cm -n argocd --type merge -p '
{"data":{
  "admin.enabled":"true",
  "accounts.john":"login",
  "accounts.sagar":"login",
  "accounts.ram":"login",
  "accounts.shyam":"login",
  "accounts.gita":"login"
}}'
```

**What this does:**
- Keeps the admin account enabled
- Creates 5 new user accounts with login capability
- These accounts don't have passwords yet (we'll set them in the next step)

**Verify the accounts were created:**
```bash
kubectl get cm argocd-cm -n argocd -o yaml | grep accounts
```

## Step 2: Set User Passwords

Now we'll set passwords for each user. You need to be logged in as admin to do this.

**Login as admin:**
```bash
argocd login localhost:30080 --username admin --password 'Adm!n@123' --insecure
```

**Note:** Replace `localhost:30080` with your ArgoCD server address if different.

**Set passwords for each user:**
```bash
# Set password for john
argocd account update-password \
  --account john \
  --current-password 'Adm!n@123' \
  --new-password 'john@123#'

# Set password for Sagar
argocd account update-password \
  --account sagar \
  --current-password 'Adm!n@123' \
  --new-password 'Sagar@123#'

# Set password for ram
argocd account update-password \
  --account ram \
  --current-password 'Adm!n@123' \
  --new-password 'ram@123#'

# Set password for shyam
argocd account update-password \
  --account shyam \
  --current-password 'Adm!n@123' \
  --new-password 'shyam@123#'

# Set password for Gita
argocd account update-password \
  --account Gita \
  --current-password 'Adm!n@123' \
  --new-password 'Gita@123#'
```

**What this does:**
- Uses admin credentials (`--current-password`) to authorize the password change
- Sets a new password for each user account

**Verify users can login:**
```bash
argocd account list
```

## Step 3: Configure RBAC Policies

Now we'll define what each user can do by creating/updating the `argocd-rbac-cm` ConfigMap.

**Create the RBAC ConfigMap file** (`argocd-rbac-cm.yaml`):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:none
  policy.csv: |
    # QA Role - Limited access to rc-sand-box application only
    # Permissions: view, list, and sync the rc-sand-box application
    p, role:qa, applications, get, default/rc-sand-box, allow
    p, role:qa, applications, list, default/rc-sand-box, allow
    p, role:qa, applications, sync, default/rc-sand-box, allow
    
    # Additional permissions needed for UI to work properly
    p, role:qa, projects, get, default, allow
    p, role:qa, repositories, get, *, allow
    p, role:qa, clusters, get, *, allow
    
    # Assign john to QA role
    g, john, role:qa

    # Maintainer Role - Full control over applications, projects, repos, and appsets
    # Permissions: all actions (*) on all resources
    p, role:maintainer, applications, *, *, allow
    p, role:maintainer, projects, *, *, allow
    p, role:maintainer, repositories, *, *, allow
    p, role:maintainer, applicationsets, *, *, allow
    
    # Assign users to Maintainer role
    g, sagar, role:maintainer
    g, ram, role:maintainer
    g, shyam, role:maintainer
    g, Gita, role:maintainer
```

**Apply the RBAC configuration:**
```bash
kubectl apply -f argocd-rbac-cm.yaml
```

## Step 4: Restart ArgoCD Server

For the RBAC changes to take effect, restart the ArgoCD server:

```bash
kubectl rollout restart deployment argocd-server -n argocd
```

**Wait for the rollout to complete:**
```bash
kubectl rollout status deployment argocd-server -n argocd
```

## Step 5: Verify RBAC Configuration

**Check the RBAC ConfigMap:**
```bash
kubectl get cm argocd-rbac-cm -n argocd -o yaml
```

**Test user access:**

```bash
# Login as QA user (john)
argocd login localhost:30080 --username john --password 'john@123#' --insecure

# Try to list applications (should only see rc-sand-box)
argocd app list

# Login as Maintainer user (Sagar)
argocd login localhost:30080 --username sagar --password 'Sagar@123#' --insecure

# Try to list applications (should see all applications)
argocd app list
```

## Understanding the RBAC Policy

### Policy Syntax
```
p, <role>, <resource>, <action>, <object>, <effect>
```

- **p**: Policy rule
- **role**: The role name (e.g., role:qa, role:maintainer)
- **resource**: ArgoCD resource type (applications, projects, repositories, etc.)
- **action**: What can be done (get, list, sync, create, update, delete, or * for all)
- **object**: Which specific object (default/rc-sand-box, *, or project/app pattern)
- **effect**: allow or deny

### Group Assignment Syntax
```
g, <user>, <role>
```

- **g**: Group/role assignment
- **user**: The username
- **role**: The role to assign

### QA Role Permissions

| Permission | Resource | Action | Object | Description |
|------------|----------|--------|--------|-------------|
| View | applications | get | default/rc-sand-box | Can view the rc-sand-box app details |
| List | applications | list | default/rc-sand-box | Can see rc-sand-box in the app list |
| Sync | applications | sync | default/rc-sand-box | Can trigger sync for rc-sand-box |
| View Projects | projects | get | default | Can view the default project |
| View Repos | repositories | get | * | Can view repository information |
| View Clusters | clusters | get | * | Can view cluster information |

### Maintainer Role Permissions

| Permission | Resource | Action | Object | Description |
|------------|----------|--------|--------|-------------|
| Full Control | applications | * | * | All actions on all applications |
| Full Control | projects | * | * | All actions on all projects |
| Full Control | repositories | * | * | All actions on all repositories |
| Full Control | applicationsets | * | * | All actions on all application sets |

## Troubleshooting

### Users can't see applications in UI

**Check RBAC logs:**
```bash
kubectl logs -n argocd deployment/argocd-server --tail=100 | grep -i rbac
```

**Common issues:**
1. Missing `list` permission - users need both `get` and `list` to see apps in UI
2. Missing `projects`, `repositories`, or `clusters` permissions
3. Wrong project/application name in the policy
4. RBAC ConfigMap not applied or server not restarted

### Verify application project

```bash
kubectl get application rc-sand-box -n argocd -o yaml | grep project
```

Make sure your RBAC policy matches the correct project name.

### Reset user password

If a user forgets their password:
```bash
argocd login localhost:30080 --username admin --password 'Adm!n@123' --insecure
argocd account update-password --account <username> --current-password 'Adm!n@123' --new-password '<new-password>'
```

## Adding More Users or Applications

### Add a new user
1. Patch argocd-cm to add the account
2. Set the password using argocd CLI
3. Assign the user to a role in argocd-rbac-cm
4. Restart argocd-server

### Give QA access to multiple applications
```yaml
# In argocd-rbac-cm policy.csv
p, role:qa, applications, get, default/app1, allow
p, role:qa, applications, list, default/app1, allow
p, role:qa, applications, sync, default/app1, allow

p, role:qa, applications, get, default/app2, allow
p, role:qa, applications, list, default/app2, allow
p, role:qa, applications, sync, default/app2, allow
```

### Give QA access to all applications in a project
```yaml
# Use wildcard for application name
p, role:qa, applications, get, default/*, allow
p, role:qa, applications, list, default/*, allow
p, role:qa, applications, sync, default/*, allow
```

## Security Best Practices

1. **Use strong passwords** - Enforce password complexity requirements
2. **Principle of least privilege** - Only grant necessary permissions
3. **Regular audits** - Review user access periodically
4. **Rotate passwords** - Change passwords regularly
5. **Monitor access logs** - Check ArgoCD logs for suspicious activity
6. **Disable unused accounts** - Remove or disable accounts that are no longer needed

## Summary

You now have:
- ✅ 5 user accounts created in ArgoCD
- ✅ Passwords set for all users
- ✅ RBAC policies configured with two roles:
  - **QA role** (john): Limited to rc-sand-box application
  - **Maintainer role** (Sagar, ram, shyam, Gita): Full access to all resources
- ✅ Users can login and access resources according to their roles

Each user can now login to ArgoCD UI or CLI with their credentials and will see only the resources they have permission to access.
