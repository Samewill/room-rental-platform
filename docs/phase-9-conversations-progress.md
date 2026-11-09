# Phase 9 Conversations and WhatsApp Progress

## Status

The web inbox and two-way WhatsApp relay are implemented. A conversation is
created atomically with each new contact request and has the requesting tenant
and listing landlord as participants. Authenticated participants can open the
Messages area from either dashboard, list conversations, retrieve and send
messages, and mark messages from the other participant as read.

The WhatsApp Business Cloud API is used as an intermediary. Website messages
are sent from the platform's business number to the other participant when
that participant has verified and opted in. Incoming text replies are stored
as ordinary conversation messages and forwarded through the platform number
to the other participant when they have also opted in.

## API routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/users/me/conversations` | List conversations for the authenticated participant. |
| `GET` | `/api/v1/conversations/{conversation_id}/messages` | Retrieve messages after checking participant membership. |
| `POST` | `/api/v1/conversations/{conversation_id}/messages` | Send a message as the authenticated participant. |
| `POST` | `/api/v1/conversations/{conversation_id}/messages/{message_id}/read` | Mark a message from the other participant as read. |
| `POST` | `/api/v1/conversations/{conversation_id}/messages/{message_id}/whatsapp/retry` | Retry a failed WhatsApp delivery as the original sender. |
| `GET` | `/api/v1/users/me/whatsapp` | Return whether the current user has enabled WhatsApp messaging. |
| `POST` | `/api/v1/users/me/whatsapp/verification` | Send a WhatsApp ownership-verification template after explicit opt-in. |
| `POST` | `/api/v1/users/me/whatsapp/verification/confirm` | Verify the six-digit code and enable WhatsApp messaging. |
| `DELETE` | `/api/v1/users/me/whatsapp` | Unlink the WhatsApp number and opt out. |
| `GET` | `/api/v1/webhooks/whatsapp` | Verify the provider's webhook challenge. |
| `POST` | `/api/v1/webhooks/whatsapp` | Accept signed inbound WhatsApp webhook events. |

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
- WhatsApp linking requires explicit consent and a six-digit, ten-minute
  verification code sent to the supplied E.164 number. Verification attempts
  are capped, and resend requests are throttled.
- The verified WhatsApp number is stored encrypted with AES-GCM; a keyed HMAC
  digest is used for inbound lookup. The existing public user profile no longer
  returns `phone_no`.
- Web and WhatsApp messages containing phone-number-like text are rejected;
  legacy message content is redacted in message API responses. The platform
  never puts a participant's phone number in relay text or logs.
- Meta webhook requests require an HMAC-SHA256 signature. Provider message IDs
  are unique in the database, making webhook retries idempotent.
- Website senders can view and retry their own failed WhatsApp deliveries; the
  other participant cannot see whether a WhatsApp number is linked.
- Replies are routed by the provider's quoted-message ID when available, or
  by an opaque conversation reference. If a sender has multiple conversations
  and a reply has no reference, the platform requests one rather than guessing.
- `STOP` unlinks the WhatsApp number; the user can link again through the
  verified opt-in flow.
- WhatsApp messages sent outside the provider's 24-hour service window use an
  approved message template; messages within the window use text messages.

## Database migration

Migration `20261102_10_create_conversations.py` follows Phase 8 revision
`20261102_09`. It creates conversations, participants, and messages.
Migration `20261105_11_whatsapp_messaging.py` adds encrypted contact mappings,
provider message IDs, and conversation routing codes. It has been exercised
against temporary SQLite; it has not been applied to the configured database.
The configured database remains at revision `20261102_10`; the WhatsApp
migration must be applied as part of deployment.
Existing `users.phone_no` values are not trusted as verified WhatsApp numbers;
each user must link and verify a number through the opt-in flow.

### Provider configuration

Configure these server-side environment variables before applying migration
`20261105_11` and deploying:

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID` (the platform's Meta Business phone-number ID)
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_PHONE_ENCRYPTION_KEY` (URL-safe base64 encoding of 32 random bytes)
- `WHATSAPP_PHONE_LOOKUP_KEY` (independent random secret, at least 32 bytes)
- `WHATSAPP_GRAPH_API_VERSION` (defaults to `v23.0`)
- `WHATSAPP_TEMPLATE_LANGUAGE` (defaults to `en_US`)
- `WHATSAPP_VERIFICATION_TEMPLATE_NAME` (defaults to `rental_phone_verification`)
- `WHATSAPP_MESSAGE_TEMPLATE_NAME` (defaults to `rental_message_notification`)

Both templates must be approved in Meta and have one body parameter. Configure
Meta's webhook callback as `/api/v1/webhooks/whatsapp` with the verify token
above and subscribe it to inbound message events. Keep the encryption and
lookup keys stable; changing either requires relinking verified numbers. Do
not commit these secrets or send them in chat.
After configuring a production database and credentials, apply the migration
from `backend` with `python -m alembic upgrade head`, then register the public
HTTPS webhook URL with Meta.

## Verification

- Focused WhatsApp and affected API tests: 53 passed.
- Full backend test suite: 270 passed, 1 unrelated reporting test failed
  because the installed Starlette lacks `HTTP_422_UNPROCESSABLE_CONTENT`.
- Python compilation and `git diff --check`: passed.
- Frontend production build: passed.
- The migration was also exercised against a temporary SQLite database; the
  composite sender-participant foreign key rejected a nonparticipant sender,
  and conversation deletion cascaded to its participants and messages.
- The live database contains the three existing conversation tables and the
  sender-participant foreign key; the WhatsApp migration is still pending.
- After restarting the backend, its database health check passed, the
  conversation routes appeared in OpenAPI, and an unauthenticated conversation
  request returned `401`.
- The unauthenticated browser route correctly redirects to the sign-in view.
- The signed-in message exchange has not been browser-smoke-tested.
- The full offline Alembic upgrade script could not be generated because an
  earlier Phase 3 migration expects a live query result in offline mode.
- WhatsApp privacy, webhook signature/challenge, reply routing, provider request,
  API response privacy, and migration uniqueness tests were added. A live Meta
  delivery test remains pending Business credentials and approved templates.

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
