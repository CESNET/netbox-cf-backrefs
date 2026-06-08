"""Unit tests for display-mode resolution (`display.py`).

These cover the pure decision logic — which surface(s) a model resolves to —
independent of registration. `resolve_display`/`shows_*` read PLUGINS_CONFIG
live, so `override_settings` controls them directly; no DB or registration is
needed (hence `SimpleTestCase`).

The *registration* side (a disabled surface is never wired at startup) can't be
exercised here: routes are baked once at startup, so this suite runs with
`default_display="both"` (see `tests/configuration.py`). The "disabled" direction
is therefore asserted at this decision-logic level, which is what drives
registration.
"""
from django.test import SimpleTestCase, override_settings

from netbox_cf_backrefs.display import (
    _is_custom_object,
    resolve_display,
    shows_panel,
    shows_tab,
)


def _cfg(**inner):
    return {"netbox_cf_backrefs": inner}


class ResolveDisplayTests(SimpleTestCase):
    @override_settings(PLUGINS_CONFIG=_cfg())
    def test_empty_config_defaults_to_panel(self):
        # No default_display set: the literal "panel" fallback applies (the
        # default_settings merge is bypassed by override_settings).
        self.assertEqual(resolve_display("tenancy.contact"), "panel")
        self.assertTrue(shows_panel("tenancy.contact"))
        self.assertFalse(shows_tab("tenancy.contact"))

    @override_settings(PLUGINS_CONFIG=_cfg(default_display="tab"))
    def test_explicit_default_tab(self):
        self.assertEqual(resolve_display("dcim.site"), "tab")
        self.assertFalse(shows_panel("dcim.site"))
        self.assertTrue(shows_tab("dcim.site"))

    @override_settings(PLUGINS_CONFIG=_cfg(
        default_display="panel",
        display_overrides={"dcim.device": "tab"},
    ))
    def test_override_wins_over_default(self):
        self.assertEqual(resolve_display("dcim.device"), "tab")
        self.assertEqual(resolve_display("dcim.site"), "panel")

    @override_settings(PLUGINS_CONFIG=_cfg(default_display="both"))
    def test_both_shows_each(self):
        self.assertTrue(shows_panel("dcim.site"))
        self.assertTrue(shows_tab("dcim.site"))

    @override_settings(PLUGINS_CONFIG=_cfg(default_display="none"))
    def test_none_shows_neither(self):
        self.assertFalse(shows_panel("dcim.site"))
        self.assertFalse(shows_tab("dcim.site"))

    @override_settings(PLUGINS_CONFIG=_cfg(
        default_display="tab",
        display_overrides={"dcim.device": "bogus"},
    ))
    def test_invalid_override_falls_back_to_default(self):
        self.assertEqual(resolve_display("dcim.device"), "tab")

    @override_settings(PLUGINS_CONFIG=_cfg(default_display="nonsense"))
    def test_invalid_default_falls_back_to_panel(self):
        self.assertEqual(resolve_display("dcim.device"), "panel")

    @override_settings(PLUGINS_CONFIG=_cfg(
        default_display="panel",
        display_overrides={"Tenancy.Contact": "tab"},
    ))
    def test_override_keys_are_case_insensitive(self):
        self.assertEqual(resolve_display("tenancy.contact"), "tab")


class IsCustomObjectTests(SimpleTestCase):
    def test_dynamic_custom_object_labels(self):
        self.assertTrue(_is_custom_object("netbox_custom_objects.table1model"))
        self.assertTrue(_is_custom_object("netbox_custom_objects.table999model"))

    def test_non_custom_object_labels(self):
        for label in (
            "netbox_custom_objects.customobjecttype",
            "netbox_custom_objects.customobjecttypefield",
            "netbox_custom_objects.customobjectobjecttype",
            "tenancy.contact",
            "someapp.table9model",  # right name shape, wrong app
        ):
            self.assertFalse(_is_custom_object(label), label)


class CustomObjectCoercionTests(SimpleTestCase):
    CO = "netbox_custom_objects.table7model"

    @override_settings(PLUGINS_CONFIG=_cfg(display_overrides={CO: "tab"}))
    def test_tab_override_coerced_to_panel(self):
        self.assertEqual(resolve_display(self.CO), "panel")

    @override_settings(PLUGINS_CONFIG=_cfg(display_overrides={CO: "both"}))
    def test_both_override_coerced_to_panel(self):
        self.assertEqual(resolve_display(self.CO), "panel")

    @override_settings(PLUGINS_CONFIG=_cfg(default_display="tab"))
    def test_default_tab_coerced_to_panel_for_custom_object(self):
        # A custom object inherits the global default but still can't host a tab.
        self.assertEqual(resolve_display(self.CO), "panel")

    @override_settings(PLUGINS_CONFIG=_cfg(display_overrides={CO: "none"}))
    def test_none_override_not_coerced(self):
        # "none" is not a tab, so no coercion — the model shows nothing.
        self.assertEqual(resolve_display(self.CO), "none")
