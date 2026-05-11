# django-dynamic-columns

[![PyPI](https://img.shields.io/pypi/v/django-dynamic-columns.svg)](https://pypi.org/project/django-dynamic-columns/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-dynamic-columns.svg)](https://pypi.org/project/django-dynamic-columns/)
[![License](https://img.shields.io/pypi/l/django-dynamic-columns.svg)](https://github.com/iplweb/django-dynamic-columns/blob/main/LICENSE)
[![Tests](https://github.com/iplweb/django-dynamic-columns/actions/workflows/tests.yml/badge.svg)](https://github.com/iplweb/django-dynamic-columns/actions/workflows/tests.yml)

**User-controllable, in-database `list_display` for Django admin.** End-users
enable, disable and reorder columns at runtime through the admin itself — no
code changes, no redeploy.

## Why

`django.contrib.admin.ModelAdmin.list_display` is a *developer-time* setting.
If end-users want different columns visible, the developer has to ship a code
change. In bibliographic, archival and CRUD-heavy admin sites the column set
varies between users and projects; this library moves that choice into the
database so the admin UI itself is the configuration surface.

Extracted from the [BPP](https://github.com/iplweb/django-bpp) academic
bibliography system where it has run in production since 2022.

## Features

- Drop-in `DynamicColumnsMixin` for any `ModelAdmin`.
- **In-changelist picker.** A *Columns* button in the standard
  `object-tools` area opens a modal where end-users toggle columns and
  reorder them via drag-and-drop — no admin training, no separate
  preferences page.
- **Per-user layouts.** Each staff user keeps their own column
  configuration; users without a personal layout fall back to the
  global defaults. Resetting is one click away.
- Three column tiers: **always** (pinned, code-only), **default** (visible
  out of the box, user can toggle), **allowed** (hidden by default,
  user-discoverable).
- Per-admin and project-wide regex denylists (`list_display_forbidden`,
  `DYNAMIC_COLUMNS_FORBIDDEN_COLUMN_NAMES`) to keep sensitive or noisy
  fields out of the picker.
- `"__all__"` shorthand: expose every model field and let the user pick.
- Dictionary form of `list_select_related` that activates joins only for
  columns that are actually visible — no overhead for columns the user
  has hidden.
- Vanilla-JS picker UI — **no SortableJS, no jQuery, no Bootstrap**.
- Settings-gated import allowlist (`DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS`)
  to prevent arbitrary class loading from untrusted database content.
- Polish translation included.

## Installation

```bash
uv add django-dynamic-columns
# or
pip install django-dynamic-columns
```

Add the apps and the import allowlist to your settings:

```python
INSTALLED_APPS = [
    # ...
    "adminsortable2",
    "dynamic_columns",
]

DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS = [
    "myapp.admin",
]

# Optional global regex denylist applied to every dynamic admin.
DYNAMIC_COLUMNS_FORBIDDEN_COLUMN_NAMES = [
    r".*_cache$",
    r"^cached_.*",
]

# django-admin-sortable2's reordering view triggers admin.E117 with a dict
# ``list_select_related`` — silence it.
SILENCED_SYSTEM_CHECKS = ["admin.E117"]
```

Then run migrations:

```bash
python manage.py migrate dynamic_columns
```

## Usage

```python
# myapp/admin.py
from django.contrib import admin
from dynamic_columns.mixins import DynamicColumnsMixin

from myapp.models import Book


@admin.register(Book)
class BookAdmin(DynamicColumnsMixin, admin.ModelAdmin):
    # Pinned columns: always visible, always first, cannot be toggled.
    list_display_always = ["title"]

    # Visible out of the box, user can hide or reorder.
    list_display_default = ["author", "isbn"]

    # Hidden by default, user can enable via the admin.
    list_display_allowed = ["pages", "notes"]

    # Per-admin denylist (regex). Wins over ``__all__``.
    list_display_forbidden = [r"^legacy_.*"]
```

First time a user opens the changelist, the matching `ModelAdmin` row and
`ModelAdminColumn` rows are created automatically. The user manages them
from the standard "Model admin columns" admin section.

### Dynamic select_related

Pay the JOIN cost only for columns that are actually visible:

```python
class BookAdmin(DynamicColumnsMixin, admin.ModelAdmin):
    list_display_default = ["author"]
    list_display_allowed = ["publisher"]

    list_select_related = {
        "__always__": ["category"],       # always joined
        "author": ["author"],             # joined only if the column is visible
        "publisher": ["publisher"],
    }
```

## Example project

A minimal Django project demonstrating the library lives in
[`example/`](example/). Run it with:

```bash
cd example
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then visit `http://127.0.0.1:8000/admin/` and inspect the *Books* admin to
see dynamic columns in action.

## Supported versions

### Python

| Python | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 |
|--------|------|------|------|------|------|
|        | ✓    | ✓    | ✓    | ✓    | ✓    |

### Django

This package targets **actively supported** Django releases. Older
Django versions (4.2 LTS, 5.0, 5.1) are end-of-life upstream and are
not covered by CI. If you are still on those releases, pin
`django-dynamic-columns < 0.2` once a 0.2 release lands; the 0.1.x
series will keep working with whatever Django you can install.

| Django  | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | Status                                 |
|---------|------|------|------|------|------|----------------------------------------|
| 5.2 LTS | ✓    | ✓    | ✓    | ✓    | —    | Active LTS, extended support Apr 2028 |
| 6.0     | —    | —    | ✓    | ✓    | ✓    | Current mainstream                     |

CI exercises every ✓ cell on GitHub Actions.

## License

MIT. See [LICENSE](LICENSE).
