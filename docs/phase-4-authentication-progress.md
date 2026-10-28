# Phase 4 Authentication Progress

This document records the Phase 4 authentication work on the
`feature/authentication` branch as of 2026-10-28. It describes the merged
Phase 3 baseline, the authentication implementation, the verified Neon schema
change, tests performed, and known follow-up work.

## Branch and workflow status

- Current branch: `feature/authentication`.
- Phase 3 listing API and Alembic files were merged into this branch before
  authentication work continued.
- Authentication, tests, and frontend changes in the working tree have not
  been committed.
- Work has been done incrementally: one file at a time, with review and
  approval before proceeding. The user later approved creating related files
  together.

## Phase 3 and Alembic baseline

The merged Phase 3 work includes:

- Public listing and area API routes, models, schemas, repositories, and
  services.
- `backend/alembic.ini` and `backend/migrations/env.py`.
- Migration `20261027_01_phase_3_listing_schema.py`, recorded by Neon as the
  existing database revision.

The Alembic history was verified as:

```text
<base> -> 20261027_01 -> 20261027_02
```

The listing implementation was merged as the starting point for the
authentication branch. This document does not assert that every Phase 3
frontend milestone has been completed.

## Database alignment for authentication

Before the Phase 4 migration, the live database had a `users.role` enum rather
than the separate role tables described in the roadmap. The user email and
password-hash columns were nullable.

Migration `20261027_02_normalize_user_roles.py` was added and applied to the
existing Neon database. It:

1. Created `roles` and `user_roles`.
2. Seeded `tenant`, `landlord`, and `admin`.
3. Copied each existing user's role assignment to `user_roles`.
4. Made `users.email` non-null while retaining its unique constraint.
5. Removed `users.role` and the old `user_role_enum`.
6. Left `users.password_hash` nullable.

The hash column remains nullable because two accounts existed without password
hashes. Assigning a fake password or hash would be unsafe. Those legacy
accounts need a password setup/reset flow before they can authenticate.

The live database was subsequently checked read-only and reported revision
`20261027_02`. At the latest recorded aggregate check, it had four users and
role assignments of one admin, one landlord, and two tenants; two users still
had no password hash. No personal account data or credentials are documented
here.

## Authentication policy and implementation

### Registration and password handling

- Public registration lets a new user choose either `tenant` or `landlord`.
- The request role is validated against those two choices and assigned through
  `user_roles`. Public requests cannot assign `admin`.
- The tenant form asks only for name, phone, email, and password. Landlord
  registration can additionally provide an optional business name.
- Existing admins must be created administratively; public registration does
  not provide an admin-signup path.
- Passwords are hashed with Argon2 using `pwdlib`.
- Login verifies the supplied password against the stored hash.
- Email is normalized to lowercase during registration and login.
- Duplicate email or phone conflicts are returned as an account-conflict
  response.
- A new user's record and selected role assignment are committed together.
- The response schemas do not expose `password_hash`.

### Access tokens

- Login issues a JWT bearer access token with a 30-minute default lifetime.
- The token uses HS256 and includes a string user ID subject plus issued-at and
  expiry claims.
- Tokens do not contain role claims. Protected endpoints reload the user, and
  role checks query current role assignments in the database.
- `JWT_SECRET_KEY` is held in local `backend/.env`, not in source control or
  this document. The application rejects a missing secret and requires at
  least 32 bytes when issuing or validating tokens.
- No refresh-token or token-revocation flow is implemented. A token remains
  usable until it expires unless the referenced user is removed.

### Profile and role authorization

- `GET /api/v1/users/me` returns the authenticated user's profile and current
  role names.
- `PATCH /api/v1/users/me` can update `full_name` and `business_name` only.
  Email and phone changes are deferred until a verification flow exists.
- `business_name` can be cleared with `null`; `full_name` cannot be null or
  blank.
- The response includes role names for display. Authorization uses the
  separate `require_role` dependency, which checks current roles from Neon and
  requires an exact role match. Admin does not automatically inherit tenant
  or landlord permissions.
- An admin can grant the landlord role to another existing user through
  `POST /api/v1/admin/users/{user_id}/roles/landlord`.
- The grant adds the landlord role without removing other roles, is
  idempotent, rejects unknown users, and cannot be used by an admin to grant
  the role to themselves. There is no public endpoint to grant admin.
- Successful new grants are logged with the acting admin's ID and target
  user's ID. A persistent role-change audit table has not been added.
- The public home page and listing details remain available without signing in.
- The shared sign-in page loads the profile's current roles and routes admins
  to `/admin`, landlords to `/landlord`, and tenants to `/tenant`. When an
  account has multiple roles, the routing precedence is admin, landlord,
  tenant.
- These are starter dashboards. Landlord listing management, tenant contact
  requests, admin invitations, and admin two-step verification are not yet
  implemented. The `/admin` path is not linked from public pages.
- By user choice, admin invitations and two-step verification are deferred.

## Files changed for Phase 4

| File | Purpose |
|---|---|
| `backend/.env.example` | Documents `JWT_SECRET_KEY` and the 30-minute token setting without a real secret. |
| `backend/requirements.txt` | Adds `pwdlib[argon2]`, `email-validator`, and `PyJWT[crypto]`. |
| `backend/requirements-dev.txt` | Includes runtime requirements and `httpx2` for Starlette's `TestClient`. |
| `backend/app/core/config.py` | Loads the optional masked JWT secret and positive access-token expiry setting. |
| `backend/app/core/security.py` | Hashes and verifies passwords; creates and validates JWT access tokens. |
| `backend/app/models/user.py` | Maps the existing `users` table. |
| `backend/app/models/role.py` | Maps `roles`. |
| `backend/app/models/user_role.py` | Maps the composite user-to-role join table. |
| `backend/app/schemas/admin.py` | Defines the landlord-role grant response. |
| `backend/app/schemas/auth.py` | Defines tenant/landlord registration, login, and token response schemas; admin is excluded from public registration. |
| `backend/app/schemas/user.py` | Defines safe profile output and restricted profile-update input. |
| `backend/app/repositories/user_repository.py` | Looks up and adds users. |
| `backend/app/repositories/role_repository.py` | Looks up roles, lists user roles, and assigns roles. |
| `backend/app/services/auth_service.py` | Assigns the selected public role and authenticates passwords. |
| `backend/app/services/role_service.py` | Grants landlord roles idempotently and logs successful grants. |
| `backend/app/services/user_service.py` | Applies profile changes and controls commit/rollback. |
| `backend/app/api/dependencies.py` | Validates bearer tokens, reloads users, and checks current database roles. |
| `backend/app/api/v1/endpoints/admin.py` | Defines the admin-only landlord-role grant endpoint and blocks self-grants. |
| `backend/app/api/v1/endpoints/auth.py` | Defines registration and login endpoints. |
| `backend/app/api/v1/endpoints/users.py` | Defines authenticated profile read and update endpoints. |
| `backend/app/api/v1/router.py` | Includes auth, user, admin, and existing Phase 3 routers. |
| `backend/migrations/versions/20261027_02_normalize_user_roles.py` | Aligns the live role schema with the roadmap. |
| `backend/tests/test_auth_service.py` | Tests auth-service registration and login behavior. |
| `backend/tests/test_auth_endpoints.py` | Tests registration, login, and profile HTTP behavior. |
| `backend/tests/test_user_service.py` | Tests profile updates and request validation. |
| `backend/tests/test_role_service.py` | Tests landlord-role assignment and transaction behavior. |
| `backend/tests/test_admin_endpoints.py` | Tests admin authorization, self-grant prevention, and landlord-role endpoint behavior. |
| `frontend/package.json` and `frontend/package-lock.json` | Define and lock the React, TypeScript, and Vite frontend dependencies. |
| `frontend/index.html`, `frontend/vite.config.ts`, and `frontend/tsconfig*.json` | Configure the Vite app, local API proxy, and TypeScript builds. |
| `frontend/src/App.tsx`, `frontend/src/main.tsx`, and `frontend/src/api.ts` | Implement public role selection, shared sign-in, in-memory token handling, role-based routing, and API calls. |
| `frontend/src/pages/DashboardPage.tsx` | Provides starter tenant, landlord, and admin dashboards. |
| `frontend/src/App.css`, `frontend/src/index.css`, and `frontend/src/vite-env.d.ts` | Provide responsive authentication/dashboard styling and Vite environment typing. |
| `frontend/.env.example` | Documents the optional API base URL; Vite proxies `/api` to the local backend by default. |

## Available API routes

After starting the backend from the `backend` directory with Uvicorn, the
interactive API page is available at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a tenant or landlord account; admin is not accepted. |
| `POST` | `/api/v1/auth/login` | Verify credentials and return a bearer token. |
| `GET` | `/api/v1/users/me` | Return the authenticated user's profile and roles. |
| `PATCH` | `/api/v1/users/me` | Update the authenticated user's name and/or business name. |
| `POST` | `/api/v1/admin/users/{user_id}/roles/landlord` | Allow an admin to grant the landlord role to another user. |

The `/health` and `/health/database` endpoints remain separate: the former
checks that the API is running, and the latter checks database connectivity.

## Verification performed

Checks were run as changes were made. They included:

- Python syntax checks and module import checks.
- SQLAlchemy model metadata checks against the live database column
  definitions, lengths, nullability, identity, and constraints.
- Pydantic validation checks for valid and invalid registration, login, token,
  profile, and profile-update payloads.
- Argon2 hashing checks, including successful verification and rejection of
  an incorrect password.
- JWT checks for token round-trip, subject and expiry claims, invalid/expired
  tokens, absence of role claims, and missing/short-secret errors.
- FastAPI HTTP checks for registration and login responses, duplicate
  conflicts, selected tenant/landlord roles, rejected admin registration,
  invalid credentials, authenticated profile access, profile
  updates, landlord-role grants, and authorization failures.
- OpenAPI checks confirming routes are available and protected profile routes
  require bearer authentication.
- The backend `unittest` suite currently has 35 tests and was run with
  deprecation warnings treated as errors.
- `npm run build` passed for the frontend.
- The frontend was opened in the integrated browser; login and registration
  forms rendered. A request through Vite's `/api` proxy reached the backend
  profile endpoint and correctly received 401 without authentication.
- Read-only Neon checks of migration revision, tables, role seeds,
  assignment counts, user-column definitions, and constraints.

The user reported completing manual endpoint tests. Subsequent read-only Neon
checks observed four users and two tenant assignments. The assistant's
isolated HTTP checks used mocked services and did not create users or change
Neon; the exact actions taken during the user's manual tests were not
independently recorded. `httpx2` was installed only in the local virtual
environment to support Starlette's `TestClient` and is listed in
`backend/requirements-dev.txt`; it is not a production dependency.

One issue found during verification was corrected: Pydantic's
`model_validate()` does not accept an `update` argument. Profile responses now
validate the ORM object and use `model_copy(update=...)` to include roles.

## Known limitations and next work

- The frontend home and listing detail pages are public. Registration supports
  tenant/landlord selection; tenants see only the four basic signup fields.
  Login is shared, then users are routed to starter role-specific dashboards.
  Tokens remain in memory only, and sign-out does not revoke a token server
  side.
- The two legacy accounts without password hashes cannot log in. A secure
  password setup/reset process is needed before making `password_hash`
  non-null.
- There is no email or phone verification flow, so those fields cannot be
  changed through profile updates.
- There are no refresh tokens, server-side logout/revocation mechanism, or
  account lockout/rate-limiting policy yet.
- Public registration cannot grant admin access. An admin-only landlord grant
  exists, but there is no revoke endpoint or persistent audit history;
  successful grants are recorded in application logs.
- Admin invitations and two-step verification were explicitly deferred. Admin
  accounts must currently be provisioned outside public registration, and
  existing admin logins do not yet have a second-factor challenge. Do not treat
  the starter `/admin` page as a substitute for MFA or a complete admin console.
- Tenant contact requests and landlord listing management are not implemented;
  the dashboards are routing/UI starters only.
- The JWT secret must be set locally in `backend/.env`; never commit that
  file or paste the secret into chat.
- The frontend uses Vite's development proxy for `/api`. A production
  deployment must route frontend API requests to the backend or configure an
  allowed backend origin.
- The migration has been applied to the current Neon database. A new database
  must apply the full migration history in order, starting with the Phase 3
  baseline.
- The automated backend tests exist in the working tree.
- Authentication changes are still uncommitted on `feature/authentication`.

## File-by-file continuation point

The public listing site, tenant/landlord registration, shared login, role-based
starter dashboards, authenticated profile routes, and admin-only landlord
grant are implemented. Remaining candidates include admin invitations and
two-step verification, tenant contact requests, landlord listing management,
a password setup/reset flow for legacy accounts, role revocation/audit
history, and token logout/revocation.
