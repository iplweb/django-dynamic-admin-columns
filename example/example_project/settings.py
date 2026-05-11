"""Minimal Django settings for the django-dynamic-admin-columns example project."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-not-secret-do-not-deploy-this"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "adminsortable2",
    "dynamic_admin_columns",
    "library",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "example_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "example_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SILENCED_SYSTEM_CHECKS = ["admin.E117"]

# ----------------------------------------------------------------------
# django-dynamic-admin-columns configuration
# ----------------------------------------------------------------------
# Only ModelAdmin classes whose dotted import path starts with one of the
# following prefixes can be loaded back from the database. This protects
# the project from arbitrary class loading via tampered DB rows.
DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = [
    "library.admin",
]

# Project-wide regex denylist applied to every dynamic admin.
DYNAMIC_ADMIN_COLUMNS_FORBIDDEN_COLUMN_NAMES = [
    r".*_cache$",
    r"^cached_.*",
]
