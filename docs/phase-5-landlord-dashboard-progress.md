# Phase 5 Landlord Dashboard Progress

## Scope and status

The landlord dashboard supports creating, viewing, editing, submitting, and
closing listings. Landlord-only API operations derive the owner ID from the
authenticated account and only retrieve or update listings owned by that
landlord.

The listing status workflow is:

```text
draft -> pending -> active
   |         |         |
   +---------+---------+-> closed
```

New listings start as drafts. Submitting a draft moves it to `pending`.
Editing a pending or active listing returns it to `draft` so it must be
submitted again. Withdrawing any non-closed listing moves it to `closed`.
Closed listings cannot be edited or receive more photos.

Only a future administrator moderation workflow can approve a pending listing
and move it to `active`. Until that workflow exists, submitted Phase 5 listings
remain private. The public listing service continues to require both `active`
status and a latest approved moderation decision.

Contact-request viewing is deferred until Phase 6. Admin invitations and
two-step verification are also deferred.

## API routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/users/me/listings` | List the signed-in landlord's listings. |
| `POST` | `/api/v1/listings` | Create a draft listing. |
| `PATCH` | `/api/v1/listings/{listing_id}` | Update an owned listing. |
| `POST` | `/api/v1/listings/{listing_id}/submit` | Submit a draft for moderation. |
| `POST` | `/api/v1/listings/{listing_id}/withdraw` | Close an owned listing. |
| `POST` | `/api/v1/listings/{listing_id}/photos` | Upload an image for an owned listing. |

Listing write endpoints require the landlord role. Ownership is checked in the
database query; clients cannot choose the listing owner ID.

## Cloudinary configuration

Photo uploads use Cloudinary from the backend. Set these values in
`backend/.env`; do not commit the file or send the API secret in chat:

```text
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

Uploads accept JPEG, PNG, and WebP files up to 10 MB. The backend stores the
Cloudinary secure URL in `listing_photos`. If credentials are missing, the API
returns a service-unavailable response rather than pretending the upload
succeeded.

The database stores listing statuses in the PostgreSQL `listing_status_enum`.
Migration `20261029_03` adds the `draft` and `closed` values required by the
Phase 5 workflow; apply it with `alembic upgrade head` before creating listings.

## Remaining work

- Add the administrator moderation workflow in Phase 7 so pending listings can
  become active.
- Add tenant contact-request creation and landlord request views in Phase 6.
- Configure local Cloudinary credentials and verify an actual photo upload
  before using that feature.
- Admin invitations and two-step verification remain deferred.
