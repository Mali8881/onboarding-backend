from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status

from common.permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from .models import User
from .tokens import CustomTokenObtainPairSerializer
from .serializers import (
    MeSerializer,
    AdminUserListSerializer,
    AdminUserCreateSerializer,
)

# =====================================================
# AUTH
# =====================================================

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


# =====================================================
# ADMIN USERS API
# =====================================================

class AdminUserViewSet(ModelViewSet):
    """
    Админ API для управления пользователями

    SUPER_ADMIN:
    - create ADMIN / INTERN
    - block / unblock
    - list users

    ADMIN:
    - create INTERN
    - list users
    """
    queryset = User.objects.all().order_by("id")
    permission_classes = [IsAdminOrSuperAdmin]
    http_method_names = ["get", "post"]

    def get_serializer_class(self):
        if self.action == "create":
            return AdminUserCreateSerializer
        return AdminUserListSerializer

    def create(self, request, *args, **kwargs):
        """
        Создание пользователя.
        Ограничения по ролям — внутри сериализатора.
        """
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            AdminUserListSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def block(self, request, pk=None):
        user = self.get_object()

        if user.role == "SUPER_ADMIN":
            return Response(
                {"detail": "Cannot block SUPER_ADMIN"},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.is_blocked = True
        user.save()

        return Response({"detail": "User blocked"}, status=200)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def unblock(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = False
        user.save()

        return Response({"detail": "User unblocked"}, status=200)
