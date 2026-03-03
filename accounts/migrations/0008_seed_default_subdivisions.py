from django.db import migrations


def _get_or_create_department(Department, canonical_name, aliases):
    qs = Department.objects.all()
    for alias in aliases:
        match = qs.filter(name__icontains=alias).first()
        if match:
            return match
    department, _ = Department.objects.get_or_create(
        name=canonical_name,
        defaults={"is_active": True},
    )
    return department


def forwards(apps, schema_editor):
    Department = apps.get_model("accounts", "Department")
    DepartmentSubdivision = apps.get_model("accounts", "DepartmentSubdivision")

    dept_it = _get_or_create_department(
        Department,
        "IT департамент",
        aliases=["it", "разработ", "dev", "тех"],
    )
    dept_sales = _get_or_create_department(
        Department,
        "Отдел продаж",
        aliases=["продаж"],
    )
    dept_marketing = _get_or_create_department(
        Department,
        "Отдел маркетинга",
        aliases=["маркет"],
    )
    dept_hr = _get_or_create_department(
        Department,
        "HR отдел",
        aliases=["hr", "кадр", "персонал"],
    )
    dept_finance = _get_or_create_department(
        Department,
        "Финансовый отдел",
        aliases=["финанс", "бух"],
    )
    dept_support = _get_or_create_department(
        Department,
        "Отдел поддержки",
        aliases=["поддерж", "support"],
    )

    defaults_map = {
        dept_it.id: [
            {
                "name": "Бэкенд разработчик",
                "title": "День 2: Бэкенд разработка",
                "description": "Реализовать парсер по ТЗ и опубликовать результат в GitHub.",
            },
            {
                "name": "Фронтенд разработчик",
                "title": "День 2: Фронтенд разработка",
                "description": "Сверстать и подключить интерфейс по ТЗ, загрузить результат в GitHub.",
            },
            {
                "name": "SQL разработчик",
                "title": "День 2: SQL задача",
                "description": "Подготовить SQL-решение по ТЗ и оформить результат в GitHub.",
            },
            {
                "name": "QA инженер",
                "title": "День 2: QA задача",
                "description": "Составить тест-кейсы и провести проверку сценариев по ТЗ.",
            },
            {
                "name": "DevOps инженер",
                "title": "День 2: DevOps задача",
                "description": "Подготовить инфраструктурный сценарий/CI по ТЗ.",
            },
        ],
        dept_sales.id: [
            {
                "name": "Менеджер по продажам",
                "title": "День 2: Продажи",
                "description": "Подготовить скрипт продаж и отработать кейсы по ТЗ.",
            },
            {
                "name": "Хантер (холодные продажи)",
                "title": "День 2: Холодные продажи",
                "description": "Сформировать базу лидов и сценарии первичного контакта.",
            },
            {
                "name": "Аккаунт-менеджер",
                "title": "День 2: Работа с клиентами",
                "description": "Подготовить план сопровождения клиента и коммуникаций.",
            },
        ],
        dept_marketing.id: [
            {
                "name": "SMM специалист",
                "title": "День 2: SMM задача",
                "description": "Подготовить контент-план и публикации по ТЗ.",
            },
            {
                "name": "Контент-менеджер",
                "title": "День 2: Контент задача",
                "description": "Создать материалы и структуру контента по ТЗ.",
            },
            {
                "name": "Performance маркетолог",
                "title": "День 2: Performance задача",
                "description": "Подготовить рекламную гипотезу и медиаплан по ТЗ.",
            },
        ],
        dept_hr.id: [
            {
                "name": "HR менеджер",
                "title": "День 2: HR задача",
                "description": "Подготовить этапы подбора и адаптации кандидата по ТЗ.",
            },
            {
                "name": "Рекрутер",
                "title": "День 2: Рекрутинг",
                "description": "Сформировать воронку подбора и шаблоны коммуникаций.",
            },
            {
                "name": "HR аналитик",
                "title": "День 2: HR аналитика",
                "description": "Подготовить метрики найма и отчет по воронке.",
            },
        ],
        dept_finance.id: [
            {
                "name": "Бухгалтер",
                "title": "День 2: Бухгалтерская задача",
                "description": "Сформировать шаблон отчетности и проверить первичные данные.",
            },
            {
                "name": "Финансовый аналитик",
                "title": "День 2: Финансовая аналитика",
                "description": "Подготовить базовый финансовый отчет по ТЗ.",
            },
        ],
        dept_support.id: [
            {
                "name": "Специалист поддержки",
                "title": "День 2: Поддержка клиентов",
                "description": "Разобрать обращения и подготовить ответы по регламенту.",
            },
            {
                "name": "Оператор call-центра",
                "title": "День 2: Call-центр",
                "description": "Отработать скрипты и сценарии обработки звонков.",
            },
        ],
    }

    for department_id, subdivision_items in defaults_map.items():
        for item in subdivision_items:
            subdivision, created = DepartmentSubdivision.objects.get_or_create(
                department_id=department_id,
                name=item["name"],
                defaults={
                    "day_two_task_title": item["title"],
                    "day_two_task_description": item["description"],
                    "is_active": True,
                },
            )
            if not created:
                changed = []
                if not subdivision.day_two_task_title:
                    subdivision.day_two_task_title = item["title"]
                    changed.append("day_two_task_title")
                if not subdivision.day_two_task_description:
                    subdivision.day_two_task_description = item["description"]
                    changed.append("day_two_task_description")
                if not subdivision.is_active:
                    subdivision.is_active = True
                    changed.append("is_active")
                if changed:
                    subdivision.save(update_fields=changed)


def backwards(apps, schema_editor):
    DepartmentSubdivision = apps.get_model("accounts", "DepartmentSubdivision")
    names = [
        "Бэкенд разработчик",
        "Фронтенд разработчик",
        "SQL разработчик",
        "QA инженер",
        "DevOps инженер",
        "Менеджер по продажам",
        "Хантер (холодные продажи)",
        "Аккаунт-менеджер",
        "SMM специалист",
        "Контент-менеджер",
        "Performance маркетолог",
        "HR менеджер",
        "Рекрутер",
        "HR аналитик",
        "Бухгалтер",
        "Финансовый аналитик",
        "Специалист поддержки",
        "Оператор call-центра",
    ]
    DepartmentSubdivision.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_departmentsubdivision_user_subdivision"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
