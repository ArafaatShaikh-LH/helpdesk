# Follow-up recipients and shared mailboxes

Replies to a selected sent email continue to its original To recipients. Reply All keeps its original Cc participants. Replies to an incoming email address its sender; Reply All also includes other visible recipients. Configured email-account addresses and the current agent's own address are excluded from automatic To/Cc defaults. If only copied participants remain, they become To. Bcc is not copied.

The footer composer starts from the latest email by communication date, rather than the ticket's original contact. Tickets without email history fall back to their original requester. Existing saved or edited drafts are preserved; to replace an old draft's recipient list, click Reply or Reply All on the intended email, or discard and reopen it. Inspect To/Cc and choose a From mailbox before sending.

A server check rejects any reply that includes its sending mailbox in To, Cc or Bcc before creating a Communication or queuing email. This prevents direct self-addressed replies. It is not a complete defence against external forwarding loops, aliases not configured as Email Accounts, or every AI intake path.

Recipient resolution requires an active agent and ticket read access; a selected Communication must belong to that ticket. This release does not change contact data, historic email headers, receiving mailbox selection, forwarding, or queued messages. No customer data is included in tests.
