import { useEffect, useState } from "react";

import {
  cancelContactRequest,
  getMyContactRequests,
  type ContactRequest,
  type UserProfile,
} from "../api";
import AppLink from "../components/AppLink";
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
                Welcome back, {profile.full_name.split(" ")[0]}.
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
              <span aria-hidden="true" className="tenant-stat-icon tenant-icon-pending">
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
              <span aria-hidden="true" className="tenant-stat-icon tenant-icon-replied">
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
                      Browse available rooms <span aria-hidden="true">→</span>
                    </AppLink>
                  </div>
                )}

              {!isLoadingContactRequests &&
                contactRequestsError === null &&
                recentRequests.length > 0 && (
                  <ul className="tenant-request-list">
                    {recentRequests.map((contactRequest) => (
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
                        <div className="tenant-request-details">
                          <AppLink
                            className="tenant-listing-link"
                            href={`/listings/${contactRequest.listing_id}`}
                            onNavigate={onNavigate}
                          >
                            Room listing #{contactRequest.listing_id}
                          </AppLink>
                          <time dateTime={contactRequest.requested_at}>
                            Sent {formatRequestDate(contactRequest.requested_at)}
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
                              {updatingRequestId === contactRequest.request_id
                                ? "Cancelling…"
                                : "Cancel"}
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
            </section>

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
        <p className="intro">Welcome, {profile.full_name}. {content.description}</p>

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
