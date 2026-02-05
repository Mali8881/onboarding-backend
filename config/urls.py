from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
   # path("api/", include("reviews.urls")),

    path("api/v1/", include("accounts.urls")),
    path('admin/', admin.site.urls),
    path('onboarding/', include('onboarding.urls')),


]


