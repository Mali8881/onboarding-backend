class AuditEvents:
    # Accounts
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_BLOCKED_LOCKOUT = "login_blocked_lockout"
    LOGIN_BLOCKED_MANUAL = "login_blocked_manual"
    PROFILE_UPDATED = "profile_updated"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_CONFIRMED = "password_reset_confirmed"

    # Onboarding
    ONBOARDING_DAY_COMPLETED = "onboarding_day_completed"
    ONBOARDING_DAY_COMPLETED_IDEMPOTENT = "onboarding_day_completed_idempotent"
    ONBOARDING_OVERVIEW_VIEWED = "onboarding_overview_viewed"
    ONBOARDING_DAY_CREATED = "onboarding_day_created"
    ONBOARDING_DAY_UPDATED = "onboarding_day_updated"
    ONBOARDING_DAY_DELETED = "onboarding_day_deleted"
    ONBOARDING_MATERIAL_CREATED = "onboarding_material_created"
    ONBOARDING_MATERIAL_UPDATED = "onboarding_material_updated"
    ONBOARDING_MATERIAL_DELETED = "onboarding_material_deleted"
    ONBOARDING_PROGRESS_VIEWED_ADMIN = "onboarding_progress_viewed_admin"

    # Reports
    REPORT_SUBMITTED = "report_submitted"
    REPORT_REJECTED_EMPTY = "report_rejected_empty"
    REPORT_DEADLINE_BLOCKED = "report_deadline_blocked"
    REPORT_EDIT_CONFLICT = "report_edit_conflict"
    REPORT_REVIEW_STATUS_CHANGED = "report_review_status_changed"

    # Work schedule
    SCHEDULE_SELECTION_INVALID_PAYLOAD = "schedule_selection_invalid_payload"
    SCHEDULE_SELECTION_NOT_FOUND = "schedule_selection_not_found"
    SCHEDULE_SELECTED_FOR_APPROVAL = "schedule_selected_for_approval"
    WORK_SCHEDULE_CREATED = "work_schedule_created"
    WORK_SCHEDULE_UPDATED = "work_schedule_updated"
    WORK_SCHEDULE_DEACTIVATED = "work_schedule_deactivated"
    SCHEDULE_REQUEST_APPROVED = "schedule_request_approved"
    SCHEDULE_REQUEST_REJECTED = "schedule_request_rejected"
    WORK_SCHEDULE_CALENDAR_MONTH_GENERATED = "work_schedule_calendar_month_generated"

    # Content
    FEEDBACK_CREATED = "feedback_created"
    FEEDBACK_UPDATED_ADMIN = "feedback_updated_admin"
    FEEDBACK_STATUS_CHANGED_ADMIN = "feedback_status_changed_admin"

    # Common notifications
    NOTIFICATION_MARKED_READ = "notification_marked_read"
    NOTIFICATIONS_MARKED_READ_ALL = "notifications_marked_read_all"

    # Attendance
    ATTENDANCE_MARK_CREATED = "attendance_mark_created"
    ATTENDANCE_MARK_UPDATED = "attendance_mark_updated"
    ATTENDANCE_MARK_CHANGE_DENIED = "attendance_mark_change_denied"
    ATTENDANCE_MARK_DELETED = "attendance_mark_deleted"
    WORK_CALENDAR_DAY_CREATED = "work_calendar_day_created"
    WORK_CALENDAR_DAY_UPDATED = "work_calendar_day_updated"
    WORK_CALENDAR_DAY_DELETED = "work_calendar_day_deleted"
    WORK_CALENDAR_MONTH_GENERATED = "work_calendar_month_generated"

    # Tasks
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_MOVED = "task_moved"

    # Regulations
    REGULATION_CREATED = "regulation_created"
    REGULATION_UPDATED = "regulation_updated"
    REGULATION_DELETED = "regulation_deleted"
    REGULATION_ACKNOWLEDGED = "regulation_acknowledged"
    ONBOARDING_DAY1_BLOCKED_MISSING_REGULATIONS = "onboarding_day1_blocked_missing_regulations"

    # Org
    DEPARTMENT_CREATED = "department_created"
    DEPARTMENT_UPDATED = "department_updated"
    DEPARTMENT_DELETED = "department_deleted"
    DEPARTMENT_DELETE_BLOCKED = "department_delete_blocked"
    POSITION_CREATED = "position_created"
    POSITION_UPDATED = "position_updated"
    POSITION_DELETED = "position_deleted"

    # Payroll
    SALARY_PROFILE_CREATED = "salary_profile_created"
    SALARY_PROFILE_UPDATED = "salary_profile_updated"
    PAYROLL_PERIOD_GENERATED = "payroll_period_generated"
    PAYROLL_PERIOD_STATUS_CHANGED = "payroll_period_status_changed"
