import os

from .base import *  # noqa: F403,F401

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in production")

ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "").split(",") if host.strip()]
if not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be set in production")
if any(host in {"your.domain.com", "server_ip", "localhost", "127.0.0.1"} for host in ALLOWED_HOSTS):
    raise RuntimeError("ALLOWED_HOSTS contains placeholder/local values. Set real production hostnames.")

if DATABASE_URL:  # noqa: F405
    if dj_database_url is None:  # noqa: F405
        raise RuntimeError("DATABASE_URL is set, but dj-database-url is not installed.")
else:
    for env_name in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"):
        if not os.environ.get(env_name, "").strip():
            raise RuntimeError(f"{env_name} must be set in production")

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if not CORS_ALLOWED_ORIGINS:
    raise RuntimeError("CORS_ALLOWED_ORIGINS must be set in production")
if any("localhost" in origin or "127.0.0.1" in origin for origin in CORS_ALLOWED_ORIGINS):
    raise RuntimeError("CORS_ALLOWED_ORIGINS contains localhost. Set real production origins.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError("CSRF_TRUSTED_ORIGINS must be set in production")
if any("your.domain.com" in origin for origin in CSRF_TRUSTED_ORIGINS):
    raise RuntimeError("CSRF_TRUSTED_ORIGINS contains placeholder values. Set real production origins.")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip()
if not FRONTEND_URL:
    raise RuntimeError("FRONTEND_URL must be set in production")
