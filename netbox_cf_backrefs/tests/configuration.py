"""NetBox configuration for the plugin test suite.

Display surfaces are registered *conditionally at startup* based on each model's
display mode (``default_display`` / ``display_overrides``), and per-model URL
routes are baked when the URLconf is first built — so a route that wasn't
registered at startup can't be reversed later. To exercise BOTH the panel and
the tab in the HTTP tests, run the suite with ``default_display = "both"`` so
every model registers both surfaces. Everything else is inherited from the host
NetBox configuration.

Used via ``NETBOX_CONFIGURATION=netbox_cf_backrefs.tests.configuration`` — see the
Makefile ``test`` target. Production keeps the leaner ``default_display = "panel"``.
"""
from netbox.configuration import *  # noqa: F401, F403

PLUGINS_CONFIG = dict(globals().get("PLUGINS_CONFIG", {}))
PLUGINS_CONFIG["netbox_cf_backrefs"] = {
    **PLUGINS_CONFIG.get("netbox_cf_backrefs", {}),
    "default_display": "both",
}
