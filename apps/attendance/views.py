import calendar
from datetime import date
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from work_schedule.models import ProductionCalendar
from accounts.models import Role
from accounts.access_policy import AccessPolicy

from .audit import AttendanceAuditService
from .models import AttendanceMark, AttendanceSession, WorkCalendarDay
from .policies import AttendancePolicy
from .serializers import (
    AttendanceCheckinReportQuerySerializer,
    AttendanceTeamFilterSerializer,
    AttendanceMarkSerializer,
    AttendanceMarkUpsertSerializer,
    AttendanceSessionSerializer,
    MonthQuerySerializer,
    OfficeCheckInSerializer,
    WorkCalendarDaySerializer,
    WorkCalendarDayUpsertSerializer,
    WorkCalendarGenerateSerializer,
)
from .services import (
    attendance_table_queryset,
    build_attendance_table,
    get_client_ip,
    generate_work_calendar_month,
    haversine_distance_m,
    is_office_ip,
    month_bounds,
    office_geofence,
)
from work_schedule.models import UserWorkSchedule, WeeklyWorkPlan


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
        if AccessPolicy.is_super_admin(request.user):
            users_qs = User.objects.filter(is_active=True)
        elif AccessPolicy.is_main_admin(request.user):
            users_qs = User.objects.filter(is_active=True).exclude(role__name=Role.Name.SUPER_ADMIN)
        elif AccessPolicy.is_admin(request.user):
            users_qs = User.objects.filter(is_active=True)
            if request.user.department_id:
                users_qs = users_qs.filter(department_id=request.user.department_id)
            users_qs = users_qs.exclude(role__name__in=[Role.Name.SUPER_ADMIN, Role.Name.ADMIN, Role.Name.ADMINISTRATOR])
        else:
            users_qs = request.user.team_members.filter(is_active=True).exclude(role__name=Role.Name.SUPER_ADMIN)

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


class AttendanceCheckinReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _scope_users(self, actor):
        if AccessPolicy.is_super_admin(actor) or AccessPolicy.is_main_admin(actor):
            return User.objects.filter(is_active=True).exclude(role__name=Role.Name.SUPER_ADMIN)

        if AccessPolicy.is_admin(actor):
            if not actor.department_id:
                return User.objects.none()
            return User.objects.filter(is_active=True, department_id=actor.department_id).exclude(
                role__name__in=[Role.Name.SUPER_ADMIN, Role.Name.ADMIN]
            )

        if AccessPolicy.is_teamlead(actor):
            return actor.team_members.filter(is_active=True).exclude(role__name=Role.Name.SUPER_ADMIN)

        return User.objects.none()

    @staticmethod
    def _week_monday(day: date) -> date:
        return day.fromordinal(day.toordinal() - day.weekday())

    @staticmethod
    def _format_hhmm(value):
        if not value:
            return None
        return value.strftime("%H:%M")

    def _resolve_shift(self, *, actor, target_user, target_date, plan_by_user, user_schedule_by_user):
        # First priority: approved weekly plan for target date.
        plan = plan_by_user.get(target_user.id)
        if plan and isinstance(plan.days, list):
            for item in plan.days:
                if str(item.get("date")) == str(target_date):
                    mode = item.get("mode") or ""
                    if mode == "day_off":
                        return None, None, mode
                    return item.get("start_time"), item.get("end_time"), mode

        # Fallback: assigned template schedule.
        user_schedule = user_schedule_by_user.get(target_user.id)
        if user_schedule and user_schedule.schedule:
            weekday = target_date.weekday()  # Monday=0
            work_days = user_schedule.schedule.work_days or []
            if weekday in work_days:
                return (
                    self._format_hhmm(user_schedule.schedule.start_time),
                    self._format_hhmm(user_schedule.schedule.end_time),
                    "office",
                )
            return None, None, "day_off"

        return None, None, ""

    @staticmethod
    def _parse_shift_hhmm(value: Optional[str]):
        if not value:
            return None
        chunks = str(value).split(":")
        if len(chunks) < 2:
            return None
        try:
            return int(chunks[0]), int(chunks[1])
        except Exception:
            return None

    @classmethod
    def _compute_late_minutes(
        cls, target_date: date, shift_start_hhmm: Optional[str], checked_at
    ):
        if not shift_start_hhmm or not checked_at:
            return None
        parsed = cls._parse_shift_hhmm(shift_start_hhmm)
        if not parsed:
            return None
        start_h, start_m = parsed

        report_tz_name = getattr(settings, "ATTENDANCE_REPORT_TIMEZONE", "Asia/Bishkek")
        try:
            report_tz = ZoneInfo(report_tz_name)
        except Exception:
            report_tz = timezone.get_current_timezone()

        start_dt = datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=start_h,
            minute=start_m,
            tzinfo=report_tz,
        )

        local_checked = checked_at.astimezone(report_tz)
        delta_minutes = int((local_checked - start_dt).total_seconds() // 60)
        return max(0, delta_minutes)

    def get(self, request):
        if not AttendancePolicy.can_view_team(request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        query = AttendanceCheckinReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        target_date = query.validated_data.get("date") or timezone.localdate()
        users_qs = self._scope_users(request.user).select_related("department", "subdivision", "role").order_by(
            "department__name", "last_name", "first_name", "username"
        )

        user_ids = list(users_qs.values_list("id", flat=True))
        if not user_ids:
            return Response({"date": target_date, "rows": []})

        marks = AttendanceMark.objects.filter(user_id__in=user_ids, date=target_date).select_related("user")
        marks_by_user = {item.user_id: item for item in marks}

        successful_sessions = (
            AttendanceSession.objects.filter(
                user_id__in=user_ids,
                checked_at__date=target_date,
                result=AttendanceSession.Result.IN_OFFICE,
            )
            .select_related("user")
            .order_by("checked_at")
        )
        first_session_by_user = {}
        for session in successful_sessions:
            first_session_by_user.setdefault(session.user_id, session)

        monday = self._week_monday(target_date)
        plans = WeeklyWorkPlan.objects.filter(
            user_id__in=user_ids,
            week_start=monday,
            status=WeeklyWorkPlan.Status.APPROVED,
        ).select_related("user")
        plans_by_user = {plan.user_id: plan for plan in plans}

        user_schedules = UserWorkSchedule.objects.filter(user_id__in=user_ids).select_related("schedule")
        user_schedule_by_user = {item.user_id: item for item in user_schedules}

        rows = []
        for user in users_qs:
            mark = marks_by_user.get(user.id)
            shift_from, shift_to, shift_mode = self._resolve_shift(
                actor=request.user,
                target_user=user,
                target_date=target_date,
                plan_by_user=plans_by_user,
                user_schedule_by_user=user_schedule_by_user,
            )
            session = first_session_by_user.get(user.id)
            if shift_mode == "office":
                checkin_dt = session.checked_at if session else None
            else:
                checkin_dt = session.checked_at if session else (mark.created_at if mark else None)

            late_minutes = self._compute_late_minutes(target_date, shift_from, checkin_dt)
            rows.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": (f"{user.first_name} {user.last_name}".strip() or user.username),
                    "role": user.role.name if user.role_id else "",
                    "department": user.department.name if user.department_id else "",
                    "subdivision": user.subdivision.name if user.subdivision_id else "",
                    "shift_from": shift_from,
                    "shift_to": shift_to,
                    "shift_mode": shift_mode,
                    "mark_status": mark.status if mark else "",
                    "checked_at": checkin_dt,
                    "late_minutes": late_minutes,
                }
            )

        return Response({"date": target_date, "rows": rows})


class AttendanceOfficeCheckInAPIView(APIView):
    permission_classes = [IsAuthenticated]
    # JWT must be preferred for SPA requests with Authorization header.
    # Session auth is kept as fallback for admin/tools.
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def post(self, request):
        serializer = OfficeCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        geofence = office_geofence()
        client_ip = get_client_ip(request)
        ip_valid = is_office_ip(client_ip)
        lat = serializer.validated_data.get("latitude")
        lon = serializer.validated_data.get("longitude")
        accuracy = serializer.validated_data.get("accuracy_m")

        has_coordinates = lat is not None and lon is not None
        if geofence is None:
            if not ip_valid:
                return Response(
                    {"detail": "Office geofence is not configured."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            # Allow office check-in by trusted office IP even when geofence is not configured.
            office_lat, office_lon, radius_m = 0.0, 0.0, 0
            distance_m = 0.0
            in_office = True
            session_lat = float(lat) if lat is not None else office_lat
            session_lon = float(lon) if lon is not None else office_lon
            has_coordinates = lat is not None and lon is not None
        else:
            office_lat, office_lon, radius_m = geofence
            if has_coordinates:
                distance_m = haversine_distance_m(lat, lon, office_lat, office_lon)
                in_office = distance_m <= radius_m or ip_valid
                session_lat = lat
                session_lon = lon
            else:
                # Fallback for office Wi-Fi/IP verification when browser geolocation is denied.
                distance_m = 0.0 if ip_valid else float(radius_m + 1)
                in_office = ip_valid
                session_lat = office_lat
                session_lon = office_lon

        mark = None
        if in_office:
            mark, _ = AttendanceMark.objects.get_or_create(
                user=request.user,
                date=date.today(),
                defaults={
                    "status": AttendanceMark.Status.PRESENT,
                    "comment": "Office check-in",
                    "created_by": request.user,
                },
            )
            if mark.status != AttendanceMark.Status.PRESENT:
                mark.status = AttendanceMark.Status.PRESENT
                mark.save(update_fields=["status", "updated_at"])

        session = AttendanceSession.objects.create(
            user=request.user,
            latitude=session_lat,
            longitude=session_lon,
            accuracy_m=accuracy,
            ip_address=client_ip,
            distance_m=distance_m,
            office_latitude=office_lat,
            office_longitude=office_lon,
            radius_m=radius_m,
            result=(
                AttendanceSession.Result.IN_OFFICE
                if in_office
                else AttendanceSession.Result.OUTSIDE_GEOFENCE
            ),
            attendance_mark=mark,
        )

        if in_office:
            AttendanceAuditService.log_office_checkin_in_office(request, session)
        else:
            AttendanceAuditService.log_office_checkin_outside(request, session)

        payload = AttendanceSessionSerializer(session).data
        payload["status"] = "IN_OFFICE" if in_office else "OUT_OF_OFFICE"
        payload["in_office"] = in_office
        payload["ip_valid"] = ip_valid
        payload["geolocation_used"] = has_coordinates
        return Response(payload, status=status.HTTP_201_CREATED)


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
