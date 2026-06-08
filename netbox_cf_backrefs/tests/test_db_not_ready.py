"""Import-time DB-discovery must degrade gracefully when the database is not ready.

Both display surfaces enumerate ``ContentType.objects.all()`` at import time:
``template_content`` builds its panel extensions and ``views`` registers per-model
tabs. During a fresh install or image build (e.g. the netbox-docker
``collectstatic``/``migrate`` steps) Django loads every app — and therefore runs
this discovery — before the database is reachable (``OperationalError``) or before
migrations have created the tables (``ProgrammingError``). Discovery must log and
register nothing rather than raise, which would crash NetBox startup / the build.
"""
from unittest import mock

from django.db import OperationalError, ProgrammingError
from django.test import SimpleTestCase

from netbox_cf_backrefs import template_content, views


class DatabaseNotReadyTests(SimpleTestCase):
    def test_panel_discovery_returns_empty_when_db_unreachable(self):
        with mock.patch.object(template_content, "ContentType") as ct:
            ct.objects.all.side_effect = OperationalError("could not connect to server")
            with self.assertLogs("netbox_cf_backrefs", level="WARNING"):
                labels = template_content._discover_target_model_labels()
        self.assertEqual(labels, [])

    def test_panel_discovery_returns_empty_when_tables_missing(self):
        with mock.patch.object(template_content, "ContentType") as ct:
            ct.objects.all.side_effect = ProgrammingError(
                'relation "django_content_type" does not exist'
            )
            with self.assertLogs("netbox_cf_backrefs", level="WARNING"):
                labels = template_content._discover_target_model_labels()
        self.assertEqual(labels, [])

    def test_tab_registration_skips_when_db_unreachable(self):
        with mock.patch.object(views, "ContentType") as ct:
            ct.objects.all.side_effect = OperationalError("could not connect to server")
            with self.assertLogs("netbox_cf_backrefs", level="WARNING"):
                views._register_tabs()  # must not raise

    def test_tab_registration_skips_when_tables_missing(self):
        with mock.patch.object(views, "ContentType") as ct:
            ct.objects.all.side_effect = ProgrammingError(
                'relation "django_content_type" does not exist'
            )
            with self.assertLogs("netbox_cf_backrefs", level="WARNING"):
                views._register_tabs()  # must not raise
