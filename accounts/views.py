from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone

from .models import LoginHistory, User, Position
from .serializers import (
    UserSerializer,
    UserProfileUpdateSerializer,
    PositionSerializer
)
from .permissions import HasPermission
from .throttles import LoginRateThrottle


# ================= LOGIN =================

class LoginView(APIView):
    throttle_classes = [LoginRateThrottle]
    MAX_ATTEMPTS = 5
    LOCKOUT_TIME_MINUTES = 15

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        existing_user = User.objects.filter(username=username).first()

        # Проверка блокировки по попыткам
        if existing_user:
            if existing_user.lockout_until and existing_user.lockout_until > timezone.now():
                return Response(
                    {"error": "Too many failed attempts. Try again later."},
                    status=403
                )

        if not user:
            if existing_user:
                existing_user.failed_login_attempts += 1

                if existing_user.failed_login_attempts >= self.MAX_ATTEMPTS:
                    existing_user.lockout_until = timezone.now() + timedelta(
                        minutes=self.LOCKOUT_TIME_MINUTES
                    )

                existing_user.save()

            LoginHistory.objects.create(
                user=existing_user,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
                success=False
            )

            return Response({"error": "Invalid credentials"}, status=400)

        # Блокировка вручную
        if user.is_blocked:
            return Response({"error": "User blocked"}, status=403)

        # Сброс счетчиков
        user.failed_login_attempts = 0
        user.lockout_until = None
        user.save()

        refresh = RefreshToken.for_user(user)

        LoginHistory.objects.create(
            user=user,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            success=True
        )

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role.name if user.role else None
            }
        })


# ================= PROFILE =================

class MyProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ================= POSITIONS =================

class PositionListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "view_positions"

    def get(self, request):
        positions = Position.objects.filter(is_active=True)
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)
