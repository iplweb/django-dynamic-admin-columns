# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.4.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.4.0
[0.3.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.3.0
[0.2.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.2.0
[0.1.0]: https://github.com/iplweb/django-dynamic-admin-columns/releases/tag/v0.1.0
