# Ticket view auto refresh

The agent ticket list reloads its current view every 30 seconds while its browser
tab is visible. Returning to a hidden tab reloads the view immediately. The
existing new-ticket socket event and manual refresh button remain available.

The timer calls the existing `ListViewBuilder.reload()` method, which keeps the
current view, filters, sort order and page length. It skips a refresh while the
list is loading or an export, view editor, bulk reply, bulk edit or bulk assign
dialog is open. The timer and visibility listener are removed when the ticket
list page closes. Customer portal ticket lists are unchanged.

This is a frontend-only change. It requires a Helpdesk asset build and bench
deployment, with no site schema or data migration. A reload fetches the latest
list data; it does not update an individual ticket page or provide instant
delivery guarantees. Agents can still use the manual refresh button at any time.
