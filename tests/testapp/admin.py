from django.contrib import admin

from dynamic_admin_columns.mixins import DynamicColumnsMixin

from tests.testapp.models import Book


@admin.register(Book)
class BookAdmin(DynamicColumnsMixin, admin.ModelAdmin):
    list_display_always = ["title"]
    list_display_default = ["author", "isbn"]
    list_display_allowed = ["pages", "notes"]
    list_display_forbidden = [r"^legacy_.*"]
