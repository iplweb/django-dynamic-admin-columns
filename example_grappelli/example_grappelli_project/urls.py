from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Grappelli's URLs must come *before* the admin's so the
    # autocomplete / related-lookup popups resolve correctly.
    path("grappelli/", include("grappelli.urls")),
    path("admin/", admin.site.urls),
]
