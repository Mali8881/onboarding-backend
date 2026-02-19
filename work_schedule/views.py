import calendar
from datetime import date

from rest_framework import status

from .models import (
    WorkSchedule,
    UserWorkSchedule,
    ProductionCalendar,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from .services import get_month_calendar
from .serializers import CalendarDaySerializer

class CalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            year = int(request.query_params.get("year"))
            month = int(request.query_params.get("month"))

            if month < 1 or month > 12:
                raise ValueError()

        except (TypeError, ValueError):
            return Response(
                {"detail": "year и month должны быть корректными числами"},
                status=status.HTTP_400_BAD_REQUEST
            )

        calendar_data = get_month_calendar(
            user=request.user,
            year=year,
            month=month,
        )

        serializer = CalendarDaySerializer(calendar_data, many=True)
        return Response(serializer.data)
class MyScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uws = UserWorkSchedule.objects.filter(user=request.user).first()

        if not uws:
            return Response(
                {"detail": "График не выбран"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not uws.approved:
            return Response({
                "status": "pending",
                "schedule": uws.schedule.name
            })

        schedule = uws.schedule

        return Response({
            "status": "approved",
            "name": schedule.name,
            "work_days": schedule.work_days,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "break_start": schedule.break_start,
            "break_end": schedule.break_end,
        })
class ChooseScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        schedule_id = request.data.get("schedule_id")

        if not schedule_id:
            return Response(
                {"detail": "schedule_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            schedule = WorkSchedule.objects.get(
                id=schedule_id,
                is_active=True
            )
        except WorkSchedule.DoesNotExist:
            return Response(
                {"detail": "График не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        uws, _ = UserWorkSchedule.objects.get_or_create(
            user=request.user
        )

        uws.schedule = schedule
        uws.approved = False
        uws.save()

        return Response({
            "detail": "График отправлен на согласование"
        })
class CalendarMonthAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            year = int(request.query_params["year"])
            month = int(request.query_params["month"])

            if month < 1 or month > 12:
                raise ValueError()

        except (KeyError, ValueError):
            return Response(
                {"detail": "Некорректные параметры"},
                status=status.HTTP_400_BAD_REQUEST
            )

        days_in_month = calendar.monthrange(year, month)[1]
        result = []

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)

            pc = ProductionCalendar.objects.filter(
                date=current_date
            ).first()

            if pc:
                is_working = pc.is_working_day
                is_holiday = pc.is_holiday
            else:
                is_working = current_date.weekday() < 5
                is_holiday = False

            result.append({
                "date": current_date,
                "is_working_day": is_working,
                "is_holiday": is_holiday,
            })

        return Response(result)
