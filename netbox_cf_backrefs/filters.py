"""In-memory filtering helpers for the CF Backrefs tab.

Operates on `list[Reference]` (frozen dataclasses) — not a Django QuerySet —
so this is plain Python, not a `django_filters.FilterSet`.
"""
from .utils import Reference


def apply_filters(refs: list[Reference], params) -> list[Reference]:
    """Narrow `refs` by sidebar filters and quick search.

    Recognized keys in `params` (a dict-like, e.g. `request.GET`):
    - `source_type`: exact match against `Reference.source_model_label`
    - `cf_name`: exact match against `Reference.cf_name`
    - `cf_type`: exact match against `Reference.cf_type`
    - `q`: case-insensitive substring across source object str repr,
      source model label, CF label, and CF name
    """
    source_type = params.get("source_type")
    cf_name = params.get("cf_name")
    cf_type = params.get("cf_type")
    q = (params.get("q") or "").strip().lower()

    out = list(refs)
    if source_type:
        out = [r for r in out if r.source_model_label == source_type]
    if cf_name:
        out = [r for r in out if r.cf_name == cf_name]
    if cf_type:
        out = [r for r in out if r.cf_type == cf_type]
    if q:
        out = [
            r for r in out
            if q in str(r.source_object).lower()
            or q in r.source_model_label.lower()
            or q in r.cf_label.lower()
            or q in r.cf_name.lower()
        ]
    return out
