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