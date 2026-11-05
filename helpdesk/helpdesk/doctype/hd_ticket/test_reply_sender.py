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
            policy = self.ticket.get_reply_sender()
            self.assertIsNone(policy["sender"])
            self.assertIn(
                {"email_account": self.account, "email_id": self.address},
                policy["available_senders"],
            )
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

    def test_no_reply_is_not_a_sender_option(self):
        with (
            self.set_user(self.agent),
            patch("frappe.get_all", return_value=[]) as get_all,
            patch.object(self.ticket, "get_reply_recipients", return_value={"to": [], "cc": [], "bcc": []}),
        ):
            self.ticket.get_reply_sender()
        self.assertEqual(
            get_all.call_args.kwargs["filters"],
            {"enable_outgoing": 1, "name": ["!=", "No Reply"]},
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

    def test_selected_reply_cannot_read_another_tickets_email(self):
        other_ticket = make_ticket()
        mail = make_ticket_mail(other_ticket, self.account)
        with self.set_user(self.agent), self.assertRaises(frappe.PermissionError):
            self.ticket.get_reply_recipients(communication=mail.name)

    def test_reply_recipients_require_ticket_access(self):
        with (
            self.set_user(self.agent),
            patch.object(self.ticket, "check_permission", side_effect=frappe.PermissionError),
            self.assertRaises(frappe.PermissionError),
        ):
            self.ticket.get_reply_recipients()

    def test_guest_cannot_read_reply_recipients(self):
        with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
            self.ticket.get_reply_recipients()

    def test_reply_to_sending_mailbox_is_rejected_before_communication_insert(self):
        with self.set_user(self.agent), patch.object(self.ticket, "_resolve_sender_email") as resolve:
            resolve.return_value = (frappe._dict(email_id=self.address), self.account)
            for field in ("to", "cc", "bcc"):
                with self.subTest(field=field), self.assertRaises(frappe.ValidationError):
                    self.ticket.reply_via_agent(
                        message="Synthetic self-reply check", **{field: f'"Shared mailbox" <{self.address.upper()}>'}
                    )

    def test_sent_followup_preserves_message_recipients_not_original_requester(self):
        mail = make_ticket_mail(self.ticket, self.account, direction="Sent")
        recipient = unique_email("followup-supplier")
        copied = unique_email("followup-copied")
        mail.db_set("sender", self.address)
        mail.db_set("recipients", recipient)
        mail.db_set("cc", copied)
        with self.set_user(self.agent):
            selected = self.ticket.get_reply_recipients(communication=mail.name)
            defaults = self.ticket.get_reply_recipients()
        expected = {"to": [recipient], "cc": [copied], "bcc": []}
        self.assertEqual(selected, expected)
        self.assertEqual(defaults, expected)
