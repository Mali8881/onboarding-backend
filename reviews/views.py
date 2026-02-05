# reviews/views.py
from rest_framework import generics, viewsets, permissions
from reports.models import Report
from accounts.models import ReportReview
from .serializers import (
    ReportListSerializer, 
    ReportReviewSerializer
)

class ReportListView(generics.ListAPIView):
    """Список отчетов для админки (проверяющих)"""
    queryset = Report.objects.all()
    serializer_class = ReportListSerializer
    permission_classes = [permissions.IsAuthenticated]

class ReportReviewViewSet(viewsets.ModelViewSet):
    """Создание и редактирование проверок"""
    queryset = ReportReview.objects.all()
    serializer_class = ReportReviewSerializer
    permission_classes = [permissions.IsAuthenticated]