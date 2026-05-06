from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from tenancy.models import Contact
from utilities.testing import TestCase

from netbox_cf_backrefs.utils import Reference, get_reverse_cf_references

from ._factories import make_cf


class GetReverseCFReferencesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Minimal device prerequisites (NetBox requires these to create a Device).
        cls.site = Site.objects.create(name="S1", slug="s1")
        manufacturer = Manufacturer.objects.create(name="M1", slug="m1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="DT1", slug="dt1"
        )
        cls.role = DeviceRole.objects.create(name="R1", slug="r1")

        # Contacts have an M2M `groups` relationship in NetBox 4.x; we don't
        # need a group for these tests, so omit it entirely.
        cls.target_a = Contact.objects.create(name="Alice")
        cls.target_b = Contact.objects.create(name="Bob")

    def _make_device(self, name: str, cf_data: dict | None = None) -> Device:
        return Device.objects.create(
            name=name,
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data=cf_data or {},
        )

    def test_returns_empty_when_no_cfs_target_the_model(self):
        result = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(result, [])

    def test_object_cf_returns_only_matching_source(self):
        make_cf(
            name="tech_contact",
            label="Technical contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        match = self._make_device("dev-match", {"tech_contact": self.target_a.pk})
        self._make_device("dev-other", {"tech_contact": self.target_b.pk})

        refs = list(get_reverse_cf_references(self.target_a))

        self.assertEqual(len(refs), 1)
        ref = refs[0]
        self.assertIsInstance(ref, Reference)
        self.assertEqual(ref.source_object, match)
        self.assertEqual(ref.source_model_label, "device")
        self.assertEqual(ref.cf_name, "tech_contact")
        self.assertEqual(ref.cf_label, "Technical contact")

    def test_multiobject_cf_matches_when_pk_in_list(self):
        make_cf(
            name="responsible_contacts",
            label="Responsible contacts",
            cf_type="multiobject",
            target_model=Contact,
            source_models=[Device],
        )
        match = self._make_device(
            "dev-multi-match",
            {"responsible_contacts": [self.target_a.pk, self.target_b.pk]},
        )
        self._make_device(
            "dev-multi-other", {"responsible_contacts": [self.target_b.pk]}
        )

        refs = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].source_object, match)
        self.assertEqual(refs[0].cf_name, "responsible_contacts")

    def test_mixed_source_models(self):
        from circuits.models import Circuit, CircuitType, Provider

        make_cf(
            name="primary_contact",
            label="Primary contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device, Circuit],
        )
        device = self._make_device("dev-mixed", {"primary_contact": self.target_a.pk})

        provider = Provider.objects.create(name="P1", slug="p1")
        ctype = CircuitType.objects.create(name="CT1", slug="ct1")
        circuit = Circuit.objects.create(
            cid="C-1",
            provider=provider,
            type=ctype,
            custom_field_data={"primary_contact": self.target_a.pk},
        )

        refs = list(get_reverse_cf_references(self.target_a))
        sources = {(r.source_object, r.source_model_label) for r in refs}
        self.assertEqual(
            sources,
            {(device, "device"), (circuit, "circuit")},
        )

    def test_two_cfs_on_same_source_yield_two_rows(self):
        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        make_cf(
            name="escalation_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        self._make_device(
            "dev-double",
            {
                "tech_contact": self.target_a.pk,
                "escalation_contact": self.target_a.pk,
            },
        )

        refs = list(get_reverse_cf_references(self.target_a))
        cf_names = sorted(r.cf_name for r in refs)
        self.assertEqual(cf_names, ["escalation_contact", "tech_contact"])

    def test_excluded_custom_fields_setting_skips_cf(self):
        from django.test import override_settings

        make_cf(
            name="hidden_link",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        self._make_device("dev-hidden", {"hidden_link": self.target_a.pk})

        with override_settings(
            PLUGINS_CONFIG={
                "netbox_cf_backrefs": {
                    "page_size": 50,
                    "excluded_custom_fields": ["hidden_link"],
                }
            }
        ):
            refs = list(get_reverse_cf_references(self.target_a))
        self.assertEqual(refs, [])
