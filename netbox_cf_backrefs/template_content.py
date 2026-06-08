"""Dynamic PluginTemplateExtension registration.

Register a backref panel extension for every installed model whose display
mode includes the panel (see ``display.resolve_display``). The mode is read
once at import, so changing it requires a NetBox restart. A registered
extension still renders nothing unless the object has at least one incoming
object/multi-object CF reference.
"""
import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django_tables2 import RequestConfig
from netbox.plugins import PluginTemplateExtension, get_plugin_config
from utilities.paginator import EnhancedPaginator

from .display import shows_panel
from .tables import CFBackrefTable
from .utils import get_reverse_cf_references

logger = logging.getLogger("netbox_cf_backrefs")

PAGE_QUERY_PARAM = "cfbackrefs_page"
PER_PAGE_QUERY_PARAM = "cfbackrefs_per_page"


def _resolve_per_page(request, default: int) -> int:
    raw = request.GET.get(PER_PAGE_QUERY_PARAM)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value >= 1 else default


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
            per_page = _resolve_per_page(request, page_size)
            table = CFBackrefTable(refs)
            # RequestConfig binds ?cfbackrefs_sort and ?cfbackrefs_page to the
            # table (django_tables2 honors Meta.prefix) and catches InvalidPage.
            RequestConfig(request, paginate={
                "paginator_class": EnhancedPaginator,
                "per_page": per_page,
                "orphans": 0,
            }).configure(table)

            return render_to_string(
                "netbox_cf_backrefs/panel.html",
                {"table": table, "total": len(refs)},
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


template_extensions = [
    _build_extension(label)
    for label in _discover_target_model_labels()
    if shows_panel(label)
]
