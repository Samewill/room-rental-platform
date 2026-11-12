import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  buildApiUrl,
  createSavedSearch,
  getPublicListingMapLocation,
  getAmenities,
  type SavedSearchCreateRequest,
  type SavedSearchRoomType,
} from "../api";
import type { UserProfile } from "../api";
import AppLink from "../components/AppLink";
import type { GoogleAddressSelection } from "../components/GoogleAddressSearch";
import ListingResultsMap, {
  type ListingMapPoint,
} from "../components/ListingResultsMap";
import ListingGrid from "../components/ListingGrid";
import SearchFilters, {
  type ListingFilters,
} from "../components/SearchFilters";
import type { Listing } from "../components/ListingCard";
import type { Amenity, Area } from "../types/listing";

type MapCoordinates = {
  latitude: number;
  longitude: number;
};

function getAvailabilityDateFromSearch(search: string): string {
  const value = new URLSearchParams(search).get("availableBy") ?? "";
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : "";
}

function isListing(value: unknown): value is Listing {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const listing = value as Record<string, unknown>;

  return (
    typeof listing.listing_id === "number" &&
    typeof listing.area_id === "number" &&
    typeof listing.title === "string" &&
    typeof listing.description === "string" &&
    typeof listing.room_type === "string" &&
    (typeof listing.monthly_rent === "string" ||
      typeof listing.monthly_rent === "number") &&
    (typeof listing.deposit_amount === "string" ||
      typeof listing.deposit_amount === "number") &&
    typeof listing.address === "string" &&
    typeof listing.date_available === "string" &&
    typeof listing.status === "string" &&
    typeof listing.created_at === "string" &&
    Array.isArray(listing.amenities) &&
    listing.amenities.every((amenity) => typeof amenity === "string") &&
    Array.isArray(listing.photos) &&
    listing.photos.every(
      (photo) =>
        typeof photo === "object" &&
        photo !== null &&
        typeof photo.photo_id === "number" &&
        typeof photo.url === "string" &&
        typeof photo.uploaded_at === "string",
    )
  );
}

function isArea(value: unknown): value is Area {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const area = value as Record<string, unknown>;
  return typeof area.area_id === "number" && typeof area.name === "string";
}

function isAmenity(value: unknown): value is Amenity {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const amenity = value as Record<string, unknown>;
  return (
    typeof amenity.amenity_id === "number" &&
    typeof amenity.name === "string"
  );
}

function getFiltersFromSearch(search: string): ListingFilters {
  const params = new URLSearchParams(search);
  const roomType = getSavedSearchRoomType(params.get("roomType") ?? "");
  const minimumRent = params.get("minimumRent") ?? "";
  const maximumRent = params.get("maximumRent") ?? "";

  return {
    location: params.get("location") ?? "",
    roomType: roomType ?? "",
    minimumRent:
      minimumRent !== "" && Number.isFinite(Number(minimumRent))
        ? minimumRent
        : "",
    maximumRent:
      maximumRent !== "" && Number.isFinite(Number(maximumRent))
        ? maximumRent
        : "",
    amenities: params.getAll("amenity"),
  };
}

type ListingsPageProps = {
  accessToken: string | null;
  isAuthReady: boolean;
  onNavigate: (path: string) => void;
  onRetrySessionRestore: () => void;
  onSignOut: () => void;
  profile: UserProfile | null;
  sessionNotice: string | null;
  sessionRestoreError: string | null;
};

function getDashboardPath(profile: UserProfile): string {
  if (profile.roles.includes("admin")) {
    return "/admin";
  }
  if (profile.roles.includes("landlord")) {
    return "/landlord";
  }
  return "/tenant";
}

function getSavedSearchRoomType(value: string): SavedSearchRoomType | null {
  switch (value) {
    case "single_room":
    case "shared_room":
    case "bachelor_flat":
    case "self_contained":
      return value;
    default:
      return null;
  }
}

export default function ListingsPage({
  accessToken,
  isAuthReady,
  onNavigate,
  onRetrySessionRestore,
  onSignOut,
  profile,
  sessionNotice,
  sessionRestoreError,
}: ListingsPageProps) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [amenities, setAmenities] = useState<Amenity[]>([]);
  const [filters, setFilters] = useState<ListingFilters>(() =>
    getFiltersFromSearch(window.location.search),
  );
  const [availableBy, setAvailableBy] = useState(() =>
    getAvailabilityDateFromSearch(window.location.search),
  );
  const [searchCenter, setSearchCenter] =
    useState<GoogleAddressSelection | null>(null);
  const [radius, setRadius] = useState<5 | 10>(5);
  const [radiusMatchedListingIds, setRadiusMatchedListingIds] =
    useState<Set<number> | null>(null);
  const [isSearchingRadius, setIsSearchingRadius] = useState(false);
  const [radiusSearchRetryKey, setRadiusSearchRetryKey] = useState(0);
  const [radiusSearchError, setRadiusSearchError] = useState<string | null>(
    null,
  );
  const [listingMapLocations, setListingMapLocations] = useState<
    Map<number, MapCoordinates>
  >(() => new Map());
  const mapLocationAttemptedIds = useRef(new Set<number>());
  const [isLoadingMapLocations, setIsLoadingMapLocations] = useState(false);
  const [mapLocationError, setMapLocationError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [isSavingSearch, setIsSavingSearch] = useState(false);
  const [enableWhatsAppAlerts, setEnableWhatsAppAlerts] = useState(false);
  const [savedSearchError, setSavedSearchError] = useState<string | null>(null);
  const [savedSearchNotice, setSavedSearchNotice] = useState<string | null>(
    null,
  );

  const loadListings = useCallback(async (signal: AbortSignal) => {
    setIsLoading(true);
    setError(null);

    try {
      const [listingsResponse, areasResponse, amenitiesPayload] = await Promise.all([
        fetch(buildApiUrl("/api/v1/listings"), { signal }),
        fetch(buildApiUrl("/api/v1/areas"), { signal }),
        getAmenities(signal),
      ]);
      if (!listingsResponse.ok) {
        throw new Error(
          `Listings request failed with status ${listingsResponse.status}`,
        );
      }
      if (!areasResponse.ok) {
        throw new Error(
          `Areas request failed with status ${areasResponse.status}`,
        );
      }
      const [listingsPayload, areasPayload]: [unknown, unknown] =
        await Promise.all([listingsResponse.json(), areasResponse.json()]);
      if (!Array.isArray(listingsPayload) || !listingsPayload.every(isListing)) {
        throw new Error("The listings response has an unexpected format.");
      }
      if (!Array.isArray(areasPayload) || !areasPayload.every(isArea)) {
        throw new Error("The areas response has an unexpected format.");
      }
      if (
        !Array.isArray(amenitiesPayload) ||
        !amenitiesPayload.every(isAmenity)
      ) {
        throw new Error("The amenities response has an unexpected format.");
      }

      setListings(listingsPayload);
      setAreas(areasPayload);
      setAmenities(amenitiesPayload);
      setListingMapLocations(
        new Map(
          listingsPayload.flatMap((listing) =>
            typeof listing.approximate_latitude === "number" &&
            Number.isFinite(listing.approximate_latitude) &&
            typeof listing.approximate_longitude === "number" &&
            Number.isFinite(listing.approximate_longitude)
              ? [
                  [
                    listing.listing_id,
                    {
                      latitude: listing.approximate_latitude,
                      longitude: listing.approximate_longitude,
                    },
                  ] as const,
                ]
              : [],
          ),
        ),
      );
      setMapLocationError(null);
    } catch (requestError) {
      if (signal.aborted) {
        return;
      }

      setError(
        requestError instanceof Error
          ? requestError.message
          : "Listings could not be loaded.",
      );
    } finally {
      if (!signal.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadListings(controller.signal);

    return () => controller.abort();
  }, [loadListings, reloadKey]);

  useEffect(() => {
    if (searchCenter === null) {
      setRadiusMatchedListingIds(null);
      setIsSearchingRadius(false);
      setRadiusSearchError(null);
      return;
    }

    const controller = new AbortController();
    const params = new URLSearchParams({
      latitude: String(searchCenter.latitude),
      longitude: String(searchCenter.longitude),
      radius_km: String(radius),
    });
    setRadiusMatchedListingIds(null);
    setIsSearchingRadius(true);
    setRadiusSearchError(null);

    async function searchWithinRadius(): Promise<void> {
      try {
        const response = await fetch(
          buildApiUrl(`/api/v1/listings?${params.toString()}`),
          { signal: controller.signal },
        );
        if (!response.ok) {
          const errorPayload: unknown = await response.json();
          const detail =
            typeof errorPayload === "object" &&
            errorPayload !== null &&
            "detail" in errorPayload &&
            typeof errorPayload.detail === "string"
              ? errorPayload.detail
              : `Radius search failed with status ${response.status}.`;
          throw new Error(detail);
        }

        const payload: unknown = await response.json();
        if (!Array.isArray(payload) || !payload.every(isListing)) {
          throw new Error("The radius search response has an unexpected format.");
        }
        if (controller.signal.aborted) {
          return;
        }
        setRadiusMatchedListingIds(
          new Set(payload.map((listing) => listing.listing_id)),
        );
        setListingMapLocations((current) => {
          const next = new Map(current);
          for (const listing of payload) {
            if (
              typeof listing.approximate_latitude === "number" &&
              Number.isFinite(listing.approximate_latitude) &&
              typeof listing.approximate_longitude === "number" &&
              Number.isFinite(listing.approximate_longitude)
            ) {
              next.set(listing.listing_id, {
                latitude: listing.approximate_latitude,
                longitude: listing.approximate_longitude,
              });
            }
          }
          return next;
        });
      } catch (searchError: unknown) {
        if (!controller.signal.aborted) {
          setRadiusSearchError(
            searchError instanceof Error
              ? searchError.message
              : "Radius search could not be completed.",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsSearchingRadius(false);
        }
      }
    }

    void searchWithinRadius();
    return () => controller.abort();
  }, [radius, radiusSearchRetryKey, searchCenter]);

  useEffect(() => {
    mapLocationAttemptedIds.current.clear();
  }, [reloadKey]);

  const filteredListings = useMemo(() => {
    const locationQuery = filters.location.trim().toLocaleLowerCase();
    const roomTypeQuery = filters.roomType.trim().toLocaleLowerCase();
    const minimumRent =
      filters.minimumRent === "" ? null : Number(filters.minimumRent);
    const maximumRent =
      filters.maximumRent === "" ? null : Number(filters.maximumRent);
    const areaNames = new Map(
      areas.map((area) => [area.area_id, area.name.toLocaleLowerCase()]),
    );

    return listings.filter((listing) => {
      const rent = Number(listing.monthly_rent);
      if (!Number.isFinite(rent)) {
        return false;
      }

      const matchesLocation =
        searchCenter !== null ||
        locationQuery === "" ||
        listing.address.toLocaleLowerCase().includes(locationQuery) ||
        listing.area_name?.toLocaleLowerCase().includes(locationQuery) ===
          true ||
        areaNames
          .get(listing.area_id)
          ?.includes(locationQuery) === true;
      const matchesRoomType =
        roomTypeQuery === "" ||
        listing.room_type.toLocaleLowerCase() === roomTypeQuery;
      const matchesMinimumRent =
        minimumRent === null || rent >= minimumRent;
      const matchesMaximumRent =
        maximumRent === null || rent <= maximumRent;
      const matchesAmenities = filters.amenities.every((amenity) =>
        listing.amenities.includes(amenity),
      );
      const matchesRadius =
        searchCenter === null ||
        radiusMatchedListingIds?.has(listing.listing_id) === true;
      const matchesAvailability =
        availableBy === "" || listing.date_available <= availableBy;

      return (
        matchesLocation &&
        matchesRoomType &&
        matchesMinimumRent &&
        matchesMaximumRent &&
        matchesAmenities &&
        matchesRadius &&
        matchesAvailability
      );
    });
  }, [
    areas,
    availableBy,
    filters,
    listings,
    radiusMatchedListingIds,
    searchCenter,
  ]);

  useEffect(() => {
    const unresolvedListings = filteredListings.filter(
      (listing) =>
        listing.has_map_location === true &&
        !mapLocationAttemptedIds.current.has(listing.listing_id) &&
        !listingMapLocations.has(listing.listing_id) &&
        (typeof listing.approximate_latitude !== "number" ||
          !Number.isFinite(listing.approximate_latitude) ||
          typeof listing.approximate_longitude !== "number" ||
          !Number.isFinite(listing.approximate_longitude)),
    );
    if (unresolvedListings.length === 0) {
      setIsLoadingMapLocations(false);
      return;
    }

    const controller = new AbortController();
    for (const listing of unresolvedListings) {
      mapLocationAttemptedIds.current.add(listing.listing_id);
    }
    setIsLoadingMapLocations(true);
    setMapLocationError(null);

    let completed = false;
    async function loadMissingLocations(): Promise<void> {
      const results = await Promise.all(
        unresolvedListings.map(async (listing) => {
          try {
            const location = await getPublicListingMapLocation(
              listing.listing_id,
              controller.signal,
            );
            return {
              listingId: listing.listing_id,
              point: {
                latitude: location.approximate_latitude,
                longitude: location.approximate_longitude,
              },
              error: null,
            };
          } catch (locationError: unknown) {
            return {
              listingId: listing.listing_id,
              point: null,
              error:
                locationError instanceof Error
                  ? locationError.message
                  : "A listing map location could not be loaded.",
            };
          }
        }),
      );

      if (controller.signal.aborted) {
        return;
      }
      completed = true;

      const resolvedLocations = results.filter(
        (
          result,
        ): result is typeof result & {
          point: MapCoordinates;
        } => result.point !== null,
      );
      setListingMapLocations((current) => {
        const next = new Map(current);
        for (const result of resolvedLocations) {
          next.set(result.listingId, result.point);
        }
        return next;
      });

      const failures = results.filter((result) => result.error !== null);
      if (failures.length > 0) {
        setMapLocationError(
          `${failures.length} map location(s) could not be loaded. ${failures[0].error}`,
        );
      }
      setIsLoadingMapLocations(false);
    }

    void loadMissingLocations();
    return () => {
      controller.abort();
      if (!completed) {
        for (const listing of unresolvedListings) {
          mapLocationAttemptedIds.current.delete(listing.listing_id);
        }
      }
    };
  }, [filteredListings, listingMapLocations]);

  const hasActiveFilters =
    Object.values({
      location: filters.location,
      roomType: filters.roomType,
      minimumRent: filters.minimumRent,
      maximumRent: filters.maximumRent,
      availableBy,
    }).some((value) => value.trim() !== "") ||
    filters.amenities.length > 0 ||
    searchCenter !== null;
  const hasAdvancedSearchFilters =
    searchCenter !== null || availableBy !== "";

  function selectSearchLocation(selection: GoogleAddressSelection): void {
    setSearchCenter(selection);
    setFilters((current) => ({
      ...current,
      location: selection.displayAddress ?? selection.address,
    }));
  }

  const mapListings = useMemo(
    () =>
      filteredListings.flatMap((listing): ListingMapPoint[] => {
        const coordinates = listingMapLocations.get(listing.listing_id);
        return coordinates === undefined
          ? []
          : [
              {
                listingId: listing.listing_id,
                title: listing.title,
                monthlyRent: listing.monthly_rent,
                ...coordinates,
              },
            ];
      }),
    [filteredListings, listingMapLocations],
  );

  async function handleSaveSearch(): Promise<void> {
    if (accessToken === null || isSavingSearch) {
      return;
    }

    const payload: SavedSearchCreateRequest = {};
    const location = filters.location.trim();
    if (location !== "") {
      payload.location = location;
    }
    const roomType = getSavedSearchRoomType(filters.roomType);
    if (roomType !== null) {
      payload.room_type = roomType;
    }
    if (filters.minimumRent !== "") {
      payload.minimum_rent = Number(filters.minimumRent);
    }
    if (filters.maximumRent !== "") {
      payload.maximum_rent = Number(filters.maximumRent);
    }
    if (filters.amenities.length > 0) {
      payload.amenities = filters.amenities;
    }
    if (enableWhatsAppAlerts) {
      payload.alerts_enabled = true;
    }

    setIsSavingSearch(true);
    setSavedSearchError(null);
    setSavedSearchNotice(null);
    try {
      await createSavedSearch(accessToken, payload);
      setSavedSearchNotice("Search saved. You can view it from your dashboard.");
    } catch (saveError: unknown) {
      setSavedSearchError(
        saveError instanceof Error
          ? saveError.message
          : "Your search could not be saved.",
      );
    } finally {
      setIsSavingSearch(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f7f8fa",
        color: "#182230",
        fontFamily: "system-ui, sans-serif",
        padding: "48px 24px",
      }}
    >
      <section style={{ maxWidth: 1120, margin: "0 auto" }}>
        <header
          style={{
            alignItems: "flex-start",
            display: "flex",
            gap: 20,
            justifyContent: "space-between",
            marginBottom: 32,
          }}
        >
          <div>
            <p
              style={{
                color: "#476b55",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: "0.12em",
                margin: "0 0 8px",
                textTransform: "uppercase",
              }}
            >
              Room rentals
            </p>
            <h1 style={{ fontSize: 36, margin: "0 0 8px" }}>
              Find a room to call home
            </h1>
            <p style={{ color: "#596579", margin: 0 }}>
              Browse rooms available now or soon.
            </p>
          </div>
          <nav
            aria-label="Account"
            style={{
              alignItems: "center",
              display: "flex",
              flexWrap: "wrap",
              gap: 10,
              justifyContent: "flex-end",
            }}
          >
            {!isAuthReady ? (
              <span role="status">Checking your session…</span>
            ) : sessionRestoreError !== null ? (
              <>
                <span role="alert">Your saved session could not be verified.</span>
                <button
                  onClick={onRetrySessionRestore}
                  style={{
                    background: "white",
                    border: "1px solid #dfe3e7",
                    borderRadius: 8,
                    color: "#244b35",
                    cursor: "pointer",
                    font: "inherit",
                    fontWeight: 600,
                    padding: "10px 16px",
                  }}
                  type="button"
                >
                  Retry
                </button>
                <AppLink
                  href="/login"
                  onNavigate={onNavigate}
                  style={{ color: "#244b35", fontWeight: 600 }}
                >
                  Sign in
                </AppLink>
              </>
            ) : profile !== null ? (
              <>
                <AppLink
                  href={getDashboardPath(profile)}
                  onNavigate={onNavigate}
                  style={{
                    background: "#244b35",
                    border: "1px solid #244b35",
                    borderRadius: 8,
                    color: "white",
                    fontWeight: 600,
                    padding: "10px 16px",
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  Your dashboard
                </AppLink>
                <button
                  onClick={onSignOut}
                  style={{
                    background: "white",
                    border: "1px solid #dfe3e7",
                    borderRadius: 8,
                    color: "#244b35",
                    cursor: "pointer",
                    font: "inherit",
                    fontWeight: 600,
                    padding: "10px 16px",
                  }}
                  type="button"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <AppLink
                  href="/login"
                  onNavigate={onNavigate}
                  style={{
                    background: "white",
                    border: "1px solid #dfe3e7",
                    borderRadius: 8,
                    color: "#244b35",
                    fontWeight: 600,
                    padding: "10px 16px",
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  Sign in
                </AppLink>
                <AppLink
                  href="/register"
                  onNavigate={onNavigate}
                  style={{
                    background: "#244b35",
                    border: "1px solid #244b35",
                    borderRadius: 8,
                    color: "white",
                    fontWeight: 600,
                    padding: "10px 16px",
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                  }}
                >
                  Create account
                </AppLink>
              </>
            )}
          </nav>
        </header>

        {sessionRestoreError !== null && (
          <p
            role="alert"
            style={{
              background: "#fff1f0",
              border: "1px solid #e6aaa5",
              borderRadius: 12,
              color: "#7c241d",
              margin: "0 0 24px",
              padding: 16,
            }}
          >
            {sessionRestoreError}
          </p>
        )}
        {sessionNotice !== null && (
          <p role="status" style={{ margin: "0 0 24px" }}>
            {sessionNotice}
          </p>
        )}

        {isLoading && (
          <p role="status" style={{ color: "#596579" }}>
            Loading available rooms…
          </p>
        )}

        {!isLoading && error && (
          <div
            role="alert"
            style={{
              background: "#fff1f0",
              border: "1px solid #e6aaa5",
              borderRadius: 12,
              padding: 20,
            }}
          >
            <p style={{ margin: "0 0 12px" }}>
              We couldn’t load rooms right now. {error}
            </p>
            <button
              onClick={() => setReloadKey((key) => key + 1)}
              style={{
                background: "#244b35",
                border: 0,
                borderRadius: 8,
                color: "white",
                cursor: "pointer",
                font: "inherit",
                padding: "10px 16px",
              }}
              type="button"
            >
              Try again
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <>
            {radiusSearchError !== null && (
              <div role="alert">
                <p>{radiusSearchError}</p>
                <button
                  onClick={() =>
                    setRadiusSearchRetryKey((current) => current + 1)
                  }
                  type="button"
                >
                  Retry radius search
                </button>
              </div>
            )}
            <SearchFilters
              amenities={amenities}
              availableBy={availableBy}
              filters={filters}
              hasLocationSelection={searchCenter !== null}
              onAvailabilityChange={setAvailableBy}
              onChange={(nextFilters) => {
                if (nextFilters.location !== filters.location) {
                  setSearchCenter(null);
                }
                setFilters(nextFilters);
              }}
              onLocationSelected={selectSearchLocation}
              onRadiusChange={setRadius}
              radius={radius}
            />
            {profile?.roles.includes("tenant") &&
              accessToken !== null &&
              hasActiveFilters && (
                <div style={{ margin: "-8px 0 24px" }}>
                {!hasAdvancedSearchFilters && (
                  <label
                    style={{
                      alignItems: "flex-start",
                      display: "flex",
                      gap: 8,
                      marginBottom: 12,
                    }}
                  >
                    <input
                      checked={enableWhatsAppAlerts}
                      onChange={(event) =>
                        setEnableWhatsAppAlerts(
                          event.currentTarget.checked,
                        )
                      }
                      type="checkbox"
                    />
                    <span>
                      Send me a WhatsApp alert when a new approved room
                      matches this search. Verified WhatsApp is required;
                      you can turn alerts off from your dashboard.
                    </span>
                  </label>
                )}
                {hasAdvancedSearchFilters ? (
                    <p role="status">
                      Saved searches do not yet retain radius or availability
                      date filters. Clear those filters to save this search.
                    </p>
                  ) : (
                    <button
                      className="secondary-button"
                      disabled={isSavingSearch}
                      onClick={() => void handleSaveSearch()}
                      type="button"
                    >
                      {isSavingSearch ? "Saving search…" : "Save this search"}
                    </button>
                  )}
                  {savedSearchError !== null && (
                    <p role="alert">{savedSearchError}</p>
                  )}
                  {savedSearchNotice !== null && (
                    <p role="status">{savedSearchNotice}</p>
                  )}
                </div>
              )}
          </>
        )}

        {!isLoading && !error && listings.length === 0 && (
          <p
            style={{
              background: "white",
              border: "1px solid #e3e7ed",
              borderRadius: 12,
              color: "#596579",
              padding: 24,
            }}
          >
            No public rooms are available yet. Please check back soon.
          </p>
        )}

        {!isLoading &&
          !error &&
          listings.length > 0 &&
          filteredListings.length === 0 &&
          !(searchCenter !== null && isSearchingRadius) &&
          radiusSearchError === null && (
            <p
              role="status"
              style={{
                background: "white",
                border: "1px solid #e3e7ed",
                borderRadius: 12,
                color: "#596579",
                padding: 24,
              }}
            >
              {hasActiveFilters
                ? "No rooms match those filters. Try changing your search."
                : "No public rooms are available yet. Please check back soon."}
            </p>
          )}

        {!isLoading &&
          !error &&
          searchCenter !== null &&
          isSearchingRadius &&
          filteredListings.length === 0 && (
            <p role="status">
              Checking private listing locations within {radius} km…
            </p>
          )}

        {!isLoading && !error && filteredListings.length > 0 && (
          <>
            <p aria-live="polite" style={{ color: "#596579" }}>
              Showing {filteredListings.length} of {listings.length} rooms
            </p>
            <ListingResultsMap
              listings={mapListings}
              onNavigate={onNavigate}
              radius={radius}
              searchCenter={searchCenter}
            />
            {isLoadingMapLocations && (
              <p role="status">Loading approximate map locations…</p>
            )}
            {mapLocationError !== null && (
              <p role="alert">
                {mapLocationError} Those rooms may not appear on the map or
                within radius-filtered results.
              </p>
            )}
            <ListingGrid
              listings={filteredListings}
              onNavigate={onNavigate}
            />
          </>
        )}
      </section>
    </main>
  );
}
