from django.contrib import admin

from dynamic_columns.mixins import DynamicColumnsMixin

from library.models import Book


@admin.register(Book)
class BookAdmin(DynamicColumnsMixin, admin.ModelAdmin):
    # Always visible. Cannot be toggled or moved by the user.
    list_display_always = ["title"]

    # Visible by default. The user can hide them.
    list_display_default = ["author", "isbn"]

    # Hidden by default. The user can enable them.
    list_display_allowed = ["pages", "notes", "published_on", "language"]
