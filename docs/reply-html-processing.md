# Reply HTML processing

## Behaviour

Agent replies pass through `HDTicket.parse_content` before the outgoing
email is queued. A failure rolls back the reply transaction, including its
new Communication. `ReplyHTMLParser` transforms that HTML as
a stream rather than building and serializing a BeautifulSoup tag tree.

It removes HTML comments (including Outlook conditional comments) and converts
local `/files/` and `/private/files/` image/video `src` attributes into `embed`
attributes for Frappe's inline attachment handling. External, data and CID URLs
keep their existing `src`. Text, entities, tables, links and quoted content are
retained. Rewritten attribute values are HTML-escaped.

The parser does not flatten or truncate the conversation, increase Python's
recursion limit, or change sender selection, recipients, permissions, attachment
selection or email queue delivery. It is not an HTML sanitizer; the existing
Framework sanitization and file-access checks still apply. Existing composer
draft restoration on send failure is unchanged.

## Failure prevented

Deeply nested quoted HTML could raise `RecursionError` in BeautifulSoup's tag
comparison during serialization, before the reply was queued. Nesting alone is
not sufficient to reproduce this: whitespace between closing wrappers also
matters. A synthetic 3,000-layer quote with interleaved closing whitespace
reproduces the old failure without including any customer content.

## Validation and rollout

The `test_parse_content_*` cases in `test_hd_ticket.py` cover deep quotes,
Outlook comments, local inline media, external/data/CID URLs, formatting,
entities and attribute escaping. Run them through the normal Frappe test runner.

After deployment, use a synthetic ticket and an approved test recipient to
check a deep quoted reply with a PDF attachment. Confirm one Communication and
queue entry, receipt, readable quoted text and the attachment. Do not retry a
real supplier draft automatically. Deployment and an actual delivery test are
separate from the local parser tests.

Rollback is a revert of the code commit and redeploy. No database migration or
site configuration change is required.
