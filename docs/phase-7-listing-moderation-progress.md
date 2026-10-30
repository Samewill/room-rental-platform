# Phase 7: Listing moderation progress

## Scope

This progress file covers the listing-moderation stream only. Reporting is a
separate Phase 7 feature and is not included.

The admin workspace supports:

- Reviewing pending listings.
- Approving pending listings, which changes their status to `active`.
- Rejecting pending listings with a required reason, returning them to `draft`
  so landlords can edit and resubmit.
- Hiding published listings with a required reason, changing their status to
  `removed`.
- Viewing append-only moderation history, including the admin, decision,
  reason, and timestamp.

Approval reasons are optional. Rejection and hiding reasons must contain
non-whitespace text. Each moderation decision is recorded in
`listing_moderation`; existing decisions are not overwritten.

Only authenticated administrators can use the moderation API. Public listings
continue to require `active` status and a latest `approved` decision.

## API routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/admin/listings/pending` | List pending listings. |
| `GET` | `/api/v1/admin/listings/published` | List currently public listings available to hide. |
| `GET` | `/api/v1/admin/listings/{listing_id}/moderation-history` | Read a listing's decision history. |
| `POST` | `/api/v1/admin/listings/{listing_id}/approve` | Approve a pending listing. |
| `POST` | `/api/v1/admin/listings/{listing_id}/reject` | Reject a pending listing with a reason. |
| `POST` | `/api/v1/admin/listings/{listing_id}/hide` | Hide an active listing with a reason. |

## Database migration

Migration `20261030_04` ensures the `moderation_decision_enum` and
`listing_moderation` table exist. It preserves an existing moderation table and
history. The configured database currently reports revision `20261030_04`;
the moderation table still contains its four existing history rows.

## Not included

- Tenant reports and the admin report queue.
- Reinstating a hidden listing.
- Admin invitations or two-step verification.
