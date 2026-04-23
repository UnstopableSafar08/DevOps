To manage RBAC (Role-Based Access Control) in Jenkins 2.346, you should use the **Role-based Strategy** plugin. If you haven't installed it, go to *Manage Jenkins > Manage Plugins* and install "Role-based Authorization Strategy."

Here is how to set up the roles and assign them to your `devops_test` user so they can only see and interact with your specific view and pipelines.

---

### Step 1: Enable Role-Based Strategy
1.  Go to **Manage Jenkins** > **Configure Global Security**.
2.  Under **Authorization**, select **Role-Based Strategy**.
3.  Click **Save**.

---

### Step 2: Create the Roles
Go to **Manage Jenkins** > **Manage and Assign Roles** > **Manage Roles**.

#### 1. Global Role (Required for Login)
You must give the user "Read" access at the global level so they can actually log in and see the dashboard.
* **Role to add:** `base_read`
* **Permissions:** Check **Overall: Read**.
* Click **Add**.

#### 2. Item Role (Project/Pipeline Level)
This restricts the user to only see jobs starting with `SDK-`.
* **Role to add:** `sdk_developer`
* **Pattern:** `SDK-.*` (This uses Regex to match all pipelines starting with SDK-)
* **Permissions:** Check **Job: Read**, **Job: Build**, **Job: Cancel**, and **Job: Workspace**.
* Click **Add**.

#### 3. View Role (UI Visibility)
This ensures they see the specific tab/view you created.
* **Role to add:** `sdk_view_role`
* **Pattern:** `SDK-MODULES`
* **Permissions:** Check **View: Read**.
* Click **Add** and then click **Save**.

---

### Step 3: Assign Roles to the User
Go to **Manage Jenkins** > **Manage and Assign Roles** > **Assign Roles**.

#### 1. Global Roles
* In the **User/group to add** box, type `devops_test`.
* Click **Add**.
* Check the box for the `base_read` role you created.

#### 2. Item Roles
* In the **User/group to add** box, type `devops_test`.
* Click **Add**.
* Check the box for the `sdk_developer` role.

#### 3. View Roles
* In the **User/group to add** box, type `devops_test`.
* Click **Add**.
* Check the box for the `sdk_view_role`.
* Click **Save**.

---

### Summary Table of Permissions for `devops_test`

| Role Type | Role Name | Pattern | Key Permissions |
| :--- | :--- | :--- | :--- |
| **Global** | `base_read` | N/A | Overall: Read |
| **Item** | `sdk_developer` | `SDK-.*` | Job: Read, Build, Cancel |
| **View** | `sdk_view_role` | `SDK-MODULES` | View: Read |

### Why this works:
* **Pattern Matching:** By using the regex `SDK-.*`, any future pipeline you create (e.g., `SDK-WEB`, `SDK-API`) will automatically be visible to this user without you needing to update the role.
* **Security:** The user will not be able to see or run any jobs that do not start with the `SDK-` prefix, nor will they be able to change Jenkins system settings.

**Note:** Ensure your View name `SDK-MODULES` exactly matches the Pattern in the View Role section (it is case-sensitive).
