from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import render

from content.models import Employee, Feedback, Instruction, News
from onboarding_core.models import OnboardingDay, OnboardingMaterial
from regulations.models import Regulation
from reports.models import OnboardingReport

STATUS_META = {
    "DRAFT": {"label": "Черновик", "color": "#64748b"},
    "SENT": {"label": "Отправлен", "color": "#2563eb"},
    "ACCEPTED": {"label": "Принят", "color": "#16a34a"},
    "REVISION": {"label": "На доработку", "color": "#d97706"},
    "REJECTED": {"label": "Отклонен", "color": "#dc2626"},
}


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
