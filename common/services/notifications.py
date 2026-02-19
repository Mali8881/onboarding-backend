from common.models import Notification, NotificationTemplate


class NotificationService:

    @staticmethod
    def send(template_code, user, context=None):

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
            type=template.type
        )

    @staticmethod
    def broadcast(template_code, queryset, context=None):

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
                    type=template.type
                )
            )

        Notification.objects.bulk_create(notifications)
