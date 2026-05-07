# CF Backrefs Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-object detail-page tab `CF Backrefs` to the `netbox_cf_backrefs` plugin with the full NetBox list-view chrome (filter sidebar, quick search, Configure Table modal, per-user column prefs, htmx-paginated table, per-row filter-button pivot). Panel stays unchanged.

**Architecture:** Subclass `netbox.views.generic.ObjectView`, register via `@register_model_view` for every CF target type at module import. The view fetches `list[Reference]` from `get_reverse_cf_references(obj, apply_visibility_filters=False)`, filters/sorts in Python, paginates with `EnhancedPaginator`, and renders via `CFBackrefTabTable(NetBoxTable)`. htmx partial branch for re-renders on filter/search/pagination.

**Tech Stack:** NetBox 4.5+ plugin APIs (`register_model_view`, `ViewTab`, `ObjectView`, `NetBoxTable`, `EnhancedPaginator`), `django_tables2`, `htmx`, Python 3.12+.

**Spec:** `docs/superpowers/specs/2026-05-07-cf-backrefs-tab-design.md`

**Working directory:** `/opt/netbox_custom_fields_object_display_plugin/`
**Branch:** `feat/v0.1-bootstrap` (already checked out)
**Test runner:** `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb`
**Lint:** `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs` + `/opt/netbox/venv/bin/python -m djlint netbox_cf_backrefs/templates --check`
**Reinstall after `__init__.py` changes:** `cd /opt/netbox_custom_fields_object_display_plugin && /opt/netbox/venv/bin/pip install -e .`

---

## File map

```
netbox_cf_backrefs/
├── __init__.py                                  # MODIFY — import views in PluginConfig.ready()
├── utils.py                                     # MODIFY — Reference.cf_type field; apply_visibility_filters kwarg
├── filters.py                                   # NEW — apply_filters(refs, params) helper
├── tables.py                                    # MODIFY — add CFBackrefTabTable(NetBoxTable)
├── views.py                                     # NEW — _make_tab_view + _register_tabs
├── templates/netbox_cf_backrefs/
│   ├── tab.html                                 # NEW
│   └── tab_partial.html                         # NEW
└── tests/
    ├── test_filters.py                          # NEW — unit tests for apply_filters
    ├── test_tab.py                              # NEW — integration tests for tab rendering
    └── test_utils.py                            # MODIFY — extend assertions for cf_type and visibility kwarg
CHANGELOG.md                                     # MODIFY — append bullet under ## 0.1.1
README.md                                        # MODIFY — document tab
```

---

## Task 1: Add `cf_type` field to `Reference` dataclass

**Files:**
- Modify: `netbox_cf_backrefs/utils.py`
- Modify: `netbox_cf_backrefs/tests/test_utils.py`

- [ ] **Step 1: Extend an existing test in `tests/test_utils.py` to assert `cf_type`**

In `test_object_cf_returns_only_matching_source`, after the existing assertions, append:

```python
        self.assertEqual(ref.cf_type, "object")
```

In `test_multiobject_cf_matches_when_pk_in_list`, after the existing assertions, append:

```python
        self.assertEqual(refs[0].cf_type, "multiobject")
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: `AttributeError: 'Reference' object has no attribute 'cf_type'`

- [ ] **Step 3: Add `cf_type` field to `Reference` and populate it**

In `netbox_cf_backrefs/utils.py`, replace the `Reference` definition:

```python
@dataclass(frozen=True)
class Reference:
    source_object: object
    source_model_label: str
    cf_name: str
    cf_label: str
    cf_type: str
```

In the same file, find the `yield Reference(...)` call inside `get_reverse_cf_references` and add `cf_type=cf.type`:

```python
            for src in source_model.objects.filter(**lookup):
                yield Reference(
                    source_object=src,
                    source_model_label=source_ct.model,
                    cf_name=cf.name,
                    cf_label=cf_label,
                    cf_type=cf.type,
                )
```

- [ ] **Step 4: Run test — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK, all utils tests pass.

- [ ] **Step 5: Run ruff**

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/test_utils.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat(utils): add cf_type field to Reference dataclass"
```

---

## Task 2: Add `apply_visibility_filters` kwarg to `get_reverse_cf_references`

The kwarg defaults to `True` so existing behavior (panel) is preserved. With `False`, the function does NOT exclude `excluded_custom_fields` CFs and does NOT skip `ui_visible='hidden'`.

**Files:**
- Modify: `netbox_cf_backrefs/utils.py`
- Modify: `netbox_cf_backrefs/tests/test_utils.py`

- [ ] **Step 1: Append the failing test to `GetReverseCFReferencesTests` in `tests/test_utils.py`**

```python
    def test_apply_visibility_filters_false_returns_hidden_and_excluded(self):
        from django.test import override_settings

        # Hidden CF that the panel-style call would skip
        make_cf(
            name="hidden_link",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
            ui_visible="hidden",
        )
        # Excluded CF (also panel-skipped)
        make_cf(
            name="excluded_link",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        self._make_device(
            "dev-hidden-and-excluded",
            {"hidden_link": self.target_a.pk, "excluded_link": self.target_a.pk},
        )

        with override_settings(
            PLUGINS_CONFIG={
                "netbox_cf_backrefs": {
                    "page_size": 50,
                    "excluded_custom_fields": ["excluded_link"],
                }
            }
        ):
            filtered = list(
                get_reverse_cf_references(self.target_a, apply_visibility_filters=True)
            )
            unfiltered = list(
                get_reverse_cf_references(self.target_a, apply_visibility_filters=False)
            )

        filtered_names = {r.cf_name for r in filtered}
        unfiltered_names = {r.cf_name for r in unfiltered}

        # filtered: panel behavior — both hidden and excluded suppressed
        self.assertNotIn("hidden_link", filtered_names)
        self.assertNotIn("excluded_link", filtered_names)
        # unfiltered: tab behavior — both surface
        self.assertIn("hidden_link", unfiltered_names)
        self.assertIn("excluded_link", unfiltered_names)
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils.GetReverseCFReferencesTests.test_apply_visibility_filters_false_returns_hidden_and_excluded -v 2 --keepdb`
Expected: `TypeError: get_reverse_cf_references() got an unexpected keyword argument 'apply_visibility_filters'`

- [ ] **Step 3: Add the kwarg to `get_reverse_cf_references`**

In `netbox_cf_backrefs/utils.py`, change the function signature and the queryset construction:

```python
def get_reverse_cf_references(
    target_obj,
    *,
    apply_visibility_filters: bool = True,
) -> Iterator[Reference]:
    """Yield Reference rows for every object/multi-object CF pointing to `target_obj`.

    With `apply_visibility_filters=True` (default) skips CFs whose name is in
    `excluded_custom_fields` and CFs marked `ui_visible='hidden'`. The tab view
    passes `False` to surface the unfiltered set.
    """
    target_ct = ContentType.objects.get_for_model(target_obj)

    cfs = CustomField.objects.filter(
        type__in=("object", "multiobject"),
        related_object_type=target_ct,
    ).prefetch_related("object_types")
    if apply_visibility_filters:
        cfs = cfs.exclude(name__in=_excluded_cf_names()).exclude(ui_visible="hidden")

    for cf in cfs:
```

(The rest of the function body — `for cf in cfs:` loop — is unchanged.)

- [ ] **Step 4: Run all utils tests — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK, all tests pass (the new one + all existing).

- [ ] **Step 5: Run ruff**

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/test_utils.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat(utils): add apply_visibility_filters kwarg for tab view"
```

---

## Task 3: Implement `filters.apply_filters` helper

Pure-Python filtering over `list[Reference]`. No Django FilterSet (data is in-memory dataclasses, not a QuerySet).

**Files:**
- Create: `netbox_cf_backrefs/filters.py`
- Create: `netbox_cf_backrefs/tests/test_filters.py`

- [ ] **Step 1: Write the failing tests in `netbox_cf_backrefs/tests/test_filters.py`**

```python
from django.test import SimpleTestCase

from netbox_cf_backrefs.filters import apply_filters
from netbox_cf_backrefs.utils import Reference


class _FakeObject:
    """Minimal stand-in for a NetBox model instance — only str() is needed."""

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return self._name


def _ref(name, model="device", cf_name="tech_contact", cf_label="Technical contact",
         cf_type="object"):
    return Reference(
        source_object=_FakeObject(name),
        source_model_label=model,
        cf_name=cf_name,
        cf_label=cf_label,
        cf_type=cf_type,
    )


class ApplyFiltersTests(SimpleTestCase):
    def setUp(self):
        self.refs = [
            _ref("dev-1", model="device", cf_name="tech_contact",
                 cf_label="Technical contact", cf_type="object"),
            _ref("dev-2", model="device", cf_name="responsible",
                 cf_label="Responsible contacts", cf_type="multiobject"),
            _ref("circuit-1", model="circuit", cf_name="tech_contact",
                 cf_label="Technical contact", cf_type="object"),
        ]

    def test_empty_params_returns_all(self):
        self.assertEqual(apply_filters(self.refs, {}), self.refs)

    def test_filter_by_source_type(self):
        result = apply_filters(self.refs, {"source_type": "device"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1", "dev-2"])

    def test_filter_by_cf_name(self):
        result = apply_filters(self.refs, {"cf_name": "tech_contact"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1", "circuit-1"])

    def test_filter_by_cf_type(self):
        result = apply_filters(self.refs, {"cf_type": "multiobject"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-2"])

    def test_quick_search_matches_source_object_name(self):
        result = apply_filters(self.refs, {"q": "circuit"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["circuit-1"])

    def test_quick_search_matches_cf_label_case_insensitive(self):
        result = apply_filters(self.refs, {"q": "RESPONSIBLE"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-2"])

    def test_quick_search_matches_source_model_label(self):
        result = apply_filters(self.refs, {"q": "device"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1", "dev-2"])

    def test_quick_search_matches_cf_name(self):
        result = apply_filters(self.refs, {"q": "responsible"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-2"])

    def test_combined_filter_and_q(self):
        result = apply_filters(
            self.refs, {"source_type": "device", "q": "tech"}
        )
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1"])

    def test_unknown_filter_value_returns_empty(self):
        result = apply_filters(self.refs, {"source_type": "vlan"})
        self.assertEqual(result, [])
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_filters -v 2 --keepdb`
Expected: `ModuleNotFoundError: No module named 'netbox_cf_backrefs.filters'`

- [ ] **Step 3: Implement `netbox_cf_backrefs/filters.py`**

```python
"""In-memory filtering helpers for the CF Backrefs tab.

Operates on `list[Reference]` (frozen dataclasses) — not a Django QuerySet —
so this is plain Python, not a `django_filters.FilterSet`.
"""
from .utils import Reference


def apply_filters(refs: list[Reference], params) -> list[Reference]:
    """Narrow `refs` by sidebar filters and quick search.

    Recognized keys in `params` (a dict-like, e.g. `request.GET`):
    - `source_type`: exact match against `Reference.source_model_label`
    - `cf_name`: exact match against `Reference.cf_name`
    - `cf_type`: exact match against `Reference.cf_type`
    - `q`: case-insensitive substring across source object str repr,
      source model label, CF label, and CF name
    """
    source_type = params.get("source_type")
    cf_name = params.get("cf_name")
    cf_type = params.get("cf_type")
    q = (params.get("q") or "").strip().lower()

    out = list(refs)
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

- [ ] **Step 4: Run tests — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_filters -v 2 --keepdb`
Expected: OK, 10 tests pass.

- [ ] **Step 5: Run ruff**

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add netbox_cf_backrefs/filters.py netbox_cf_backrefs/tests/test_filters.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat(filters): add in-memory apply_filters helper"
```

---

## Task 4: Add `CFBackrefTabTable(NetBoxTable)` with filter-icon column

The tab table is separate from the panel's `CFBackrefTable` so the panel keeps working unchanged. NetBoxTable activates Configure-Table modal + per-user column prefs.

**Files:**
- Modify: `netbox_cf_backrefs/tables.py`

(No table-level unit test in this task — table behavior is verified in the integration tests in Task 5+.)

- [ ] **Step 1: Append `CFBackrefTabTable` and a small URL helper to `netbox_cf_backrefs/tables.py`**

At the top of the file, replace the import block to also pull `format_html`, `mark_safe`, `reverse`, `NoReverseMatch`, and `NetBoxTable`:

```python
"""django_tables2 tables for the CF Backrefs panel and tab."""
import django_tables2 as tables
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from netbox.tables import NetBoxTable
```

Keep the existing `CFBackrefTable(tables.Table)` class as-is. Append at the bottom:

```python
def _peer_list_url(reference, target_pk):
    """Build the source-model list URL filtered by the CF that produced this row.

    Returns None if the source model has no NetBox `<app>:<model>_list` URL.
    """
    meta = reference.source_object._meta
    try:
        list_url = reverse(f"{meta.app_label}:{meta.model_name}_list")
    except NoReverseMatch:
        return None
    return f"{list_url}?cf_{reference.cf_name}={target_pk}"


class CFBackrefTabTable(NetBoxTable):
    """Full list-view-style table used by the CF Backrefs tab.

    Subclasses NetBoxTable so the Configure-Table modal and per-user column
    prefs work. The leading `pivot` column renders the per-row filter icon.
    """

    pivot = tables.Column(
        empty_values=(),
        verbose_name="",
        orderable=False,
    )
    source_object = tables.Column(
        linkify=True,
        verbose_name=_("Source object"),
    )
    source_model_label = tables.Column(verbose_name=_("Source type"))
    cf_label = tables.Column(verbose_name=_("Custom field"))
    cf_type = tables.Column(verbose_name=_("CF type"))

    actions = None

    class Meta(NetBoxTable.Meta):
        attrs = {"class": "table table-hover object-list"}
        empty_text = _("No references")
        fields = ("pivot", "source_object", "source_model_label", "cf_label", "cf_type")
        default_columns = (
            "pivot", "source_object", "source_model_label", "cf_label", "cf_type",
        )

    def __init__(self, *args, target_pk=None, **kwargs):
        self._target_pk = target_pk
        super().__init__(*args, **kwargs)

    def render_pivot(self, record):
        url = _peer_list_url(record, self._target_pk)
        if url is None:
            return mark_safe('<span class="text-muted"><i class="mdi mdi-filter"></i></span>')
        return format_html(
            '<a href="{}" title="Show peers"><i class="mdi mdi-filter"></i></a>', url
        )

    def render_source_model_label(self, value):
        return value.capitalize()

    def render_cf_type(self, value):
        return {"object": "Object", "multiobject": "Multi-object"}.get(value, value)
```

- [ ] **Step 2: Run ruff to confirm imports are clean**

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

- [ ] **Step 3: Run existing test suite — verify nothing regresses**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb`
Expected: OK, all existing tests still pass (the new table is unused so far).

- [ ] **Step 4: Commit**

```bash
git add netbox_cf_backrefs/tables.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat(tables): add CFBackrefTabTable(NetBoxTable) with filter-icon pivot column"
```

---

## Task 5: Register the tab view + `tab.html` template + integration tests for permissions and rendering

This is the largest task: it produces a clickable, working tab. Subsequent tasks add htmx, Configure-Table, and docs.

**Files:**
- Create: `netbox_cf_backrefs/views.py`
- Create: `netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html`
- Create: `netbox_cf_backrefs/templates/netbox_cf_backrefs/tab_partial.html`
- Create: `netbox_cf_backrefs/tests/test_tab.py`
- Modify: `netbox_cf_backrefs/__init__.py`

- [ ] **Step 1: Write the failing integration tests in `netbox_cf_backrefs/tests/test_tab.py`**

```python
from core.models import ObjectType
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from django.contrib.auth import get_user_model
from django.urls import reverse
from tenancy.models import Contact
from users.models import ObjectPermission
from utilities.testing import TestCase

from ._factories import make_cf


class CFBackrefsTabRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff_user = User.objects.create_user("staff_u", password="p")
        cls.staff_user.is_superuser = True
        cls.staff_user.save()

        cls.unprivileged_user = User.objects.create_user("plain_u", password="p")

        cls.site = Site.objects.create(name="S1", slug="s1")
        manufacturer = Manufacturer.objects.create(name="M1", slug="m1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="DT1", slug="dt1"
        )
        cls.role = DeviceRole.objects.create(name="R1", slug="r1")
        cls.contact = Contact.objects.create(name="cfbtab-bob")

        make_cf(
            name="tech_contact",
            label="Technical contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        cls.device = Device.objects.create(
            name="cfbtab-dev-1",
            site=cls.site,
            device_type=cls.device_type,
            role=cls.role,
            custom_field_data={"tech_contact": cls.contact.pk},
        )
        cls.tab_url = reverse("tenancy:contact_cf_backrefs", args=[cls.contact.pk])

    def _grant_view_contact(self, user):
        perm = ObjectPermission.objects.create(name="view-contact", actions=["view"])
        perm.users.add(user)
        perm.object_types.add(ObjectType.objects.get_for_model(Contact))

    def test_user_with_view_contact_permission_gets_200(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("CF Backrefs", body)
        self.assertIn(self.device.get_absolute_url(), body)
        self.assertIn("Technical contact", body)

    def test_user_without_view_contact_permission_gets_forbidden(self):
        # No grant — user has no object permissions at all.
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        self.assertEqual(response.status_code, 403)

    def test_filter_button_url_contains_cf_filter(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.tab_url)
        body = response.content.decode()
        # Filter-button cell links to the source model's list view filtered by
        # the CF that produced this row.
        expected = f"/dcim/devices/?cf_tech_contact={self.contact.pk}"
        self.assertIn(expected, body)
        self.assertIn("mdi-filter", body)

    def test_anonymous_user_redirected_or_forbidden(self):
        # Default NetBox config has LOGIN_REQUIRED=True. We accept either 302
        # (redirect to login) or 403 — both are acceptable "not allowed" states.
        response = self.client.get(self.tab_url)
        self.assertIn(response.status_code, (302, 403))
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab -v 2 --keepdb`
Expected: `NoReverseMatch: Reverse for 'contact_cf_backrefs' not found.` (the URL doesn't exist yet)

- [ ] **Step 3: Create `netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html`**

```html
{% extends 'generic/object.html' %}
{% load render_table from django_tables2 %}
{% load i18n %}

{% block content %}
  <div class="row">
    <div class="col col-md-12">
      <div class="card">
        <h5 class="card-header">{% trans 'CF Backrefs' %} ({{ total }})</h5>
        <div id="cf-backrefs-table"
             hx-target="this"
             hx-select="#cf-backrefs-table"
             hx-swap="outerHTML">
          <div class="table-responsive">{% render_table table 'inc/table.html' %}</div>
          {% include 'inc/paginator.html' with paginator=table.paginator page=table.page %}
        </div>
      </div>
    </div>
  </div>
{% endblock content %}
```

- [ ] **Step 4: Create `netbox_cf_backrefs/templates/netbox_cf_backrefs/tab_partial.html`**

```html
{% load render_table from django_tables2 %}
<div id="cf-backrefs-table"
     hx-target="this"
     hx-select="#cf-backrefs-table"
     hx-swap="outerHTML">
  <div class="table-responsive">{% render_table table 'inc/table.html' %}</div>
  {% include 'inc/paginator.html' with paginator=table.paginator page=table.page %}
</div>
```

- [ ] **Step 5: Create `netbox_cf_backrefs/views.py`**

```python
"""Per-CF-target detail-page tabs.

For every NetBox model that is currently a CF target, register a per-object
tab via `register_model_view`. Each tab subclasses `ObjectView` so it inherits
NetBox's standard `view_<parent_model>` permission check.
"""
import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import InvalidPage
from django.shortcuts import render
from django_tables2 import RequestConfig
from netbox.views.generic import ObjectView
from utilities.htmx import htmx_partial
from utilities.paginator import EnhancedPaginator
from utilities.views import ViewTab, register_model_view

from .filters import apply_filters
from .tables import CFBackrefTabTable
from .utils import get_reverse_cf_references

logger = logging.getLogger("netbox_cf_backrefs")


def _badge_for(obj):
    count = sum(1 for _ in get_reverse_cf_references(obj, apply_visibility_filters=False))
    return count or None


def _make_tab_view(model_class):
    class _CFBackrefsTabView(ObjectView):
        queryset = model_class.objects.all()
        template_name = "netbox_cf_backrefs/tab.html"
        partial_template_name = "netbox_cf_backrefs/tab_partial.html"
        tab = ViewTab(
            label="CF Backrefs",
            badge=_badge_for,
            weight=2000,
            hide_if_empty=True,
        )

        def get(self, request, **kwargs):
            instance = self.get_object(**kwargs)
            refs = list(get_reverse_cf_references(instance, apply_visibility_filters=False))
            filtered = apply_filters(refs, request.GET)

            table = CFBackrefTabTable(filtered, target_pk=instance.pk)
            try:
                RequestConfig(request, paginate={
                    "paginator_class": EnhancedPaginator,
                    "per_page": int(request.GET.get("per_page", 50) or 50),
                    "orphans": 0,
                }).configure(table)
            except (InvalidPage, ValueError):
                RequestConfig(request, paginate={
                    "paginator_class": EnhancedPaginator,
                    "per_page": 50,
                    "orphans": 0,
                }).configure(table)

            ctx = {
                "object": instance,
                "tab": self.tab,
                "table": table,
                "total": len(filtered),
                "all_refs": refs,
            }
            template = self.partial_template_name if htmx_partial(request) else self.template_name
            return render(request, template, ctx)

    _CFBackrefsTabView.__name__ = f"CFBackrefsTabView_{model_class._meta.app_label}_{model_class._meta.model_name}"
    return _CFBackrefsTabView


def _register_tabs():
    """Register one ObjectView+tab per installed content type at import time."""
    for ct in ContentType.objects.all():
        if not apps.is_installed(ct.app_label):
            continue
        try:
            model_class = ct.model_class()
        except Exception:
            continue
        if model_class is None:
            continue
        view_cls = _make_tab_view(model_class)
        register_model_view(model_class, name="cf_backrefs", path="cf-backrefs")(view_cls)


_register_tabs()
```

- [ ] **Step 6: Trigger view registration from `PluginConfig.ready()` in `netbox_cf_backrefs/__init__.py`**

Add a `ready()` method on the `NetBoxCFBackrefsConfig` class. The full file becomes:

```python
from netbox.plugins import PluginConfig

from .version import __version__


class NetBoxCFBackrefsConfig(PluginConfig):
    name = "netbox_cf_backrefs"
    verbose_name = "NetBox Custom Field Backrefs"
    description = "Show reverse references from object / multi-object custom fields on the target object's detail page."
    version = __version__
    author = "Jan Krupa"
    author_email = "jan.krupa@cesnet.cz"
    base_url = "cf-backrefs"
    min_version = "4.5.0"
    max_version = "4.6.99"
    default_settings = {
        "page_size": 50,
        "excluded_custom_fields": [],
    }

    def ready(self):
        super().ready()
        # Importing the views module triggers register_model_view for each
        # installed content type. Same import-time pattern as template_content.
        from . import views  # noqa: F401


config = NetBoxCFBackrefsConfig
```

- [ ] **Step 7: Reinstall the plugin so NetBox picks up the new module**

Run: `cd /opt/netbox_custom_fields_object_display_plugin && /opt/netbox/venv/bin/pip install -e .`
Expected: `Successfully installed netbox-cf-backrefs-0.1.1`

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 8: Run the integration tests — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab -v 2 --keepdb`
Expected: OK, 4 tests pass.

If `test_user_with_view_contact_permission_gets_200` fails because the URL name differs from `tenancy:contact_cf_backrefs`, run this in a Django shell to discover the actual name and update the test:

```python
from django.urls import get_resolver
[u for u in get_resolver().reverse_dict.keys() if isinstance(u, str) and "cf_backrefs" in u and "contact" in u]
```

- [ ] **Step 9: Run the full test suite + lint**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb`
Expected: OK across all tests (utils + filters + tab).

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

Run: `/opt/netbox/venv/bin/python -m djlint netbox_cf_backrefs/templates --check`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add netbox_cf_backrefs/views.py netbox_cf_backrefs/__init__.py netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html netbox_cf_backrefs/templates/netbox_cf_backrefs/tab_partial.html netbox_cf_backrefs/tests/test_tab.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat: add CF Backrefs detail-page tab via register_model_view"
```

---

## Task 6: Verify htmx partial rendering

Task 5 already wired `htmx_partial(request)` and shipped both templates. This task adds an integration test that confirms the partial returns rows-only markup (no parent layout chrome).

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_tab.py`

- [ ] **Step 1: Append the test inside `CFBackrefsTabRenderingTests`**

```python
    def test_htmx_partial_returns_rows_only(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        # Partial does NOT include the parent layout chrome.
        self.assertNotIn('<html', body)
        # Partial DOES include the rows + paginator wrapper.
        self.assertIn('id="cf-backrefs-table"', body)
        self.assertIn(self.device.get_absolute_url(), body)

    def test_full_response_wraps_table_in_swap_target(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        body = response.content.decode()
        self.assertIn('id="cf-backrefs-table"', body)
```

- [ ] **Step 2: Run tab tests — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab -v 2 --keepdb`
Expected: OK, 6 tests pass (the swap target id is present from Task 5's templates).

If either test fails because the rendered template chose a path different from what was set up in Task 5, double-check `htmx_partial` import path and `HX-Request` header handling in NetBox's `utilities.htmx`.

- [ ] **Step 3: Commit**

```bash
git add netbox_cf_backrefs/tests/test_tab.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "test(tab): lock in htmx partial rows-only rendering"
```

---

## Task 7: Wire filter sidebar + quick search end-to-end

The filter helper (Task 3) already narrows `refs` based on `request.GET`, and the view (Task 5) already calls it. This task adds the sidebar UI in `tab.html` and integration tests proving querystring filtering works.

**Files:**
- Modify: `netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html`
- Modify: `netbox_cf_backrefs/views.py`
- Modify: `netbox_cf_backrefs/tests/test_tab.py`

- [ ] **Step 1: Append the failing tests inside `CFBackrefsTabRenderingTests`**

```python
    def test_filter_by_source_type_via_querystring(self):
        from circuits.models import Circuit, CircuitType, Provider
        provider = Provider.objects.create(name="cfbtab-prov", slug="cfbtab-prov")
        ctype = CircuitType.objects.create(name="cfbtab-ct", slug="cfbtab-ct")
        # Add a circuit ref so unfiltered count is 2 but ?source_type=device returns 1.
        make_cf(
            name="primary_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device, Circuit],
        )
        Circuit.objects.create(
            cid="cfbtab-c1", provider=provider, type=ctype,
            custom_field_data={"primary_contact": self.contact.pk},
        )
        Device.objects.create(
            name="cfbtab-dev-2",
            site=self.site, device_type=self.device_type, role=self.role,
            custom_field_data={"primary_contact": self.contact.pk},
        )

        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url, {"source_type": "device"})
        body = response.content.decode()
        self.assertNotIn("cfbtab-c1", body)
        self.assertIn("cfbtab-dev-2", body)

    def test_quick_search_narrows_results(self):
        Device.objects.create(
            name="cfbtab-other",
            site=self.site, device_type=self.device_type, role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url, {"q": "cfbtab-other"})
        body = response.content.decode()
        self.assertIn("cfbtab-other", body)
        self.assertNotIn("cfbtab-dev-1", body)

    def test_sidebar_options_built_from_unfiltered_refs(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        body = response.content.decode()
        # Source type dropdown lists "device" because the unfiltered refs
        # include at least one Device row.
        self.assertIn('value="device"', body)
        # Quick search input is present.
        self.assertIn('name="q"', body)
```

- [ ] **Step 2: Run new tests — verify FAIL**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab.CFBackrefsTabRenderingTests.test_sidebar_options_built_from_unfiltered_refs -v 2 --keepdb`
Expected: FAIL — `value="device"` and `name="q"` not in body (sidebar not rendered yet).

- [ ] **Step 3: Build sidebar option lists in the view**

In `netbox_cf_backrefs/views.py`, replace the `get` method body with this version (it adds three sorted option lists computed from the unfiltered `refs` and surfaces the "current" values for re-rendering selected dropdowns):

```python
        def get(self, request, **kwargs):
            instance = self.get_object(**kwargs)
            refs = list(get_reverse_cf_references(instance, apply_visibility_filters=False))
            filtered = apply_filters(refs, request.GET)

            table = CFBackrefTabTable(filtered, target_pk=instance.pk)
            try:
                RequestConfig(request, paginate={
                    "paginator_class": EnhancedPaginator,
                    "per_page": int(request.GET.get("per_page", 50) or 50),
                    "orphans": 0,
                }).configure(table)
            except (InvalidPage, ValueError):
                RequestConfig(request, paginate={
                    "paginator_class": EnhancedPaginator,
                    "per_page": 50,
                    "orphans": 0,
                }).configure(table)

            source_type_options = sorted({r.source_model_label for r in refs})
            cf_name_options = sorted({(r.cf_name, r.cf_label) for r in refs})
            cf_type_options = sorted({r.cf_type for r in refs})

            ctx = {
                "object": instance,
                "tab": self.tab,
                "table": table,
                "total": len(filtered),
                "all_refs": refs,
                "source_type_options": source_type_options,
                "cf_name_options": cf_name_options,
                "cf_type_options": cf_type_options,
                "current_source_type": request.GET.get("source_type", ""),
                "current_cf_name": request.GET.get("cf_name", ""),
                "current_cf_type": request.GET.get("cf_type", ""),
                "current_q": request.GET.get("q", ""),
            }
            template = self.partial_template_name if htmx_partial(request) else self.template_name
            return render(request, template, ctx)
```

- [ ] **Step 4: Render the sidebar + quick-search input in `tab.html`**

Replace the entire body of `tab.html` with:

```html
{% extends 'generic/object.html' %}
{% load render_table from django_tables2 %}
{% load i18n %}

{% block content %}
  <div class="row">
    <div class="col col-md-9">
      <div class="card">
        <h5 class="card-header">{% trans 'CF Backrefs' %} ({{ total }})</h5>
        <div class="card-body">
          <form method="get" class="row g-2 mb-3">
            <div class="col-md-9">
              <input type="search"
                     name="q"
                     value="{{ current_q }}"
                     class="form-control"
                     placeholder="{% trans 'Quick search' %}"/>
            </div>
            <div class="col-md-3">
              <button type="submit" class="btn btn-primary w-100">
                {% trans 'Search' %}
              </button>
            </div>
          </form>
        </div>
        <div id="cf-backrefs-table"
             hx-target="this"
             hx-select="#cf-backrefs-table"
             hx-swap="outerHTML">
          <div class="table-responsive">{% render_table table 'inc/table.html' %}</div>
          {% include 'inc/paginator.html' with paginator=table.paginator page=table.page %}
        </div>
      </div>
    </div>
    <div class="col col-md-3">
      <div class="card">
        <h5 class="card-header">{% trans 'Filters' %}</h5>
        <div class="card-body">
          <form method="get">
            {% if current_q %}
              <input type="hidden" name="q" value="{{ current_q }}"/>
            {% endif %}
            <div class="mb-3">
              <label class="form-label">{% trans 'Source type' %}</label>
              <select name="source_type" class="form-select">
                <option value="">{% trans 'Any' %}</option>
                {% for opt in source_type_options %}
                  <option value="{{ opt }}"
                          {% if opt == current_source_type %}selected{% endif %}>
                    {{ opt|capfirst }}
                  </option>
                {% endfor %}
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">{% trans 'Custom field' %}</label>
              <select name="cf_name" class="form-select">
                <option value="">{% trans 'Any' %}</option>
                {% for name, label in cf_name_options %}
                  <option value="{{ name }}"
                          {% if name == current_cf_name %}selected{% endif %}>
                    {{ label }}
                  </option>
                {% endfor %}
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label">{% trans 'CF type' %}</label>
              <select name="cf_type" class="form-select">
                <option value="">{% trans 'Any' %}</option>
                {% for opt in cf_type_options %}
                  <option value="{{ opt }}"
                          {% if opt == current_cf_type %}selected{% endif %}>
                    {{ opt|capfirst }}
                  </option>
                {% endfor %}
              </select>
            </div>
            <button type="submit" class="btn btn-primary w-100">
              {% trans 'Apply' %}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
{% endblock content %}
```

- [ ] **Step 5: Run tab tests — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab -v 2 --keepdb`
Expected: OK, 9 tests pass.

- [ ] **Step 6: Lint**

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

Run: `/opt/netbox/venv/bin/python -m djlint netbox_cf_backrefs/templates --check`
Expected: clean. If drift, run `--reformat` and stage the result.

- [ ] **Step 7: Commit**

```bash
git add netbox_cf_backrefs/views.py netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html netbox_cf_backrefs/tests/test_tab.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat(tab): filter sidebar + quick search wired to apply_filters"
```

---

## Task 8: Wire Configure-Table modal + per-user column prefs

Subclassing `NetBoxTable` already enables column prefs at the model layer (Task 4). This task adds the modal markup + button to `tab.html` and an integration test confirming the modal is present.

**Files:**
- Modify: `netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html`
- Modify: `netbox_cf_backrefs/views.py`
- Modify: `netbox_cf_backrefs/tests/test_tab.py`

- [ ] **Step 1: Append the failing test inside `CFBackrefsTabRenderingTests`**

```python
    def test_configure_table_button_and_modal_present(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        body = response.content.decode()
        # Configure-Table button visible to authenticated users.
        self.assertIn("Configure Table", body)
        # NetBox attaches the modal id from the table class name.
        self.assertIn("CFBackrefTabTable_config", body)
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab.CFBackrefsTabRenderingTests.test_configure_table_button_and_modal_present -v 2 --keepdb`
Expected: FAIL — `Configure Table` not in body.

- [ ] **Step 3: Pass `table_modal` into context**

In `netbox_cf_backrefs/views.py`, inside the `get` method, extend `ctx` with the modal id NetBox uses:

```python
            ctx = {
                "object": instance,
                "tab": self.tab,
                "table": table,
                "table_modal": f"{table.name}_config",
                "total": len(filtered),
                "all_refs": refs,
                "source_type_options": source_type_options,
                "cf_name_options": cf_name_options,
                "cf_type_options": cf_type_options,
                "current_source_type": request.GET.get("source_type", ""),
                "current_cf_name": request.GET.get("cf_name", ""),
                "current_cf_type": request.GET.get("cf_type", ""),
                "current_q": request.GET.get("q", ""),
            }
```

(Only the `"table_modal"` line is new; the rest is unchanged.)

- [ ] **Step 4: Add the Configure-Table button + modal to `tab.html`**

Inside `tab.html`, immediately above the `<form method="get" class="row g-2 mb-3">` in the main column, insert the button:

```html
          {% if request.user.is_authenticated %}
            <div class="d-flex justify-content-end mb-2">
              <button type="button"
                      data-bs-toggle="modal"
                      data-bs-target="#{{ table_modal }}"
                      class="btn btn-sm btn-outline-secondary">
                <i class="mdi mdi-cog"></i> {% trans 'Configure Table' %}
              </button>
            </div>
          {% endif %}
```

At the end of `{% block content %}` (after the closing `</div></div>` of the row), add the standard NetBox table-config modal include:

```html
  {% if request.user.is_authenticated %}
    {% include 'inc/table_config_form.html' with table=table table_modal=table_modal %}
  {% endif %}
```

- [ ] **Step 5: Run test — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_tab -v 2 --keepdb`
Expected: OK, 10 tests pass.

If `inc/table_config_form.html` is not found in this NetBox version, look for `inc/table_controls_htmx.html` or a similar name with `grep -rn 'table_modal' /opt/netbox/netbox/templates/inc/ | head` and substitute. Report the discovered name in the commit message if you change it.

- [ ] **Step 6: Lint**

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

Run: `/opt/netbox/venv/bin/python -m djlint netbox_cf_backrefs/templates --check`
Expected: clean (run `--reformat` if needed).

- [ ] **Step 7: Commit**

```bash
git add netbox_cf_backrefs/views.py netbox_cf_backrefs/templates/netbox_cf_backrefs/tab.html netbox_cf_backrefs/tests/test_tab.py
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "feat(tab): Configure Table modal for per-user column prefs"
```

---

## Task 9: Regression test for panel + manual smoke + docs

Belt-and-braces test that `apply_visibility_filters=True` (panel default) keeps the panel data unchanged. Then add the README + CHANGELOG bullets and run a manual smoke.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_template_content.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Append a regression test to `tests/test_template_content.py`**

Inside `PanelRenderTests`, append:

```python
    def test_panel_does_not_show_hidden_or_excluded_cfs(self):
        from django.test import override_settings

        # Hidden CF — visible in tab, NOT in panel.
        make_cf(
            name="hidden_link",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
            ui_visible="hidden",
        )
        # Excluded CF — visible in tab, NOT in panel.
        make_cf(
            name="excluded_link",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        Device.objects.create(
            name="cfb-panel-regression",
            site=self.site, device_type=self.device_type, role=self.role,
            custom_field_data={
                "hidden_link": self.contact.pk,
                "excluded_link": self.contact.pk,
            },
        )

        with override_settings(
            PLUGINS_CONFIG={
                "netbox_cf_backrefs": {
                    "page_size": 50,
                    "excluded_custom_fields": ["excluded_link"],
                }
            }
        ):
            response = self.client.get(
                reverse("tenancy:contact", args=[self.contact.pk])
            )

        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("hidden_link", body)
        self.assertNotIn("excluded_link", body)
```

- [ ] **Step 2: Run the test — verify PASS**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content.PanelRenderTests.test_panel_does_not_show_hidden_or_excluded_cfs -v 2 --keepdb`
Expected: OK.

- [ ] **Step 3: Update `README.md` with a CF Backrefs Tab section**

Find the existing `## Behavior notes` section in `README.md` and append this new section right after it (before `## Development`):

```markdown
## CF Backrefs tab

In addition to the inline panel, every object detail page exposes a **CF Backrefs** tab (`/<app>/<model>/<pk>/cf-backrefs/`) when at least one CF references the object. The tab uses NetBox's standard list-view chrome — sortable columns, filter sidebar, quick search, Configure Table modal, per-user column preferences, htmx-paginated rows.

The tab additionally exposes a per-row filter icon (`mdi mdi-filter`) that pivots to the source model's NetBox list view filtered by the CF that produced the row, e.g. `/dcim/devices/?cf_tech_contact=<contact_pk>` ("show me every Device that references this same target via this CF").

**Important:** the tab deliberately ignores the `excluded_custom_fields` setting and the CF-level `ui_visible='hidden'` flag. Anyone with `view_<parent_model>` permission can see hidden / excluded CF references via the tab. The panel honors both filters and is the curated view; the tab is the "everything" view. If your hidden CFs carry sensitive data, do not rely on the tab to hide them.
```

- [ ] **Step 4: Append a bullet to the existing `## 0.1.1` entry in `CHANGELOG.md`**

In `CHANGELOG.md`, under the `## 0.1.1 — 2026-05-06` heading, append (no new version section):

```markdown
- New `CF Backrefs` detail-page tab on every CF target object. Adds list-view chrome (filter sidebar, quick search, Configure Table modal, per-user column prefs, htmx pagination, sortable columns) and a per-row filter-icon pivot to `/<app>/<model>/?cf_<name>=<target_pk>`. Tab uses standard NetBox tab permissions (`view_<parent_model>`) and deliberately surfaces hidden / excluded CFs that the panel suppresses.
```

- [ ] **Step 5: Run the full test suite + lint as a final check**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb`
Expected: OK across every test (utils + filters + tab + template_content).

Run: `/opt/netbox/venv/bin/python -m ruff check netbox_cf_backrefs`
Expected: `All checks passed!`

Run: `/opt/netbox/venv/bin/python -m djlint netbox_cf_backrefs/templates --check`
Expected: clean.

- [ ] **Step 6: Manual smoke test (re-using `cfb-` fixture data)**

1. Restart NetBox (the `_register_tabs()` call runs at import).
2. Open `/tenancy/contacts/<alice_pk>/` (the existing test contact). Confirm the **CF Backrefs** tab appears in the tab bar with badge showing 5 (= 4 panel rows + 1 excluded). Click it.
3. Confirm a styled NetBox list-view-style table renders with 5 rows, sortable headers, the per-row filter icon column, the filter sidebar on the right, and the quick-search box up top.
4. Click the filter icon on any Device row → URL becomes `/dcim/devices/?cf_<name>=<alice_pk>` and the page lists peer Devices.
5. Type a CF label fragment in quick search → table narrows.
6. Apply `CF type = Multi-object` from the sidebar → table narrows further.
7. Click "Configure Table", toggle off the `cf_type` column, save → table re-renders without that column. Reload page → preference persists.
8. As a non-superuser without `view_contact` permission, hit the URL directly → 403.

- [ ] **Step 7: Commit**

```bash
git add netbox_cf_backrefs/tests/test_template_content.py README.md CHANGELOG.md
git -c user.email=jan.krupa@cesnet.cz -c user.name='Jan Krupa' commit -m "docs+test: regression test panel filters; document CF Backrefs tab"
```

---

## Self-review

**Spec coverage:**
- Tab label `CF Backrefs`, `hide_if_empty=True` — Tasks 5 + ViewTab metadata.
- 5 columns (Filter / Source object / Source type / Custom field / CF type) — Task 4.
- Filter sidebar (Source type / CF name / CF type) — Task 7.
- Quick search across 4 fields — Task 7 + Task 3 unit tests.
- URL `/cf-backrefs/` — Task 5 (path="cf-backrefs").
- Tab ignores `excluded_custom_fields` + `ui_visible='hidden'` — Task 2 (kwarg) + Task 5 (view passes `False`).
- Permissions = standard `view_<parent_model>` via `ObjectView` — Task 5 (`queryset = Model.objects.all()`).
- Filter-button URL format — Task 4 (`_peer_list_url`) + Task 5 test.
- htmx partial — Task 5 (template + branch) + Task 6 (lock-in test).
- Configure Table modal — Task 8.
- Reference dataclass `cf_type` field — Task 1.
- `apply_visibility_filters` kwarg defaults `True` — Task 2.
- README discloses hidden/excluded CF leak — Task 9.
- No version bump — verified via "no edits to `pyproject.toml` or `version.py`" in any task.

No spec gaps detected.

**Placeholder scan:** no `TBD`/`TODO`/`add appropriate ...` patterns. Each step shows actual code or commands.

**Type consistency:**
- `Reference(source_object, source_model_label, cf_name, cf_label, cf_type)` — defined in Task 1, used identically in `apply_filters` (Task 3), `CFBackrefTabTable` (Task 4), the view (Task 5), and the panel regression test (Task 9).
- `apply_visibility_filters` kwarg is keyword-only (`*,`) and defaults `True` — used the same way in Task 2 (definition), Task 5 (`apply_visibility_filters=False`), Task 9 (panel still uses default).
- `_peer_list_url(reference, target_pk)` — defined Task 4, called only via `CFBackrefTabTable.render_pivot` (also Task 4).
- View URL name `<app>:<model>_cf_backrefs` is consistent across all integration tests (Task 5 sets `tab_url`, later tasks reuse `self.tab_url`).
- HTML id `cf-backrefs-table` consistent between `tab.html` (Task 5/7) and `tab_partial.html` (Task 5) and the integration tests (Tasks 5/6/7).
