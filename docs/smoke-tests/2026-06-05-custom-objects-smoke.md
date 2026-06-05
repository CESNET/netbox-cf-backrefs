# Smoke Test — `netbox_cf_backrefs` × Custom Objects (`netbox_custom_objects`)

**For:** Chrome-extension Claude session with browser control.
**Server:** https://krupa.vm.cesnet.cz/ (logged in as superuser; no re-auth expected).
**Branch under test:** `feat/v0.1-bootstrap` (plugin v0.1.1).
**Goal:** empirically confirm how the plugin's two surfaces — the inline **panel** ("Referenced by Custom Fields") and the **CF Backrefs tab** — behave when a Custom Object (from `netbox_custom_objects`) is the custom-field *target*, both for a type that existed at NetBox startup and for a type created at runtime.

## Verified predictions (this is what "Pass" means)

Static code analysis (adversarially verified) predicts:

| Scenario | Panel | Tab |
|---|---|---|
| **A.** Existing CO type as CF target (`projects` row, seeded) | **present** | **ABSENT** |
| **B.** Newly-created CO type as CF target (no restart) | **ABSENT** | **ABSENT** |
| **C.** Same new type, *after a NetBox restart* (done by the dev, not the browser) | present | ABSENT |

Mechanisms (for your notes, not something to verify in DOM):
- Panel matches by model label with no URL reversal → works for any CO type present at our plugin's startup.
- Tab needs a reversible URL that `netbox_custom_objects` never creates for dynamic `table{id}model`s → `NoReverseMatch` → silently dropped. So the tab is expected ABSENT on **every** Custom Object page.
- Our discovery runs once at startup → a type created at runtime is invisible to both surfaces until a process restart.

**A row counts as a "Pass" when observed behaviour matches the prediction above.** A panel that DOES appear in B, or a tab that DOES appear anywhere, is a Fail (and an interesting one — capture it).

---

Copy everything inside the fenced block into the Chrome session.

````markdown
You are smoke-testing the NetBox plugin `netbox_cf_backrefs` against Custom Objects on https://krupa.vm.cesnet.cz/ (you are logged in as superuser). Two surfaces exist on a custom-field *target* object's detail page:
- PANEL: a full-width card near the bottom titled "Referenced by Custom Fields (N)".
- TAB: a "CF Backrefs" entry in the object's tab strip (next to the main view tab), linking to `.../cf-backrefs/`.

Predictions you are confirming:
- On an EXISTING Custom Object row that is a CF target → PANEL present, TAB absent.
- On a NEWLY-created Custom Object type's row (created during this session, no server restart) that is a CF target → PANEL absent, TAB absent.

Do not try to fix anything. Observe, capture verbatim text / URLs / HTTP status, and report. Part B creates test data prefixed `cfbsmoke` — clean it up at the end (Group Z).

## Group A — Existing Custom Object type as CF target (no data changes)

Seeded data: Custom Object type `projects`, row pk=1, is referenced by a Device `cfb-project-linker` via a NetBox custom field `cfb_project_link` (label likely "Linked project").

A1. Open `/plugins/custom-objects/projects/1/`.
   - Record HTTP status. If the page 404s or the `projects` type / pk=1 no longer exists, mark A1–A3 Skipped and note that, then go to Group B.
   - Confirm the page renders the custom object detail view (you should see the project's fields).

A2. On that page, scroll to the bottom and look for a card titled `Referenced by Custom Fields (N)`.
   - EXPECTED: present, with N ≥ 1.
   - Capture the exact header text (including the count) and the first row's cells (expected: a Device named `cfb-project-linker`, source type `device`, custom field `Linked project` or similar). Paste verbatim.

A3. Look at the TAB STRIP at the top of the same page (the row of tabs near the object's name/title).
   - EXPECTED: there is NO `CF Backrefs` tab.
   - Capture the full list of tab labels you see, left to right, verbatim.
   - Note: because A2 proved at least one backref exists, the tab's badge would be ≥1 — so its absence is NOT due to emptiness; it confirms the tab is dropped. Just record "no CF Backrefs tab present" or, if present, capture its href and whether clicking it 404s.

## Group B — Newly-created Custom Object type as CF target (creates `cfbsmoke` data)

You will create a new Custom Object type, a row, a NetBox custom field targeting it, and set that field on a device — then check the new row's detail page.

B1. Create a Custom Object TYPE.
   - Navigate to the Custom Objects area (nav menu → "Custom Objects" → "Custom Object Types"), or open `/plugins/custom-objects/custom-object-types/`.
   - Click Add. Name it `cfbsmoke target` (let the slug auto-fill, e.g. `cfbsmoke-target`). Add at least one simple field, e.g. a Text field named `title`. Save.
   - Capture: the final detail URL of the created type, and its slug. If the UI shows a model/content-type name like `table<N>model`, capture N.

B2. Create one ROW of that type.
   - From the type's page (or its "Custom Objects" list), click Add object (Add row). Set `title` = `cfbsmoke-row-1`. Save.
   - Capture the row's detail URL (expected shape `/plugins/custom-objects/cfbsmoke-target/<pk>/`) and its pk.

B3. Create a NetBox custom field targeting the new type.
   - Open `/extras/custom-fields/add/`.
   - Name: `cfbsmoke_link`. Type: `Object`. 
   - Related object type: select the new Custom Object type (search `cfbsmoke`). If it does NOT appear in the related-object-type dropdown, capture that fact (it would mean the ObjectType row wasn't created) and continue.
   - Object types (the models this CF applies to / the source side): select `DCIM > Device`.
   - Group name / label: optional. Save.
   - Capture HTTP status and any error. If saving fails or the page 500s, paste the error verbatim and skip to B6 noting B4–B5 could not be set up.

B4. Set the new CF on a device (creates the actual backref).
   - Open a device edit form, e.g. `/dcim/devices/5309/edit/` (cfb-dev-1) — or pick any device and click Edit.
   - In the Custom Fields section find `cfbsmoke_link` (or its label). Use the object picker to select the row `cfbsmoke-row-1`. Save.
   - Capture HTTP status. If the object picker is empty or errors, capture that verbatim.

B5. Confirm the reference is real data.
   - Open the device's detail page (`/dcim/devices/5309/`). In its Custom Fields section, confirm `cfbsmoke_link` shows `cfbsmoke-row-1` as a link. Capture verbatim. (This proves a valid backref now exists pointing at the new CO row.)

B6. THE KEY CHECK — open the new CO row detail page.
   - Open the row URL from B2 (`/plugins/custom-objects/cfbsmoke-target/<pk>/`). Record HTTP status.
   - PANEL: EXPECTED ABSENT. Scroll to the bottom and confirm there is NO `Referenced by Custom Fields` card. Capture: "no panel" or, if a panel IS present, paste its header text verbatim (that would be a Fail — and would mean discovery is not actually startup-frozen).
   - TAB: EXPECTED ABSENT. Capture the tab strip labels verbatim and confirm there is no `CF Backrefs` tab.
   - Interpretation (record this sentence in Notes): "B5 proved a device references this new row, yet B6 shows no panel/tab — confirming the plugin's startup-only discovery did not pick up the runtime-created type."

## Group Z — Cleanup (do this even if some steps failed)

Delete the `cfbsmoke` test data you created, in this order (skip any that don't exist):
Z1. Edit device `/dcim/devices/5309/edit/` → clear the `cfbsmoke_link` value → Save.
Z2. Delete the custom field `cfbsmoke_link` (`/extras/custom-fields/` → find it → Delete).
Z3. Delete the custom object row `cfbsmoke-row-1`.
Z4. Delete the custom object type `cfbsmoke target`.
Confirm each deletion's resulting status. Do NOT touch any `cfb-`, `projects`, or non-`cfbsmoke` data.

## Required output

A markdown table, one row per step:

| Step | Pass/Fail/Skipped | Captured details (verbatim text, URLs, HTTP status) | Notes |

Where Pass = observed behaviour matches the prediction stated at the top.
- A2 Pass = panel present with N≥1. A3 Pass = no CF Backrefs tab.
- B6 Pass = panel absent AND tab absent.
- For B6 explicitly write one of: "panel ABSENT / tab ABSENT (matches prediction)" or "panel PRESENT — header: <verbatim>" / "tab PRESENT — href: <verbatim>".

After the table:
- One-line totals (Pass / Fail / Skipped).
- One short paragraph: any 500s, console errors, or surprises while creating the custom object type / field / setting the device CF (these paths exercise dynamic-model generation and are the most likely to misbehave).

Keep the report under 1000 words.
````

---

## After the browser run (dev-side follow-up, not in the browser)

If Group B confirms the new type shows neither surface, the remaining prediction is the **restart** case: after a NetBox process restart, the same new CO row should gain the panel (tab still absent). That restart can't be done from the browser — ask the dev (Claude Code session) to restart NetBox and re-open the B2 row URL to confirm the panel appears.
