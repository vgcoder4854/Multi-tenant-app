# API Reference

Base URL: `/api/v1`. All responses are JSON. Errors use `{"detail": str, "code": str}`.
Interactive docs: `/docs` (Swagger) · machine-readable: `docs/openapi.json`.

**Roles:** `PA` = platform admin · `OA` = org_admin · `M` = manager · `E` = employee.
Endpoints marked "any member" require an active membership in the active organization.
Cross-tenant resource IDs always return **404**.

## Auth — tag `auth`
| Method | Path | Role | Body | Success | Errors / notes |
| --- | --- | --- | --- | --- | --- |
| POST | `/auth/register` | — | `{email, password(min 8), full_name}` | 201 UserOut | 409 `EMAIL_TAKEN`, 422 |
| POST | `/auth/login` | — | `{email, password}` | 200 `{access_token, token_type, expires_in}` | 401 `INVALID_CREDENTIALS`/`USER_INACTIVE` (same message for unknown email) |
| GET | `/auth/me` | token | — | 200 MeOut (with active memberships) | 401 |
| POST | `/auth/switch-organization` | token | `{org_id}` | 200 token scoped to org | 401, 403 `NOT_A_MEMBER` |

## Organizations — tag `organizations`
| Method | Path | Role | Body | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/organizations` | any user | `{name, slug?}` | 201 OrganizationOut | 409 `SLUG_TAKEN` |
| GET | `/organizations/mine` | any user | — | 200 [MyOrganizationOut] | 401 |

## Invitations & members — tags `org`, `invitations`
| Method | Path | Role | Body | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/org/invitations` | OA | `{email, role}` | 201 InvitationCreated (raw token once) | 409 `ALREADY_MEMBER`/`INVITATION_EXISTS` |
| GET | `/org/invitations` | OA | — | 200 [InvitationOut] | 403 |
| DELETE | `/org/invitations/{id}` | OA | — | 204 | 404, 409 `INVITATION_NOT_PENDING` |
| GET | `/org/members` | any member | — | 200 [MemberOut] | 403 |
| PATCH | `/org/members/{user_id}/role` | OA | `{role}` | 200 MemberOut | 404, 409 `LAST_ADMIN` |
| DELETE | `/org/members/{user_id}` | OA | — | 204 | 404, 409 `LAST_ADMIN` |
| POST | `/invitations/accept` | token | `{token}` | 200 OrganizationOut | 403 `INVITATION_EMAIL_MISMATCH`, 404, 409, 422 `INVITATION_EXPIRED` |

## Platform admin — tag `platform-admin`
| Method | Path | Role | Success |
| --- | --- | --- | --- |
| GET | `/platform/organizations` | PA | 200 Page (filters `status`, `name`, `page`, `page_size`) |
| PATCH | `/platform/organizations/{id}/status` | PA | 200 OrganizationOut (audited) |
| GET | `/platform/stats` | PA | 200 counts |
| GET | `/platform/audit-logs` | PA | 200 Page (optional `org_id`) |

## Projects — tag `projects`
| Method | Path | Role | Body | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/projects` | OA | `{name, description?}` | 201 ProjectOut | 409 `PROJECT_NAME_TAKEN` |
| GET | `/projects` | any member | — | 200 [ProjectOut] (role visibility) | 403 |
| GET | `/projects/{id}` | any member | — | 200 ProjectDetailOut (with members) | 404 (also for non-members) |
| PATCH | `/projects/{id}` | OA | `{name?, description?}` | 200 | 404, 409 `PROJECT_NAME_TAKEN` |
| POST | `/projects/{id}/archive` | OA | — | 200 (status archived) | 404, 409 `ALREADY_ARCHIVED` |
| GET | `/projects/{id}/members` | any member | — | 200 [ProjectMemberOut] | 404 |
| POST | `/projects/{id}/members` | OA | `{user_id}` | 204 | 404, 409 `ALREADY_PROJECT_MEMBER`, 422 `USER_NOT_IN_ORG` |
| DELETE | `/projects/{id}/members/{user_id}` | OA | — | 204 | 404 |

## Tasks — tag `tasks`
| Method | Path | Role | Body | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/tasks` | OA, M | `{project_id, title, description?, priority?, status?, assignee_id?, due_date?}` | 201 TaskOut | 404 project, 409 `PROJECT_ARCHIVED`, 422 `ASSIGNEE_NOT_IN_ORG`, 403 `NOT_PROJECT_MEMBER` |
| GET | `/tasks` | any member | query: `project_id, status, priority, assignee_id, due_from, due_to, search, sort_by, sort_dir, page, page_size(≤100)` | 200 Page[TaskOut] | 422 on bad enum |
| GET | `/tasks/{id}` | any member | — | 200 TaskDetailOut (with history) | 404 |
| PATCH | `/tasks/{id}` | OA, M | `{title?, description?, priority?, assignee_id?, due_date?}` | 200 TaskOut | 404, 409 `PROJECT_ARCHIVED`, 422 `ASSIGNEE_NOT_IN_ORG` |
| PATCH | `/tasks/{id}/status` | assignee/OA/M | `{status}` | 200 TaskOut | 403 `NOT_ALLOWED`, 409 `SAME_STATUS`/`INVALID_TRANSITION`/`PROJECT_ARCHIVED` |

## Workflow templates — tag `workflow-templates`
| Method | Path | Role | Body | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/workflow-templates` | OA | `{name, description?, steps:[{name, approver_type, approver_role?, approver_user_id?}]}` | 201 | 409 `TEMPLATE_NAME_TAKEN`, 422 `NO_STEPS`/`INVALID_APPROVER` |
| GET | `/workflow-templates` | any member | — | 200 [WorkflowTemplateOut] | 403 |
| GET | `/workflow-templates/{id}` | any member | — | 200 | 404 |
| PATCH | `/workflow-templates/{id}` | OA | `{name?, description?, is_active?, steps?}` | 200 | 404, 409 `TEMPLATE_NAME_TAKEN`/`TEMPLATE_IN_USE`, 422 |
| POST | `/workflow-templates/{id}/deactivate` | OA | — | 200 | 404 |

## Approval requests — tag `approvals`
| Method | Path | Who | Body | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | `/approval-requests` | any member | `{template_id, title, details?}` | 201 (step 1, pending) | 404, 409 `TEMPLATE_INACTIVE`, 422 `NO_STEPS` |
| GET | `/approval-requests/mine` | any member | — | 200 list | 403 |
| GET | `/approval-requests/pending-for-me` | any member | — | 200 list | 403 |
| GET | `/approval-requests/{id}` | requester/approver/OA | — | 200 detail (steps, decisions, `can_decide`) | 404 |
| POST | `/approval-requests/{id}/decision` | current approver | `{decision: approved\|rejected, comment?}` | 200 | 403 `NOT_AUTHORIZED_APPROVER`, 409 `REQUEST_NOT_PENDING`, 422 (comment required on reject) |
| POST | `/approval-requests/{id}/cancel` | requester | — | 200 | 404, 409 `REQUEST_NOT_PENDING` |

## Notifications — tag `notifications` (+ `admin`)
| Method | Path | Role | Success |
| --- | --- | --- | --- |
| GET | `/notifications` | any member | 200 Page (query `unread_only`, `page`, `page_size`) |
| GET | `/notifications/unread-count` | any member | 200 `{unread}` |
| POST | `/notifications/{id}/read` | owner | 200 (someone else's → 404) |
| POST | `/notifications/read-all` | any member | 200 `{unread}` |
| POST | `/admin/run-due-scan` | OA | 200 `{scanned, notified}` |

## Audit — tag `audit`
| Method | Path | Role | Success |
| --- | --- | --- | --- |
| GET | `/audit-logs` | OA | 200 Page (filters `actor_id`, `action`, `resource_type`, `date_from`, `date_to`) |

## Dashboard — tag `dashboard`
| Method | Path | Role | Success |
| --- | --- | --- | --- |
| GET | `/dashboard/summary` | any member | 200 DashboardSummary (filters `project_id`, `assignee_id`, `status`, `date_from`, `date_to`) |
| GET | `/dashboard/export.csv` | OA, M | 200 `text/csv` (row limit 5000) |

## Meta
| Method | Path | Success |
| --- | --- | --- |
| GET | `/health` | 200 `{status, database, environment}` |
| GET | `/` | 200 links |
