import os
from pathlib import Path
from corsheaders.defaults import default_headers
import dj_database_url

# ======================
# BASE
# ======================
BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# SECURITY
# ======================
SECRET_KEY = "*0u4%0xl)j45n9d+hglu6$69cx-=%iy+w!dh15w-dzd3zita6f"



DEBUG = True


ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "*"
).split(",")

# ======================
# APPLICATIONS$env:SECRET_KEY="dev-secret"
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
        "NAME": "onboarding",
        "USER": "postgres",
        "PASSWORD": "malika2005",
        "HOST": "127.0.0.1",
        "PORT": "5433",
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

JAZZMIN_SETTINGS.update(
    {
        "custom_css": "common/admin_theme.css",
        "show_ui_builder": False,
        "hide_apps": ["authtoken"],
        "icons": {
            "accounts": "fas fa-users-cog",
            "accounts.user": "fas fa-user",
            "accounts.role": "fas fa-user-shield",
            "accounts.permission": "fas fa-key",
            "accounts.department": "fas fa-sitemap",
            "accounts.position": "fas fa-id-badge",
            "accounts.auditlog": "fas fa-clipboard-list",
            "onboarding_core": "fas fa-graduation-cap",
            "reports": "fas fa-file-alt",
            "regulations": "fas fa-book",
            "work_schedule": "fas fa-calendar-alt",
            "attendance": "fas fa-calendar-check",
            "tasks": "fas fa-tasks",
            "payroll": "fas fa-wallet",
            "common": "fas fa-bell",
            "content": "fas fa-newspaper",
            "security": "fas fa-shield-alt"
        },
        "order_with_respect_to": [
            "accounts",
            "onboarding_core",
            "reports",
            "regulations",
            "work_schedule",
            "attendance",
            "tasks",
            "payroll",
            "common",
            "content",
            "security"
        ]
    }
)

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": None,
    "navbar": "navbar-white navbar-light",
    "accent": "accent-primary",
    "navbar_small_text": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme_color": "primary",
    "button_classes": {
        "primary": "btn btn-primary",
        "secondary": "btn btn-outline-secondary",
        "info": "btn btn-info",
        "warning": "btn btn-warning",
        "danger": "btn btn-danger",
        "success": "btn btn-success"
    }
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
