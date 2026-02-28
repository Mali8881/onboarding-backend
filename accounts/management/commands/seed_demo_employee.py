from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Department, Role, User
from apps.attendance.models import AttendanceMark, WorkCalendarDay
from apps.bpm.models import ProcessInstance, ProcessTemplate, StepInstance, StepTemplate
from apps.kb.models import KBArticle, KBCategory, KBViewLog
from apps.tasks.models import Board, Column, Task


class Command(BaseCommand):
    help = "Creates demo employee with tasks, KB, metrics, and BPM data for frontend testing."

    @transaction.atomic
    def handle(self, *args, **options):
        role_employee, _ = Role.objects.get_or_create(
            name=Role.Name.EMPLOYEE,
            defaults={"level": Role.Level.EMPLOYEE},
        )
        role_teamlead, _ = Role.objects.get_or_create(
            name=Role.Name.TEAMLEAD,
            defaults={"level": Role.Level.TEAMLEAD},
        )
        role_admin, _ = Role.objects.get_or_create(
            name=Role.Name.ADMIN,
            defaults={"level": Role.Level.ADMIN},
        )

        department, _ = Department.objects.get_or_create(name="Демо отдел")

        admin_user, _ = User.objects.update_or_create(
            username="demo_admin",
            defaults={
                "role": role_admin,
                "department": department,
                "is_active": True,
                "is_staff": True,
                "first_name": "Демо",
                "last_name": "Админ",
            },
        )
        admin_user.set_password("DemoAdmin123!")
        admin_user.save(update_fields=["password"])

        teamlead_user, _ = User.objects.update_or_create(
            username="demo_teamlead",
            defaults={
                "role": role_teamlead,
                "department": department,
                "is_active": True,
                "first_name": "Демо",
                "last_name": "Тимлид",
            },
        )
        teamlead_user.set_password("DemoLead123!")
        teamlead_user.save(update_fields=["password"])

        employee_user, _ = User.objects.update_or_create(
            username="demo_employee",
            defaults={
                "role": role_employee,
                "department": department,
                "manager": teamlead_user,
                "is_active": True,
                "first_name": "Тест",
                "last_name": "Сотрудник",
            },
        )
        employee_user.set_password("DemoEmp123!")
        employee_user.save(update_fields=["password"])

        board, _ = Board.objects.get_or_create(
            created_by=employee_user,
            is_personal=True,
            defaults={"name": f"{employee_user.username} board", "department": department},
        )
        if board.department_id != department.id:
            board.department = department
            board.save(update_fields=["department"])

        col_new, _ = Column.objects.get_or_create(board=board, order=1, defaults={"name": "new"})
        col_progress, _ = Column.objects.get_or_create(board=board, order=2, defaults={"name": "in progress"})
        col_done, _ = Column.objects.get_or_create(board=board, order=3, defaults={"name": "done"})

        today = timezone.localdate()
        Task.objects.update_or_create(
            board=board,
            assignee=employee_user,
            title="Подготовить отчет по адаптации",
            defaults={
                "column": col_progress,
                "description": "Собрать статус по задачам и рискам.",
                "reporter": teamlead_user,
                "due_date": today + timedelta(days=2),
                "priority": Task.Priority.HIGH,
            },
        )
        Task.objects.update_or_create(
            board=board,
            assignee=employee_user,
            title="Проверить регламенты отдела",
            defaults={
                "column": col_done,
                "description": "Прочитать и отметить изменения.",
                "reporter": admin_user,
                "due_date": today - timedelta(days=1),
                "priority": Task.Priority.MEDIUM,
            },
        )
        Task.objects.update_or_create(
            board=board,
            assignee=employee_user,
            title="Обновить карточку клиента",
            defaults={
                "column": col_new,
                "description": "Добавить новые поля и комментарии.",
                "reporter": teamlead_user,
                "due_date": today + timedelta(days=4),
                "priority": Task.Priority.LOW,
            },
        )

        kb_category, _ = KBCategory.objects.get_or_create(name="Демо База знаний")
        kb_article_public, _ = KBArticle.objects.update_or_create(
            title="Как оформлять ежедневный отчет",
            defaults={
                "content": "Короткая памятка по заполнению ежедневного отчета.",
                "category": kb_category,
                "visibility": KBArticle.Visibility.ALL,
                "created_by": admin_user,
                "is_published": True,
            },
        )
        KBArticle.objects.update_or_create(
            title="Правила работы в демо отделе",
            defaults={
                "content": "Внутренние правила команды для демонстрации.",
                "category": kb_category,
                "visibility": KBArticle.Visibility.DEPARTMENT,
                "department": department,
                "created_by": admin_user,
                "is_published": True,
            },
        )
        KBViewLog.objects.get_or_create(user=employee_user, article=kb_article_public)

        template, _ = ProcessTemplate.objects.get_or_create(
            name="Согласование отпуска (демо)",
            defaults={"description": "Демонстрационный процесс", "is_active": True},
        )
        step_1, _ = StepTemplate.objects.get_or_create(
            process_template=template,
            order=1,
            defaults={
                "name": "Подготовка заявки",
                "role_responsible": Role.Name.EMPLOYEE,
                "requires_comment": False,
            },
        )
        step_2, _ = StepTemplate.objects.get_or_create(
            process_template=template,
            order=2,
            defaults={
                "name": "Согласование руководителем",
                "role_responsible": Role.Name.TEAMLEAD,
                "requires_comment": True,
            },
        )

        process, _ = ProcessInstance.objects.get_or_create(
            template=template,
            created_by=employee_user,
            status=ProcessInstance.Status.IN_PROGRESS,
        )
        StepInstance.objects.update_or_create(
            process_instance=process,
            step_template=step_1,
            defaults={
                "status": StepInstance.Status.IN_PROGRESS,
                "responsible_user": employee_user,
                "started_at": timezone.now(),
                "finished_at": None,
                "comment": "",
            },
        )
        StepInstance.objects.update_or_create(
            process_instance=process,
            step_template=step_2,
            defaults={
                "status": StepInstance.Status.PENDING,
                "responsible_user": teamlead_user,
                "started_at": None,
                "finished_at": None,
                "comment": "",
            },
        )

        for delta in range(0, 5):
            day = today - timedelta(days=delta)
            WorkCalendarDay.objects.get_or_create(
                date=day,
                defaults={"is_working_day": day.weekday() < 5, "is_holiday": False},
            )
            if day.weekday() < 5:
                AttendanceMark.objects.update_or_create(
                    user=employee_user,
                    date=day,
                    defaults={
                        "status": AttendanceMark.Status.PRESENT,
                        "created_by": teamlead_user,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Demo data prepared."))
        self.stdout.write("Login: demo_employee / DemoEmp123!")
        self.stdout.write("Teamlead: demo_teamlead / DemoLead123!")
        self.stdout.write("Admin: demo_admin / DemoAdmin123!")
