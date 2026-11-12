# Database design notes

## Listing locations

The existing `listings.area_id` foreign key remains the normalized area
reference. Area names are not duplicated on the listing row: landlords can
enter an arbitrary area or suburb name, and the authenticated area-resolve API
reuses or creates the corresponding `areas` row.

Migration `20261109_12` adds nullable `latitude` and `longitude` double
precision columns to `listings`. Both coordinates must be null or both present,
latitude must be between -90 and 90, and longitude must be between -180 and
180. Existing rows remain valid with no coordinates. Landlords can search any
South African address or area with Google Places API (New), select a result,
and save their entered address text and the selected Place ID. Google-returned
formatted addresses and coordinates are not persisted. Place IDs are stored in
the separate `google_place_id` column; coordinates are resolved on demand.

Migration `20261110_13` added the nullable `google_place_id` column and a
constraint preventing it from coexisting with stored coordinates. Listing
updates clear coordinates when a Google Place ID is selected, or clear the
Place ID when manual coordinates are supplied.

Exact coordinates are landlord-only data. Public API responses expose
coordinates rounded to two decimal places, not the stored values. The public
Room Details map labels its marker as approximate. Place IDs are not included
in public listing responses. Do not return exact coordinates in public API
responses without an explicit, reviewed privacy policy.

## Future rental interest

Migration `20261111_18` adds:

- `rental_interest_opportunities`, linked to an existing listing and storing
  its expected availability window, optional room count, active-registration
  limit, and open/closed state.
- `rental_interests`, storing a tenant's expected move-in date, rental
  duration, monthly budget, room-type preference, required amenities, current
  status, registration timestamp, and expiry.
- `rental_interest_amenities`, linking registrations to the existing amenity
  catalog.
- `rental_interest_status_history`, recording status transitions and their
  actor (null for scheduled system actions).

Partial unique indexes prevent more than one open opportunity per listing and
more than one active/waitlisted/contacted/invited registration per tenant and
opportunity. Withdrawn, expired, converted, and closed registrations remain
historical rows and do not block a later registration. A registration is not
a reservation, and no payment data is stored.

Migration `20261111_19` adds `rental_interest_notifications`, which stores
recipient-scoped in-app updates and the deduplicated WhatsApp delivery outbox.
An event key derived from the status-history row prevents duplicate
notifications. Delivery state, provider IDs, and errors are recorded without
storing an additional phone number or exposing one in the notification payload.