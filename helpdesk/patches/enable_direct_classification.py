"""Permit agents to select existing ticket classifications directly."""

import frappe
from frappe.permissions import update_permission_property


def execute():
    fields = (
        "custom_main_category",
        "custom_classification_category",
        "custom_classification_2_category",
    )
    for field in fields:
        doc = frappe.get_doc("Custom Field", f"HD Ticket-{field}")
        doc.permlevel = 9
        doc.read_only = 0
        doc.save(ignore_permissions=True)
        for name in frappe.get_all(
            "Property Setter",
            filters={"doc_type": "HD Ticket", "field_name": field,
                     "property": ["in", ["read_only", "permlevel"]]},
            pluck="name",
        ):
            setter = frappe.get_doc("Property Setter", name)
            setter.value = "9" if setter.property == "permlevel" else "0"
            setter.save(ignore_permissions=True)

    for role in ("Agent", "Agent Manager"):
        update_permission_property("HD Ticket", role, 9, "read", 1)
        update_permission_property("HD Ticket", role, 9, "write", 1)
    frappe.clear_cache(doctype="HD Ticket")
