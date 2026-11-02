from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from helpdesk.test_utils import (
    create_agent,
    make_communication_attachment,
    make_email_account,
    make_ticket,
    make_ticket_mail,
    unique_email,
)


class TestForwardEmail(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.enterContext(
            patch("frappe.email.doctype.email_account.email_account.EmailServer")
        )
        self.enterContext(
            change_settings(
                "HD Settings",
                {
                    "reply_from_receiving_mailbox": 1,
                    "enable_reply_email_via_agent": 1,
                },
            )
        )
        self.enterContext(patch.dict(frappe.conf, {"mute_emails": 0}))
        self.sendmail = self.enterContext(
            patch("frappe.sendmail", return_value=frappe._dict(name="mock-queue"))
        )
        self.agent = create_agent(unique_email("forward-agent")).name
        self.account = make_email_account("Sendgrid", enable_incoming=0)
        self.address = frappe.db.get_value("Email Account", self.account, "email_id")
        self.ticket = make_ticket()
        self.source = make_ticket_mail(self.ticket, self.account)
        self.source.reload()
        self.file = make_communication_attachment(self.source)
        self.args = {
            "communication": self.source.name,
            "source_modified": str(self.source.modified),
            "request_id": frappe.generate_hash(length=32),
            "to": "forward-recipient@example.invalid",
            "from_email": {"email_account": self.account, "email_id": self.address},
            "note": "Please check this selected email.",
        }

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_forwards_selected_email_only_and_preserves_ticket_state(self):
        before = frappe.db.get_value(
            "HD Ticket",
            self.ticket.name,
            ["status", "first_responded_on", "last_agent_response"],
            as_dict=True,
        )
        with self.set_user(self.agent):
            name = self.ticket.forward_email(**self.args)
        forward = frappe.get_doc("Communication", name)
        queued = self.sendmail.call_args.kwargs
        self.assertEqual(forward.custom_hd_forward_source, self.source.name)
        self.assertEqual(forward.reference_name, str(self.ticket.name))
        self.assertEqual(queued["recipients"], ["forward-recipient@example.invalid"])
        self.assertEqual(queued["cc"], [])
        self.assertEqual(queued["bcc"], [])
        self.assertNotIn(self.source.recipients, queued["recipients"])
        self.assertEqual(queued["sender"], self.address)
        self.assertEqual(queued["reply_to"], self.address)
        self.assertEqual(queued["message_id"], forward.message_id)
        self.assertNotIn("in_reply_to", queued)
        self.assertIn(self.source.content, forward.content)
        self.assertEqual(queued["attachments"], [{"file_url": self.file.file_url}])
        linked = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Communication", "attached_to_name": name},
            fields=["file_url", "is_private"],
        )
        self.assertEqual(linked, [{"file_url": self.file.file_url, "is_private": 1}])
        after = frappe.db.get_value(
            "HD Ticket",
            self.ticket.name,
            ["status", "first_responded_on", "last_agent_response"],
            as_dict=True,
        )
        self.assertEqual(after, before)
        self.assertEqual(
            frappe.db.get_value("File", self.file.name, "attached_to_name"),
            self.source.name,
        )

    def test_retry_does_not_queue_twice(self):
        with self.set_user(self.agent):
            first = self.ticket.forward_email(**self.args)
            second = self.ticket.forward_email(**self.args)
        self.assertEqual(first, second)
        self.assertEqual(self.sendmail.call_count, 1)

    def test_agent_can_exclude_selected_attachment_and_add_explicit_copies(self):
        with self.set_user(self.agent):
            self.ticket.forward_email(
                **self.args,
                attachments=[],
                cc="copy@example.invalid",
                bcc="blind@example.invalid",
            )
        self.assertEqual(self.sendmail.call_args.kwargs["attachments"], [])
        self.assertEqual(self.sendmail.call_args.kwargs["cc"], ["copy@example.invalid"])
        self.assertEqual(
            self.sendmail.call_args.kwargs["bcc"], ["blind@example.invalid"]
        )

    def test_guest_cannot_read_or_send(self):
        with self.set_user("Guest"):
            with self.assertRaises(frappe.PermissionError):
                self.ticket.get_forward_email(self.source.name)
            with self.assertRaises(frappe.PermissionError):
                self.ticket.forward_email(**self.args)
        self.sendmail.assert_not_called()

    def test_ticket_write_permission_is_required(self):
        with (
            self.set_user(self.agent),
            patch.object(
                self.ticket, "check_permission", side_effect=frappe.PermissionError
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                self.ticket.forward_email(**self.args)
        self.sendmail.assert_not_called()

    def test_other_ticket_source_and_attachments_are_refused(self):
        other = make_ticket_mail(make_ticket(), self.account)
        other_file = make_communication_attachment(other)
        with self.set_user(self.agent):
            with self.assertRaises(frappe.PermissionError):
                self.ticket.get_forward_email(other.name)
            with self.assertRaises(frappe.PermissionError):
                self.ticket.forward_email(**{**self.args, "communication": other.name})
            with self.assertRaises(frappe.PermissionError):
                self.ticket.forward_email(**self.args, attachments=[other_file.name])
        self.sendmail.assert_not_called()

    def test_comments_cannot_be_forwarded(self):
        frappe.db.set_value(
            "Communication", self.source.name, "communication_medium", "Other"
        )
        with self.set_user(self.agent), self.assertRaises(frappe.PermissionError):
            self.ticket.forward_email(**self.args)
        self.sendmail.assert_not_called()

    def test_recipients_must_be_explicit_and_valid(self):
        with self.set_user(self.agent):
            for to in ["", "invalid", "a@example.invalid\nBcc: hidden@example.invalid"]:
                with self.assertRaises(frappe.ValidationError):
                    self.ticket.forward_email(**{**self.args, "to": to})
        self.sendmail.assert_not_called()

    def test_changed_source_is_not_sent(self):
        with self.set_user(self.agent), self.assertRaises(frappe.ValidationError):
            self.ticket.forward_email(**{**self.args, "source_modified": "old"})
        self.sendmail.assert_not_called()

    def test_disabled_or_wrong_sender_is_not_sent(self):
        with self.set_user(self.agent), self.assertRaises(frappe.ValidationError):
            self.ticket.forward_email(
                **{
                    **self.args,
                    "from_email": {
                        "email_account": self.account,
                        "email_id": "wrong@example.invalid",
                    },
                }
            )
        frappe.db.set_value("Email Account", self.account, "enable_outgoing", 0)
        with self.set_user(self.agent), self.assertRaises(frappe.ValidationError):
            self.ticket.forward_email(**self.args)
        self.sendmail.assert_not_called()

    def test_email_mute_and_disabled_outbound_are_respected(self):
        with self.set_user(self.agent):
            with (
                patch.dict(frappe.conf, {"mute_emails": 1}),
                self.assertRaises(frappe.ValidationError),
            ):
                self.ticket.forward_email(**self.args)
            with (
                change_settings("HD Settings", {"enable_reply_email_via_agent": 0}),
                self.assertRaises(frappe.ValidationError),
            ):
                self.ticket.forward_email(**self.args)
        self.sendmail.assert_not_called()

    def test_body_does_not_embed_another_messages_private_files(self):
        self.source.db_set(
            "content",
            '<p>Selected body</p><img src="/private/files/other-secret.png"><span embed="/private/files/hidden.txt">Text</span>',
        )
        self.source.reload()
        with self.set_user(self.agent):
            self.ticket.forward_email(
                **{
                    **self.args,
                    "source_modified": str(self.source.modified),
                    "note": "<script>unsafe</script>",
                }
            )
        message = self.sendmail.call_args.kwargs["message"]
        self.assertNotIn("other-secret.png", message)
        self.assertNotIn('embed="/private/files/hidden.txt"', message)
        self.assertNotIn("<script>", message)
        self.assertIn("&lt;script&gt;", message)

    def test_raw_embed_text_cannot_read_unrelated_private_file(self):
        self.source.db_set(
            "content", '<p>Text embed="/private/files/unrelated-secret.txt"</p>'
        )
        self.source.reload()
        with self.set_user(self.agent), self.assertRaises(frappe.PermissionError):
            self.ticket.forward_email(
                **{**self.args, "source_modified": str(self.source.modified)}
            )
        self.sendmail.assert_not_called()

    def test_missing_queue_is_reported_as_failure(self):
        self.sendmail.return_value = None
        with self.set_user(self.agent), self.assertRaises(frappe.ValidationError):
            self.ticket.forward_email(**self.args)
