from core.models import ObjectType
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from django.contrib.auth import get_user_model
from django.urls import reverse
from tenancy.models import Contact
from users.models import ObjectPermission
from utilities.testing import TestCase

from ._factories import make_cf


class CFBackrefsTabRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff_user = User.objects.create_user("staff_u", password="p")
        cls.staff_user.is_superuser = True
        cls.staff_user.save()

        cls.unprivileged_user = User.objects.create_user("plain_u", password="p")

        cls.site = Site.objects.create(name="S1", slug="s1")
        manufacturer = Manufacturer.objects.create(name="M1", slug="m1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer, model="DT1", slug="dt1"
        )
        cls.role = DeviceRole.objects.create(name="R1", slug="r1")
        cls.contact = Contact.objects.create(name="cfbtab-bob")

        make_cf(
            name="tech_contact",
            label="Technical contact",
            cf_type="object",
            target_model=Contact,
            source_models=[Device],
        )
        cls.device = Device.objects.create(
            name="cfbtab-dev-1",
            site=cls.site,
            device_type=cls.device_type,
            role=cls.role,
            custom_field_data={"tech_contact": cls.contact.pk},
        )
        cls.tab_url = reverse("tenancy:contact_cf_backrefs", args=[cls.contact.pk])

    def _grant_view_contact(self, user):
        perm = ObjectPermission.objects.create(name="view-contact", actions=["view"])
        perm.users.add(user)
        perm.object_types.add(ObjectType.objects.get_for_model(Contact))

    def test_user_with_view_contact_permission_gets_200(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("CF Backrefs", body)
        self.assertIn(self.device.get_absolute_url(), body)
        self.assertIn("Technical contact", body)

    def test_user_without_view_contact_permission_gets_forbidden(self):
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        self.assertEqual(response.status_code, 403)

    def test_filter_button_url_contains_cf_filter(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.tab_url)
        body = response.content.decode()
        expected = f"/dcim/devices/?cf_tech_contact={self.contact.pk}"
        self.assertIn(expected, body)
        self.assertIn("mdi-filter", body)

    def test_anonymous_user_redirected_or_forbidden(self):
        response = self.client.get(self.tab_url)
        self.assertIn(response.status_code, (302, 403))

    def test_htmx_partial_returns_rows_only(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        # Partial does NOT include the parent layout chrome.
        self.assertNotIn('<html', body)
        # Partial DOES include the rows + paginator wrapper.
        self.assertIn('id="cf-backrefs-table"', body)
        self.assertIn(self.device.get_absolute_url(), body)

    def test_full_response_wraps_table_in_swap_target(self):
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url)
        body = response.content.decode()
        self.assertIn('id="cf-backrefs-table"', body)

    def test_quick_search_narrows_results(self):
        Device.objects.create(
            name="cfbtab-other",
            site=self.site, device_type=self.device_type, role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        response = self.client.get(self.tab_url, {"q": "cfbtab-other"})
        body = response.content.decode()
        self.assertIn("cfbtab-other", body)
        self.assertNotIn("cfbtab-dev-1", body)

    def test_header_count_matches_tab_badge(self):
        # Two Devices both reference the contact via tech_contact. Header
        # `(N)` must equal the unfiltered count, regardless of any active
        # quick-search narrowing — same number the tab badge shows.
        Device.objects.create(
            name="cfbtab-second",
            site=self.site, device_type=self.device_type, role=self.role,
            custom_field_data={"tech_contact": self.contact.pk},
        )
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)

        unfiltered = self.client.get(self.tab_url).content.decode()
        self.assertIn("CF Backrefs (2)", unfiltered)

        # With a narrowing search the header count stays at the unfiltered
        # value and a "Matching X of Y" subtitle reports the narrowing.
        narrowed = self.client.get(self.tab_url, {"q": "cfbtab-second"}).content.decode()
        self.assertIn("CF Backrefs (2)", narrowed)
        self.assertIn("Matching 1 of 2", narrowed)

    def test_configure_table_button_and_filter_sidebar_absent(self):
        # Phase 4 stripped both. Lock that in.
        self._grant_view_contact(self.unprivileged_user)
        self.client.force_login(self.unprivileged_user)
        body = self.client.get(self.tab_url).content.decode()
        self.assertNotIn("Configure Table", body)
        self.assertNotIn("CFBackrefTabTable_config", body)
        # Sidebar dropdowns gone.
        self.assertNotIn('name="source_type"', body)
        self.assertNotIn('name="cf_name"', body)
        self.assertNotIn('name="cf_type"', body)
