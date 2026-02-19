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
    "accounts",
    "regulations",
    "reports",
    "content.apps.ContentConfig",
    "common",
    "work_schedule",
    "security",
    "onboarding_core",
]

# ======================
# MIDDLEWARE
# ======================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
    },
}


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