# Ticket classification and team routing

Agents edit Main Category, Classification and Classification 2 directly in More Details on desktop or mobile. These Select fields use the approved options; agents cannot create or rename options. Only System Managers can edit Custom Field, Property Setter and Customize Form. The former Change classification / team form and its API have been removed.

The deployment patch enables Agent and Agent Manager write access at permission level 9 for the three active fields. Customer roles retain read-only access at that level. Historic Classification and Historic Classification 2 stay read-only, with a server guard against non-admin changes. No ticket data is backfilled by the patch.

Changing Main Category sets Team to the matching name, including Human Review. An unchanged category preserves a manual Team override. Existing nested values incompatible with a newly selected category are cleared; agents can select the new applicable values afterwards. Explicit invalid or unapproved selections are rejected on the server. Blank nested values are allowed while making sequential edits. Unrelated edits to legacy tickets are not blocked by old mismatched nested values.

Each saved classification change records previous values, new values, user and time in HD Classification Review, retaining the existing audit records. This record supports review and reporting; it does not automatically retrain an AI model. Standard ticket permissions and Version tracking remain. A team change can remove an assignee outside that team under the existing assignment hooks. It does not change the reply mailbox or create another ticket.

Human Review remains a team queue. Members are selected by the team lead; no person is assigned by this change. Existing individual-distribution rules are unaffected.

Before release, run server checks for agent edits, customer denial, historic-field protection, invalid options, category/team routing, clearing incompatible nested values and audit capture. After deployment, rehearse as an ordinary agent on a synthetic ticket, check the three direct dropdowns and confirm there is no correction form. Verify an agent cannot edit classification definitions. Production deployment remains a separate step.
