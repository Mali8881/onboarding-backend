from django.contrib import admin
from django.template.context_processors import static
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config import settings

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
   # path("api/", include("reviews.urls")),
    path("api/", include("regulations.urls")),
    path("api/", include("work_schedule.urls")),
    path("api/v1/", include("accounts.urls")),
    path('onboarding/', include('onboarding.urls')),
    path("api/", include("common.urls")),
    path("api/", include("content.urls")),

]




