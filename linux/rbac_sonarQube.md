# SonarQube RBAC Configuration Guide

**Community Build v25.8.0.112029**  
**Server:** http://10.13.133.177:9000  
**Scanner CLI:** 7.2.0.5079 | Linux x86_64

---

## 1. Architecture Overview

The SonarQube RBAC setup is designed so that developers can scan code directly from their laptops. Each new project is auto-created during the first scan and automatically receives the correct permissions through Permission Templates.

```
SonarQube Server (10.13.133.177:9000)
        |
   [sonar-scanner] <--- Dev Laptop (using User Token)
        |
   [Permission Template auto-applied on project creation]
        |
   [dev-team group gets correct permissions instantly]
```

---

## 2. Groups

Three groups are created to separate access levels. These groups are the foundation of the RBAC structure.

| Group Name | Purpose |
|---|---|
| dev-team | All developers - can scan and view dev-.* projects |
| dev-lead | Tech leads - can also manage issues and administer projects |
| dev-readonly | Read-only access to dev-.* projects only |
| sonar-admins | Internal SonarQube administrators only |

Navigation path to create groups:

```
Administration > Security > Groups > Create Group
```

---

## 3. Permission Templates

Permission Templates are the key mechanism for auto-applying permissions to newly created projects. When a developer scans a new project, SonarQube auto-creates it and immediately applies the matching template based on the project key pattern.

### 3.1 Template: dev-team-template

```
Administration > Security > Permission Templates > Create Template

  Name               : dev-team-template
  Description        : Auto-applied to all projects starting with dev-
  Project Key Pattern: dev-.*
```

SonarQube uses regular expressions for patterns. The pattern `dev-.*` matches any project key that starts with `dev-` followed by any characters.

| Permission | dev-team | dev-lead | dev-readonly |
|---|---|---|---|
| Browse (view results) | Yes | Yes | Yes |
| See Source Code | Yes | Yes | No |
| Execute Analysis | Yes | Yes | No |
| Administer Issues | No | Yes | No |
| Administer Project | No | No | No |

### 3.2 Template: default-template (catch-all)

```
  Name               : default-template
  Project Key Pattern: .*
  Groups with Browse : sonar-admins ONLY
```

> Note: The default catch-all template ensures any project not matching `dev-.*` is only visible to administrators.

### 3.3 Set dev-team-template as Default

After creating the template, set it as the default so all new projects automatically inherit it:

```
Administration > Security > Permission Templates
  > Click the 3-dot menu next to dev-team-template
  > Select 'Set Default'
```

### 3.4 Pattern Reference

| Pattern | Matches | Does Not Match |
|---|---|---|
| `dev.*` | dev-payment, dev-frontend, devops-tool | backend-app, mobile-app |
| `dev-.*` | dev-payment, dev-frontend | devops-tool, backend |
| `dev-backend-.*` | dev-backend-payment, dev-backend-auth | dev-frontend-app |

---

## 4. User Accounts and Token Management

### 4.1 Token Types

| Token Type | Scope | Best For | Risk Level |
|---|---|---|---|
| User Token | Inherits user permissions | Individual devs on laptop | Medium |
| Project Analysis Token | One specific project only | CI/CD pipeline per project | Low |
| Global Analysis Token | All projects | Shared team scanner | High - avoid |

### 4.2 Service Account (Recommended for Shared Token)

SonarQube does not support group-level tokens. Tokens are always tied to a user account. For a shared dev team token, create a dedicated service account:

```
Administration > Security > Users > Create User

  Login    : svc-devteam-scanner
  Name     : Dev Team Scanner Bot
  Email    : devteam-scanner@company.com

Then assign: svc-devteam-scanner > dev-team group
```

### 4.3 Generate Token for a User

Method 1 - User generates their own token (self-service):

```
Login as the user
  > Top Right Avatar > My Account > Security
  > Generate Token
    Name       : dev-laptop-token
    Type       : User Token
    Expiration : 90 days
  > Click Generate > Copy token immediately
```

Method 2 - Admin generates token via UI:

```
Administration > Security > Users
  > Find the user > Click Tokens icon
  > Generate Token
    Name       : dev-laptop-token
    Type       : User Token
    Expiration : 90 days
```

Method 3 - Admin generates token via API:

```bash
curl -u $ADMIN_TOKEN: -X POST \
  "http://10.13.133.177:9000/api/user_tokens/generate" \
  -d "login=dev_esewa" \
  -d "name=dev-laptop-token" \
  -d "type=USER_TOKEN" \
  -d "expirationDate=2026-06-01"
```

> Note: The token is shown only once after generation. Copy it before closing the window.

### 4.4 Validate Token

After generating a token, validate it using the correct curl syntax. The token goes in the username field with an empty password:

```bash
# Correct syntax - token as username, password empty
curl -u squ_YOUR_TOKEN: \
  "http://10.13.133.177:9000/api/authentication/validate" \
  | jq .

# Expected response
{ "valid": true }

# Wrong - do not mix username and token
curl -u username:squ_token     <- incorrect
```

---

## 5. Project Visibility and Access Isolation

### 5.1 Root Cause of Visibility Leakage

If a user can see projects they should not have access to, there are two common causes:

- Projects are set to Public visibility - any logged-in user can see them
- The sonar-users built-in group has Browse permission - all authenticated users automatically belong to sonar-users

### 5.2 sonar-users Built-in Group

Every authenticated user in SonarQube automatically belongs to the `sonar-users` group. This group cannot be deleted. To prevent unwanted access, all permissions must be removed from it:

```
Administration > Security > Global Permissions
  > sonar-users row
  > Uncheck ALL permissions

Administration > Security > Permission Templates
  > Open EACH template
  > Remove sonar-users from Browse permission
```

### 5.3 Set Non-Dev Projects to Private

Existing projects that do not start with `dev-` must be set to private visibility manually or via API:

```
Per project:
  Project Settings > Permissions > Visibility > Private
```

```bash
# Bulk via API
curl -s -u $ADMIN_TOKEN: \
  "http://10.13.133.177:9000/api/projects/search?ps=500" \
  | jq -r '.components[].key' \
  | grep -v "^dev-" | while read project; do
    curl -s -u $ADMIN_TOKEN: -X POST \
      "http://10.13.133.177:9000/api/projects/update_visibility" \
      -d "project=${project}" \
      -d "visibility=private"
  done
```

### 5.4 Set Default New Project Visibility to Private

```
Administration > Configuration > General Settings > General
  > Default New Project Visibility > Private
```

### 5.5 Access Isolation Architecture

| Project Key | Template Applied | Who Can See |
|---|---|---|
| dev-payment | dev-team-template | dev-team, dev-lead, dev-readonly |
| dev-auth | dev-team-template | dev-team, dev-lead, dev-readonly |
| dev-frontend | dev-team-template | dev-team, dev-lead, dev-readonly |
| ops-infrastructure | ops-team-template | ops-team only |
| staging-backend | staging-template | qa-team only |
| anything-else | default-template | sonar-admins only |

---

## 6. Developer Laptop Setup

### 6.1 Project Naming Convention

All project keys must start with `dev-` so that the permission template pattern `dev-.*` matches and auto-applies on first scan:

```
Correct project keys (template will auto-apply):
  sonar.projectKey=dev-payment-service
  sonar.projectKey=dev-frontend-dashboard
  sonar.projectKey=dev-auth-service
  sonar.projectKey=dev-mobile-ios

Incorrect (template will not match):
  sonar.projectKey=payment-service
  sonar.projectKey=frontend-dashboard
```

### 6.2 sonar-project.properties

Each developer adds this file to the root of each project repository:

```properties
sonar.projectKey=dev-payment-service
sonar.projectName=Payment Service
sonar.projectVersion=1.0
sonar.sources=src
sonar.exclusions=**/node_modules/**,**/dist/**,**/*.test.js
sonar.sourceEncoding=UTF-8
sonar.host.url=http://10.13.133.177:9000
sonar.token=${SONAR_TOKEN}
```

### 6.3 Running a Scan

The developer sets their token as an environment variable and runs the scanner. The project is auto-created with correct permissions on first scan:

```bash
export SONAR_TOKEN=squ_their_personal_token

sonar-scanner \
  -Dsonar.projectKey=dev-payment-service \
  -Dsonar.sources=. \
  -Dsonar.host.url=http://10.13.133.177:9000 \
  -Dsonar.token=$SONAR_TOKEN
```

> Note: Never hardcode the token in the properties file or commit it to Git. Always use an environment variable.

---

## 7. Common Errors and Fixes

| Error Message | Cause | Fix |
|---|---|---|
| Not authorized to analyze | Token has no Execute Analysis permission | Add Execute Analysis to dev-team in template |
| Not authorized to create project | Missing Create Projects global permission | Grant Create Projects to dev-team globally |
| valid: false on token check | Token revoked, expired, or wrong value | Regenerate token and validate again |
| Connection refused | Wrong URL or SonarQube not running | Verify http://10.13.133.177:9000 is reachable |
| Dev user sees non-dev projects | sonar-users has Browse or projects are Public | Remove sonar-users permissions, set projects Private |

### 7.1 Fix: Not Authorized to Analyze or Create

```
Step 1 - Grant Create Projects globally to dev-team:
  Administration > Security > Global Permissions
  > dev-team row > Check 'Create Projects'

Step 2 - Confirm Execute Analysis in template:
  Administration > Security > Permission Templates
  > dev-team-template
  > dev-team group > Check 'Execute Analysis'

Step 3 - Confirm user is in dev-team group:
  Administration > Security > Users
  > Find user > Groups > Must show dev-team
```

---

## 8. Security Best Practices

| Practice | Reason |
|---|---|
| Use tokens, never passwords in scanner config | Tokens are revocable and auditable |
| Set token expiration to 90 days maximum | Limits exposure if a token is leaked |
| Use project-level permissions, not global | Principle of least privilege |
| Each developer has their own token | Provides a full audit trail per user |
| Never commit tokens to Git | Use environment variables instead |
| Disable anonymous access | Prevent unauthenticated users from browsing |
| Remove Browse from sonar-users group | Prevents all authenticated users seeing all projects |
| Remove Browse from Anyone group | Prevents unauthenticated access to projects |
| Set default project visibility to Private | New projects are hidden until explicitly granted |

### 8.1 Disable Anonymous Access

```
Administration > Configuration > Security
  > Force user authentication: ON
```

---

## 9. Setup Checklist

### Groups

- Create dev-team group
- Create dev-lead group
- Create dev-readonly group
- Create sonar-admins group

### Permission Templates

- Create dev-team-template with pattern dev-.*
- Assign dev-team: Browse, See Source Code, Execute Analysis
- Assign dev-lead: Browse, See Source Code, Execute Analysis, Administer Issues
- Assign dev-readonly: Browse only
- Create default-template with pattern .* (sonar-admins Browse only)
- Set dev-team-template as default template

### Security Hardening

- Remove all permissions from Anyone group
- Remove all permissions from sonar-users group
- Set default new project visibility to Private
- Set all existing non-dev-.* projects to Private
- Enable Force User Authentication
- Grant Create Projects globally to dev-team group

### User and Token Management

- Create user accounts for all dev team members
- Assign all developers to dev-team group
- Each developer generates their own User Token
- Set token expiration policy to 90 days
- Store tokens in environment variables, never in files

### Verification

- Validate token: `curl -u squ_token: .../api/authentication/validate`
- Run test scan with dev-.* project key - should succeed
- Log in as dev-readonly-user - should only see dev-.* projects
- Confirm non-dev-.* projects are not visible to dev users

---

*SonarQube Community Build v25.8.0.112029 | Scanner CLI 7.2.0.5079 | Server: 10.13.133.177:9000*
