import { useEffect, useState } from "react";

import {
  cancelContactRequest,
  getMyContactRequests,
  type ContactRequest,
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

        {role === "tenant" && (
          <section
            aria-labelledby="contact-requests-heading"
            className="contact-requests"
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
            {!isLoadingContactRequests &&
              contactRequestsError === null &&
              contactRequests.length === 0 && (
                <p>You have not submitted any contact requests yet.</p>
              )}
            {!isLoadingContactRequests &&
              contactRequestsError === null &&
              contactRequests.length > 0 && (
                <ul className="contact-request-list">
                  {contactRequests.map((contactRequest) => (
                    <li
                      className="contact-request-item"
                      key={contactRequest.request_id}
                    >
                      <p>
                        Listing #{contactRequest.listing_id}
                      </p>
                      <p>
                        Status: <strong>{contactRequest.status}</strong>
                      </p>
                      <p>
                        Requested:{" "}
                        {formatRequestDate(contactRequest.requested_at)}
                      </p>
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
                  ))}
                </ul>
              )}
          </section>
        )}

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
