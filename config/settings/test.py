from .base import *  # noqa: F403,F401

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "test-secret-key")  # noqa: F405
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / ".test.sqlite3",  # noqa: F405
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
