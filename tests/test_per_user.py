"""Per-user column layout — manager, mixin, view endpoints."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dynamic_admin_columns.models import ModelAdmin


@pytest.fixture
def second_admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="other",
        email="other@example.com",
        password="otherpass",
    )


@pytest.fixture
def client_other(client, second_admin_user):
    client.force_login(second_admin_user)
    return client


# ---------------------------------------------------------------------------
# Manager: clone_for_user / db_repr_for_user
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_clone_for_user_creates_personal_copy_from_global(admin_user):
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    instance = BookAdmin(Book, None)

    user_row = ModelAdmin.objects.clone_for_user(instance, admin_user)

    assert user_row.user_id == admin_user.pk
    assert user_row.class_name == "tests.testapp.admin.BookAdmin"

    user_cols = set(user_row.modeladmincolumn_set.values_list("col_name", flat=True))
    global_row = ModelAdmin.objects.get(
        user__isnull=True, class_name=user_row.class_name
    )
    global_cols = set(
        global_row.modeladmincolumn_set.values_list("col_name", flat=True)
    )

    assert user_cols == global_cols


@pytest.mark.django_db
def test_clone_for_user_is_idempotent(admin_user):
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    instance = BookAdmin(Book, None)
    first = ModelAdmin.objects.clone_for_user(instance, admin_user)
    second = ModelAdmin.objects.clone_for_user(instance, admin_user)

    assert first.pk == second.pk
    assert (
        ModelAdmin.objects.filter(user=admin_user, class_name=first.class_name).count()
        == 1
    )


@pytest.mark.django_db
def test_db_repr_for_user_returns_personal_when_present(admin_user):
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    instance = BookAdmin(Book, None)
    personal = ModelAdmin.objects.clone_for_user(instance, admin_user)

    resolved = ModelAdmin.objects.db_repr_for_user(instance, admin_user)
    assert resolved.pk == personal.pk
    assert resolved.user_id == admin_user.pk


@pytest.mark.django_db
def test_db_repr_for_user_falls_back_to_global(admin_user):
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    instance = BookAdmin(Book, None)

    # No clone yet — admin_user should land on the global row.
    resolved = ModelAdmin.objects.db_repr_for_user(instance, admin_user)
    assert resolved.user_id is None


@pytest.mark.django_db
def test_two_users_have_independent_personal_layouts(admin_user, second_admin_user):
    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    instance = BookAdmin(Book, None)
    row_a = ModelAdmin.objects.clone_for_user(instance, admin_user)
    row_b = ModelAdmin.objects.clone_for_user(instance, second_admin_user)

    assert row_a.pk != row_b.pk

    row_a.modeladmincolumn_set.filter(col_name="author").update(enabled=False)

    # row_b is untouched
    assert row_b.modeladmincolumn_set.get(col_name="author").enabled is True


@pytest.mark.django_db
def test_clone_for_user_requires_authenticated_user():
    from django.contrib.auth.models import AnonymousUser

    from tests.testapp.admin import BookAdmin
    from tests.testapp.models import Book

    instance = BookAdmin(Book, None)

    with pytest.raises(ValueError):
        ModelAdmin.objects.clone_for_user(instance, AnonymousUser())

    with pytest.raises(ValueError):
        ModelAdmin.objects.clone_for_user(instance, None)


# ---------------------------------------------------------------------------
# Save endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_endpoint_creates_personal_layout(client_admin):
    # Prime the global row.
    client_admin.get(reverse("admin:testapp_book_changelist"))

    url = reverse("admin:testapp_book_dyncol_save")
    response = client_admin.post(
        url,
        data=json.dumps(
            {
                "columns": [
                    {"col_name": "isbn", "enabled": True, "ordering": 1},
                    {"col_name": "author", "enabled": True, "ordering": 2},
                    {"col_name": "pages", "enabled": True, "ordering": 3},
                    {"col_name": "notes", "enabled": False, "ordering": 4},
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True

    User = get_user_model()
    user = User.objects.get(username="admin")
    row = ModelAdmin.objects.get(user=user, class_name="tests.testapp.admin.BookAdmin")

    order = list(
        row.modeladmincolumn_set.order_by("ordering").values_list("col_name", "enabled")
    )
    assert order == [
        ("isbn", True),
        ("author", True),
        ("pages", True),
        ("notes", False),
    ]


@pytest.mark.django_db
def test_save_endpoint_changelist_reflects_personal_layout(client_admin, book_factory):
    book_factory(title="Some title", author="Authoring Person")

    client_admin.get(reverse("admin:testapp_book_changelist"))

    save_url = reverse("admin:testapp_book_dyncol_save")
    client_admin.post(
        save_url,
        data=json.dumps(
            {
                "columns": [
                    {"col_name": "notes", "enabled": True, "ordering": 1},
                    {"col_name": "author", "enabled": False, "ordering": 2},
                    {"col_name": "isbn", "enabled": False, "ordering": 3},
                    {"col_name": "pages", "enabled": False, "ordering": 4},
                ]
            }
        ),
        content_type="application/json",
    )

    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    # ``title`` is in list_display_always — always rendered.
    assert 'class="field-title"' in content
    # ``notes`` was the only user-toggled column.
    assert 'class="field-notes"' in content
    # ``author`` was the default but the user just disabled it.
    assert 'class="field-author"' not in content


@pytest.mark.django_db
def test_save_endpoint_ignores_unknown_columns(client_admin):
    client_admin.get(reverse("admin:testapp_book_changelist"))

    url = reverse("admin:testapp_book_dyncol_save")
    response = client_admin.post(
        url,
        data=json.dumps(
            {
                "columns": [
                    {"col_name": "ghost", "enabled": True, "ordering": 1},
                    {"col_name": "isbn", "enabled": False, "ordering": 2},
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200

    User = get_user_model()
    user = User.objects.get(username="admin")
    row = ModelAdmin.objects.get(user=user)
    assert not row.modeladmincolumn_set.filter(col_name="ghost").exists()
    assert row.modeladmincolumn_set.get(col_name="isbn").enabled is False


@pytest.mark.django_db
def test_save_endpoint_rejects_non_staff(client, book_factory):
    User = get_user_model()
    plain_user = User.objects.create_user(username="bob", password="bobpass")
    client.force_login(plain_user)
    book_factory()

    url = reverse("admin:testapp_book_dyncol_save")
    response = client.post(
        url,
        data=json.dumps({"columns": []}),
        content_type="application/json",
    )
    # admin_site.admin_view redirects unauthenticated/non-staff to login.
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_save_endpoint_rejects_invalid_json(client_admin):
    client_admin.get(reverse("admin:testapp_book_changelist"))
    url = reverse("admin:testapp_book_dyncol_save")
    response = client_admin.post(url, data="not-json", content_type="application/json")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Reset endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reset_endpoint_removes_personal_layout(client_admin):
    # Build a personal layout first.
    client_admin.get(reverse("admin:testapp_book_changelist"))
    save_url = reverse("admin:testapp_book_dyncol_save")
    client_admin.post(
        save_url,
        data=json.dumps(
            {"columns": [{"col_name": "isbn", "enabled": False, "ordering": 1}]}
        ),
        content_type="application/json",
    )

    User = get_user_model()
    user = User.objects.get(username="admin")
    assert ModelAdmin.objects.filter(user=user).exists()

    reset_url = reverse("admin:testapp_book_dyncol_reset")
    response = client_admin.post(reset_url)
    assert response.status_code == 200
    assert not ModelAdmin.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_reset_endpoint_404_without_personal_layout(client_admin):
    client_admin.get(reverse("admin:testapp_book_changelist"))
    reset_url = reverse("admin:testapp_book_dyncol_reset")
    response = client_admin.post(reset_url)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Changelist context
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_changelist_includes_columns_button(client_admin):
    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    assert 'id="dyncol-button"' in content
    assert "Configure columns" in content
    # Columns are now serialised as JSON for the JS to render; the
    # pinned ``list_display_always`` rows ("title") must not appear in
    # the personal payload.
    import json as _json
    import re as _re

    m = _re.search(
        r'id="dyncol-personal-data"[^>]*>(.+?)</script>', content, _re.DOTALL
    )
    assert m, "dyncol-personal-data script must be present"
    payload = _json.loads(m.group(1))
    col_names = {row["col_name"] for row in payload}
    assert "title" not in col_names


@pytest.mark.django_db
def test_changelist_marks_personal_layout(client_admin):
    client_admin.get(reverse("admin:testapp_book_changelist"))
    save_url = reverse("admin:testapp_book_dyncol_save")
    client_admin.post(
        save_url,
        data=json.dumps({"columns": []}),
        content_type="application/json",
    )

    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    assert "dyncol-personal" in content
    assert 'id="dyncol-reset"' in content


@pytest.mark.django_db
def test_changelist_without_personal_layout_hides_reset_button(client_admin):
    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    # The reset button is always present in the DOM (so JS can toggle it
    # based on the scope radio); it ships hidden whenever the user has
    # no personal layout to discard.
    assert 'id="dyncol-reset"' in content
    assert 'id="dyncol-reset" hidden' in content


# ---------------------------------------------------------------------------
# Global scope (superuser)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_changelist_shows_scope_radio_to_superuser(client_admin):
    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    assert 'name="dyncol-scope"' in content
    assert 'value="personal"' in content
    assert 'value="global"' in content


@pytest.mark.django_db
def test_changelist_hides_scope_radio_from_non_superuser(client, book_factory):
    from django.contrib.auth.models import Permission

    User = get_user_model()
    plain_staff = User.objects.create_user(
        username="staffer", password="staffpass", is_staff=True
    )
    plain_staff.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="testapp")
    )
    client.force_login(plain_staff)
    response = client.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    assert 'id="dyncol-button"' in content
    # Non-superuser staff get the picker but no scope switch.
    assert 'name="dyncol-scope"' not in content


@pytest.mark.django_db
def test_save_endpoint_global_scope_updates_user_null_row(client_admin):
    client_admin.get(reverse("admin:testapp_book_changelist"))
    url = reverse("admin:testapp_book_dyncol_save")
    response = client_admin.post(
        url,
        data=json.dumps(
            {
                "scope": "global",
                "columns": [
                    {"col_name": "isbn", "enabled": False, "ordering": 1},
                    {"col_name": "author", "enabled": True, "ordering": 2},
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "global"

    global_row = ModelAdmin.objects.get(
        user__isnull=True, class_name="tests.testapp.admin.BookAdmin"
    )
    assert global_row.modeladmincolumn_set.get(col_name="isbn").enabled is False

    # The acting superuser did NOT get a personal row (they edited global).
    User = get_user_model()
    user = User.objects.get(username="admin")
    assert not ModelAdmin.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_save_endpoint_global_scope_rejected_for_non_superuser(client, book_factory):
    User = get_user_model()
    plain_staff = User.objects.create_user(
        username="staffer", password="staffpass", is_staff=True
    )
    client.force_login(plain_staff)
    book_factory()

    client.get(reverse("admin:testapp_book_changelist"))
    url = reverse("admin:testapp_book_dyncol_save")
    response = client.post(
        url,
        data=json.dumps({"scope": "global", "columns": []}),
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_save_endpoint_global_scope_affects_other_users(
    client_admin, second_admin_user, book_factory
):
    book_factory(title="Globally visible", author="Some Author")

    # Superuser writes a global layout
    client_admin.get(reverse("admin:testapp_book_changelist"))
    client_admin.post(
        reverse("admin:testapp_book_dyncol_save"),
        data=json.dumps(
            {
                "scope": "global",
                "columns": [
                    {"col_name": "isbn", "enabled": False, "ordering": 1},
                    {"col_name": "author", "enabled": True, "ordering": 2},
                    {"col_name": "pages", "enabled": False, "ordering": 3},
                    {"col_name": "notes", "enabled": False, "ordering": 4},
                ],
            }
        ),
        content_type="application/json",
    )

    # Another user without a personal layout should now see the new global.
    from django.test import Client

    other_client = Client()
    other_client.force_login(second_admin_user)
    response = other_client.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    assert 'class="field-title"' in content  # pinned, always
    assert 'class="field-author"' in content  # global default still on
    # ``isbn`` was disabled in the global save above.
    assert 'class="field-isbn"' not in content


@pytest.mark.django_db
def test_reset_endpoint_global_scope_removes_global_row(client_admin):
    client_admin.get(reverse("admin:testapp_book_changelist"))
    reset_url = reverse("admin:testapp_book_dyncol_reset")
    response = client_admin.post(
        reset_url,
        data=json.dumps({"scope": "global"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert not ModelAdmin.objects.filter(
        user__isnull=True, class_name="tests.testapp.admin.BookAdmin"
    ).exists()


@pytest.mark.django_db
def test_reset_endpoint_global_scope_rejected_for_non_superuser(client, book_factory):
    User = get_user_model()
    plain_staff = User.objects.create_user(
        username="staffer", password="staffpass", is_staff=True
    )
    client.force_login(plain_staff)
    book_factory()

    client.get(reverse("admin:testapp_book_changelist"))
    response = client.post(
        reverse("admin:testapp_book_dyncol_reset"),
        data=json.dumps({"scope": "global"}),
        content_type="application/json",
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Constraint sanity check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unique_global_modeladmin_per_class(admin_user):
    from django.db import IntegrityError

    ct = ContentType.objects.first()

    ModelAdmin.objects.create(class_name="tests.X", model_ref=ct)
    with pytest.raises(IntegrityError):
        ModelAdmin.objects.create(class_name="tests.X", model_ref=ct)


@pytest.mark.django_db
def test_user_can_have_only_one_modeladmin_per_class(admin_user):
    from django.db import IntegrityError

    ct = ContentType.objects.first()
    ModelAdmin.objects.create(user=admin_user, class_name="tests.X", model_ref=ct)
    with pytest.raises(IntegrityError):
        ModelAdmin.objects.create(user=admin_user, class_name="tests.X", model_ref=ct)


@pytest.mark.django_db
def test_user_and_global_can_coexist_for_same_class(admin_user):
    ct = ContentType.objects.first()
    ModelAdmin.objects.create(class_name="tests.X", model_ref=ct)
    ModelAdmin.objects.create(user=admin_user, class_name="tests.X", model_ref=ct)
    assert ModelAdmin.objects.filter(class_name="tests.X").count() == 2


@pytest.mark.django_db
def test_two_users_can_have_their_own_layout(admin_user, second_admin_user):
    ct = ContentType.objects.first()
    ModelAdmin.objects.create(user=admin_user, class_name="tests.X", model_ref=ct)
    ModelAdmin.objects.create(
        user=second_admin_user, class_name="tests.X", model_ref=ct
    )
    assert ModelAdmin.objects.filter(class_name="tests.X").count() == 2
