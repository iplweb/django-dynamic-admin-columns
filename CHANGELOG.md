# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/iplweb/django-dynamic-columns/releases/tag/v0.2.0
[0.1.0]: https://github.com/iplweb/django-dynamic-columns/releases/tag/v0.1.0
