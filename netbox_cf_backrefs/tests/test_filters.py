from django.test import SimpleTestCase

from netbox_cf_backrefs.filters import apply_filters
from netbox_cf_backrefs.utils import Reference


class _FakeObject:
    """Minimal stand-in for a NetBox model instance — only str() is needed."""

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return self._name


def _ref(name, model="device", cf_name="tech_contact", cf_label="Technical contact",
         cf_type="object"):
    return Reference(
        source_object=_FakeObject(name),
        source_model_label=model,
        cf_name=cf_name,
        cf_label=cf_label,
        cf_type=cf_type,
    )


class ApplyFiltersTests(SimpleTestCase):
    def setUp(self):
        self.refs = [
            _ref("dev-1", model="device", cf_name="tech_contact",
                 cf_label="Technical contact", cf_type="object"),
            _ref("dev-2", model="device", cf_name="responsible",
                 cf_label="Responsible contacts", cf_type="multiobject"),
            _ref("circuit-1", model="circuit", cf_name="tech_contact",
                 cf_label="Technical contact", cf_type="object"),
        ]

    def test_empty_params_returns_all(self):
        self.assertEqual(apply_filters(self.refs, {}), self.refs)

    def test_filter_by_source_type(self):
        result = apply_filters(self.refs, {"source_type": "device"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1", "dev-2"])

    def test_filter_by_cf_name(self):
        result = apply_filters(self.refs, {"cf_name": "tech_contact"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1", "circuit-1"])

    def test_filter_by_cf_type(self):
        result = apply_filters(self.refs, {"cf_type": "multiobject"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-2"])

    def test_quick_search_matches_source_object_name(self):
        result = apply_filters(self.refs, {"q": "circuit"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["circuit-1"])

    def test_quick_search_matches_cf_label_case_insensitive(self):
        result = apply_filters(self.refs, {"q": "RESPONSIBLE"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-2"])

    def test_quick_search_matches_source_model_label(self):
        result = apply_filters(self.refs, {"q": "device"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1", "dev-2"])

    def test_quick_search_matches_cf_name(self):
        result = apply_filters(self.refs, {"q": "responsible"})
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-2"])

    def test_combined_filter_and_q(self):
        result = apply_filters(
            self.refs, {"source_type": "device", "q": "tech"}
        )
        names = [str(r.source_object) for r in result]
        self.assertEqual(names, ["dev-1"])

    def test_unknown_filter_value_returns_empty(self):
        result = apply_filters(self.refs, {"source_type": "vlan"})
        self.assertEqual(result, [])
