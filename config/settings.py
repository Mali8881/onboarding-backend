SECRET_KEY = "django-insecure-dev-secret-key"

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
AUTH_USER_MODEL = "accounts.User"

CSRF_TRUSTED_ORIGINS = [
    'https://natalie-theroid-tony.ngrok-free.dev',

]

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "onboarding",
        "USER": "postgres",
        "PASSWORD": "malika2005",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",   # ← ВАЖНО: первым
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

]

INSTALLED_APPS = [
    'jazzmin',
    'ckeditor',  # Сам редактор
    'ckeditor_uploader',  # Загрузчик файлов (если захотите вставлять картинки прямо в текст)

    'accounts',
    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",


    "rest_framework.authtoken",
    # Third-party
    "rest_framework",
    "regulations",
    'reports',
    'content.apps.ContentConfig',
    "common",
    'work_schedule',
    'security',
    'onboarding_core',
    "drf_spectacular",





]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DEBUG = True
ALLOWED_HOSTS = ['*']


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = 'accounts.User'

# Путь для загрузки картинок через редактор
CKEDITOR_UPLOAD_PATH = "uploads/ckeditor/"

# Настройка панелей инструментов (чтобы было как в Word)
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Full', # Полная панель инструментов
        'height': 300,
        'width': '100%',
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Onboarding API",
    "DESCRIPTION": "API for onboarding platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
