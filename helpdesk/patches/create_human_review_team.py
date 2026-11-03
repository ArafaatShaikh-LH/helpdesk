"""Add the Human Review queue without assigning a person prematurely."""

import frappe


def execute():
    if frappe.db.exists("HD Team", "Human Review"):
        return
    team = frappe.get_doc({"doctype": "HD Team", "team_name": "Human Review"})
    # Members are mandatory in the standard form, but are intentionally chosen
    # later by the team lead. HD Team creates its assignment rule when added.
    team.insert(ignore_permissions=True, ignore_mandatory=True)
