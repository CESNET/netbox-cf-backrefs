"""Test factories for netbox_cf_backrefs.

Reusable helpers to build CustomFields without boilerplate in every test
method. Kept inside `tests/` so they ship with the test suite but are not
part of the importable plugin API.
"""
from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField


def make_cf(
    *,
    name: str,
    cf_type: str,
    target_model,
    source_models,
    label: str = "",
    ui_visible: str = "always",
):
    """Create a CustomField of `cf_type` ("object" or "multiobject") and
    attach it to `source_models`.

    `target_model` is the Django model class the CF points to.
    `source_models` is an iterable of Django model classes the CF is attached to.
    """
    cf = CustomField.objects.create(
        name=name,
        label=label or name,
        type=cf_type,
        related_object_type=ContentType.objects.get_for_model(target_model),
        ui_visible=ui_visible,
    )
    cf.object_types.set(
        ContentType.objects.get_for_model(m) for m in source_models
    )
    return cf
