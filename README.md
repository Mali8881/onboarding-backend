Как запустить проект локально

Клонировать:

git clone <URL_репозитория>
cd onboarding_platform


Виртуальное окружение:

python -m venv .venv
source .venv/bin/activate


Установить зависимости:

pip install -r requirements.txt


ENV:

cp .env.example .env


Далее в .env поставить свой пароль от Postgres.

Применить миграции:

python manage.py migrate


Запуск:

python manage.py runserver
