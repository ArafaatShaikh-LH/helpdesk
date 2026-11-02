"""Selected-email forwarding. Public entry points live on HD Ticket."""

import hashlib
import json
import re
from email.utils import getaddresses
from html import escape

import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.email.email_body import EMBED_PATTERN, get_message_id
from frappe.utils import cint, get_string_between, strip_html, validate_email_address
from frappe.utils.html_utils import sanitize_html

from helpdesk.utils import is_agent


def _source(ticket, communication, permission):
    if not is_agent():
        frappe.throw(
            _("Only Helpdesk agents can forward email."), frappe.PermissionError
        )
    ticket.check_permission(permission)
    source = frappe.get_doc("Communication", communication)
    if (
        source.reference_doctype != "HD Ticket"
        or str(source.reference_name) != str(ticket.name)
        or source.communication_medium != "Email"
        or source.communication_type != "Communication"
    ):
        frappe.throw(_("Select an email on this ticket."), frappe.PermissionError)
    # Ticket access was checked above. Only files linked to this exact message
    # are eligible; ticket-level files and other messages' files are excluded.
    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Communication",
            "attached_to_name": source.name,
        },
        fields=["name", "file_name", "file_url", "is_private"],
        order_by="creation asc, name asc",
    )
    return source, files


def prepare_forward(ticket, communication):
    source, files = _source(ticket, communication, "read")
    return {
        "communication": source.name,
        "source_modified": str(source.modified),
        "subject": _subject(source.subject),
        "sender": source.sender,
        "preview_text": strip_html(source.content or ""),
        "attachments": files,
    }


def _subject(subject):
    subject = re.sub(r"[\r\n]+", " ", subject or "").strip()
    return subject if subject.lower().startswith("fwd:") else f"Fwd: {subject}"


def _recipients(value, required=False):
    if not isinstance(value, str) or any(c in value for c in "\r\n\x00"):
        frappe.throw(_("Enter valid email addresses separated by commas."))
    if required and not value.strip():
        frappe.throw(_("Enter at least one To recipient."))
    if not value.strip():
        return []
    addresses = []
    # Accept bare addresses and display names; never silently drop a bad token.
    for name, address in getaddresses([value]):
        if not address or not validate_email_address(address, throw=False):
            frappe.throw(_("Enter valid email addresses separated by commas."))
        if address.lower() not in {a.lower() for a in addresses}:
            addresses.append(address)
    if required and not addresses:
        frappe.throw(_("Enter at least one To recipient."))
    return addresses


def _sender(ticket, submitted):
    if not isinstance(submitted, dict):
        frappe.throw(_("Choose a sending mailbox."))
    # Use the reply policy, including its locked receiving mailbox. Even when
    # that policy is disabled, do not trust the legacy caller-provided address.
    resolved, account_name = ticket._resolve_sender_email(
        submitted.get("email_account"), submitted.get("email_id")
    )
    account = (
        frappe.db.get_value(
            "Email Account",
            account_name,
            ["name", "email_id", "enable_outgoing"],
            as_dict=True,
        )
        if account_name
        else None
    )
    if (
        not resolved
        or not account
        or not account.enable_outgoing
        or account.name == "No Reply"
        or submitted.get("email_account") != account.name
        or submitted.get("email_id", "").lower() != account.email_id.lower()
    ):
        frappe.throw(
            _(
                "The sending mailbox changed or is unavailable. Reopen Forward and try again."
            )
        )
    return account


def _message(source, note, files):
    body = source.content or ""
    if not re.search(r"<[a-z][\s\S]*>", body, re.I):
        body = escape(body).replace("\n", "<br>")
    soup = BeautifulSoup(sanitize_html(body, always_sanitize=True), "html.parser")
    allowed = {f.file_url for f in files}
    # Frappe embeds local files in outgoing mail. Never let an HTML reference
    # embed a private file that was not attached to the selected email.
    for tag in soup.find_all(True):
        tag.attrs.pop("embed", None)
    for tag in soup.find_all(["img", "video", "audio", "source"]):
        src = tag.get("src", "")
        if src.startswith(("/", "file:", "cid:")) and src not in allowed:
            tag.decompose()
    return (
        f"<p>{escape(note).replace(chr(10), '<br>')}</p>"
        "<hr><p>---------- Forwarded message ----------<br>"
        f"From: {escape(source.sender or '')}<br>"
        f"Date: {escape(str(source.communication_date or source.creation))}<br>"
        f"Subject: {escape(source.subject or '')}</p>"
        f"<blockquote>{soup}</blockquote>"
    )


def send_forward(
    ticket,
    communication,
    source_modified,
    request_id,
    to,
    from_email,
    note="",
    cc="",
    bcc="",
    attachments=None,
):
    source, files = _source(ticket, communication, "write")
    recipients, copies, blind_copies = (
        _recipients(to, True),
        _recipients(cc),
        _recipients(bcc),
    )
    if len(recipients + copies + blind_copies) > 50:
        frappe.throw(_("Forward to no more than 50 recipients at a time."))
    if not isinstance(note, str) or len(note) > 50000:
        frappe.throw(_("The forward note must be under 50,000 characters."))
    if not isinstance(request_id, str) or not re.fullmatch(
        r"[a-zA-Z0-9-]{16,80}", request_id
    ):
        frappe.throw(_("Reopen Forward and try again."))
    if attachments is None:
        attachments = [f.name for f in files]
    if not isinstance(attachments, list) or any(
        not isinstance(name, str) for name in attachments
    ):
        frappe.throw(_("Select attachments from this email."))
    eligible = {f.name for f in files}
    if set(attachments) - eligible:
        frappe.throw(
            _("An attachment does not belong to this email."), frappe.PermissionError
        )
    selected = [f for f in files if f.name in attachments]
    account = _sender(ticket, from_email)
    # A retry after a lost response must not queue the same forward twice.
    payload = [
        str(ticket.name),
        source.name,
        frappe.session.user,
        request_id,
        recipients,
        copies,
        blind_copies,
        account.name,
        note,
        sorted(attachments),
    ]
    name = hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:32]
    if frappe.db.exists("Communication", name):
        existing = frappe.get_doc("Communication", name)
        if (
            existing.get("custom_hd_forward_source") == source.name
            and existing.message_id
        ):
            return existing.name
        frappe.throw(_("This forward has not been queued. Contact your administrator."))
    if str(source.modified) != source_modified:
        frappe.throw(
            _("This email changed. Reopen Forward to review its latest content.")
        )
    if (
        cint(frappe.conf.get("mute_emails"))
        or ticket.skip_email_workflow()
        or not cint(
            frappe.db.get_single_value("HD Settings", "enable_reply_email_via_agent")
        )
    ):
        frappe.throw(
            _("Outgoing ticket email is disabled. Contact your administrator.")
        )
    if not frappe.get_meta("Communication").has_field("custom_hd_forward_source"):
        frappe.throw(_("Complete the Helpdesk update before forwarding email."))

    content = _message(source, note, selected)
    delivery_content = ticket.parse_content(content)
    if any(
        url not in {f.file_url for f in selected}
        for url in EMBED_PATTERN.findall(delivery_content)
    ):
        frappe.throw(
            _(
                "This email contains an unrelated embedded file. Contact your administrator."
            ),
            frappe.PermissionError,
        )
    message_id = get_string_between("<", get_message_id(), ">")
    forward = frappe.get_doc(
        {
            "doctype": "Communication",
            "communication_medium": "Email",
            "communication_type": "Communication",
            "sent_or_received": "Sent",
            "status": "Linked",
            "email_status": "Open",
            "reference_doctype": "HD Ticket",
            "reference_name": ticket.name,
            "custom_hd_forward_source": source.name,
            "sender": account.email_id,
            "email_account": account.name,
            "recipients": ", ".join(recipients),
            "cc": ", ".join(copies),
            "bcc": ", ".join(blind_copies),
            "subject": _subject(source.subject),
            "content": content,
        }
    ).insert(ignore_permissions=True, set_name=name)
    for file in selected:
        frappe.get_doc(
            {
                "doctype": "File",
                "file_url": file.file_url,
                "file_name": file.file_name,
                "is_private": file.is_private,
                "attached_to_doctype": "Communication",
                "attached_to_name": forward.name,
            }
        ).insert(ignore_permissions=True)
    queued = frappe.sendmail(
        recipients=recipients,
        cc=copies,
        bcc=blind_copies,
        sender=account.email_id,
        reply_to=account.email_id,
        subject=forward.subject,
        message=delivery_content,
        attachments=[{"file_url": f.file_url} for f in selected],
        communication=forward.name,
        reference_doctype="HD Ticket",
        reference_name=ticket.name,
        message_id=message_id,
        expose_recipients="header",
        delayed=True,
        now=False,
        with_container=False,
    )
    if not queued:
        # Throw so the request rolls back the new message and its attachment links.
        frappe.throw(_("The forward could not be queued. No email has been sent."))
    forward.db_set("message_id", message_id)
    return forward.name
