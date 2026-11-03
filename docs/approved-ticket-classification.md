# Approved Helpdesk ticket classification

The three live classification fields use these exact, case-sensitive choices:

| Field | Choices |
| --- | --- |
| Main category | Contracts; Contract Queries; Human Review; Allocation; Special Offers; Stop Sales |
| Classification | Transfer Contract; Xml; Chm; Extranet; Fit; Booking Amendment; Booking Query; Vcc |
| Classification 2 | Amendment; Loading; Supplier Query; Content; Special Offers Amendment; Special Offers; Finance; Tech; Accommodation; Transfers |

The migration checks all existing main categories before changing anything. It stops if an unapproved main category exists, because that mandatory value needs a human decision. For Classification and Classification 2, a nonempty value outside the approved choices is copied to its matching read-only Historic field and cleared from the active field. Valid values remain untouched. The original ticket `modified` timestamp is retained, and ticket save hooks are not run. The two Historic fields appear in the Helpdesk ticket details when populated.

The three active fields use Frappe permission level 9: agents, managers and customers can read them, while System Managers can write them. The desktop and mobile ticket details and bulk edit hide classification editing from non-admin users. The HD Ticket validation also rejects changes to the three active fields and two Historic fields from non-admin users. System Managers and the Administrator retain correction access. AI imports using Administrator or `ignore_permissions` can still populate new tickets; the actual integration identity and roles must be checked before restricting creation further. The patch does not change assignment, status, source mailbox or outbound email settings.

The pre-deployment audit on 3 November 2026 found 4,662 tickets: no invalid main category, 749 invalid Classification entries, 444 invalid Classification 2 entries, and 786 distinct tickets with at least one invalid entry. Of these, 407 had both fields invalid. The patch recomputes the actual set at deployment rather than relying on those counts.
