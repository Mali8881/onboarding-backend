import calendar
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from work_schedule.models import ProductionCalendar

from .audit import AttendanceAuditService
from .models import AttendanceMark, WorkCalendarDay
from .policies import AttendancePolicy
from .serializers import (
    AttendanceTeamFilterSerializer,
    AttendanceMarkSerializer,
    AttendanceMarkUpsertSerializer,
    MonthQuerySerializer,
    WorkCalendarDaySerializer,
    WorkCalendarDayUpsertSerializer,
    WorkCalendarGenerateSerializer,
)
from .services import build_attendance_table, generate_work_calendar_month, month_bounds, attendance_table_queryset


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


class AttendanceOverviewAPIView(APIView):
    """
    /attendance/ endpoint from TZ.
    Returns table-shaped payload (rows=users, columns=days) with filters.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = AttendanceTeamFilterSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        year = query.validated_data["year"]
        month = query.validated_data["month"]
        user_id = query.validated_data.get("user_id")
        position_id = query.validated_data.get("position_id")
        status_filter = query.validated_data.get("status")

        users = attendance_table_queryset(request.user)
        if user_id:
            users = users.filter(id=user_id)
        if position_id:
            users = users.filter(position_id=position_id)

        payload = build_attendance_table(
            users=users.order_by("id"),
            year=year,
            month=month,
            status_filter=status_filter,
        )
        return Response(payload)


class AttendanceMarkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return self._upsert(request)

    def patch(self, request):
        return self._upsert(request)

    def delete(self, request):
        user_id = request.data.get("user_id", request.user.id)
        mark_date = request.data.get("date")
        if not mark_date:
            return Response({"date": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed_date = date.fromisoformat(mark_date)
        except ValueError:
            return Response({"date": ["Date has wrong format. Use YYYY-MM-DD."]}, status=status.HTTP_400_BAD_REQUEST)

        target_user = User.objects.filter(id=user_id).first()
        if not target_user:
            return Response({"user_id": ["User not found."]}, status=status.HTTP_404_NOT_FOUND)

        if parsed_date > date.today():
            return Response({"detail": "Future dates are not allowed."}, status=status.HTTP_400_BAD_REQUEST)

        if not AttendancePolicy.can_delete_mark(request.user, target_user):
            AttendanceAuditService.log_mark_change_denied(request, int(user_id), parsed_date)
            raise PermissionDenied("Access denied.")

        mark = AttendanceMark.objects.filter(user=target_user, date=parsed_date).first()
        if not mark:
            return Response({"detail": "Attendance mark not found."}, status=status.HTTP_404_NOT_FOUND)

        AttendanceAuditService.log_mark_deleted(request, mark)
        mark.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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

        query = AttendanceTeamFilterSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        first, last = month_bounds(query.validated_data["year"], query.validated_data["month"])
        user_id = query.validated_data.get("user_id")
        position_id = query.validated_data.get("position_id")
        status_filter = query.validated_data.get("status")

        users_qs = User.objects.none()
        if AttendancePolicy.is_admin_like(request.user):
            users_qs = User.objects.filter(is_active=True)
        else:
            users_qs = request.user.team_members.filter(is_active=True)

        if user_id:
            users_qs = users_qs.filter(id=user_id)
        if position_id:
            users_qs = users_qs.filter(position_id=position_id)

        qs = AttendanceMark.objects.filter(
            user__in=users_qs,
            date__range=(first, last),
        ).select_related("user", "created_by")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(AttendanceMarkSerializer(qs, many=True).data)


class WorkCalendarDayAdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not AttendancePolicy.can_manage_work_calendar(request.user):
            raise PermissionDenied("Access denied.")
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        first, last = month_bounds(query.validated_data["year"], query.validated_data["month"])
        qs = WorkCalendarDay.objects.filter(date__range=(first, last)).order_by("date")
        return Response(WorkCalendarDaySerializer(qs, many=True).data)

    def post(self, request):
        if not AttendancePolicy.can_manage_work_calendar(request.user):
            raise PermissionDenied("Access denied.")
        serializer = WorkCalendarDayUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day, created = WorkCalendarDay.objects.update_or_create(
            date=serializer.validated_data["date"],
            defaults={
                "is_working_day": serializer.validated_data["is_working_day"],
                "is_holiday": serializer.validated_data["is_holiday"],
                "note": serializer.validated_data.get("note", ""),
            },
        )
        if created:
            AttendanceAuditService.log_work_calendar_day_created(request, day)
        else:
            AttendanceAuditService.log_work_calendar_day_updated(
                request,
                day,
                changed_fields=["is_working_day", "is_holiday", "note"],
            )
        return Response(
            WorkCalendarDaySerializer(day).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def patch(self, request):
        if not AttendancePolicy.can_manage_work_calendar(request.user):
            raise PermissionDenied("Access denied.")
        serializer = WorkCalendarDayUpsertSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        day_date = serializer.validated_data.get("date")
        if not day_date:
            return Response({"date": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        day = WorkCalendarDay.objects.filter(date=day_date).first()
        if not day:
            return Response({"detail": "WorkCalendarDay not found."}, status=status.HTTP_404_NOT_FOUND)

        changed_fields = []
        for field in ("is_working_day", "is_holiday", "note"):
            if field in serializer.validated_data:
                value = serializer.validated_data[field]
                if getattr(day, field) != value:
                    setattr(day, field, value)
                    changed_fields.append(field)
        if changed_fields:
            day.save(update_fields=changed_fields)
            AttendanceAuditService.log_work_calendar_day_updated(request, day, changed_fields)
        return Response(WorkCalendarDaySerializer(day).data)

    def delete(self, request):
        if not AttendancePolicy.can_manage_work_calendar(request.user):
            raise PermissionDenied("Access denied.")
        day_date = request.data.get("date")
        if not day_date:
            return Response({"date": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            parsed = date.fromisoformat(day_date)
        except ValueError:
            return Response({"date": ["Date has wrong format. Use YYYY-MM-DD."]}, status=status.HTTP_400_BAD_REQUEST)

        day = WorkCalendarDay.objects.filter(date=parsed).first()
        if not day:
            return Response({"detail": "WorkCalendarDay not found."}, status=status.HTTP_404_NOT_FOUND)
        day.delete()
        AttendanceAuditService.log_work_calendar_day_deleted(request, parsed)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkCalendarGenerateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not AttendancePolicy.can_manage_work_calendar(request.user):
            raise PermissionDenied("Access denied.")
        serializer = WorkCalendarGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        month = serializer.validated_data["month"]
        overwrite = serializer.validated_data.get("overwrite", False)

        created, updated = generate_work_calendar_month(year, month, overwrite=overwrite)
        AttendanceAuditService.log_work_calendar_month_generated(
            request,
            year=year,
            month=month,
            created=created,
            updated=updated,
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
