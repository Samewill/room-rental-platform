# Phase 9 Web Conversations Progress

## Status

The first web-conversation experience is implemented. A conversation is
created atomically with each new contact request and has the requesting tenant
and listing landlord as participants. Authenticated participants can open the
Messages area from either dashboard, list conversations, retrieve and send
messages, and mark messages from the other participant as read.

WhatsApp integration is not implemented yet.

## API routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/users/me/conversations` | List conversations for the authenticated participant. |
| `GET` | `/api/v1/conversations/{conversation_id}/messages` | Retrieve messages after checking participant membership. |
| `POST` | `/api/v1/conversations/{conversation_id}/messages` | Send a message as the authenticated participant. |
| `POST` | `/api/v1/conversations/{conversation_id}/messages/{message_id}/read` | Mark a message from the other participant as read. |

The frontend is available at `/conversations`. It includes an inbox, a
conversation thread, message composition, explicit read-status updates, loading
and error states, refresh actions, and empty states. Tenant and landlord
dashboards link to the inbox, and a newly submitted listing contact request
links directly to Messages.

## Data integrity and authorization

- Each contact request can have at most one conversation.
- Conversation participants are created from the contact-request tenant and
  the owner of the requested listing.
- The database enforces that a message sender is a participant in its
  conversation using a composite foreign key.
- Every conversation and message operation checks authenticated participant
  membership. A nonparticipant receives a not-found response.
- Message content is trimmed and limited to 4,000 characters.
- Message status is `sent` or `read`; the sender cannot mark their own message
  as read.
- A landlord cannot create a contact request against their own listing.

## Database migration

Migration `20261102_10_create_conversations.py` follows Phase 8 revision
`20261102_09`. It creates conversations, participants, and messages.

The migration was applied to the configured database; Alembic now reports
`20261102_10` as the current head.

## Verification

- Backend test suite: 246 passed.
- Python compilation and `git diff --check`: passed.
- Frontend production build: passed.
- The migration was also exercised against a temporary SQLite database; the
  composite sender-participant foreign key rejected a nonparticipant sender,
  and conversation deletion cascaded to its participants and messages.
- The live database contains all three new tables and the sender-participant
  foreign key.
- After restarting the backend, its database health check passed, the
  conversation routes appeared in OpenAPI, and an unauthenticated conversation
  request returned `401`.
- The unauthenticated browser route correctly redirects to the sign-in view.
- The signed-in message exchange has not been browser-smoke-tested.
- The full offline Alembic upgrade script could not be generated because an
  earlier Phase 3 migration expects a live query result in offline mode.
