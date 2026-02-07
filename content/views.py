from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import (
    News, WelcomeBlock, Feedback, Employee,
    Instruction, LanguageSetting, NewsSliderSettings
)

from .serializers import (
    NewsListSerializer,
    NewsDetailSerializer,
    WelcomeBlockSerializer,
    FeedbackSerializer,
    EmployeeSerializer,
    InstructionSerializer,
    LanguageSettingSerializer,
    NewsSerializer,
    NewsSliderSettingsSerializer
)


# 🔹 НОВОСТИ
class NewsListAPIView(ListAPIView):
    serializer_class = NewsListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Получаем язык из параметров или ставим 'ru' по умолчанию
        language = self.request.query_params.get("language", "ru")
        return News.objects.filter(is_active=True, language=language)


class NewsDetailAPIView(RetrieveAPIView):
    queryset = News.objects.filter(is_active=True)
    serializer_class = NewsDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'  # Указываем явный поиск по UUID


# 🔹 ПРИВЕТСТВЕННЫЙ БЛОК
class WelcomeBlockAPIView(ListAPIView):
    serializer_class = WelcomeBlockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WelcomeBlock.objects.filter(is_active=True)


# 🔹 ОБРАТНАЯ СВЯЗЬ
class FeedbackCreateAPIView(CreateAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [AllowAny]


# 🔹 СОТРУДНИКИ
class EmployeeListAPIView(ListAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        show_management = self.request.query_params.get("management")
        qs = Employee.objects.filter(is_active=True)

        # ВНИМАНИЕ: Поле is_management должно быть в моделях!
        # Если его там нет, этот блок нужно убрать или добавить поле в models.py
        if show_management == "true":
            # Проверьте, есть ли поле is_management в модели Employee
            if hasattr(Employee, 'is_management'):
                qs = qs.filter(is_management=True)
        return qs


# 🔹 ИНСТРУКЦИИ
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


# 🔹 ЯЗЫКИ
class EnabledLanguagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        languages = LanguageSetting.objects.filter(is_enabled=True)
        return Response(LanguageSettingSerializer(languages, many=True).data)


# 🔹 НАСТРОЙКИ СЛАЙДЕРА
class NewsSliderSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings_obj = NewsSliderSettings.objects.first()

        if not settings_obj:
            # Дефолтные настройки, если в БД пусто
            return Response({
                "autoplay": True,
                "autoplay_delay": 5000
            })

        # ИСПРАВЛЕНО: autoplay_delay вместо autoplay_de
        return Response({
            "autoplay": settings_obj.autoplay,
            "autoplay_delay": settings_obj.autoplay_delay
        })