# Audit Migration Status

## Goal
Unify audit logging through `apps.audit.log_event(...)` with:
- primary backend: `accounts.AuditLog`
- legacy backend: `security.SystemLog` (read compatibility)
- no DB schema changes during migration

## Current Configuration
- `AUDIT_PRIMARY_BACKEND=accounts`
- `AUDIT_LEGACY_BACKEND=security`
- `AUDIT_WRITE_MODE=primary_only`

## Migrated Modules

### 1) Accounts
Status: `done` (MVP)

Implemented via facade:
- `login_success`
- `login_failed`
- `login_blocked_lockout`
- `login_blocked_manual`

Source: `accounts/views.py`

### 2) Onboarding Core
Status: `done`

Implemented via facade:
- `onboarding_day_completed`
- `onboarding_day_completed_idempotent`
- `onboarding_overview_viewed`
- `onboarding_day_created`
- `onboarding_day_updated`
- `onboarding_day_deleted`
- `onboarding_material_created`
- `onboarding_material_updated`
- `onboarding_material_deleted`
- `onboarding_progress_viewed_admin`

Sources:
- `onboarding_core/audit.py`
- `onboarding_core/views.py`

### 3) Reports
Status: `done` (submit/review flow)

Implemented via facade:
- `report_submitted`
- `report_rejected_empty`
- `report_deadline_blocked`
- `report_edit_conflict`
- `report_review_status_changed`

Sources:
- `reports/audit.py`
- `reports/views.py`

### 4) Work Schedule
Status: `done` (choose-schedule flow)

Implemented via facade:
- `schedule_selection_invalid_payload`
- `schedule_selection_not_found`
- `schedule_selected_for_approval`

Sources:
- `work_schedule/audit.py`
- `work_schedule/views.py`

### 5) Content
Status: `done` (feedback flow)

Implemented via facade:
- `feedback_created`
- `feedback_updated_admin`
- `feedback_status_changed_admin`

Sources:
- `content/audit.py`
- `content/views.py`

### 6) Attendance
Status: `done` (MVP)

Implemented via facade:
- `attendance_mark_created`
- `attendance_mark_updated`
- `attendance_mark_change_denied`

Sources:
- `apps/attendance/audit.py`
- `apps/attendance/views.py`

## Verified End-to-End
Events verified in `accounts.AuditLog` via API + shell checks:
- reports events (submit/reject/review)
- work_schedule events (invalid/not_found/success)
- content feedback events (create/update/status_change)

## Legacy / Compatibility Notes
- `security.SystemLog` remains available as deprecated read-only legacy model.
- Deprecation policy: all new writes must use `apps.audit.log_event(...)` only.
- Existing domain logs (`reports.OnboardingReportLog`) remain unchanged.
- No model removals, no table deletions, no migrations added for this phase.

## Guardrails
- Do not log PII in `metadata` (email, phone, full text payloads).
- Keep `object_id` as string (`str(uuid)` / string identifier).
- Keep one business action mapped to one audit event.
- Run `python manage.py check_audit_writes` to block direct `AuditLog/SystemLog` writes outside facade backends.
- Use event-name constants from `apps.audit.events.AuditEvents` instead of raw string actions.

## Next Phase
1. Add module-level event contracts as docs for remaining apps.
2. Migrate remaining write flows (if any) to facade-first approach.
3. Add CI check to prevent direct audit writes outside facade.
4. Plan eventual read unification for legacy `security.SystemLog`.
