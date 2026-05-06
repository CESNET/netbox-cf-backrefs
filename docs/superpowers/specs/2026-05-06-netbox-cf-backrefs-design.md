# netbox_cf_backrefs — Design

**Date:** 2026-05-06
**Status:** Draft for review
**Target NetBox:** 4.5.0 – 4.6.99
**Python:** 3.12 / 3.13 / 3.14

## Problem

NetBox custom fields of type `object` and `multi-object` create one-way links from a source object (e.g., a Device) to a target object (e.g., a Contact). The source page shows the link; the target page shows nothing. A user viewing the Contact has no indication that any Device, Circuit, or other object references it via a custom field.

## Goal

Surface the **reverse** side of object/multi-object custom field links on the target object's detail page, so users viewing the target can see what references it and why.

## Non-goals

- Modifying or supplementing the *forward* side (already works in NetBox).
- Reverse lookups for non-CF relations (FKs, GFKs) — out of scope.
- A standalone full-page browse view — v1 keeps everything inside the object detail panel.

## Display

A single inline panel injected via `PluginTemplateExtension.full_width_page()`, rendered below the object's standard content. No tab; no separate URL.

**Panel header:** `Referenced by Custom Fields (N)` where N is the total reference count.

**Table:** flat, three columns:

| Source object | Source type | Custom field |
|---|---|---|
| `device-01` (link) | Device | Technical contact |
| `circuit-42` (link) | Circuit | Escalation contact |

- Source object cell links to `source_object.get_absolute_url()`.
- Source type is the model's verbose name.
- Custom field shows `cf.label` (falls back to `cf.name`).
- Sorting: client-side per page (current-page slice only).
- Pagination: standard NetBox `inc/paginator.html`; query param `?cfbackrefs_page=N`.

**Empty state:** panel suppressed entirely when zero rows. No "no references" message.

## Architecture

A standard NetBox plugin package, no models, no migrations.

### File layout

```
netbox_cf_backrefs/
├── __init__.py              # PluginConfig
├── template_content.py      # Dynamic PluginTemplateExtension registration
├── utils.py                 # get_reverse_cf_references()
├── templates/
│   └── netbox_cf_backrefs/
│       └── panel.html
├── tests/
│   ├── __init__.py
│   ├── test_utils.py
│   └── test_template_content.py
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── MANIFEST.in
└── Makefile
```

### Dynamic extension registration

On plugin import, `template_content.py` executes:

1. Query `CustomField.objects.filter(type__in=['object', 'multiobject'])`.
2. Collect distinct `related_object_type` values (the *target* content types).
3. For each target content type, generate a `PluginTemplateExtension` subclass with `model = "<app>.<model>"` and a `full_width_page()` method that calls into `utils.get_reverse_cf_references()` and renders the panel template.
4. Append each subclass to the `template_extensions` list exported by the module.

The panel therefore appears only on detail pages of objects whose type is currently a CF target. Adding a new CF after startup requires a NetBox restart for the registration to pick it up — same restart constraint NetBox imposes for plugin/template-extension reloads. Documented in README.

### Per-page query flow

`utils.get_reverse_cf_references(target_obj) -> list[Reference]`:

1. Look up `CustomField.objects.filter(type__in=['object','multiobject'], related_object_type=ContentType.objects.get_for_model(target_obj))`, excluding CFs whose `name` is in the `excluded_custom_fields` setting and CFs whose `ui_visible == 'hidden'`.
2. For each matching CF, iterate the source models from `CustomField.object_types` (M2M to `ObjectType`).
3. For each (CF, source_model) pair, run a JSONField-backed query:
   - **object CF:** `source_model.objects.filter(**{f'custom_field_data__{cf.name}': target_obj.pk})`
   - **multi-object CF:** `source_model.objects.filter(**{f'custom_field_data__{cf.name}__contains': [target_obj.pk]})`
4. Yield `Reference(source_object, source_model_label, cf_name, cf_label)` rows.
5. The view paginates the combined list in Python (size from `page_size` setting). If empty, `full_width_page()` returns `''` so no panel is rendered.

`Reference` is a simple dataclass / namedtuple — no DB persistence.

### Permissions

Per the explicit design decision, **the panel does not filter source objects by the viewing user's object permissions**. Every viewer sees the same complete list. The trade-off (potential leakage of restricted object names) is accepted in exchange for predictability and simpler implementation. Documented prominently in README.

CF-level visibility is still respected: CFs with `ui_visible='hidden'` are skipped.

## Settings

```python
PLUGINS_CONFIG = {
    'netbox_cf_backrefs': {
        'page_size': 50,
        'excluded_custom_fields': [],   # list of CF names (not labels)
    }
}
```

Defaults shown above. Both keys validated and merged in `PluginConfig.default_settings`.

## Error handling

| Edge case | Behavior |
|---|---|
| CF deleted but source row still has orphan JSON key | Invisible — only current `CustomField` rows are iterated. |
| Source object deleted between query and render | Not returned; nothing to handle. |
| `related_object_type` references an uninstalled model | `try/except` around `ContentType.model_class()`; log warning, skip CF. |
| CF marked `ui_visible='hidden'` | Skipped. |
| Multi-object stored as list — value type mismatch | Wrap target PK as `[pk]` for `__contains`. Unit-tested. |
| Same source object referenced by two CFs | Two rows (no dedup). |
| Any unhandled exception in `full_width_page()` | Caught at panel boundary, logged, returns `''`. Object page must never 500 because of this plugin. |

## Testing

NetBox's Django test runner: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb`.

### Unit tests (`tests/test_utils.py`)

- Returns `[]` when no CFs target the model.
- Single-object CF: matching source returned, non-matching not.
- Multi-object CF: target PK inside list returned, absent not.
- Multiple CFs from same source model on same target → multiple rows.
- Mixed source models on same target → all returned with correct labels.
- `excluded_custom_fields` setting suppresses the named CF.
- CF with `ui_visible='hidden'` skipped.
- CF whose `object_types` references an unloadable model skipped silently with log warning.
- Same source object with two CFs to same target → two rows (no dedup).

### Integration tests (`tests/test_template_content.py`)

- Object that is a CF target with references → response contains panel header, link, CF label.
- Object whose type has CFs but zero current references → panel absent.
- Object whose type has no CF targets → panel absent.
- Pagination: `page_size=2` + 5 references → pages of 2/2/1; `?cfbackrefs_page=2` works.
- Permission decision (B): a user without view permission on the source object **still sees the row** — assertion locks the decision in.
- Panel exception path: monkey-patch `get_reverse_cf_references` to raise → object page returns 200, panel absent.

### Coverage target

≥80 % on `utils.py` and `template_content.py`.

### Manual QA (README + CONTRIBUTING)

- Install into a dev NetBox, create CFs, verify panel.
- Test with a third-party plugin model (e.g., custom-objects plugin) to confirm dynamic registration handles plugin-supplied models.

## Open questions

None at design time. The following are deferred to future versions, not blockers:

- Server-side cross-page sorting.
- Hot-reload of CF registrations without restart.
- Switch to a denormalized index table if profiling shows the live-query approach is too slow at scale.
