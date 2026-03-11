from apps.common.models import Notification, NotificationTemplate


class NotificationService:

    @staticmethod
    def send(
        template_code,
        user,
        context=None,
        *,
        code="generic.info",
        severity="info",
        entity_type="",
        entity_id="",
        action_url="",
    ):

        template = NotificationTemplate.objects.filter(
            code=template_code,
            is_active=True
        ).first()

        if not template:
            return None

        context = context or {}

        title = template.title_template.format(**context)
        message = template.message_template.format(**context)

        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=template.type,
            code=code,
            severity=severity,
            entity_type=entity_type,
            entity_id=str(entity_id or ""),
            action_url=action_url or "",
        )

    @staticmethod
    def broadcast(
        template_code,
        queryset,
        context=None,
        *,
        code="generic.info",
        severity="info",
        entity_type="",
        entity_id="",
        action_url="",
    ):

        template = NotificationTemplate.objects.filter(
            code=template_code,
            is_active=True
        ).first()

        if not template:
            return None

        context = context or {}
        notifications = []

        for user in queryset:
            notifications.append(
                Notification(
                    user=user,
                    title=template.title_template.format(**context),
                    message=template.message_template.format(**context),
                    type=template.type,
                    code=code,
                    severity=severity,
                    entity_type=entity_type,
                    entity_id=str(entity_id or ""),
                    action_url=action_url or "",
                )
            )

        Notification.objects.bulk_create(notifications)
