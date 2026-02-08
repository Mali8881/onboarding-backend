from drf_spectacular.utils import extend_schema, OpenApiResponse
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
    EmployeeSerializer,
    InstructionSerializer,
    LanguageSettingSerializer,
    FeedbackResponseSerializer, FeedbackCreateSerializer
)


# 🔹 НОВОСТИ
class NewsListAPIView(ListAPIView):
    serializer_class = NewsListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Получаем язык из параметров или ставим 'ru' по умолчанию
        language = self.request.query_params.get("language", "ru")
        return News.objects.filter(
            is_active=True,
            language=language
        ).order_by("position", "-published_at")[:10]


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

@extend_schema(
    description="""
Отправка обращения через форму обратной связи.

type — тип обращения.
Допустимые значения: complaint | proposal | feedback
""",
    request=FeedbackCreateSerializer,
    responses={
        201: FeedbackResponseSerializer
    }
)


# 🔹 ОБРАТНАЯ СВЯЗЬ
class FeedbackCreateAPIView(CreateAPIView):
    serializer_class = FeedbackCreateSerializer
    permission_classes = [AllowAny]


# 🔹 СОТРУДНИКИ
class EmployeeListAPIView(ListAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        show_management = self.request.query_params.get("management")
        qs = Employee.objects.filter(is_active=True)

        if show_management == "true":
            qs = qs.filter(is_management=True)

        return qs



# 🔹 ИНСТРУКЦИИ
class InstructionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="""
    Возвращает инструкцию по использованию платформы.

    Инструкция может быть представлена в одном из форматов:
    — текст;
    — ссылка на внешний ресурс;
    — файл для скачивания.

    Доступ: любой авторизованный пользователь.
    """,
        responses={
            200: OpenApiResponse(
                description="Инструкция платформы",
                response={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Тип инструкции",
                            "enum": ["text", "link", "file"]
                        },
                        "content": {
                            "type": "string",
                            "description": "Содержимое инструкции (текст или URL)"
                        }
                    }
                }
            ),
            401: OpenApiResponse(description="Пользователь не авторизован")
        }
    )
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
from drf_spectacular.utils import extend_schema, OpenApiResponse

class EnabledLanguagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="""
Возвращает список доступных (включённых) языков интерфейса платформы.

Используется для:
— переключателя языка интерфейса;
— инициализации языка пользователя.

Возвращаются только языки с флагом `is_enabled = true`.

Доступ: любой авторизованный пользователь.
""",
        responses={
            200: OpenApiResponse(
                description="Список доступных языков",
                response=LanguageSettingSerializer(many=True)
            ),
            401: OpenApiResponse(description="Пользователь не авторизован")
        }
    )
    def get(self, request):
        languages = LanguageSetting.objects.filter(is_enabled=True)
        return Response(LanguageSettingSerializer(languages, many=True).data)

from drf_spectacular.utils import extend_schema, OpenApiResponse

class NewsSliderSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="""
Возвращает настройки слайдера новостей на главной странице.

Если настройки отсутствуют в базе данных,
возвращаются значения по умолчанию.

Доступ: любой авторизованный пользователь.
""",
        responses={
            200: OpenApiResponse(
                description="Настройки слайдера новостей",
                response={
                    "type": "object",
                    "properties": {
                        "autoplay": {
                            "type": "boolean",
                            "description": "Включена ли автопрокрутка слайдера"
                        },
                        "autoplay_delay": {
                            "type": "integer",
                            "description": "Задержка автопрокрутки в миллисекундах"
                        }
                    }
                }
            ),
            401: OpenApiResponse(description="Пользователь не авторизован")
        }
    )
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
