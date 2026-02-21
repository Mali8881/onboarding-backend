from __future__ import annotations

from accounts.access_policy import AccessPolicy


class PayrollPolicy:
    @staticmethod
    def is_admin_like(user) -> bool:
        return AccessPolicy.is_admin_like(user)

    @classmethod
    def can_manage_payroll(cls, user) -> bool:
        return bool(user and user.is_authenticated and cls.is_admin_like(user))

    @classmethod
    def can_view_entry(cls, actor, target_user) -> bool:
        if not actor or not actor.is_authenticated:
            return False
        if cls.is_admin_like(actor):
            return True
        return actor.id == target_user.id

