"""Reverse lookup of object / multi-object custom field references."""
from dataclasses import dataclass
from typing import Iterator

from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField


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

    cfs = CustomField.objects.filter(
        type__in=("object", "multiobject"),
        related_object_type=target_ct,
    )

    for cf in cfs:
        cf_label = cf.label or cf.name
        for source_ct in cf.object_types.all():
            source_model = source_ct.model_class()
            qs = source_model.objects.filter(
                **{f"custom_field_data__{cf.name}": target_obj.pk}
            )
            for src in qs:
                yield Reference(
                    source_object=src,
                    source_model_label=source_ct.model,
                    cf_name=cf.name,
                    cf_label=cf_label,
                )
