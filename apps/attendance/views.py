import calendar
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from work_schedule.models import ProductionCalendar

from .audit import AttendanceAuditService
from .models import AttendanceMark, WorkCalendarDay
from .policies import AttendancePolicy
from .serializers import (
    AttendanceMarkSerializer,
    AttendanceMarkUpsertSerializer,
    MonthQuerySerializer,
)
from .services import month_bounds


User = get_user_model()


class AttendanceCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        year = query.validated_data["year"]
        month = query.validated_data["month"]

        first, last = month_bounds(year, month)
        calendar_map = {
            item.date: item
            for item in WorkCalendarDay.objects.filter(date__range=(first, last))
        }
        prod_map = {
            item.date: item
            for item in ProductionCalendar.objects.filter(date__range=(first, last))
        }

        result = []
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            current = date(year, month, day)
            if current in calendar_map:
                item = calendar_map[current]
                is_working_day = item.is_working_day
                is_holiday = item.is_holiday
                note = item.note
            elif current in prod_map:
                item = prod_map[current]
                is_working_day = item.is_working_day
                is_holiday = item.is_holiday
                note = item.holiday_name or ""
            else:
                is_working_day = current.weekday() < 5
                is_holiday = False
                note = ""

            result.append(
                {
                    "date": current,
                    "is_working_day": is_working_day,
                    "is_holiday": is_holiday,
                    "note": note,
                }
            )

        return Response(result)


class AttendanceMarkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return self._upsert(request)

    def patch(self, request):
        return self._upsert(request)

    def _upsert(self, request):
        serializer = AttendanceMarkUpsertSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            target_user_id = request.data.get("user_id", request.user.id)
            mark_date = request.data.get("date")
            if serializer.errors.get("detail") and mark_date:
                try:
                    parsed_date = date.fromisoformat(mark_date)
                    AttendanceAuditService.log_mark_change_denied(request, int(target_user_id), parsed_date)
                except Exception:
                    pass
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        target_user = validated["target_user"]
        mark, created = AttendanceMark.objects.get_or_create(
            user=target_user,
            date=validated["date"],
            defaults={
                "status": validated["status"],
                "comment": validated.get("comment", ""),
                "created_by": request.user,
            },
        )

        if not created:
            changed_fields = []
            new_status = validated["status"]
            new_comment = validated.get("comment", "")
            if mark.status != new_status:
                mark.status = new_status
                changed_fields.append("status")
            if mark.comment != new_comment:
                mark.comment = new_comment
                changed_fields.append("comment")
            if changed_fields:
                mark.save(update_fields=changed_fields + ["updated_at"])
                AttendanceAuditService.log_mark_updated(request, mark, changed_fields)
        else:
            AttendanceAuditService.log_mark_created(request, mark)

        return Response(
            AttendanceMarkSerializer(mark).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AttendanceMyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        first, last = month_bounds(query.validated_data["year"], query.validated_data["month"])
        qs = AttendanceMark.objects.filter(
            user=request.user,
            date__range=(first, last),
        ).select_related("user", "created_by")
        return Response(AttendanceMarkSerializer(qs, many=True).data)


class AttendanceTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not AttendancePolicy.can_view_team(request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        first, last = month_bounds(query.validated_data["year"], query.validated_data["month"])

        users_qs = User.objects.none()
        if AttendancePolicy.is_admin_like(request.user):
            users_qs = User.objects.all()
        else:
            users_qs = request.user.team_members.all()

        qs = AttendanceMark.objects.filter(
            user__in=users_qs,
            date__range=(first, last),
        ).select_related("user", "created_by")
        return Response(AttendanceMarkSerializer(qs, many=True).data)

