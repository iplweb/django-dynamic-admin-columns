import pytest
from django.contrib.admin import site
from django.contrib.auth import get_user_model


@pytest.fixture(autouse=True)
def reset_dynamic_columns_admin_cache():
    """Drop cached ``_modeladmin_enabled`` on every registered admin.

    Admin instances are module-level singletons, so the
    ``cached_property`` on :class:`DynamicColumnsMixin` survives the
    per-test database rollback that pytest-django performs. Without
    clearing it, a test that mutates ``ModelAdminColumn`` rows would
    see those columns reappear from the previous test's cache."""

    yield

    for admin_instance in site._registry.values():
        admin_instance.__dict__.pop("_modeladmin_enabled", None)


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )


@pytest.fixture
def client_admin(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def book_factory(db):
    from tests.testapp.models import Book

    def make(**kwargs):
        defaults = {
            "title": "Untitled",
            "author": "Anonymous",
            "isbn": "0000000000000",
            "pages": 1,
        }
        defaults.update(kwargs)
        return Book.objects.create(**defaults)

    return make
