import unittest

from helpdesk.helpdesk.utils.reply_recipients import addresses, reply_recipients


class TestReplyRecipients(unittest.TestCase):
    def test_sent_followup_keeps_original_to_and_cc(self):
        result = reply_recipients({
            "sender": '"Contracts" <contracts@example.invalid>',
            "sent_or_received": "Sent",
            "recipients": '"Supplier, One" <one@example.invalid>',
            "cc": "two@example.invalid, buyer@example.invalid, contracts@example.invalid",
            "bcc": "hidden@example.invalid",
        }, ["contracts@example.invalid"], "agent@example.invalid")
        self.assertEqual(result, {"to": ["one@example.invalid"], "cc": ["two@example.invalid", "buyer@example.invalid"], "bcc": []})

    def test_shared_sender_is_recognised_even_if_direction_is_missing(self):
        self.assertEqual(reply_recipients({"sender": '"Team" <CONTRACTS@example.invalid>', "recipients": "supplier@example.invalid"}, ["contracts@example.invalid"])["to"], ["supplier@example.invalid"])

    def test_incoming_reply_and_reply_all(self):
        email = {"sender": '"Supplier" <supplier@example.invalid>', "recipients": "contracts@example.invalid, other@example.invalid", "cc": "OTHER@example.invalid, copied@example.invalid"}
        self.assertEqual(reply_recipients(email, ["contracts@example.invalid"], reply_all=False), {"to": ["supplier@example.invalid"], "cc": [], "bcc": []})
        self.assertEqual(reply_recipients(email, ["contracts@example.invalid"]), {"to": ["supplier@example.invalid"], "cc": ["other@example.invalid", "copied@example.invalid"], "bcc": []})

    def test_promote_copied_participants_when_to_contains_only_mailbox(self):
        self.assertEqual(reply_recipients({"sent_or_received": "Sent", "recipients": "contracts@example.invalid", "cc": "supplier@example.invalid"}, ["contracts@example.invalid"]), {"to": ["supplier@example.invalid"], "cc": [], "bcc": []})

    def test_self_only_message_does_not_fall_back_to_a_mailbox(self):
        self.assertEqual(reply_recipients({"sender": "contracts@example.invalid", "recipients": "contracts@example.invalid"}, ["contracts@example.invalid"]), {"to": [], "cc": [], "bcc": []})

    def test_quoted_names_and_case_insensitive_duplicates(self):
        self.assertEqual(addresses('"One, Supplier" <one@example.invalid>, ONE@example.invalid, two@example.invalid'), ["one@example.invalid", "two@example.invalid"])

    def test_internal_people_are_not_removed_by_domain(self):
        self.assertEqual(reply_recipients({"sender": "buyer@example.invalid", "recipients": "contracts@example.invalid"}, ["contracts@example.invalid"])["to"], ["buyer@example.invalid"])
