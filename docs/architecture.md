# Application architecture

## Listing location and map privacy

Listings continue to reference the shared `areas` table through `area_id`.
Landlords can enter any area or suburb name; the authenticated
`POST /api/v1/areas/resolve` endpoint reuses or creates that area instead of
restricting it to a fixed catalog.

`frontend/src/components/GoogleAddressSearch.tsx` uses the Google Places API
(New) autocomplete widget, restricted to South African results. Selecting a
result updates the landlord map preview and saves its Place ID; the landlord's
own entered address text remains the listing address. Google-returned
coordinates and formatted addresses are not persisted. `RoomMap` is
the reusable, zoomable Google map used for landlord preview and public Room
Details. Exact manually stored coordinates remain landlord-only; public
responses expose only coordinates rounded to two decimal places. For listings
with a Place ID, `GET /api/v1/listings/{listing_id}/map-location` resolves
coordinates on demand and returns an approximate point with `Cache-Control:
no-store`. Do not expose Place IDs or exact coordinates in public listing,
search, assistant, or unauthenticated responses.

## Future rental interest

Future-interest opportunities are attached to a landlord's active, approved
listing. A tenant registration records the expected move-in date, rental
duration, budget, room-type preference, and required amenities. This is free
and is not a reservation or accommodation guarantee; landlords retain tenant
selection control.

Registrations use a capped active queue and a separate waitlist. A database
row lock on the opportunity serializes registration and promotion, while a
partial unique index prevents duplicate active registrations by the same
tenant. Compatibility ordering is deterministic and exposes its reasons to
landlords; registration time is an oldest-first tie-breaker. Status changes
are recorded in an append-only history table.

Waiting-list admission is controlled per opportunity and defaults to disabled.
When active capacity is full, the API creates no registration until the tenant
explicitly confirms joining an enabled waitlist; when waitlisting is disabled,
the request is rejected. Existing, consented waitlist entries remain eligible
for priority promotion when a place opens. The API also returns a derived
availability state (`open`, `full`, or `closed`) based on eligibility,
opportunity dates, and active capacity. Landlords may optionally configure an
expected rental duration; it is not inferred when unspecified.

Registration expiry defaults to 90 days and is configurable with
`RENTAL_INTEREST_EXPIRY_DAYS`. Spam protection defaults to 20 submissions per
tenant per 24 hours and is configurable with
`RENTAL_INTEREST_MAX_SUBMISSIONS_PER_DAY`. Schedule
`python -m app.jobs.expire_rental_interests` from the backend directory (for
example, every 15 minutes) to expire registrations, promote eligible
waitlisted tenants, and close opportunities whose listings are no longer
active and approved. Do not treat either active or waitlisted interest as a
booking.

The repository does not configure a production scheduler. Deployment must
schedule this command externally from the backend working directory at least
every 15 minutes, with the same database and notification-provider
configuration as the application. The job logs a completion summary; an
uncaught failure exits unsuccessfully and writes its traceback to stderr.
Configure the scheduler to retain stdout/stderr, alert on a non-zero exit or
missed run, and monitor the recorded expiry counts. The application does not
retry failed maintenance runs or provide scheduler alerting itself.

Registration, landlord status changes, waitlist promotion, expiry, closure, and
tenant withdrawal create deduplicated in-app notifications. WhatsApp delivery
is queued only for a verified contact that was opted in when the event occurred
and remains opted in when the message is sent. Notification text redacts phone
numbers; landlord notifications do not include tenant contact details. The
maintenance command also drains the WhatsApp outbox using the existing
transactional-message template. Provider failures are recorded and are not
retried automatically; interrupted sends are marked failed after 30 minutes to
avoid duplicate delivery.

Configure `VITE_GOOGLE_MAPS_API_KEY` and, for production,
`VITE_GOOGLE_MAP_ID` in the frontend build environment. The browser key is
public; restrict it by application referrer and enabled Maps JavaScript API and
Places API (New). Configure `GOOGLE_MAPS_SERVER_API_KEY` on the backend,
restricted to Places API (New) and server egress. Enable billing, quotas, and
budget alerts. Development uses Google's `DEMO_MAP_ID` when no map ID is set.
Address searches are sent to Google Maps Platform; the UI links to Google's
privacy policy. Review Google Maps Platform terms and data policies for the
deployment and retention of returned address data.