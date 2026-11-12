import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  getMyRentalInterests,
  renewRentalInterest,
  withdrawRentalInterest,
  type RentalInterest,
  type RentalInterestStatus,
} from "../api";
import "./RentalInterestPanels.css";

type TenantRentalInterestsPanelProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
  refreshKey: number;
};

const activeStatuses: RentalInterestStatus[] = [
  "active",
  "waitlisted",
  "contacted",
  "invited_to_apply",
];

const statusLabels: Record<RentalInterestStatus, string> = {
  active: "Registered",
  waitlisted: "Waitlisted",
  contacted: "Landlord marked contacted",
  invited_to_apply: "Invited to apply",
  converted: "Marked as converted",
  withdrawn: "Withdrawn",
  expired: "Expired",
  closed: "Closed",
};

const statusDescriptions: Record<RentalInterestStatus, string> = {
  active: "Your interest is in the active queue. This is not a booking.",
  waitlisted:
    "The active queue is full. You are waitlisted and have no confirmed place.",
  contacted:
    "The landlord updated your status. This does not confirm that a message was sent.",
  invited_to_apply:
    "The landlord marked you as invited to apply. A room is not reserved.",
  converted:
    "The landlord marked this interest as converted. Confirm any rental directly; this status is not a booking.",
  withdrawn: "You withdrew this interest.",
  expired: "This interest expired. You can renew it if the opportunity is still open.",
  closed: "The landlord closed this opportunity.",
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(date);
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatRent(value: string | number): string {
  const rent = Number(value);
  return Number.isFinite(rent)
    ? new Intl.NumberFormat("en-ZA", {
        style: "currency",
        currency: "ZAR",
        maximumFractionDigits: 0,
      }).format(rent)
    : "Rent unavailable";
}

export default function TenantRentalInterestsPanel({
  accessToken,
  onNavigate,
  refreshKey,
}: TenantRentalInterestsPanelProps) {
  const [interests, setInterests] = useState<RentalInterest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("recent");
  const [updatingInterestId, setUpdatingInterestId] = useState<number | null>(
    null,
  );
  const [waitlistRenewalId, setWaitlistRenewalId] = useState<number | null>(
    null,
  );

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setLoadError(null);
    getMyRentalInterests(accessToken)
      .then((items) => {
        if (active) {
          setInterests(items);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Your future rental interests could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [accessToken, refreshKey]);

  const visibleInterests = useMemo(() => {
    const filtered = interests.filter(
      (interest) =>
        statusFilter === "all" || interest.status === statusFilter,
    );
    return filtered.sort((first, second) => {
      if (sortOrder === "move_in") {
        return first.expected_move_in_date.localeCompare(
          second.expected_move_in_date,
        );
      }
      if (sortOrder === "status") {
        return statusLabels[first.status].localeCompare(
          statusLabels[second.status],
        );
      }
      return second.registered_at.localeCompare(first.registered_at);
    });
  }, [interests, sortOrder, statusFilter]);

  async function handleWithdraw(interestId: number): Promise<void> {
    setActionError(null);
    setActionNotice(null);
    setUpdatingInterestId(interestId);
    try {
      const updated = await withdrawRentalInterest(accessToken, interestId);
      setInterests((items) =>
        items.map((item) =>
          item.interest_id === updated.interest_id ? updated : item,
        ),
      );
      setActionNotice("Your interest was withdrawn.");
    } catch (error: unknown) {
      setActionError(
        error instanceof Error
          ? error.message
          : "Your interest could not be withdrawn.",
      );
    } finally {
      setUpdatingInterestId(null);
    }
  }

  async function handleRenew(
    interestId: number,
    joinWaitlist = false,
  ): Promise<void> {
    setActionError(null);
    setActionNotice(null);
    setUpdatingInterestId(interestId);
    try {
      const updated = await renewRentalInterest(
        accessToken,
        interestId,
        joinWaitlist,
      );
      setInterests((items) =>
        items.map((item) =>
          item.interest_id === updated.interest_id ? updated : item,
        ),
      );
      setWaitlistRenewalId(null);
      setActionNotice("Your interest was renewed.");
    } catch (error: unknown) {
      if (
        error instanceof ApiError &&
        error.code === "waitlist_consent_required"
      ) {
        setWaitlistRenewalId(interestId);
      } else {
        setActionError(
          error instanceof Error
            ? error.message
            : "Your interest could not be renewed.",
        );
      }
    } finally {
      setUpdatingInterestId(null);
    }
  }

  return (
    <section
      aria-labelledby="tenant-rental-interests-heading"
      className="rental-interest-panel tenant-panel"
    >
      <div className="tenant-panel-heading">
        <div>
          <p className="tenant-eyebrow tenant-eyebrow-muted">
            PLAN YOUR NEXT MOVE
          </p>
          <h2 id="tenant-rental-interests-heading">Future rental interests</h2>
        </div>
        <div className="rental-interest-controls">
          <label>
            <span className="visually-hidden">Filter by status</span>
            <select
              onChange={(event) => setStatusFilter(event.target.value)}
              value={statusFilter}
            >
              <option value="all">All statuses</option>
              {Object.entries(statusLabels).map(([status, label]) => (
                <option key={status} value={status}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="visually-hidden">Sort interests</span>
            <select
              onChange={(event) => setSortOrder(event.target.value)}
              value={sortOrder}
            >
              <option value="recent">Newest first</option>
              <option value="move_in">Move-in date</option>
              <option value="status">Status</option>
            </select>
          </label>
        </div>
      </div>

      <p className="rental-interest-notice">
        Registering interest is free. It is not a booking or reservation, and
        rent is not charged through this feature.
      </p>

      {isLoading && (
        <p className="tenant-inline-state" role="status">
          Loading your future rental interests…
        </p>
      )}
      {loadError !== null && (
        <p className="message message-error" role="alert">
          {loadError}
        </p>
      )}
      {actionError !== null && (
        <p className="message message-error" role="alert">
          {actionError}
        </p>
      )}
      {actionNotice !== null && (
        <p className="message message-success" role="status">
          {actionNotice}
        </p>
      )}
      {!isLoading && loadError === null && interests.length === 0 && (
        <div className="tenant-saved-empty">
          <p>
            You have not registered interest in any future rental
            opportunities yet.
          </p>
        </div>
      )}
      {!isLoading &&
        loadError === null &&
        interests.length > 0 &&
        visibleInterests.length === 0 && (
          <p className="rental-interest-empty-filter">
            No interests match this status filter.
          </p>
        )}

      {visibleInterests.length > 0 && (
        <ul className="rental-interest-list">
          {visibleInterests.map((interest) => {
            const canWithdraw = activeStatuses.includes(interest.status);
            return (
              <li className="rental-interest-card" key={interest.interest_id}>
                <div className="rental-interest-card-heading">
                  <div>
                    <h3>{interest.opportunity.listing_title}</h3>
                    <p>
                      {interest.opportunity.area_name} ·{" "}
                      {formatRent(interest.opportunity.monthly_rent)}/month
                    </p>
                  </div>
                  <span
                    className={`rental-interest-status status-${interest.status}`}
                  >
                    {statusLabels[interest.status]}
                  </span>
                </div>
                <p className="rental-interest-status-description">
                  {statusDescriptions[interest.status]}
                </p>
                <dl className="rental-interest-facts">
                  <div>
                    <dt>Move-in date</dt>
                    <dd>{formatDate(interest.expected_move_in_date)}</dd>
                  </div>
                  <div>
                    <dt>Rental period</dt>
                    <dd>{interest.expected_duration_months} months</dd>
                  </div>
                  <div>
                    <dt>Your monthly budget</dt>
                    <dd>{formatRent(interest.monthly_budget)}</dd>
                  </div>
                  <div>
                    <dt>Registered</dt>
                    <dd>{formatDateTime(interest.registered_at)}</dd>
                  </div>
                  <div>
                    <dt>Interest expires</dt>
                    <dd>{formatDateTime(interest.expires_at)}</dd>
                  </div>
                </dl>
                {(interest.required_amenities.length > 0 ||
                  interest.preferred_room_type !== null) && (
                  <p className="rental-interest-preferences">
                    Preferences:{" "}
                    {[
                      interest.preferred_room_type?.replaceAll("_", " "),
                      ...interest.required_amenities,
                    ]
                      .filter((value): value is string => value !== undefined)
                      .join(", ")}
                  </p>
                )}
                <details className="rental-interest-history">
                  <summary>
                    Status history ({interest.history.length})
                  </summary>
                  <ol>
                    {interest.history.map((entry, index) => (
                      <li key={`${entry.changed_at}-${index}`}>
                        <strong>{statusLabels[entry.to_status]}</strong>
                        <time dateTime={entry.changed_at}>
                          {formatDateTime(entry.changed_at)}
                        </time>
                        {entry.note !== null && <p>{entry.note}</p>}
                      </li>
                    ))}
                  </ol>
                </details>
                <div className="rental-interest-actions">
                  <button
                    className="rental-interest-secondary-button"
                    onClick={() =>
                      onNavigate(`/listings/${interest.opportunity.listing_id}`)
                    }
                    type="button"
                  >
                    View room
                  </button>
                  {interest.status === "expired" && (
                    waitlistRenewalId === interest.interest_id ? (
                      <div className="rental-interest-consent" role="status">
                        <p>
                          Capacity is full. Renewing with consent will place
                          your interest on the waiting list, not reserve a
                          room.
                        </p>
                        <button
                          className="rental-interest-primary-button"
                          disabled={updatingInterestId !== null}
                          onClick={() =>
                            void handleRenew(interest.interest_id, true)
                          }
                          type="button"
                        >
                          {updatingInterestId === interest.interest_id
                            ? "Renewing…"
                            : "Confirm and join waitlist"}
                        </button>
                        <button
                          className="rental-interest-text-button"
                          disabled={updatingInterestId !== null}
                          onClick={() => setWaitlistRenewalId(null)}
                          type="button"
                        >
                          No, cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        className="rental-interest-primary-button"
                        disabled={updatingInterestId !== null}
                        onClick={() => void handleRenew(interest.interest_id)}
                        type="button"
                      >
                        {updatingInterestId === interest.interest_id
                          ? "Renewing…"
                          : "Renew interest"}
                      </button>
                    )
                  )}
                  {canWithdraw && (
                    <button
                      className="rental-interest-text-button"
                      disabled={updatingInterestId !== null}
                      onClick={() => void handleWithdraw(interest.interest_id)}
                      type="button"
                    >
                      {updatingInterestId === interest.interest_id
                        ? "Withdrawing…"
                        : "Withdraw"}
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
