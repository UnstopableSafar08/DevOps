**Applying ArgoCD RBAC ConfigMap**

To apply the changes, I can use the following `kubectl` command to patch the ConfigMap:

```
kubectl -n argocd patch configmap argocd-cm --type merge -p '{"data":{"policy.csv":"..."} }'
```

However, it's easier to apply the full YAML directly. 

If needed, restart the `argocd-server` to ensure the changes take effect. Use this command:

```
kubectl rollout restart deployment argocd-server -n argocd
```

This will ensure the new configuration is picked up.
### Argo CD RBAC policy (goal)
Grant **user `abc`** the following permissions on the single Argo CD application **`applications/argocd/rc-sand-box`**: **sync**, **refresh**, and **readonly (get)**.

---

### ConfigMap snippet to add to `argocd-cm`
Add the following `policy.csv` entries to your `argocd-cm` in the `argocd` namespace (append to any existing `policy.csv`):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  policy.csv: |
    # Role that has access to the single application
    p, role:rc-sand-box-access, applications, get, applications/argocd/rc-sand-box, allow
    p, role:rc-sand-box-access, applications, sync, applications/argocd/rc-sand-box, allow
    p, role:rc-sand-box-access, applications, refresh, applications/argocd/rc-sand-box, allow

    # Bind the user 'abc' to that role
    g, user:abc, role:rc-sand-box-access
```

**Notes**
- The `p, ...` lines define the role permissions for the specific application path `applications/argocd/rc-sand-box`.
- The `g, ...` line binds the Argo CD user `abc` to the role.
- If you already have a `policy.csv`, merge/append these lines rather than replacing the whole file.

---

### Apply the change
Save the YAML above to a file (e.g., `argocd-rbac-patch.yaml`) and apply:

```bash
kubectl apply -f argocd-rbac-patch.yaml
```

If you appended to an existing `policy.csv` manually, you can patch the ConfigMap instead.

---

### Reload Argo CD (if needed)
Argo CD usually picks up ConfigMap changes automatically. If you want to ensure the server reloads, restart the server deployment:

```bash
kubectl -n argocd rollout restart deployment argocd-server
```

---

### Verification
1. Log in as `abc` (or use `argocd` CLI with that user) and confirm:
   - You can **view** the application (readonly/get).
   - You can **sync** the application.
   - You can **refresh** the application status.
