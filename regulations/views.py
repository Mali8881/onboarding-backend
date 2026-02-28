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
    RegulationReadReport,
    RegulationQuiz,
    RegulationQuizAttempt,
    RegulationQuizOption,
    RegulationReadProgress,
)
from .permissions import IsAdminLike
from .serializers import (
    InternOnboardingRequestSerializer,
    RegulationSerializer,
    RegulationAdminSerializer,
    RegulationAcknowledgementSerializer,
    RegulationFeedbackCreateSerializer,
    RegulationReadReportCreateSerializer,
    RegulationQuizResultSerializer,
    RegulationQuizSerializer,
    RegulationQuizSubmitSerializer,
    RegulationReadProgressSerializer,
)


class RegulationListAPIView(ListAPIView):
    serializer_class = RegulationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Regulation.objects.filter(
            is_active=True,
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
        read_progress_map = {
            progress.regulation_id: progress
            for progress in RegulationReadProgress.objects.filter(
                user=request.user,
                regulation__in=queryset,
            )
        }
        today = timezone.localdate()
        required_today_ids = {
            rid
            for rid, progress in read_progress_map.items()
            if progress.is_read and progress.read_at and progress.read_at.date() == today
        }
        read_report_map = {
            report.regulation_id: True
            for report in RegulationReadReport.objects.filter(
                user=request.user,
                regulation__in=queryset,
                opened_on=today,
            )
        }
        quiz_required_map = {
            regulation_id: True
            for regulation_id in RegulationQuiz.objects.filter(
                regulation__in=queryset,
                is_active=True,
            ).values_list("regulation_id", flat=True)
        }
        quiz_passed_map = {
            attempt.quiz.regulation_id: True
            for attempt in RegulationQuizAttempt.objects.filter(
                user=request.user,
                passed=True,
                quiz__regulation__in=queryset,
                quiz__is_active=True,
            ).select_related("quiz")
        }
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
            context={
                "request": request,
                "ack_map": ack_map,
                "read_progress_map": read_progress_map,
                "read_report_map": read_report_map,
                "quiz_required_map": quiz_required_map,
                "quiz_passed_map": quiz_passed_map,
                "required_today_ids": required_today_ids,
            },
        )
        return Response(serializer.data)


class RegulationDetailAPIView(RetrieveAPIView):
    serializer_class = RegulationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Regulation.objects.filter(
            is_active=True,
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
            progress = RegulationReadProgress.objects.filter(
                user=self.request.user,
                regulation_id=regulation_id,
            ).first()
            ctx["read_progress_map"] = {progress.regulation_id: progress} if progress else {}
            if progress and progress.read_at:
                opened_on = progress.read_at.date()
                has_report = RegulationReadReport.objects.filter(
                    user=self.request.user,
                    regulation_id=regulation_id,
                    opened_on=opened_on,
                ).exists()
                ctx["read_report_map"] = {regulation_id: has_report}
            else:
                ctx["read_report_map"] = {}
            quiz_required = RegulationQuiz.objects.filter(
                regulation_id=regulation_id,
                is_active=True,
            ).exists()
            ctx["quiz_required_map"] = {regulation_id: quiz_required}
            quiz_passed = RegulationQuizAttempt.objects.filter(
                user=self.request.user,
                quiz__regulation_id=regulation_id,
                quiz__is_active=True,
                passed=True,
            ).exists()
            ctx["quiz_passed_map"] = {regulation_id: quiz_passed}
        return ctx


class RegulationAdminListCreateAPIView(ListCreateAPIView):
    serializer_class = RegulationAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminLike]

    def get_queryset(self):
        queryset = Regulation.objects.all().order_by("position", "created_at")
        is_active = self.request.query_params.get("is_active")

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
        return Regulation.objects.filter(
            is_active=True,
            is_mandatory_on_day_one=True,
        ).order_by("position", "-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        read_progress_map = {
            progress.regulation_id: progress
            for progress in RegulationReadProgress.objects.filter(
                user=request.user,
                regulation__in=queryset,
            )
        }
        read_report_map = {
            report.regulation_id: True
            for report in RegulationReadReport.objects.filter(
                user=request.user,
                regulation__in=queryset,
                opened_on=timezone.localdate(),
            )
        }
        quiz_required_map = {
            regulation_id: True
            for regulation_id in RegulationQuiz.objects.filter(
                regulation__in=queryset,
                is_active=True,
            ).values_list("regulation_id", flat=True)
        }
        quiz_passed_map = {
            attempt.quiz.regulation_id: True
            for attempt in RegulationQuizAttempt.objects.filter(
                user=request.user,
                passed=True,
                quiz__regulation__in=queryset,
                quiz__is_active=True,
            ).select_related("quiz")
        }
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
            context={
                "request": request,
                "ack_map": ack_map,
                "read_progress_map": read_progress_map,
                "read_report_map": read_report_map,
                "quiz_required_map": quiz_required_map,
                "quiz_passed_map": quiz_passed_map,
            },
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
        required_report_ids = {
            rid
            for rid, progress in progress_map.items()
            if progress.is_read and progress.read_at and progress.read_at.date() == timezone.localdate()
        }
        report_map = {
            report.regulation_id: True
            for report in RegulationReadReport.objects.filter(
                user=request.user,
                regulation__in=regulations,
                opened_on=timezone.localdate(),
            )
        }
        quiz_required_map = {
            regulation_id: True
            for regulation_id in RegulationQuiz.objects.filter(
                regulation__in=regulations,
                is_active=True,
            ).values_list("regulation_id", flat=True)
        }
        quiz_passed_map = {
            attempt.quiz.regulation_id: True
            for attempt in RegulationQuizAttempt.objects.filter(
                user=request.user,
                passed=True,
                quiz__regulation__in=regulations,
                quiz__is_active=True,
            ).select_related("quiz")
        }
        ack_map = {
            ack.regulation_id: ack
            for ack in RegulationAcknowledgement.objects.filter(
                user=request.user,
                regulation__in=regulations,
            )
        }

        items = []
        read_count = 0
        for regulation in regulations:
            progress = progress_map.get(regulation.id)
            is_read = bool(progress and progress.is_read)
            if is_read:
                read_count += 1
            items.append(
                {
                    "regulation": RegulationSerializer(
                        regulation,
                        context={
                            "request": request,
                            "ack_map": ack_map,
                            "read_progress_map": progress_map,
                            "read_report_map": report_map,
                            "quiz_required_map": quiz_required_map,
                            "quiz_passed_map": quiz_passed_map,
                        },
                    ).data,
                    "is_read": is_read,
                    "read_at": progress.read_at if progress else None,
                }
            )

        total_count = len(regulations)
        all_read = total_count > 0 and read_count == total_count
        report_required_count = len(required_report_ids)
        report_submitted_count = len([rid for rid in required_report_ids if report_map.get(rid)])
        all_reports_submitted = report_required_count == report_submitted_count
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
                "report_required_count": report_required_count,
                "report_submitted_count": report_submitted_count,
                "all_reports_submitted": all_reports_submitted,
                "next_step_message": (
                    "Вы прочитали все регламенты. Подойдите к Жибек и подпишите документы об ознакомлении."
                    if all_read and all_reports_submitted
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


class RegulationReadReportCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, regulation_id):
        if not AccessPolicy.is_intern(request.user):
            return Response(
                {"detail": "Only intern can submit regulation read report."},
                status=status.HTTP_403_FORBIDDEN,
            )

        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            return Response({"detail": "Regulation not found."}, status=404)

        progress = RegulationReadProgress.objects.filter(
            user=request.user,
            regulation=regulation,
            is_read=True,
        ).first()
        if not progress or not progress.read_at:
            return Response(
                {"detail": "Read/open regulation first before submitting report."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        opened_on = progress.read_at.date()
        serializer = RegulationReadReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now_local_date = timezone.localdate()
        report, created = RegulationReadReport.objects.get_or_create(
            user=request.user,
            regulation=regulation,
            opened_on=opened_on,
            defaults={
                "report_text": serializer.validated_data["report_text"],
                "submitted_at": timezone.now(),
                "is_late": now_local_date > opened_on,
            },
        )
        if not created:
            report.report_text = serializer.validated_data["report_text"]
            report.submitted_at = timezone.now()
            report.is_late = now_local_date > opened_on
            report.save(update_fields=["report_text", "submitted_at", "is_late"])

        return Response(
            {
                "id": report.id,
                "opened_on": report.opened_on,
                "is_late": report.is_late,
                "submitted_at": report.submitted_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RegulationQuizDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, regulation_id):
        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            return Response({"detail": "Regulation not found."}, status=404)
        quiz = RegulationQuiz.objects.filter(regulation=regulation, is_active=True).prefetch_related(
            "questions__options"
        ).first()
        if not quiz:
            return Response({"detail": "Quiz is not configured for this regulation."}, status=404)
        return Response(RegulationQuizSerializer(quiz).data)


class RegulationQuizSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, regulation_id):
        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            return Response({"detail": "Regulation not found."}, status=404)
        quiz = RegulationQuiz.objects.filter(regulation=regulation, is_active=True).prefetch_related(
            "questions__options"
        ).first()
        if not quiz:
            return Response({"detail": "Quiz is not configured for this regulation."}, status=404)

        serializer = RegulationQuizSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Mark read automatically when user takes quiz after opening regulation.
        progress, _ = RegulationReadProgress.objects.get_or_create(
            user=request.user,
            regulation=regulation,
        )
        if not progress.is_read:
            progress.is_read = True
            progress.read_at = timezone.now()
            progress.save(update_fields=["is_read", "read_at"])

        answers = serializer.validated_data["answers"]
        questions = list(quiz.questions.all())
        if not questions:
            return Response({"detail": "Quiz has no questions."}, status=400)

        correct_count = 0
        for question in questions:
            selected = answers.get(str(question.id))
            if selected is None:
                continue
            is_correct = RegulationQuizOption.objects.filter(
                id=selected,
                question=question,
                is_correct=True,
            ).exists()
            if is_correct:
                correct_count += 1

        total = len(questions)
        score_percent = int((correct_count / total) * 100) if total else 0
        passed = score_percent >= quiz.passing_score

        attempt = RegulationQuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score_percent=score_percent,
            passed=passed,
        )
        return Response(
            {
                "result": RegulationQuizResultSerializer(attempt).data,
                "passing_score": quiz.passing_score,
                "correct_answers": correct_count,
                "questions_total": total,
            },
            status=201,
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

        today = timezone.localdate()
        opened_today_ids = set(
            RegulationReadProgress.objects.filter(
                user=request.user,
                regulation__in=active_regulations,
                is_read=True,
                read_at__date=today,
            ).values_list("regulation_id", flat=True)
        )
        if opened_today_ids:
            reported_today_ids = set(
                RegulationReadReport.objects.filter(
                    user=request.user,
                    regulation_id__in=opened_today_ids,
                    opened_on=today,
                ).values_list("regulation_id", flat=True)
            )
            missing_report_ids = [str(reg_id) for reg_id in opened_today_ids if reg_id not in reported_today_ids]
            if missing_report_ids:
                return Response(
                    {
                        "detail": "Submit daily report for every regulation opened today.",
                        "missing_report_regulation_ids": missing_report_ids,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        quiz_regulation_ids = list(
            RegulationQuiz.objects.filter(
                regulation__in=active_regulations,
                is_active=True,
            ).values_list("regulation_id", flat=True)
        )
        if quiz_regulation_ids:
            passed_regulation_ids = set(
                RegulationQuizAttempt.objects.filter(
                    user=request.user,
                    passed=True,
                    quiz__is_active=True,
                    quiz__regulation_id__in=quiz_regulation_ids,
                ).values_list("quiz__regulation_id", flat=True)
            )
            missing_quiz_ids = [str(reg_id) for reg_id in quiz_regulation_ids if reg_id not in passed_regulation_ids]
            if missing_quiz_ids:
                return Response(
                    {
                        "detail": "Pass mini tests for all required regulations before completion submit.",
                        "missing_quiz_regulation_ids": missing_quiz_ids,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        onboarding_request = InternOnboardingRequest.objects.create(user=request.user)
        request.user.intern_onboarding_completed_at = timezone.now()
        request.user.save(update_fields=["intern_onboarding_completed_at"])

        admin_qs = User.objects.filter(
            role__name__in=[Role.Name.ADMINISTRATOR, Role.Name.ADMIN]
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
        if not AccessPolicy.is_admin_like(self.request.user):
            return InternOnboardingRequest.objects.none()
        status_value = self.request.query_params.get("status")
        qs = InternOnboardingRequest.objects.select_related("user", "reviewed_by")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class AdminApproveInternOnboardingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if not AccessPolicy.is_admin_like(request.user):
            return Response(
                {"detail": "Only operational admin can approve onboarding."},
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

