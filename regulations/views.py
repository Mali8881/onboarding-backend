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
from .models import Regulation, RegulationAcknowledgement
from .permissions import IsAdminLike
from .serializers import (
    RegulationSerializer,
    RegulationAdminSerializer,
    RegulationAcknowledgementSerializer,
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

