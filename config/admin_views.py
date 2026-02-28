from datetime import date as dt_date
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login as auth_login
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import LoginHistory, Role, User
from apps.audit import AuditEvents, log_event
from content.models import Employee, Feedback, Instruction, News
from onboarding_core.models import OnboardingDay, OnboardingMaterial
from regulations.models import Regulation
from reports.models import OnboardingReport
from work_schedule.models import UserWorkSchedule, WeeklyWorkPlan, WorkSchedule

STATUS_META = {
    "DRAFT": {"label": "Черновик", "color": "#64748b"},
    "SENT": {"label": "Отправлен", "color": "#2563eb"},
    "ACCEPTED": {"label": "Принят", "color": "#16a34a"},
    "REVISION": {"label": "На доработку", "color": "#d97706"},
    "REJECTED": {"label": "Отклонен", "color": "#dc2626"},
}


def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _landing_for(user):
    role_name = user.role.name if getattr(user, "role", None) else ""
    if role_name in {Role.Name.ADMIN, Role.Name.SUPER_ADMIN}:
        return "admin_panel"
    if role_name == Role.Name.INTERN:
        return "intern_portal"
    if role_name == Role.Name.TEAMLEAD:
        return "teamlead_portal"
    return "employee_portal"


def unified_admin_login(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect("/admin/login/portal/")
        return render(request, "admin/unified_login.html")

    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""

    if not username or not password:
        return render(
            request,
            "admin/unified_login.html",
            {"error": "Введите логин и пароль."},
            status=400,
        )

    existing_user = User.objects.filter(username=username).first()
    if not existing_user:
        existing_user = User.objects.filter(email__iexact=username).first()

    auth_username = existing_user.username if existing_user else username
    user = authenticate(request, username=auth_username, password=password)

    if existing_user and existing_user.lockout_until and existing_user.lockout_until > timezone.now():
        log_event(
            action=AuditEvents.LOGIN_BLOCKED_LOCKOUT,
            actor=existing_user,
            object_type="user",
            object_id=str(existing_user.id),
            level="warning",
            category="auth",
            ip_address=_get_ip(request),
        )
        return render(
            request,
            "admin/unified_login.html",
            {"error": "Слишком много неудачных попыток. Попробуйте позже."},
            status=403,
        )

    if not user:
        if existing_user:
            existing_user.failed_login_attempts += 1
            if existing_user.failed_login_attempts >= 5:
                existing_user.lockout_until = timezone.now() + timedelta(minutes=15)
            existing_user.save(update_fields=["failed_login_attempts", "lockout_until"])

        LoginHistory.objects.create(
            user=existing_user,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            success=False,
        )
        log_event(
            action=AuditEvents.LOGIN_FAILED,
            actor=existing_user,
            object_type="user",
            object_id=str(existing_user.id) if existing_user else "",
            level="warning",
            category="auth",
            ip_address=_get_ip(request),
            metadata={"username": username},
        )
        return render(
            request,
            "admin/unified_login.html",
            {"error": "Неверный логин или пароль."},
            status=400,
        )

    if user.is_blocked:
        log_event(
            action=AuditEvents.LOGIN_BLOCKED_MANUAL,
            actor=user,
            object_type="user",
            object_id=str(user.id),
            level="warning",
            category="auth",
            ip_address=_get_ip(request),
        )
        return render(
            request,
            "admin/unified_login.html",
            {"error": "Пользователь заблокирован."},
            status=403,
        )

    user.failed_login_attempts = 0
    user.lockout_until = None
    user.save(update_fields=["failed_login_attempts", "lockout_until"])
    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    LoginHistory.objects.create(
        user=user,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        success=True,
    )
    log_event(
        action=AuditEvents.LOGIN_SUCCESS,
        actor=user,
        object_type="user",
        object_id=str(user.id),
        level="info",
        category="auth",
        ip_address=_get_ip(request),
    )

    refresh = RefreshToken.for_user(user)
    return render(
        request,
        "admin/unified_employee_redirect.html",
        {
            "access_token": str(refresh.access_token),
            "landing": _landing_for(user),
            "role": user.role.name if user.role else "",
            "target_url": "/admin/login/portal/",
        },
    )


@staff_member_required
def onboarding_dashboard(request):
    reports = list(
        OnboardingReport.objects.select_related("user", "day").order_by("-created_at")[:20]
    )
    for report in reports:
        report.status_meta = STATUS_META.get(report.status, {"label": report.status, "color": "#64748b"})

    days = (
        OnboardingDay.objects.annotate(materials_count=Count("materials"))
        .order_by("position", "day_number")[:30]
    )

    materials = (
        OnboardingMaterial.objects.select_related("day")
        .order_by("day__position", "position")[:30]
    )

    context = {
        "title": "Онбординг / Отчёты",
        "reports": reports,
        "days": days,
        "materials": materials,
        "stats": {
            "total": OnboardingReport.objects.count(),
            "sent": OnboardingReport.objects.filter(status="SENT").count(),
            "draft": OnboardingReport.objects.filter(status="DRAFT").count(),
            "accepted": OnboardingReport.objects.filter(status="ACCEPTED").count(),
        },
    }
    return render(request, "admin/onboarding_dashboard.html", context)


@staff_member_required
def content_dashboard(request):
    context = {
        "title": "Управление контентом",
        "cards": [
            {
                "emoji": "📰",
                "title": "Новости компании",
                "desc": "Публикация новостей и объявлений для сотрудников.",
                "meta": f"{News.objects.count()} опубликовано",
                "url": "/admin/content/news/",
                "action": "Перейти",
            },
            {
                "emoji": "📘",
                "title": "Инструкция по платформе",
                "desc": "Текст, ссылки и файлы с инструкциями.",
                "meta": f"{Instruction.objects.filter(is_active=True).count()} активна",
                "url": "/admin/content/instruction/",
                "action": "Редактировать",
            },
            {
                "emoji": "💬",
                "title": "Обратная связь",
                "desc": "Жалобы, предложения и отзывы сотрудников.",
                "meta": f"{Feedback.objects.filter(status='new').count()} новых",
                "url": "/admin/content/feedback/",
                "action": "Перейти",
            },
            {
                "emoji": "👥",
                "title": "Сотрудники и команда",
                "desc": "Профили сотрудников и контактная информация.",
                "meta": f"{Employee.objects.count()} сотрудников",
                "url": "/admin/accounts/user/",
                "action": "Управление",
            },
            {
                "emoji": "📑",
                "title": "Регламенты",
                "desc": "База документов и внутренних правил.",
                "meta": f"{Regulation.objects.count()} документов",
                "url": "/admin/regulations/regulation/",
                "action": "Перейти",
            },
        ],
    }
    return render(request, "admin/content_dashboard.html", context)


@staff_member_required
def attendance_checkin_page(request):
    context = {
        "title": "Отметка в офисе",
        "checkin_api_url": "/api/v1/attendance/check-in/",
    }
    return render(request, "admin/attendance_checkin.html", context)


@staff_member_required
def work_schedule_board_page(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    fallback_schedule = (
        WorkSchedule.objects.filter(is_active=True, is_default=True).first()
        or WorkSchedule.objects.filter(is_active=True).order_by("id").first()
    )
    employees = User.objects.filter(role__name=Role.Name.EMPLOYEE).select_related("role")

    existing_assignments = {
        item.user_id: item
        for item in UserWorkSchedule.objects.select_related("user", "schedule").filter(user__in=employees)
    }
    if fallback_schedule:
        missing = [u for u in employees if u.id not in existing_assignments]
        if missing:
            UserWorkSchedule.objects.bulk_create(
                [
                    UserWorkSchedule(user=user, schedule=fallback_schedule, approved=False)
                    for user in missing
                ],
                ignore_conflicts=True,
            )
            existing_assignments = {
                item.user_id: item
                for item in UserWorkSchedule.objects.select_related("user", "schedule").filter(user__in=employees)
            }

    day_buckets = [[] for _ in range(7)]
    for user in employees:
        assignment = existing_assignments.get(user.id)
        if not assignment:
            continue

        weekly_plan = (
            WeeklyWorkPlan.objects.filter(user=user, week_start=week_start)
            .order_by("-updated_at")
            .first()
        )
        day_map = {}
        if weekly_plan:
            for item in (weekly_plan.days or []):
                if isinstance(item, dict) and item.get("date"):
                    day_map[str(item.get("date"))] = item

        user_label = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username
        details_url = reverse("admin:work_schedule_userworkschedule_change", args=[assignment.id])

        for idx, day in enumerate(week_dates):
            item = day_map.get(day.isoformat())
            if item:
                mode = item.get("mode")
                if mode == "day_off":
                    continue
                start_time = item.get("start_time") or "-"
                end_time = item.get("end_time") or "-"
                mode_label = "online" if mode == "online" else "office"
            else:
                if day.weekday() not in (assignment.schedule.work_days or []):
                    continue
                start_time = assignment.schedule.start_time.strftime("%H:%M")
                end_time = assignment.schedule.end_time.strftime("%H:%M")
                mode_label = "office"

            day_buckets[idx].append(
                {
                    "user_display": user_label,
                    "time_range": f"{start_time} - {end_time}",
                    "mode": mode_label,
                    "details_url": details_url,
                }
            )

    context = {
        "title": "Графики работы (неделя)",
        "week_start": week_start,
        "day_headers": list(
            zip(
                ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"),
                week_dates,
            )
        ),
        "day_buckets": day_buckets,
    }
    return render(request, "admin/work_schedule_board.html", context)


