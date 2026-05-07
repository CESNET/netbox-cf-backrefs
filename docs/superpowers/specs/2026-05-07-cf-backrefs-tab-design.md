# netbox_cf_backrefs — CF Backrefs Tab

**Date:** 2026-05-07
**Status:** Draft for review
**Target NetBox:** 4.5.0 – 4.6.99
**Python:** 3.12 / 3.13 / 3.14
**Builds on:** `2026-05-06-netbox-cf-backrefs-design.md` (panel design)
**Version policy:** stays on the current `0.1.1` line — no version bump for this feature.

## Problem

The v0.1.1 panel is a fixed slot with three columns and no controls. Users viewing a target with many incoming CF references can't filter, search, or pivot to "show me other objects that share this same CF link". The panel is also constrained by spec to skip `excluded_custom_fields` and `ui_visible='hidden'` — which is correct UX for a passive panel but wrong for diagnostic / discovery work.

## Goal

Add a minimal detail-page tab `CF Backrefs` to every CF-target object type. Visual baseline mirrors `netbox_custom_objects`'s combined-tabs view (`/opt/netbox-custom-objects/netbox_custom_objects/tab_views.py:169-240`): quick-search input, htmx-paginated table, single per-row filter-icon action. **No** filter sidebar, **no** Configure-Table modal, **no** sortable column headers — by design. The panel stays unchanged.

## Non-goals

- Removing or restyling the existing inline panel.
- Editing CF data from the tab (read-only listing).
- Anything for non-CF relations (FKs, GFKs) — still out of scope.
- A "View all" link on the panel pointing at the tab — deferred.

## Display

A NetBox detail-page tab registered via `@register_model_view(model_class, name="cf_backrefs", path="cf-backrefs")` for every CF-target content type. URL: `/<app>/<model>/<pk>/cf-backrefs/`.

**ViewTab metadata:**
- Label: `CF Backrefs`
- Badge: callable returning `len(refs)` (unfiltered count) or `None` if zero
- Weight: 2000 (sits with other plugin tabs)
- `hide_if_empty=True` — tab not shown in the tab bar when the target has zero inbound CF refs

**Columns (5):**

| # | Column | Render |
|---|---|---|
| 1 | Filter | Filter icon (`mdi mdi-filter`); links to the source model's NetBox list view filtered by the CF that produced this row: `<list-url>?cf_<cfname>=<target_pk>` |
| 2 | Source object | Linkified via `source_object.get_absolute_url()` |
| 3 | Source type | Source model's verbose name |
| 4 | Custom field | `cf.label` (falls back to `cf.name`) |
| 5 | CF type | `Object` or `Multi-object` |

**Header:** `CF Backrefs (N)` where `N` is the unfiltered ref count — always equal to the tab badge. When a quick-search narrows the table, a `Matching X of Y` subtitle appears under the header.

**Quick search:** case-insensitive substring across Source object str repr, Source model label, CF label, CF name. Submitted via `?q=`.

**Sortable columns:** none. All `tables.Column(orderable=False)`. Mirrors `netbox_custom_objects` baseline; sidesteps a previous descending-sort bug.

**Configure Table / per-user column prefs:** removed. The earlier modal didn't persist correctly with our non-model `Reference` rows; users explicitly asked for the simpler view.

**Filter sidebar:** removed. Quick search is the only narrowing UI.

**Pagination:** `EnhancedPaginator` with `orphans=0`. Tab uses NetBox-stock `?page=N` and `?per_page=N` because the URL is dedicated (no sibling paginators on the same URL).

## Permissions

The tab uses the **standard NetBox detail-page tab permission model**: viewing the tab requires the same `view_<parent_model>` permission as viewing the parent object's detail page. No additional restriction (no `is_staff` gate, no separate view-permission). Implemented by subclassing `netbox.views.generic.ObjectView`, which inherits NetBox's `ObjectPermissionRequiredMixin` and enforces `view_<model>` on the parent.

Result: anyone who can already see `/dcim/devices/<pk>/` can also see `/dcim/devices/<pk>/cf-backrefs/`. Users without view permission on the parent get NetBox's standard 403 (or login redirect for anonymous users).

## Data semantics

The tab calls `get_reverse_cf_references(target_obj, apply_visibility_filters=False)` — a new optional kwarg defaulting to `True` so the existing panel keeps its current behavior. With `False`, the function does NOT apply `excluded_custom_fields` and does NOT skip `ui_visible='hidden'` CFs.

**Trade-off (deliberate, user-confirmed):** the tab is the "everything" view, the panel is the curated view. Users who can view the parent object will see hidden / excluded CFs that point to it via this tab. The leak surface is limited to users who already have view permission on the parent — same shape as the panel's existing "no permission filtering on referencing objects" decision (Section "Permissions" in the v0.1.0 panel design). Documented in README.

## Architecture

### File map (additions/edits over v0.1.1)

```
netbox_cf_backrefs/
├── views.py                                      # NEW — _make_tab_view factory + _register_tabs loop
├── tables.py                                     # add CFBackrefTabTable(NetBoxTable)
├── filters.py                                    # NEW — apply_filters(refs, params) helper
├── utils.py                                      # add apply_visibility_filters kwarg + cf_type field on Reference
├── __init__.py                                   # import views in PluginConfig.ready() to trigger registration
├── templates/netbox_cf_backrefs/
│   ├── tab.html                                  # NEW — extends base, renders sidebar + controls + table + paginator
│   └── tab_partial.html                          # NEW — htmx partial: rows + paginator only
└── tests/
    ├── test_filters.py                           # NEW — unit tests for the filter helper
    └── test_tab.py                               # NEW — integration tests for tab rendering, htmx, filter-button link
```

### View shape

```python
@register_model_view(SomeModel, name="cf_backrefs", path="cf-backrefs")
class CFBackrefsTabView(ObjectView):
    queryset = SomeModel.objects.all()
    template_name = "netbox_cf_backrefs/tab.html"
    tab = ViewTab(
        label="CF Backrefs",
        badge=lambda obj: len(list(get_reverse_cf_references(obj, apply_visibility_filters=False))) or None,
        weight=2000,
        hide_if_empty=True,
    )

    def get(self, request, **kwargs):
        # ObjectView.get_object() handles get_object_or_404 + view permission check.
        instance = self.get_object(**kwargs)
        refs = list(get_reverse_cf_references(instance, apply_visibility_filters=False))
        refs = filters.apply_filters(refs, request.GET)
        # sort, paginate (EnhancedPaginator), build table (CFBackrefTabTable)
        if htmx_partial(request):
            return render(request, "netbox_cf_backrefs/tab_partial.html", ctx)
        return render(request, self.template_name, ctx)
```

### Reference dataclass change (additive)

```python
@dataclass(frozen=True)
class Reference:
    source_object: object
    source_model_label: str
    cf_name: str
    cf_label: str
    cf_type: str  # NEW — "object" or "multiobject"
```

`get_reverse_cf_references` populates `cf_type` from `cf.type`. Existing tests build `Reference` only via the function (not directly), so the additive field is safe.

### `apply_visibility_filters` kwarg

```python
def get_reverse_cf_references(
    target_obj,
    *,
    apply_visibility_filters: bool = True,
) -> Iterator[Reference]:
    cfs = CustomField.objects.filter(
        type__in=("object", "multiobject"),
        related_object_type=target_ct,
    ).prefetch_related("object_types")
    if apply_visibility_filters:
        cfs = cfs.exclude(name__in=_excluded_cf_names()).exclude(ui_visible="hidden")
    # ... rest unchanged
```

Default `True` preserves panel behavior. Tab passes `False`.

### Filter-button URL

```python
from django.urls import reverse, NoReverseMatch

def pivot_url(reference, target_pk):
    meta = reference.source_object._meta
    try:
        list_url = reverse(f"{meta.app_label}:{meta.model_name}_list")
    except NoReverseMatch:
        return None  # cell renders disabled filter icon
    return f"{list_url}?cf_{reference.cf_name}={target_pk}"
```

Falls back gracefully when a source model has no `_list` URL (rare; some plugin models). The cell renders the filter icon as a link, or as a disabled `<span>` when URL resolution fails.

### Filter helper

```python
# filters.py
def apply_filters(refs: list[Reference], params) -> list[Reference]:
    source_type = params.get("source_type")
    cf_name = params.get("cf_name")
    cf_type = params.get("cf_type")
    q = (params.get("q") or "").strip().lower()
    out = refs
    if source_type:
        out = [r for r in out if r.source_model_label == source_type]
    if cf_name:
        out = [r for r in out if r.cf_name == cf_name]
    if cf_type:
        out = [r for r in out if r.cf_type == cf_type]
    if q:
        out = [
            r for r in out
            if q in str(r.source_object).lower()
            or q in r.source_model_label.lower()
            or q in r.cf_label.lower()
            or q in r.cf_name.lower()
        ]
    return out
```

Sidebar dropdown options are computed from the unfiltered `refs` list (so they're always relevant — no "Site" option appears if no Site references this target).

### Sort

`?sort=<column>` and `?sort=-<column>` parsed by the view; map to dataclass attributes; in-memory `sorted()`. NetBoxTable's column-header click toggle handles URL generation. No sort-prefix collision concern (the tab has its own URL).

### Tab registration scope

Mirror the panel's discovery loop (`_discover_target_model_labels`) — register a tab on every installed content type (broad net). The tab self-suppresses on objects with zero refs (badge returns `None` + `hide_if_empty=True`). Same trade-off as the panel: simpler than narrowing to actual CF target types; revisit if profiling shows cost.

## Error handling

- **`reverse(...)` for the filter-button URL fails:** render the cell as a disabled span, log debug.
- **CF type filter receives a value not in `{"object", "multiobject"}`:** filter returns `[]`, no error.
- **Pagination with `?page=foo`:** `InvalidPage` → fall back to last page.
- **htmx partial fails:** standard Django 500 surfaces in the htmx response; client falls back to the full page on next click. Don't try to be cleverer.
- **The whole tab view raising:** standard NetBox view-level error handling — let it bubble. Unlike the panel, a 500 in the tab affects only the tab page, not the parent object detail page.

## Testing

### Unit tests (`tests/test_filters.py`)

- Empty params → all refs returned.
- `source_type=device` → only device rows.
- `cf_name=tech_contact` → only that CF's rows.
- `cf_type=multiobject` → only multi-object rows.
- `q=` substring matches across each of the four searchable fields.
- Combined filter + q narrows correctly.

### Integration tests (`tests/test_tab.py`)

- User with `view_device` permission opens `/dcim/devices/<pk>/cf-backrefs/` → 200, response contains expected rows.
- User WITHOUT `view_device` permission opens the URL → 403 (or whatever NetBox returns when `view_<parent>` is missing — `ObjectView` handles this).
- Anonymous user (when `LOGIN_REQUIRED=True`, NetBox default) → 302 redirect to login URL — handled by NetBox's auth middleware.
- Object with zero refs → tab badge returns `None`; tab not in tab bar (server-rendered detail page); direct URL still 200 with empty-state row.
- Filter via querystring (`?source_type=device`) narrows.
- Quick search (`?q=foo`) narrows.
- htmx partial request (header `HX-Request: true`) returns `tab_partial.html` content (no tab chrome, just rows + paginator).
- Filter-button URL contains `cf_<cfname>=<target_pk>` for each row's source list.
- A CF marked `ui_visible='hidden'` IS visible in the tab (asserts the deliberate divergence).
- A CF in `excluded_custom_fields` IS visible in the tab.
- The same hidden / excluded CFs are NOT in the panel (regression test for `apply_visibility_filters=True` default).

### Manual smoke (re-using `cfb-` test data on `/tenancy/contacts/<pk>/`)

- As any user with `view_contact` permission: open Alice → `CF Backrefs` tab visible with badge showing 5 (= 4 panel + 1 excluded). Click → table with 5 rows.
- Click the filter icon on a Device row → navigates to `/dcim/devices/?cf_tech_contact=<alice_pk>` showing the peer Devices.
- Quick search "circuit" → table narrows to circuit rows only.
- Filter sidebar `CF type = Multi-object` → narrows to multi-object refs.
- Configure Table button → modal opens; toggle a column off → table re-renders with that column hidden; pref persists across page refresh.

## Future considerations (out of scope for this release)

- **Make the panel match the tab's visibility scope** (i.e., panel also ignores `excluded_custom_fields` and `ui_visible='hidden'`). User flagged this as a possible future change. Not in this release.

## Open questions

None. All five from the prior plan are resolved (see `~/.claude/plans/rippling-leaping-bachman.md`, "Decisions resolved (final)"). README must clearly disclose: anyone with `view_<parent_model>` permission can see hidden / excluded CFs via the tab.
