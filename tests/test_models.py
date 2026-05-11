"""Tests for ``dynamic_admin_columns.models``."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError

from dynamic_admin_columns.exceptions import CodeAccessNotAllowed
from dynamic_admin_columns.models import ModelAdmin, ModelAdminColumn


@pytest.mark.django_db
def test_modeladmin_column_str_without_parent():
    column = ModelAdminColumn(col_name="bar")
    assert str(column) == 'Column "bar"'


@pytest.mark.django_db
def test_modeladmin_column_str_with_parent():
    ct = ContentType.objects.first()
    parent = ModelAdmin.objects.create(class_name="foo", model_ref=ct)
    column = ModelAdminColumn(col_name="bar", parent=parent)
    assert str(column) == 'Column "bar" of model "foo"'


@pytest.mark.django_db
def test_modeladmin_str():
    ct = ContentType.objects.first()
    ma = ModelAdmin.objects.create(class_name="some.path.Admin", model_ref=ct)
    assert str(ma) == "some.path.Admin"


@pytest.mark.django_db
def test_modeladmin_column_unique_constraint():
    ct = ContentType.objects.first()
    ma = ModelAdmin.objects.create(class_name="testapp.UniqueAdmin", model_ref=ct)
    ModelAdminColumn.objects.create(parent=ma, col_name="col_a", ordering=1)

    with pytest.raises(IntegrityError):
        ModelAdminColumn.objects.create(parent=ma, col_name="col_a", ordering=2)


@pytest.mark.django_db
def test_class_ref_raises_for_unauthorized_path(settings):
    settings.DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = ["only.this.module"]

    ct = ContentType.objects.first()
    ma = ModelAdmin.objects.create(class_name="unauthorized.path.Admin", model_ref=ct)

    with pytest.raises(CodeAccessNotAllowed, match="unauthorized.path.Admin"):
        _ = ma.class_ref


@pytest.mark.django_db
def test_db_repr_requires_allowed_import_path(settings):
    settings.DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = ["nowhere"]

    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    admin_instance = BookAdmin(Book, None)
    with pytest.raises(CodeAccessNotAllowed):
        ModelAdmin.objects.db_repr(admin_instance)


@pytest.mark.django_db
def test_enable_creates_columns_from_attributes():
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    admin_instance = BookAdmin(Book, None)
    ma = ModelAdmin.objects.enable(admin_instance)

    names = set(ma.modeladmincolumn_set.values_list("col_name", flat=True))
    # ``list_display_always`` is *not* persisted (those columns are not
    # user-configurable). The defaults and the allowed columns are.
    assert names == {"author", "isbn", "pages", "notes"}

    enabled = set(
        ma.modeladmincolumn_set.filter(enabled=True).values_list("col_name", flat=True)
    )
    assert enabled == {"author", "isbn"}


@pytest.mark.django_db
def test_enable_drops_columns_no_longer_declared():
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    admin_instance = BookAdmin(Book, None)
    ma = ModelAdmin.objects.enable(admin_instance)

    # Inject a stale column that is not in any declared source.
    ModelAdminColumn.objects.create(parent=ma, col_name="ghost", ordering=999)
    assert ma.modeladmincolumn_set.filter(col_name="ghost").exists()

    ModelAdmin.objects.enable(admin_instance)

    assert not ma.modeladmincolumn_set.filter(col_name="ghost").exists()


@pytest.mark.django_db
def test_get_list_display_returns_always_then_enabled_only():
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    admin_instance = BookAdmin(Book, None)
    ma = ModelAdmin.objects.enable(admin_instance)

    visible = list(ma.get_list_display(model_admin=admin_instance, request=None))
    assert visible[0] == "title"  # always
    assert "author" in visible and "isbn" in visible
    # ``pages`` and ``notes`` are declared in ``list_display_allowed`` and
    # remain disabled by default.
    assert "pages" not in visible
    assert "notes" not in visible


@pytest.mark.django_db
def test_all_keyword_expands_to_all_model_fields(settings):
    """When a ModelAdmin uses ``"__all__"`` it should pull all non-forbidden fields."""
    settings.DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS = ["tests.test_models"]

    from django.contrib.admin import ModelAdmin as DjangoModelAdmin

    from tests.testapp.models import Book

    class AllColumnsAdmin(DjangoModelAdmin):
        list_display_default = "__all__"

    AllColumnsAdmin.__module__ = "tests.test_models"
    instance = AllColumnsAdmin(Book, None)
    ma = ModelAdmin.objects.enable(instance)

    column_names = set(ma.modeladmincolumn_set.values_list("col_name", flat=True))
    # Every model field except the primary key shows up. ``legacy_data``
    # remains here because the global forbidden list in tests.settings
    # only blocks ``^_internal_.*`` — the ``__all__`` expansion does not
    # know about per-admin ``list_display_forbidden`` (the admin in this
    # synthetic class hasn't declared any).
    assert {"title", "author", "isbn", "pages", "notes"} <= column_names
