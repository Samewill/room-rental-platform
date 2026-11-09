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

Configure `VITE_GOOGLE_MAPS_API_KEY` and, for production,
`VITE_GOOGLE_MAP_ID` in the frontend build environment. The browser key is
public; restrict it by application referrer and enabled Maps JavaScript API and
Places API (New). Configure `GOOGLE_MAPS_SERVER_API_KEY` on the backend,
restricted to Places API (New) and server egress. Enable billing, quotas, and
budget alerts. Development uses Google's `DEMO_MAP_ID` when no map ID is set.
Address searches are sent to Google Maps Platform; the UI links to Google's
privacy policy. Review Google Maps Platform terms and data policies for the
deployment and retention of returned address data.