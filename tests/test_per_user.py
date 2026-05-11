"""Per-user column layout — manager, mixin, view endpoints."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from dynamic_columns.models import ModelAdmin


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
    # The picker should *not* show pinned ``list_display_always`` rows.
    # ``title`` is the only pinned column for BookAdmin.
    item_block = content.split('class="dyncol-modal"')[1]
    assert 'data-col-name="title"' not in item_block


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
def test_changelist_without_personal_layout_has_no_reset_button(client_admin):
    response = client_admin.get(reverse("admin:testapp_book_changelist"))
    content = response.content.decode()
    assert 'id="dyncol-reset"' not in content


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
