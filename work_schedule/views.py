import calendar
from datetime import date

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
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
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            raise ValidationError("year and month are required")

        calendar = get_month_calendar(
            user=request.user,
            year=int(year),
            month=int(month),
        )

        serializer = CalendarDaySerializer(calendar, many=True)
        return Response(serializer.data)


class MyScheduleAPIView(APIView):
    """
    Текущий график пользователя
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uws = UserWorkSchedule.objects.filter(user=request.user).first()

        if not uws:
            return Response({"detail": "График не выбран"})

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
            "break_time": schedule.break_time,
        })


class ChooseScheduleAPIView(APIView):
    """
    Запрос на смену графика (уходит на согласование)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        schedule_id = request.data.get("schedule_id")

        if not schedule_id:
            return Response(
                {"detail": "schedule_id обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        schedule = WorkSchedule.objects.get(
            id=schedule_id,
            is_active=True
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
    """
    Календарь месяца с учётом производственного календаря
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = int(request.query_params["year"])
        month = int(request.query_params["month"])

        days_in_month = calendar.monthrange(year, month)[1]
        result = []

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)

            pc = ProductionCalendar.objects.filter(
                date=current_date
            ).first()

            result.append({
                "date": current_date,
                "is_working_day": pc.is_working_day if pc else False,
                "is_holiday": pc.is_holiday if pc else False,
            })

        return Response(result)
