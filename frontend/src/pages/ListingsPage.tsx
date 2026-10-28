import { useCallback, useEffect, useMemo, useState } from "react";

import ListingGrid from "../components/ListingGrid";
import SearchFilters, {
  type ListingFilters,
} from "../components/SearchFilters";
import type { Listing } from "../components/ListingCard";

type Area = {
  area_id: number;
  name: string;
};

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

const emptyFilters: ListingFilters = {
  location: "",
  roomType: "",
  minimumRent: "",
  maximumRent: "",
};

export default function ListingsPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [filters, setFilters] = useState<ListingFilters>(emptyFilters);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  const loadListings = useCallback(async (signal: AbortSignal) => {
    setIsLoading(true);
    setError(null);

    try {
      const [listingsResponse, areasResponse] = await Promise.all([
        fetch("/api/v1/listings", { signal }),
        fetch("/api/v1/areas", { signal }),
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

      setListings(listingsPayload);
      setAreas(areasPayload);
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
        locationQuery === "" ||
        listing.address.toLocaleLowerCase().includes(locationQuery) ||
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

      return (
        matchesLocation &&
        matchesRoomType &&
        matchesMinimumRent &&
        matchesMaximumRent
      );
    });
  }, [areas, filters, listings]);

  const hasActiveFilters = Object.values(filters).some(
    (value) => value.trim() !== "",
  );

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
        <header style={{ marginBottom: 32 }}>
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
            Browse rooms currently available for rent.
          </p>
        </header>

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
          <SearchFilters filters={filters} onChange={setFilters} />
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
          filteredListings.length === 0 && (
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

        {!isLoading && !error && filteredListings.length > 0 && (
          <>
            <p aria-live="polite" style={{ color: "#596579" }}>
              Showing {filteredListings.length} of {listings.length} rooms
            </p>
            <ListingGrid listings={filteredListings} />
          </>
        )}
      </section>
    </main>
  );
}
