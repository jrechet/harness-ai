"""Settings for every environment. What differs between them comes from the environment variables
listed in docs/exploitation.md; the defaults are the ones of a developer's machine."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("CURSUS_SECRET_KEY", "dev-only-key-not-used-anywhere-else")
DEBUG = os.environ.get("CURSUS_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("CURSUS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalog",
    "enrollments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cursus.urls"
WSGI_APPLICATION = "cursus.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# SQLite on a developer's machine and in CI, PostgreSQL in production.
if os.environ.get("CURSUS_DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["CURSUS_DB_HOST"],
            "NAME": os.environ.get("CURSUS_DB_NAME", "cursus"),
            "USER": os.environ.get("CURSUS_DB_USER", "cursus"),
            "PASSWORD": os.environ.get("CURSUS_DB_PASSWORD", ""),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGIN_URL = "admin:login"

# Outside production every e-mail is printed on the console.
EMAIL_BACKEND = os.environ.get("CURSUS_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("CURSUS_SMTP_HOST", "localhost")
EMAIL_HOST_USER = os.environ.get("CURSUS_SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("CURSUS_SMTP_PASSWORD", "")
EMAIL_USE_TLS = bool(os.environ.get("CURSUS_SMTP_HOST"))
DEFAULT_FROM_EMAIL = "Service formation <formation@cursus.example>"
