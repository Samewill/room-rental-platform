import { useEffect, useState } from "react";

import type { Listing } from "../components/ListingCard";

type ListingDetailsPageProps = {
  listingId: number;
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

function formatCurrency(value: string | number): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return "Amount unavailable";
  }

  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(date);
}

export default function ListingDetailsPage({
  listingId,
}: ListingDetailsPageProps) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function loadListing(): Promise<void> {
      try {
        const response = await fetch(`/api/v1/listings/${listingId}`, {
          signal: controller.signal,
        });
        if (response.status === 404) {
          setError("This room could not be found or is no longer available.");
          return;
        }
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const payload: unknown = await response.json();
        if (!isListing(payload)) {
          throw new Error("The listing response has an unexpected format.");
        }

        setListing(payload);
      } catch (requestError) {
        if (controller.signal.aborted) {
          return;
        }

        setError(
          requestError instanceof Error
            ? requestError.message
            : "Listing details could not be loaded.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadListing();
    return () => controller.abort();
  }, [listingId]);

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
      <article
        style={{
          background: "white",
          border: "1px solid #e3e7ed",
          borderRadius: 14,
          margin: "0 auto",
          maxWidth: 800,
          padding: 28,
        }}
      >
        <a
          href="/"
          style={{ color: "#244b35", fontWeight: 600, textDecoration: "none" }}
        >
          ← Back to rooms
        </a>

        {isLoading && <p role="status">Loading room details…</p>}

        {!isLoading && error && (
          <p role="alert" style={{ color: "#9b2820", marginTop: 24 }}>
            {error}
          </p>
        )}

        {!isLoading && !error && listing && (
          <>
            {listing.photos.length > 0 ? (
              <div
                aria-label="Room photos"
                style={{
                  display: "grid",
                  gap: 12,
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  marginTop: 24,
                }}
              >
                {listing.photos.map((photo, index) => (
                  <img
                    key={photo.photo_id}
                    alt={`Room interior ${index + 1} for ${listing.title}`}
                    src={photo.url}
                    style={{
                      borderRadius: 10,
                      height: 260,
                      objectFit: "cover",
                      width: "100%",
                    }}
                  />
                ))}
              </div>
            ) : (
              <div
                aria-hidden="true"
                style={{
                  alignItems: "center",
                  background: "linear-gradient(135deg, #dce9df, #f1e8d8)",
                  borderRadius: 10,
                  color: "#355b43",
                  display: "flex",
                  fontWeight: 600,
                  height: 260,
                  justifyContent: "center",
                  marginTop: 24,
                }}
              >
                Room photos are not available yet
              </div>
            )}
            <p style={{ color: "#476b55", margin: "24px 0 6px" }}>
              {listing.room_type}
            </p>
            <h1 style={{ fontSize: 32, margin: "0 0 16px" }}>
              {listing.title}
            </h1>
            <p style={{ color: "#596579", lineHeight: 1.7 }}>
              {listing.description}
            </p>
            <dl
              style={{
                display: "grid",
                gap: 16,
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                marginTop: 28,
              }}
            >
              <div>
                <dt style={{ color: "#596579" }}>Monthly rent</dt>
                <dd style={{ fontWeight: 700, margin: "4px 0 0" }}>
                  {formatCurrency(listing.monthly_rent)}
                </dd>
              </div>
              <div>
                <dt style={{ color: "#596579" }}>Deposit</dt>
                <dd style={{ fontWeight: 700, margin: "4px 0 0" }}>
                  {formatCurrency(listing.deposit_amount)}
                </dd>
              </div>
              <div>
                <dt style={{ color: "#596579" }}>Address</dt>
                <dd style={{ margin: "4px 0 0" }}>{listing.address}</dd>
              </div>
              <div>
                <dt style={{ color: "#596579" }}>Area ID</dt>
                <dd style={{ margin: "4px 0 0" }}>{listing.area_id}</dd>
              </div>
              <div>
                <dt style={{ color: "#596579" }}>Available from</dt>
                <dd style={{ margin: "4px 0 0" }}>
                  {formatDate(listing.date_available)}
                </dd>
              </div>
            </dl>
          </>
        )}
      </article>
    </main>
  );
}
