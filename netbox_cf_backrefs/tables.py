"""django_tables2 tables for the CF Backrefs panel and tab."""
import django_tables2 as tables
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from netbox.tables import BaseTable


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


def _actions_column():
    """A fresh per-row Actions column holding the filter-icon peer pivot."""
    return tables.Column(
        empty_values=(),
        verbose_name=_("Actions"),
        orderable=False,
        attrs={"td": {"class": "text-end text-nowrap noprint"}},
    )


class _PeerActionsMixin:
    """Per-row "Show peers" filter-icon action shared by the panel and tab tables.

    Subclasses declare an ``actions`` column (via ``_actions_column()``) and are
    constructed with ``target_pk`` — the object whose detail page is rendered.
    The button pivots to the source model's list filtered by the CF that
    produced the row, i.e. ``/<app>/<model>/?cf_<cf_name>=<target_pk>``.
    """

    def __init__(self, *args, target_pk=None, **kwargs):
        self._target_pk = target_pk
        super().__init__(*args, **kwargs)

    def render_actions(self, record):
        url = _peer_list_url(record, self._target_pk)
        if url is None:
            return mark_safe(
                '<span class="btn-group">'
                '<span class="btn btn-sm btn-outline-secondary disabled" aria-hidden="true">'
                '<i class="mdi mdi-filter"></i></span></span>'
            )
        label = _("Show peers referencing this target")
        return format_html(
            '<span class="btn-group">'
            '<a class="btn btn-sm btn-primary" href="{}" type="button" '
            'aria-label="{}" title="{}">'
            '<i class="mdi mdi-filter"></i></a></span>',
            url, label, label,
        )

    def render_source_model_label(self, value):
        return value.capitalize()


class CFBackrefTable(_PeerActionsMixin, tables.Table):
    source_object = tables.Column(
        linkify=True,
        verbose_name=_("Source object"),
    )
    source_model_label = tables.Column(verbose_name=_("Source type"))
    cf_label = tables.Column(verbose_name=_("Custom field"))
    actions = _actions_column()

    class Meta:
        attrs = {"class": "table table-hover object-list"}
        empty_text = _("No references")
        prefix = "cfbackrefs_"


class CFBackrefTabTable(_PeerActionsMixin, BaseTable):
    """Minimal list-view table used by the CF Backrefs tab.

    Mirrors the visual baseline of `netbox_custom_objects`'s combined-tabs
    view — no sortable column headers, no filter sidebar. Rows are `Reference`
    dataclasses (not Django model instances), which is why the base is
    `BaseTable` rather than `NetBoxTable`. The trailing `actions` column renders
    the per-row filter icon.
    """

    source_object = tables.Column(
        linkify=True,
        verbose_name=_("Source object"),
        orderable=False,
    )
    source_model_label = tables.Column(verbose_name=_("Source type"), orderable=False)
    cf_label = tables.Column(verbose_name=_("Custom field"), orderable=False)
    cf_type = tables.Column(verbose_name=_("CF type"), orderable=False)
    actions = _actions_column()

    class Meta(BaseTable.Meta):
        attrs = {"class": "table table-hover object-list"}
        empty_text = _("No references")
        fields = ("source_object", "source_model_label", "cf_label", "cf_type", "actions")
        default_columns = (
            "source_object", "source_model_label", "cf_label", "cf_type", "actions",
        )

    def render_cf_type(self, value):
        return {"object": "Object", "multiobject": "Multi-object"}.get(value, value)
