# Smoke Test — `netbox_cf_backrefs` v0.1.1 (CF Backrefs tab + panel)

**For:** Chrome-extension Claude session with browser control.
**Branch under test:** `feat/v0.1-bootstrap` @ `bd2e651` or later.
**Scope:** validates Phase 4 simplifications (no filter sidebar, NetBox-built-in quick search, Actions column last, Configure Table persistence) plus a quick panel regression check.

Copy everything inside the fenced block below into the Chrome session.

````markdown
You are running smoke tests on `netbox_cf_backrefs` v0.1.1. The user is logged in to NetBox at https://krupa.vm.cesnet.cz/ as a superuser; navigation should work without re-auth.

The plugin has TWO surfaces to test:

A. **Inline panel** at the bottom of every CF-target object's detail page — labelled "Referenced by Custom Fields (N)". Honors `excluded_custom_fields` setting + skips `ui_visible='hidden'` CFs. Prefixed query params: `?cfbackrefs_page=N` / `?cfbackrefs_per_page=N` / `?cfbackrefs_sort=col`. Quick regression only.

B. **CF Backrefs tab** at `/<app>/<model>/<pk>/cf-backrefs/`. Recently rebuilt — minimal NetBox-native shape. Expected:
- Single-column layout (NO right-hand filter sidebar).
- Quick search uses NetBox's built-in `inc/table_controls_htmx.html` component: input id `quicksearch`, htmx-live (re-renders on keyup with 500ms delay; no Submit button).
- Configure Table button present at the top-right of the search row (NetBox-stock); clicking opens a two-pane "Available Columns / Selected Columns" modal. Saved column selections must PERSIST across reload.
- NO sortable column headers — clicking them must NOT change `?sort=` and must NOT reorder rows.
- Header `CF Backrefs (N)` where `N` is the unfiltered count and ALWAYS equals the tab badge.
- Narrowing from the quick-search is surfaced by the paginator footer (`Showing 1-N of M`); there is no separate subtitle.
- The URL does NOT push `?q=` on htmx live-search — this matches NetBox's own list views (no `hx-push-url` in the stock include).
- Last column is `Actions` (header text). Each row's action is a single `btn btn-sm btn-primary` filter icon button inside `<span class="btn-group">`. The button links to `/<app>/<model>/?cf_<name>=<target_pk>`.
- htmx swap target id is `object_list` (NetBox-standard).

Active dev config (already set on the server):
- `PLUGINS_CONFIG["netbox_cf_backrefs"]["page_size"] = 2`
- `PLUGINS_CONFIG["netbox_cf_backrefs"]["excluded_custom_fields"] = ["cfb_excluded_contact"]`

Pre-seeded `cfb-` test data:
- Contacts: cfb-alice (PK 5491), cfb-bob (5492), cfb-charlie (5493), cfb-popular (5494, 60 device refs), cfb-multimodel (5495, one ref per model type)
- Tenant target: cfb-target-tenant (PK 6152, referenced by Site + Device via `cfb_tenant_pm`)
- Devices: cfb-dev-1 (5309), cfb-dev-2 (5310), cfb-dev-3 (5311), cfb-dev-page-1..5 (5312-5316), cfb-dev-hidden (5317), cfb-dev-excluded (5318), cfb-pop-01..60 (60 devices), cfb-tenant-target-dev, cfb-project-linker
- Circuit: cfb-circuit-1 (1196)
- Other source rows (multi-model coverage): Site `cfb-mm-site`, Tenant `cfb-mm-tenant`, VLAN `cfb-mm-vlan`, Provider `cfb-mm-provider`, IPAddress `192.0.2.1/32`, VirtualMachine `cfb-mm-vm`, Site `cfb-tenant-target-site`, Device `cfb-project-linker`
- CFs (targets in parens):
  - `cfb_tech_contact` object → Contact (sources: Device, Circuit)
  - `cfb_responsible` multi-object → Contact (Device)
  - `cfb_hidden_contact` object → Contact, `ui_visible='hidden'` (Device)
  - `cfb_excluded_contact` object → Contact, in excluded list (Device)
  - `cfb_site_owner` object → Contact (Site)
  - `cfb_tenant_owner` object → Contact (Tenant)
  - `cfb_vlan_owner` object → Contact (VLAN)
  - `cfb_ip_owner` object → Contact (IPAddress)
  - `cfb_provider_rep` object → Contact (Provider)
  - `cfb_vm_admins` multi-object → Contact (VirtualMachine)
  - `cfb_tenant_pm` object → Tenant (Site, Device)
  - `cfb_project_link` object → Custom Object `projects` row (Device)

Known WIP / non-bug to ignore:
- `/.../?page=N` (no prefix) on a contact page may 500 with `EmptyPage` from `netbox_custom_objects/template_content.py:87`. Separate plugin's bug — don't flag as our failure.

For each scenario: open the URL, observe, capture details. Don't fix; just report.

## Scenarios

### Group 1 — Panel regression (quick)

1. Open `/tenancy/contacts/5491/` (cfb-alice). Confirm panel `Referenced by Custom Fields (4)`. NEITHER `cfb-dev-excluded` NOR `cfb-dev-hidden` appears.
2. Open `/tenancy/contacts/5493/` (cfb-charlie). Confirm panel `Referenced by Custom Fields (5)`, paginator carousel `1 2 3 ›`. Click `›` → URL gains `?cfbackrefs_page=2`.

### Group 2 — Tab structure

3. Open `/tenancy/contacts/5491/cf-backrefs/`.
   - Confirm header `CF Backrefs (6)`.
   - Confirm tab badge in tab bar also `6`.
   - Confirm there is NO right-side `Filters` sidebar.
   - Confirm `Configure Table` button IS present (top-right area of the search row), with `mdi mdi-cog` icon.
   - Capture column headers in left-to-right order. Expected: `Source object | Source type | Custom field | CF type | Actions`.
   - Confirm the `Actions` column is LAST, not first.

4. On the same page, locate the quick-search input above the table.
   - Confirm input has `id="quicksearch"` (NetBox-standard).
   - Confirm there is no separate "Search" submit button — search is htmx-live.
   - Confirm an `mdi mdi-close-circle` clear icon is visible to the right of the input.

5. On the tab, click any column header (e.g., `Source object`).
   - Confirm the URL does NOT gain a `?sort=` parameter.
   - Confirm row order does NOT change.
   - Confirm there are no sort-arrow indicators on the headers.

### Group 3 — Quick search (htmx live)

6. On cfb-alice's tab, type `circuit` into the quick-search input. Wait ~700ms.
   - Confirm the table refreshes WITHOUT a full page reload (htmx swap of `#object_list` only — observable via DevTools Network: a single XHR to the tab URL with `HX-Request: true`, returning a partial).
   - Confirm exactly 1 row appears: `cfb-circuit-1`.
   - Confirm the paginator footer reads `Showing 1-1 of 1` (this is how the narrowing is surfaced — there is no separate subtitle).
   - Note: the URL is NOT expected to gain `?q=circuit` — NetBox's stock live-search component doesn't push state. This matches every other NetBox list view.
   - Click the close-circle icon next to the search input. Confirm input clears AND the table refreshes back to 6 rows.

7. On the tab, type `RESPONSIBLE` (uppercase). Confirm narrows to 1 row (`cfb-dev-1` / Responsible contacts) — case-insensitive.

### Group 4 — Configure Table persistence (the new fix)

8. On cfb-alice's tab, click `Configure Table` (top-right button with cog icon).
   - Confirm a modal opens titled `Table Configuration`.
   - Confirm two-pane layout: `Available columns` on the left, `Selected columns` on the right.
   - Confirm `Selected columns` initially contains: Source object, Source type, Custom field, CF type, Actions (in that order).

9. In the modal, select `CF type` in the Selected pane and click `Remove` (left arrow). `CF type` moves to Available. Click `Save`.
   - Confirm modal closes.
   - Confirm the `CF type` column disappears from the table immediately. Header now reads `Source object | Source type | Custom field | Actions`.

10. **Reload the page (F5).**
    - Confirm the `CF type` column is STILL hidden after reload — preference persisted to `request.user.config['tables.CFBackrefTabTable.columns']`.

11. Re-open `Configure Table`. Move `CF type` back to Selected. Save.
    - Confirm `CF type` reappears in the table.
    - Reload — confirm it stays.

12. (Optional sanity) In the modal, drag `Actions` to the top of the Selected list (or use the "Move Up" button until it's first). Save → reload.
    - Confirm `Actions` is now the first column. (Persists per-user column order, not just visibility.)
    - Restore `Actions` to the last position via Configure Table → Save → reload before continuing.

### Group 5 — Actions column (button family + pivot)

13. On cfb-alice's tab, locate any Device row (e.g., `cfb-dev-1` / Technical contact). Inspect the `Actions` cell HTML.
    - Confirm a wrapping `<span class="btn-group">`.
    - Confirm an `<a>` with `class="btn btn-sm btn-primary"`.
    - Confirm an `<i class="mdi mdi-filter">` icon inside the `<a>`.
    - Confirm `aria-label` and `title` attributes mention "peers".
    - Visually confirm the button matches NetBox's standard small-primary row-action button look.

14. Click the Actions button on the `cfb-dev-1` / Technical contact row.
    - Capture the destination URL. Expected: `/dcim/devices/?cf_cfb_tech_contact=5491`.
    - Confirm the resulting page is the standard NetBox Device list filtered by that CF, listing peer devices.

15. Go back. Click the Actions button on the `cfb-circuit-1` row.
    - Capture URL. Expected: `/circuits/circuits/?cf_cfb_tech_contact=5491`.

### Group 6 — Pagination

16. Open cfb-charlie's tab `/tenancy/contacts/5493/cf-backrefs/`.
    - Default per-page from NetBox settings (typically 50) — all 5 rows fit on one page; no carousel.

17. Open `/tenancy/contacts/5493/cf-backrefs/?per_page=2`.
    - Confirm 2 rows visible.
    - Confirm a paginator at the bottom showing `1 2 3 ›`.
    - Click `›`. Capture URL — should contain `?per_page=2&page=2` (or similar). Confirm new rows appear.

### Group 7 — Tab visibility

18. Find any contact unrelated to `cfb-` (zero CF backrefs). Open it. Confirm there is NO `CF Backrefs` tab in the tab bar (`hide_if_empty=True`). If you can't easily find such a contact, skip.

19. Open `/dcim/devices/5309/` (cfb-dev-1, a CF source). Confirm there is NO `CF Backrefs` tab (devices are CF sources here, not targets).

### Group 8 — Cross-surface consistency

20. Open both cfb-alice's panel (scroll down on `/tenancy/contacts/5491/`) and the CF Backrefs tab in two browser tabs.
    - Panel count = 4. Tab count = 6.
    - Rows in tab but not in panel: BOTH `cfb-dev-excluded` and `cfb-dev-hidden`.
    - This is the load-bearing divergence (tab = "everything" view; panel = curated).

### Group 9 — Real pagination on cfb-popular (60 refs)

21. Open `/tenancy/contacts/5494/` (cfb-popular). Confirm panel header `Referenced by Custom Fields (60)`. Confirm panel paginator shows multiple pages (with `page_size=2`, expect 30 pages).
22. Open `/tenancy/contacts/5494/cf-backrefs/`. Confirm tab header `CF Backrefs (60)`. Confirm tab paginator carousel is rendered (default per_page=50, so expect ~2 pages, e.g., `1 2 ›`).
23. Click the tab paginator's `›`. Confirm URL gains `?page=2`. Confirm a different slice of devices appears.
24. Append `?per_page=10` to the tab URL. Confirm 10 rows visible and a longer paginator (e.g., `1 2 3 4 5 6 ›`). Note: small per_page values (≤5 with very few items) may collapse to one page due to NetBox `EnhancedPaginator`'s `orphans=5` default — that is upstream-standard NetBox behavior, not our bug.

### Group 10 — Cross-model coverage (cfb-multimodel)

25. Open `/tenancy/contacts/5495/cf-backrefs/` (cfb-multimodel).
    - Confirm header `CF Backrefs (6)`.
    - Confirm 6 rows, one per source-model type. Capture each row's `Source type` value. Expected set (in any order): `Site`, `Tenant`, `Vlan`, `Provider`, `Ipaddress`, `Virtualmachine`.
    - Click the Actions filter button on the `Vlan` row. Capture URL. Expected pattern: `/ipam/vlans/?cf_cfb_vlan_owner=5495`.
    - Click the Actions filter button on the `Virtualmachine` row. Expected URL: `/virtualization/virtual-machines/?cf_cfb_vm_admins=5495`.
26. On the same tab, capture the `Custom field` column values across the six rows. Expected set: `Site owner`, `Tenant owner`, `VLAN owner`, `IP owner`, `Provider rep`, `VM admins`.

### Group 11 — Non-Contact target (cfb-target-tenant)

27. Open `/tenancy/tenants/6152/` (cfb-target-tenant). Confirm an inline panel `Referenced by Custom Fields (2)` appears (panel works on Tenant detail pages too, not just Contact).
28. Confirm the two rows: `cfb-tenant-target-site | Site | Tenant PM` and `cfb-tenant-target-dev | Device | Tenant PM`.
29. Open `/tenancy/tenants/6152/cf-backrefs/`. Confirm tab header `CF Backrefs (2)` with the same two rows. Confirm Actions filter buttons work and route to `/dcim/sites/?cf_cfb_tenant_pm=6152` and `/dcim/devices/?cf_cfb_tenant_pm=6152` respectively.

### Group 12 — Custom Object row as a CF target

A CF (`cfb_project_link`) was created with `related_object_type` = the `projects` Custom Object dynamic model (Table68Model). A device `cfb-project-linker` references project pk=1.

30. Open the standard NetBox CF admin to confirm the CF exists: `/extras/custom-fields/?q=cfb_project_link`. Capture the row.
31. Open the project's detail page: `/plugins/custom-objects/projects/1/`. Two checks:
    - Does the project page render at all? (Yes / No / 500.)
    - Does our `CF Backrefs` tab appear in its tab bar?
    - If yes, click it and confirm the device `cfb-project-linker` appears in the table. If no, just record "tab not registered on Custom Object pages" (this is a known limitation — Custom Object detail pages aren't standard NetBox object detail views and may not surface plugin-registered tabs).
32. Open `cfb-project-linker` device detail page (`/dcim/devices/?q=cfb-project-linker` then click into it). Confirm the device's `Custom Fields` section shows `Linked project` with the project name as the value.

### Group 13 — Plugin model coverage

For each of these plugin models, navigate to a sample object's detail page and report whether (a) the standard `Custom Fields` panel appears at all (= the model supports NetBox CFs); (b) our backref panel appears (= it's been targeted by some CF); (c) our `CF Backrefs` tab appears (= it's been targeted by some CF).

| Plugin | Sample object URL | a) supports CFs? | b) panel? | c) tab? |
|---|---|---|---|---|
| netbox_authorized_keys | `/plugins/authorized_keys/keys/` (pick any row) | | | |
| inventory_monitor | `/plugins/inventory-monitor/` (pick any object) | | | |
| netbox_attachments | (not user-facing — attachments live ON other objects) | n/a | n/a | n/a |
| cesnet_service_path_plugin | `/plugins/cesnet-service-path/` (pick any object) | | | |
| netbox_cesnet_services_plugin | `/plugins/cesnet-services/` (pick any object) | | | |
| netbox_rt | `/plugins/netbox-rt/` (pick any object) | | | |
| netbox_custom_objects | `/plugins/custom-objects/projects/1/` | | | |

For each row, fill the three columns with `yes` / `no` / `n/a` and add a Notes column observation. Don't create new CFs — just observe whether the surfaces work on each plugin's existing models given the data we have.

33. Fill in the table above and report it as part of the standard table. (One row per plugin → use one numbered scenario per row to keep the report layout consistent, OR include the table verbatim under #33 with a single Pass/Fail/Skipped verdict for the whole sweep.)

## Required output format

Markdown table — one row per scenario:

| # | Pass/Fail/Skipped | Captured details | Notes |

For "Captured details", include:
- Verbatim text observed (header text, subtitle, button class strings, etc.).
- Final URL after click/navigate (paste query string verbatim).
- HTTP status code where relevant.
- For #10 / #11 (persistence): explicitly state "column was hidden after reload" or "column reappeared after reload — persistence FAILED".

For Pass/Fail:
- **Pass:** observed behaviour matches expectation.
- **Fail:** diverges. Paste exact error message or unexpected text. Don't investigate.
- **Skipped:** explain why.

After the table:
- One-line totals (Pass / Fail / Skipped).
- One paragraph of cross-cutting observations (any DevTools console errors, layout breakage, htmx flicker, anything visual not captured by individual scenarios).

Keep total report under 1500 words. Do not modify any data in NetBox.
````
