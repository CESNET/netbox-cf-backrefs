"""Per-target-model display-mode resolution (panel vs tab vs both vs none).

Operators choose how custom-field backrefs surface on each target model via
``PLUGINS_CONFIG``::

    "netbox_cf_backrefs": {
        "default_display": "panel",       # panel | tab | both | none
        "display_overrides": {            # {"app_label.model": mode}
            "dcim.device": "tab",
        },
    }

Both surfaces are always registered; only *rendering* is gated here, so config
changes take effect on the next request with no NetBox restart. Custom Object
dynamic models are forced to ``panel`` because their tab route is structurally
unreversible (see ``docs/TODO-custom-objects-tab.md``).
"""
import logging
import re

from netbox.plugins import get_plugin_config

logger = logging.getLogger("netbox_cf_backrefs")

VALID_MODES = frozenset({"panel", "tab", "both", "none"})
DEFAULT_MODE = "panel"

# Dynamic Custom Object models are named ``table<id>model`` in the
# ``netbox_custom_objects`` app (e.g. ``table3model``). Static models in that
# app (customobjecttype, customobjecttypefield, customobjectobjecttype) do not
# match the pattern and are treated as ordinary models.
_CO_APP = "netbox_custom_objects"
_CO_MODEL_RE = re.compile(r"^table\d+model$", re.IGNORECASE)


def _is_custom_object(label: str) -> bool:
    app, _, model = label.partition(".")
    return app == _CO_APP and bool(_CO_MODEL_RE.match(model))


def _default_mode() -> str:
    # Pass the literal default explicitly: get_plugin_config only falls back to
    # the plugin's default_settings when those were merged at startup, which
    # django.test.override_settings (and a hand-edited PLUGINS_CONFIG) bypass.
    mode = get_plugin_config("netbox_cf_backrefs", "default_display", DEFAULT_MODE)
    return mode if mode in VALID_MODES else DEFAULT_MODE


def _overrides() -> dict:
    raw = get_plugin_config("netbox_cf_backrefs", "display_overrides", {}) or {}
    # Normalize keys to lowercase so "Tenancy.Contact" matches _meta.label_lower.
    return {str(key).lower(): value for key, value in raw.items()}


def resolve_display(label: str) -> str:
    """Return the effective mode ('panel'|'tab'|'both'|'none') for a model label."""
    default = _default_mode()
    mode = _overrides().get(label, default)
    if mode not in VALID_MODES:
        mode = default
    # Custom Objects can't host the tab; coerce tab/both down to panel.
    if _is_custom_object(label) and mode in ("tab", "both"):
        mode = "panel"
    return mode


def shows_panel(label: str) -> bool:
    return resolve_display(label) in ("panel", "both")


def shows_tab(label: str) -> bool:
    return resolve_display(label) in ("tab", "both")


def validate_display_config() -> None:
    """Log (once, at startup) any invalid or coerced display configuration.

    Never raises — this runs from ``AppConfig.ready()`` and must not break
    NetBox startup.
    """
    try:
        default = get_plugin_config("netbox_cf_backrefs", "default_display", DEFAULT_MODE)
        if default not in VALID_MODES:
            logger.warning(
                "netbox_cf_backrefs: invalid default_display %r; using %r. Valid modes: %s",
                default, DEFAULT_MODE, sorted(VALID_MODES),
            )
        raw = get_plugin_config("netbox_cf_backrefs", "display_overrides", {}) or {}
        for key, value in raw.items():
            label = str(key).lower()
            if value not in VALID_MODES:
                logger.warning(
                    "netbox_cf_backrefs: invalid display_overrides[%r]=%r; "
                    "falling back to default. Valid modes: %s",
                    key, value, sorted(VALID_MODES),
                )
            elif _is_custom_object(label) and value in ("tab", "both"):
                logger.warning(
                    "netbox_cf_backrefs: display_overrides[%r]=%r coerced to 'panel' "
                    "(Custom Object models cannot host the CF Backrefs tab).",
                    key, value,
                )
    except Exception:
        logger.exception("netbox_cf_backrefs: failed to validate display config")
