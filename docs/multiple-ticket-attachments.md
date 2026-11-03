# Selecting several ticket attachments

The attachment picker accepts multiple files in one selection for agent replies,
internal comments and the shared compact editor used by bulk replies and forwards.
The existing ticket creation editor also uses it for users with creation access.
This does not grant agents permission to create tickets.

On Mac, hold Command while selecting separate files, or Shift for a range. On
Windows, use Ctrl or Shift. Each uploaded file appears separately in the existing
attachment list and can be removed individually.

## Implementation and privacy

`AttachmentUploader.vue` uses Frappe UI's published `useFileUpload()` API, the
entry point its documentation recommends for custom UI and multiple files. The
installed `frappe-ui@1.0.0-rc.1` already exports this API. No dependency upgrade,
package patch, Framework change or additional fork is required.

Every upload explicitly sets `private: true`. Existing Frappe authentication,
CSRF handling, file-size checks, server permissions and document references are
preserved by the library upload implementation. The picker does not change email
recipients, sender routing, existing file privacy or attachment download access.

Files upload sequentially. The editor's existing busy guard stays active for the
whole batch. A failed upload displays a notification, keeps successful attachments
and continues with the remaining files. The picker resets after selection so the
same file can be selected again. Leaving the editor cancels the active upload and
stops the queued files; it does not delete previously completed uploads.

## Verification

18 isolated checks passed against the mounted picker and the unmodified published
Frappe UI upload implementation, with simulated XMLHttpRequest transport. Checks
cover multiple selection, sequential requests, private FormData and document
references, the whole-batch busy state, partial failure, size limits, retry,
cancellation, single-file regression and compilation of all changed Vue SFCs.

Browser regression cases cover Reply and Comment batch selection and check that
all three uploaded File records are private and attached to the intended ticket.
These bench tests and the full application assets build have not been run locally;
a linked Framework UI/bench is not available. No production files or emails were
used in the local checks.

After deployment, rehearse with three non-sensitive files, confirm each appears,
remove one, and verify the remaining attachments on an approved test reply and an
internal comment. Existing mail-provider total attachment-size limits still apply.
