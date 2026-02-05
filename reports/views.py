from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Report
from .serializers import ReportSerializer
from .permissions import IsAdmin
from .services import change_report_status
from reports.models import Report



class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Report.objects.all()
        return Report.objects.filter(user=user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        report = self.get_object()
        change_report_status(report, Report.Status.SENT)
        return Response({"status": "sent"})

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdmin],
    )
    def review(self, request, pk=None):
        report = self.get_object()
        new_status = request.data.get("status")

        change_report_status(report, new_status)
        return Response({"status": new_status})
