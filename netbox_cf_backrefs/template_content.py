"""Dynamic PluginTemplateExtension registration.

For every installed NetBox model, register a backref panel extension. The
extension renders nothing unless the current object has at least one
incoming object/multi-object CF reference. Discovery happens at module
import; the per-render call into utils handles all dynamic CF state.
"""
import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import InvalidPage
from django.template.loader import render_to_string
from netbox.plugins import PluginTemplateExtension, get_plugin_config
from utilities.paginator import EnhancedPaginator

from .tables import CFBackrefTable
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
            table = CFBackrefTable(refs)
            try:
                table.paginate(
                    page=request.GET.get(PAGE_QUERY_PARAM, 1),
                    per_page=request.GET.get("cfbackrefs_per_page", page_size),
                    paginator_class=EnhancedPaginator,
                    orphans=0,
                )
            except InvalidPage:
                table.paginate(
                    page=table.paginator.num_pages,
                    per_page=page_size,
                    paginator_class=EnhancedPaginator,
                    orphans=0,
                )

            return render_to_string(
                "netbox_cf_backrefs/panel.html",
                {"table": table, "total": len(refs), "object": obj},
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
