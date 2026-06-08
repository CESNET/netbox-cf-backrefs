# TODO — make the CF Backrefs **tab** work on Custom Object detail pages

**Status:** not started · **Effort:** ~M (one new module + ready() wiring + tests) · **Risk:** medium (couples to `netbox_custom_objects` 0.5.1 internals)

The **panel** already works on Custom Object detail pages. The **tab** does not, and never will via `register_model_view` alone. This file is the verified recipe to fix it. Findings are code-cited against **`netbox_custom_objects` 0.5.1** at `/opt/netbox-custom-objects/netbox_custom_objects/` and our own `netbox_cf_backrefs`.

> Empirically confirmed broken via a live browser check: on a Custom Object detail page the backref panel renders, but there is no `cf-backrefs` href anywhere in the tab strip.

---

## Root cause (verified)

A Custom Object's detail page renders its tab strip with `{% plugin_extra_tabs object %}` (`customobject.html:80`). That tag (`templatetags/custom_object_tab_tags.py`):

1. **does** enumerate the global NetBox view registry `registry['views'][app_label][model_name]` for the dynamic model (`table{id}model`) — so our `register_model_view(..., name='cf_backrefs')` ViewTab **is found** and its badge **is rendered** (`custom_object_tab_tags.py:31-42`);
2. computes the href via `get_action_url(instance, action='cf_backrefs', ...)` → `CustomObject._get_action_url` → `reverse('plugins:netbox_custom_objects:customobject_cf_backrefs', kwargs={'custom_object_type': <slug>, 'pk': <pk>})` (`models.py:954-964`);
3. that URL **name does not exist** — `register_model_view` only fills the registry, it never bakes a URL, and `netbox_custom_objects/urls.py` never calls `get_model_urls()` for dynamic models (`get_model_urls` would anyway produce `table{id}model_cf_backrefs`, not `customobject_cf_backrefs` — `utilities/urls.py:44`);
4. so `reverse()` raises `NoReverseMatch`, which is caught at `custom_object_tab_tags.py:44-47` with `continue` → **tab silently dropped**.

**The entire fix = make `plugins:netbox_custom_objects:customobject_cf_backrefs` reversible**, pointed at a slug-resolving view. This is exactly how `netbox_custom_objects` makes its *own* combined "Custom Objects" tab reversible (`_inject_co_urls`, `related_tabs/registry.py:19-45`).

---

## ⚠️ Resolve before coding — scope question

`get_reverse_cf_references` (`utils.py:39-44`) queries `extras.CustomField` rows whose `related_object_type` is the CO row's content type. On a CO page that means **"NetBox extras object/multi-object CFs (on Devices, Sites, …) that point AT this Custom Object row."** That is a real, valid set (e.g. a Device with a NetBox object-CF pointing at this Custom Object row).

It does **not** surface **CO→CO** references stored in `CustomObjectTypeField` FK columns — those are the host plugin's *own* "Custom Objects" tab (`related_tabs/views/combined.py:91-106`), a different reference system.

**Confirm with the maintainer:** "CF Backrefs" on a CO page = extras-CF backrefs (proceed). If CO→CO links were the intent, this plugin is the wrong layer — point users at the host's built-in "Custom Objects" tab and stop here.

Also worth a one-line live check: does any extras `CustomField.related_object_type` in this deployment actually target a `netbox_custom_objects` dynamic model? If users can't/don't create object-CFs pointing at Custom Objects, the CO tab is always empty (`hide_if_empty=True`) and the effort is moot.

---

## Recipe (verified `recipeSound: true`)

Keep all `netbox_custom_objects` coupling isolated in one optional-import module.

1. **`netbox_cf_backrefs/co_tab.py` — slug-resolving view.** Mirror `make_co_combined_view` (`combined.py:570-585`):
   ```python
   class CFBackrefsCOTabView(ConditionalLoginRequiredMixin, View):
       tab = ViewTab(label="CF Backrefs", badge=_badge_for, weight=2000, hide_if_empty=True)
       def get(self, request, custom_object_type, pk, **kwargs):
           from netbox_custom_objects.models import CustomObjectType
           cot = get_object_or_404(CustomObjectType, slug=custom_object_type)
           model = cot.get_model()                       # same call the host's combined view uses
           instance = get_object_or_404(model.objects.restrict(request.user, "view"), pk=pk)
           return _render_cf_backrefs_tab(request, instance, self.tab)
   ```
   (`from utilities.views import ConditionalLoginRequiredMixin, ViewTab`; `from django.views.generic import View`.) It differs from the built-in `_make_tab_view` (`views.py:28`) only in that it cannot bind a fixed `model_class` — it resolves the dynamic model per request.

2. **Extract the shared body.** Refactor `views.py:40-64` into a module-level `_render_cf_backrefs_tab(request, instance, tab)` so the built-in `_CFBackrefsTabView` and `CFBackrefsCOTabView` produce byte-identical output (analogue of the host's shared `_render_combined_tab`, `combined.py:419`). **Behavior-preserving** — the existing `tests/test_tab.py` tenancy cases are the regression net. The helper must not assume `ObjectView.get_object`.

3. **Inject the URL** (in `co_tab.py`), copied structurally from `registry.py:19-45`, **idempotent**:
   ```python
   def _inject_co_cf_backrefs_url():
       try:
           import netbox_custom_objects.urls as co_urls
           from django.urls import path as url_path
       except ImportError:
           return
       if any(getattr(p, "name", None) == "customobject_cf_backrefs" for p in co_urls.urlpatterns):
           return
       co_urls.urlpatterns.append(url_path(
           "<str:custom_object_type>/<int:pk>/cf-backrefs/",
           CFBackrefsCOTabView.as_view(),
           name="customobject_cf_backrefs",   # ← load-bearing: must equal CustomObject._get_viewname('cf_backrefs')
       ))
   ```
   The name `customobject_cf_backrefs` and the `<str:custom_object_type>/<int:pk>` kwargs are exact requirements (see Root cause #2).

4. **Wire into `ready()`** (`__init__.py:21-25`), after `from . import views`:
   ```python
   from . import co_tab
   co_tab._inject_co_cf_backrefs_url()
   from django.urls import clear_url_caches
   clear_url_caches()
   ```

5. **Keep the existing dynamic-model `register_model_view`** (`views.py:88`). Once the URL is reversible, the strip renders the tab from that registry entry's `ViewTab` (badge/label) while the **href routes through the injected slug-resolving view** — the two are complementary. `_badge_for` (`views.py:23-25`) already works on CO rows (the dynamic model has a ContentType).

---

## 🔴 Critical constraints the verify pass flagged (do not skip)

- **(A) Fails closed on plugin load order — make it loud.** The whole fix silently no-ops if `netbox_cf_backrefs` ever loads *before* `netbox_custom_objects`. Reason: the dynamic `table{id}model` is only added to `apps.all_models` by the host's eager Pass-1 `get_model()` at *its* `ready()` (`netbox_custom_objects/__init__.py:359-360`); our `_register_tabs()` skips any ContentType whose `model_class()` is `None` (`views.py:85-86`). Today PLUGINS order (`configuration.py:232-233`) puts `netbox_custom_objects` first, so it works — but that's implicit. **Add a startup check:** if `netbox_custom_objects` isn't in `INSTALLED_APPS` / its app isn't ready, log a WARNING and skip CO-tab wiring cleanly. Document the required PLUGINS order in the README.
- **(B) `clear_url_caches()` after our append is mandatory, not belt-and-suspenders.** The host already called `clear_url_caches()` at `registry.py:140` *before* our pattern exists. Without our own call after the append, an earlier `resolve()` may have cached the resolver without our route → unreachable until restart.
- **(C) Guard `_register_tabs()` against dev-autoreload double-registration.** `register_model_view` appends unconditionally with no dedup (`utilities/views.py:378-387`); a re-import would render two identical "CF Backrefs" `<li>`s. Add a name-guard / dedup by `config['name']` per `(app_label, model_name)`.

---

## Tests (`tests/test_tab.py`) — note the test-runner gotcha

Under the default NetBox test runner, `should_skip_dynamic_model_creation()` returns `True` (`netbox_custom_objects/__init__.py:248-253`), so dynamic models are **not** generated and the strip has no registry entry to enumerate. Therefore:

- **Do** add a `@skipIf(not installed)` test that (1) creates a `CustomObjectType` + row, (2) creates an extras object-CF on Device targeting that COT + a Device referencing the row, (3) asserts `reverse('plugins:netbox_custom_objects:customobject_cf_backrefs', kwargs={'custom_object_type': cot.slug, 'pk': co.pk})` resolves — the `NoReverseMatch` regression guard — and (4) GETs that URL as a user with view perm and asserts 200 + the Device appears.
- **Force dynamic-model availability** in setUp (e.g. monkeypatch the host's `_app_ready=True` and call `cot.get_model()`) if you want to assert the strip actually renders the nav-link; otherwise **drop** that assertion — it's not exercisable under the default runner.
- **Keep** the existing built-in `tenancy:contact_cf_backrefs` cases unchanged as the must-not-regress guard for the shared-body refactor.
- **Add** a permission test: an unprivileged user is filtered/403'd on the CO tab. `CustomObject` uses `RestrictedQuerySet.as_manager()` (`models.py:610`) so `.restrict(user, 'view')` exists; prefer the host's defensive `_restrict_or_warn` pattern (`combined.py:42-55`) over a bare `.restrict`.

---

## Risks

- **Version coupling** to four undocumented `netbox_custom_objects` internals: the `netbox_custom_objects.urls` module + mutable `urlpatterns`, the `customobject_<action>` viewname convention (`models.py:954-964`), `CustomObjectType.get_model()`, and the strip's `plugin_extra_tabs` registry enumeration. Any upstream rename → silent `NoReverseMatch` (tab disappears). Pin/test against 0.5.1; log when injection is skipped.
- **Stale dynamic model:** a COT deleted after startup leaves a stale registry entry whose `queryset = Table{id}Model.objects.all()` references a dropped table. The user-facing href routes through the slug-resolving view (404s cleanly via `get_object_or_404(CustomObjectType, …)`); just make sure the **badge** computation can't 500 — wrap `_badge_for` in try/except like the panel does.
- **Dual-tab:** don't also add a competing template tag (see alternative below) or the page shows two "CF Backrefs" tabs. Pick one rendering path (the host's existing `plugin_extra_tabs` enumeration).

---

## Alternatives considered

1. **Drop the tab on CO pages; rely on the panel** (which already renders there). Zero coupling, zero `NoReverseMatch` surface. **The correct zero-risk ship if tab fidelity isn't required** — the panel already shows the same data. *(Recommended fallback.)*
2. **Standalone (non-tab) view** at our own plugin URL, linked from the panel header. Avoids mutating `netbox_custom_objects.urls`, but cannot appear in the CO tab strip (the strip only reverses `customobject_<action>` names) → second-class link, not a tab.
3. **Upstream a public `register_co_tab(name, path, view_factory)` hook** into `netbox_custom_objects`. The correct long-term fix (eliminates all coupling), but needs an upstream release + version floor. **File this regardless**; gate our injection behind a version check so a future upstream rename fails *loud* (logged), not silent.
4. **Monkeypatch `CustomObject._get_action_url` / the strip.** Strictly worse than appending one named route; re-breaks on every upstream change to `models.py:954-964`.

---

## Open questions

- Scope confirmation (extras-CF backrefs vs CO→CO) — see the ⚠️ section above. **Blocking.**
- Is depending on `netbox_custom_objects` 0.5.1 internals acceptable for a release, or should the CO-page tab be feature-flagged off by default and documented as best-effort?
- Live `runserver` checks (couldn't run Django headless): (a) `reverse(...customobject_cf_backrefs...)` actually resolves after injection + `clear_url_caches()`; (b) the dynamic model's manager exposes `.restrict(user, 'view')` (static analysis says yes).
- Should we add `[project.optional-dependencies] custom-objects = ["netbox-custom-objects>=0.5.1"]` in `pyproject.toml` (NOT a hard dep — the `ImportError` guard keeps the plugin working without it)?
