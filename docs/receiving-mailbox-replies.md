# Agent reply mailbox routing

This fork change is based on Helpdesk v1.31.0 (7d7e394), matching the deployed site and compatible with Frappe Framework 16. Do not deploy the fork's upstream develop branch: it requires Framework 17.

Enable **HD Settings → Reply from receiving mailbox** (`reply_from_receiving_mailbox = 1`) after deployment and migration. The setting defaults off, preserving upstream behavior until explicitly enabled.

When enabled:

- Replies use the `email_account` on the latest Received / Email Communication linked to the ticket. Later outgoing replies cannot change this selection. The server enforces the account and matching From address.
- A disabled or deleted receiving account blocks sending with an administrator-facing error; no default sender is substituted.
- With no incoming account metadata, the composer starts blank and the agent must choose an enabled sender. The API rejects a missing choice or an address/account mismatch.
- The sender is scoped to the ticket. Old cross-ticket local storage is ignored in this mode. Late responses from another ticket cannot change the active selection; lookup failures block sending until retried.
- The receiving mailbox appears in the picker even if absent from the agent's saved account preferences, because the server has checked agent role, ticket read permission and outgoing enablement. Tickets without incoming account metadata offer every enabled business mailbox to all agents, regardless of their saved preferences or team memberships. The system **No Reply** account is excluded from manual agent choices and rejected by the reply API.
- System notifications, account invitations, resets, incoming collection, existing queued mail and stored historic Communications are unaffected. The system default Email Account can remain for authentication emails; it is not an agent-reply fallback in this mode.
- Bulk replies with no receiving account require a sender-capable workflow; they cannot silently substitute the global default.

`HD Ticket.get_reply_sender` is a read-only document method. It returns `{ticket, enabled, sender}`, with `sender` null or `{email_account, email_id}`. Sending remains through the existing `reply_via_agent` method and normal Email Queue.

## Local verification

Eight isolated backend policy checks pass, covering routing, explicit choice, invalid and disabled accounts, role and ticket permission checks, and legacy mode. The Vue script and template compile, and isolated composer checks pass for per-ticket defaults, manual choice, late response handling, lookup failure/retry, incoming mailboxes without saved preferences and legacy mode. These checks mock network/database boundaries and are not a full asset build or a Frappe bench test run. The integration test module below is supplied for CI or a configured test bench.

## Verification and deployment

Run `bench --site <test-site> run-tests --module helpdesk.helpdesk.doctype.hd_ticket.test_reply_sender` on a configured test bench. Sender policy tests cover incoming-versus-outgoing precedence, latest incoming account, explicit choice, disabled accounts, address mismatch, permissions and disabled-feature compatibility.

Local checks must distinguish isolated frontend/backend policy checks from full Frappe integration. A passing local policy check is not proof of SMTP delivery. No customer test emails are part of this change.

After the PR is merged, register this fork as the Helpdesk app source in Frappe Cloud and deploy the stable branch. Switch the existing Helpdesk source; do not uninstall Helpdesk or create a second Helpdesk app on the site. Enable the setting, refresh agent tabs, inspect From on existing Contracts and Contract Queries tickets and on a synthetic ticket without incoming mail, and run a separately approved internal delivery test.

Rollback: disable `reply_from_receiving_mailbox`; the prior selection behavior returns. Keep the system email account enabled so authentication email remains available.
