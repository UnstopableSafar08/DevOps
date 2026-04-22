# Why Your JFrog Artifactory Is Publicly Accessible (And How to Fix It)

## Overview

If your JFrog Artifactory instance is accessible without login, and users can:

* Browse repositories
* View artifacts
* Download files

Then your Artifactory is exposed via anonymous access.

This is a common misconfiguration and can lead to serious security risks.

---

## Root Cause

### 1. Anonymous Access Enabled

JFrog includes a built-in `anonymous` user.

If enabled:

```
Anyone can access Artifactory without authentication
```

---

### 2. Anonymous User Has Read Permissions

If permissions are configured like:

```
User: anonymous
Permissions: READ
```

Then all repositories become publicly visible.

---

### 3. Open UI Access

If the web interface is accessible:

```
http://<your-artifactory>:8081/artifactory
```

Anyone can browse repositories without login.

---

## How to Verify

### Check via Browser

Open:

```
http://<your-artifactory>:8081/artifactory/webapp
```

If it loads without login, anonymous access is enabled.

---

## How to Fix (Step-by-Step)

### Step 1: Disable Anonymous Access

Navigate to:

```
Admin → Security → General
```

Uncheck:

```
Allow Anonymous Access
```

---

### Step 2: Remove Anonymous Permissions

Go to:

```
Admin → Security → Permissions
```

For each permission target:

* Remove `anonymous` user
  or
* Remove READ permission

---

### Step 3: Verify Repository Access

Go to:

```
Admin → Repositories
```

Ensure:

* Repositories are not unintentionally exposed
* Only authenticated users can access

---

### Step 4: Optional Reverse Proxy Restriction

If using NGINX or Apache:

* Restrict access by IP
* Allow only internal networks

---

## Security Risks

If anonymous access is enabled:

| Risk               | Impact                             |
| ------------------ | ---------------------------------- |
| Repository listing | Exposes internal project structure |
| Artifact download  | Leaks binaries                     |
| Metadata exposure  | Reveals versions and dependencies  |

This effectively makes your artifacts publicly accessible.

---

## Real-World Scenario

You may observe:

* Able to browse repositories without login
* Upload fails with 403 Forbidden

This means:

```
anonymous → READ access
authenticated user → NO deploy permission
```

Permissions are inconsistent.

---

## Best Practices

### Disable Anonymous Access

```
No login → No access
```

---

### Create Dedicated Users

Instead of using admin:

* jenkins-ci → Deploy permissions
* developers → Read permissions
* admins → Full access

---

### Use Permission Targets

Define access per repository:

| Role       | Permission    |
| ---------- | ------------- |
| CI/CD      | Deploy + Read |
| Developers | Read          |
| Admins     | Full          |

---

### Principle of Least Privilege

Grant only required access:

```
Avoid using admin credentials in pipelines
```

---

## Final Checklist

* Anonymous access disabled
* Anonymous user removed from permissions
* Repositories secured
* CI user created with deploy rights
* Admin usage minimized

---

## Summary

Your Artifactory is publicly accessible because:

```
Anonymous access is enabled
AND
Anonymous user has read permissions
```

Fixing this ensures:

* Secure artifact storage
* Controlled access
* Production-ready setup

---

## Next Steps

For advanced setups, consider:

* Repository segregation (dev, staging, prod)
* Artifact promotion pipelines
* Integration with CI/CD tools
* Reverse proxy security

---

Maintainer: Sagar Malla
Role: DevOps Engineer
