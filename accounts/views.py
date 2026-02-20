from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone

from .models import LoginHistory, PasswordResetToken, Position, User
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    PositionSerializer,
)
from .permissions import HasPermission
from .throttles import (
    LoginRateThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetRequestThrottle,
)
from apps.audit import AuditEvents, log_event


# ================= LOGIN =================

class LoginView(APIView):
    throttle_classes = [LoginRateThrottle]
    MAX_ATTEMPTS = 5
    LOCKOUT_TIME_MINUTES = 15

    @staticmethod
    def _get_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        existing_user = User.objects.filter(username=username).first()

        # Проверка блокировки по попыткам
        if existing_user:
            if existing_user.lockout_until and existing_user.lockout_until > timezone.now():
                log_event(
                    action=AuditEvents.LOGIN_BLOCKED_LOCKOUT,
                    actor=existing_user,
                    object_type="user",
                    object_id=str(existing_user.id),
                    level="warning",
                    category="auth",
                    ip_address=self._get_ip(request),
                )
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
            log_event(
                action=AuditEvents.LOGIN_FAILED,
                actor=existing_user,
                object_type="user",
                object_id=str(existing_user.id) if existing_user else "",
                level="warning",
                category="auth",
                ip_address=self._get_ip(request),
                metadata={"username": username},
            )

            return Response({"error": "Invalid credentials"}, status=400)

        # Блокировка вручную
        if user.is_blocked:
            log_event(
                action=AuditEvents.LOGIN_BLOCKED_MANUAL,
                actor=user,
                object_type="user",
                object_id=str(user.id),
                level="warning",
                category="auth",
                ip_address=self._get_ip(request),
            )
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
        log_event(
            action=AuditEvents.LOGIN_SUCCESS,
            actor=user,
            object_type="user",
            object_id=str(user.id),
            level="info",
            category="auth",
            ip_address=self._get_ip(request),
        )

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role.name if user.role else None,
                "role_level": user.role.level if user.role else None,
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
        changed_fields = sorted(serializer.validated_data.keys())
        log_event(
            action=AuditEvents.PROFILE_UPDATED,
            actor=request.user,
            object_type="user_profile",
            object_id=str(request.user.id),
            level="info",
            category="user",
            ip_address=LoginView._get_ip(request),
            metadata={
                "actor_id": request.user.id,
                "changed_fields": changed_fields,
            },
        )
        return Response(serializer.data)


# ================= POSITIONS =================

class PositionListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = "view_positions"

    def get(self, request):
        positions = Position.objects.filter(is_active=True)
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)


class PasswordResetRequestAPIView(APIView):
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        value = serializer.validated_data["username_or_email"].strip()
        user = User.objects.filter(username=value).first()
        if not user:
            user = User.objects.filter(email=value).first()

        token = None
        if user:
            token_obj = PasswordResetToken.objects.create(user=user)
            token = str(token_obj.token)
            log_event(
                action=AuditEvents.PASSWORD_RESET_REQUESTED,
                actor=user,
                object_type="password_reset",
                object_id=str(token_obj.token),
                level="info",
                category="auth",
                ip_address=LoginView._get_ip(request),
                metadata={"user_id": user.id},
            )

        response = {
            "detail": "If the account exists, password reset instructions were created."
        }
        if settings.DEBUG and token:
            response["reset_token"] = token
        return Response(response)


class PasswordResetConfirmAPIView(APIView):
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        token_obj = PasswordResetToken.objects.filter(token=token).first()
        if not token_obj or token_obj.is_used or token_obj.is_expired():
            return Response({"error": "Invalid or expired token"}, status=400)

        try:
            validate_password(new_password, token_obj.user)
        except DjangoValidationError as exc:
            return Response({"error": list(exc.messages)}, status=400)
        user = token_obj.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])

        log_event(
            action=AuditEvents.PASSWORD_RESET_CONFIRMED,
            actor=user,
            object_type="password_reset",
            object_id=str(token_obj.token),
            level="info",
            category="auth",
            ip_address=LoginView._get_ip(request),
            metadata={"user_id": user.id},
        )

        return Response({"detail": "Password has been reset successfully."})
