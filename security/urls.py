from rest_framework.routers import DefaultRouter
from .views import SystemLogViewSet

router = DefaultRouter()
router.register(
    r"admin/system-logs",
    SystemLogViewSet,
    basename="system-logs",
)

urlpatterns = router.urls
