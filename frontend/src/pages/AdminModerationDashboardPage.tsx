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
  const [listingView, setListingView] = useState<"pending" | "published">(
    "pending",
  );
  const [searchQuery, setSearchQuery] = useState("");
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
  const currentListings =
    listingView === "pending" ? pendingListings : publishedListings;
  const normalizedSearch = searchQuery.trim().toLocaleLowerCase();
  const filteredListings = currentListings.filter((listing) =>
    [
      listing.title,
      listing.address,
      listing.room_type.replaceAll("_", " "),
      String(listing.listing_id),
    ].some((value) => value.toLocaleLowerCase().includes(normalizedSearch)),
  );

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
          {listing.photos[0] !== undefined ? (
            <img
              alt={`Room photo for ${listing.title}`}
              className="moderation-listing-cover"
              src={listing.photos[0].url}
            />
          ) : (
            <div className="moderation-listing-cover moderation-listing-no-photo">
              <span aria-hidden="true">⌂</span>
              <small>No photo</small>
            </div>
          )}
          <div className="moderation-listing-copy">
            <div className="moderation-listing-heading">
              <div>
                <p className="moderation-listing-type">
                  {listing.room_type.replaceAll("_", " ")}
                </p>
                <h3>{listing.title}</h3>
              </div>
              <span
                className={`moderation-status ${isPublished ? "is-published" : "is-pending"}`}
              >
                {isPublished ? "Published" : "Needs review"}
              </span>
            </div>
            <p className="moderation-listing-description">
              {listing.description}
            </p>
            <p className="moderation-listing-address">{listing.address}</p>
            <div className="moderation-listing-meta">
              <strong>
                R {Number(listing.monthly_rent).toLocaleString("en-ZA")}
                <span> / month</span>
              </strong>
              <span>Available {listing.date_available}</span>
              <span>Listing #{listing.listing_id}</span>
            </div>
          </div>
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
    <main className="admin-dashboard">
      <aside className="admin-sidebar" aria-label="Admin navigation">
        <a className="admin-brand" href="/" aria-label="Room Rentals home">
          <span aria-hidden="true">R</span>
          <strong>Room Rentals</strong>
        </a>
        <p className="admin-nav-label">WORKSPACE</p>
        <nav className="admin-sidebar-nav">
          <button className="admin-nav-item active" type="button">
            <span aria-hidden="true">▦</span>
            Listings
          </button>
          <button
            className="admin-nav-item"
            onClick={onOpenReports}
            type="button"
          >
            <span aria-hidden="true">⚑</span>
            Reports
          </button>
          <a className="admin-nav-item" href="/">
            <span aria-hidden="true">↗</span>
            Browse rooms
          </a>
        </nav>
        <div className="admin-sidebar-account">
          <span className="admin-avatar" aria-hidden="true">
            {profile.full_name
              .split(/\s+/)
              .slice(0, 2)
              .map((part) => part[0] ?? "")
              .join("")
              .toUpperCase()}
          </span>
          <span className="admin-account-name">{profile.full_name}</span>
        </div>
      </aside>

      <div className="admin-dashboard-main">
        <header className="admin-topbar">
          <div className="admin-page-heading">
            <p className="admin-eyebrow">ADMIN WORKSPACE</p>
            <h1>Listings</h1>
            <p>Review submissions and manage published rooms.</p>
          </div>
          <div className="admin-topbar-actions">
            <label className="admin-search">
              <span aria-hidden="true">⌕</span>
              <span className="visually-hidden">Search listings</span>
              <input
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search by title, address or ID"
                type="search"
                value={searchQuery}
              />
            </label>
            <button
              className="primary-button admin-reports-button"
              onClick={onOpenReports}
              type="button"
            >
              Open reports
            </button>
            <button
              className="admin-topbar-signout"
              onClick={onSignOut}
              type="button"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="admin-dashboard-content">
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

          <section className="admin-stats" aria-label="Listing overview">
            <article className="admin-stat-card pending-stat">
              <span className="admin-stat-mark" aria-hidden="true">
                !
              </span>
              <div>
                <p>Needs review</p>
                <strong>{pendingListings.length}</strong>
                <small>Listings awaiting a decision</small>
              </div>
            </article>
            <article className="admin-stat-card published-stat">
              <span className="admin-stat-mark" aria-hidden="true">
                ✓
              </span>
              <div>
                <p>Published</p>
                <strong>{publishedListings.length}</strong>
                <small>Listings currently published</small>
              </div>
            </article>
            <article className="admin-stat-card total-stat">
              <span className="admin-stat-mark" aria-hidden="true">
                ▦
              </span>
              <div>
                <p>Listings in view</p>
                <strong>
                  {pendingListings.length + publishedListings.length}
                </strong>
                <small>Pending and published listings</small>
              </div>
            </article>
          </section>

          <section
            className="admin-moderation-panel"
            aria-labelledby="listings-heading"
          >
            <div className="admin-listings-toolbar">
              <div>
                <p className="admin-section-eyebrow">PROPERTY MANAGEMENT</p>
                <h2 id="listings-heading">
                  {listingView === "pending"
                    ? "Review queue"
                    : "Published listings"}
                </h2>
              </div>
              <div
                aria-label="Filter listings by status"
                className="admin-listing-tabs"
                role="group"
              >
                <button
                  aria-pressed={listingView === "pending"}
                  className={listingView === "pending" ? "active" : ""}
                  onClick={() => setListingView("pending")}
                  type="button"
                >
                  Needs review <span>{pendingListings.length}</span>
                </button>
                <button
                  aria-pressed={listingView === "published"}
                  className={listingView === "published" ? "active" : ""}
                  onClick={() => setListingView("published")}
                  type="button"
                >
                  Published <span>{publishedListings.length}</span>
                </button>
              </div>
            </div>

            {isLoading && (
              <p className="admin-listings-state" role="status">
                Loading listings...
              </p>
            )}
            {!isLoading && filteredListings.length === 0 && (
              <p className="admin-listings-state">
                {normalizedSearch.length > 0
                  ? "No listings match your search."
                  : listingView === "pending"
                    ? "No listings are waiting for review."
                    : "No published listings are available to hide."}
              </p>
            )}
            <ul className="moderation-list">
              {filteredListings.map((listing) =>
                renderListing(listing, listingView === "published"),
              )}
            </ul>
          </section>
          <p className="admin-moderation-note">
            Approving publishes a listing when it is available. Rejection
            returns it to the landlord as a draft. Hiding removes a published
            listing from public search.
          </p>
        </div>
      </div>
    </main>
  );
}
