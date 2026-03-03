from __future__ import annotations

import mimetypes

from django.contrib.auth import authenticate
from django.http import FileResponse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.access_policy import AccessPolicy
from accounts.models import AuditLog, Department, Position, PromotionRequest, Role, User
from accounts.serializers import PasswordChangeSerializer, UserProfileUpdateSerializer
from content.models import Feedback, Instruction, News
from content.serializers import (
    InstructionSerializer,
    NewsDetailSerializer,
    NewsListSerializer,
)
from onboarding_core.views import OnboardingOverviewView
from regulations.models import (
    Regulation,
    RegulationAcknowledgement,
    RegulationFeedback,
    RegulationQuiz,
    RegulationQuizAttempt,
    RegulationQuizOption,
    RegulationQuizQuestion,
    RegulationReadProgress,
    RegulationReadReport,
)
from regulations.serializers import RegulationAdminSerializer, RegulationSerializer
from reports.models import OnboardingReport
from work_schedule.models import ProductionCalendar
from work_schedule.views import MyScheduleAPIView, WorkScheduleListAPIView

ROLE_SUPER_ADMIN = getattr(Role.Name, "SUPER_ADMIN", "SUPER_ADMIN")
ROLE_ADMIN = getattr(Role.Name, "ADMIN", "ADMIN")
ROLE_ADMINISTRATOR = getattr(Role.Name, "ADMINISTRATOR", "ADMINISTRATOR")
ROLE_DEPARTMENT_HEAD = getattr(Role.Name, "DEPARTMENT_HEAD", None)
ROLE_TEAMLEAD = getattr(Role.Name, "TEAMLEAD", "TEAMLEAD")
ROLE_EMPLOYEE = getattr(Role.Name, "EMPLOYEE", "EMPLOYEE")
ROLE_INTERN = getattr(Role.Name, "INTERN", "INTERN")

PRIVILEGED_ROLE_NAMES = {ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_ADMINISTRATOR}
if ROLE_DEPARTMENT_HEAD:
    PRIVILEGED_ROLE_NAMES.add(ROLE_DEPARTMENT_HEAD)


def _role_to_front(role: Role | None) -> str:
    if not role:
        return ""
    mapping = {
        ROLE_SUPER_ADMIN: "superadmin",
        ROLE_ADMIN: "admin",
        ROLE_ADMINISTRATOR: "administrator",
        ROLE_TEAMLEAD: "projectmanager",
        ROLE_EMPLOYEE: "employee",
        ROLE_INTERN: "intern",
    }
    if ROLE_DEPARTMENT_HEAD:
        mapping[ROLE_DEPARTMENT_HEAD] = "department_head"
    return mapping.get(role.name, role.name.lower())


def _user_to_front_payload(user: User) -> dict:
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    role_front = _role_to_front(user.role)
    role_label_map = {
        "intern": "Стажер",
        "employee": "Сотрудник",
        "projectmanager": "Тимлид",
        "department_head": "Руководитель отдела",
        "admin": "Админ",
        "superadmin": "Суперадмин",
    }
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": full_name,
        "role": role_front,
        "role_label": role_label_map.get(role_front, role_front),
        "department": user.department_id,
        "department_name": user.department.name if user.department_id else "",
        "subdivision": user.department_id,
        "subdivision_name": user.department.name if user.department_id else "",
        "position": user.position_id,
        "position_name": user.position.name if user.position_id else (user.custom_position or ""),
        "manager": user.manager_id,
        "manager_name": (
            f"{user.manager.first_name} {user.manager.last_name}".strip() or user.manager.username
            if user.manager_id
            else ""
        ),
        "phone": user.phone or "",
        "telegram": user.telegram or "",
        "photo": user.photo.url if getattr(user, "photo", None) else "",
        "hire_date": user.date_joined.date().isoformat() if user.date_joined else None,
        "is_active": user.is_active,
    }


def _ensure_admin_like(user: User):
    if not (AccessPolicy.is_admin_like(user) or _is_department_scoped_admin(user)):
        raise PermissionDenied("Only department head/admin/super admin can perform this action.")


def _ensure_content_manager(user: User):
    if not AccessPolicy.is_admin_like(user):
        raise PermissionDenied("Only admin/super admin can manage content.")


def _ensure_structure_editor(user: User):
    if not (AccessPolicy.is_super_admin(user) or AccessPolicy.is_administrator(user)):
        raise PermissionDenied("Only administrator/super admin can edit company structure.")


def _role_name(user: User | None) -> str:
    return str(getattr(getattr(user, "role", None), "name", "")).upper()


def _is_department_scoped_admin(user: User | None) -> bool:
    return _role_name(user) in {"DEPARTMENT_HEAD", "DEPARTMENTHEAD"}


def _is_privileged_target(target: User) -> bool:
    if not getattr(target, "role_id", None):
        return False
    return target.role.name in PRIVILEGED_ROLE_NAMES


def _first_validation_error(errors) -> str:
    if isinstance(errors, dict):
        for value in errors.values():
            if isinstance(value, (list, tuple)) and value:
                return str(value[0])
            if isinstance(value, dict):
                nested = _first_validation_error(value)
                if nested:
                    return nested
            if value:
                return str(value)
    elif isinstance(errors, (list, tuple)) and errors:
        return str(errors[0])
    return "Validation error."


def _resolve_role(value: str | None) -> Role | None:
    if not value:
        return None
    normalized = str(value).strip().upper()
    aliases = {
        "PROJECTMANAGER": ROLE_TEAMLEAD,
        "PROJECT_MANAGER": ROLE_TEAMLEAD,
        "TEAMLEAD": ROLE_TEAMLEAD,
        "TEAM_LEAD": ROLE_TEAMLEAD,
        "DEPARTMENTHEAD": ROLE_DEPARTMENT_HEAD or ROLE_ADMIN,
        "DEPARTMENT_HEAD": ROLE_DEPARTMENT_HEAD or ROLE_ADMIN,
        "ADMIN": ROLE_ADMIN,
        "ADMINISTRATOR": ROLE_ADMINISTRATOR,
        "SUPERADMIN": ROLE_SUPER_ADMIN,
        "SUPER_ADMIN": ROLE_SUPER_ADMIN,
        "EMPLOYEE": ROLE_EMPLOYEE,
        "INTERN": ROLE_INTERN,
    }
    role_name = aliases.get(normalized)
    if not role_name:
        return None
    return Role.objects.filter(name=role_name).first()


class FrontendLoginAPIView(APIView):
    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"error": "Username and password are required"}, status=400)

        user = User.objects.filter(Q(username=username) | Q(email__iexact=username)).first()
        auth_username = user.username if user else username
        authed_user = authenticate(username=auth_username, password=password)
        if not authed_user:
            return Response({"error": "Invalid credentials"}, status=400)
        if authed_user.is_blocked:
            return Response({"error": "User blocked"}, status=403)

        refresh = RefreshToken.for_user(authed_user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "landing": "admin_panel" if AccessPolicy.is_admin_like(authed_user) else "employee_portal",
                "user": _user_to_front_payload(authed_user),
            }
        )


class FrontendLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                token = RefreshToken(refresh)
                token.blacklist()
            except Exception:
                pass
        return Response({"detail": "Logged out."}, status=200)


class FrontendMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_to_front_payload(request.user))

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return Response(_user_to_front_payload(request.user))


class FrontendMePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."}, status=200)


class FrontendUsersSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=False, write_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "department",
            "position",
            "manager",
            "custom_position",
            "telegram",
            "phone",
            "is_active",
            "role",
            "password",
            "photo",
        )

    def validate_role(self, value):
        if not value:
            return value
        role = _resolve_role(value)
        if not role:
            raise serializers.ValidationError("Unknown role.")
        return role.name


class FrontendUsersCollectionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _inject_names_from_full_name(data):
        payload = dict(data)
        full_name = str(payload.get("full_name") or "").strip()
        if full_name:
            first_name = str(payload.get("first_name") or "").strip()
            last_name = str(payload.get("last_name") or "").strip()
            if not first_name or not last_name:
                parts = full_name.split()
                if parts:
                    payload["first_name"] = parts[0]
                    payload["last_name"] = " ".join(parts[1:]) if len(parts) > 1 else ""
        return payload

    def get(self, request):
        if not (AccessPolicy.is_admin_like(request.user) or AccessPolicy.is_teamlead(request.user)):
            raise PermissionDenied("Only department head/admin/super admin/teamlead can perform this action.")
        qs = User.objects.select_related("role", "department", "position", "manager").order_by("id")
        if AccessPolicy.is_teamlead(request.user) and not AccessPolicy.is_admin_like(request.user):
            # Teamlead can only see direct subordinates.
            qs = qs.filter(manager_id=request.user.id)
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            qs = qs.filter(
                Q(role__name=ROLE_INTERN)
                | Q(role__name=ROLE_EMPLOYEE, department_id=request.user.department_id)
                | Q(role__name=ROLE_TEAMLEAD, department_id=request.user.department_id)
            )
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return Response([_user_to_front_payload(item) for item in qs])

    def post(self, request):
        _ensure_structure_editor(request.user)
        incoming = self._inject_names_from_full_name(request.data)
        serializer = FrontendUsersSerializer(data=incoming)
        if not serializer.is_valid():
            return Response(
                {"detail": _first_validation_error(serializer.errors), "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validated = dict(serializer.validated_data)
        password = validated.pop("password", None)
        role_name = validated.pop("role", None)

        user = User(**validated)
        user.role = _resolve_role(role_name) or Role.objects.filter(name=ROLE_INTERN).first()
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            # Department head can create employees/teamleads only in own department.
            # Interns must be created without department.
            if user.role and user.role.name in {ROLE_EMPLOYEE, ROLE_TEAMLEAD}:
                if not request.user.department_id:
                    return Response({"detail": "Department head must belong to a department."}, status=400)
                user.department_id = request.user.department_id
            elif user.role and user.role.name == ROLE_INTERN:
                user.department = None

        if user.role and user.role.name == ROLE_TEAMLEAD and user.manager_id:
            return Response({"detail": "Teamlead cannot have a manager."}, status=400)
        if user.manager_id:
            manager = User.objects.select_related("role").filter(id=user.manager_id).first()
            if not manager or manager.role.name != ROLE_TEAMLEAD:
                return Response({"detail": "Manager must be a teamlead."}, status=400)
            if (
                (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user))
                and request.user.department_id
                and manager.department_id != request.user.department_id
            ):
                return Response({"detail": "Department head can assign only teamleads from own department."}, status=403)
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if user.role and user.role.name in PRIVILEGED_ROLE_NAMES:
                return Response({"detail": "Department head cannot create privileged users."}, status=403)
        if not user.role:
            return Response({"detail": "Default role INTERN not found. Run role seed first."}, status=400)
        if password:
            user.set_password(password)
        else:
            user.set_password("ChangeMe123!")
        user.save()
        return Response(_user_to_front_payload(user), status=status.HTTP_201_CREATED)


class FrontendUsersDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user(self, user_id: int) -> User:
        user = User.objects.select_related("role", "department", "position", "manager").filter(id=user_id).first()
        if not user:
            raise NotFound("User not found.")
        return user

    def patch(self, request, user_id: int):
        _ensure_structure_editor(request.user)
        target = self._get_user(user_id)
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if _is_privileged_target(target):
                return Response({"detail": "Department head cannot edit privileged users."}, status=403)
        serializer = FrontendUsersSerializer(target, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"detail": _first_validation_error(serializer.errors), "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validated = dict(serializer.validated_data)
        role_name = validated.pop("role", None)
        password = validated.pop("password", None)
        next_role = _resolve_role(role_name) if role_name else target.role
        if role_name and (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if next_role and next_role.name in PRIVILEGED_ROLE_NAMES:
                return Response({"detail": "Department head cannot assign privileged role."}, status=403)

        if next_role and next_role.name == ROLE_TEAMLEAD:
            if "manager" in validated and validated.get("manager"):
                return Response({"detail": "Teamlead cannot have a manager."}, status=400)
            validated["manager"] = None
        if "manager" in validated:
            manager = validated.get("manager")
            if manager:
                manager = User.objects.select_related("role").filter(id=manager.id).first()
                if not manager or manager.role.name != ROLE_TEAMLEAD:
                    return Response({"detail": "Manager must be a teamlead."}, status=400)
                if (
                    (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user))
                    and request.user.department_id
                    and manager.department_id != request.user.department_id
                ):
                    return Response({"detail": "Department head can assign only teamleads from own department."}, status=403)
        for field, value in validated.items():
            setattr(target, field, value)
        if role_name:
            target.role = next_role
            if next_role and next_role.name == ROLE_TEAMLEAD:
                target.manager = None
        if password:
            target.set_password(password)
        target.save()
        return Response(_user_to_front_payload(target))

    def delete(self, request, user_id: int):
        _ensure_structure_editor(request.user)
        target = self._get_user(user_id)
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if _is_privileged_target(target):
                return Response({"detail": "Department head cannot delete privileged users."}, status=403)
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FrontendUsersToggleStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id: int):
        _ensure_structure_editor(request.user)
        target = User.objects.filter(id=user_id).first()
        if not target:
            raise NotFound("User not found.")
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if _is_privileged_target(target):
                return Response({"detail": "Department head cannot change status of privileged users."}, status=403)
        target.is_active = not target.is_active
        target.is_blocked = not target.is_active
        target.save(update_fields=["is_active", "is_blocked"])
        target.refresh_from_db()
        return Response(_user_to_front_payload(target))


class FrontendUsersSetRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id: int):
        _ensure_structure_editor(request.user)
        target = User.objects.filter(id=user_id).first()
        if not target:
            raise NotFound("User not found.")
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if _is_privileged_target(target):
                return Response({"detail": "Department head cannot change role of privileged users."}, status=403)
        role = _resolve_role(request.data.get("role"))
        if not role:
            return Response({"detail": "Invalid role."}, status=400)
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if role.name in PRIVILEGED_ROLE_NAMES:
                return Response({"detail": "Department head cannot assign privileged role."}, status=403)
        target.role = role
        if role.name == ROLE_TEAMLEAD:
            target.manager = None
            target.save(update_fields=["role", "manager"])
        else:
            target.save(update_fields=["role"])
        target.refresh_from_db()
        return Response(_user_to_front_payload(target))


class FrontendDepartmentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items_qs = Department.objects.select_related("parent")
        if "subdivisions" in (request.path or ""):
            items_qs = items_qs.filter(parent__isnull=False)
        items = list(items_qs.order_by("name"))
        children_counter = {}
        for dep in items:
            if dep.parent_id:
                children_counter[dep.parent_id] = children_counter.get(dep.parent_id, 0) + 1
        return Response(
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "comment": item.comment or "",
                    "parent": item.parent_id,
                    "is_active": item.is_active,
                    "children_count": children_counter.get(item.id, 0),
                }
                for item in items
            ]
        )

    def post(self, request):
        _ensure_structure_editor(request.user)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": ["This field is required."]}, status=400)
        if "subdivisions" in (request.path or "") and not request.data.get("parent"):
            return Response({"parent": ["Subdivision must have a parent department."]}, status=400)
        parent_id = request.data.get("parent")
        parent = None
        if parent_id:
            parent = Department.objects.filter(id=parent_id).first()
            if not parent:
                return Response({"parent": ["Parent department not found."]}, status=400)
        item = Department.objects.create(
            name=name,
            comment=(request.data.get("comment") or "").strip(),
            parent=parent,
            is_active=bool(request.data.get("is_active", True)),
        )
        return Response(
            {
                "id": item.id,
                "name": item.name,
                "comment": item.comment or "",
                "parent": item.parent_id,
                "is_active": item.is_active,
                "children_count": 0,
            },
            status=201,
        )


class FrontendDepartmentsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, department_id: int):
        _ensure_structure_editor(request.user)
        item = Department.objects.filter(id=department_id).first()
        if not item:
            raise NotFound("Department not found.")

        if "name" in request.data:
            name = (request.data.get("name") or "").strip()
            if not name:
                return Response({"name": ["This field is required."]}, status=400)
            item.name = name

        if "comment" in request.data:
            item.comment = (request.data.get("comment") or "").strip()

        if "is_active" in request.data:
            item.is_active = bool(request.data.get("is_active"))

        if "parent" in request.data:
            parent_id = request.data.get("parent")
            if not parent_id:
                item.parent = None
            else:
                parent = Department.objects.filter(id=parent_id).first()
                if not parent:
                    return Response({"parent": ["Parent department not found."]}, status=400)
                if parent.id == item.id:
                    return Response({"parent": ["Department cannot be parent of itself."]}, status=400)
                cursor = parent
                while cursor is not None:
                    if cursor.id == item.id:
                        return Response({"parent": ["Department hierarchy cycle is not allowed."]}, status=400)
                    cursor = cursor.parent
                item.parent = parent

        item.save()
        return Response(
            {
                "id": item.id,
                "name": item.name,
                "comment": item.comment or "",
                "parent": item.parent_id,
                "is_active": item.is_active,
            }
        )

    def delete(self, request, department_id: int):
        _ensure_structure_editor(request.user)
        item = Department.objects.filter(id=department_id).first()
        if not item:
            raise NotFound("Department not found.")
        if User.objects.filter(department=item).exists():
            return Response({"detail": "Department has users and cannot be deleted."}, status=400)
        item.delete()
        return Response(status=204)


class FrontendPositionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Position.objects.order_by("name")
        return Response([{"id": item.id, "name": item.name, "is_active": item.is_active} for item in items])

    def post(self, request):
        _ensure_structure_editor(request.user)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": ["This field is required."]}, status=400)
        item = Position.objects.create(name=name, is_active=bool(request.data.get("is_active", True)))
        return Response({"id": item.id, "name": item.name, "is_active": item.is_active}, status=201)


class FrontendPositionsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, position_id: int):
        _ensure_structure_editor(request.user)
        item = Position.objects.filter(id=position_id).first()
        if not item:
            raise NotFound("Position not found.")
        item.delete()
        return Response(status=204)


class FrontendPromotionRequestsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    def get(self, request):
        _ensure_admin_like(request.user)
        qs = PromotionRequest.objects.select_related("user", "requested_role", "reviewed_by").order_by("-created_at")
        status_value = (request.query_params.get("status") or "").strip().lower()
        if status_value in {PromotionRequest.Status.PENDING, PromotionRequest.Status.APPROVED, PromotionRequest.Status.REJECTED}:
            qs = qs.filter(status=status_value)
        return Response(
            [
                {
                    "id": item.id,
                    "user_id": item.user_id,
                    "username": item.user.username,
                    "requested_role": _role_to_front(item.requested_role),
                    "reason": item.reason,
                    "status": item.status,
                    "review_comment": item.review_comment,
                    "reviewed_by": item.reviewed_by.username if item.reviewed_by_id else None,
                    "reviewed_at": item.reviewed_at,
                    "created_at": item.created_at,
                }
                for item in qs
            ]
        )

    def post(self, request):
        role = _resolve_role(request.data.get("role") or request.data.get("requested_role"))
        if not role:
            return Response({"detail": "Invalid requested role."}, status=400)
        target_user = request.user
        requested_user_id = request.data.get("user_id")
        if requested_user_id:
            _ensure_admin_like(request.user)
            candidate = User.objects.filter(id=requested_user_id).first()
            if not candidate:
                return Response({"detail": "Target user not found."}, status=404)
            target_user = candidate
        reason = (request.data.get("reason") or "").strip()
        item = PromotionRequest.objects.create(
            user=target_user,
            requested_role=role,
            reason=reason,
        )
        return Response(
            {
                "id": item.id,
                "user_id": item.user_id,
                "requested_role": _role_to_front(item.requested_role),
                "reason": item.reason,
                "status": item.status,
                "created_at": item.created_at,
            },
            status=201,
        )


class FrontendPromotionRequestsActionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    def post(self, request, request_id: int, action: str):
        _ensure_admin_like(request.user)
        item = PromotionRequest.objects.select_related("user", "requested_role").filter(id=request_id).first()
        if not item:
            raise NotFound("Promotion request not found.")
        if item.status != PromotionRequest.Status.PENDING:
            return Response({"detail": "Request already processed."}, status=400)

        action_value = (action or "").strip().lower()
        comment = (request.data.get("comment") or request.data.get("reason") or "").strip()
        if action_value == "approve":
            item.status = PromotionRequest.Status.APPROVED
            item.user.role = item.requested_role
            item.user.save(update_fields=["role"])
        elif action_value == "reject":
            item.status = PromotionRequest.Status.REJECTED
        else:
            return Response({"detail": "Unknown action."}, status=400)

        item.review_comment = comment
        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.save(update_fields=["status", "review_comment", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(
            {
                "id": item.id,
                "status": item.status,
                "review_comment": item.review_comment,
                "reviewed_at": item.reviewed_at,
            }
        )


class FrontendNewsCollectionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    def get(self, request):
        language = request.query_params.get("language", "ru")
        qs = News.objects.filter(is_active=True, language=language).order_by("position", "-published_at")[:10]
        return Response(NewsListSerializer(qs, many=True).data)

    def post(self, request):
        _ensure_content_manager(request.user)
        serializer = NewsDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        news = News.objects.create(
            language=request.data.get("language", "ru"),
            title=serializer.validated_data["title"],
            full_text=serializer.validated_data["full_text"],
            published_at=serializer.validated_data["published_at"],
            image=serializer.validated_data.get("image"),
            is_active=bool(request.data.get("is_active", True)),
            position=int(request.data.get("position", 0)),
            created_by=request.user,
        )
        return Response(NewsDetailSerializer(news).data, status=201)


class FrontendNewsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, news_id):
        item = News.objects.filter(id=news_id, is_active=True).first()
        if not item:
            raise NotFound("News not found.")
        return Response(NewsDetailSerializer(item).data)

    def patch(self, request, news_id):
        _ensure_content_manager(request.user)
        item = News.objects.filter(id=news_id).first()
        if not item:
            raise NotFound("News not found.")
        serializer = NewsDetailSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(NewsDetailSerializer(item).data)

    def delete(self, request, news_id):
        _ensure_content_manager(request.user)
        item = News.objects.filter(id=news_id).first()
        if not item:
            raise NotFound("News not found.")
        item.delete()
        return Response(status=204)


class FrontendAuditListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _ensure_admin_like(request.user)
        qs = AuditLog.objects.select_related("user").order_by("-created_at")
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if request.user.department_id:
                qs = qs.filter(user__department_id=request.user.department_id)
            else:
                qs = qs.none()
        level = request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)
        payload = [
            {
                "id": item.id,
                "actor_id": item.user_id,
                "actor_username": item.user.username if item.user_id else "",
                "action": item.action,
                "level": item.level,
                "category": item.category,
                "metadata": item.metadata if hasattr(item, "metadata") else None,
                "created_at": item.created_at,
            }
            for item in qs[:200]
        ]
        return Response(payload)


class FrontendRegulationsCollectionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Regulation.objects.filter(is_active=True).order_by("position", "-created_at")
        regulation_type = request.query_params.get("type")
        if regulation_type in {Regulation.RegulationType.LINK, Regulation.RegulationType.FILE}:
            qs = qs.filter(type=regulation_type)
        read_progress_map = {
            progress.regulation_id: progress
            for progress in RegulationReadProgress.objects.filter(
                user=request.user,
                regulation__in=qs,
            )
        }
        today = timezone.localdate()
        read_report_map = {
            report.regulation_id: True
            for report in RegulationReadReport.objects.filter(
                user=request.user,
                regulation__in=qs,
                opened_on=today,
            )
        }
        quiz_required_map = {
            regulation_id: True
            for regulation_id in RegulationQuiz.objects.filter(
                regulation__in=qs,
                is_active=True,
            ).values_list("regulation_id", flat=True)
        }
        quiz_passed_map = {
            attempt.quiz.regulation_id: True
            for attempt in RegulationQuizAttempt.objects.filter(
                user=request.user,
                passed=True,
                quiz__regulation__in=qs,
                quiz__is_active=True,
            ).select_related("quiz")
        }
        ack_map = {
            ack.regulation_id: ack
            for ack in RegulationAcknowledgement.objects.filter(user=request.user, regulation__in=qs)
        }
        serializer = RegulationSerializer(
            qs,
            many=True,
            context={
                "request": request,
                "ack_map": ack_map,
                "read_progress_map": read_progress_map,
                "read_report_map": read_report_map,
                "quiz_required_map": quiz_required_map,
                "quiz_passed_map": quiz_passed_map,
            },
        )
        return Response([_append_front_quiz_payload(item, reg, request=request) for item, reg in zip(serializer.data, qs)])

    def post(self, request):
        _ensure_content_manager(request.user)
        serializer = RegulationAdminSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        _apply_front_quiz_patch(instance, request.data, partial=False)
        output = RegulationAdminSerializer(instance, context={"request": request}).data
        return Response(_append_front_quiz_payload(output, instance, request=request), status=201)


class FrontendRegulationsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, regulation_id):
        item = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not item:
            raise NotFound("Regulation not found.")
        ack = RegulationAcknowledgement.objects.filter(user=request.user, regulation=item).first()
        progress = RegulationReadProgress.objects.filter(user=request.user, regulation=item).first()
        today = timezone.localdate()
        has_report = RegulationReadReport.objects.filter(
            user=request.user,
            regulation=item,
            opened_on=today,
        ).exists()
        quiz_required = RegulationQuiz.objects.filter(regulation=item, is_active=True).exists()
        quiz_passed = RegulationQuizAttempt.objects.filter(
            user=request.user,
            quiz__regulation=item,
            quiz__is_active=True,
            passed=True,
        ).exists()
        serializer = RegulationSerializer(
            item,
            context={
                "request": request,
                "ack_map": {item.id: ack} if ack else {},
                "read_progress_map": {item.id: progress} if progress else {},
                "read_report_map": {item.id: has_report},
                "quiz_required_map": {item.id: quiz_required},
                "quiz_passed_map": {item.id: quiz_passed},
            },
        )
        return Response(_append_front_quiz_payload(serializer.data, item, request=request))

    def patch(self, request, regulation_id):
        _ensure_content_manager(request.user)
        item = Regulation.objects.filter(id=regulation_id).first()
        if not item:
            raise NotFound("Regulation not found.")
        serializer = RegulationAdminSerializer(item, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _apply_front_quiz_patch(item, request.data, partial=True)
        output = RegulationAdminSerializer(item, context={"request": request}).data
        return Response(_append_front_quiz_payload(output, item, request=request))

    def delete(self, request, regulation_id):
        _ensure_content_manager(request.user)
        item = Regulation.objects.filter(id=regulation_id).first()
        if not item:
            raise NotFound("Regulation not found.")
        item.delete()
        return Response(status=204)


def _normalize_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "да"}


def _current_quiz_payload(regulation: Regulation):
    quiz = (
        RegulationQuiz.objects.filter(regulation=regulation, is_active=True)
        .prefetch_related("questions__options")
        .first()
    )
    if not quiz:
        return {
            "quiz_required": False,
            "quiz_question": regulation.quiz_question or "",
            "quiz_options": [],
            "quiz_expected_answer": regulation.quiz_expected_answer or "",
        }
    question = quiz.questions.order_by("position", "id").first()
    options = list(question.options.order_by("position", "id")) if question else []
    expected = next((opt.text for opt in options if opt.is_correct), regulation.quiz_expected_answer or "")
    return {
        "quiz_required": True,
        "quiz_question": question.text if question else (regulation.quiz_question or ""),
        "quiz_options": [opt.text for opt in options],
        "quiz_expected_answer": expected or "",
    }


def _regulation_open_url(request, regulation: Regulation) -> str:
    if regulation.type != Regulation.RegulationType.FILE or not regulation.file:
        return ""
    return request.build_absolute_uri(f"/api/v1/content/regulations/{regulation.id}/open/")


def _append_front_quiz_payload(data, regulation: Regulation, request=None):
    payload = dict(data)
    payload.update(_current_quiz_payload(regulation))
    if request and regulation.type == Regulation.RegulationType.FILE and regulation.file:
        open_url = _regulation_open_url(request, regulation)
        payload["file_url"] = open_url
        payload["content"] = open_url
    return payload


def _validate_quiz_fields(quiz_question, quiz_options, quiz_expected_answer):
    if not quiz_question:
        raise serializers.ValidationError({"quiz_question": ["This field is required when quiz is enabled."]})
    if not isinstance(quiz_options, list):
        raise serializers.ValidationError({"quiz_options": ["Must be an array of strings."]})
    normalized_options = [str(item).strip() for item in quiz_options if str(item).strip()]
    if len(normalized_options) < 2:
        raise serializers.ValidationError({"quiz_options": ["Provide at least 2 answer options."]})
    if not quiz_expected_answer:
        raise serializers.ValidationError({"quiz_expected_answer": ["This field is required when quiz is enabled."]})
    if quiz_expected_answer not in normalized_options:
        raise serializers.ValidationError(
            {"quiz_expected_answer": ["Must exactly match one of quiz_options."]}
        )
    return normalized_options


def _apply_front_quiz_patch(regulation: Regulation, data, partial: bool):
    has_quiz_payload = any(
        field in data for field in ("quiz_required", "quiz_question", "quiz_options", "quiz_expected_answer")
    )
    if not has_quiz_payload:
        return

    current = _current_quiz_payload(regulation)
    if "quiz_required" in data:
        quiz_required = _normalize_bool(data.get("quiz_required"))
    elif partial:
        quiz_required = bool(current["quiz_required"])
    else:
        quiz_required = False

    if not quiz_required:
        RegulationQuiz.objects.filter(regulation=regulation).update(is_active=False)
        regulation.quiz_question = ""
        regulation.quiz_expected_answer = ""
        regulation.save(update_fields=["quiz_question", "quiz_expected_answer", "updated_at"])
        return

    quiz_question = str(data.get("quiz_question", current.get("quiz_question") or "")).strip()
    quiz_options = data.get("quiz_options", current.get("quiz_options") or [])
    quiz_expected_answer = str(
        data.get("quiz_expected_answer", current.get("quiz_expected_answer") or "")
    ).strip()
    quiz_options = _validate_quiz_fields(quiz_question, quiz_options, quiz_expected_answer)

    with transaction.atomic():
        regulation.quiz_question = quiz_question
        regulation.quiz_expected_answer = quiz_expected_answer
        regulation.save(update_fields=["quiz_question", "quiz_expected_answer", "updated_at"])

        quiz, _ = RegulationQuiz.objects.get_or_create(
            regulation=regulation,
            defaults={
                "title": f"Мини-тест: {regulation.title}",
                "description": "",
                "passing_score": 100,
                "is_active": True,
            },
        )
        quiz.is_active = True
        if not quiz.title:
            quiz.title = f"Мини-тест: {regulation.title}"
        if not quiz.passing_score:
            quiz.passing_score = 100
        quiz.save(update_fields=["title", "is_active", "passing_score", "updated_at"])

        quiz.questions.all().delete()
        question = RegulationQuizQuestion.objects.create(
            quiz=quiz,
            text=quiz_question,
            position=1,
        )
        for idx, option_text in enumerate(quiz_options, start=1):
            RegulationQuizOption.objects.create(
                question=question,
                text=option_text,
                is_correct=(option_text == quiz_expected_answer),
                position=idx,
            )


class FrontendRegulationsActionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, regulation_id, action):
        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            raise NotFound("Regulation not found.")
        normalized_action = str(action or "").strip().lower()
        if normalized_action in {"open", "file"}:
            if regulation.type != Regulation.RegulationType.FILE or not regulation.file:
                return Response({"detail": "File is not configured for this regulation."}, status=404)
            content_type, _ = mimetypes.guess_type(regulation.file.name)
            response = FileResponse(
                regulation.file.open("rb"),
                content_type=content_type or "application/octet-stream",
            )
            response["Content-Disposition"] = f'inline; filename="{regulation.file.name.split("/")[-1]}"'
            return response
        if normalized_action not in {"quiz", "test"}:
            raise NotFound("Unknown action.")

        quiz = (
            RegulationQuiz.objects.filter(regulation=regulation, is_active=True)
            .prefetch_related("questions__options")
            .first()
        )
        if not quiz:
            if not (regulation.quiz_question and regulation.quiz_expected_answer):
                return Response({"detail": "Quiz is not configured for this regulation."}, status=404)
            options = []
            if regulation.quiz_expected_answer:
                options.append(regulation.quiz_expected_answer)
            return Response(
                {
                    "regulation_id": str(regulation.id),
                    "quiz_required": True,
                    "question": regulation.quiz_question,
                    "options": options,
                }
            )

        question = quiz.questions.order_by("position", "id").first()
        if not question:
            return Response({"detail": "Quiz has no questions."}, status=404)
        options = [opt.text for opt in question.options.order_by("position", "id")]
        return Response(
            {
                "regulation_id": str(regulation.id),
                "quiz_required": True,
                "question": question.text,
                "options": options,
            }
        )

    def post(self, request, regulation_id, action):
        regulation = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not regulation:
            raise NotFound("Regulation not found.")
        normalized_action = str(action or "").strip().lower()
        if normalized_action in {"acknowledge", "mark-read"}:
            full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            RegulationAcknowledgement.objects.get_or_create(
                user=request.user,
                regulation=regulation,
                defaults={
                    "user_full_name": full_name,
                    "regulation_title": regulation.title,
                },
            )
            progress, _ = RegulationReadProgress.objects.get_or_create(
                user=request.user,
                regulation=regulation,
            )
            if not progress.is_read:
                progress.is_read = True
                progress.read_at = timezone.now()
                progress.save(update_fields=["is_read", "read_at"])
            quiz_required = RegulationQuiz.objects.filter(regulation=regulation, is_active=True).exists()
            quiz_passed = RegulationQuizAttempt.objects.filter(
                user=request.user,
                quiz__regulation=regulation,
                quiz__is_active=True,
                passed=True,
            ).exists()
            needs_quiz = AccessPolicy.is_intern(request.user) and quiz_required and not quiz_passed
            return Response({"status": "ok", "is_acknowledged": True, "needs_quiz": needs_quiz})

        if normalized_action == "feedback":
            text = (
                request.data.get("text")
                or request.data.get("message")
                or request.data.get("feedback")
                or ""
            ).strip()
            if not text:
                return Response({"text": ["This field is required."]}, status=400)
            feedback = RegulationFeedback.objects.create(
                user=request.user,
                regulation=regulation,
                text=text,
            )
            return Response({"id": feedback.id, "created_at": feedback.created_at}, status=201)

        if normalized_action in {"read-report", "report"}:
            text = (
                request.data.get("report_text")
                or request.data.get("report")
                or request.data.get("text")
                or request.data.get("message")
                or ""
            ).strip()
            if not text:
                return Response({"report_text": ["This field is required."]}, status=400)
            progress = RegulationReadProgress.objects.filter(
                user=request.user,
                regulation=regulation,
                is_read=True,
            ).first()
            if not progress or not progress.read_at:
                return Response({"detail": "Read/open regulation first before submitting report."}, status=400)
            opened_on = progress.read_at.date()
            today = timezone.localdate()
            report, created = RegulationReadReport.objects.get_or_create(
                user=request.user,
                regulation=regulation,
                opened_on=opened_on,
                defaults={
                    "report_text": text,
                    "submitted_at": timezone.now(),
                    "is_late": today > opened_on,
                },
            )
            if not created:
                report.report_text = text
                report.submitted_at = timezone.now()
                report.is_late = today > opened_on
                report.save(update_fields=["report_text", "submitted_at", "is_late"])
            return Response(
                {
                    "id": report.id,
                    "opened_on": report.opened_on,
                    "is_late": report.is_late,
                    "submitted_at": report.submitted_at,
                },
                status=201 if created else 200,
            )

        if normalized_action in {"quiz", "test"}:
            answer = str(request.data.get("answer") or request.data.get("user_answer") or "").strip()
            if not answer:
                return Response({"answer": ["This field is required."]}, status=400)

            quiz = (
                RegulationQuiz.objects.filter(regulation=regulation, is_active=True)
                .prefetch_related("questions__options")
                .first()
            )
            expected_answer = ""
            passing_score = 100
            if quiz:
                question = quiz.questions.order_by("position", "id").first()
                if question:
                    correct_option = question.options.filter(is_correct=True).order_by("position", "id").first()
                    if correct_option:
                        expected_answer = correct_option.text
                passing_score = int(quiz.passing_score or 100)
            if not expected_answer:
                expected_answer = regulation.quiz_expected_answer or ""
            if not expected_answer:
                return Response({"detail": "Quiz is not configured for this regulation."}, status=404)

            progress, _ = RegulationReadProgress.objects.get_or_create(
                user=request.user,
                regulation=regulation,
            )
            if not progress.is_read:
                progress.is_read = True
                progress.read_at = timezone.now()
                progress.save(update_fields=["is_read", "read_at"])

            passed = answer.casefold() == expected_answer.strip().casefold()
            score_percent = 100 if passed else 0
            result_payload = {
                "score_percent": score_percent,
                "passed": passed,
                "submitted_at": timezone.now(),
            }
            if quiz:
                attempt = RegulationQuizAttempt.objects.create(
                    user=request.user,
                    quiz=quiz,
                    score_percent=score_percent,
                    passed=passed,
                )
                result_payload["submitted_at"] = attempt.submitted_at

            return Response(
                {
                    "result": result_payload,
                    "passing_score": passing_score,
                    "correct_answers": 1 if passed else 0,
                    "questions_total": 1,
                },
                status=201,
            )

        raise NotFound("Unknown action.")


class FrontendInstructionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lang = request.query_params.get("lang")
        qs = Instruction.objects.filter(is_active=True)
        if lang:
            qs = qs.filter(language=lang)
        return Response(InstructionSerializer(qs.order_by("-updated_at"), many=True).data)

    def post(self, request):
        _ensure_content_manager(request.user)
        language = (request.data.get("language") or "ru").strip().lower()
        instruction_type = (request.data.get("type") or "text").strip().lower()
        content = (request.data.get("content") or "").strip()
        if language not in {"ru", "en", "kg"}:
            return Response({"language": ["Unsupported language."]}, status=400)
        if instruction_type not in {"text", "link", "file"}:
            return Response({"type": ["Unsupported instruction type."]}, status=400)
        if not content and instruction_type != "file":
            return Response({"content": ["This field is required."]}, status=400)

        payload = {
            "language": language,
            "type": instruction_type,
            "is_active": bool(request.data.get("is_active", True)),
        }
        if instruction_type == "text":
            payload["text"] = content
            payload["external_url"] = ""
        elif instruction_type == "link":
            payload["text"] = ""
            payload["external_url"] = content
        else:
            payload["text"] = ""
            payload["external_url"] = ""

        item = Instruction.objects.create(**payload)
        return Response(InstructionSerializer(item).data, status=201)


class FrontendInstructionsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, instruction_id):
        _ensure_content_manager(request.user)
        item = Instruction.objects.filter(id=instruction_id).first()
        if not item:
            raise NotFound("Instruction not found.")

        if "language" in request.data:
            language = (request.data.get("language") or "").strip().lower()
            if language not in {"ru", "en", "kg"}:
                return Response({"language": ["Unsupported language."]}, status=400)
            item.language = language

        if "type" in request.data:
            instruction_type = (request.data.get("type") or "").strip().lower()
            if instruction_type not in {"text", "link", "file"}:
                return Response({"type": ["Unsupported instruction type."]}, status=400)
            item.type = instruction_type

        if "is_active" in request.data:
            item.is_active = bool(request.data.get("is_active"))

        if "content" in request.data:
            content = (request.data.get("content") or "").strip()
            if item.type == "text":
                item.text = content
                item.external_url = ""
            elif item.type == "link":
                item.text = ""
                item.external_url = content
            else:
                item.text = ""
                item.external_url = ""

        item.save()
        return Response(InstructionSerializer(item).data)

    def delete(self, request, instruction_id):
        _ensure_content_manager(request.user)
        item = Instruction.objects.filter(id=instruction_id).first()
        if not item:
            raise NotFound("Instruction not found.")
        item.delete()
        return Response(status=204)


class FrontendOnboardingMyAPIView(OnboardingOverviewView):
    permission_classes = [IsAuthenticated]


class FrontendOnboardingReportsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = OnboardingReport.objects.select_related("day", "user").order_by("-updated_at", "day__day_number")
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if request.user.department_id:
                qs = qs.filter(user__department_id=request.user.department_id)
        elif not AccessPolicy.is_admin_like(request.user):
            qs = qs.filter(user=request.user)
        return Response(
            [
                {
                    "id": str(item.id),
                    "user_id": item.user_id,
                    "username": item.user.username,
                    "full_name": f"{item.user.first_name} {item.user.last_name}".strip() or item.user.username,
                    "day_id": str(item.day_id),
                    "day_number": item.day.day_number,
                    "did": item.did,
                    "will_do": item.will_do,
                    "problems": item.problems,
                    "status": item.status,
                    "reviewer_comment": item.reviewer_comment,
                    "updated_at": item.updated_at,
                }
                for item in qs
            ]
        )

    def post(self, request):
        if not AccessPolicy.is_intern(request.user):
            return Response({"detail": "Only intern can submit onboarding report."}, status=403)
        day_id = request.data.get("day_id")
        if not day_id:
            return Response({"day_id": ["This field is required."]}, status=400)
        did = (request.data.get("did") or "").strip()
        will_do = (request.data.get("will_do") or "").strip()
        problems = (request.data.get("problems") or "").strip()
        report, _ = OnboardingReport.objects.update_or_create(
            user=request.user,
            day_id=day_id,
            defaults={"did": did, "will_do": will_do, "problems": problems},
        )
        if did and will_do:
            report.status = OnboardingReport.Status.SENT
            report.save(update_fields=["status", "updated_at"])
        return Response({"id": str(report.id), "status": report.status}, status=201)


class FrontendOnboardingReportDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, report_id):
        report = OnboardingReport.objects.filter(id=report_id, user=request.user).first()
        if not report:
            raise NotFound("Report not found.")
        if not report.can_be_modified():
            return Response({"detail": "Report cannot be modified"}, status=409)
        for field in ("did", "will_do", "problems"):
            if field in request.data:
                setattr(report, field, request.data.get(field) or "")
        report.save(update_fields=["did", "will_do", "problems", "updated_at"])
        return Response({"id": str(report.id), "status": report.status})


class FrontendOnboardingReportReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        _ensure_admin_like(request.user)
        report = OnboardingReport.objects.filter(id=report_id).first()
        if not report:
            raise NotFound("Report not found.")
        if (_is_department_scoped_admin(request.user) or AccessPolicy.is_admin(request.user)) and not AccessPolicy.is_super_admin(request.user):
            if request.user.department_id and report.user.department_id != request.user.department_id:
                raise PermissionDenied("Access denied for this department.")
        status_value = request.data.get("status")
        comment = request.data.get("reviewer_comment") or request.data.get("comment")
        report.set_status(status_value, reviewer=request.user, comment=comment)
        return Response({"id": str(report.id), "status": report.status, "reviewer_comment": report.reviewer_comment})


class FrontendSchedulesWorkSchedulesAPIView(WorkScheduleListAPIView):
    permission_classes = [IsAuthenticated]


class FrontendSchedulesMineAPIView(MyScheduleAPIView):
    permission_classes = [IsAuthenticated]


class FrontendSchedulesHolidaysAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = request.query_params.get("year")
        qs = ProductionCalendar.objects.filter(is_holiday=True).order_by("date")
        if year:
            qs = qs.filter(date__year=year)
        return Response(
            [{"date": item.date, "name": item.holiday_name or "", "is_holiday": True} for item in qs]
        )


class FrontendFeedbackTicketsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = []

    @staticmethod
    def _to_bool(value, default=True):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return bool(value)

    def get(self, request):
        _ensure_admin_like(request.user)
        qs = Feedback.objects.all().order_by("-created_at")
        return Response(
            [
                {
                    "id": item.id,
                    "type": item.type,
                    "text": item.text,
                    "status": item.status,
                    "is_anonymous": item.is_anonymous,
                    "full_name": item.full_name,
                    "contact": item.contact,
                    "is_read": item.is_read,
                    "created_at": item.created_at,
                }
                for item in qs
            ]
        )

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        feedback_type = request.data.get("type") or "review"
        if not text:
            return Response({"text": ["This field is required."]}, status=400)
        item = Feedback.objects.create(
            type=feedback_type,
            text=text,
            is_anonymous=self._to_bool(request.data.get("is_anonymous"), default=True),
            full_name=request.data.get("full_name"),
            contact=request.data.get("contact"),
        )
        return Response({"id": item.id, "status": item.status}, status=201)


class FrontendFeedbackReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        _ensure_admin_like(request.user)
        item = Feedback.objects.filter(id=ticket_id).first()
        if not item:
            raise NotFound("Ticket not found.")
        # Legacy frontend expects reply endpoint. We mark ticket as in_progress/closed.
        new_status = request.data.get("status") or "in_progress"
        if new_status not in {"new", "in_progress", "closed"}:
            new_status = "in_progress"
        item.status = new_status
        item.is_read = True
        item.save(update_fields=["status", "is_read"])
        return Response({"id": item.id, "status": item.status})




