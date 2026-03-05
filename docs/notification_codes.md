# Notification Codes

Stable event codes for frontend routing and UI behavior.

## Payload fields

- `code`: stable machine-readable event code
- `severity`: `info|warning|critical`
- `entity_type`: logical entity type
- `entity_id`: entity identifier as string
- `action_url`: frontend/admin deep-link

## Current codes

- `feedback.new`
  - Trigger: new feedback created by non-admin author
  - Recipients: `SUPER_ADMIN`, `ADMINISTRATOR` (+ legacy system admin aliases)
- `report.daily_submitted`
  - Trigger: employee daily report submitted
  - Recipients: direct manager/teamlead and admin recipients by scope
- `onboarding.intern_completed`
  - Trigger: intern completed regulations onboarding and submitted request
  - Recipients: admin recipients
- `onboarding.intern_approved`
  - Trigger: intern onboarding request approved
  - Recipients: approved intern
- `schedule.weekly_plan_deadline_missed`
  - Trigger: Monday 12:00 deadline missed for weekly plan
  - Recipients: admin recipients

## Role display logic (frontend)

- Use `code` for decision logic and routing.
- Use `severity` for badge color/priority.
- Use `action_url` for CTA button "Open".
- Never rely on localized text for business logic.
