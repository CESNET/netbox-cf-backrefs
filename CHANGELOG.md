# Changelog

## 0.1.1 — 2026-05-06

- Rebuild panel rendering on `django_tables2` + `NetBoxTable`-style markup; rows now use NetBox's standard `inc/table.html` partial (sortable headers, hover styles, htmx-aware).
- Pagination switched to `EnhancedPaginator` with prefixed query params `?cfbackrefs_page=N` and `?cfbackrefs_per_page=N` to avoid collisions with sibling plugins' paginators on the same object page.
- Per-page dropdown added to the panel paginator (uses `page_size` setting as the default).
- `orphans=0` so panels with few rows still paginate predictably.
- New minimal `CF Backrefs` detail-page tab on every CF target object. Visual baseline mirrors `netbox_custom_objects`'s combined-tabs view: quick-search input, htmx-paginated table, and a single per-row filter-icon action pivoting to `/<app>/<model>/?cf_<name>=<target_pk>`. No filter sidebar, no Configure-Table modal, no sortable headers — by design. Tab uses standard NetBox tab permissions (`view_<parent_model>`) and deliberately surfaces hidden / excluded CFs that the panel suppresses.

## 0.1.0 — 2026-05-06

- Initial release.
- Inline `Referenced by Custom Fields` panel on object detail pages, listing source object, source type, and custom field for every object/multi-object CF reference pointing to the current object.
- `page_size` and `excluded_custom_fields` plugin settings.
- Skips CFs with `ui_visible='hidden'`.
- Resilient to uninstalled source models (logs a warning and continues).
- No permission filtering on rows — design decision documented in README.
