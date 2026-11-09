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

That migration was applied to the configured database; at the time this status
was recorded, the configured database revision was `20261102_10`.

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

## Website AI assistant

The website now includes a role-specific AI assistant widget for signed-in
tenants and landlords. It is separate from the persisted tenant–landlord
Messages area; assistant conversations and workflow state are stored in their
own tables so they can be reopened after signing in again.

### Assistant workflows

- Tenant conversations use LangGraph to extract room-search criteria. Search
  results are filtered from `ListingService.list_public_listings()`, which
  already restricts results to active, approved listings. Listing cards,
  prices, addresses, amenities, and availability are populated only from those
  service responses. Unsupported amenity requests do not return approximate
  matches. Contact requests use the existing contact-request API.
- Landlord conversations collect the fields required by
  `ListingCreateRequest`, use the existing area and amenity catalogs, and show
  a review summary before the landlord confirms. Confirmation calls the
  existing `LandlordListingService`; it creates a draft and does not publish
  it. Optional photos are uploaded using the existing photo endpoint.
- When an administrator approves or rejects a listing, the moderation
  transaction also creates a landlord assistant conversation with a persisted
  decision notification. Approval notifications link to the published listing;
  rejection notifications include the admin's reason and link to the landlord
  dashboard to edit the draft. An open assistant widget refreshes the
  conversation list every 10 seconds and opens a new notification conversation;
  landlords see it when they next open the widget if it was closed.
- Assistant history is owner-scoped. The API checks the user's tenant or
  landlord role and conversation ownership before reading or changing a
  conversation. A listing is created only by the explicit confirmation route.

### AI provider configuration

Inception is tried first and Groq is used as a fallback. Configure
`INCEPTION_API_KEY` and/or `GROQ_API_KEY` in `backend/.env`; never put provider
keys in the frontend. Model, token, retry, backoff, and timeout settings are
available in `backend/.env.example`. The user-provided `MISTRAL_API_KEY` is not
used by the selected Inception/Groq routing.

### Assistant API routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/assistant/conversations` | List the authenticated user's assistant conversations. |
| `POST` | `/api/v1/assistant/conversations` | Start a tenant or landlord assistant conversation. |
| `GET` | `/api/v1/assistant/conversations/{conversation_id}` | Retrieve an owned conversation and its messages. |
| `POST` | `/api/v1/assistant/conversations/{conversation_id}/messages` | Add a message and run the role-specific LangGraph workflow. |
| `POST` | `/api/v1/assistant/conversations/{conversation_id}/confirm-listing` | Confirm a complete landlord draft and create it through the existing service. |

Migration `20261105_11_create_ai_assistant.py` creates the assistant
conversation and message tables. Apply it with `alembic upgrade head` from the
backend directory before using the assistant against the database. It was not
applied to the configured database as part of this implementation.

### Verification

- Backend suite: 264 passed, including assistant graph, API authorization,
  provider fallback, and listing-filter tests.
- Frontend TypeScript check and production build: passed.
- The new migration upgrade and downgrade both passed against a temporary
  SQLite database. The configured database was not changed.
- A live provider request and signed-in browser chat have not been exercised;
  provider behavior is covered with mocked requests in tests.
