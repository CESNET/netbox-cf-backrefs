# netbox_cf_backrefs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a NetBox plugin (`netbox_cf_backrefs`) that adds an inline panel to object detail pages showing every other object that references it via `object` or `multi-object` custom fields.

**Architecture:** Single Django app, no models, no migrations. A `PluginTemplateExtension` is dynamically generated for each NetBox model that is currently a target of an object/multi-object CF. The extension's `full_width_page()` calls a pure function that runs per-CF JSONField queries against each source model's `custom_field_data` and renders a paginated table. Empty result → panel suppressed.

**Tech Stack:** Python ≥3.12, Django (NetBox-pinned), NetBox 4.5.0–4.6.99, PostgreSQL JSONField lookups (`__contains`), Django's standard `Paginator`. Tooling: `ruff`, `djlint`, `pytest`/`manage.py test`.

**Spec:** `docs/superpowers/specs/2026-05-06-netbox-cf-backrefs-design.md`

**Working directory:** `/opt/netbox_custom_fields_object_display_plugin/` (the directory name is legacy; the package inside is `netbox_cf_backrefs`).

**NetBox dev environment commands** (per project CLAUDE.md):
- Test runner: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb`
- Shell: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py nbshell`
- Dev server: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py runserver`

---

## File map

```
netbox_cf_backrefs/
├── __init__.py                                       # PluginConfig + default settings
├── version.py                                        # __version__
├── utils.py                                          # get_reverse_cf_references(), Reference dataclass
├── template_content.py                               # Dynamic PluginTemplateExtension registration
├── templates/netbox_cf_backrefs/panel.html           # Panel HTML
└── tests/
    ├── __init__.py
    ├── _factories.py                                 # Shared test helpers (CF + source-object factories)
    ├── test_utils.py                                 # Unit tests for utils
    └── test_template_content.py                      # Integration tests rendering object pages
pyproject.toml                                        # Packaging
README.md                                             # Install, settings, permission warning, restart constraint
CHANGELOG.md
LICENSE                                               # Apache-2.0 (matching netbox-attachments)
MANIFEST.in
Makefile                                              # `make test`, `make lint`, `make format`
```

---

## Task 1: Project scaffolding & PluginConfig

**Files:**
- Create: `pyproject.toml`
- Create: `netbox_cf_backrefs/__init__.py`
- Create: `netbox_cf_backrefs/version.py`
- Create: `MANIFEST.in`
- Create: `Makefile`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `README.md` (skeleton; final content in Task 13)

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "netbox-cf-backrefs"
version = "0.1.0"
description = "NetBox plugin: show reverse references from object / multi-object custom fields on the target object's detail page."
readme = "README.md"
requires-python = ">=3.12,<3.15"
license = {text = "Apache-2.0"}
authors = [{name = "Jan Krupa", email = "jan.krupa@cesnet.cz"}]
classifiers = [
    "Framework :: Django",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
]

[project.urls]
Homepage = "https://github.com/cesnet/netbox-cf-backrefs"

[tool.setuptools]
packages = ["netbox_cf_backrefs", "netbox_cf_backrefs.tests"]
include-package-data = true

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.djlint]
profile = "django"
indent = 2
```

- [ ] **Step 2: Write `netbox_cf_backrefs/__init__.py`**

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


config = NetBoxCFBackrefsConfig
```

- [ ] **Step 3: Write `netbox_cf_backrefs/version.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Write `MANIFEST.in`**

```
include README.md
include CHANGELOG.md
include LICENSE
recursive-include netbox_cf_backrefs/templates *
```

- [ ] **Step 5: Write `Makefile`**

```makefile
PY = /opt/netbox/venv/bin/python
MANAGE = $(PY) /opt/netbox/netbox/manage.py

.PHONY: test lint format

test:
	$(MANAGE) test netbox_cf_backrefs --keepdb

lint:
	$(PY) -m ruff check netbox_cf_backrefs
	$(PY) -m djlint netbox_cf_backrefs/templates --check

format:
	$(PY) -m ruff format netbox_cf_backrefs
	$(PY) -m djlint netbox_cf_backrefs/templates --reformat
```

- [ ] **Step 6: Write `LICENSE` (Apache-2.0)**

Copy the standard Apache-2.0 license text from https://www.apache.org/licenses/LICENSE-2.0.txt verbatim into `LICENSE`. Do not modify.

- [ ] **Step 7: Write `CHANGELOG.md`**

```markdown
# Changelog

## 0.1.0 — Unreleased

- Initial release: inline panel on object detail pages showing reverse object/multi-object custom field references.
```

- [ ] **Step 8: Write `README.md` skeleton (final content in Task 13)**

```markdown
# netbox_cf_backrefs

NetBox plugin that surfaces the reverse side of object / multi-object custom field references on the target object's detail page.

## Status

Pre-release. See `docs/superpowers/specs/2026-05-06-netbox-cf-backrefs-design.md` for the design.
```

- [ ] **Step 9: Verify the plugin loads in NetBox**

Add to `/opt/netbox/netbox/netbox/configuration.py`:

```python
PLUGINS = [..., "netbox_cf_backrefs"]
```

Install in editable mode and run NetBox's system check:

Run: `cd /opt/netbox_custom_fields_object_display_plugin && /opt/netbox/venv/bin/pip install -e .`
Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml MANIFEST.in Makefile LICENSE CHANGELOG.md README.md netbox_cf_backrefs/__init__.py netbox_cf_backrefs/version.py
git commit -m "feat: scaffold netbox_cf_backrefs plugin with PluginConfig"
```

---

## Task 2: Test factories + Reference dataclass + single-object CF lookup

The simplest possible case: one CustomField of type `object`, attached to a Device source model, pointing to a Contact target. A Device that references the contact must appear; a Device referencing a different contact must not.

**Files:**
- Create: `netbox_cf_backrefs/tests/__init__.py` (empty)
- Create: `netbox_cf_backrefs/tests/_factories.py`
- Create: `netbox_cf_backrefs/tests/test_utils.py`
- Create: `netbox_cf_backrefs/utils.py`

- [ ] **Step 1: Write `tests/__init__.py`**

Empty file.

- [ ] **Step 2: Write `tests/_factories.py`**

```python
"""Test factories for netbox_cf_backrefs.

Reusable helpers to build CustomFields without boilerplate in every test
method. Kept inside `tests/` so they ship with the test suite but are not
part of the importable plugin API.
"""
from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField


def make_cf(
    *,
    name: str,
    cf_type: str,
    target_model,
    source_models,
    label: str = "",
    ui_visible: str = "always",
):
    """Create a CustomField of `cf_type` ("object" or "multiobject") and
    attach it to `source_models`.

    `target_model` is the Django model class the CF points to.
    `source_models` is an iterable of Django model classes the CF is attached to.
    """
    cf = CustomField.objects.create(
        name=name,
        label=label or name,
        type=cf_type,
        related_object_type=ContentType.objects.get_for_model(target_model),
        ui_visible=ui_visible,
    )
    cf.object_types.set(
        ContentType.objects.get_for_model(m) for m in source_models
    )
    return cf
```

- [ ] **Step 3: Write the failing test in `tests/test_utils.py`**

```python
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from tenancy.models import Contact
from utilities.testing import TestCase

from netbox_cf_backrefs.utils import Reference, get_reverse_cf_references

from ._factories import make_cf


class GetReverseCFReferencesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Minimal device prerequisites (NetBox requires these to create a Device).
        cls.site = Site.objects.create(name="S1", slug="s1")
        manufacturer = Manufacturer.objects.create(name="M1", slug="m1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="DT1", slug="dt1"
        )
        cls.role = DeviceRole.objects.create(name="R1", slug="r1")

        # Contacts have an M2M `groups` relationship in NetBox 4.x; we don't
        # need a group for these tests, so omit it entirely.
        cls.target_a = Contact.objects.create(name="Alice")
        cls.target_b = Contact.objects.create(name="Bob")

    def _make_device(self, name: str, cf_data: dict | None = None) -> Device:
        return Device.objects.create(
            name=name,
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data=cf_data or {},
        )

    def test_returns_empty_when_no_cfs_target_the_model(self):
        result = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(result, [])

    def test_object_cf_returns_only_matching_source(self):
        make_cf(
            name="tech_contact",
            label="Technical contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        match = self._make_device("dev-match", {"tech_contact": self.target_a.pk})
        self._make_device("dev-other", {"tech_contact": self.target_b.pk})

        refs = list(get_reverse_cf_references(self.target_a))

        self.assertEqual(len(refs), 1)
        ref = refs[0]
        self.assertIsInstance(ref, Reference)
        self.assertEqual(ref.source_object, match)
        self.assertEqual(ref.source_model_label, "device")
        self.assertEqual(ref.cf_name, "tech_contact")
        self.assertEqual(ref.cf_label, "Technical contact")
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: `ModuleNotFoundError: No module named 'netbox_cf_backrefs.utils'` (or `ImportError` for `Reference`/`get_reverse_cf_references`).

- [ ] **Step 5: Write minimal `netbox_cf_backrefs/utils.py`**

```python
"""Reverse lookup of object / multi-object custom field references."""
from dataclasses import dataclass
from collections.abc import Iterator

from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField


@dataclass(frozen=True)
class Reference:
    source_object: object
    source_model_label: str
    cf_name: str
    cf_label: str


def get_reverse_cf_references(target_obj) -> Iterator[Reference]:
    """Yield Reference rows for every object/multi-object CF pointing to `target_obj`.

    Uses live JSONField queries against each source model's `custom_field_data`.
    """
    target_ct = ContentType.objects.get_for_model(target_obj)

    cfs = CustomField.objects.filter(
        type__in=("object", "multiobject"),
        related_object_type=target_ct,
    )

    for cf in cfs:
        cf_label = cf.label or cf.name
        for source_ct in cf.object_types.all():
            source_model = source_ct.model_class()
            qs = source_model.objects.filter(
                **{f"custom_field_data__{cf.name}": target_obj.pk}
            )
            for src in qs:
                yield Reference(
                    source_object=src,
                    source_model_label=source_ct.model,
                    cf_name=cf.name,
                    cf_label=cf_label,
                )
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK — both tests pass.

- [ ] **Step 7: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/__init__.py netbox_cf_backrefs/tests/_factories.py netbox_cf_backrefs/tests/test_utils.py
git commit -m "feat(utils): add get_reverse_cf_references for single-object CFs"
```

---

## Task 3: Multi-object CF support

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_utils.py` (append a test method)
- Modify: `netbox_cf_backrefs/utils.py`

- [ ] **Step 1: Append the failing test inside `GetReverseCFReferencesTests`**

```python
    def test_multiobject_cf_matches_when_pk_in_list(self):
        make_cf(
            name="responsible_contacts",
            label="Responsible contacts",
            cf_type="multiobject",
            target_model=Contact,
            source_models=[Device],
        )
        match = self._make_device(
            "dev-multi-match",
            {"responsible_contacts": [self.target_a.pk, self.target_b.pk]},
        )
        self._make_device(
            "dev-multi-other", {"responsible_contacts": [self.target_b.pk]}
        )

        refs = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].source_object, match)
        self.assertEqual(refs[0].cf_name, "responsible_contacts")
```

- [ ] **Step 2: Run — verify failure**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils.GetReverseCFReferencesTests.test_multiobject_cf_matches_when_pk_in_list -v 2 --keepdb`
Expected: FAIL — the device with `responsible_contacts: [target_a.pk, target_b.pk]` is not returned because the current code does scalar equality, not list containment.

- [ ] **Step 3: Update `netbox_cf_backrefs/utils.py` — branch on CF type**

Replace the `for source_ct in cf.object_types.all():` loop body with:

```python
        for source_ct in cf.object_types.all():
            source_model = source_ct.model_class()
            if cf.type == "object":
                lookup = {f"custom_field_data__{cf.name}": target_obj.pk}
            else:  # "multiobject"
                lookup = {f"custom_field_data__{cf.name}__contains": [target_obj.pk]}
            for src in source_model.objects.filter(**lookup):
                yield Reference(
                    source_object=src,
                    source_model_label=source_ct.model,
                    cf_name=cf.name,
                    cf_label=cf_label,
                )
```

- [ ] **Step 4: Run all utils tests — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK, 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/test_utils.py
git commit -m "feat(utils): support multi-object CF reverse lookups via __contains"
```

---

## Task 4: Mixed source models and multiple CFs per source

Verifies the spec behaviors: same target referenced by two different source models, and one source object with two CFs both pointing to the target → two rows.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_utils.py`

- [ ] **Step 1: Append the failing tests inside `GetReverseCFReferencesTests`**

```python
    def test_mixed_source_models(self):
        from circuits.models import Circuit, CircuitType, Provider

        make_cf(
            name="primary_contact",
            label="Primary contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device, Circuit],
        )
        device = self._make_device("dev-mixed", {"primary_contact": self.target_a.pk})

        provider = Provider.objects.create(name="P1", slug="p1")
        ctype = CircuitType.objects.create(name="CT1", slug="ct1")
        circuit = Circuit.objects.create(
            cid="C-1",
            provider=provider,
            type=ctype,
            custom_field_data={"primary_contact": self.target_a.pk},
        )

        refs = list(get_reverse_cf_references(self.target_a))
        sources = {(r.source_object, r.source_model_label) for r in refs}
        self.assertEqual(
            sources,
            {(device, "device"), (circuit, "circuit")},
        )

    def test_two_cfs_on_same_source_yield_two_rows(self):
        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        make_cf(
            name="escalation_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        self._make_device(
            "dev-double",
            {
                "tech_contact": self.target_a.pk,
                "escalation_contact": self.target_a.pk,
            },
        )

        refs = list(get_reverse_cf_references(self.target_a))
        cf_names = sorted(r.cf_name for r in refs)
        self.assertEqual(cf_names, ["escalation_contact", "tech_contact"])
```

- [ ] **Step 2: Run the new tests**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK — both tests pass without code changes (the existing implementation already handles these cases). If a test fails, fix the implementation; do not loosen the test.

- [ ] **Step 3: Commit**

```bash
git add netbox_cf_backrefs/tests/test_utils.py
git commit -m "test(utils): cover mixed source models and multiple CFs per source"
```

---

## Task 5: `excluded_custom_fields` plugin setting

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_utils.py`
- Modify: `netbox_cf_backrefs/utils.py`

- [ ] **Step 1: Append the failing test**

```python
    def test_excluded_custom_fields_setting_skips_cf(self):
        from django.test import override_settings

        make_cf(
            name="hidden_link",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        self._make_device("dev-hidden", {"hidden_link": self.target_a.pk})

        with override_settings(
            PLUGINS_CONFIG={
                "netbox_cf_backrefs": {
                    "page_size": 50,
                    "excluded_custom_fields": ["hidden_link"],
                }
            }
        ):
            refs = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(refs, [])
```

- [ ] **Step 2: Run — verify failure**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils.GetReverseCFReferencesTests.test_excluded_custom_fields_setting_skips_cf -v 2 --keepdb`
Expected: FAIL — `assertEqual([], [Reference(...)])`.

- [ ] **Step 3: Add a settings helper to `netbox_cf_backrefs/utils.py`**

Add to imports at the top of the file:

```python
from netbox.plugins import get_plugin_config
```

Add helper near the top of the module (after imports, before `Reference`):

```python
def _excluded_cf_names() -> set[str]:
    return set(get_plugin_config("netbox_cf_backrefs", "excluded_custom_fields") or [])
```

Update the CF queryset filter inside `get_reverse_cf_references`:

```python
    cfs = CustomField.objects.filter(
        type__in=("object", "multiobject"),
        related_object_type=target_ct,
    ).exclude(name__in=_excluded_cf_names())
```

- [ ] **Step 4: Run all utils tests — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/test_utils.py
git commit -m "feat(utils): honor excluded_custom_fields plugin setting"
```

---

## Task 6: Skip CFs with `ui_visible='hidden'`

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_utils.py`
- Modify: `netbox_cf_backrefs/utils.py`

- [ ] **Step 1: Append the failing test**

```python
    def test_hidden_cf_is_skipped(self):
        make_cf(
            name="internal_only",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
            ui_visible="hidden",
        )
        self._make_device("dev-internal", {"internal_only": self.target_a.pk})

        refs = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(refs, [])
```

- [ ] **Step 2: Run — verify failure**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils.GetReverseCFReferencesTests.test_hidden_cf_is_skipped -v 2 --keepdb`
Expected: FAIL — one `Reference` returned instead of `[]`.

- [ ] **Step 3: Update the CF queryset filter in `get_reverse_cf_references`**

Replace the queryset construction with:

```python
    cfs = (
        CustomField.objects.filter(
            type__in=("object", "multiobject"),
            related_object_type=target_ct,
        )
        .exclude(name__in=_excluded_cf_names())
        .exclude(ui_visible="hidden")
    )
```

- [ ] **Step 4: Run all utils tests — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/test_utils.py
git commit -m "feat(utils): skip CFs with ui_visible='hidden'"
```

---

## Task 7: Resilient handling of unloadable source models

If a CF's `object_types` references a content type whose Django model can no longer be loaded (uninstalled plugin), the lookup must skip it without raising.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_utils.py`
- Modify: `netbox_cf_backrefs/utils.py`

- [ ] **Step 1: Append the failing test**

If not already present at the top of `test_utils.py`, add: `from django.contrib.contenttypes.models import ContentType`.

```python
    def test_unloadable_source_model_is_skipped_with_warning(self):
        from unittest.mock import patch

        make_cf(
            name="primary_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        device = self._make_device("dev-ok", {"primary_contact": self.target_a.pk})

        original_model_class = ContentType.model_class

        def fake_model_class(self):
            if self.app_label == "dcim" and self.model == "device":
                return None  # simulate unloadable model
            return original_model_class(self)

        with patch.object(ContentType, "model_class", fake_model_class), \
                self.assertLogs("netbox_cf_backrefs", level="WARNING") as captured:
            refs = list(get_reverse_cf_references(self.target_a))

        self.assertEqual(refs, [])
        self.assertTrue(any("device" in m for m in captured.output))
        # Sanity: device still exists; we only simulated an unloadable model.
        self.assertEqual(Device.objects.filter(pk=device.pk).count(), 1)
```

- [ ] **Step 2: Run — verify failure**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils.GetReverseCFReferencesTests.test_unloadable_source_model_is_skipped_with_warning -v 2 --keepdb`
Expected: FAIL — `AttributeError: 'NoneType' object has no attribute 'objects'`.

- [ ] **Step 3: Add logging + skip in `netbox_cf_backrefs/utils.py`**

Add at module top (after imports):

```python
import logging

logger = logging.getLogger("netbox_cf_backrefs")
```

Update the per-source-model loop:

```python
        for source_ct in cf.object_types.all():
            source_model = source_ct.model_class()
            if source_model is None:
                logger.warning(
                    "Skipping CF %r: source content type %s.%s is not loadable",
                    cf.name, source_ct.app_label, source_ct.model,
                )
                continue
            if cf.type == "object":
                lookup = {f"custom_field_data__{cf.name}": target_obj.pk}
            else:
                lookup = {f"custom_field_data__{cf.name}__contains": [target_obj.pk]}
            for src in source_model.objects.filter(**lookup):
                yield Reference(
                    source_object=src,
                    source_model_label=source_ct.model,
                    cf_name=cf.name,
                    cf_label=cf_label,
                )
```

- [ ] **Step 4: Run all utils tests — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_utils -v 2 --keepdb`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add netbox_cf_backrefs/utils.py netbox_cf_backrefs/tests/test_utils.py
git commit -m "feat(utils): skip unloadable source models with warning"
```

---

## Task 8: Panel template + dynamic `PluginTemplateExtension`

End-to-end integration: an actual object detail page should now contain the panel.

**Files:**
- Create: `netbox_cf_backrefs/templates/netbox_cf_backrefs/panel.html`
- Create: `netbox_cf_backrefs/template_content.py`
- Create: `netbox_cf_backrefs/tests/test_template_content.py`

- [ ] **Step 1: Write the failing integration test in `tests/test_template_content.py`**

```python
from django.contrib.auth import get_user_model
from django.urls import reverse
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from tenancy.models import Contact
from utilities.testing import TestCase

from ._factories import make_cf


class PanelRenderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("u1", password="p")
        cls.user.is_superuser = True
        cls.user.save()

        cls.site = Site.objects.create(name="S1", slug="s1")
        manufacturer = Manufacturer.objects.create(name="M1", slug="m1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="DT1", slug="dt1"
        )
        cls.role = DeviceRole.objects.create(name="R1", slug="r1")
        # Contact.groups is M2M in NetBox 4.x; not needed for these tests.
        cls.contact = Contact.objects.create(name="Bob")

    def setUp(self):
        self.client.force_login(self.user)

    def test_panel_renders_with_one_reference(self):
        make_cf(
            name="tech_contact",
            label="Technical contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        device = Device.objects.create(
            name="dev-1",
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )

        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Referenced by Custom Fields", body)
        self.assertIn(device.get_absolute_url(), body)
        self.assertIn("Technical contact", body)
```

- [ ] **Step 2: Run — verify failure**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content -v 2 --keepdb`
Expected: FAIL — `"Referenced by Custom Fields" not found in body`.

- [ ] **Step 3: Write `netbox_cf_backrefs/templates/netbox_cf_backrefs/panel.html`**

```html
{% load helpers %}
<div class="card">
  <h5 class="card-header">Referenced by Custom Fields ({{ total }})</h5>
  <div class="card-body p-0">
    <table class="table table-hover">
      <thead>
        <tr>
          <th>Source object</th>
          <th>Source type</th>
          <th>Custom field</th>
        </tr>
      </thead>
      <tbody>
        {% for ref in page.object_list %}
          <tr>
            <td><a href="{{ ref.source_object.get_absolute_url }}">{{ ref.source_object }}</a></td>
            <td>{{ ref.source_model_label|capfirst }}</td>
            <td>{{ ref.cf_label }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% if page.has_other_pages %}
    <div class="card-footer">
      {% include 'inc/paginator.html' with paginator=page.paginator page=page %}
    </div>
  {% endif %}
</div>
```

- [ ] **Step 4: Write `netbox_cf_backrefs/template_content.py`**

> Approach: register one extension per **installed** content type at module import. The extension's `full_width_page()` calls `get_reverse_cf_references()`, returns `""` when there are no rows, otherwise renders the panel. This avoids the chicken-and-egg problem where CFs created during a test's `setUpTestData` would otherwise miss the import-time registration window.

```python
"""Dynamic PluginTemplateExtension registration.

For every installed NetBox model, register a backref panel extension. The
extension renders nothing unless the current object has at least one
incoming object/multi-object CF reference. Discovery happens at module
import; the per-render call into utils handles all dynamic CF state.
"""
import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import InvalidPage, Paginator
from django.template.loader import render_to_string
from netbox.plugins import PluginTemplateExtension, get_plugin_config

from .utils import get_reverse_cf_references

logger = logging.getLogger("netbox_cf_backrefs")

PAGE_QUERY_PARAM = "cfbackrefs_page"


def _build_extension(model_label: str):
    class _Extension(PluginTemplateExtension):
        models = [model_label]

        def full_width_page(self):
            obj = self.context["object"]
            request = self.context["request"]
            try:
                refs = list(get_reverse_cf_references(obj))
            except Exception:
                logger.exception("Failed to compute backrefs for %r", obj)
                return ""

            if not refs:
                return ""

            page_size = get_plugin_config("netbox_cf_backrefs", "page_size") or 50
            paginator = Paginator(refs, page_size)
            try:
                page = paginator.page(request.GET.get(PAGE_QUERY_PARAM, 1))
            except InvalidPage:
                page = paginator.page(paginator.num_pages)

            return render_to_string(
                "netbox_cf_backrefs/panel.html",
                {"page": page, "total": len(refs), "object": obj},
                request=request,
            )

    _Extension.__name__ = f"CFBackrefsExtension_{model_label.replace('.', '_')}"
    return _Extension


def _discover_target_model_labels() -> list[str]:
    """Return `app_label.model` strings for every installed content type."""
    labels: list[str] = []
    for ct in ContentType.objects.all():
        if not apps.is_installed(ct.app_label):
            continue
        try:
            if ct.model_class() is None:
                continue
        except Exception:
            continue
        labels.append(f"{ct.app_label}.{ct.model}")
    return labels


template_extensions = [_build_extension(label) for label in _discover_target_model_labels()]
```

> **NetBox API note for the implementer:** NetBox 4.5+ exposes the target via the `models` class attribute (a list of `"app_label.model"` strings). If your local NetBox build still uses the older `model = "..."` singular form, swap that single line — keep the test as the source of truth.

- [ ] **Step 5: Run the integration test — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content -v 2 --keepdb`
Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add netbox_cf_backrefs/template_content.py netbox_cf_backrefs/templates/netbox_cf_backrefs/panel.html netbox_cf_backrefs/tests/test_template_content.py
git commit -m "feat: render Referenced by CF panel on object detail pages"
```

---

## Task 9: Suppress panel when zero references

The behavior was implemented in Task 8 (`if not refs: return ""`); this task locks it in with two tests.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_template_content.py`

- [ ] **Step 1: Append both tests inside `PanelRenderTests`**

```python
    def test_panel_absent_when_no_references(self):
        # CF exists targeting Contact, but no source object references this contact.
        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Referenced by Custom Fields", response.content.decode())

    def test_panel_absent_when_no_cfs_target_the_model(self):
        # No CF created at all.
        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Referenced by Custom Fields", response.content.decode())
```

- [ ] **Step 2: Run — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content -v 2 --keepdb`
Expected: OK, 3 tests.

- [ ] **Step 3: Commit**

```bash
git add netbox_cf_backrefs/tests/test_template_content.py
git commit -m "test: lock in panel suppression when no references exist"
```

---

## Task 10: Pagination via `cfbackrefs_page` query param

Pagination logic is already in `template_content.py` (Task 8); this task verifies it.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_template_content.py`

- [ ] **Step 1: Append the test**

```python
    def test_pagination_with_overridden_page_size(self):
        from django.test import override_settings
        from bs4 import BeautifulSoup

        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        for i in range(5):
            Device.objects.create(
                name=f"dev-{i}",
                site=self.site,
                device_type=self.device_type,
                role=self.role,
                custom_field_data={"tech_contact": self.contact.pk},
            )

        plugins_config = {
            "netbox_cf_backrefs": {
                "page_size": 2,
                "excluded_custom_fields": [],
            }
        }

        def _panel_row_count(html: str) -> int:
            soup = BeautifulSoup(html, "html.parser")
            header = soup.find(
                "h5", string=lambda s: s and "Referenced by Custom Fields" in s
            )
            self.assertIsNotNone(header, "Panel header missing")
            table = header.find_parent("div").find("table")
            return len(table.find("tbody").find_all("tr"))

        with override_settings(PLUGINS_CONFIG=plugins_config):
            response = self.client.get(
                reverse("tenancy:contact", args=[self.contact.pk])
            )
            self.assertEqual(_panel_row_count(response.content.decode()), 2)

            response = self.client.get(
                reverse("tenancy:contact", args=[self.contact.pk]),
                {"cfbackrefs_page": 3},
            )
            self.assertEqual(_panel_row_count(response.content.decode()), 1)
```

- [ ] **Step 2: Run — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content -v 2 --keepdb`
Expected: OK.

- [ ] **Step 3: Commit**

```bash
git add netbox_cf_backrefs/tests/test_template_content.py
git commit -m "test: verify cfbackrefs_page pagination with overridden page_size"
```

---

## Task 11: Lock-in test for the no-permission-filter decision

The spec deliberately chose option B: a viewer without view permission on the source object **still sees the row**. This test exists so a future refactor can't quietly tighten it.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_template_content.py`

- [ ] **Step 1: Append the test**

```python
    def test_user_without_view_permission_still_sees_referencing_row(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission

        User = get_user_model()
        plain = User.objects.create_user("plain", password="p")
        plain.user_permissions.add(
            Permission.objects.get(codename="view_contact"),
        )

        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        device = Device.objects.create(
            name="dev-restricted",
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )

        self.client.force_login(plain)
        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        # Even though `plain` has no view_device permission, the row is still rendered.
        self.assertIn(device.get_absolute_url(), body)
        self.assertIn("dev-restricted", body)
```

- [ ] **Step 2: Run — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content -v 2 --keepdb`
Expected: OK.

- [ ] **Step 3: Commit**

```bash
git add netbox_cf_backrefs/tests/test_template_content.py
git commit -m "test: lock in design decision — no permission filtering on backref rows"
```

---

## Task 12: Panel exception safety

The `try/except` in `full_width_page` was added in Task 8; this task tests it.

**Files:**
- Modify: `netbox_cf_backrefs/tests/test_template_content.py`

- [ ] **Step 1: Append the test**

```python
    def test_panel_does_not_break_object_page_when_utils_raises(self):
        from unittest.mock import patch

        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        Device.objects.create(
            name="dev-broken",
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )

        with patch(
            "netbox_cf_backrefs.template_content.get_reverse_cf_references",
            side_effect=RuntimeError("boom"),
        ):
            response = self.client.get(
                reverse("tenancy:contact", args=[self.contact.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Referenced by Custom Fields", response.content.decode())
```

- [ ] **Step 2: Run — verify pass**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs.tests.test_template_content -v 2 --keepdb`
Expected: OK.

- [ ] **Step 3: Commit**

```bash
git add netbox_cf_backrefs/tests/test_template_content.py
git commit -m "test: ensure object page survives backrefs computation failures"
```

---

## Task 13: Finalize README and CHANGELOG

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Replace `README.md` with the full version**

````markdown
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
    }
}
```

Restart NetBox.

## Settings

| Key | Default | Description |
|---|---|---|
| `page_size` | `50` | Rows per page in the panel paginator. |
| `excluded_custom_fields` | `[]` | List of CF *names* (not labels) to suppress from all backref panels. |

## Behavior notes

- **No permission filtering.** Every viewer sees the same complete list of references. If user X has no `view` permission on Device-1 but Device-1 references the Contact they are viewing, Device-1 will still appear (as a clickable link). Choose this plugin only if that trade-off is acceptable for your deployment.
- **CFs marked `ui_visible='hidden'` are skipped** — admin-only CFs won't leak through the panel.
- **Restart required when adding/removing object-CFs** — the plugin discovers CF target models at NetBox startup. Adding a new CF later requires a NetBox restart for it to take effect on the panel.
- **Empty panels are hidden.** If no objects currently reference the target via CFs, the panel is not rendered.

## Development

```bash
make test       # /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs --keepdb
make lint       # ruff + djlint --check
make format     # ruff format + djlint --reformat
```

## License

Apache-2.0
````

- [ ] **Step 2: Update `CHANGELOG.md`**

```markdown
# Changelog

## 0.1.0 — 2026-05-06

- Initial release.
- Inline `Referenced by Custom Fields` panel on object detail pages, listing source object, source type, and custom field for every object/multi-object CF reference pointing to the current object.
- `page_size` and `excluded_custom_fields` plugin settings.
- Skips CFs with `ui_visible='hidden'`.
- Resilient to uninstalled source models (logs a warning and continues).
- No permission filtering on rows — design decision documented in README.
```

- [ ] **Step 3: Run the full test suite**

Run: `/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py test netbox_cf_backrefs -v 2 --keepdb`
Expected: OK across every test.

- [ ] **Step 4: Run lint**

Run: `make lint`
Expected: no findings. If `ruff` or `djlint` flags anything, fix and re-run.

- [ ] **Step 5: Manual smoke test**

1. Restart NetBox with the plugin installed.
2. Create an object CF (`Type: Object`, target `Contact`, attached to `Device`) named `tech_contact`.
3. Edit one device, set its `tech_contact` to a specific contact.
4. Open that contact's detail page.
5. Confirm the **Referenced by Custom Fields** panel appears with one row pointing to the device.
6. Delete the device's CF value, reload the contact page, confirm the panel disappears.

- [ ] **Step 6: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: finalize README and CHANGELOG for v0.1.0"
```

---

## Self-review

**Spec coverage:**
- Display (panel, header, three columns, suppression on empty) — Tasks 8, 9
- Architecture (dynamic registration, per-page query flow) — Task 8
- Settings (page_size, excluded_custom_fields) — Tasks 1 (defaults), 5 (filter), 10 (override test)
- Permissions decision (B) — Task 11
- Error handling (orphan JSON keys covered by current-CF iteration; uninstalled source model — Task 7; multi-object stored as list — Task 3; double-CF same source — Task 4; panel exception isolation — Task 12)
- Testing (every spec test bullet has a corresponding task)
- README / restart caveat / permission warning — Task 13

No spec gaps detected.

**Placeholder scan:** None. Each step has concrete code or a concrete command.

**Type consistency:**
- `Reference` defined in Task 2 with fields `source_object`, `source_model_label`, `cf_name`, `cf_label`. All later code uses the same names.
- `get_reverse_cf_references(target_obj) -> Iterator[Reference]` signature stable across tasks.
- Setting key `excluded_custom_fields` consistent in Task 1 (PluginConfig.default_settings), Task 5 (utils filter), Task 13 (README).
- Pagination query param `cfbackrefs_page` consistent in Task 8 (template_content) and Task 10 (test).
