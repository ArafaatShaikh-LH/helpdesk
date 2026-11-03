"""Archive retired classification values before narrowing the ticket choices."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property


MAIN = (
    "Contracts", "Contract Queries", "Human Review", "Allocation",
    "Special Offers", "Stop Sales",
)
CLASSIFICATION = (
    "Transfer Contract", "Xml", "Chm", "Extranet", "Fit",
    "Booking Amendment", "Booking Query", "Vcc",
)
CLASSIFICATION_2 = (
    "Amendment", "Loading", "Supplier Query", "Content",
    "Special Offers Amendment", "Special Offers", "Finance", "Tech",
    "Accommodation", "Transfers",
)


def legacy_changes(row):
    changes = {}
    if (
        row.custom_classification_category
        and row.custom_classification_category not in CLASSIFICATION
    ):
        changes["custom_historic_classification"] = row.custom_classification_category
        changes["custom_classification_category"] = None
    if (
        row.custom_classification_2_category
        and row.custom_classification_2_category not in CLASSIFICATION_2
    ):
        changes["custom_historic_classification_2"] = row.custom_classification_2_category
        changes["custom_classification_2_category"] = None
    return changes


def execute():
    # Check before touching schema or data. An unexpected main category needs a
    # human mapping decision, because Main category is mandatory.
    rows = frappe.db.sql(
        """SELECT name, custom_main_category, custom_classification_category,
                  custom_classification_2_category
             FROM `tabHD Ticket`""",
        as_dict=True,
    )
    unexpected_main = [
        row.name for row in rows if row.custom_main_category not in MAIN
    ]
    if unexpected_main:
        frappe.throw(
            f"Classification migration stopped: {len(unexpected_main)} tickets "
            "have an unapproved Main category. Review them before deploying."
        )

    create_custom_fields({
        "HD Ticket": [
            {
                "fieldname": "custom_historic_classification",
                "label": "Historic Classification",
                "fieldtype": "Data",
                "insert_after": "custom_classification_2_category",
                "read_only": 1,
                "no_copy": 1,
            },
            {
                "fieldname": "custom_historic_classification_2",
                "label": "Historic Classification 2",
                "fieldtype": "Data",
                "insert_after": "custom_historic_classification",
                "read_only": 1,
                "no_copy": 1,
            },
        ]
    })
    frappe.clear_cache(doctype="HD Ticket")

    for row in rows:
        changes = legacy_changes(row)
        if changes:
            # This does not run ticket hooks, send mail, or move the ticket to
            # the top of agents' Last Modified view.
            frappe.db.set_value("HD Ticket", row.name, changes, update_modified=False)

    for fieldname, options in (
        ("custom_main_category", MAIN),
        ("custom_classification_category", CLASSIFICATION),
        ("custom_classification_2_category", CLASSIFICATION_2),
    ):
        name = f"HD Ticket-{fieldname}"
        if not frappe.db.exists("Custom Field", name):
            frappe.throw(f"Classification migration stopped: missing {name}")
        frappe.db.set_value(
            "Custom Field", name,
            {"options": "\n".join(options), "permlevel": 9},
        )

    # Level 9 keeps the values readable in Helpdesk while reserving writes for
    # System Managers. AI imports using Administrator/ignore_permissions remain
    # able to populate newly created tickets.
    for role, can_write in (
        ("Agent", 0),
        ("Agent Manager", 0),
        ("HD Customer", 0),
        ("HD Customer Manager", 0),
        ("System Manager", 1),
    ):
        if not frappe.db.exists(
            "Custom DocPerm", {"parent": "HD Ticket", "role": role, "permlevel": 9}
        ):
            add_permission("HD Ticket", role, 9)
        update_permission_property("HD Ticket", role, 9, "read", 1)
        update_permission_property("HD Ticket", role, 9, "write", can_write)

    template = frappe.get_doc("HD Ticket Template", "Default")
    existing = {field.fieldname for field in template.fields}
    for fieldname in (
        "custom_historic_classification",
        "custom_historic_classification_2",
    ):
        if fieldname not in existing:
            template.append("fields", {"fieldname": fieldname, "required": 0})
    template.save(ignore_permissions=True)
    frappe.clear_cache(doctype="HD Ticket")
