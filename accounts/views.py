from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from content.models import News
from content.serializers import NewsListSerializer

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .permissions import IsSuperAdmin, IsAdminOrSuperAdmin
from .models import Department, Position
from .serializers import (
    UserProfileSerializer,
    DepartmentSerializer,
    PositionSerializer,
)


@extend_schema(
    description="""
Получение и обновление профиля текущего пользователя.

GET:
— возвращает данные профиля авторизованного пользователя.

PATCH:
— обновляет данные профиля;
— стажёр НЕ может изменять подразделение и должность;
— администратор и суперадминистратор могут изменять все поля.

Доступ: любой авторизованный пользователь.
""",
    responses=UserProfileSerializer,
)
class MyProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UserProfileSerializer(request.user).data
        )

    @extend_schema(
        request=UserProfileSerializer,
        responses=UserProfileSerializer,
    )
    def patch(self, request):
        data = request.data.copy()

        if not request.user.is_superuser:
            data.pop("department", None)
            data.pop("position", None)

        serializer = UserProfileSerializer(
            request.user,
            data=data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

@extend_schema(
    description="""
Возвращает список активных подразделений компании.

Используется в административных формах
(например, при редактировании профиля пользователя).

Возвращаются только активные подразделения.

Доступ: только суперадминистратор.
""",
    responses=DepartmentSerializer,
)
class DepartmentListAPIView(ListAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        return Department.objects.filter(is_active=True)
@extend_schema(
    description="""
Возвращает список активных должностей компании.

Используется в административных интерфейсах
и при редактировании профилей пользователей.

Возвращаются только активные должности.

Доступ: администратор / суперадминистратор.
""",
    responses=PositionSerializer,
)
class PositionListAPIView(ListAPIView):
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get_queryset(self):
        return Position.objects.filter(is_active=True)

@extend_schema(
    description="""
Возвращает список последних новостей платформы.

Особенности:
— можно указать язык через query-параметр `language`;
— по умолчанию используется язык `ru`;
— возвращаются только активные новости;
— максимум 10 записей;
— сортировка по дате создания (сначала новые).

Доступ: любой авторизованный пользователь.
""",
    responses=NewsListSerializer,
)
class NewsListAPIView(ListAPIView):
    serializer_class = NewsListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        language = self.request.query_params.get("language", "ru")
        return News.objects.filter(
            is_active=True,
            language=language
        ).order_by("-created_at")[:10]
