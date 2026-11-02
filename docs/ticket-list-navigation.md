# Previous and Next ticket navigation

The desktop ticket header shows Previous and Next beside the existing actions.
The position counter shows the current ticket's place in the loaded list.
On desktop widths, a collapsible left pane shows the loaded ticket IDs,
subjects and statuses in the same order. Clicking a row opens that ticket;
the active row is highlighted and scrolled into view. The pane remains hidden
for direct links without a matching list and on smaller screens, where the
header navigation remains available. The ticket details panel stays on the right.
Subjects and statuses are kept in memory only. After a page refresh, the pane
loads them using the standard permission-checked ticket list API.

Navigation follows the exact order of the loaded ticket list, including unsaved
filters, sorting, saved views and grouped rows. The list's ticket IDs and view
name are stored in sessionStorage, scoped to the signed-in user and browser tab.
No message bodies, customer details or attachments are stored by this feature.
Opening a ticket in a new tab can inherit that tab's sessionStorage, depending
on the browser. Direct links without a matching list context have disabled
buttons rather than falling back to an unrelated queue.

Previous is disabled at the beginning; Next is disabled at the end. There is no
wraparound. If more matching tickets exist than are loaded, the Next tooltip
asks the agent to return to the list and load more. The feature does not fetch
additional tickets or bypass ticket permissions. Refreshing the same tab retains
its list context. Returning to a list replaces the context with its current
results. Opening a different saved view does not reuse a mismatched context.

The existing Shift + < / > shortcuts and command-palette actions use the same
neighbors as the buttons. Navigation derives its position from the current
route, so opening a middle ticket or using browser Back does not reset to the
first result. Buttons are disabled while a route change is pending.

The agent root keys the ticket component by ticket ID. A ticket change therefore
unmounts the old composer and mounts the next ticket's own timeline and draft.
This preserves the existing per-ticket draft save on unmount and avoids reusing
setup state for a different ticket. Existing draft storage is unchanged.

## Acceptance checks

1. Filter and sort a list, open a middle ticket, and use Previous/Next. Confirm
   the sequence matches the list and the saved view remains selected.
2. Check the first/last ticket, a single result, no matching list context,
   grouped lists, refresh, browser Back and opening in another tab.
3. Start a reply with a changed recipient and attachment, switch tickets,
   return and reopen Reply. Confirm the original draft is retained only on its
   own ticket. Also verify the new ticket's timeline shows its own messages.
4. At the end of a partially loaded list, verify Next is disabled and the
   tooltip explains how to load more.
5. Open a filtered list and use the left pane. Confirm its rows match the
   loaded list, the selected row stays visible, and Hide list restores space.

This frontend change requires a new Helpdesk assets build and deployment. It
changes no server APIs, email routing, ticket records, roles or sharing rules.
