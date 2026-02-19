from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import HasPermission

from .models import (
    News, WelcomeBlock, Feedback, Employee,
    Instruction, LanguageSetting, NewsSliderSettings
)

from .serializers import (
    NewsListSerializer,
    NewsDetailSerializer,
    WelcomeBlockSerializer,
    EmployeeSerializer,
    InstructionSerializer,
    LanguageSettingSerializer,
    FeedbackSerializer,
    FeedbackCreateSerializer,
    FeedbackResponseSerializer
)


# ---------------- NEWS ----------------

class NewsListAPIView(ListAPIView):
    serializer_class = NewsListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        language = self.request.query_params.get("language", "ru")
        return News.objects.filter(
            is_active=True,
            language=language
        ).order_by("position", "-published_at")[:10]


class NewsDetailAPIView(RetrieveAPIView):
    queryset = News.objects.filter(is_active=True)
    serializer_class = NewsDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"


# ---------------- FEEDBACK ----------------

class FeedbackAdminView(ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "feedback_manage"


class FeedbackCreateView(CreateAPIView):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackCreateSerializer
    permission_classes = [AllowAny]


# ---------------- EMPLOYEES ----------------

class EmployeeListAPIView(ListAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        show_management = self.request.query_params.get("management")
        qs = Employee.objects.filter(is_active=True)

        if show_management == "true":
            qs = qs.filter(is_management=True)

        return qs


# ---------------- INSTRUCTION ----------------

class InstructionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lang = request.query_params.get("lang", "ru")
        instruction = Instruction.objects.filter(language=lang, is_active=True).first()

        if not instruction:
            return Response(
                {"detail": "Инструкция не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(InstructionSerializer(instruction).data)


# ---------------- LANGUAGES ----------------

class EnabledLanguagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        languages = LanguageSetting.objects.filter(is_enabled=True)
        return Response(LanguageSettingSerializer(languages, many=True).data)


# ---------------- SLIDER SETTINGS ----------------

class NewsSliderSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings_obj = NewsSliderSettings.objects.first()

        if not settings_obj:
            return Response({
                "autoplay": True,
                "autoplay_delay": 5000
            })

        return Response({
            "autoplay": settings_obj.autoplay,
            "autoplay_delay": settings_obj.autoplay_delay
        })


# ---------------- WELCOME BLOCK ----------------

class WelcomeBlockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        language = request.query_params.get("language", "ru")
        block = WelcomeBlock.objects.filter(
            language=language,
            is_active=True
        ).first()

        if not block:
            return Response(
                {"detail": "Welcome block not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(WelcomeBlockSerializer(block).data)
