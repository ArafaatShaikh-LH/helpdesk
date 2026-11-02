# Ticket reply drafts

## Behaviour

The agent reply composer saves the body, quoted email, To/Cc/Bcc recipients and
uploaded attachment references in browser storage under the ticket ID. Changes
are saved synchronously, so
leaving a ticket immediately after typing does not drop the last edit. Reopening
the same ticket in the same browser restores the draft. The composer shows
“Draft saved on this device” while a message body is present.

Sending or selecting Discard resets the stored draft and recipients. The normal
reply sender policy still chooses the From mailbox. The draft does not sync
across browsers or devices. The stored attachment list refers to files already
uploaded to the ticket; it does not copy file bytes into browser storage.

## Reason for this change

The body previously copied its value into browser storage from a default Vue
watcher. That watcher could run after a ticket navigation unmounted the
composer, leaving the latest text unsaved. Synchronous storage and an explicit
unmount save close that gap. Recipient storage ensures reopening a draft does
not silently revert its To/Cc/Bcc choices.

## Acceptance check

1. Open a ticket, type a reply, change To/Cc, then click the ticket number or
   navigate away immediately. Return to the ticket and reopen Reply. The text
   and recipients should still be present. Repeat with one uploaded attachment.
2. Open another ticket. Its reply draft must be independent.
3. Discard the first draft, leave and return. The discarded text must not return.
4. Send a reply and return. The sent text must not reappear as a draft.

This is a frontend-only change; it needs a new Helpdesk frontend build and
deployment before agents see it.
