from __future__ import annotations

from django.contrib.auth import authenticate
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
from regulations.models import Regulation, RegulationAcknowledgement
from regulations.serializers import RegulationAdminSerializer, RegulationSerializer
from reports.models import OnboardingReport
from work_schedule.models import ProductionCalendar
from work_schedule.views import MyScheduleAPIView, WorkScheduleListAPIView


def _role_to_front(role: Role | None) -> str:
    if not role:
        return ""
    mapping = {
        Role.Name.SUPER_ADMIN: "superadmin",
        Role.Name.ADMIN: "admin",
        Role.Name.TEAMLEAD: "projectmanager",
        Role.Name.EMPLOYEE: "employee",
        Role.Name.INTERN: "intern",
    }
    return mapping.get(role.name, role.name.lower())


def _user_to_front_payload(user: User) -> dict:
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    role_front = _role_to_front(user.role)
    role_label_map = {
        "intern": "Стажёр",
        "employee": "Сотрудник",
        "projectmanager": "Проект-менеджер",
        "admin": "Администратор",
        "superadmin": "Суперадминистратор",
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
        "phone": user.phone or "",
        "telegram": user.telegram or "",
        "photo": user.photo.url if getattr(user, "photo", None) else "",
        "hire_date": user.date_joined.date().isoformat() if user.date_joined else None,
        "is_active": user.is_active,
    }


def _ensure_admin_like(user: User):
    if not AccessPolicy.is_admin_like(user):
        raise PermissionDenied("Only admin/super admin can perform this action.")


def _resolve_role(value: str | None) -> Role | None:
    if not value:
        return None
    normalized = str(value).strip().upper()
    aliases = {
        "PROJECTMANAGER": Role.Name.TEAMLEAD,
        "PROJECT_MANAGER": Role.Name.TEAMLEAD,
        "TEAMLEAD": Role.Name.TEAMLEAD,
        "TEAM_LEAD": Role.Name.TEAMLEAD,
        "ADMIN": Role.Name.ADMIN,
        "SUPERADMIN": Role.Name.SUPER_ADMIN,
        "SUPER_ADMIN": Role.Name.SUPER_ADMIN,
        "EMPLOYEE": Role.Name.EMPLOYEE,
        "INTERN": Role.Name.INTERN,
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

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "department",
            "position",
            "custom_position",
            "telegram",
            "phone",
            "is_active",
            "role",
            "password",
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

    def get(self, request):
        _ensure_admin_like(request.user)
        qs = User.objects.select_related("role", "department", "position").order_by("id")
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
        _ensure_admin_like(request.user)
        serializer = FrontendUsersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        password = validated.pop("password", None)
        role_name = validated.pop("role", None)

        user = User(**validated)
        user.role = _resolve_role(role_name) or Role.objects.filter(name=Role.Name.INTERN).first()
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
        user = User.objects.select_related("role", "department", "position").filter(id=user_id).first()
        if not user:
            raise NotFound("User not found.")
        return user

    def patch(self, request, user_id: int):
        _ensure_admin_like(request.user)
        target = self._get_user(user_id)
        serializer = FrontendUsersSerializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        role_name = validated.pop("role", None)
        password = validated.pop("password", None)
        for field, value in validated.items():
            setattr(target, field, value)
        if role_name:
            target.role = _resolve_role(role_name) or target.role
        if password:
            target.set_password(password)
        target.save()
        return Response(_user_to_front_payload(target))

    def delete(self, request, user_id: int):
        _ensure_admin_like(request.user)
        target = self._get_user(user_id)
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FrontendUsersToggleStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id: int):
        _ensure_admin_like(request.user)
        target = User.objects.filter(id=user_id).first()
        if not target:
            raise NotFound("User not found.")
        target.is_active = not target.is_active
        target.is_blocked = not target.is_active
        target.save(update_fields=["is_active", "is_blocked"])
        target.refresh_from_db()
        return Response(_user_to_front_payload(target))


class FrontendUsersSetRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id: int):
        _ensure_admin_like(request.user)
        target = User.objects.filter(id=user_id).first()
        if not target:
            raise NotFound("User not found.")
        role = _resolve_role(request.data.get("role"))
        if not role:
            return Response({"detail": "Invalid role."}, status=400)
        target.role = role
        target.save(update_fields=["role"])
        target.refresh_from_db()
        return Response(_user_to_front_payload(target))


class FrontendDepartmentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Department.objects.select_related("parent").order_by("name")
        return Response(
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "parent": item.parent_id,
                    "is_active": item.is_active,
                }
                for item in items
            ]
        )

    def post(self, request):
        _ensure_admin_like(request.user)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": ["This field is required."]}, status=400)
        parent_id = request.data.get("parent")
        item = Department.objects.create(
            name=name,
            parent_id=parent_id if parent_id else None,
            is_active=bool(request.data.get("is_active", True)),
        )
        return Response({"id": item.id, "name": item.name, "parent": item.parent_id, "is_active": item.is_active}, status=201)


class FrontendDepartmentsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, department_id: int):
        _ensure_admin_like(request.user)
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
        _ensure_admin_like(request.user)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": ["This field is required."]}, status=400)
        item = Position.objects.create(name=name, is_active=bool(request.data.get("is_active", True)))
        return Response({"id": item.id, "name": item.name, "is_active": item.is_active}, status=201)


class FrontendPositionsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, position_id: int):
        _ensure_admin_like(request.user)
        item = Position.objects.filter(id=position_id).first()
        if not item:
            raise NotFound("Position not found.")
        item.delete()
        return Response(status=204)


class FrontendPromotionRequestsAPIView(APIView):
    permission_classes = [IsAuthenticated]

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

    def get(self, request):
        language = request.query_params.get("language", "ru")
        qs = News.objects.filter(is_active=True, language=language).order_by("position", "-published_at")[:10]
        return Response(NewsListSerializer(qs, many=True).data)

    def post(self, request):
        _ensure_admin_like(request.user)
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
        _ensure_admin_like(request.user)
        item = News.objects.filter(id=news_id).first()
        if not item:
            raise NotFound("News not found.")
        serializer = NewsDetailSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(NewsDetailSerializer(item).data)

    def delete(self, request, news_id):
        _ensure_admin_like(request.user)
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
        ack_map = {
            ack.regulation_id: ack
            for ack in RegulationAcknowledgement.objects.filter(user=request.user, regulation__in=qs)
        }
        serializer = RegulationSerializer(qs, many=True, context={"request": request, "ack_map": ack_map})
        return Response(serializer.data)

    def post(self, request):
        _ensure_admin_like(request.user)
        serializer = RegulationAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(RegulationAdminSerializer(instance).data, status=201)


class FrontendRegulationsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, regulation_id):
        item = Regulation.objects.filter(id=regulation_id, is_active=True).first()
        if not item:
            raise NotFound("Regulation not found.")
        ack = RegulationAcknowledgement.objects.filter(user=request.user, regulation=item).first()
        serializer = RegulationSerializer(item, context={"request": request, "ack_map": {item.id: ack} if ack else {}})
        return Response(serializer.data)

    def patch(self, request, regulation_id):
        _ensure_admin_like(request.user)
        item = Regulation.objects.filter(id=regulation_id).first()
        if not item:
            raise NotFound("Regulation not found.")
        serializer = RegulationAdminSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, regulation_id):
        _ensure_admin_like(request.user)
        item = Regulation.objects.filter(id=regulation_id).first()
        if not item:
            raise NotFound("Regulation not found.")
        item.delete()
        return Response(status=204)


class FrontendInstructionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lang = request.query_params.get("lang")
        qs = Instruction.objects.filter(is_active=True)
        if lang:
            qs = qs.filter(language=lang)
        return Response(InstructionSerializer(qs.order_by("-updated_at"), many=True).data)

    def post(self, request):
        _ensure_admin_like(request.user)
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
        _ensure_admin_like(request.user)
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
        _ensure_admin_like(request.user)
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
        if not AccessPolicy.is_admin_like(request.user):
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
