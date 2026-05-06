"""Reverse lookup of object / multi-object custom field references."""
import logging
from collections.abc import Iterator
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField
from netbox.plugins import get_plugin_config

logger = logging.getLogger("netbox_cf_backrefs")


def _excluded_cf_names() -> set[str]:
    return set(get_plugin_config("netbox_cf_backrefs", "excluded_custom_fields") or [])


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

    cfs = (
        CustomField.objects.filter(
            type__in=("object", "multiobject"),
            related_object_type=target_ct,
        )
        .exclude(name__in=_excluded_cf_names())
        .exclude(ui_visible="hidden")
    )

    for cf in cfs:
        cf_label = cf.label or cf.name
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
            else:  # "multiobject"
                lookup = {f"custom_field_data__{cf.name}__contains": [target_obj.pk]}
            for src in source_model.objects.filter(**lookup):
                yield Reference(
                    source_object=src,
                    source_model_label=source_ct.model,
                    cf_name=cf.name,
                    cf_label=cf_label,
                )
