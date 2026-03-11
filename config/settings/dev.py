from .base import *  # noqa: F403,F401

DEBUG = env_bool("DEBUG", True)  # noqa: F405

# Local development defaults.
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)  # noqa: F405
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)  # noqa: F405
