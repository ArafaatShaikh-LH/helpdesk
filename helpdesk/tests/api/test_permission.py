import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.permission import has_app_permission
from helpdesk.test_utils import create_agent


class TestPermission(FrappeTestCase):
    website_user = "helpdesk-website-user@example.com"
    manager_user = "helpdesk-manager@example.com"
    original_user = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_user = frappe.session.user

    def tearDown(self):
        frappe.set_user(self.original_user or "Administrator")

    def test_agent_can_access_helpdesk_app(self):
        create_agent("helpdesk-agent@example.com")

        frappe.set_user("helpdesk-agent@example.com")

        self.assertTrue(has_app_permission())

    def test_agent_manager_can_access_helpdesk_app(self):
        user = self._get_or_create_user(self.manager_user)
        user.add_roles("Agent Manager")

        frappe.set_user(self.manager_user)

        self.assertTrue(has_app_permission())

    def test_regular_website_user_cannot_access_helpdesk_app(self):
        self._get_or_create_user(self.website_user)

        frappe.set_user(self.website_user)

        self.assertFalse(has_app_permission())

    def _get_or_create_user(self, email):
        if frappe.db.exists("User", email):
            return frappe.get_doc("User", email)

        return frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)


class TestManagerOverviewLink(FrappeTestCase):
    """Optional Insights integration must fail closed without broadening access."""

    def test_no_insights_role_does_not_read_optional_settings(self):
        from unittest.mock import patch
        from helpdesk.api.auth import get_manager_overview_url

        with patch("frappe.db.get_single_value") as setting:
            self.assertIsNone(get_manager_overview_url("agent@example.com", ["Agent"]))
            setting.assert_not_called()

    def test_insights_not_installed_hides_link(self):
        from unittest.mock import patch
        from helpdesk.api.auth import get_manager_overview_url

        with patch("frappe.get_installed_apps", return_value=["helpdesk"]):
            self.assertIsNone(get_manager_overview_url("agent@example.com", ["Insights User"]))

    def test_unshared_dashboard_hides_link(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from helpdesk.api.auth import get_manager_overview_url

        with (
            patch("frappe.get_installed_apps", return_value=["helpdesk", "insights"]),
            patch("frappe.get_meta", return_value=SimpleNamespace(has_field=lambda field: True)),
            patch("frappe.db.get_single_value", return_value="manager-dashboard"),
            patch("frappe.db.exists", return_value=True),
            patch("frappe.has_permission", return_value=False) as permission,
        ):
            self.assertIsNone(get_manager_overview_url("agent@example.com", ["Insights User"]))
            permission.assert_called_once_with(
                "Insights Dashboard v3", ptype="read", doc="manager-dashboard", user="agent@example.com"
            )

    def test_shared_dashboard_uses_same_origin_and_escaped_id(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from helpdesk.api.auth import get_manager_overview_url

        with (
            patch("frappe.get_installed_apps", return_value=["helpdesk", "insights"]),
            patch("frappe.get_meta", return_value=SimpleNamespace(has_field=lambda field: True)),
            patch("frappe.db.get_single_value", return_value="dashboard/id?next=elsewhere"),
            patch("frappe.db.exists", return_value=True),
            patch("frappe.has_permission", return_value=True),
        ):
            self.assertEqual(
                get_manager_overview_url("agent@example.com", ["Insights User"]),
                "/insights/dashboards/dashboard%2Fid%3Fnext%3Delsewhere",
            )
