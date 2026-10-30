# Original emails and mailboxes

The existing **Original emails / mailboxes** ticket action opens
`/ticket-origins?ticket=<name>`. Helpdesk owns this read-only page so the action
does not depend on the removed LH Email Triage app.

The page requires a signed-in Helpdesk agent with read access to the ticket. It
lists received Email Communications on the ticket and accessible merged source
tickets, including the stored Email Account, time, message ID and links to each
record. Queries retain Frappe permissions and have explicit limits. No email
body is returned. The page disables caching and escapes displayed data.

Deploying the Helpdesk app registers the route. The existing HD Form Script
continues to supply the button; no site record or ticket data migration is
needed. After deployment, open a ticket with a received email and check that
the button shows its receiving mailbox. A missing or inaccessible ticket must
not expose its origin records.
