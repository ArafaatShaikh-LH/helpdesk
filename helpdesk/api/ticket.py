import frappe
from frappe import _

from helpdesk.utils import agent_only, is_admin


@frappe.whitelist(methods=["POST"])
@agent_only
def apply_classification_review(
    ticket_id: str,
    main_category: str,
    classification: str = "",
    classification_2: str = "",
    note: str = "",
):
    """Apply an agent classification decision with a record of previous values."""
    from frappe.utils import now_datetime
    from helpdesk.patches.approved_ticket_classification import MAIN

    if main_category not in MAIN or main_category == "Human Review":
        frappe.throw(_("Choose a final Main Category."))
    allowed_classifications = {
        "Contracts": {"Transfer Contract", "Xml", "Chm", "Extranet", "Fit"},
        "Contract Queries": {"Booking Amendment", "Booking Query", "Vcc"},
    }
    allowed_second = {
        "Contracts": {"Amendment", "Loading", "Supplier Query", "Content", "Special Offers Amendment", "Special Offers", "Finance", "Tech"},
        "Contract Queries": {"Accommodation", "Transfers"},
    }
    if classification not in allowed_classifications.get(main_category, {""}):
        frappe.throw(_("Invalid Classification."))
    if classification_2 not in allowed_second.get(main_category, {""}):
        frappe.throw(_("Invalid Classification 2."))
    ticket = frappe.get_doc("HD Ticket", ticket_id)
    frappe.has_permission("HD Ticket", "write", doc=ticket, throw=True)
    if not frappe.db.exists("HD Team", main_category):
        frappe.throw(_("The selected category has no matching Team."))

    audit = frappe.get_doc({
        "doctype": "HD Classification Review",
        "ticket": ticket.name,
        "reviewed_by": frappe.session.user,
        "reviewed_at": now_datetime(),
        "original_main_category": ticket.custom_main_category,
        "original_classification": ticket.custom_classification_category,
        "original_classification_2": ticket.custom_classification_2_category,
        "reviewed_main_category": main_category,
        "reviewed_classification": classification or None,
        "reviewed_classification_2": classification_2 or None,
        "note": note or None,
    })
    ticket.flags.classification_review = True
    ticket.custom_main_category = main_category
    ticket.agent_group = main_category
    ticket.custom_classification_category = classification or None
    ticket.custom_classification_2_category = classification_2 or None
    ticket.save(ignore_permissions=True)
    audit.insert(ignore_permissions=True)
    return {"ticket": ticket.name, "team": ticket.agent_group, "review": audit.name}


@frappe.whitelist()
@agent_only
def bulk_reply(ticket_ids: list, message: str, attachments: list | None = None):

    if not ticket_ids:
        return

    # dedupe but keep the order the agent picked. set() orders by hash, which varies
    # per process, and duplicates would attach the same file to a ticket twice
    ticket_ids = list(dict.fromkeys(ticket_ids))

    # Check every ticket before writing anything, so one ticket the agent cannot
    # reply to does not leave the rest of the batch half done
    tickets = []
    for ticket_id in ticket_ids:
        frappe.has_permission("HD Ticket", "write", doc=ticket_id, throw=True)
        tickets.append(frappe.get_doc("HD Ticket", ticket_id))

    link_attachments_to_tickets(attachments, ticket_ids)

    for doc in tickets:
        try:
            doc.reply_via_agent(
                message, to=doc.raised_by, attachments=attachments or []
            )
        except Exception as e:
            frappe.log_error(
                title=f"Bulk reply failed for ticket {doc.name}",
                message=str(e),
            )


def link_attachments_to_tickets(attachments: list | None, ticket_ids: list):
    if not attachments:
        return
    if not ticket_ids:
        return

    # only one attachment is created, but does not refer to any doctype/docname until now. Link it to all the tickets in context.
    # Done because, FileUploader only handles for one file, and cant upload to multiple doctypes/docnames at the same time.
    for a in attachments:
        file_doc = frappe.get_doc("File", a)
        file_doc.attached_to_doctype = "HD Ticket"
        file_doc.attached_to_name = ticket_ids[0]
        file_doc.save()

    for ticket_id in ticket_ids[1:]:
        for a in attachments:
            file_doc = frappe.get_doc("File", a)
            new_file_doc = frappe.copy_doc(file_doc)
            new_file_doc.attached_to_name = ticket_id
            new_file_doc.save()


def assign_ticket_to_agent(ticket_id, agent_id=None):
    if not ticket_id:
        return

    ticket_doc = frappe.get_doc("HD Ticket", ticket_id)

    if not agent_id:
        # assign to self
        agent_id = frappe.session.user

    if not frappe.db.exists("HD Agent", agent_id):
        frappe.throw(_("Tickets can only be assigned to agents"))

    ticket_doc.assign_agent(agent_id)
    return ticket_doc


@frappe.whitelist()
def delete_ticket(name: str):
    if not is_admin():
        frappe.throw(
            msg=_("Only administrators can delete tickets."),
            title=_("Not Allowed"),
            exc=frappe.PermissionError,
        )
    frappe.delete_doc("HD Ticket", name, force=True, ignore_permissions=True)
