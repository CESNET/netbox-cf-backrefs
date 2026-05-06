# Changelog

## 0.1.0 — 2026-05-06

- Initial release.
- Inline `Referenced by Custom Fields` panel on object detail pages, listing source object, source type, and custom field for every object/multi-object CF reference pointing to the current object.
- `page_size` and `excluded_custom_fields` plugin settings.
- Skips CFs with `ui_visible='hidden'`.
- Resilient to uninstalled source models (logs a warning and continues).
- No permission filtering on rows — design decision documented in README.
