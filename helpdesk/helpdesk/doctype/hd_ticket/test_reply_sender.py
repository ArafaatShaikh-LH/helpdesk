from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from helpdesk.test_utils import (
    create_agent,
    make_email_account,
    make_ticket,
    make_ticket_mail,
    unique_email,
)


class TestReplySender(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.enterContext(
            patch("frappe.email.doctype.email_account.email_account.EmailServer")
        )
        self.enterContext(
            change_settings("HD Settings", {"reply_from_receiving_mailbox": 1})
        )
        self.agent = create_agent(unique_email("reply-agent")).name
        self.account = make_email_account("Sendgrid", enable_incoming=0)
        self.other = make_email_account("Sendgrid", enable_incoming=0)
        self.address = frappe.db.get_value("Email Account", self.account, "email_id")
        self.ticket = make_ticket()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_incoming_account_wins_over_later_outgoing_reply(self):
        make_ticket_mail(self.ticket, self.account)
        make_ticket_mail(self.ticket, self.other, direction="Sent")
        with self.set_user(self.agent):
            sender, name = self.ticket._resolve_sender_email(
                self.other, "wrong@example.invalid"
            )
        self.assertEqual((sender.email_id, name), (self.address, self.account))

    def test_latest_incoming_account_wins(self):
        make_ticket_mail(self.ticket, self.other)
        make_ticket_mail(self.ticket, self.account)
        with self.set_user(self.agent):
            policy = self.ticket.get_reply_sender()
        self.assertTrue(policy["enabled"])
        self.assertEqual(policy["sender"]["email_account"], self.account)

    def test_no_incoming_requires_explicit_sender(self):
        with self.set_user(self.agent):
            self.assertIsNone(self.ticket.get_reply_sender()["sender"])
            with self.assertRaises(frappe.ValidationError):
                self.ticket._resolve_sender_email(None, None)
            sender, name = self.ticket._resolve_sender_email(self.account, self.address)
        self.assertEqual((sender.email_id, name), (self.address, self.account))

    def test_disabled_receiving_account_does_not_fall_back(self):
        make_ticket_mail(self.ticket, self.account)
        frappe.db.set_value("Email Account", self.account, "enable_outgoing", 0)
        with self.set_user(self.agent), self.assertRaises(frappe.ValidationError):
            self.ticket._resolve_sender_email(self.other, "other@example.invalid")

    def test_explicit_address_must_match_enabled_account(self):
        with self.set_user(self.agent):
            with self.assertRaises(frappe.ValidationError):
                self.ticket._resolve_sender_email(self.account, "wrong@example.invalid")
            frappe.db.set_value("Email Account", self.account, "enable_outgoing", 0)
            with self.assertRaises(frappe.ValidationError):
                self.ticket._resolve_sender_email(self.account, self.address)

    def test_no_reply_is_not_a_manual_agent_sender(self):
        with self.set_user(self.agent):
            with patch(
                "frappe.db.get_value",
                return_value=frappe._dict(
                    name="No Reply", email_id="donotreply@example.invalid"
                ),
            ):
                with self.assertRaises(frappe.ValidationError):
                    self.ticket._resolve_sender_email(
                        "No Reply", "donotreply@example.invalid"
                    )

    def test_guest_cannot_read_sender_policy(self):
        with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
            self.ticket.get_reply_sender()

    def test_ticket_permission_is_required(self):
        with (
            self.set_user(self.agent),
            patch.object(
                self.ticket, "check_permission", side_effect=frappe.PermissionError
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                self.ticket.get_reply_sender()

    def test_feature_disabled_preserves_legacy_resolution(self):
        with change_settings("HD Settings", {"reply_from_receiving_mailbox": 0}):
            with self.set_user(self.agent):
                self.assertFalse(self.ticket.get_reply_sender()["enabled"])
                with patch.object(
                    self.ticket,
                    "_resolve_legacy_sender_email",
                    return_value=(None, None),
                ) as legacy:
                    self.ticket._resolve_sender_email(None, None)
                    legacy.assert_called_once_with(None, None)
