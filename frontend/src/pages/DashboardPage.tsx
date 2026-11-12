import { useEffect, useState } from "react";

import {
  cancelContactRequest,
  createReview,
  deleteSavedListing,
  deleteSavedSearch,
  getMyContactRequests,
  getMyReviews,
  getMySavedListings,
  getMySavedSearches,
  updateSavedSearchAlerts,
  type ContactRequest,
  type Review,
  type SavedSearch,
  type UserProfile,
} from "../api";
import AppLink from "../components/AppLink";
import TenantFutureRentalOpportunitiesPanel from "../components/TenantFutureRentalOpportunitiesPanel";
import RentalInterestNotificationsPanel from "../components/RentalInterestNotificationsPanel";
import TenantRentalInterestsPanel from "../components/TenantRentalInterestsPanel";
import type { Listing } from "../types/listing";
import "./DashboardPage.css";

export type DashboardRole = "tenant" | "landlord" | "admin";

type DashboardPageProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
  profile: UserProfile;
  role: DashboardRole;
  onSignOut: () => void;
  onOpenReports: () => void;
};

const dashboardContent: Record<
  DashboardRole,
  { heading: string; description: string; nextStep: string }
> = {
  tenant: {
    heading: "Your tenant dashboard",
    description: "Find a room that feels like home.",
    nextStep: "Review your contact requests and their latest status below.",
  },
  landlord: {
    heading: "Your landlord dashboard",
    description: "Manage your room rentals from one place.",
    nextStep:
      "Your landlord account is ready. Listing management tools are not available yet.",
  },
  admin: {
    heading: "Admin workspace",
    description: "This area is for authorized platform administrators.",
    nextStep:
      "Admin invitations and two-step verification have not been implemented yet.",
  },
};

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

function getSavedSearchLabel(search: SavedSearch): string {
  const filters = [
    search.location,
    search.room_type?.replaceAll("_", " "),
    search.minimum_rent === null
      ? null
      : `min R ${Number(search.minimum_rent).toLocaleString("en-ZA")}`,
    search.maximum_rent === null
      ? null
      : `max R ${Number(search.maximum_rent).toLocaleString("en-ZA")}`,
    ...search.amenities,
  ].filter((value): value is string => value !== null);
  return filters.length === 0 ? "All available rooms" : filters.join(" · ");
}

function getSavedSearchPath(search: SavedSearch): string {
  const params = new URLSearchParams();
  if (search.location !== null) {
    params.set("location", search.location);
  }
  if (search.room_type !== null) {
    params.set("roomType", search.room_type);
  }
  if (search.minimum_rent !== null) {
    params.set("minimumRent", String(search.minimum_rent));
  }
  if (search.maximum_rent !== null) {
    params.set("maximumRent", String(search.maximum_rent));
  }
  search.amenities.forEach((amenity) => params.append("amenity", amenity));
  const query = params.toString();
  return query === "" ? "/" : `/?${query}`;
}

export default function DashboardPage({
  accessToken,
  onNavigate,
  profile,
  role,
  onSignOut,
  onOpenReports,
}: DashboardPageProps) {
  const content = dashboardContent[role];
  const [rentalInterestRefreshKey, setRentalInterestRefreshKey] = useState(0);
  const [contactRequests, setContactRequests] = useState<ContactRequest[]>([]);
  const [contactRequestsError, setContactRequestsError] = useState<
    string | null
  >(null);
  const [isLoadingContactRequests, setIsLoadingContactRequests] =
    useState(true);
  const [updatingRequestId, setUpdatingRequestId] = useState<number | null>(
    null,
  );
  const [contactRequestActionError, setContactRequestActionError] = useState<
    string | null
  >(null);
  const [contactRequestActionNotice, setContactRequestActionNotice] = useState<
    string | null
  >(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [isLoadingReviews, setIsLoadingReviews] = useState(true);
  const [reviewContactRequestId, setReviewContactRequestId] = useState<
    number | null
  >(null);
  const [reviewRating, setReviewRating] = useState("5");
  const [reviewComment, setReviewComment] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewActionError, setReviewActionError] = useState<string | null>(
    null,
  );
  const [reviewActionNotice, setReviewActionNotice] = useState<string | null>(
    null,
  );
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [savedSearchesError, setSavedSearchesError] = useState<string | null>(
    null,
  );
  const [isLoadingSavedSearches, setIsLoadingSavedSearches] = useState(true);
  const [deletingSavedSearchId, setDeletingSavedSearchId] = useState<
    number | null
  >(null);
  const [savedSearchActionError, setSavedSearchActionError] = useState<
    string | null
  >(null);
  const [savedListings, setSavedListings] = useState<Listing[]>([]);
  const [savedListingsError, setSavedListingsError] = useState<string | null>(
    null,
  );
  const [isLoadingSavedListings, setIsLoadingSavedListings] = useState(true);
  const [deletingSavedListingId, setDeletingSavedListingId] = useState<
    number | null
  >(null);
  const [updatingAlertSearchId, setUpdatingAlertSearchId] = useState<
    number | null
  >(null);

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let active = true;
    setContactRequests([]);
    setContactRequestsError(null);
    setIsLoadingContactRequests(true);

    async function loadContactRequests(): Promise<void> {
      try {
        const requests = await getMyContactRequests(accessToken);
        if (active) {
          setContactRequests(requests);
        }
      } catch (error: unknown) {
        if (active) {
          setContactRequestsError(
            error instanceof Error
              ? error.message
              : "Your contact requests could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingContactRequests(false);
        }
      }
    }

    void loadContactRequests();
    return () => {
      active = false;
    };
  }, [accessToken, role]);

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let active = true;
    setSavedListings([]);
    setSavedListingsError(null);
    setIsLoadingSavedListings(true);

    async function loadSavedListings(): Promise<void> {
      try {
        const listings = await getMySavedListings(accessToken);
        if (active) {
          setSavedListings(listings);
        }
      } catch (error: unknown) {
        if (active) {
          setSavedListingsError(
            error instanceof Error
              ? error.message
              : "Your saved listings could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingSavedListings(false);
        }
      }
    }

    void loadSavedListings();
    return () => {
      active = false;
    };
  }, [accessToken, role]);

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let active = true;
    setReviews([]);
    setReviewsError(null);
    setIsLoadingReviews(true);

    async function loadReviews(): Promise<void> {
      try {
        const tenantReviews = await getMyReviews(accessToken);
        if (active) {
          setReviews(tenantReviews);
        }
      } catch (error: unknown) {
        if (active) {
          setReviewsError(
            error instanceof Error
              ? error.message
              : "Your reviews could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingReviews(false);
        }
      }
    }

    void loadReviews();
    return () => {
      active = false;
    };
  }, [accessToken, role]);

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let active = true;
    setSavedSearches([]);
    setSavedSearchesError(null);
    setIsLoadingSavedSearches(true);

    async function loadSavedSearches(): Promise<void> {
      try {
        const searches = await getMySavedSearches(accessToken);
        if (active) {
          setSavedSearches(searches);
        }
      } catch (error: unknown) {
        if (active) {
          setSavedSearchesError(
            error instanceof Error
              ? error.message
              : "Your saved searches could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingSavedSearches(false);
        }
      }
    }

    void loadSavedSearches();
    return () => {
      active = false;
    };
  }, [accessToken, role]);

  async function handleCancelContactRequest(
    requestId: number,
  ): Promise<void> {
    setContactRequestActionError(null);
    setContactRequestActionNotice(null);
    setUpdatingRequestId(requestId);
    try {
      const updatedRequest = await cancelContactRequest(accessToken, requestId);
      setContactRequests((requests) =>
        requests.map((request) =>
          request.request_id === updatedRequest.request_id
            ? updatedRequest
            : request,
        ),
      );
      setContactRequestActionNotice("Contact request cancelled.");
    } catch (error: unknown) {
      setContactRequestActionError(
        error instanceof Error
          ? error.message
          : "The contact request could not be cancelled.",
      );
    } finally {
      setUpdatingRequestId(null);
    }
  }

  async function handleDeleteSavedSearch(savedSearchId: number): Promise<void> {
    setSavedSearchActionError(null);
    setDeletingSavedSearchId(savedSearchId);
    try {
      await deleteSavedSearch(accessToken, savedSearchId);
      setSavedSearches((searches) =>
        searches.filter((search) => search.saved_search_id !== savedSearchId),
      );
    } catch (error: unknown) {
      setSavedSearchActionError(
        error instanceof Error
          ? error.message
          : "The saved search could not be deleted.",
      );
    } finally {
      setDeletingSavedSearchId(null);
    }
  }

  async function handleDeleteSavedListing(listingId: number): Promise<void> {
    setSavedSearchActionError(null);
    setDeletingSavedListingId(listingId);
    try {
      await deleteSavedListing(accessToken, listingId);
      setSavedListings((listings) =>
        listings.filter((listing) => listing.listing_id !== listingId),
      );
    } catch (error: unknown) {
      setSavedSearchActionError(
        error instanceof Error
          ? error.message
          : "The saved listing could not be removed.",
      );
    } finally {
      setDeletingSavedListingId(null);
    }
  }

  async function handleUpdateSearchAlerts(
    searchId: number,
    alertsEnabled: boolean,
  ): Promise<void> {
    setSavedSearchActionError(null);
    setUpdatingAlertSearchId(searchId);
    try {
      const updatedSearch = await updateSavedSearchAlerts(
        accessToken,
        searchId,
        alertsEnabled,
      );
      setSavedSearches((searches) =>
        searches.map((search) =>
          search.saved_search_id === searchId ? updatedSearch : search,
        ),
      );
    } catch (error: unknown) {
      setSavedSearchActionError(
        error instanceof Error
          ? error.message
          : "The WhatsApp alert preference could not be updated.",
      );
    } finally {
      setUpdatingAlertSearchId(null);
    }
  }

  async function handleSubmitReview(
    contactRequestId: number,
  ): Promise<void> {
    setReviewActionError(null);
    setReviewActionNotice(null);
    setIsSubmittingReview(true);
    try {
      const comment = reviewComment.trim();
      const review = await createReview(accessToken, {
        contact_request_id: contactRequestId,
        rating: Number(reviewRating),
        ...(comment === "" ? {} : { comment }),
      });
      setReviews((currentReviews) => [review, ...currentReviews]);
      setReviewContactRequestId(null);
      setReviewRating("5");
      setReviewComment("");
      setReviewActionNotice("Your review was submitted.");
    } catch (error: unknown) {
      setReviewActionError(
        error instanceof Error
          ? error.message
          : "Your review could not be submitted.",
      );
    } finally {
      setIsSubmittingReview(false);
    }
  }

  if (role === "tenant") {
    const contactRequestsUnavailable =
      isLoadingContactRequests || contactRequestsError !== null;
    const pendingCount = contactRequests.filter(
      (request) => request.status === "pending",
    ).length;
    const respondedCount = contactRequests.filter(
      (request) =>
        request.status === "approved" || request.status === "rejected",
    ).length;
    const recentRequests = [...contactRequests]
      .sort(
        (first, second) =>
          new Date(second.requested_at).getTime() -
          new Date(first.requested_at).getTime(),
      )
      .slice(0, 5);

    return (
      <main className="page-shell tenant-page">
        <div className="tenant-dashboard">
          <header className="tenant-topbar">
            <AppLink
              className="tenant-brand"
              href="/"
              onNavigate={onNavigate}
            >
              <span aria-hidden="true" className="tenant-brand-mark">
                R
              </span>
              <span>Room Rentals</span>
            </AppLink>
            <nav aria-label="Tenant navigation" className="tenant-nav">
              <AppLink
                className="tenant-nav-link"
                href="/"
                onNavigate={onNavigate}
              >
                Browse rooms
              </AppLink>
              <AppLink
                className="tenant-nav-link"
                href="/conversations"
                onNavigate={onNavigate}
              >
                Messages
              </AppLink>
              <button
                className="tenant-signout"
                onClick={onSignOut}
                type="button"
              >
                Sign out
              </button>
            </nav>
          </header>

          <section aria-labelledby="dashboard-heading" className="tenant-hero">
            <div className="tenant-hero-copy">
              <p className="tenant-eyebrow">YOUR TENANT SPACE</p>
              <h1 id="dashboard-heading">
                Welcome back, {profile.full_name.trim().split(/\s+/)[0]}.
              </h1>
              <p>
                Keep track of your room enquiries and find your next place to
                call home.
              </p>
              <AppLink
                className="tenant-hero-button"
                href="/"
                onNavigate={onNavigate}
              >
                Explore available rooms <span aria-hidden="true">→</span>
              </AppLink>
            </div>
            <div aria-hidden="true" className="tenant-hero-art">
              <span className="tenant-hero-sun" />
              <span className="tenant-hero-home">
                <span className="tenant-hero-roof" />
                <span className="tenant-hero-window tenant-hero-window-left" />
                <span className="tenant-hero-window tenant-hero-window-right" />
                <span className="tenant-hero-door" />
              </span>
              <span className="tenant-hero-ground" />
            </div>
          </section>

          <section
            aria-label="Contact request overview"
            className="tenant-stat-grid"
          >
            <article className="tenant-stat-card">
              <span aria-hidden="true" className="tenant-stat-icon">
                ↗
              </span>
              <div>
                <p>Total enquiries</p>
                <strong>
                  {contactRequestsUnavailable ? "—" : contactRequests.length}
                </strong>
              </div>
            </article>
            <article className="tenant-stat-card">
              <span
                aria-hidden="true"
                className="tenant-stat-icon tenant-icon-pending"
              >
                ◷
              </span>
              <div>
                <p>Awaiting reply</p>
                <strong>
                  {contactRequestsUnavailable ? "—" : pendingCount}
                </strong>
              </div>
            </article>
            <article className="tenant-stat-card">
              <span
                aria-hidden="true"
                className="tenant-stat-icon tenant-icon-replied"
              >
                ✓
              </span>
              <div>
                <p>Replies received</p>
                <strong>
                  {contactRequestsUnavailable ? "—" : respondedCount}
                </strong>
              </div>
            </article>
          </section>

          <div className="tenant-content-grid">
            <div className="tenant-main-column">
              <RentalInterestNotificationsPanel
                accessToken={accessToken}
                onNavigate={onNavigate}
              />
              <TenantFutureRentalOpportunitiesPanel
                accessToken={accessToken}
                onNavigate={onNavigate}
                onRegistered={() =>
                  setRentalInterestRefreshKey((current) => current + 1)
                }
              />
              <TenantRentalInterestsPanel
                accessToken={accessToken}
                onNavigate={onNavigate}
                refreshKey={rentalInterestRefreshKey}
              />
              <section
                aria-labelledby="contact-requests-heading"
                className="tenant-panel tenant-requests-panel"
              >
                <div className="tenant-panel-heading">
                  <div>
                    <p className="tenant-eyebrow tenant-eyebrow-muted">
                      STAY IN THE LOOP
                    </p>
                    <h2 id="contact-requests-heading">Your enquiries</h2>
                  </div>
                  {contactRequests.length > 5 && (
                    <span className="tenant-count">
                      Latest 5 of {contactRequests.length}
                    </span>
                  )}
                </div>

                {isLoadingContactRequests && (
                  <p className="tenant-inline-state" role="status">
                    Loading your enquiries…
                  </p>
                )}
                {contactRequestsError !== null && (
                  <p className="message message-error" role="alert">
                    {contactRequestsError}
                  </p>
                )}
                {contactRequestActionError !== null && (
                  <p className="message message-error" role="alert">
                    {contactRequestActionError}
                  </p>
                )}
                {contactRequestActionNotice !== null && (
                  <p className="message message-success" role="status">
                    {contactRequestActionNotice}
                  </p>
                )}
                {reviewActionError !== null && (
                  <p className="message message-error" role="alert">
                    {reviewActionError}
                  </p>
                )}
                {reviewActionNotice !== null && (
                  <p className="message message-success" role="status">
                    {reviewActionNotice}
                  </p>
                )}

                {!isLoadingContactRequests &&
                  contactRequestsError === null &&
                  contactRequests.length === 0 && (
                    <div className="tenant-empty-state">
                      <span aria-hidden="true" className="tenant-empty-icon">
                        ⌂
                      </span>
                      <h3>Your next chapter starts with a room</h3>
                      <p>
                        When you enquire about a room, you’ll be able to follow
                        the response right here.
                      </p>
                      <AppLink
                        className="tenant-empty-link"
                        href="/"
                        onNavigate={onNavigate}
                      >
                        Browse available rooms{" "}
                        <span aria-hidden="true">→</span>
                      </AppLink>
                    </div>
                  )}

                {!isLoadingContactRequests &&
                  contactRequestsError === null &&
                  recentRequests.length > 0 && (
                    <ul className="tenant-request-list">
                      {recentRequests.map((contactRequest) => {
                        const review = reviews.find(
                          (item) =>
                            item.contact_request_id ===
                            contactRequest.request_id,
                        );
                        const canWriteReview =
                          contactRequest.status === "approved" &&
                          !isLoadingReviews &&
                          reviewsError === null;

                        return (
                          <li
                            className="tenant-request-item"
                            key={contactRequest.request_id}
                          >
                            <div
                              aria-hidden="true"
                              className="tenant-request-symbol"
                            >
                              ⌂
                            </div>
                            <div className="tenant-request-content">
                              <div className="tenant-request-main">
                                <div className="tenant-request-details">
                                  <AppLink
                                    className="tenant-listing-link"
                                    href={`/listings/${contactRequest.listing_id}`}
                                    onNavigate={onNavigate}
                                  >
                                    Room listing #{contactRequest.listing_id}
                                  </AppLink>
                                  <time dateTime={contactRequest.requested_at}>
                                    Sent {formatDate(contactRequest.requested_at)}
                                  </time>
                                </div>
                                <div className="tenant-request-actions">
                                  <span
                                    className={`tenant-status tenant-status-${contactRequest.status}`}
                                  >
                                    {contactRequest.status}
                                  </span>
                                  {contactRequest.status === "pending" && (
                                    <button
                                      className="tenant-cancel-button"
                                      disabled={updatingRequestId !== null}
                                      onClick={() =>
                                        void handleCancelContactRequest(
                                          contactRequest.request_id,
                                        )
                                      }
                                      type="button"
                                    >
                                      {updatingRequestId ===
                                      contactRequest.request_id
                                        ? "Cancelling…"
                                        : "Cancel"}
                                    </button>
                                  )}
                                </div>
                              </div>

                              {contactRequest.status === "approved" &&
                                isLoadingReviews && (
                                  <p
                                    className="tenant-review-muted"
                                    role="status"
                                  >
                                    Checking review status…
                                  </p>
                                )}
                              {contactRequest.status === "approved" &&
                                reviewsError !== null && (
                                  <p className="tenant-review-muted" role="alert">
                                    Reviews could not be checked. Try reloading
                                    the dashboard before submitting one.
                                  </p>
                                )}
                              {canWriteReview && review !== undefined && (
                                <div className="tenant-review-summary">
                                  <span aria-label={`${review.rating} out of 5 stars`}>
                                    {"★".repeat(review.rating)}
                                    {"☆".repeat(5 - review.rating)}
                                  </span>
                                  <strong>{review.rating} / 5</strong>
                                  {review.comment !== null && (
                                    <p>{review.comment}</p>
                                  )}
                                </div>
                              )}
                              {canWriteReview &&
                                review === undefined &&
                                reviewContactRequestId !==
                                  contactRequest.request_id && (
                                  <button
                                    className="tenant-review-button"
                                    disabled={isSubmittingReview}
                                    onClick={() => {
                                      setReviewActionError(null);
                                      setReviewActionNotice(null);
                                      setReviewContactRequestId(
                                        contactRequest.request_id,
                                      );
                                    }}
                                    type="button"
                                  >
                                    Write a review
                                  </button>
                                )}
                              {canWriteReview &&
                                review === undefined &&
                                reviewContactRequestId ===
                                  contactRequest.request_id && (
                                  <form
                                    className="tenant-review-form"
                                    onSubmit={(event) => {
                                      event.preventDefault();
                                      void handleSubmitReview(
                                        contactRequest.request_id,
                                      );
                                    }}
                                  >
                                    <label>
                                      Rating
                                      <select
                                        disabled={isSubmittingReview}
                                        onChange={(event) =>
                                          setReviewRating(
                                            event.currentTarget.value,
                                          )
                                        }
                                        value={reviewRating}
                                      >
                                        {[5, 4, 3, 2, 1].map((rating) => (
                                          <option key={rating} value={rating}>
                                            {rating} / 5
                                          </option>
                                        ))}
                                      </select>
                                    </label>
                                    <label>
                                      Comment <span>Optional</span>
                                      <textarea
                                        maxLength={2000}
                                        onChange={(event) =>
                                          setReviewComment(
                                            event.currentTarget.value,
                                          )
                                        }
                                        rows={3}
                                        value={reviewComment}
                                      />
                                    </label>
                                    <div className="tenant-review-actions">
                                      <button
                                        className="tenant-review-submit"
                                        disabled={isSubmittingReview}
                                        type="submit"
                                      >
                                        {isSubmittingReview
                                          ? "Submitting…"
                                          : "Submit review"}
                                      </button>
                                      <button
                                        className="tenant-review-cancel"
                                        disabled={isSubmittingReview}
                                        onClick={() =>
                                          setReviewContactRequestId(null)
                                        }
                                        type="button"
                                      >
                                        Cancel
                                      </button>
                                    </div>
                                  </form>
                                )}
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
              </section>

              <section
                aria-labelledby="saved-listings-heading"
                className="tenant-panel"
              >
                <div className="tenant-panel-heading">
                  <div>
                    <p className="tenant-eyebrow tenant-eyebrow-muted">
                      KEEP YOUR FAVOURITES
                    </p>
                    <h2 id="saved-listings-heading">Saved rooms</h2>
                  </div>
                  <AppLink
                    className="tenant-panel-link"
                    href="/"
                    onNavigate={onNavigate}
                  >
                    Browse rooms <span aria-hidden="true">→</span>
                  </AppLink>
                </div>

                {isLoadingSavedListings && (
                  <p className="tenant-inline-state" role="status">
                    Loading your saved rooms…
                  </p>
                )}
                {savedListingsError !== null && (
                  <p className="message message-error" role="alert">
                    {savedListingsError}
                  </p>
                )}
                {!isLoadingSavedListings &&
                  savedListingsError === null &&
                  savedListings.length === 0 && (
                    <div className="tenant-saved-empty">
                      <p>Save rooms you like to find them here later.</p>
                    </div>
                  )}
                {!isLoadingSavedListings &&
                  savedListingsError === null &&
                  savedListings.length > 0 && (
                    <ul className="tenant-saved-search-list">
                      {savedListings.map((listing) => (
                        <li key={listing.listing_id}>
                          <div>
                            <strong>{listing.title}</strong>
                            <time>
                              {listing.area_name ?? listing.address} · R
                              {Number(listing.monthly_rent).toLocaleString(
                                "en-ZA",
                              )}
                              /month
                            </time>
                          </div>
                          <div className="tenant-saved-search-actions">
                            <button
                              className="tenant-review-button"
                              onClick={() =>
                                onNavigate(`/listings/${listing.listing_id}`)
                              }
                              type="button"
                            >
                              View room
                            </button>
                            <button
                              className="tenant-cancel-button"
                              disabled={deletingSavedListingId !== null}
                              onClick={() =>
                                void handleDeleteSavedListing(
                                  listing.listing_id,
                                )
                              }
                              type="button"
                            >
                              {deletingSavedListingId === listing.listing_id
                                ? "Removing…"
                                : "Remove"}
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
              </section>

              <section
                aria-labelledby="saved-searches-heading"
                className="tenant-panel tenant-saved-searches"
              >
                <div className="tenant-panel-heading">
                  <div>
                    <p className="tenant-eyebrow tenant-eyebrow-muted">
                      YOUR PREFERENCES
                    </p>
                    <h2 id="saved-searches-heading">Saved searches</h2>
                  </div>
                  <AppLink
                    className="tenant-panel-link"
                    href="/"
                    onNavigate={onNavigate}
                  >
                    Find rooms <span aria-hidden="true">→</span>
                  </AppLink>
                </div>

                {isLoadingSavedSearches && (
                  <p className="tenant-inline-state" role="status">
                    Loading your saved searches…
                  </p>
                )}
                {savedSearchesError !== null && (
                  <p className="message message-error" role="alert">
                    {savedSearchesError}
                  </p>
                )}
                {savedSearchActionError !== null && (
                  <p className="message message-error" role="alert">
                    {savedSearchActionError}
                  </p>
                )}
                {!isLoadingSavedSearches &&
                  savedSearchesError === null &&
                  savedSearches.length === 0 && (
                    <div className="tenant-saved-empty">
                      <p>
                        Save a search from the room browser to quickly revisit
                        the places and amenities you prefer.
                      </p>
                      <AppLink
                        className="tenant-empty-link"
                        href="/"
                        onNavigate={onNavigate}
                      >
                        Browse and save a search{" "}
                        <span aria-hidden="true">→</span>
                      </AppLink>
                    </div>
                  )}
                {!isLoadingSavedSearches &&
                  savedSearchesError === null &&
                  savedSearches.length > 0 && (
                    <ul className="tenant-saved-search-list">
                      {savedSearches.map((search) => (
                        <li key={search.saved_search_id}>
                          <div>
                            <strong>{getSavedSearchLabel(search)}</strong>
                            <time dateTime={search.created_at}>
                              Saved {formatDate(search.created_at)}
                            </time>
                          </div>
                          <div className="tenant-saved-search-actions">
                            <button
                              className="tenant-review-button"
                              onClick={() =>
                                onNavigate(getSavedSearchPath(search))
                              }
                              type="button"
                            >
                              Search again
                            </button>
                            <button
                              className="tenant-review-button"
                              disabled={updatingAlertSearchId !== null}
                              onClick={() =>
                                void handleUpdateSearchAlerts(
                                  search.saved_search_id,
                                  !search.alerts_enabled,
                                )
                              }
                              type="button"
                            >
                              {updatingAlertSearchId ===
                              search.saved_search_id
                                ? "Updating…"
                                : search.alerts_enabled
                                  ? "Turn alerts off"
                                  : "Turn WhatsApp alerts on"}
                            </button>
                            <button
                              className="tenant-cancel-button"
                              disabled={deletingSavedSearchId !== null}
                              onClick={() =>
                                void handleDeleteSavedSearch(
                                  search.saved_search_id,
                                )
                              }
                              type="button"
                            >
                              {deletingSavedSearchId === search.saved_search_id
                                ? "Deleting…"
                                : "Delete"}
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
              </section>
            </div>

            <aside className="tenant-side-column">
              <section
                aria-labelledby="profile-heading"
                className="tenant-panel tenant-profile-panel"
              >
                <div className="tenant-avatar" aria-hidden="true">
                  {profile.full_name.trim().charAt(0).toUpperCase()}
                </div>
                <p className="tenant-eyebrow tenant-eyebrow-muted">
                  YOUR ACCOUNT
                </p>
                <h2 id="profile-heading">{profile.full_name}</h2>
                <p className="tenant-profile-email">{profile.email}</p>
                <div className="tenant-profile-divider" />
                <div className="tenant-profile-role">
                  <span>Account type</span>
                  <span className="tenant-role-pill">Tenant</span>
                </div>
              </section>

              <section
                aria-labelledby="support-heading"
                className="tenant-help-card"
              >
                <span aria-hidden="true" className="tenant-help-icon">
                  ?
                </span>
                <h2 id="support-heading">Need to flag something?</h2>
                <p>
                  Let our team know about a listing or account that needs a
                  closer look.
                </p>
                <button
                  className="tenant-help-link"
                  onClick={onOpenReports}
                  type="button"
                >
                  Report an issue <span aria-hidden="true">→</span>
                </button>
              </section>
            </aside>
          </div>

          <footer className="tenant-footer">
            <span>Room Rentals</span>
            <span>Find a place to feel at home.</span>
          </footer>
        </div>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="profile-card" aria-labelledby="dashboard-heading">
        <p className="eyebrow">Room Rentals</p>
        <h1 id="dashboard-heading">{content.heading}</h1>
        <p className="intro">
          Welcome, {profile.full_name}. {content.description}
        </p>

        <dl className="profile-list">
          <div>
            <dt>Email</dt>
            <dd>{profile.email}</dd>
          </div>
          <div>
            <dt>Account role</dt>
            <dd className="role-list">
              <span className="role-chip">{role}</span>
            </dd>
          </div>
        </dl>

        <p className="dashboard-note">{content.nextStep}</p>

        <div className="dashboard-actions">
          <AppLink
            className="primary-button dashboard-link"
            href="/"
            onNavigate={onNavigate}
          >
            Browse rooms
          </AppLink>
          <button
            className="secondary-button"
            onClick={onSignOut}
            type="button"
          >
            Sign out
          </button>
        </div>
      </section>
    </main>
  );
}
