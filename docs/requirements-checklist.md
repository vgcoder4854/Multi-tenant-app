# Requirements Traceability Checklist

Every assignment requirement mapped to the code, endpoint and test that satisfies it.
Legend: ✅ implemented & tested · ⚠️ partial / documented limitation.

## Modules

| # | Requirement | Code | Endpoints | Tests |
| --- | --- | --- | --- | --- |
| 1 | Auth: register, login, JWT | `core/security.py`, `services/auth_service.py`, `api/auth.py` | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | `test_security_utils.py`, `test_auth_org.py` |
| 1 | Orgs, memberships, invitations, roles | `services/org_service.py`, `api/organizations.py` | `/organizations`, `/org/*`, `/invitations/accept` | `test_auth_org.py::test_invitation_flow` |
| 1 | Workspace switching | `api/auth.py` | `POST /auth/switch-organization` | `test_auth_org.py::test_create_org_and_switch`, `test_switch_to_foreign_org_is_403` |
| 1 | Suspend / activate orgs (platform) | `services/platform_service.py`, `api/platform.py` | `PATCH /platform/organizations/{id}/status` | `test_auth_org.py::test_platform_admin_stats_and_suspension_blocks_org` |
| 2 | `org_id` on every tenant row | `models/*` | — | schema + composite FKs (PG smoke) |
| 2 | Membership/permission check every op | `api/deps.py` | all protected routes | `test_security.py` (48 parametrized 401 + cross-tenant) |
| 2 | No cross-org access (404) | `services/tenant.py` | all | `test_security.py::test_scenario2_*`, `test_tenant_helpers.py` |
| 2 | Tenant-safe search/filter/export/dashboard | `services/task_service.py`, `dashboard_service.py` | `/tasks`, `/dashboard/*` | `test_dashboard.py`, `test_projects_tasks.py::test_task_filters_and_pagination` |
| 3 | Project CRUD, archive, members | `services/project_service.py`, `api/projects.py` | `/projects*` | `test_projects_tasks.py::test_project_crud_and_duplicate_name`, `test_archived_project_is_read_only` |
| 3 | Task CRUD, assign, priorities/statuses | `services/task_service.py`, `api/tasks.py` | `/tasks*` | `test_projects_tasks.py` |
| 3 | Filter, search, paginate, status history | `task_service.py` | `GET /tasks`, `GET /tasks/{id}` | `test_projects_tasks.py::test_task_status_change_writes_history_and_notifies`, `test_task_filters_and_pagination` |
| 4 | Templates with ordered steps | `services/workflow_service.py`, `api/workflows.py` | `/workflow-templates*` | `test_workflow.py::test_template_validation_and_creation` |
| 4 | Submit request, only approver decides, no re-decide | `services/workflow_engine.py`, `workflow_service.py`, `api/approvals.py` | `/approval-requests*` | `test_workflow_engine.py`, `test_workflow.py` |
| 4 | Full decision history + atomicity | `workflow_service.py` | `/approval-requests/{id}` | `test_workflow.py::test_two_step_approval_success_and_history`, `test_rollback_leaves_no_partial_records` |
| 5 | In-app notifications (all types) | `services/notification_service.py`, `api/notifications.py` | `/notifications*` | `test_notifications.py` |
| 5 | Read/unread, mark read, ownership | `notification_service.py` | `/notifications/{id}/read`, `/read-all` | `test_notifications.py::test_cannot_read_someone_elses_notification` |
| 5 | Due/overdue scan (email optional/mocked) | `jobs/due_scan.py`, `services/email_service.py` | `POST /admin/run-due-scan` | `test_notifications.py::test_due_scan_creates_one_notification_per_task_per_day` |
| 6 | Append-only audit (actor, org, action, resource, ts) | `services/audit_service.py`, migration `37108ea71cca` | `GET /audit-logs`, `GET /platform/audit-logs` | `test_audit.py` (incl. DB trigger) |
| 7 | Dashboard from SQL aggregates, tenant-scoped, filters | `services/dashboard_service.py`, `api/dashboard.py` | `/dashboard/summary`, `/dashboard/export.csv` | `test_dashboard.py` |

## Non-negotiable rules

| Rule | Where |
| --- | --- |
| Authorization & isolation on the backend for every endpoint | `api/deps.py`, `services/tenant.py` |
| Layered architecture (routers → services → models; Pydantic separate) | `app/api`, `app/services`, `app/models`, `app/schemas` |
| DB transactions for multi-record changes; FKs, uniques, indexes | services + `models/*` + migrations |
| Secrets only from env; synthetic data only | `core/config.py`, `.env.example`, `app/seed.py` |
| Correct status codes (401/403/404/409/422) | `core/errors.py` + service raises |
| 404 (not 403) for cross-org resources | `services/tenant.py::get_in_org` |
| Tests verify persisted DB state | all suites assert via the session, e.g. `test_security.py`, `test_workflow.py` |

## Mandatory test scenarios (10)

| # | Scenario | Test |
| --- | --- | --- |
| 1 | Unauthenticated → 401 on every protected endpoint | `test_security.py::test_scenario1_unauthenticated_is_401` (parametrized over 48 routes) |
| 2 | Org A reads Org B's resource by ID → 404, nothing leaks | `test_security.py::test_scenario2_cross_tenant_reads_are_404` (+ writes, notifications) |
| 3 | Employee calls an admin action → 403, no row changed | `test_security.py::test_scenario3_employee_admin_actions_are_403_and_no_change` |
| 4 | Non-approver tries to approve → 403, state unchanged | `test_workflow.py::test_two_step_approval_success_and_history` |
| 5 | Final request cannot be decided again → 409 | `test_workflow.py::test_two_step_approval_success_and_history`, `test_double_decision_second_fails_with_409` |
| 6 | Assign task to non-member → 422, assignee unchanged | `test_projects_tasks.py::test_task_create_assign_and_validate_assignee` |
| 7 | Approval history recorded (row, decider, ts, comment, step) | `test_workflow.py::test_two_step_approval_success_and_history` |
| 8 | Failed op leaves no partial records | `test_workflow.py::test_rollback_leaves_no_partial_records` |
| 9 | Notifications only to intended recipients, not the actor | `test_notifications.py::test_assignment_notifies_assignee_not_actor` |
| 10 | Audit records actor, org, action, resource | `test_audit.py::test_audit_records_actor_org_action_resource` |

**Extra coverage:** suspended org blocked (`test_auth_org.py`), last org_admin cannot be
removed/demoted (`test_auth_org.py::test_last_admin_cannot_be_demoted_or_removed`),
duplicate invitation 409 (`test_auth_org.py::test_invitation_flow`), pagination/filters
tenant-scoped (`test_projects_tasks.py`, `test_dashboard.py`), audit append-only enforced
at the DB level (`test_audit.py::test_audit_is_append_only_at_db_level`).

## Gaps / deviations (documented)

- **✅ Docker verified.** `docker compose up --build` was executed: db (PostgreSQL 16, healthy),
  backend (migrations + uvicorn on :8000), frontend (nginx SPA on :3000) and mailhog. A live
  API round-trip and cross-tenant isolation checks passed on the containerized stack.
- **⚠️ Migrations:** one initial migration per schema group (4 files) rather than
  per-table; still fully reversible on SQLite and PostgreSQL.
- **⚠️ Email is mocked** (`services/email_service.py`) — by design, per the assignment.
- **⚠️ Enum columns** are CHECK-constrained strings (portable) rather than native PG enum
  types; the assignment explicitly allows "CHECK-constrained strings".
