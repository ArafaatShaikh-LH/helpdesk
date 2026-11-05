"""Recipient policy for ticket replies; no delivery or database writes."""

from email.utils import getaddresses


def addresses(value):
    """Parse mail headers, preserving address order and ignoring display names."""
    if not value:
        return []
    headers = [value] if isinstance(value, str) else value
    result = []
    seen = set()
    for _, address in getaddresses([header for header in headers if header and header.strip()]):
        address = address.strip()
        key = address.casefold()
        if "@" in address and key not in seen:
            result.append(address)
            seen.add(key)
    return result


def reply_recipients(email, mailbox_addresses, own_address=None, reply_all=True):
    """Continue sent email to its recipients; reply to incoming email's sender."""
    mailboxes = {a.casefold() for a in addresses(mailbox_addresses)}
    own = {a.casefold() for a in addresses(own_address)}
    excluded = mailboxes | own
    sender = addresses(email.get("sender"))
    sent = email.get("sent_or_received") == "Sent" or any(
        a.casefold() in excluded for a in sender
    )
    to = addresses(email.get("recipients")) if sent else sender
    cc = []
    if reply_all:
        cc = addresses(email.get("cc"))
        if not sent:
            cc = addresses(email.get("recipients")) + cc
    to = [a for a in to if a.casefold() not in excluded]
    used = excluded | {a.casefold() for a in to}
    unique_cc = []
    for address in cc:
        if address.casefold() not in used:
            unique_cc.append(address)
            used.add(address.casefold())
    # A copied mailbox must never become the only To address. If all original
    # To addresses were internal mailboxes, expose remaining participants as To.
    if not to and unique_cc:
        to, unique_cc = unique_cc, []
    # Bcc is never reconstructed from another message's hidden recipients.
    return {"to": to, "cc": unique_cc, "bcc": []}
