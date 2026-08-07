"""Coverage for the package's *own* admin classes.

``ModelAdminColumnAdmin`` mixes in ``adminsortable2``'s
``SortableAdminMixin``, which reaches deep into Django's admin
internals. That makes it the single most version-fragile surface in the
package, and until these tests existed nothing exercised it — the
``tests.testapp`` admin only covers ``DynamicColumnsMixin``.
"""

import json

import pytest
from django.urls import reverse


@pytest.fixture
def columns(client_admin, book_factory):
    """Populate ``ModelAdminColumn`` rows by hitting the Book changelist."""
    from dynamic_admin_columns.models import ModelAdminColumn

    book_factory()
    client_admin.get(reverse("admin:testapp_book_changelist"))
    return list(ModelAdminColumn.objects.order_by("ordering"))


@pytest.mark.django_db
def test_modeladmin_changelist_renders(client_admin, columns):
    response = client_admin.get(
        reverse("admin:dynamic_admin_columns_modeladmin_changelist")
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_sortable_column_changelist_renders(client_admin, columns):
    """Regression guard for the ``adminsortable2`` template plumbing.

    Releases up to 2.1.1 handed Django ``pathlib.Path`` template names,
    which stopped resolving on Django 6.0 — hence the ``>=2.1.2`` floor
    in ``pyproject.toml``.
    """
    response = client_admin.get(
        reverse("admin:dynamic_admin_columns_modeladmincolumn_changelist")
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_sortable_column_change_view_renders(client_admin, columns):
    response = client_admin.get(
        reverse(
            "admin:dynamic_admin_columns_modeladmincolumn_change",
            args=[columns[0].pk],
        )
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_adminsortable2_reorder_endpoint(client_admin, columns):
    """The drag-and-drop AJAX endpoint contributed by ``adminsortable2``."""
    first, last = columns[0], columns[-1]
    url = reverse("admin:dynamic_admin_columns_modeladmincolumn_changelist")
    response = client_admin.post(
        url + "adminsortable2_update/",
        data=json.dumps(
            {"updatedItems": [[first.pk, last.ordering], [last.pk, first.ordering]]}
        ),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content[:400]

    first.refresh_from_db()
    last.refresh_from_db()
    assert first.ordering == last.ordering + (len(columns) - 1)
