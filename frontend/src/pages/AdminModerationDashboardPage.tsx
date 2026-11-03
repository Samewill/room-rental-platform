import { useEffect, useState } from "react";

import {
  approveListing,
  getListingModerationHistory,
  getPendingListings,
  getPublishedListings,
  hideListing,
  rejectListing,
  type UserProfile,
} from "../api";
import type {
  Listing,
  ListingModerationRecord,
} from "../types/listing";
import "./AdminModerationDashboardPage.css";

type AdminModerationDashboardPageProps = {
  accessToken: string;
  profile: UserProfile;
  onOpenReports: () => void;
  onSignOut: () => void;
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The request could not be completed. Please try again.";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function AdminModerationDashboardPage({
  accessToken,
  profile,
  onOpenReports,
  onSignOut,
}: AdminModerationDashboardPageProps) {
  const [pendingListings, setPendingListings] = useState<Listing[]>([]);
  const [publishedListings, setPublishedListings] = useState<Listing[]>([]);
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [histories, setHistories] = useState<
    Record<number, ListingModerationRecord[]>
  >({});
  const [expandedHistory, setExpandedHistory] = useState<number[]>([]);
  const [busyListingId, setBusyListingId] = useState<number | null>(null);
  const [historyLoadingId, setHistoryLoadingId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function refreshListings(): Promise<void> {
    const [pending, published] = await Promise.all([
      getPendingListings(accessToken),
      getPublishedListings(accessToken),
    ]);
    setPendingListings(pending);
    setPublishedListings(published);
  }

  useEffect(() => {
    let active = true;

    async function loadDashboard(): Promise<void> {
      try {
        const [pending, published] = await Promise.all([
          getPendingListings(accessToken),
          getPublishedListings(accessToken),
        ]);
        if (active) {
          setPendingListings(pending);
          setPublishedListings(published);
        }
      } catch (error: unknown) {
        if (active) {
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [accessToken]);

  async function runAction(
    listingId: number,
    action: () => Promise<Listing>,
    successMessage: string,
  ): Promise<void> {
    setBusyListingId(listingId);
    setErrorMessage(null);
    setNotice(null);
    try {
      await action();
      setNotice(successMessage);
      setHistories((current) => {
        const next = { ...current };
        delete next[listingId];
        return next;
      });
      setExpandedHistory((current) =>
        current.filter((id) => id !== listingId),
      );
      await refreshListings();
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusyListingId(null);
    }
  }

  async function toggleHistory(listingId: number): Promise<void> {
    setErrorMessage(null);
    if (expandedHistory.includes(listingId)) {
      setExpandedHistory((current) =>
        current.filter((id) => id !== listingId),
      );
      return;
    }

    setExpandedHistory((current) => [...current, listingId]);
    if (histories[listingId] !== undefined) {
      return;
    }

    setHistoryLoadingId(listingId);
    try {
      const history = await getListingModerationHistory(
        accessToken,
        listingId,
      );
      setHistories((current) => ({ ...current, [listingId]: history }));
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
      setExpandedHistory((current) =>
        current.filter((id) => id !== listingId),
      );
    } finally {
      setHistoryLoadingId(null);
    }
  }

  function renderListing(listing: Listing, isPublished: boolean) {
    const reason = reasons[listing.listing_id] ?? "";
    const historyIsExpanded = expandedHistory.includes(listing.listing_id);
    const history = histories[listing.listing_id];

    return (
      <li className="moderation-listing" key={listing.listing_id}>
        <div className="moderation-listing-main">
          <div className="moderation-listing-copy">
            <p className="moderation-listing-type">
              {listing.room_type.replaceAll("_", " ")}
            </p>
            <h3>{listing.title}</h3>
            <p>{listing.description}</p>
            <p>
              R {Number(listing.monthly_rent).toLocaleString("en-ZA")} / month
              {" · "}
              {listing.address}
            </p>
            <p>Available {listing.date_available}</p>
          </div>
          {listing.photos.length > 0 && (
            <div className="moderation-photo-list">
              {listing.photos.map((photo) => (
                <img
                  alt={`Room photo for ${listing.title}`}
                  key={photo.photo_id}
                  src={photo.url}
                />
              ))}
            </div>
          )}
        </div>

        <label className="moderation-reason">
          {isPublished
            ? "Reason for hiding this listing"
            : "Decision reason (required to reject)"}
          <textarea
            onChange={(event) =>
              setReasons((current) => ({
                ...current,
                [listing.listing_id]: event.target.value,
              }))
            }
            rows={2}
            value={reason}
          />
        </label>

        <div className="moderation-actions">
          {!isPublished && (
            <>
              <button
                className="primary-button"
                disabled={busyListingId === listing.listing_id}
                onClick={() =>
                  void runAction(
                    listing.listing_id,
                    () =>
                      approveListing(
                        accessToken,
                        listing.listing_id,
                        reason.trim() || undefined,
                      ),
                    "The listing was approved.",
                  )
                }
                type="button"
              >
                Approve
              </button>
              <button
                className="secondary-button danger-button"
                disabled={
                  busyListingId === listing.listing_id || !reason.trim()
                }
                onClick={() =>
                  void runAction(
                    listing.listing_id,
                    () =>
                      rejectListing(
                        accessToken,
                        listing.listing_id,
                        reason,
                      ),
                    "The listing was returned to the landlord for changes.",
                  )
                }
                type="button"
              >
                Reject
              </button>
            </>
          )}
          {isPublished && (
            <button
              className="secondary-button danger-button"
              disabled={
                busyListingId === listing.listing_id || !reason.trim()
              }
              onClick={() =>
                void runAction(
                  listing.listing_id,
                  () =>
                    hideListing(accessToken, listing.listing_id, reason),
                  "The published listing was hidden.",
                )
              }
              type="button"
            >
              Hide listing
            </button>
          )}
          <button
            className="secondary-button"
            disabled={historyLoadingId === listing.listing_id}
            onClick={() => void toggleHistory(listing.listing_id)}
            type="button"
          >
            {historyLoadingId === listing.listing_id
              ? "Loading history..."
              : historyIsExpanded
                ? "Hide history"
                : "View history"}
          </button>
        </div>

        {historyIsExpanded && (
          <div className="moderation-history">
            <h4>Moderation history</h4>
            {history?.length === 0 && <p>No moderation decisions yet.</p>}
            {history !== undefined && history.length > 0 && (
              <ol>
                {history.map((item) => (
                  <li key={item.moderation_id}>
                    <strong>{item.decision}</strong>
                    {" · "}
                    {formatDate(item.decided_at)}
                    {" · Admin #"}
                    {item.admin_id}
                    {item.reason && <p>{item.reason}</p>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </li>
    );
  }

  return (
    <main className="page-shell admin-moderation-page">
      <section className="admin-moderation-shell">
        <header className="admin-moderation-header">
          <div>
            <p className="eyebrow">Room Rentals · Administration</p>
            <h1>Listing moderation</h1>
            <p className="intro">Welcome, {profile.full_name}.</p>
          </div>
          <div className="moderation-actions">
            <button
              className="secondary-button"
              onClick={onOpenReports}
              type="button"
            >
              Open report queue
            </button>
            <button
              className="secondary-button"
              onClick={onSignOut}
              type="button"
            >
              Sign out
            </button>
          </div>
        </header>

        <p className="admin-moderation-note">
          Approving publishes a listing when it is available. Rejection returns
          it to the landlord as a draft. Hiding removes a published listing
          from public search.
        </p>

        {errorMessage !== null && (
          <p className="message message-error" role="alert">
            {errorMessage}
          </p>
        )}
        {notice !== null && (
          <p className="message message-success" role="status">
            {notice}
          </p>
        )}

        <section
          className="admin-moderation-panel"
          aria-labelledby="pending-listings-heading"
        >
          <h2 id="pending-listings-heading">Pending review</h2>
          {isLoading && <p role="status">Loading pending listings...</p>}
          {!isLoading && pendingListings.length === 0 && (
            <p>No listings are waiting for review.</p>
          )}
          <ul className="moderation-list">
            {pendingListings.map((listing) => renderListing(listing, false))}
          </ul>
        </section>

        <section
          className="admin-moderation-panel"
          aria-labelledby="published-listings-heading"
        >
          <h2 id="published-listings-heading">Published listings</h2>
          {!isLoading && publishedListings.length === 0 && (
            <p>No published listings are available to hide.</p>
          )}
          <ul className="moderation-list">
            {publishedListings.map((listing) => renderListing(listing, true))}
          </ul>
        </section>

        <footer className="admin-moderation-footer">
          <a href="/">Browse public rooms</a>
        </footer>
      </section>
    </main>
  );
}
