# Ticket deadline dates

The Helpdesk ticket list displays `custom_due_date_and_time` (Due Date and Time)
and `custom_follow_up_at` (Follow-up at) as absolute dates and times. These fields
use the existing `dateFormat` helper, including the configured date format, time
format and timezone handling. Empty values display an empty cell.

The column overrides live in `desk/src/pages/ticket/Tickets.vue`. They apply
regardless of the column's position and use the same renderer in saved ticket
views. Created and other relative-time columns retain their existing behavior.

This is a display change only. It does not update ticket values, add custom
fields, change date filters or sorting, or schedule follow-ups. It requires a
Helpdesk frontend asset rebuild and deployment; no data migration is needed.

After deployment, refresh Helpdesk and add the two fields through Columns.
Check a ticket with a known deadline against the date in its sidebar, and check
that an unset deadline stays blank. Sort and filter by the deadline to confirm
that the original stored values are still used.
