from django.db import transaction
from django.utils import timezone
from accounts.access_policy import AccessPolicy
from accounts.models import Role, User
from common.models import Notification
from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .audit import RegulationsAuditService
from .models import (
    InternOnboardingRequest,
    Regulation,
    RegulationAcknowledgement,
    RegulationFeedback,
    RegulationReadProgress,
)
from .permissions import IsAdminLike
from .serializers import (
    InternOnboardingRequestSerializer,
    RegulationSerializer,
    RegulationAdminSerializer,
    RegulationAcknowledgementSerializer,
    RegulationFeedbackCreateSerializer,
    RegulationReadProgressSerializer,
)


class RegulationListAPIView(ListAPIView):
    serializer_class = RegulationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        language = self.request.query_params.get("language", "ru")
        queryset = Regulation.objects.filter(
            is_active=True,
            language=language,
        )
        regulation_type = self.request.query_params.get("type")
        query = self.request.query_params.get("q")
        if regulation_type in {Regulation.RegulationType.LINK, Regulation.RegulationType.FILE}:
            queryset = queryset.filter(type=regulation_type)
        if query:
            queryset = queryset.filter(title__icontains=query)
        return queryset.order_by("position", "-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        ack_map = {
            ack.regulation_id: ack
            for ack in RegulationAcknowledgement.objects.filter(
                user=request.user,
                regulation__in=queryset,
            )
        }
        serializer = self.get_serializer(
            queryset,
            many=True,
            context={"request": request, "ack_map": ack_map},
        )
        return Response(serializer.data)


class RegulationDetailAPIView(RetrieveAPIView):
    serializer_class = RegulationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        language = self.request.query_params.get("language", "ru")
        return Regulation.objects.filter(
            is_active=True,
            language=language,
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        regulation_id = self.kwargs.get("id")
        if self.request.user.is_authenticated and regulation_id:
            ack = RegulationAcknowledgement.objects.filter(
                user=self.request.user,
                regulation_id=regulation_id,
            ).first()
            ctx["ack_map"] = {ack.regulation_id: ack} if ack else {}
        return ctx


class RegulationAdminListCreateAPIView(ListCreateAPIView):
    serializer_class = RegulationAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminLike]

    def get_queryset(self):
        queryset = Regulation.objects.all().order_by("position", "created_at")
        language = self.request.query_params.get("language")
        is_active = self.request.query_params.get("is_active")

        if language:
            queryset = queryset.filter(language=language)
        if is_active is not None:
            value = str(is_active).lower() in {"1", "true", "yes"}
            queryset = queryset.filter(is_active=value)
        return queryset

    def perform_create(self, serializer):
        regulation = serializer.save()
        RegulationsAuditService.regulation_created(
            actor=self.request.user,
            regulation=regulation,
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )


class RegulationAdminDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Regulation.objects.all()
    serializer_class = RegulationAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminLike]
    lookup_field = "id"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        changed_fields = {
            field
            for field, value in serializer.validated_data.items()
            if getattr(instance, field) != value
        }

        self.perform_update(serializer)
        if changed_fields:
            RegulationsAuditService.regulation_updated(
                actor=request.user,
                regulation=serializer.instance,
                changed_fields=changed_fields,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        regulation_id = instance.id
        self.perform_destroy(instance)
        RegulationsAuditService.regulation_deleted(
            actor=request.user,
            regulation_id=regulation_id,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegulationAcknowledgeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        regulation = get_object_or_404(Regulation, id=id, is_active=True)
        full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username

        ack, created = RegulationAcknowledgement.objects.get_or_create(
            user=request.user,
            regulation=regulation,
            defaults={
                "user_full_name": full_name,
                "regulation_title": regulation.title,
            },
        )

        RegulationsAuditService.regulation_acknowledged(
            actor=request.user,
            acknowledgement=ack,
            ip_address=request.META.get("REMOTE_ADDR"),
            idempotent=not created,
        )
        return Response(
            RegulationAcknowledgementSerializer(ack).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FirstDayMandatoryRegulationsAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegulationSerializer

    def get_queryset(self):
        language = self.request.query_params.get("language", "ru")
        return Regulation.objects.filter(
            is_active=True,
            is_mandatory_on_day_one=True,
            language=language,
        ).order_by("position", "-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        ack_map = {
            ack.regulation_id: ack
            for ack in RegulationAcknowledgement.objects.filter(
                user=request.user,
                regulation__in=queryset,
            )
        }
        serializer = self.get_serializer(
            queryset,
            many=True,
            context={"request": request, "ack_map": ack_map},
        )
        data = serializer.data
        return Response(
            {
                "required_count": len(data),
                "acknowledged_count": len([x for x in data if x.get("is_acknowledged")]),
                "items": data,
            }
        )


class InternOnboardingOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not AccessPolicy.is_intern(request.user):
            return Response(
                {"detail": "Only intern can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        regulations = list(Regulation.objects.filter(is_active=True).order_by("position"))
        progresses = RegulationReadProgress.objects.filter(
            user=request.user,
            regulation__in=regulations,
        ).select_related("regulation")
        progress_map = {item.regulation_id: item for item in progresses}

        items = []
        read_count = 0
        for regulation in regulations:
            progress = progress_map.get(regulation.id)
            is_read = bool(progress and progress.is_read)
            if is_read:
                read_count += 1
            items.append(
                {
                    "regulation": RegulationSerializer(regulation).data,
                    "is_read": is_read,
                    "read_at": progress.read_at if progress else None,
                }
            )

        total_count = len(regulations)
        all_read = total_count > 0 and read_count == total_count
        progress_percent = int((read_count / total_count) * 100) if total_count else 0
        latest_request = InternOnboardingRequest.objects.filter(user=request.user).first()

        return Response(
            {
                "welcome": f"Здравствуйте, {request.user.first_name or request.user.username}!",
                "is_first_login": request.user.intern_onboarding_started_at is None,
                "total_regulations": total_count,
                "read_regulations": read_count,
                "progress_percent": progress_percent,
                "all_read": all_read,
                "next_step_message": (
                    "Вы прочитали все регламенты. Подойдите к Жибек и подпишите документы об ознакомлении."
                    if all_read
                    else ""
                ),
                "request_status": latest_request.status if latest_request else None,
                "items": items,
            }
        )


class StartInternOnboardingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not AccessPolicy.is_intern(request.user):
            return Response(
                {"detail": "Only intern can start onboarding."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.user.intern_onboarding_started_at:
            return Response({"status": "already_started"})

        request.user.intern_onboarding_started_at = timezone.now()
        request.user.save(update_fields=["intern_onboarding_started_at"])
        return Response({"status": "started"})


class MarkRegulationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, regulation_id):
        if not AccessPolicy.is_intern(request.user):
            return Response(
                {"detail": "Only intern can mark regulation as read."},
                status=status.HTTP_403_FORBIDDEN,
            )

        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            return Response({"detail": "Regulation not found."}, status=404)

        progress, _ = RegulationReadProgress.objects.get_or_create(
            user=request.user,
            regulation=regulation,
        )
        if not progress.is_read:
            progress.is_read = True
            progress.read_at = timezone.now()
            progress.save(update_fields=["is_read", "read_at"])

        return Response(RegulationReadProgressSerializer(progress).data)


class RegulationFeedbackCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, regulation_id):
        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            return Response({"detail": "Regulation not found."}, status=404)

        serializer = RegulationFeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = RegulationFeedback.objects.create(
            user=request.user,
            regulation=regulation,
            text=serializer.validated_data["text"],
        )
        return Response(
            {"id": feedback.id, "created_at": feedback.created_at},
            status=status.HTTP_201_CREATED,
        )


class SubmitInternOnboardingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not AccessPolicy.is_intern(request.user):
            return Response(
                {"detail": "Only intern can submit onboarding completion."},
                status=status.HTTP_403_FORBIDDEN,
            )

        active_regulations = Regulation.objects.filter(is_active=True)
        total = active_regulations.count()
        if total == 0:
            return Response(
                {"detail": "No active regulations found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        read_count = RegulationReadProgress.objects.filter(
            user=request.user,
            regulation__in=active_regulations,
            is_read=True,
        ).count()
        if read_count != total:
            return Response(
                {"detail": "Read all regulations before completion submit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        onboarding_request = InternOnboardingRequest.objects.create(user=request.user)
        request.user.intern_onboarding_completed_at = timezone.now()
        request.user.save(update_fields=["intern_onboarding_completed_at"])

        admin_qs = User.objects.filter(
            role__name__in=[Role.Name.ADMIN, Role.Name.SUPER_ADMIN]
        ).select_related("role")
        Notification.objects.bulk_create(
            [
                Notification(
                    user=admin_user,
                    title="Стажер завершил обучение",
                    message=(
                        f"Стажер {request.user.username} завершил ознакомление с регламентами. "
                        "Проверьте и подтвердите перевод в работника."
                    ),
                    type=Notification.Type.LEARNING,
                )
                for admin_user in admin_qs
            ]
        )

        return Response(
            {
                "request_id": onboarding_request.id,
                "message": "Заявка отправлена. Подойдите к Жибек и подпишите документы об ознакомлении.",
            },
            status=status.HTTP_201_CREATED,
        )


class AdminInternOnboardingRequestListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InternOnboardingRequestSerializer

    def get_queryset(self):
        if not (AccessPolicy.is_admin(self.request.user) or AccessPolicy.is_super_admin(self.request.user)):
            return InternOnboardingRequest.objects.none()
        status_value = self.request.query_params.get("status")
        qs = InternOnboardingRequest.objects.select_related("user", "reviewed_by")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class AdminApproveInternOnboardingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if not (AccessPolicy.is_admin(request.user) or AccessPolicy.is_super_admin(request.user)):
            return Response(
                {"detail": "Only admin or super admin can approve onboarding."},
                status=status.HTTP_403_FORBIDDEN,
            )

        onboarding_request = InternOnboardingRequest.objects.select_related("user").filter(
            id=request_id,
            status=InternOnboardingRequest.Status.PENDING,
        ).first()
        if not onboarding_request:
            return Response({"detail": "Pending request not found."}, status=404)

        department_id = request.data.get("department_id")
        with transaction.atomic():
            user = onboarding_request.user
            user.role = Role.objects.get(name=Role.Name.EMPLOYEE)
            if department_id:
                user.department_id = department_id
            user.save(update_fields=["role", "department"] if department_id else ["role"])

            onboarding_request.status = InternOnboardingRequest.Status.APPROVED
            onboarding_request.reviewed_at = timezone.now()
            onboarding_request.reviewed_by = request.user
            onboarding_request.note = request.data.get("note", "")
            onboarding_request.save(update_fields=["status", "reviewed_at", "reviewed_by", "note"])

            Notification.objects.create(
                user=user,
                title="Стажировка подтверждена",
                message="Администратор подтвердил завершение стажировки. Вам назначена роль работника.",
                type=Notification.Type.LEARNING,
            )

        return Response({"status": "approved"})

