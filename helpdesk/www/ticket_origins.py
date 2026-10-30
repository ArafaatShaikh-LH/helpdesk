"""Read-only receiving-mailbox history for a Helpdesk ticket."""

import frappe

from helpdesk.utils import is_agent

no_cache = 1


def get_context(context):
    ticket = frappe.form_dict.get("ticket")
    if frappe.session.user == "Guest" or not is_agent():
        frappe.throw("Sign in as a Helpdesk agent", frappe.PermissionError)
    if not isinstance(ticket, str) or not ticket or len(ticket) > 140:
        frappe.throw("Invalid ticket", frappe.PermissionError)

    frappe.get_doc("HD Ticket", ticket).check_permission("read")
    source_tickets = [ticket]
    frontier = [ticket]
    while frontier:
        rows = frappe.get_list(
            "HD Ticket",
            filters={"merged_with": ["in", frontier], "is_merged": 1},
            fields=["name"],
            limit_page_length=101,
        )
        new_sources = [row.name for row in rows if row.name not in source_tickets]
        if len(rows) > 100 or len(source_tickets) + len(new_sources) > 100:
            frappe.throw("Too many merged source tickets for this overview")
        for name in new_sources:
            frappe.get_doc("HD Ticket", name).check_permission("read")
        source_tickets.extend(new_sources)
        frontier = new_sources

    messages = frappe.get_list(
        "Communication",
        filters={
            "reference_doctype": "HD Ticket",
            "reference_name": ["in", source_tickets],
            "communication_medium": "Email",
            "sent_or_received": "Received",
        },
        fields=[
            "name",
            "email_account",
            "email_date",
            "creation",
            "reference_name",
            "message_id",
        ],
        order_by="creation asc, name asc",
        limit_page_length=5001,
    )
    if len(messages) > 5000:
        frappe.throw("Too many messages for this overview")

    context.update(
        ticket=ticket,
        source_tickets=source_tickets,
        messages=messages,
        mailboxes=sorted(
            {
                str(message.get("email_account") or "Unknown — needs reconciliation")
                for message in messages
            }
        ),
    )
    context.no_cache = 1
    frappe.local.response_headers.update(
        {
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        }
    )
