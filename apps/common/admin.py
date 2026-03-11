from django.contrib import admin
from apps.common.models import Notification, NotificationTemplate

admin.site.register(Notification)
admin.site.register(NotificationTemplate)
