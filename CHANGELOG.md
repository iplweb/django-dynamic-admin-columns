# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/iplweb/django-dynamic-columns/releases/tag/v0.1.0
