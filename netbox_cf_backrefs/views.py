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

            source_type_options = sorted({r.source_model_label for r in refs})
            cf_name_options = sorted({(r.cf_name, r.cf_label) for r in refs})
            cf_type_options = sorted({r.cf_type for r in refs})

            ctx = {
                "object": instance,
                "tab": self.tab,
                "table": table,
                "table_modal": f"{table.name}_config",
                "total": len(filtered),
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

    _CFBackrefsTabView.__name__ = (
        f"CFBackrefsTabView_{model_class._meta.app_label}_{model_class._meta.model_name}"
    )
    return _CFBackrefsTabView


def _register_tabs():
    """Register one ObjectView+tab per installed content type at import time."""
    for ct in ContentType.objects.all():
        if not apps.is_installed(ct.app_label):
            continue
        try:
            model_class = ct.model_class()
        except Exception as exc:
            logger.debug(
                "Skipping CF Backrefs tab registration for %s.%s: %s",
                ct.app_label, ct.model, exc,
            )
            continue
        if model_class is None:
            continue
        view_cls = _make_tab_view(model_class)
        register_model_view(model_class, name="cf_backrefs", path="cf-backrefs")(view_cls)


_register_tabs()
