from datetime import date

from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import WorkScheduleAuditService
from .models import ProductionCalendar, UserWorkSchedule, WorkSchedule
from .policies import WorkSchedulePolicy
from .serializers import (
    CalendarDaySerializer,
    ScheduleRequestDecisionSerializer,
    UserWorkScheduleSerializer,
    WorkScheduleMonthGenerateSerializer,
    WorkScheduleSelectSerializer,
    WorkScheduleSerializer,
)
from .services import generate_production_calendar_month, get_month_calendar


class WorkScheduleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = WorkSchedule.objects.filter(is_active=True).annotate(users_count=Count("users"))
        return Response(WorkScheduleSerializer(qs, many=True).data)


class WorkScheduleAdminListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not WorkSchedulePolicy.can_manage_templates(request.user):
            raise PermissionDenied("Insufficient permissions.")
        qs = WorkSchedule.objects.all().annotate(users_count=Count("users")).order_by("id")
        return Response(WorkScheduleSerializer(qs, many=True).data)

    def post(self, request):
        if not WorkSchedulePolicy.can_manage_templates(request.user):
            raise PermissionDenied("Insufficient permissions.")
        serializer = WorkScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        WorkScheduleAuditService.log_work_schedule_created(request, schedule)
        return Response(WorkScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)


class WorkScheduleAdminDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, schedule_id: int):
        if not WorkSchedulePolicy.can_manage_templates(request.user):
            raise PermissionDenied("Insufficient permissions.")
        schedule = WorkSchedule.objects.filter(id=schedule_id).first()
        if not schedule:
            return Response({"detail": "Schedule not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkScheduleSerializer(instance=schedule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed_fields = [field for field in serializer.validated_data.keys()]
        schedule = serializer.save()
        if changed_fields:
            WorkScheduleAuditService.log_work_schedule_updated(request, schedule, changed_fields)
        return Response(WorkScheduleSerializer(schedule).data, status=status.HTTP_200_OK)


class MyScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uws = UserWorkSchedule.objects.filter(user=request.user).select_related("schedule").first()
        if not uws:
            return Response({"detail": "Schedule is not selected."}, status=status.HTTP_404_NOT_FOUND)
        payload = UserWorkScheduleSerializer(uws).data
        payload["status"] = "approved" if uws.approved else "pending"
        return Response(payload)


class ChooseScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not WorkSchedulePolicy.can_select_schedule(request.user):
            raise PermissionDenied("Insufficient permissions.")

        if request.data.get("schedule_id") in (None, ""):
            WorkScheduleAuditService.log_schedule_selection_invalid_payload(request)
            return Response({"detail": "schedule_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WorkScheduleSelectSerializer(data=request.data)
        if not serializer.is_valid():
            WorkScheduleAuditService.log_schedule_selection_invalid_payload(request)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        schedule_id = serializer.validated_data["schedule_id"]
        schedule = WorkSchedule.objects.filter(id=schedule_id, is_active=True).first()
        if not schedule:
            WorkScheduleAuditService.log_schedule_selection_not_found(request, schedule_id)
            return Response({"detail": "Schedule not found."}, status=status.HTTP_404_NOT_FOUND)

        uws, created = UserWorkSchedule.objects.get_or_create(
            user=request.user,
            defaults={"schedule": schedule, "approved": False},
        )
        if not created:
            uws.schedule = schedule
            uws.approved = False
            uws.save(update_fields=["schedule", "approved"])

        WorkScheduleAuditService.log_schedule_selected_for_approval(request, schedule, was_created=created)
        return Response({"detail": "Schedule was sent for approval."}, status=status.HTTP_200_OK)


class WorkScheduleRequestListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not WorkSchedulePolicy.can_approve_requests(request.user):
            raise PermissionDenied("Insufficient permissions.")
        qs = UserWorkSchedule.objects.select_related("user", "schedule").order_by("-requested_at")
        pending = request.query_params.get("pending")
        if pending == "1":
            qs = qs.filter(approved=False)
        return Response(UserWorkScheduleSerializer(qs, many=True).data)


class WorkScheduleRequestDecisionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: int):
        if not WorkSchedulePolicy.can_approve_requests(request.user):
            raise PermissionDenied("Insufficient permissions.")
        uws = UserWorkSchedule.objects.filter(id=request_id).select_related("user", "schedule").first()
        if not uws:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ScheduleRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approved = serializer.validated_data["approved"]
        uws.approved = approved
        uws.save(update_fields=["approved"])
        WorkScheduleAuditService.log_schedule_request_decision(request, uws, approved=approved)
        return Response(UserWorkScheduleSerializer(uws).data, status=status.HTTP_200_OK)


class WorkScheduleTemplateUsersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, schedule_id: int):
        if not WorkSchedulePolicy.can_manage_templates(request.user):
            raise PermissionDenied("Insufficient permissions.")
        schedule = WorkSchedule.objects.filter(id=schedule_id).first()
        if not schedule:
            return Response({"detail": "Schedule not found."}, status=status.HTTP_404_NOT_FOUND)
        users = schedule.users.select_related("user").order_by("-requested_at")
        return Response(UserWorkScheduleSerializer(users, many=True).data)


class CalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            year = int(request.query_params.get("year"))
            month = int(request.query_params.get("month"))
            if month < 1 or month > 12:
                raise ValueError()
        except (TypeError, ValueError):
            return Response({"detail": "year and month must be valid integers."}, status=status.HTTP_400_BAD_REQUEST)

        calendar_data = get_month_calendar(user=request.user, year=year, month=month)
        return Response(CalendarDaySerializer(calendar_data, many=True).data)


class CalendarMonthAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return CalendarView().get(request)


class ProductionCalendarDayAdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not WorkSchedulePolicy.can_manage_calendar(request.user):
            raise PermissionDenied("Insufficient permissions.")
        day = request.data.get("date")
        if not day:
            return Response({"date": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            day_date = date.fromisoformat(day)
        except ValueError:
            return Response({"date": ["Date has wrong format. Use YYYY-MM-DD."]}, status=status.HTTP_400_BAD_REQUEST)

        is_working_day = bool(request.data.get("is_working_day", True))
        is_holiday = bool(request.data.get("is_holiday", False))
        holiday_name = request.data.get("holiday_name", "")
        obj, _ = ProductionCalendar.objects.update_or_create(
            date=day_date,
            defaults={
                "is_working_day": is_working_day,
                "is_holiday": is_holiday,
                "holiday_name": holiday_name,
            },
        )
        return Response(
            {
                "date": obj.date,
                "is_working_day": obj.is_working_day,
                "is_holiday": obj.is_holiday,
                "holiday_name": obj.holiday_name or "",
            },
            status=status.HTTP_200_OK,
        )


class ProductionCalendarMonthGenerateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not WorkSchedulePolicy.can_manage_calendar(request.user):
            raise PermissionDenied("Insufficient permissions.")

        serializer = WorkScheduleMonthGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        month = serializer.validated_data["month"]
        overwrite = serializer.validated_data.get("overwrite", False)

        created, updated = generate_production_calendar_month(year, month, overwrite=overwrite)
        WorkScheduleAuditService.log_calendar_month_generated(
            request,
            year=year,
            month=month,
            created=created,
            updated=updated,
            overwrite=overwrite,
        )
        return Response(
            {
                "year": year,
                "month": month,
                "created": created,
                "updated": updated,
                "overwrite": overwrite,
            },
            status=status.HTTP_200_OK,
        )
