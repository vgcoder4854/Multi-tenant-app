# ER Diagram

Shared database, shared schema, **row-level tenancy**: every tenant-owned table
carries `org_id`. Global tables are `users` and `organizations`.

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ MEMBERSHIPS : "has members"
    USERS         ||--o{ MEMBERSHIPS : "belongs to"
    ORGANIZATIONS ||--o{ INVITATIONS : "invites"
    USERS         ||--o{ INVITATIONS : "invited_by"

    ORGANIZATIONS ||--o{ PROJECTS : "owns"
    PROJECTS      ||--o{ PROJECT_MEMBERS : "has members"
    USERS         ||--o{ PROJECT_MEMBERS : "is member"
    PROJECTS      ||--o{ TASKS : "contains"
    TASKS         ||--o{ TASK_STATUS_HISTORY : "status changes"

    ORGANIZATIONS ||--o{ WORKFLOW_TEMPLATES : "owns"
    WORKFLOW_TEMPLATES ||--o{ WORKFLOW_STEPS : "ordered steps"
    WORKFLOW_TEMPLATES ||--o{ APPROVAL_REQUESTS : "instantiated as"
    APPROVAL_REQUESTS  ||--o{ APPROVAL_DECISIONS : "decisions"

    ORGANIZATIONS ||--o{ NOTIFICATIONS : "targets"
    USERS         ||--o{ NOTIFICATIONS : "receives"
    ORGANIZATIONS ||--o{ AUDIT_LOGS : "records"

    ORGANIZATIONS {
        uuid id PK
        string name
        string slug UK
        enum status "active|suspended"
        datetime created_at
    }
    USERS {
        uuid id PK
        string email UK "lowercased"
        string full_name
        string password_hash
        bool is_platform_admin
        bool is_active
        datetime created_at
    }
    MEMBERSHIPS {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        enum role "org_admin|manager|employee"
        enum status "active|removed"
        datetime created_at
    }
    INVITATIONS {
        uuid id PK
        uuid org_id FK
        string email
        enum role
        string token_hash UK
        enum status "pending|accepted|revoked|expired"
        uuid invited_by FK
        datetime expires_at
        datetime created_at
    }
    PROJECTS {
        uuid id PK
        uuid org_id FK
        string name
        text description
        enum status "active|archived"
        uuid created_by FK
        datetime created_at
        datetime updated_at
    }
    PROJECT_MEMBERS {
        uuid id PK
        uuid org_id FK
        uuid project_id FK
        uuid user_id FK
    }
    TASKS {
        uuid id PK
        uuid org_id FK
        uuid project_id FK
        string title
        text description
        enum priority "low|medium|high|critical"
        enum status "todo|in_progress|blocked|completed"
        uuid assignee_id FK
        uuid created_by FK
        date due_date
        datetime created_at
        datetime updated_at
    }
    TASK_STATUS_HISTORY {
        uuid id PK
        uuid org_id FK
        uuid task_id FK
        enum from_status
        enum to_status
        uuid changed_by FK
        datetime changed_at
    }
    WORKFLOW_TEMPLATES {
        uuid id PK
        uuid org_id FK
        string name
        text description
        bool is_active
        uuid created_by FK
        datetime created_at
        datetime updated_at
    }
    WORKFLOW_STEPS {
        uuid id PK
        uuid org_id FK
        uuid template_id FK
        int step_order
        string name
        enum approver_type "role|user"
        enum approver_role "org_admin|manager"
        uuid approver_user_id FK
    }
    APPROVAL_REQUESTS {
        uuid id PK
        uuid org_id FK
        uuid template_id FK
        uuid requester_id FK
        string title
        jsonb details
        enum status "pending|approved|rejected|cancelled"
        int current_step_order
        datetime submitted_at
        datetime completed_at
        int version "optimistic lock"
    }
    APPROVAL_DECISIONS {
        uuid id PK
        uuid org_id FK
        uuid request_id FK
        uuid step_id FK
        int step_order
        uuid decided_by FK
        enum decision "approved|rejected"
        text comment
        datetime decided_at
    }
    NOTIFICATIONS {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        enum type
        string title
        text body
        string resource_type
        uuid resource_id
        bool is_read
        datetime read_at
        datetime created_at
    }
    AUDIT_LOGS {
        uuid id PK
        uuid org_id FK "nullable = platform-level"
        uuid actor_id FK
        string action
        string resource_type
        uuid resource_id
        jsonb metadata
        datetime created_at
    }
```

## Key integrity rules

- **Composite foreign keys** `(org_id, parent_id) → (org_id, id)` on `tasks`,
  `project_members`, `task_status_history`, `workflow_steps`, `approval_requests`,
  `approval_decisions`: the database itself refuses a row whose parent lives in a
  different organization.
- `tasks(org_id, assignee_id) → memberships(org_id, user_id)`: an assignee must have
  a membership in the same organization.
- `UNIQUE(org_id, user_id)` on memberships; `UNIQUE(project_id, user_id)` on project
  members; `UNIQUE(template_id, step_order)`; `UNIQUE(request_id, step_order)`.
- Partial unique index on `invitations(org_id, email) WHERE status='pending'`.
- `audit_logs` is append-only via a database trigger.
