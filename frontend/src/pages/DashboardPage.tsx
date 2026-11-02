import { useEffect, useState } from "react";

import {
  cancelContactRequest,
  createReview,
  deleteSavedSearch,
  getMyContactRequests,
  getMySavedSearches,
  getMyReviews,
  type ContactRequest,
  type Review,
  type SavedSearch,
  type UserProfile,
} from "../api";
import AppLink from "../components/AppLink";

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

export default function DashboardPage({
  accessToken,
  onNavigate,
  profile,
  role,
  onSignOut,
  onOpenReports,
}: DashboardPageProps) {
  const content = dashboardContent[role];
  const [contactRequests, setContactRequests] = useState<ContactRequest[]>([]);
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

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let isCurrent = true;
    setContactRequestsError(null);
    setIsLoadingContactRequests(true);

    async function loadContactRequests(): Promise<void> {
      try {
        const requests = await getMyContactRequests(accessToken);
        if (isCurrent) {
          setContactRequests(requests);
        }
      } catch (error: unknown) {
        if (isCurrent) {
          setContactRequestsError(
            error instanceof Error
              ? error.message
              : "Your contact requests could not be loaded.",
          );
        }
      } finally {
        if (isCurrent) {
          setIsLoadingContactRequests(false);
        }
      }
    }

    void loadContactRequests();
    return () => {
      isCurrent = false;
    };
  }, [accessToken, role]);

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let isCurrent = true;
    setReviewsError(null);
    setIsLoadingReviews(true);

    async function loadReviews(): Promise<void> {
      try {
        const tenantReviews = await getMyReviews(accessToken);
        if (isCurrent) {
          setReviews(tenantReviews);
        }
      } catch (error: unknown) {
        if (isCurrent) {
          setReviewsError(
            error instanceof Error
              ? error.message
              : "Your reviews could not be loaded.",
          );
        }
      } finally {
        if (isCurrent) {
          setIsLoadingReviews(false);
        }
      }
    }

    void loadReviews();
    return () => {
      isCurrent = false;
    };
  }, [accessToken, role]);

  useEffect(() => {
    if (role !== "tenant") {
      return;
    }

    let isCurrent = true;
    setSavedSearchesError(null);
    setIsLoadingSavedSearches(true);

    async function loadSavedSearches(): Promise<void> {
      try {
        const searches = await getMySavedSearches(accessToken);
        if (isCurrent) {
          setSavedSearches(searches);
        }
      } catch (error: unknown) {
        if (isCurrent) {
          setSavedSearchesError(
            error instanceof Error
              ? error.message
              : "Your saved searches could not be loaded.",
          );
        }
      } finally {
        if (isCurrent) {
          setIsLoadingSavedSearches(false);
        }
      }
    }

    void loadSavedSearches();
    return () => {
      isCurrent = false;
    };
  }, [accessToken, role]);

  function formatRequestDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Date unavailable";
    }

    return new Intl.DateTimeFormat("en-ZA", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  function formatSavedSearch(search: SavedSearch): string {
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
    return filters.join(" · ");
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
    return `/?${params.toString()}`;
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

  async function handleCancelContactRequest(
    requestId: number,
  ): Promise<void> {
    setContactRequestActionError(null);
    setContactRequestActionNotice(null);
    setUpdatingRequestId(requestId);
    try {
      const updatedRequest = await cancelContactRequest(
        accessToken,
        requestId,
      );
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

  return (
    <main
      className={
        role === "tenant" ? "page-shell tenant-dashboard-shell" : "page-shell"
      }
    >
      <section
        className={
          role === "tenant"
            ? "profile-card tenant-dashboard-card"
            : "profile-card"
        }
        aria-labelledby="dashboard-heading"
      >
        <header
          className={
            role === "tenant" ? "tenant-dashboard-header" : undefined
          }
        >
          <div>
            <p className="eyebrow">Room Rentals</p>
            <h1 id="dashboard-heading">{content.heading}</h1>
            <p className="intro">
              Welcome, {profile.full_name}. {content.description}
            </p>
          </div>
        </header>

        <dl
          className={
            role === "tenant"
              ? "profile-list tenant-dashboard-profile"
              : "profile-list"
          }
        >
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

        <p
          className={
            role === "tenant"
              ? "dashboard-note tenant-dashboard-note"
              : "dashboard-note"
          }
        >
          {content.nextStep}
        </p>

        {role === "tenant" && (
          <section
            aria-labelledby="saved-searches-heading"
            className="contact-requests tenant-dashboard-section saved-searches-section"
          >
            <h2 id="saved-searches-heading">Your saved searches</h2>
            {isLoadingSavedSearches && (
              <p role="status">Loading your saved searches…</p>
            )}
            {savedSearchesError !== null && (
              <p role="alert">{savedSearchesError}</p>
            )}
            {savedSearchActionError !== null && (
              <p role="alert">{savedSearchActionError}</p>
            )}
            {!isLoadingSavedSearches &&
              savedSearchesError === null &&
              savedSearches.length === 0 && (
                <p>You have not saved any searches yet.</p>
              )}
            {!isLoadingSavedSearches &&
              savedSearchesError === null &&
              savedSearches.length > 0 && (
                <ul className="contact-request-list tenant-dashboard-list">
                  {savedSearches.map((search) => (
                    <li
                      className="contact-request-item tenant-dashboard-item"
                      key={search.saved_search_id}
                    >
                      <p>{formatSavedSearch(search)}</p>
                      <p>Saved: {formatRequestDate(search.created_at)}</p>
                      <button
                        className="secondary-button"
                        onClick={() => onNavigate(getSavedSearchPath(search))}
                        type="button"
                      >
                        Search again
                      </button>
                      <button
                        className="secondary-button"
                        disabled={deletingSavedSearchId !== null}
                        onClick={() =>
                          void handleDeleteSavedSearch(search.saved_search_id)
                        }
                        type="button"
                      >
                        {deletingSavedSearchId === search.saved_search_id
                          ? "Deleting…"
                          : "Delete search"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
          </section>
        )}

        {role === "tenant" && (
          <section
            aria-labelledby="contact-requests-heading"
            className="contact-requests tenant-dashboard-section contact-requests-section"
          >
            <h2 id="contact-requests-heading">Your contact requests</h2>
            {isLoadingContactRequests && (
              <p role="status">Loading your contact requests…</p>
            )}
            {contactRequestsError !== null && (
              <p role="alert">{contactRequestsError}</p>
            )}
            {contactRequestActionError !== null && (
              <p role="alert">{contactRequestActionError}</p>
            )}
            {contactRequestActionNotice !== null && (
              <p role="status">{contactRequestActionNotice}</p>
            )}
            {reviewActionError !== null && (
              <p role="alert">{reviewActionError}</p>
            )}
            {reviewActionNotice !== null && (
              <p role="status">{reviewActionNotice}</p>
            )}
            {!isLoadingContactRequests &&
              contactRequestsError === null &&
              contactRequests.length === 0 && (
                <p>You have not submitted any contact requests yet.</p>
              )}
            {!isLoadingContactRequests &&
              contactRequestsError === null &&
              contactRequests.length > 0 && (
                <ul className="contact-request-list tenant-dashboard-list">
                  {contactRequests.map((contactRequest) => {
                    const review = reviews.find(
                      (item) =>
                        item.contact_request_id === contactRequest.request_id,
                    );
                    return (
                      <li
                        className="contact-request-item tenant-dashboard-item"
                        key={contactRequest.request_id}
                      >
                      <p className="tenant-request-listing">
                        Listing #{contactRequest.listing_id}
                      </p>
                      <p>
                        Status:{" "}
                        <strong
                          className={`request-status request-status-${contactRequest.status}`}
                        >
                          {contactRequest.status}
                        </strong>
                      </p>
                      <p>
                        Requested: {formatRequestDate(contactRequest.requested_at)}
                      </p>
                      {contactRequest.status === "approved" &&
                        !isLoadingReviews &&
                        reviewsError === null &&
                        (review !== undefined ? (
                          <>
                            <p>
                              Review submitted:{" "}
                              <strong>{review.rating} / 5</strong>
                            </p>
                            {review.comment !== null && (
                              <p>{review.comment}</p>
                            )}
                          </>
                        ) : reviewContactRequestId ===
                          contactRequest.request_id ? (
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
                                  setReviewRating(event.currentTarget.value)
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
                              Comment (optional)
                              <textarea
                                maxLength={2000}
                                onChange={(event) =>
                                  setReviewComment(event.currentTarget.value)
                                }
                                value={reviewComment}
                              />
                            </label>
                            <button
                              className="primary-button"
                              disabled={isSubmittingReview}
                              type="submit"
                            >
                              {isSubmittingReview
                                ? "Submitting review…"
                                : "Submit review"}
                            </button>
                            <button
                              className="secondary-button"
                              disabled={isSubmittingReview}
                              onClick={() =>
                                setReviewContactRequestId(null)
                              }
                              type="button"
                            >
                              Cancel
                            </button>
                          </form>
                        ) : (
                          <button
                            className="secondary-button"
                            disabled={isLoadingReviews || reviewsError !== null}
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
                        ))}
                      {reviewsError !== null &&
                        contactRequest.status === "approved" && (
                          <p role="alert">
                            Reviews could not be checked, so review submission
                            is unavailable.
                          </p>
                        )}
                      {contactRequest.status === "pending" && (
                        <button
                          className="secondary-button"
                          disabled={updatingRequestId !== null}
                          onClick={() =>
                            void handleCancelContactRequest(
                              contactRequest.request_id,
                            )
                          }
                          type="button"
                        >
                          {updatingRequestId === contactRequest.request_id
                            ? "Cancelling…"
                            : "Cancel request"}
                        </button>
                      )}
                      </li>
                    );
                  })}
                </ul>
              )}
          </section>
        )}

        <div
          className={
            role === "tenant"
              ? "dashboard-actions tenant-dashboard-actions"
              : "dashboard-actions"
          }
        >
          {role === "tenant" && (
            <button
              className="secondary-button"
              onClick={onOpenReports}
              type="button"
            >
              Report an issue / view my reports
            </button>
          )}
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
