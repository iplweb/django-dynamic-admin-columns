"""Tests for ``dynamic_columns.mixins.DynamicColumnsMixin``."""

import pytest
from django.contrib.admin import ModelAdmin as DjangoModelAdmin

from dynamic_columns.mixins import DynamicColumnsMixin
from dynamic_columns.models import ModelAdmin


@pytest.mark.django_db
def test_mixin_get_list_display_through_book_admin():
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    admin_instance = BookAdmin(Book, None)
    columns = list(admin_instance.get_list_display(request=None))
    assert columns[0] == "title"
    assert "author" in columns and "isbn" in columns


@pytest.mark.django_db
def test_mixin_get_list_select_related_returns_list_unchanged():
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    class WithListSR(BookAdmin):
        list_select_related = ["author"]

    instance = WithListSR(Book, None)
    assert instance.get_list_select_related(request=None) == ["author"]


@pytest.mark.django_db
def test_mixin_get_list_select_related_filters_dict_by_visible_columns(settings):
    settings.DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS = [
        "tests.testapp.admin",
        "tests.test_mixins",
    ]

    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    class WithDictSR(BookAdmin):
        list_select_related = {
            "__always__": ["always_related"],
            "author": ["author_related"],
            "pages": ["pages_related"],
        }

    instance = WithDictSR(Book, None)
    sr = instance.get_list_select_related(request=None)

    # ``__always__`` is always present; ``author`` is enabled by default;
    # ``pages`` is only allowed (disabled by default) so it should not
    # contribute to select_related.
    assert "always_related" in sr
    assert "author_related" in sr
    assert "pages_related" not in sr


@pytest.mark.django_db
def test_mixin_works_when_list_display_unchanged_but_list_display_always_set(
    settings,
):
    """Regression: if ``list_display`` is the Django default and
    ``list_display_always`` is set, the default value should be dropped
    from persisted columns (otherwise we'd end up with ``__str__`` in
    the database)."""

    settings.DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS = ["tests.test_mixins"]

    from tests.testapp.models import Book

    class DefaultListDisplayAdmin(DynamicColumnsMixin, DjangoModelAdmin):
        list_display_always = ["title"]
        list_display_default = ["author"]

    DefaultListDisplayAdmin.__module__ = "tests.test_mixins"

    instance = DefaultListDisplayAdmin(Book, None)
    ma = ModelAdmin.objects.enable(instance)

    persisted = set(ma.modeladmincolumn_set.values_list("col_name", flat=True))
    assert "__str__" not in persisted
    assert "author" in persisted
