# onboarding-backend / V Plus HRM

Корпоративная HRM/onboarding платформа **"В Плюсе"**.

Проект состоит из backend (Django + DRF) и frontend (Vite/React в отдельной папке/репозитории). Платформа покрывает onboarding, сотрудников, оргструктуру, посещаемость, графики, регламенты, зарплаты, контент и обратную связь.

---

## 1. Что делает проект

Система автоматизирует внутренние HR-процессы компании:

- управление пользователями, ролями, отделами и должностями;
- onboarding стажеров и сотрудников;
- регламенты и контроль ознакомления;
- посещаемость (check-in/check-out, статусы дня);
- рабочие графики;
- payroll (расчет зарплаты по модели оплаты);
- новости, инструкции и внутренний контент;
- заявки/тикеты и обратная связь;
- страницы админ/суперадмин функционала и совместимость с legacy frontend API.

---

## 2. Технологический стек

### Backend
- Python 3.9+
- Django 4.2.x
- Django REST Framework
- PostgreSQL
- JWT (`rest_framework_simplejwt`)
- CORS (`django-cors-headers`)

### Frontend
- React + Vite
- Axios
- Локализация RU/EN/KG (частично/поэтапно)

---

## 3. Структура backend (ключевые приложения)

- `accounts/` — пользователи, роли, отделы, должности, оргструктура
- `onboarding_core/` — onboarding сценарии и отчеты
- `regulations/` — регламенты, подтверждение ознакомления, тестовые проверки
- `apps/attendance/` — посещаемость
- `apps/payroll/` — расчет зарплаты и ставки
- `content/` — новости и инструкции
- `feedback/` — тикеты/обратная связь
- `config/` — settings, urls, compat views/urls

Дополнительно:
- `config/frontend_compat_urls.py` и `config/frontend_compat_views.py` — слой совместимости со старым фронтом.

---

## 3.1 Подробная структура проекта и ответственность модулей

### Корень проекта (`onboarding-backend/`)
- `manage.py` — точка входа Django-команд.
- `requirements.txt` — зависимости backend.
- `.env` — окружение (секреты, БД, CORS, debug-параметры).
- `README.md` — документация проекта.

### Конфигурация (`config/`)
- `settings.py` — глобальные настройки Django/DRF.
- `urls.py` — главный роутинг API и страниц.
- `frontend_compat_urls.py` / `frontend_compat_views.py` — совместимость со старым frontend-контрактом.
- `spa_views.py` — отдача SPA/шаблонов в web-режиме.

### Домен пользователей и оргструктуры (`accounts/`)
- Пользователи, роли, отделы, должности.
- Иерархия компании и данные для страниц "Компания" / "Пользователи".
- Авторизация/профиль и доступы по ролям.

### Онбординг (`onboarding_core/`)
- Программы onboarding по дням/этапам.
- Задачи, отчеты, статусы прохождения.
- Логика для стажеров и кураторов.

### Регламенты (`regulations/`)
- Хранение регламентов (файлы/ссылки/описания).
- Подтверждение ознакомления.
- Проверка знаний/мини-тесты (в зависимости от текущей версии схемы).

### Посещаемость (`apps/attendance/`)
- Check-in/check-out.
- Дневные статусы (в офисе, не отмечен и т.д.).
- История посещаемости по сотрудникам/месяцу.

### Зарплаты (`apps/payroll/`)
- Модели оплаты (оклад/почасовая/поминутная).
- Ставки сотрудников.
- Пересчет и выдача итоговых payroll-данных.

### Контент (`content/`)
- Новости, инструкции и информационные блоки.
- Данные для дашбордов и внутренних страниц.

### Обратная связь (`feedback/`)
- Тикеты/обращения сотрудников.
- Статусы обработки и ответы.

### Отчеты (`reports/`)
- Агрегированные отчеты для управленческих страниц.

### Статические и медиа файлы
- `static/` — статические ресурсы backend.
- `media/` — загруженные файлы (регламенты, вложения и пр.).
- `templates/` — серверные HTML-шаблоны (если используются).

### Frontend-папки (локально)
- `vpluse_front_clean` / `vpluse_front-main` / `vpluse_front` — React/Vite frontend (в зависимости от вашей рабочей копии).
- Ответственность frontend:
  - рендер интерфейса;
  - отправка запросов в backend API;
  - локализация (RU/EN/KG);
  - валидация формы на уровне UI.

### Граница ответственности backend vs frontend
- Backend — источник истины для бизнес-логики, прав и расчетов.
- Frontend — отображение, UX, фильтрация/поиск на клиенте, отправка корректных payload.
- Любые итоговые значения (зарплата, статусы, доступы) должны финально определяться backend.

---

## 4. Роли и доступы (базовая модель)

Актуальные бизнес-роли зависят от состояния ветки, но обычно используются:

- `superadmin`
- `administrator`
- `admin`
- `projectmanager` / `teamlead`
- `employee`
- `intern`

Принцип доступа:
- `superadmin/administrator` — расширенное управление (пользователи, оргструктура, ставки и пр.);
- менеджерские роли — управление в рамках команды/подчиненных;
- `employee/intern` — пользовательские разделы (профиль, задачи, расписание и т.д.).

---

## 5. API (основные префиксы)

- `/api/v1/accounts/`
- `/api/v1/onboarding/`
- `/api/v1/regulations/` или `/api/v1/content/regulations/` (в зависимости от маршрута)
- `/api/v1/attendance/`
- `/api/v1/payroll/`
- `/api/v1/content/`
- `/api/v1/feedback/`

Legacy/compat маршруты могут дублироваться в `config/frontend_compat_urls.py`.

---

## 6. Быстрый запуск backend (локально)

1. Клонировать и перейти в каталог:

```bash
git clone <repo_url>
cd onboarding-backend
```

2. Создать и активировать виртуальное окружение:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Установить зависимости:

```bash
pip install -r requirements.txt
```

4. Настроить `.env` на базе `.env.example`.

5. Применить миграции:

```bash
python manage.py migrate
```

6. Запустить backend:

```bash
python manage.py runserver
```

Backend: `http://127.0.0.1:8000`

---

## 7. Запуск frontend (локально)

В вашем окружении использовались несколько фронтов. Выберите **один** рабочий каталог (пример):

- `C:\Users\User\vpluse_front_clean`
- или `C:\Users\User\vpluse_front-main`
- или `C:\Users\User\onboarding-backend\vpluse_front`

Далее:

```bash
npm install
npm run dev
```

Если порт `5173` занят, Vite автоматически поднимет `5174`.

### Важно для связи с backend
В `.env` фронта:

```env
VITE_API_URL=http://localhost:8000/api
```

Тогда frontend будет обращаться к backend по маршрутам вида:
`http://localhost:8000/api/v1/...`

---

## 8. Payroll: источник истины

Логика расчета зарплаты должна быть на backend:

- `fixed`: `accrual = fixed_salary`
- `hourly`: `accrual = worked_hours * hourly_rate`
- `minute`: `accrual = worked_minutes * minute_rate`

Итог:
`total_salary = accrual + bonus - penalty (+ adjustments)`

Frontend не должен пересчитывать зарплату вручную — только отправлять настройки и отображать готовые поля API.

Рабочий поток:
1. `POST /api/v1/payroll/admin/hourly-rates/`
2. `POST /api/v1/payroll/admin/recalculate/`
3. `GET /api/v1/payroll/admin/?year=...&month=...`
4. `GET /api/v1/payroll/admin/summary/?year=...&month=...`

---

## 9. Полезные команды backend

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py showmigrations
```

Планировщик дедлайнов:

```bash
python manage.py check_weekly_plan_deadlines
```

---

## 10. Частые проблемы и решения

### 10.1 Conflicting migrations / multiple leaf nodes

```bash
python manage.py makemigrations --merge
python manage.py migrate
```

### 10.2 401 Unauthorized / бесконечные refresh попытки
- проверить access/refresh токены в `localStorage`;
- выйти/войти заново;
- убедиться, что frontend смотрит на правильный backend URL.

### 10.3 429 Too Many Requests
Причина: частый polling + много вкладок.

Решение:
- уменьшить polling во frontend;
- закрыть лишние вкладки;
- в DEBUG временно ослабить throttle.

### 10.4 404 на compat endpoint
Проверить, что маршрут добавлен в `config/frontend_compat_urls.py`.

### 10.5 ImportError по моделям после merge
Пример: `RegulationKnowledgeCheck` / `RegulationQuiz`.

Решение:
- привести код и импорты к одной версии схемы;
- проверить `admin.py`, `serializers.py`, `views.py`;
- затем `makemigrations` + `migrate`.

### 10.6 Frontend не показывает последние изменения
Проверить:
- открыт ли правильный frontend-проект;
- правильный порт (`5173/5174`);
- `Ctrl+F5`;
- API URL в `.env`;
- что backend запущен именно из текущей ветки.

---

## 11. Рекомендованный git-flow

1. Перед работой:

```bash
git checkout <your-branch>
git pull --rebase
```

2. После изменений:

```bash
git add .
git commit -m "<clear message>"
git push origin <your-branch>
```

3. Перед merge чужой ветки:
- убедиться, что рабочее дерево чистое;
- при конфликтах фиксировать единую схему моделей/миграций.

---

## 12. Минимальный checklist перед демо

- backend поднят без traceback;
- все миграции применены;
- login работает (`/api/v1/accounts/login/` или compat `/api/auth/login/`);
- ключевые страницы открываются без 401/403/404/500;
- payroll/attendance/regulations получают валидные ответы;
- frontend запущен из правильной папки и смотрит в нужный API.

---

## 13. Статус документа

README поддерживается как рабочая инструкция для команды разработки.

Если меняются API-контракты или роли — обновляйте этот файл вместе с кодом.
