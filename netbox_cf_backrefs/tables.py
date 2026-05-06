"""django_tables2 Table for the backrefs panel."""
import django_tables2 as tables
from django.utils.translation import gettext_lazy as _


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
        fields = ("source_object", "source_model_label", "cf_label")

    def render_source_model_label(self, value):
        return value.capitalize() if isinstance(value, str) else value
