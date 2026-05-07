"""django_tables2 tables for the CF Backrefs panel and tab."""
import django_tables2 as tables
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from netbox.tables import BaseTable


class CFBackrefTable(tables.Table):
    source_object = tables.Column(
        linkify=True,
        verbose_name=_("Source object"),
    )
    source_model_label = tables.Column(verbose_name=_("Source type"))
    cf_label = tables.Column(verbose_name=_("Custom field"))

    class Meta:
        attrs = {"class": "table table-hover object-list"}
        empty_text = _("No references")
        prefix = "cfbackrefs_"

    def render_source_model_label(self, value):
        return value.capitalize()


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


class CFBackrefTabTable(BaseTable):
    """Minimal list-view table used by the CF Backrefs tab.

    Mirrors the visual baseline of `netbox_custom_objects`'s combined-tabs
    view — no sortable column headers, no Configure-Table modal, no filter
    sidebar. Rows are `Reference` dataclasses (not Django model instances),
    which is why the base is `BaseTable` rather than `NetBoxTable`. The
    leading `pivot` column renders the per-row filter icon.
    """

    pivot = tables.Column(
        empty_values=(),
        verbose_name="",
        orderable=False,
    )
    source_object = tables.Column(
        linkify=True,
        verbose_name=_("Source object"),
        orderable=False,
    )
    source_model_label = tables.Column(verbose_name=_("Source type"), orderable=False)
    cf_label = tables.Column(verbose_name=_("Custom field"), orderable=False)
    cf_type = tables.Column(verbose_name=_("CF type"), orderable=False)

    class Meta(BaseTable.Meta):
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
