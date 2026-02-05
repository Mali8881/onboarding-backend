# reviews/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reviews', views.ReportReviewViewSet, basename='report-review')

urlpatterns = [
    path('', include(router.urls)),
    # Вот эта строка вызывала ошибку:
    path('reports/', views.ReportListView.as_view(), name='report-list'),
]