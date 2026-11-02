# Phase 7: Reporting progress

## Scope

This document tracks the reporting portion of Phase 7, separately from listing
moderation. Tenants can report a public listing, a landlord through a public
listing, or a user account. A tenant can view their own reports and current
statuses. Administrators can review the report queue, assign an open report to
themselves, read its history, and resolve or dismiss it after it is under
review.

Reports are submitted with a reason and details. Reporting a user account
requires that account's user ID. Reporting a landlord requires a public
listing ID so the reported landlord is resolved from the listing.

## Workflow

| Current status | Action | New status |
|---|---|---|
| `open`, unassigned | An administrator assigns the report to themself. | `under_review` |
| `under_review` | An administrator resolves the report. | `resolved` |
| `under_review` | An administrator dismisses the report. | `dismissed` |

Submission, assignment, resolution, and dismissal are recorded in the
append-only `report_history` table. Resolving and dismissing support an
optional note. An administrator may resolve or dismiss any report that is
under review; the assigned administrator is not required to perform the final
action.

## API routes

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/reports` | Submit a report as a tenant. |
| `GET` | `/api/v1/users/me/reports` | List reports submitted by the signed-in tenant. |
| `GET` | `/api/v1/admin/reports` | List the admin queue; optional `status` filter. |
| `GET` | `/api/v1/admin/reports/{report_id}/history` | Read a report's audit history. |
| `POST` | `/api/v1/admin/reports/{report_id}/assign` | Assign an open report to the signed-in admin. |
| `POST` | `/api/v1/admin/reports/{report_id}/resolve` | Resolve a report under review. |
| `POST` | `/api/v1/admin/reports/{report_id}/dismiss` | Dismiss a report under review. |

## Frontend

- Tenant dashboard links to report submission and status.
- A signed-in tenant can start a listing report from a listing's detail page;
  the form is prefilled with that listing ID.
- The tenant report page also accepts landlord and user-account reports.
- The admin listing-moderation page links to the report queue.
- The report queue supports status filtering, self-assignment, history viewing,
  and resolution or dismissal.

## Database migration

Migration `20261030_05` extends the existing singular `report` table, allowing
reports to reference a listing, a user account, or both where applicable. It
adds report details and creates the append-only `report_history` table while
preserving existing report rows.

After approval, migration `20261030_05` was applied to the configured
database. The database is at revision `20261030_05`; the expected report and
history columns and target check constraint were verified. No report or
history records were inserted during migration.

## Verification

- The backend unittest suite passes, including reporting service and endpoint
  coverage.
- The frontend TypeScript check and production build pass.
- The combined migration graph has reporting at `20261030_05` and the
  renumbered Phase 6 contact-request migration at `20261030_06`. Offline SQL
  rendering must start from a known parent because earlier migrations contain
  database introspection that cannot execute in Alembic's offline mode.
- The applied schema was inspected, and both `report` and `report_history`
  contain one and three rows, respectively. Migration `20261030_06` did not
  modify either reporting table.

The interactive workflow has not yet been exercised in a browser using
authenticated tenant and admin accounts.
