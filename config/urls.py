from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("onboarding_core.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("schedules.urls")),
    path("api/", include("security.urls")),
]
