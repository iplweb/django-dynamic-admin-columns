# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-08-07

### Added

- **Support for Django 6.1.** The CI matrix now covers Django 6.1
  alongside 5.2 LTS and 6.0, and the trove classifiers advertise it.
  Django 6.1 requires Python 3.12+, so the `3.11 × 6.1` cell is
  excluded from the matrix just like `3.11 × 6.0`.

- **Tests for the package's own admin classes.** `tests/test_own_admin.py`
  renders the `ModelAdmin` and `ModelAdminColumn` changelists, the
  column change form and `adminsortable2`'s drag-and-drop reordering
  endpoint. `ModelAdminColumnAdmin` mixes in
  `adminsortable2.admin.SortableAdminMixin` — the most Django-version-
  fragile surface in the package — and nothing exercised it before.

### Fixed

- **`django-admin-sortable2` floor raised from `>=2.1` to `>=2.1.2`.**
  Releases 2.1 and 2.1.1 returned `pathlib.Path` objects from
  `SortableAdminMixin.change_list_template`. Django's template loaders
  tolerated that through 5.2, but on Django 6.0 and 6.1 the lookup no
  longer resolves, so every sortable changelist — including this
  package's own `ModelAdminColumn` admin — raised
  `TypeError: sequence item 0: expected str instance, PosixPath found`
  while building the `TemplateDoesNotExist` message. 2.1.2 wraps the
  names in `str()`. Verified locally against Django 5.2, 6.0 and 6.1
  at both the new floor and the current 2.3.1.

## [0.5.0] - 2026-05-31

### Changed

- **`0001_initial` is now idempotent and swappable-user-model safe.**
  The migration builds its tables through the schema editor
  (`create_model`), guarded to run only when `dynamic_columns_*` are
  absent, instead of a plain `CreateModel`. Two payoffs:
  - **Pre-existing schema no longer collides.** Projects that predate
    the package extraction (notably BPP, whose in-tree `dynamic_columns`
    app created these tables years ago) can apply `0001_initial` onto a
    database that already carries the tables — it detects them and
    no-ops. This makes the dedicated `MIGRATION_MODULES` override such
    projects used to ship unnecessary; they can drop it and consume the
    package's migrations directly.
  - **Custom user models resolve correctly on a from-empty build.** The
    `user` FK is materialised by the schema editor against
    `settings.AUTH_USER_MODEL`, so a fresh `migrate` (or
    `migrate --create-db` / baseline rebuild) on a project with a
    swapped user model points the FK at the right table instead of a
    hard-coded `auth_user`.

  The migration state is unchanged (a `CreateModel` pair plus the
  existing constraints, now under `SeparateDatabaseAndState`), so
  databases that already recorded `0001_initial` as applied are
  unaffected and `makemigrations` detects no drift.

## [0.4.5] - 2026-05-12

### Fixed

- **CSRF 403 on save/reset when `CSRF_COOKIE_HTTPONLY = True`.** The
  picker JS used to read the token exclusively from `document.cookie`,
  which is unreachable when downstream projects harden the cookie per
  Django's security recommendations — the `X-CSRFToken` header was
  posted empty and Django rejected it with "incorrect length". Both
  changelist templates now render `{% csrf_token %}` inside the modal
  and `column-picker.js` prefers the hidden input, falling back to the
  cookie for projects that don't override the default.

### Changed

- **Column list inside the picker now scrolls; Save/Reset/Cancel stay
  pinned.** `.dyncol-modal-content` switched to a flex column with the
  list as the only scrolling child (`flex: 1 1 auto; overflow-y:
  auto`), so the action bar is always visible regardless of column
  count.
- **Auto-scroll while dragging.** A list-level `dragover` handler
  nudges `scrollTop` when the dragged pointer enters a 40 px zone near
  the top or bottom edge, so reordering across long lists no longer
  requires letting go and scrolling manually.

## [0.4.4] - 2026-05-12

### Fixed

- **`change_list_template` is now a settable property.** The skin-aware
  `@property` introduced in 0.4.x had no setter, so any downstream
  `ModelAdmin` that composed `DynamicColumnsMixin` with a library that
  reassigns `self.change_list_template` in `__init__` — notably
  `django-import-export`'s `ImportExportMixinBase`, which deliberately
  wraps the existing template by stashing it as
  `ie_base_change_list_template` and pointing the active template at
  its own — silently lost that composition. The assignment raised
  `AttributeError` (caught upstream and logged only as `failed to
  assign change_list_template attribute`), so the host's Export
  object-tool never rendered. The property now stores assignments to
  an instance-level `_change_list_template_override`; reading returns
  the override when set, otherwise the skin-derived default; `del
  self.change_list_template` clears the override. Three regression
  tests cover the round-trip, per-instance isolation, and the
  import_export-style composition pattern end-to-end.

## [0.4.3] - 2026-05-12

### Changed

- **Translation workflow is now strictly per-app.** The package
  catalog (`src/dynamic_admin_columns/locale/pl/`) was previously
  regenerable from the repo root, which silently slurped strings from
  `example/` and `example_grappelli/` into the published `.po`. Source
  line references in `django.po` are now refreshed against the current
  code (`mixins.py` line numbers shifted by three lines) and the file
  is guaranteed to contain only msgids extracted from
  `src/dynamic_admin_columns/`. No msgid / msgstr content changes —
  end-user-visible strings and their Polish translations are identical
  to 0.4.2.
- **Plain example (`example/library/`) is now translation-ready.**
  Model field labels and the app `verbose_name` were promoted from
  plain literals to `gettext_lazy`, and the app ships its own
  `locale/pl/` catalog mirroring `example_grappelli/library/`. The
  plain example's `LANGUAGE_CODE` remains `en-us`; the Polish catalog
  is provided so developers experimenting with the example can flip
  the setting and see a fully translated demo without first having to
  add `_()` wrappers. The package's own catalog is unaffected.

### Added

- `CLAUDE.md` documenting the per-app `makemessages` rule, the
  two-table data model with allowlist-gated `class_name` loading, and
  the dual stock/grappelli changelist template flow, so future
  automated assistants can be productive without re-reading
  `mixins.py` and `models.py` end-to-end.

## [0.4.2] - 2026-05-12

### Fixed

- **Published metadata no longer carries direct git references.**
  `[example]` / `[example-grappelli]` optional-dependency groups
  pinned `django-run-site` from a GitHub tag (it has no PyPI release
  under its current name); PyPI's `/legacy/` upload endpoint rejects
  any package metadata that contains direct-URL requirements, which
  blocked the 0.4.1 upload. The dev stack moved to per-folder
  `example/requirements-dev.txt` and
  `example_grappelli/requirements-dev.txt` — installable with
  `pip install -r …` from a checkout, invisible to PyPI consumers.

## [0.4.1] - 2026-05-12

### Fixed

- **Compiled translation catalogs (`.mo`) now ship in the published
  wheel and sdist.** Hatchling honours `.gitignore` by default and the
  repo excludes `*.mo` (each contributor compiles locally from `.po`),
  which silently meant that PyPI users of 0.2 – 0.4.0 never received
  any of the Polish strings. `pyproject.toml` now sets
  `[tool.hatch.build] artifacts = ["*.mo"]` so the published artifacts
  contain the compiled catalogs and translations work out of the box
  for `pip install`-from-PyPI consumers.

### Changed

- `README.md` — embedded a picker-modal screenshot, dropped the
  standalone Python support table (the Django × Python matrix already
  conveys the same information).

## [0.4.0] - 2026-05-11

### Added

- **django-grappelli compatibility.** `DynamicColumnsMixin` now
  auto-detects `grappelli` in `INSTALLED_APPS` and switches its
  changelist template to a grappelli-aware variant
  (`dynamic_admin_columns/grappelli/change_list.html`) that renders
  the picker pill in grappelli's `.grp-object-tools` style and the
  modal action buttons as `grp-button` instances. A second stylesheet,
  `column-picker-grappelli.css`, neutralises grappelli's
  `button { height:28px; overflow:hidden }` reset (which truncated
  long labels such as *"Przywróć globalne ustawienia z kodu"*) and
  lets every button grow with its current label. Override
  `DynamicColumnsMixin._change_list_template_default` /
  `_change_list_template_grappelli` (or the
  `change_list_template` property itself) to opt out per-admin.
- **Second example project** (`example_grappelli/`) demonstrating the
  picker under [django-grappelli](https://django-grappelli.readthedocs.io/)
  with a Polish-localised UI (`LANGUAGE_CODE = "pl"`, `gettext_lazy` on
  every field, `library/locale/pl/`). Pulled in via a new
  `[example-grappelli]` optional-dependency group.
- **Completed Polish translation catalog** for every picker UI string
  — including the dynamic ones rendered by `column-picker.js` when the
  user flips the scope radio (*Editing the global defaults…*, *Reset
  global defaults from code*) and the confirm / error dialogs (*Reset
  the GLOBAL defaults?…*, *Failed to save columns:*). The JavaScript
  side now reads translations from a server-rendered JSON tag
  (`#dyncol-i18n`) instead of `window.gettext`, so projects do not
  have to wire up a custom `JavaScriptCatalog` URL to get localised
  status messages.

## [0.3.0] - 2026-05-11

### Breaking

- **Renamed Python module and Django app label** from
  `dynamic_columns` to `dynamic_admin_columns` for naming consistency
  with the published PyPI distribution `django-dynamic-admin-columns`.
  Update imports:

  ```python
  from dynamic_admin_columns.mixins import DynamicColumnsMixin
  ```

  Use `"dynamic_admin_columns"` in `INSTALLED_APPS`.
- **Renamed settings constants**:
  `DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS` →
  `DYNAMIC_ADMIN_COLUMNS_ALLOWED_IMPORT_PATHS` and
  `DYNAMIC_COLUMNS_FORBIDDEN_COLUMN_NAMES` →
  `DYNAMIC_ADMIN_COLUMNS_FORBIDDEN_COLUMN_NAMES`.

### Notes

- On-disk DB table names stay as `dynamic_columns_modeladmin` /
  `dynamic_columns_modeladmincolumn` via `Meta.db_table`, so existing
  data carries over without any SQL migration. Only the Python import
  path and the settings constant names change.

### Added

- Superuser-only **"Global defaults"** scope in the column picker.
  Staff users without `is_superuser` see only the *My personal layout*
  tab; superusers see a radio switch that lets them save changes
  either as their personal copy or as the global default visible to
  every user without one. The matching *Discard* / *Reset* button
  operates on whichever scope is currently selected.

## [0.2.0] - 2026-05-11

### Added

- **Per-user column layouts.** Each staff user now keeps a personal
  copy of the columns visible in a `ModelAdmin` changelist. Global
  rows (the previous behaviour) still work and act as the default
  layout for any user who has not personalised the admin.
- **In-changelist picker UI.** `DynamicColumnsMixin` injects a
  *Columns* button into the standard `object-tools` area at the
  top-right of the changelist. The button opens a modal where the
  logged-in user can toggle the visibility of each user-configurable
  column and reorder them via native HTML5 drag-and-drop. Saving
  writes through to that user's personal layout; a *Reset to
  defaults* button discards the personal layout and falls back to
  the global defaults.
- Manager methods `ModelAdmin.objects.db_repr_for_user(model_admin, user)`
  and `ModelAdmin.objects.clone_for_user(model_admin, user)` for
  resolving and creating per-user layouts programmatically.
- `views.save_columns` and `views.reset_columns` JSON endpoints,
  registered automatically through `DynamicColumnsMixin.get_urls()`
  under `dynamic-columns/save/` and `dynamic-columns/reset/` inside
  each admin's URL namespace.
- Vanilla-JS picker (`column-picker.js`) and matching stylesheet —
  no external JS libraries, no SortableJS, no jQuery.
- Polish-language UI labels are exposed via `gettext_lazy` and ready
  for translation.
- Example project (`example/`) updated to ship two pre-loaded staff
  users (`alice`, `bob`) so the per-user behaviour can be
  demonstrated without manual setup.

### Changed

- `ModelAdmin` rows now carry an optional `user` foreign key. Rows
  with `user IS NULL` are global defaults (existing behaviour);
  rows with a populated `user` are that user's personal copy.
- `unique_together = [("class_name", "model_ref")]` replaced by two
  conditional `UniqueConstraint`s (`user IS NULL` / `user IS NOT NULL`)
  so global and per-user rows can coexist for the same admin.
- `ModelAdmin.get_list_display` now reads from
  `self.modeladmincolumn_set` rather than re-looking up the global
  row, which makes it polymorphic between global and per-user rows
  without a second query.
- Internal helper `_check_allowed` factored out of the manager to
  share the `DYNAMIC_COLUMNS_ALLOWED_IMPORT_PATHS` gate between
  `db_repr`, `db_repr_for_user` and `clone_for_user`.
- Existing `ModelAdminColumnAdmin` is joined by a new read-mostly
  `ModelAdminAdmin` that exposes which rows are global vs personal
  and lets superusers filter by user.

### Migration

- New migration `0005_modeladmin_user`. It adds the `user` column
  (NULLable, `on_delete=CASCADE`) and swaps the unique constraints.
  Existing rows remain unchanged: they keep `user=NULL` and continue
  to act as global defaults, so upgrading is a no-op for anyone who
  has not yet adopted per-user layouts.

## [0.1.0] - 2026-05-11

### Added

- Initial public release. Extracted from the BPP project where it has been
  running in production since 2022.
- `DynamicColumnsMixin` for `ModelAdmin` classes — enables runtime, per-user
  configurable `list_display` stored in the database.
- Support for `list_display_always`, `list_display_default`,
  `list_display_allowed` and `list_display_forbidden` attributes on
  `ModelAdmin`.
- Support for the special `"__all__"` value in column source attributes to
  expose all model fields as candidate columns.
- Dictionary form of `list_select_related` that mirrors visible columns,
  including the `"__always__"` key for unconditional select-related entries.
- Polish translation (`pl`).
- Pytest-based test suite and minimal example Django project demonstrating
  end-user configuration of admin columns.

[0.6.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.6.0
[0.4.2]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.4.2
[0.4.1]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.4.1
[0.4.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.4.0
[0.3.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.3.0
[0.2.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.2.0
[0.1.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.1.0
