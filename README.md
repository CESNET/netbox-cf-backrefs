# netbox_cf_backrefs

NetBox plugin that surfaces the **reverse** side of object / multi-object custom field references on the target object's detail page.

If you create a custom field of type `object` (or `multi-object`) on a Device pointing to a Contact, NetBox shows the contact under the device — but the contact page has no indication of being referenced. This plugin adds an inline panel **"Referenced by Custom Fields"** to the contact page (and to every other NetBox object that is a current CF target).

## Compatibility

- NetBox 4.5.0 – 4.6.99
- Python 3.12 / 3.13 / 3.14

## Install

```bash
source /opt/netbox/venv/bin/activate
pip install netbox-cf-backrefs
```

Add to `configuration.py`:

```python
PLUGINS = ["netbox_cf_backrefs"]

PLUGINS_CONFIG = {
    "netbox_cf_backrefs": {
        "page_size": 50,
        "excluded_custom_fields": [],
        "default_display": "panel",
        "display_overrides": {},
    }
}
```

Restart NetBox.

## Settings

| Key | Default | Description |
|---|---|---|
| `page_size` | `50` | Rows per page in the panel paginator. |
| `excluded_custom_fields` | `[]` | List of CF *names* (not labels) to suppress from all backref panels. |
| `default_display` | `"panel"` | How backrefs surface by default: `"panel"`, `"tab"`, `"both"`, or `"none"`. |
| `display_overrides` | `{}` | Per-model overrides — `{"app_label.model": mode}` (keys lowercase). |

## Display: panel vs tab

Each target model can surface its backrefs as the inline **panel**, the **CF Backrefs tab**, **both**, or **neither**. By default every model uses the panel only.

- `default_display` — the mode for any model without an override: `"panel"` (default), `"tab"`, `"both"`, or `"none"`.
- `display_overrides` — a map of `"app_label.model"` (lowercase) to a mode, overriding the default for specific models.

```python
PLUGINS_CONFIG = {
    "netbox_cf_backrefs": {
        "default_display": "panel",
        "display_overrides": {
            "tenancy.contact": "both",   # panel + tab
            "dcim.device": "tab",        # tab only
            "ipam.prefix": "none",       # neither
        },
    }
}
```

- **Surfaces are registered at startup**, so changing `default_display` / `display_overrides` requires a **NetBox restart** (consistent with how the plugin discovers CF targets). A model gated to `panel`/`none` never registers a tab route at all — a direct visit to its `…/cf-backrefs/` URL is a normal 404.
- **Custom Objects are always forced to `panel`.** A `tab`/`both` mode on a `netbox_custom_objects.table<N>model` target is coerced to `panel`, because their tab route is structurally unreversible (see [`docs/TODO-custom-objects-tab.md`](docs/TODO-custom-objects-tab.md)).
- Invalid values fall back to the default and are logged once at startup.

## Behavior notes

- **No permission filtering.** Every viewer sees the same complete list of references. If user X has no `view` permission on Device-1 but Device-1 references the Contact they are viewing, Device-1 will still appear (as a clickable link). Choose this plugin only if that trade-off is acceptable for your deployment.
- **CFs marked `ui_visible='hidden'` are skipped** — admin-only CFs won't leak through the panel.
- **Restart required for discovery & display changes** — the plugin discovers CF target models and registers each model's surfaces (panel/tab) at NetBox startup. Adding a new CF, or changing `default_display` / `display_overrides`, requires a NetBox restart to take effect.
- **Empty panels are hidden.** If no objects currently reference the target via CFs, the panel is not rendered.

## CF Backrefs tab

When a model's display mode includes the tab (`tab` or `both` — see *Display: panel vs tab*; off by default), its detail page exposes a **CF Backrefs** tab (`/<app>/<model>/<pk>/cf-backrefs/`) whenever at least one CF references the object. The tab is intentionally minimal — it mirrors `netbox_custom_objects`'s combined-tabs visual baseline: a quick-search input, an htmx-paginated table, and a single per-row filter-icon action. No filter sidebar, no sortable headers.

The per-row filter icon (`mdi mdi-filter`) pivots to the source model's NetBox list view filtered by the CF that produced the row, e.g. `/dcim/devices/?cf_tech_contact=<contact_pk>` ("show me every Device that references this same target via this CF").

**Important:** the tab deliberately ignores the `excluded_custom_fields` setting and the CF-level `ui_visible='hidden'` flag. Anyone with `view_<parent_model>` permission can see hidden / excluded CF references via the tab. The panel honors both filters and is the curated view; the tab is the "everything" view. If your hidden CFs carry sensitive data, do not rely on the tab to hide them.

## Custom Objects (`netbox_custom_objects`)

When a Custom Object is the **target** of an object / multi-object CF, support is partial. Behavior (verified against `netbox_custom_objects` 0.5.1):

| Situation | Panel | Tab |
|---|---|---|
| Custom Object type that existed at NetBox startup | ✅ works | ❌ not shown |
| Custom Object type created **after** NetBox started | ❌ until restart | ❌ |
| Same new type, **after a NetBox restart** | ✅ works | ❌ |

- **The panel works** on Custom Object detail pages, because it is a template extension matched by model label (no URL routing involved).
- **The tab never appears on Custom Object pages — and the plugin now enforces it.** A `tab`/`both` display mode on a Custom Object target is coerced to `panel`, so no tab route is registered for it. Even without the coercion, Custom Object models are dynamically generated (`table<N>model`) and `netbox_custom_objects` never registers a routable URL for them, so the tab's link can't be reversed (see [`docs/TODO-custom-objects-tab.md`](docs/TODO-custom-objects-tab.md)).
- **New Custom Object types need a NetBox restart.** The plugin discovers CF target models once, at startup. A Custom Object type created at runtime is invisible to both surfaces until the next restart (same caveat as adding any object-CF — see *Behavior notes* above).
- **A Custom Object instance cannot be a CF *source*.** Custom Object rows have no `custom_field_data` field, so they can never hold a NetBox object/multiobject CF and will never appear as a source row in a backref panel or tab.

## Development

```bash
make test       # runs the suite via NETBOX_CONFIGURATION=netbox_cf_backrefs.tests.configuration (both surfaces enabled)
make lint       # ruff + djlint --check
make format     # ruff format + djlint --reformat
```

## License

Apache-2.0
