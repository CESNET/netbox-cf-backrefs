from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from django.contrib.auth import get_user_model
from django.urls import reverse
from tenancy.models import Contact
from utilities.testing import TestCase

from ._factories import make_cf


class PanelRenderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user("u1", password="p")
        cls.user.is_superuser = True
        cls.user.save()

        cls.site = Site.objects.create(name="S1", slug="s1")
        manufacturer = Manufacturer.objects.create(name="M1", slug="m1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="DT1", slug="dt1"
        )
        cls.role = DeviceRole.objects.create(name="R1", slug="r1")
        # Contact.groups is M2M in NetBox 4.x; not needed for these tests.
        cls.contact = Contact.objects.create(name="Bob")

    def setUp(self):
        self.client.force_login(self.user)

    def test_panel_renders_with_one_reference(self):
        make_cf(
            name="tech_contact",
            label="Technical contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        device = Device.objects.create(
            name="dev-1",
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )

        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Referenced by Custom Fields", body)
        self.assertIn(device.get_absolute_url(), body)
        self.assertIn("Technical contact", body)

    def test_panel_absent_when_no_references(self):
        # CF exists targeting Contact, but no source object references this contact.
        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Referenced by Custom Fields", response.content.decode())

    def test_panel_absent_when_no_cfs_target_the_model(self):
        # No CF created at all.
        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Referenced by Custom Fields", response.content.decode())

    def test_pagination_with_overridden_page_size(self):
        import re

        from django.test import override_settings

        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        for i in range(5):
            Device.objects.create(
                name=f"dev-{i}",
                site=self.site,
                device_type=self.device_type,
                role=self.role,
                custom_field_data={"tech_contact": self.contact.pk},
            )

        plugins_config = {
            "netbox_cf_backrefs": {
                "page_size": 2,
                "excluded_custom_fields": [],
            }
        }

        def _panel_row_count(html: str) -> int:
            # Locate the panel by its header, then count <tr> inside its <tbody>.
            match = re.search(
                r"Referenced by Custom Fields.*?<tbody>(.*?)</tbody>",
                html,
                re.DOTALL,
            )
            self.assertIsNotNone(match, "Panel <tbody> not found in response")
            return len(re.findall(r"<tr\b", match.group(1)))

        with override_settings(PLUGINS_CONFIG=plugins_config):
            response = self.client.get(
                reverse("tenancy:contact", args=[self.contact.pk])
            )
            self.assertEqual(_panel_row_count(response.content.decode()), 2)

            response = self.client.get(
                reverse("tenancy:contact", args=[self.contact.pk]),
                {"cfbackrefs_page": 3},
            )
            self.assertEqual(_panel_row_count(response.content.decode()), 1)

    def test_user_without_view_permission_still_sees_referencing_row(self):
        from core.models import ObjectType
        from django.contrib.auth import get_user_model
        from users.models import ObjectPermission

        User = get_user_model()
        plain = User.objects.create_user("plain", password="p")
        # Grant view_contact via NetBox's ObjectPermission so the contact detail
        # view is reachable. Crucially, no view_device permission is granted,
        # so the user cannot view Device objects directly.
        contact_view = ObjectPermission.objects.create(
            name="view_contact", actions=["view"]
        )
        contact_view.users.add(plain)
        contact_view.object_types.add(ObjectType.objects.get_for_model(Contact))

        make_cf(
            name="tech_contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        device = Device.objects.create(
            name="dev-restricted",
            site=self.site,
            device_type=self.device_type,
            role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )

        self.client.force_login(plain)
        response = self.client.get(
            reverse("tenancy:contact", args=[self.contact.pk])
        )
        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        # Even though `plain` has no view_device permission, the row is still rendered.
        self.assertIn(device.get_absolute_url(), body)
        self.assertIn("dev-restricted", body)
