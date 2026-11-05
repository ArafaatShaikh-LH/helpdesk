from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import create_agent


class TestClassificationEdit(FrappeTestCase):
    def setUp(self):
        self.agent = create_agent(f"classification-{frappe.generate_hash(length=8)}@example.invalid")
        self.ticket = frappe.get_doc({
            "doctype": "HD Ticket",
            "name": frappe.generate_hash(length=10),
            "custom_main_category": "Contracts",
            "custom_classification_category": "Fit",
            "custom_classification_2_category": "Loading",
            "custom_historic_classification": "Legacy",
        })
        self.ticket._doc_before_save = frappe.copy_doc(self.ticket)

    def test_agent_can_select_existing_value_and_record_previous_value(self):
        self.ticket.custom_classification_category = "Chm"
        with self.set_user(self.agent.name):
            self.ticket.validate_classification_edit()
            with patch("frappe.get_doc") as get_doc:
                self.ticket.record_classification_change()
        audit = get_doc.call_args.args[0]
        self.assertEqual(audit["original_classification"], "Fit")
        self.assertEqual(audit["reviewed_classification"], "Chm")
        self.assertEqual(audit["reviewed_by"], self.agent.name)
        get_doc.return_value.insert.assert_called_once_with(ignore_permissions=True)

    def test_agent_cannot_invent_value_or_change_history(self):
        with self.set_user(self.agent.name):
            self.ticket.custom_classification_category = "Invented option"
            with self.assertRaises(frappe.ValidationError):
                self.ticket.validate_classification_edit()
            self.ticket.custom_classification_category = "Fit"
            self.ticket.custom_historic_classification = "Changed"
            with self.assertRaises(frappe.PermissionError):
                self.ticket.validate_classification_edit()

    def test_category_change_routes_team_and_clears_incompatible_values(self):
        self.ticket.custom_main_category = "Contract Queries"
        with self.set_user(self.agent.name):
            with patch("frappe.db.exists", return_value=True):
                self.ticket.route_classification_team()
            self.ticket.validate_classification_edit()
        self.assertEqual(self.ticket.agent_group, "Contract Queries")
        self.assertIsNone(self.ticket.custom_classification_category)
        self.assertIsNone(self.ticket.custom_classification_2_category)

    def test_non_agent_cannot_edit_classification(self):
        self.ticket.custom_classification_category = "Chm"
        with self.set_user("Guest"):
            with self.assertRaises(frappe.PermissionError):
                self.ticket.validate_classification_edit()
