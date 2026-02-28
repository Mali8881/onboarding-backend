from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from accounts.models import Role
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import PayrollAuditService
from .models import HourlyRateHistory, PayrollCompensation, PayrollRecord
from .permissions import IsPayrollAuthenticated, IsPayrollCompensationEditor, IsPayrollSuperAdmin, IsPayrollViewer
from .policies import PayrollPolicy
from .serializers import (
    HourlyRateHistorySerializer,
    HourlyRateUpdateSerializer,
    MonthQuerySerializer,
    PayrollCompensationSerializer,
    PayrollCompensationUpdateSerializer,
    PayrollRecalculateSerializer,
    PayrollRecordSerializer,
    PayrollRecordStatusSerializer,
)
from .services import PayrollService


User = get_user_model()


class PayrollMyAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollAuthenticated]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        period = date(query.validated_data["year"], query.validated_data["month"], 1)

        record, _ = PayrollRecord.objects.get_or_create(
            user=request.user,
            month=period,
            defaults={
                "total_hours": 0,
                "total_salary": 0,
                "bonus": 0,
                "status": PayrollRecord.Status.CALCULATED,
            },
        )
        return Response(PayrollRecordSerializer(record).data, status=status.HTTP_200_OK)


class PayrollAdminAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollViewer]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        period = date(query.validated_data["year"], query.validated_data["month"], 1)
        qs = PayrollRecord.objects.select_related("user", "user__role").filter(month=period)
        qs = qs.exclude(user__role__name=Role.Name.INTERN)
        if PayrollPolicy.can_manage_payroll(request.user):
            qs = qs.order_by("user_id")
        else:
            qs = qs.filter(user__department_id=request.user.department_id).exclude(user=request.user).order_by("user_id")
        return Response(PayrollRecordSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class PayrollFundSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollViewer]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        year = query.validated_data["year"]
        month = query.validated_data["month"]
        period = date(year, month, 1)

        qs = PayrollRecord.objects.select_related("user", "user__role").filter(month=period).exclude(user__role__name=Role.Name.INTERN)
        if not PayrollPolicy.can_manage_payroll(request.user):
            qs = qs.filter(user__department_id=request.user.department_id).exclude(user=request.user)
        aggregated = qs.aggregate(
            payroll_fund=Coalesce(Sum("total_salary"), 0),
            average_salary=Coalesce(Avg("total_salary"), 0),
            total_hours=Coalesce(Sum("total_hours"), 0),
            total_employees=Count("id"),
        )

        return Response(
            {
                "year": year,
                "month": month,
                "payroll_fund": aggregated["payroll_fund"],
                "average_salary": aggregated["average_salary"],
                "total_employees": aggregated["total_employees"],
                "total_hours": aggregated["total_hours"],
            },
            status=status.HTTP_200_OK,
        )


class PayrollRecalculateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollSuperAdmin]

    def post(self, request):
        serializer = PayrollRecalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        month = serializer.validated_data["month"]

        result = PayrollService.recalculate_month(year=year, month=month)
        PayrollAuditService.log_period_generated(request, year=year, month=month, created=result.created, updated=result.updated)

        return Response(
            {
                "year": year,
                "month": month,
                "entries_created": result.created,
                "entries_updated": result.updated,
            },
            status=status.HTTP_200_OK,
        )


class PayrollRecordStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollSuperAdmin]

    def patch(self, request, record_id: int):
        record = PayrollRecord.objects.select_related("user").filter(id=record_id).first()
        if not record:
            return Response({"detail": "Payroll record not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PayrollRecordStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        if record.status == new_status:
            return Response(PayrollRecordSerializer(record).data, status=status.HTTP_200_OK)

        previous = record.status
        record.status = new_status
        if new_status == PayrollRecord.Status.PAID:
            record.paid_at = timezone.now()
        record.save(update_fields=["status", "paid_at", "updated_at"])

        PayrollAuditService.log_period_status_changed(request, record=record, previous_status=previous)
        return Response(PayrollRecordSerializer(record).data, status=status.HTTP_200_OK)


class HourlyRateAdminAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollSuperAdmin]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsPayrollViewer()]
        return [IsAuthenticated(), IsPayrollCompensationEditor()]

    def get(self, request):
        users_qs = User.objects.filter(is_active=True).exclude(role__name=Role.Name.INTERN).select_related("role")
        if PayrollPolicy.can_manage_payroll(request.user):
            users_qs = users_qs.exclude(id=request.user.id)
        else:
            users_qs = users_qs.filter(department_id=request.user.department_id).exclude(id=request.user.id)
        users = list(users_qs.order_by("id"))
        comp_by_user = {
            comp.user_id: comp
            for comp in PayrollCompensation.objects.filter(user__in=users).select_related("user")
        }
        payload = []
        for user in users:
            comp = comp_by_user.get(user.id)
            if not comp:
                comp = PayrollCompensation(
                    user=user,
                    pay_type=PayrollCompensation.PayType.HOURLY,
                    hourly_rate=user.current_hourly_rate,
                    minute_rate=0,
                    fixed_salary=0,
                )
            payload.append(PayrollCompensationSerializer(comp).data)
        return Response(payload, status=status.HTTP_200_OK)

    def post(self, request):
        if "rate" in request.data and "pay_type" not in request.data:
            serializer = HourlyRateUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = User.objects.get(id=serializer.validated_data["user_id"])
            if not PayrollPolicy.can_edit_compensation_for_user(request.user, user):
                return Response({"detail": "You cannot edit payroll for this user."}, status=status.HTTP_403_FORBIDDEN)
            rate = serializer.validated_data["rate"]
            start_date = serializer.validated_data.get("start_date") or date.today()
            history = PayrollService.set_hourly_rate(user=user, rate=rate, start_date=start_date)
            PayrollAuditService.log_hourly_rate_changed(request, history=history)
            return Response(HourlyRateHistorySerializer(history).data, status=status.HTTP_200_OK)

        serializer = PayrollCompensationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(id=serializer.validated_data["user_id"])
        if not PayrollPolicy.can_edit_compensation_for_user(request.user, user):
            return Response({"detail": "You cannot edit payroll for this user."}, status=status.HTTP_403_FORBIDDEN)
        pay_type = serializer.validated_data["pay_type"]
        comp = PayrollService.get_or_create_compensation(user=user)
        comp.pay_type = pay_type

        if pay_type == PayrollCompensation.PayType.HOURLY:
            rate = serializer.validated_data["hourly_rate"]
            start_date = serializer.validated_data.get("start_date") or date.today()
            history = PayrollService.set_hourly_rate(user=user, rate=rate, start_date=start_date)
            PayrollAuditService.log_hourly_rate_changed(request, history=history)
            comp.refresh_from_db()
        else:
            if pay_type == PayrollCompensation.PayType.MINUTE:
                comp.minute_rate = serializer.validated_data["minute_rate"]
            elif pay_type == PayrollCompensation.PayType.FIXED_SALARY:
                comp.fixed_salary = serializer.validated_data["fixed_salary"]
            comp.save(update_fields=["pay_type", "minute_rate", "fixed_salary", "updated_at"])

        return Response(PayrollCompensationSerializer(comp).data, status=status.HTTP_200_OK)


class HourlyRateHistoryAdminAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPayrollViewer]

    def get(self, request, user_id: int):
        user = User.objects.select_related("role").filter(id=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if not PayrollPolicy.is_salary_enabled_user(user):
            return Response({"detail": "User is not part of payroll."}, status=status.HTTP_404_NOT_FOUND)
        if not PayrollPolicy.can_manage_payroll(request.user):
            if user.department_id != request.user.department_id or user.id == request.user.id:
                return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        qs = HourlyRateHistory.objects.filter(user_id=user_id).order_by("-start_date", "-id")
        return Response(HourlyRateHistorySerializer(qs, many=True).data, status=status.HTTP_200_OK)
