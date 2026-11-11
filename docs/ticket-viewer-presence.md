# Ticket viewer indicator

The desktop agent ticket header shows the names of other signed-in users reported as viewing the same ticket. It hides the current user's own identity. When the latest snapshot contains no other viewers, the badge is hidden. This is awareness, not a ticket lock or a guarantee that nobody else can reply.

The badge shows “Checking who is viewing…” until the server replies. On disconnect, connection error or no response within eight seconds, names are cleared and it shows “Viewer status unavailable”. Reconnection rejoins the current ticket automatically. An in-memory viewer snapshot is requested every 20 seconds to clear stale occupants after abrupt disconnects. The existing socket reconnection policy is unchanged; a permanently failed socket may require a page refresh.

Ticket changes leave the old room and join the new one. Late responses for other tickets are ignored. Component disposal removes only its own socket listeners, timer and browser unload handler. No new database records, permissions, API endpoints or credentials are introduced. The existing server-side room behaviour is unchanged.

Typing remains the existing, separate composer indicator; this change does not repair its independent lifecycle. The new header label is on the desktop agent ticket view; the mobile ticket layout is unchanged.

## Verification

Run `node --test desk/tests/ticketPresence.test.mjs`.

After deployment, use two different authorised agent accounts on the same ticket. Check the second name appears; then navigate to another ticket and ensure it disappears. Disconnect/reconnect one browser and confirm tracking recovers. After an abrupt browser close, allow up to 20 seconds plus the snapshot response for the other view to clear. No emails need to be sent.

This PR has controller regression tests and Vue compilation checks. Full production build and live two-agent browser verification still need completing in the deployment environment.
