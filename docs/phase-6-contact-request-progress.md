# Phase 6 Contact Request Progress

## Status

The tenant contact-request workflow is implemented for the backend and
frontend. Tenants can request contact from a publicly available listing, view
their own requests and statuses, and cancel pending requests. Landlords can
view requests for their own listings and approve or reject pending requests.

## API routes

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/listings/{listing_id}/contact-requests` | Submit a request as the signed-in tenant. |
| `GET` | `/api/v1/users/me/contact-requests` | List the signed-in tenant's requests. |
| `GET` | `/api/v1/users/me/received-requests` | List requests for the signed-in landlord's listings. |
| `PATCH` | `/api/v1/contact-requests/{request_id}` | Approve or reject as the listing's landlord, or cancel as the requesting tenant. |

The listing owner and tenant IDs are derived from authenticated account data.
The API response contains only the request ID, listing ID, status, and request
time.

## Status and privacy rules

```text
pending -> approved
        -> rejected
        -> cancelled
```

Only pending requests can transition. The listing's landlord can approve or
reject a request, except that a tenant cannot approve their own request. Only
the requesting tenant can cancel it.

Contact-request API responses and request lists do not include tenant phone
numbers, email addresses, names, or tenant IDs. Repeated requests for the same
listing are currently allowed.

Requests can be created only for listings that are publicly available under
the existing listing visibility rules.

## Database migration

Migration `20261030_04_create_contact_requests.py` creates the
`contact_requests` table with foreign keys to `listings` and `users`, a status
constraint, and a request timestamp. It is the current migration revision on
the configured database. A new database should apply the full migration
history with `alembic upgrade head`.

## Verification

- Backend test suite: 128 passed.
- Frontend production build: passed.
- Alembic current revision: `20261030_04`.
