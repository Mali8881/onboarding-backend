from __future__ import annotations

from accounts.access_policy import AccessPolicy


class WorkSchedulePolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin_like(user)

    @classmethod
    def can_manage_templates(cls, user) -> bool:
        return bool(user and user.is_authenticated and cls.is_admin_like(user))

    @classmethod
    def can_manage_calendar(cls, user) -> bool:
        return cls.can_manage_templates(user)

    @classmethod
    def can_approve_requests(cls, user) -> bool:
        return cls.can_manage_templates(user)

    @staticmethod
    def can_select_schedule(user) -> bool:
        return bool(user and user.is_authenticated)

    @staticmethod
    def can_submit_weekly_plan(user) -> bool:
        return bool(user and user.is_authenticated)

    @classmethod
    def can_view_weekly_plan_requests(cls, user) -> bool:
        return cls.can_manage_templates(user)

