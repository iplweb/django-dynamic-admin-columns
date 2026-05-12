# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`django-dynamic-admin-columns` is a Django library that moves `ModelAdmin.list_display` from a developer-time setting into the database, so end-users can enable/disable/reorder admin columns at runtime through a modal picker rendered into the changelist itself. Extracted from `iplweb/django-bpp`, in production since 2022.

Distributed on PyPI; CI matrix is Django 5.2 LTS + 6.0 on Python 3.11–3.14 (see `.github/workflows/tests.yml` for excluded cells).

## Commands

The project uses **uv** + **hatchling**. There is no Makefile; use these directly.

### Tests
```bash
uv run --no-sync pytest                              # full suite
uv run --no-sync pytest tests/test_per_user.py       # single file
uv run --no-sync pytest tests/test_per_user.py::TestClass::test_name -v
```
`pytest.ini_options` points `DJANGO_SETTINGS_MODULE` at `tests.settings`, which uses an in-memory SQLite and `tests.testapp` as the demo app under test. `tests/conftest.py` wires up `pytest-django` + `django-webtest`.

### Lint
```bash
ruff check .
ruff check --fix .
```
Ruff config in `pyproject.toml`. Migrations under `src/dynamic_admin_columns/migrations` are excluded; `tests/`, `example/`, `example_grappelli/` have the `DJ` (Django) ruleset disabled.

### Build / publish
```bash
uv build              # produces wheel + sdist in dist/
```
Hatchling honours `.gitignore`; `.mo` files are git-ignored but **must** ship — `[tool.hatch.build] artifacts = ["*.mo"]` re-includes them. The wheel only contains `src/dynamic_admin_columns/`; the sdist additionally bundles `tests/`, `example/`, and `example_grappelli/` (see `[tool.hatch.build.targets.sdist] include`).

### Translations
The package ships a Polish catalog. **Regenerate strictly per-app, never from the repo root**, otherwise `makemessages` will pollute the package catalog with strings from `example/` and `example_grappelli/`:
```bash
cd src/dynamic_admin_columns && django-admin makemessages -l pl
cd example/library            && django-admin makemessages -l pl
cd example_grappelli/library  && django-admin makemessages -l pl
```
Compile with `django-admin compilemessages` from each app dir for the same reason (running it from the repo root walks into `.venv/` site-packages).

### Running the example apps
Two parallel demos:
- `example/` — plain Django admin, English UI, no extra deps.
- `example_grappelli/` — django-grappelli skin, Polish UI, demos i18n integration.

Each has its own `requirements-dev.txt` pinning `django-run-site` (Postgres + Redis testcontainers, autologin) — intentionally **not** in `[project.optional-dependencies]` because PyPI rejects direct-reference URLs in published metadata. To launch:
```bash
uv pip install -e .
uv pip install -r example/requirements-dev.txt    # or example_grappelli/
cd example && uv run --no-sync python manage.py run_site
```
Plain-Django path (no containers): `python manage.py migrate && python manage.py loaddata sample && python manage.py runserver`.

## Architecture

### Two-table data model — `src/dynamic_admin_columns/models.py`
- `ModelAdmin` row identifies a `(class_name, model_ref, user)` triple. `user IS NULL` → **global defaults**; `user=<u>` → **personal layout** for that user.
- `ModelAdminColumn` rows are children of a `ModelAdmin`, one per column, carrying `col_name`, `enabled`, `ordering`.
- `class_name` is a dotted import path. Loading it back from the DB is gated by `DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS` (settings allowlist, enforced by `_check_allowed()` on every manager method) — without this, a tampered DB row could import arbitrary Python.
- `ModelAdminManager` exposes three semantic methods: `enable()` (return/create global row), `db_repr_for_user()` (return user row if it exists, else global), `clone_for_user()` (lazily fork global → personal on first save). Read these before adding new entry points.

### Mixin / scope flow — `mixins.py`, `views.py`
`DynamicColumnsMixin` is the user-facing entry point. It declares four list attributes that complement Django's `list_display`:
- `list_display_always` — pinned, code-only, never in the picker.
- `list_display_default` — visible out of the box, toggleable.
- `list_display_allowed` — hidden by default, user-discoverable.
- `list_display_forbidden` — per-admin regex denylist; combined with `DYNAMIC_ADMIN_COLUMNS_FORBIDDEN_COLUMN_NAMES` from settings.

`"__all__"` in any of the three positive lists expands to all model fields.

`get_list_select_related` is overridden so that when `list_select_related` is a **dict** keyed by column name, JOINs follow column visibility — hidden columns don't pay their join cost. The `"__always__"` key is always joined. This triggers `admin.E117`; the README instructs users to silence it via `SILENCED_SYSTEM_CHECKS`.

`views.save_columns` / reset endpoints accept a `scope` argument (`"personal"` / `"global"`); `_target_row()` routes to `clone_for_user` for personal scope and to `enable` for global, with a superuser gate on the global path.

### Grappelli dual templates
Two changelist templates ship under `templates/dynamic_admin_columns/`:
- `change_list.html` (stock admin)
- `grappelli/change_list.html` (django-grappelli skin)

`DynamicColumnsMixin.change_list_template` is a property that picks between them by querying `apps.is_installed("grappelli")` at request time (deferred so the app registry is populated). The grappelli example exists specifically to exercise this branch — keep both templates in sync when touching the picker UI.

### Front-end
Vanilla JS only — `static/dynamic_admin_columns/column-picker.js` (no jQuery, no SortableJS, no Bootstrap). Drag-and-drop is implemented in-house. There are two stylesheets, one per template (`column-picker.css`, `column-picker-grappelli.css`).

## Conventions worth knowing

- The package lives under `src/` (src layout). The package import name is `dynamic_admin_columns`; the distribution name is `django-dynamic-admin-columns`.
- Test app is `tests.testapp` — when adding fixtures or admin classes for tests, register them there, not in a new top-level app.
- `class_name` strings stored in the DB are produced by `util.qual()`. Any change to that helper is a migration-level breaking change for existing rows.
- The `example/` and `example_grappelli/` projects are demonstration code and are scope-excluded from the `DJ` ruff ruleset. They are bundled in the sdist but **not** in the wheel.
- Polish translation is shipped; the build pipeline depends on `.mo` files being present (regenerate before tagging a release).
