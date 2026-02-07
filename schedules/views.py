from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from .models import WorkSchedule
from .serializers import (
    WorkScheduleListSerializer,
    WorkScheduleDetailSerializer,
    ScheduleUserSerializer,
)
from accounts.models import User

class WorkScheduleListView(ListAPIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = WorkScheduleListSerializer

    def get_queryset(self):
        return WorkSchedule.objects.filter(is_active=True)

class WorkScheduleDetailView(RetrieveAPIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = WorkScheduleDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return WorkSchedule.objects.filter(is_active=True)

class WorkScheduleUsersView(ListAPIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = ScheduleUserSerializer

    def get_queryset(self):
        schedule_id = self.kwargs["id"]
        return User.objects.filter(work_schedule_id=schedule_id)

class AssignWorkScheduleView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        user_id = request.data.get("user_id")
        schedule_id = request.data.get("schedule_id")

        user = User.objects.get(id=user_id)
        schedule = WorkSchedule.objects.get(id=schedule_id, is_active=True)

        user.work_schedule = schedule
        user.save()

        return Response({"detail": "Schedule assigned"})
