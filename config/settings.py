import os
from pathlib import Path
from corsheaders.defaults import default_headers

# ======================
# BASE
# ======================
BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# SECURITY
# ======================
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key-change-me",
)



DEBUG = os.environ.get("DEBUG", "true").lower() == "true"


ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "*"
).split(",")

# ======================
# APPLICATIONS
# ======================
INSTALLED_APPS = [
    # Admin UI
    "jazzmin",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "ckeditor",
    "ckeditor_uploader",

    # Local apps
    "accounts.apps.AccountsConfig",
    "regulations.apps.RegulationsConfig",
    "reports.apps.ReportsConfig",
    "content.apps.ContentConfig",
    "common.apps.CommonConfig",
    "work_schedule.apps.WorkScheduleConfig",
    "security.apps.SecurityConfig",
    "onboarding_core.apps.OnboardingCoreConfig",
    "apps.audit.apps.AuditConfig",
    "apps.attendance.apps.AttendanceConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.payroll.apps.PayrollConfig",
]

# ======================
# MIDDLEWARE
# ======================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ======================
# URLS / WSGI
# ======================
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ======================
# DATABASE
# ======================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "onboarding"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "baschytanka"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}


# ======================
# AUTH
# ======================
AUTH_USER_MODEL = "accounts.User"

# ======================
# TEMPLATES
# ======================
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

# ======================
# STATIC / MEDIA
# ======================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ======================
# I18N / L10N
# ======================
LANGUAGE_CODE = "ru"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
]

# ======================
# Admin UI
# ======================
JAZZMIN_SETTINGS = {
    "site_title": "Админ-панель HRM",
    "site_header": "HRM Администрирование",
    "site_brand": "HRM Система",
    "welcome_sign": "Добро пожаловать в админ-панель HRM",
}

# ======================
# CKEDITOR
# ======================
CKEDITOR_UPLOAD_PATH = "uploads/ckeditor/"
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Full",
        "height": 300,
        "width": "100%",
    }
}

# ======================
# DRF
# ======================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),

    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "20/minute",
        "login": "5/minute",
        "password_reset_request": "5/hour",
        "password_reset_confirm": "10/hour",
    },
}

SIMPLE_JWT = {
    "TOKEN_OBTAIN_SERIALIZER": "accounts.tokens.CustomTokenSerializer",
}

# Unified audit facade settings.
# No DB changes required; both backends use existing models.
AUDIT_PRIMARY_BACKEND = os.environ.get("AUDIT_PRIMARY_BACKEND", "accounts")
AUDIT_LEGACY_BACKEND = os.environ.get("AUDIT_LEGACY_BACKEND", "security")
AUDIT_WRITE_MODE = os.environ.get("AUDIT_WRITE_MODE", "primary_only")


SPECTACULAR_SETTINGS = {
    "TITLE": "Onboarding API",
    "DESCRIPTION": "API for onboarding platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ======================
# CORS / CSRF
# ======================
CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", ""
    ).split(",") if origin
]


CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
