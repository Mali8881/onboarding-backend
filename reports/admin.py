from django.contrib import admin
from django.contrib import admin, messages
from django.utils import timezone
from django import forms
from django.shortcuts import render, redirect
from .models import OnboardingReport, OnboardingReportLog

from .models import (
    OnboardingReport,
    OnboardingReportComment,
    OnboardingReportLog,
)


# ============================
# INLINE: комментарии
# ============================
class OnboardingReportCommentInline(admin.TabularInline):
    model = OnboardingReportComment
    extra = 0
    readonly_fields = ("author", "text", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ============================
# INLINE: история действий
# ============================
class OnboardingReportLogInline(admin.TabularInline):
    model = OnboardingReportLog
    extra = 0
    readonly_fields = (
        "actor",
        "action",
        "from_status",
        "to_status",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ============================
# REPORT ADMIN
# ============================
@admin.register(OnboardingReport)
class OnboardingReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "day",
        "status",
        "submitted_at",
        "created_at",
    )

    list_filter = (
        "status",
        "day",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "user",
        "day",
        "did",
        "will_do",
        "problems",
        "attachment",
        "status",
        "submitted_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Основное", {
            "fields": (
                "id",
                "user",
                "day",
                "status",
            )
        }),
        ("Отчёт стажёра", {
            "fields": (
                "did",
                "will_do",
                "problems",
                "attachment",
            )
        }),
        ("Даты", {
            "fields": (
                "submitted_at",
                "created_at",
                "updated_at",
            )
        }),
    )

    inlines = [
        OnboardingReportCommentInline,
        OnboardingReportLogInline,
    ]

    def has_add_permission(self, request):
        # ❌ нельзя создавать отчёты вручную
        return False

    def has_delete_permission(self, request, obj=None):
        # ❌ нельзя удалять отчёты
        return False

@admin.action(description="✅ Approve selected reports")
def approve_reports(modeladmin, request, queryset):
    updated = 0
    for report in queryset:
        if report.status == OnboardingReport.Status.SUBMITTED:
            old = report.status
            report.status = OnboardingReport.Status.APPROVED
            report.save()

            OnboardingReportLog.objects.create(
                report=report,
                actor=request.user,
                action=OnboardingReportLog.Action.APPROVED,
                from_status=old,
                to_status=report.status,
            )
            updated += 1

    messages.success(request, f"Approved {updated} reports")


@admin.action(description="❌ Reject selected reports")
def reject_reports(modeladmin, request, queryset):
    updated = 0
    for report in queryset:
        old = report.status
        report.status = OnboardingReport.Status.REJECTED
        report.save()

        OnboardingReportLog.objects.create(
            report=report,
            actor=request.user,
            action=OnboardingReportLog.Action.REJECTED,
            from_status=old,
            to_status=report.status,
        )
        updated += 1

    messages.warning(request, f"Rejected {updated} reports")

class RevisionCommentForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    comment = forms.CharField(
        label="Комментарий для стажёра",
        widget=forms.Textarea,
        required=True,
    )

def revision_reports(modeladmin, request, queryset):
    if "apply" in request.POST:
        form = RevisionCommentForm(request.POST)
        if form.is_valid():
            comment = form.cleaned_data["comment"]
            count = 0

            for report in queryset:
                old = report.status
                report.status = OnboardingReport.Status.REVISION
                report.save()

                OnboardingReportComment.objects.create(
                    report=report,
                    author=request.user,
                    text=comment,
                )

                OnboardingReportLog.objects.create(
                    report=report,
                    actor=request.user,
                    action=OnboardingReportLog.Action.REVISION,
                    from_status=old,
                    to_status=report.status,
                )

                count += 1

            messages.success(request, f"{count} reports sent to revision")
            return None

    else:
        form = RevisionCommentForm(
            initial={
                "_selected_action": queryset.values_list("id", flat=True)
            }
        )

    return render(
        request,
        "admin/reports/revision_comment.html",
        {
            "reports": queryset,
            "form": form,
            "title": "Отправить на доработку",
        },
    )

class OnboardingReportLogInline(admin.TabularInline):
    model = OnboardingReportLog
    extra = 0
    readonly_fields = (
        "action",
        "from_status",
        "to_status",
        "actor",
        "created_at",
    )
    can_delete = False

