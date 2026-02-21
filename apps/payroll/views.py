from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import PayrollAuditService
from .models import PayrollEntry, PayrollPeriod, SalaryProfile
from .policies import PayrollPolicy
from .serializers import (
    MonthQuerySerializer,
    PayrollEntrySerializer,
    PayrollGenerateSerializer,
    PayrollPeriodStatusSerializer,
    SalaryProfileSerializer,
)
from .services import generate_period


class PayrollMyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        year = query.validated_data["year"]
        month = query.validated_data["month"]
        entry = (
            PayrollEntry.objects.select_related("period", "user")
            .filter(user=request.user, period__year=year, period__month=month)
            .first()
        )
        if not entry:
            return Response({"detail": "Payroll entry not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PayrollEntrySerializer(entry).data)


class PayrollAdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not PayrollPolicy.can_manage_payroll(request.user):
            raise PermissionDenied("Access denied.")
        query = MonthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        year = query.validated_data["year"]
        month = query.validated_data["month"]
        qs = PayrollEntry.objects.select_related("period", "user").filter(period__year=year, period__month=month)
        return Response(PayrollEntrySerializer(qs, many=True).data)


class PayrollGenerateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not PayrollPolicy.can_manage_payroll(request.user):
            raise PermissionDenied("Access denied.")
        serializer = PayrollGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        month = serializer.validated_data["month"]
        try:
            period, created, updated = generate_period(year, month)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        PayrollAuditService.log_period_generated(request, period, created, updated)
        return Response(
            {
                "period_id": period.id,
                "year": year,
                "month": month,
                "status": period.status,
                "entries_created": created,
                "entries_updated": updated,
            },
            status=status.HTTP_200_OK,
        )


class PayrollPeriodStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, period_id: int):
        if not PayrollPolicy.can_manage_payroll(request.user):
            raise PermissionDenied("Access denied.")
        period = PayrollPeriod.objects.filter(id=period_id).first()
        if not period:
            return Response({"detail": "Period not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PayrollPeriodStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if period.status == new_status:
            return Response({"id": period.id, "status": period.status}, status=status.HTTP_200_OK)

        old = period.status
        period.status = new_status
        period.save(update_fields=["status", "updated_at"])
        PayrollAuditService.log_period_status_changed(request, period, previous_status=old)
        return Response({"id": period.id, "status": period.status}, status=status.HTTP_200_OK)


class SalaryProfileAdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not PayrollPolicy.can_manage_payroll(request.user):
            raise PermissionDenied("Access denied.")
        qs = SalaryProfile.objects.select_related("user").order_by("user_id")
        return Response(SalaryProfileSerializer(qs, many=True).data)

    def post(self, request):
        if not PayrollPolicy.can_manage_payroll(request.user):
            raise PermissionDenied("Access denied.")
        serializer = SalaryProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        PayrollAuditService.log_salary_profile_created(request, profile)
        return Response(SalaryProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


class SalaryProfileAdminDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, profile_id: int):
        if not PayrollPolicy.can_manage_payroll(request.user):
            raise PermissionDenied("Access denied.")
        profile = SalaryProfile.objects.filter(id=profile_id).first()
        if not profile:
            return Response({"detail": "Salary profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SalaryProfileSerializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed_fields = list(serializer.validated_data.keys())
        profile = serializer.save()
        if changed_fields:
            PayrollAuditService.log_salary_profile_updated(request, profile, changed_fields)
        return Response(SalaryProfileSerializer(profile).data, status=status.HTTP_200_OK)

