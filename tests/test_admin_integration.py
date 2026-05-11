"""End-to-end integration tests that hit the actual admin via the test client."""

import pytest
from django.urls import reverse

from dynamic_columns.models import ModelAdmin


@pytest.mark.django_db
def test_changelist_renders_default_columns(client_admin, book_factory):
    book_factory(title="Some title", author="Mister Author")

    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    assert response.status_code == 200

    content = response.content.decode()
    assert "Some title" in content
    assert 'class="field-title"' in content
    assert 'class="field-author"' in content
    # ``notes`` is allowed but not enabled by default.
    assert 'class="field-notes"' not in content


@pytest.mark.django_db
def test_enabling_a_column_makes_it_appear_in_changelist(client_admin, book_factory):
    book_factory(title="Title", author="Author", notes="Visible notes")

    # First hit creates the in-database ModelAdmin representation.
    client_admin.get(reverse("admin:testapp_book_changelist"))

    ma = ModelAdmin.objects.get(class_name="tests.testapp.admin.BookAdmin")
    notes_col = ma.modeladmincolumn_set.get(col_name="notes")
    notes_col.enabled = True
    notes_col.save()

    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    assert 'class="field-notes"' in response.content.decode()


@pytest.mark.django_db
def test_disabling_default_column_hides_it(client_admin, book_factory):
    book_factory()

    client_admin.get(reverse("admin:testapp_book_changelist"))

    ma = ModelAdmin.objects.get(class_name="tests.testapp.admin.BookAdmin")
    author_col = ma.modeladmincolumn_set.get(col_name="author")
    author_col.enabled = False
    author_col.save()

    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    assert 'class="field-author"' not in response.content.decode()


@pytest.mark.django_db
def test_forbidden_columns_never_appear_in_database(client_admin, book_factory):
    book_factory()
    client_admin.get(reverse("admin:testapp_book_changelist"))

    ma = ModelAdmin.objects.get(class_name="tests.testapp.admin.BookAdmin")
    persisted = set(ma.modeladmincolumn_set.values_list("col_name", flat=True))
    # ``legacy_data`` is filtered by the BookAdmin's ``list_display_forbidden``.
    assert "legacy_data" not in persisted
