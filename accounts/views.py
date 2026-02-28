from django.conf import settings
from django.db.models import Count
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone

from .models import Department, LoginHistory, PasswordResetToken, Position, Role, User
from .serializers import (
    DepartmentSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    PositionSerializer,
)
from .permissions import HasPermission
from .access_policy import AccessPolicy
from .throttles import (
    LoginRateThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetRequestThrottle,
)
from apps.audit import AuditEvents, log_event
from content.models import Course, CourseEnrollment
from reports.models import EmployeeDailyReport


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

    @staticmethod
    def _landing_for(user):
        role_name = user.role.name if getattr(user, "role", None) else ""
        if role_name in {Role.Name.ADMIN, Role.Name.SUPER_ADMIN}:
            return "admin_panel"
        if role_name == Role.Name.INTERN:
            return "intern_portal"
        if role_name == Role.Name.TEAMLEAD:
            return "teamlead_portal"
        return "employee_portal"

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=400)

        existing_user = User.objects.filter(username=username).first()
        if not existing_user:
            existing_user = User.objects.filter(email__iexact=username).first()

        auth_username = existing_user.username if existing_user else username
        user = authenticate(username=auth_username, password=password)

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
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
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
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
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
            "landing": self._landing_for(user),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role.name if user.role else None,
                "role_level": user.role.level if user.role else None,
                "is_first_login": (
                    user.role.name == Role.Name.INTERN and user.intern_onboarding_started_at is None
                ) if user.role else False,
            }
        })


# ================= PROFILE =================

class MyProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class MyProfilePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        log_event(
            action=AuditEvents.PASSWORD_RESET_CONFIRMED,
            actor=request.user,
            object_type="user",
            object_id=str(request.user.id),
            level="info",
            category="auth",
            ip_address=LoginView._get_ip(request),
            metadata={"source": "profile_password_change"},
        )
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

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


# ================= ORG =================

class _OrgAdminMixin:
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _ensure_can_manage(request):
        if not AccessPolicy.can_manage_org_reference(request.user):
            raise PermissionDenied("Недостаточно прав для управления справочниками.")

    @staticmethod
    def _ip(request):
        return LoginView._get_ip(request)


class DepartmentListCreateAPIView(_OrgAdminMixin, ListCreateAPIView):
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        qs = Department.objects.select_related("parent").annotate(users_count=Count("user"))
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=str(is_active).lower() in {"1", "true", "yes"})
        return qs.order_by("name")

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется авторизация.")
        # Read access for any authenticated user to support org visibility.
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._ensure_can_manage(request)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        department = serializer.save()
        log_event(
            action=AuditEvents.DEPARTMENT_CREATED,
            actor=self.request.user,
            object_type="department",
            object_id=str(department.id),
            category="content",
            ip_address=self._ip(self.request),
        )


class DepartmentDetailAPIView(_OrgAdminMixin, RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.select_related("parent").annotate(users_count=Count("user"))
    serializer_class = DepartmentSerializer

    def update(self, request, *args, **kwargs):
        self._ensure_can_manage(request)
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
            log_event(
                action=AuditEvents.DEPARTMENT_UPDATED,
                actor=request.user,
                object_type="department",
                object_id=str(instance.id),
                category="content",
                ip_address=self._ip(request),
                metadata={"changed_fields": sorted(changed_fields)},
            )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        self._ensure_can_manage(request)
        instance = self.get_object()
        if User.objects.filter(department=instance).exists():
            log_event(
                action=AuditEvents.DEPARTMENT_DELETE_BLOCKED,
                actor=request.user,
                object_type="department",
                object_id=str(instance.id),
                category="content",
                level="warning",
                ip_address=self._ip(request),
                metadata={"reason": "has_users"},
            )
            return Response(
                {"detail": "Нельзя удалить отдел: к нему привязаны пользователи."},
                status=status.HTTP_409_CONFLICT,
            )

        dept_id = instance.id
        self.perform_destroy(instance)
        log_event(
            action=AuditEvents.DEPARTMENT_DELETED,
            actor=request.user,
            object_type="department",
            object_id=str(dept_id),
            category="content",
            ip_address=self._ip(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PositionListCreateAPIView(_OrgAdminMixin, ListCreateAPIView):
    serializer_class = PositionSerializer

    def get_queryset(self):
        qs = Position.objects.all()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=str(is_active).lower() in {"1", "true", "yes"})
        return qs.order_by("name")

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Требуется авторизация.")
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._ensure_can_manage(request)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        position = serializer.save()
        log_event(
            action=AuditEvents.POSITION_CREATED,
            actor=self.request.user,
            object_type="position",
            object_id=str(position.id),
            category="content",
            ip_address=self._ip(self.request),
        )


class PositionDetailAPIView(_OrgAdminMixin, RetrieveUpdateDestroyAPIView):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer

    def update(self, request, *args, **kwargs):
        self._ensure_can_manage(request)
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
            log_event(
                action=AuditEvents.POSITION_UPDATED,
                actor=request.user,
                object_type="position",
                object_id=str(instance.id),
                category="content",
                ip_address=self._ip(request),
                metadata={"changed_fields": sorted(changed_fields)},
            )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        self._ensure_can_manage(request)
        instance = self.get_object()
        if User.objects.filter(position=instance).exists():
            return Response(
                {"detail": "Нельзя удалить должность: она используется у пользователей."},
                status=status.HTTP_409_CONFLICT,
            )
        pos_id = instance.id
        self.perform_destroy(instance)
        log_event(
            action=AuditEvents.POSITION_DELETED,
            actor=request.user,
            object_type="position",
            object_id=str(pos_id),
            category="content",
            ip_address=self._ip(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrgStructureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _base_member_payload(self, user):
        return {
            "id": user.id,
            "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
            "position": user.position.name if user.position_id else (user.custom_position or ""),
            "role": user.role.name if user.role_id else "",
        }

    def _detailed_member_payload(self, user):
        data = self._base_member_payload(user)
        data.update(
            {
                "username": user.username,
                "telegram": user.telegram,
                "phone": user.phone,
            }
        )
        return data

    def get(self, request):
        actor = request.user
        role_filter = request.query_params.get("role")
        position_filter = request.query_params.get("position")

        users_qs = User.objects.select_related("department", "position", "role", "manager")
        if role_filter:
            users_qs = users_qs.filter(role__name=role_filter)
        if position_filter:
            users_qs = users_qs.filter(position__name=position_filter)

        users_by_department = {}
        for user in users_qs:
            users_by_department.setdefault(user.department_id, []).append(user)

        departments = Department.objects.select_related("parent").order_by("name")
        result = []

        is_admin_like = AccessPolicy.is_admin_like(actor)
        is_teamlead_like = AccessPolicy.is_teamlead(actor)
        subordinate_ids = set(actor.team_members.values_list("id", flat=True))

        for department in departments:
            members = users_by_department.get(department.id, [])
            payload_members = []
            for member in members:
                # Intern: only own department and only basic data.
                if AccessPolicy.is_intern(actor) and member.department_id != actor.department_id:
                    continue

                if is_admin_like:
                    payload_members.append(self._detailed_member_payload(member))
                    continue

                if is_teamlead_like:
                    if member.id in subordinate_ids or member.id == actor.id:
                        payload_members.append(self._detailed_member_payload(member))
                    else:
                        payload_members.append(self._base_member_payload(member))
                    continue

                # Employee/intern basic visibility.
                payload_members.append(self._base_member_payload(member))

            # Intern sees members only in own department.
            if AccessPolicy.is_intern(actor) and department.id != actor.department_id:
                payload_members = []

            result.append(
                {
                    "id": department.id,
                    "name": department.name,
                    "parent_id": department.parent_id,
                    "members": payload_members,
                }
            )

        return Response({"departments": result})


class EmployeeHomeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (
            AccessPolicy.is_employee(request.user)
            or AccessPolicy.is_admin(request.user)
            or AccessPolicy.is_super_admin(request.user)
        ):
            return Response({"detail": "Access denied."}, status=403)

        my_courses = CourseEnrollment.objects.filter(
            user=request.user,
            course__is_active=True,
        ).count()
        completed_courses = CourseEnrollment.objects.filter(
            user=request.user,
            course__is_active=True,
            status=CourseEnrollment.Status.COMPLETED,
        ).count()

        available_courses_qs = Course.objects.filter(
            is_active=True,
            visibility=Course.Visibility.PUBLIC,
        )
        if request.user.department_id:
            available_courses_qs = available_courses_qs | Course.objects.filter(
                is_active=True,
                visibility=Course.Visibility.DEPARTMENT,
                department_id=request.user.department_id,
            )

        reports_count = EmployeeDailyReport.objects.filter(user=request.user).count()

        return Response(
            {
                "greeting": f"Здравствуйте, {request.user.first_name or request.user.username}!",
                "username": request.user.username,
                "my_courses_count": my_courses,
                "completed_courses_count": completed_courses,
                "available_courses_count": available_courses_qs.distinct().count(),
                "daily_reports_count": reports_count,
            }
        )


class CompanyStructureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = []
        for department in Department.objects.filter(is_active=True):
            head = (
                User.objects.filter(department=department, manager__isnull=True)
                .exclude(role__name=Role.Name.INTERN)
                .order_by("id")
                .first()
            )
            departments.append(
                {
                    "id": department.id,
                    "name": department.name,
                    "head": (
                        {
                            "id": head.id,
                            "username": head.username,
                            "full_name": f"{head.first_name} {head.last_name}".strip(),
                        }
                        if head
                        else None
                    ),
                }
            )

        owner = (
            User.objects.filter(
                Q(first_name__iexact="Николай")
                | Q(username__iexact="nikolay")
                | Q(username__iexact="nikolai")
            )
            .order_by("id")
            .first()
        )

        return Response(
            {
                "owner": (
                    {
                        "id": owner.id,
                        "username": owner.username,
                        "full_name": f"{owner.first_name} {owner.last_name}".strip()
                        or owner.username,
                    }
                    if owner
                    else {"full_name": "Николай"}
                ),
                "departments": departments,
            }
        )
