"""Tests for ``dynamic_admin_columns.mixins.DynamicColumnsMixin``."""

import pytest
from django.contrib.admin import ModelAdmin as DjangoModelAdmin

from dynamic_admin_columns.mixins import DynamicColumnsMixin
from dynamic_admin_columns.models import ModelAdmin


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
    settings.DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = [
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

    settings.DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = ["tests.test_mixins"]

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


def test_change_list_template_default_resolves_to_skin_template():
    """Without assignment the property returns the skin-derived template."""

    class A(DynamicColumnsMixin):
        pass

    instance = A()
    # Stock admin (no grappelli in tests/settings.py INSTALLED_APPS).
    assert instance.change_list_template == "dynamic_admin_columns/change_list.html"


def test_change_list_template_is_settable_per_instance():
    """The property accepts assignment — needed for composition with
    libraries like ``django-import-export`` whose ``ImportExportMixinBase``
    deliberately does ``self.change_list_template = ...`` in ``__init__``
    to wrap whatever template the host ``ModelAdmin`` already chose.

    Without a setter this assignment silently fails (the upstream code
    swallows ``AttributeError``), and the host's Export object-tool never
    renders because the active template stays as the picker's own
    ``change_list.html`` which doesn't include ``import_export``'s tools.
    """

    class A(DynamicColumnsMixin):
        pass

    instance = A()
    instance.change_list_template = "custom/template.html"
    assert instance.change_list_template == "custom/template.html"

    # Per-instance only — siblings are unaffected.
    other = A()
    assert other.change_list_template == "dynamic_admin_columns/change_list.html"

    # Deleting the override restores the default.
    del instance.change_list_template
    assert instance.change_list_template == "dynamic_admin_columns/change_list.html"


def test_change_list_template_composes_with_import_export_pattern():
    """End-to-end of the composition idiom: a downstream ``ModelAdmin``
    that mixes both ``DynamicColumnsMixin`` and a class that — like
    ``import_export.admin.ImportExportMixinBase`` — captures the existing
    ``change_list_template`` as a fallback and reassigns the active one
    must end up with both values exposed (the override active, the
    picker template available as the chained base)."""

    class ImportExportLike:
        """Minimal stand-in for django-import-export's init hook."""

        def __init__(self):
            base = self.change_list_template
            self.ie_base_change_list_template = base
            try:
                self.change_list_template = "import_export/change_list.html"
            except AttributeError as err:  # pragma: no cover - regression guard
                raise AssertionError(
                    "change_list_template assignment failed — the property "
                    "must accept writes for downstream composition to work."
                ) from err

    class Combo(ImportExportLike, DynamicColumnsMixin):
        pass

    instance = Combo()
    assert instance.change_list_template == "import_export/change_list.html"
    assert (
        instance.ie_base_change_list_template
        == "dynamic_admin_columns/change_list.html"
    )
