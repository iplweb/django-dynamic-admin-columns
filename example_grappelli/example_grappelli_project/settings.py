"""Django settings for the django-dynamic-admin-columns + grappelli example.

This twin of ``example/`` differs in two ways:

* ``django.contrib.admin`` runs under the **django-grappelli** front-end
  (registered *before* ``admin`` in ``INSTALLED_APPS``).
* The UI is localised to Polish (``LANGUAGE_CODE = "pl"`` + a per-app
  ``locale/pl/`` catalog), to demo that the picker strings shipped by
  ``dynamic_admin_columns`` are translation-ready out of the box.
"""

import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-grappelli-not-secret-do-not-deploy-this"
DEBUG = True
ALLOWED_HOSTS = ["*"]

_DEV_HELPERS_INSTALLED = importlib.util.find_spec("django_dev_helpers") is not None

INSTALLED_APPS = [
    # ``grappelli`` MUST come before ``django.contrib.admin`` so its
    # templates override the stock admin ones.
    "grappelli",
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
if _DEV_HELPERS_INSTALLED:
    INSTALLED_APPS.append("django_dev_helpers")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "example_grappelli_project.urls"

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
                # Grappelli requires this to render its sidebar/dashboard.
                "django.template.context_processors.i18n",
            ],
        },
    },
]

WSGI_APPLICATION = "example_grappelli_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

# ----------------------------------------------------------------------
# Localisation
# ----------------------------------------------------------------------
LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

# Project-level locale catalog (overrides app-level for the same msgid).
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SILENCED_SYSTEM_CHECKS = ["admin.E117"]

# ----------------------------------------------------------------------
# django-grappelli configuration
# ----------------------------------------------------------------------
GRAPPELLI_ADMIN_TITLE = "Biblioteka — administracja"
GRAPPELLI_INDEX_DASHBOARD = None

# ----------------------------------------------------------------------
# django-dynamic-admin-columns configuration
# ----------------------------------------------------------------------
DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = [
    "library.admin",
]

DYNAMIC_ADMIN_COLUMNS_FORBIDDEN_COLUMN_NAMES = [
    r".*_cache$",
    r"^cached_.*",
]
