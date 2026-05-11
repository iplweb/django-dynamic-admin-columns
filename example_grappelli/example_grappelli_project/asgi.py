"""ASGI config for the django-grappelli example project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_grappelli_project.settings")

application = get_asgi_application()
