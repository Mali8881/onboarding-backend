from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from accounts.access_policy import AccessPolicy

from .models import ProcessInstance, ProcessTemplate, StepInstance, StepTemplate
from .permissions import IsAdminLike
from .serializers import (
    ProcessInstanceCreateSerializer,
    ProcessInstanceSerializer,
    ProcessTemplateSerializer,
    StepCompleteSerializer,
    StepTemplateSerializer,
)


User = get_user_model()


def _can_access_instance(user, instance: ProcessInstance) -> bool:
    if AccessPolicy.is_admin_like(user):
        return True
    if instance.created_by_id == user.id:
        return True
    if instance.steps.filter(responsible_user_id=user.id).exists():
        return True
    if AccessPolicy.is_teamlead(user):
        subordinate_ids = user.team_members.values_list("id", flat=True)
        if instance.created_by_id in subordinate_ids:
            return True
        return instance.steps.filter(responsible_user_id__in=subordinate_ids).exists()
    return False


class ProcessListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ProcessInstance.objects.select_related("template", "created_by").prefetch_related(
            "steps",
            "steps__step_template",
            "steps__responsible_user",
        )

        if not AccessPolicy.is_admin_like(request.user):
            if AccessPolicy.is_teamlead(request.user):
                sub_ids = list(request.user.team_members.values_list("id", flat=True))
                qs = qs.filter(
                    Q(created_by=request.user)
                    | Q(created_by_id__in=sub_ids)
                    | Q(steps__responsible_user=request.user)
                    | Q(steps__responsible_user_id__in=sub_ids)
                ).distinct()
            else:
                qs = qs.filter(Q(created_by=request.user) | Q(steps__responsible_user=request.user)).distinct()

        status_value = request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        responsible = request.query_params.get("responsible")
        if responsible:
            qs = qs.filter(steps__responsible_user_id=responsible)
        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        waiting_my_action = qs.filter(
            steps__responsible_user=request.user,
            steps__status=StepInstance.Status.IN_PROGRESS,
        ).distinct().count()

        return Response(
            {
                "waiting_my_action": waiting_my_action,
                "items": ProcessInstanceSerializer(qs, many=True).data,
            }
        )


class ProcessDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        instance = get_object_or_404(
            ProcessInstance.objects.select_related("template", "created_by").prefetch_related(
                "steps",
                "steps__step_template",
                "steps__responsible_user",
            ),
            pk=pk,
        )
        if not _can_access_instance(request.user, instance):
            return Response({"detail": "Access denied."}, status=403)
        return Response(ProcessInstanceSerializer(instance).data)


class ProcessCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProcessInstanceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = get_object_or_404(ProcessTemplate, pk=serializer.validated_data["template_id"], is_active=True)
        responsible_map = serializer.validated_data.get("responsible_by_step", {})

        instance = ProcessInstance.objects.create(
            template=template,
            created_by=request.user,
            status=ProcessInstance.Status.IN_PROGRESS,
        )

        now = timezone.now()
        steps = list(template.steps.order_by("order", "id"))
        for index, step_t in enumerate(steps):
            responsible_id = responsible_map.get(str(step_t.id)) or responsible_map.get(step_t.id)
            responsible_user = User.objects.filter(id=responsible_id).first() if responsible_id else None
            status_value = StepInstance.Status.IN_PROGRESS if index == 0 else StepInstance.Status.PENDING
            StepInstance.objects.create(
                process_instance=instance,
                step_template=step_t,
                status=status_value,
                responsible_user=responsible_user,
                started_at=now if index == 0 else None,
            )

        instance.refresh_from_db()
        return Response(ProcessInstanceSerializer(instance).data, status=201)


class StepCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, step_id: int):
        step = get_object_or_404(
            StepInstance.objects.select_related("process_instance", "step_template", "responsible_user"),
            pk=step_id,
        )
        instance = step.process_instance
        if not _can_access_instance(request.user, instance):
            return Response({"detail": "Access denied."}, status=403)
        if step.status != StepInstance.Status.IN_PROGRESS:
            return Response({"detail": "Step is not in progress."}, status=409)
        if step.responsible_user_id and step.responsible_user_id != request.user.id and not AccessPolicy.is_admin_like(request.user):
            return Response({"detail": "Only responsible user can complete this step."}, status=403)

        serializer = StepCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment", "")
        if step.step_template.requires_comment and not comment.strip():
            return Response({"comment": ["Comment is required for this step."]}, status=400)

        step.status = StepInstance.Status.COMPLETED
        step.comment = comment
        step.finished_at = timezone.now()
        step.save(update_fields=["status", "comment", "finished_at"])

        next_step = (
            StepInstance.objects.filter(
                process_instance=instance,
                step_template__order__gt=step.step_template.order,
                status=StepInstance.Status.PENDING,
            )
            .order_by("step_template__order", "id")
            .first()
        )
        if next_step:
            next_step.status = StepInstance.Status.IN_PROGRESS
            next_step.started_at = timezone.now()
            next_step.save(update_fields=["status", "started_at"])
        else:
            instance.status = ProcessInstance.Status.COMPLETED
            instance.save(update_fields=["status"])

        return Response(ProcessInstanceSerializer(instance).data)


class ProcessTemplateAdminViewSet(ModelViewSet):
    queryset = ProcessTemplate.objects.all().order_by("name")
    serializer_class = ProcessTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminLike]


class StepTemplateAdminViewSet(ModelViewSet):
    queryset = StepTemplate.objects.select_related("process_template").all()
    serializer_class = StepTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminLike]
