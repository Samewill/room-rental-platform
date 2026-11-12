import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  closeInterestOpportunity,
  getMyInterestOpportunities,
  getReceivedRentalInterests,
  saveInterestOpportunity,
  updateRentalInterestStatus,
  type InterestOpportunity,
  type InterestOpportunityRequest,
  type LandlordRentalInterest,
  type ReceivedRentalInterestFilters,
  type RentalInterestRoomType,
  type RentalInterestStatus,
} from "../api";
import type { Listing } from "../types/listing";
import "./RentalInterestPanels.css";

type LandlordRentalInterestsPanelProps = {
  accessToken: string;
  listings: Listing[];
};

type OpportunityFormState = {
  availableFrom: string;
  availableUntil: string;
  availableUnits: string;
  maxActiveRegistrations: string;
  waitlistEnabled: boolean;
  expectedRentalDurationMonths: string;
};

type FilterFormState = {
  opportunityId: string;
  moveInFrom: string;
  moveInUntil: string;
  minimumBudget: string;
  maximumBudget: string;
  preferredRoomType: string;
  requiredAmenities: string[];
};

const amenityOptions = ["Wi-Fi", "Parking", "Furnished", "Laundry"];
const roomTypes: Array<{ value: RentalInterestRoomType; label: string }> = [
  { value: "single_room", label: "Single room" },
  { value: "shared_room", label: "Shared room" },
  { value: "bachelor_flat", label: "Bachelor flat" },
  { value: "self_contained", label: "Self-contained" },
];

const statusLabels: Record<RentalInterestStatus, string> = {
  active: "Registered",
  waitlisted: "Waitlisted",
  contacted: "Contacted",
  invited_to_apply: "Invited to apply",
  converted: "Converted",
  withdrawn: "Withdrawn",
  expired: "Expired",
  closed: "Closed",
};

const emptyFilters: FilterFormState = {
  opportunityId: "",
  moveInFrom: "",
  moveInUntil: "",
  minimumBudget: "",
  maximumBudget: "",
  preferredRoomType: "",
  requiredAmenities: [],
};

function todayString(): string {
  const now = new Date();
  const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(date);
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : new Intl.DateTimeFormat("en-ZA", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function formatRent(value: string | number): string {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat("en-ZA", {
        style: "currency",
        currency: "ZAR",
        maximumFractionDigits: 0,
      }).format(amount)
    : "Budget unavailable";
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The request could not be completed. Please try again.";
}

function getOpportunityPayload(
  form: OpportunityFormState,
): InterestOpportunityRequest {
  return {
    available_from: form.availableFrom,
    available_until: form.availableUntil === "" ? null : form.availableUntil,
    available_units:
      form.availableUnits === "" ? null : Number(form.availableUnits),
    max_active_registrations: Number(form.maxActiveRegistrations),
    waitlist_enabled: form.waitlistEnabled,
    expected_rental_duration_months:
      form.expectedRentalDurationMonths === ""
        ? null
        : Number(form.expectedRentalDurationMonths),
  };
}

function getFilters(form: FilterFormState): ReceivedRentalInterestFilters {
  const filters: ReceivedRentalInterestFilters = {};
  if (form.opportunityId !== "") {
    filters.opportunity_id = Number(form.opportunityId);
  }
  if (form.moveInFrom !== "") {
    filters.move_in_from = form.moveInFrom;
  }
  if (form.moveInUntil !== "") {
    filters.move_in_until = form.moveInUntil;
  }
  if (form.minimumBudget !== "") {
    filters.minimum_budget = Number(form.minimumBudget);
  }
  if (form.maximumBudget !== "") {
    filters.maximum_budget = Number(form.maximumBudget);
  }
  if (form.preferredRoomType !== "") {
    filters.preferred_room_type =
      form.preferredRoomType as RentalInterestRoomType;
  }
  if (form.requiredAmenities.length > 0) {
    filters.required_amenities = form.requiredAmenities;
  }
  return filters;
}

export default function LandlordRentalInterestsPanel({
  accessToken,
  listings,
}: LandlordRentalInterestsPanelProps) {
  const [opportunities, setOpportunities] = useState<InterestOpportunity[]>([]);
  const [interests, setInterests] = useState<LandlordRentalInterest[]>([]);
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(true);
  const [isLoadingInterests, setIsLoadingInterests] = useState(true);
  const [opportunityError, setOpportunityError] = useState<string | null>(null);
  const [interestError, setInterestError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editingListingId, setEditingListingId] = useState<number | null>(null);
  const [opportunityForm, setOpportunityForm] =
    useState<OpportunityFormState | null>(null);
  const [savingListingId, setSavingListingId] = useState<number | null>(null);
  const [closingOpportunityId, setClosingOpportunityId] = useState<
    number | null
  >(null);
  const [updatingInterestId, setUpdatingInterestId] = useState<number | null>(
    null,
  );
  const [filters, setFilters] = useState<FilterFormState>(emptyFilters);
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("priority");

  useEffect(() => {
    let active = true;
    setIsLoadingOpportunities(true);
    setOpportunityError(null);
    getMyInterestOpportunities(accessToken)
      .then((items) => {
        if (active) {
          setOpportunities(items);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setOpportunityError(getErrorMessage(error));
        }
      })
      .finally(() => {
        if (active) {
          setIsLoadingOpportunities(false);
        }
      });

    return () => {
      active = false;
    };
  }, [accessToken]);

  useEffect(() => {
    let active = true;
    setIsLoadingInterests(true);
    setInterestError(null);
    getReceivedRentalInterests(accessToken)
      .then((items) => {
        if (active) {
          setInterests(items);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setInterestError(getErrorMessage(error));
        }
      })
      .finally(() => {
        if (active) {
          setIsLoadingInterests(false);
        }
      });

    return () => {
      active = false;
    };
  }, [accessToken]);

  const activeListings = listings.filter((listing) => listing.status === "active");
  const visibleInterests = useMemo(() => {
    const filtered = interests.filter(
      (interest) => statusFilter === "all" || interest.status === statusFilter,
    );
    if (sortOrder === "move_in") {
      filtered.sort((first, second) =>
        first.expected_move_in_date.localeCompare(second.expected_move_in_date),
      );
    } else if (sortOrder === "newest") {
      filtered.sort((first, second) =>
        second.registered_at.localeCompare(first.registered_at),
      );
    } else if (sortOrder === "budget_high") {
      filtered.sort(
        (first, second) =>
          Number(second.monthly_budget) - Number(first.monthly_budget),
      );
    } else if (sortOrder === "compatibility") {
      filtered.sort(
        (first, second) =>
          second.compatibility_score - first.compatibility_score,
      );
    }
    return filtered;
  }, [interests, sortOrder, statusFilter]);

  async function loadInterests(
    selectedFilters: ReceivedRentalInterestFilters,
  ): Promise<void> {
    setIsLoadingInterests(true);
    setInterestError(null);
    try {
      setInterests(await getReceivedRentalInterests(accessToken, selectedFilters));
    } catch (error: unknown) {
      setInterestError(getErrorMessage(error));
    } finally {
      setIsLoadingInterests(false);
    }
  }

  function startEditingOpportunity(listing: Listing): void {
    const current = opportunities.find(
      (opportunity) => opportunity.listing_id === listing.listing_id,
    );
    const earliestDate =
      listing.date_available >= todayString()
        ? listing.date_available
        : todayString();
    setEditingListingId(listing.listing_id);
    setOpportunityForm({
      availableFrom: current?.available_from ?? earliestDate,
      availableUntil: current?.available_until ?? "",
      availableUnits:
        current?.available_units === null ||
        current?.available_units === undefined
          ? ""
          : String(current.available_units),
      maxActiveRegistrations: String(
        current?.max_active_registrations ?? 50,
      ),
      waitlistEnabled: current?.waitlist_enabled ?? false,
      expectedRentalDurationMonths:
        current?.expected_rental_duration_months === null ||
        current?.expected_rental_duration_months === undefined
          ? ""
          : String(current.expected_rental_duration_months),
    });
    setActionError(null);
    setNotice(null);
  }

  function cancelEditingOpportunity(): void {
    setEditingListingId(null);
    setOpportunityForm(null);
  }

  async function handleSaveOpportunity(
    event: FormEvent<HTMLFormElement>,
    listingId: number,
  ): Promise<void> {
    event.preventDefault();
    if (opportunityForm === null) {
      return;
    }
    setActionError(null);
    setNotice(null);
    setSavingListingId(listingId);
    try {
      const saved = await saveInterestOpportunity(
        accessToken,
        listingId,
        getOpportunityPayload(opportunityForm),
      );
      setOpportunities((items) => [
        ...items.filter((item) => item.opportunity_id !== saved.opportunity_id),
        saved,
      ]);
      setEditingListingId(null);
      setOpportunityForm(null);
      setNotice("Future availability was saved.");
    } catch (error: unknown) {
      setActionError(getErrorMessage(error));
    } finally {
      setSavingListingId(null);
    }
  }

  async function handleCloseOpportunity(
    opportunityId: number,
  ): Promise<void> {
    if (
      !window.confirm(
        "Close this future availability opportunity? Tenants will no longer be able to register.",
      )
    ) {
      return;
    }
    setActionError(null);
    setNotice(null);
    setClosingOpportunityId(opportunityId);
    try {
      const closed = await closeInterestOpportunity(accessToken, opportunityId);
      setOpportunities((items) =>
        items.map((item) =>
          item.opportunity_id === closed.opportunity_id ? closed : item,
        ),
      );
      setNotice("The future availability opportunity was closed.");
    } catch (error: unknown) {
      setActionError(getErrorMessage(error));
    } finally {
      setClosingOpportunityId(null);
    }
  }

  async function handleInterestStatus(
    interestId: number,
    status: "contacted" | "invited_to_apply" | "converted",
  ): Promise<void> {
    setActionError(null);
    setNotice(null);
    setUpdatingInterestId(interestId);
    try {
      const updated = await updateRentalInterestStatus(
        accessToken,
        interestId,
        status,
      );
      setInterests((items) =>
        items.map((item) =>
          item.interest_id === updated.interest_id ? updated : item,
        ),
      );
      setNotice(`Interest status changed to ${statusLabels[status]}.`);
    } catch (error: unknown) {
      setActionError(getErrorMessage(error));
    } finally {
      setUpdatingInterestId(null);
    }
  }

  async function handleApplyFilters(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    await loadInterests(getFilters(filters));
  }

  async function handleClearFilters(): Promise<void> {
    setFilters(emptyFilters);
    setStatusFilter("all");
    setSortOrder("priority");
    await loadInterests({});
  }

  function updateFilter<K extends keyof FilterFormState>(
    key: K,
    value: FilterFormState[K],
  ): void {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <section
      aria-labelledby="landlord-rental-interests-heading"
      className="rental-interest-landlord-panel"
      id="future-interest"
    >
      <div className="rental-interest-section-heading">
        <div>
          <p className="landlord-section-eyebrow">FUTURE AVAILABILITY</p>
          <h2 id="landlord-rental-interests-heading">
            Manage future rental interest
          </h2>
        </div>
        <span className="rental-interest-badge">
          {isLoadingInterests ? "Loading…" : `${interests.length} interests`}
        </span>
      </div>
      <p className="rental-interest-notice">
        Interest registrations are free and do not reserve a room. Updating an
        interest status does not send a message or create a booking.
      </p>

      {actionError !== null && (
        <p className="message message-error" role="alert">
          {actionError}
        </p>
      )}
      {notice !== null && (
        <p className="message message-success" role="status">
          {notice}
        </p>
      )}

      <section
        aria-labelledby="opportunity-management-heading"
        className="rental-interest-subsection"
      >
        <div className="rental-interest-subheading">
          <div>
            <h3 id="opportunity-management-heading">Availability windows</h3>
            <p>
              Only active, approved listings can accept future interest.
              Listings keep their existing availability date and rent.
            </p>
          </div>
        </div>
        {opportunityError !== null && (
          <p className="message message-error" role="alert">
            {opportunityError}
          </p>
        )}
        {isLoadingOpportunities && (
          <p className="rental-interest-inline-state" role="status">
            Loading your opportunities…
          </p>
        )}
        {!isLoadingOpportunities && activeListings.length === 0 && (
          <p className="rental-interest-empty-filter">
            You do not have an active listing yet. Once an approved listing is
            active, you can publish a future availability window here.
          </p>
        )}
        {!isLoadingOpportunities && activeListings.length > 0 && (
          <div className="rental-interest-opportunity-grid">
            {activeListings.map((listing) => {
              const opportunity = opportunities.find(
                (item) => item.listing_id === listing.listing_id,
              );
              const isEditing = editingListingId === listing.listing_id;
              return (
                <article
                  className="rental-interest-opportunity-card"
                  key={listing.listing_id}
                >
                  <div className="rental-interest-card-heading">
                    <div>
                      <h4>{listing.title}</h4>
                      <p>
                        {listing.area_name ?? listing.address} ·{" "}
                        {formatRent(listing.monthly_rent)}/month
                      </p>
                    </div>
                    {opportunity !== undefined && (
                      <span
                        className={`rental-interest-status status-${opportunity.availability_status}`}
                      >
                        {opportunity.availability_status === "open"
                          ? "Open"
                          : opportunity.availability_status === "full"
                            ? "Full"
                            : "Closed"}
                      </span>
                    )}
                  </div>
                  {opportunity !== undefined && (
                    <div className="rental-interest-opportunity-summary">
                      <p>
                        {opportunity.address} · {opportunity.area_name} ·{" "}
                        {formatRent(opportunity.monthly_rent)}/month
                      </p>
                      <p>
                        Expected availability:{" "}
                        {formatDate(opportunity.available_from)}
                        {opportunity.available_until !== null
                          ? ` to ${formatDate(opportunity.available_until)}`
                          : " onward"}
                      </p>
                      <p>
                        {opportunity.active_registration_count} active ·{" "}
                        {opportunity.waitlist_count} waitlisted · limit{" "}
                        {opportunity.max_active_registrations}
                      </p>
                      <p>
                        Waiting-list registration:{" "}
                        {opportunity.waitlist_enabled ? "Enabled" : "Disabled"}
                      </p>
                      {opportunity.expected_rental_duration_months !== null && (
                        <p>
                          Expected rental period:{" "}
                          {opportunity.expected_rental_duration_months} months
                        </p>
                      )}
                    </div>
                  )}
                  {!isEditing && (
                    <div className="rental-interest-actions">
                      <button
                        className="rental-interest-secondary-button"
                        onClick={() => startEditingOpportunity(listing)}
                        type="button"
                      >
                        {opportunity === undefined
                          ? "Set availability"
                          : "Edit availability"}
                      </button>
                      {opportunity?.status === "open" && (
                        <button
                          className="rental-interest-text-button"
                          disabled={closingOpportunityId !== null}
                          onClick={() =>
                            void handleCloseOpportunity(
                              opportunity.opportunity_id,
                            )
                          }
                          type="button"
                        >
                          {closingOpportunityId === opportunity.opportunity_id
                            ? "Closing…"
                            : "Close"}
                        </button>
                      )}
                    </div>
                  )}
                  {isEditing && opportunityForm !== null && (
                    <form
                      className="rental-interest-form"
                      onSubmit={(event) =>
                        void handleSaveOpportunity(event, listing.listing_id)
                      }
                    >
                      <label>
                        Available from
                        <input
                          min={todayString()}
                          onChange={(event) =>
                            setOpportunityForm((current) =>
                              current === null
                                ? current
                                : {
                                    ...current,
                                    availableFrom: event.target.value,
                                  },
                            )
                          }
                          required
                          type="date"
                          value={opportunityForm.availableFrom}
                        />
                      </label>
                      <label>
                        Available until (optional)
                        <input
                          min={opportunityForm.availableFrom || todayString()}
                          onChange={(event) =>
                            setOpportunityForm((current) =>
                              current === null
                                ? current
                                : {
                                    ...current,
                                    availableUntil: event.target.value,
                                  },
                            )
                          }
                          type="date"
                          value={opportunityForm.availableUntil}
                        />
                      </label>
                      <label>
                        Available units (optional)
                        <input
                          max="500"
                          min="1"
                          onChange={(event) =>
                            setOpportunityForm((current) =>
                              current === null
                                ? current
                                : {
                                    ...current,
                                    availableUnits: event.target.value,
                                  },
                            )
                          }
                          placeholder="No unit limit"
                          type="number"
                          value={opportunityForm.availableUnits}
                        />
                      </label>
                      <label>
                        Active registration limit
                        <input
                          max="500"
                          min="1"
                          onChange={(event) =>
                            setOpportunityForm((current) =>
                              current === null
                                ? current
                                : {
                                    ...current,
                                    maxActiveRegistrations: event.target.value,
                                  },
                            )
                          }
                          required
                          type="number"
                          value={opportunityForm.maxActiveRegistrations}
                        />
                      </label>
                      <label>
                        Expected rental duration (months, optional)
                        <input
                          max="60"
                          min="1"
                          onChange={(event) =>
                            setOpportunityForm((current) =>
                              current === null
                                ? current
                                : {
                                    ...current,
                                    expectedRentalDurationMonths:
                                      event.target.value,
                                  },
                            )
                          }
                          type="number"
                          value={
                            opportunityForm.expectedRentalDurationMonths
                          }
                        />
                      </label>
                      <label>
                        <input
                          checked={opportunityForm.waitlistEnabled}
                          onChange={(event) =>
                            setOpportunityForm((current) =>
                              current === null
                                ? current
                                : {
                                    ...current,
                                    waitlistEnabled:
                                      event.currentTarget.checked,
                                  },
                            )
                          }
                          type="checkbox"
                        />
                        Allow waiting list
                      </label>
                      <p className="rental-interest-field-note">
                        When enabled, tenants must explicitly confirm before
                        joining the waiting list. Existing waitlisted tenants
                        remain eligible for priority promotion if a place
                        opens. The capacity cannot be lower than the current
                        active count.
                      </p>
                      <div className="rental-interest-actions">
                        <button
                          className="rental-interest-primary-button"
                          disabled={savingListingId !== null}
                          type="submit"
                        >
                          {savingListingId === listing.listing_id
                            ? "Saving…"
                            : opportunity?.status === "closed"
                              ? "Reopen opportunity"
                              : "Save availability"}
                        </button>
                        <button
                          className="rental-interest-text-button"
                          onClick={cancelEditingOpportunity}
                          type="button"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section
        aria-labelledby="received-rental-interests-heading"
        className="rental-interest-subsection"
      >
        <div className="rental-interest-subheading">
          <div>
            <h3 id="received-rental-interests-heading">
              Tenant registrations
            </h3>
            <p>
              Sorted by the platform priority: status, preference fit,
              availability date, then registration time.
            </p>
          </div>
          <label className="rental-interest-sort-control">
            Sort
            <select
              onChange={(event) => setSortOrder(event.target.value)}
              value={sortOrder}
            >
              <option value="priority">Recommended priority</option>
              <option value="compatibility">Compatibility score</option>
              <option value="move_in">Move-in date</option>
              <option value="newest">Newest registration</option>
              <option value="budget_high">Budget: high to low</option>
            </select>
          </label>
        </div>
        <form className="rental-interest-filter-form" onSubmit={handleApplyFilters}>
          <label>
            Opportunity
            <select
              onChange={(event) =>
                updateFilter("opportunityId", event.target.value)
              }
              value={filters.opportunityId}
            >
              <option value="">All opportunities</option>
              {opportunities.map((opportunity) => (
                <option
                  key={opportunity.opportunity_id}
                  value={opportunity.opportunity_id}
                >
                  {opportunity.listing_title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Move-in from
            <input
              onChange={(event) =>
                updateFilter("moveInFrom", event.target.value)
              }
              type="date"
              value={filters.moveInFrom}
            />
          </label>
          <label>
            Move-in until
            <input
              onChange={(event) =>
                updateFilter("moveInUntil", event.target.value)
              }
              type="date"
              value={filters.moveInUntil}
            />
          </label>
          <label>
            Minimum budget (R)
            <input
              min="0.01"
              onChange={(event) =>
                updateFilter("minimumBudget", event.target.value)
              }
              step="0.01"
              type="number"
              value={filters.minimumBudget}
            />
          </label>
          <label>
            Maximum budget (R)
            <input
              min="0.01"
              onChange={(event) =>
                updateFilter("maximumBudget", event.target.value)
              }
              step="0.01"
              type="number"
              value={filters.maximumBudget}
            />
          </label>
          <label>
            Preferred room type
            <select
              onChange={(event) =>
                updateFilter("preferredRoomType", event.target.value)
              }
              value={filters.preferredRoomType}
            >
              <option value="">Any room type</option>
              {roomTypes.map((roomType) => (
                <option key={roomType.value} value={roomType.value}>
                  {roomType.label}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="rental-interest-amenities">
            <legend>Required amenities</legend>
            {amenityOptions.map((amenity) => (
              <label key={amenity}>
                <input
                  checked={filters.requiredAmenities.includes(amenity)}
                  onChange={(event) => {
                    const selected = new Set(filters.requiredAmenities);
                    if (event.currentTarget.checked) {
                      selected.add(amenity);
                    } else {
                      selected.delete(amenity);
                    }
                    updateFilter("requiredAmenities", Array.from(selected));
                  }}
                  type="checkbox"
                />
                {amenity}
              </label>
            ))}
          </fieldset>
          <div className="rental-interest-filter-actions">
            <label>
              Status
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
            <button
              className="rental-interest-primary-button"
              disabled={isLoadingInterests}
              type="submit"
            >
              Apply filters
            </button>
            <button
              className="rental-interest-secondary-button"
              disabled={isLoadingInterests}
              onClick={() => void handleClearFilters()}
              type="button"
            >
              Clear
            </button>
          </div>
        </form>

        {interestError !== null && (
          <p className="message message-error" role="alert">
            {interestError}
          </p>
        )}
        {isLoadingInterests && (
          <p className="rental-interest-inline-state" role="status">
            Loading tenant registrations…
          </p>
        )}
        {!isLoadingInterests &&
          interestError === null &&
          visibleInterests.length === 0 && (
            <p className="rental-interest-empty-filter">
              No tenant registrations match the selected filters.
            </p>
          )}
        {!isLoadingInterests && visibleInterests.length > 0 && (
          <ul className="rental-interest-list">
            {visibleInterests.map((interest) => {
              const opportunity = opportunities.find(
                (item) =>
                  item.opportunity_id === interest.opportunity.opportunity_id,
              );
              const canUpdate =
                opportunity?.status === "open" &&
                (interest.status === "active" ||
                  interest.status === "contacted" ||
                  interest.status === "invited_to_apply");
              return (
                <li className="rental-interest-card" key={interest.interest_id}>
                  <div className="rental-interest-card-heading">
                    <div>
                      <h4>{interest.tenant_name}</h4>
                      <p>
                        {interest.opportunity.listing_title} ·{" "}
                        {interest.opportunity.area_name}
                      </p>
                    </div>
                    <span
                      className={`rental-interest-status status-${interest.status}`}
                    >
                      {statusLabels[interest.status]}
                    </span>
                  </div>
                  <dl className="rental-interest-facts">
                    <div>
                      <dt>Move-in date</dt>
                      <dd>{formatDate(interest.expected_move_in_date)}</dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>{interest.expected_duration_months} months</dd>
                    </div>
                    <div>
                      <dt>Monthly budget</dt>
                      <dd>{formatRent(interest.monthly_budget)}</dd>
                    </div>
                    <div>
                      <dt>Compatibility</dt>
                      <dd>{interest.compatibility_score}/100</dd>
                    </div>
                    <div>
                      <dt>Registered</dt>
                      <dd>{formatDateTime(interest.registered_at)}</dd>
                    </div>
                  </dl>
                  <div className="rental-interest-reasons">
                    <strong>Priority details</strong>
                    {interest.compatibility_reasons.length > 0 ? (
                      <ul>
                        {interest.compatibility_reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>No additional preference matches were recorded.</p>
                    )}
                  </div>
                  {interest.required_amenities.length > 0 && (
                    <p className="rental-interest-preferences">
                      Required amenities:{" "}
                      {interest.required_amenities.join(", ")}
                    </p>
                  )}
                  {interest.status === "waitlisted" && (
                    <p className="rental-interest-status-description">
                      This registration is waitlisted and does not occupy an
                      active place.
                    </p>
                  )}
                  <div className="rental-interest-actions">
                    {canUpdate && interest.status === "active" && (
                      <>
                        <button
                          className="rental-interest-secondary-button"
                          disabled={updatingInterestId !== null}
                          onClick={() =>
                            void handleInterestStatus(
                              interest.interest_id,
                              "contacted",
                            )
                          }
                          type="button"
                        >
                          Mark contacted
                        </button>
                        <button
                          className="rental-interest-primary-button"
                          disabled={updatingInterestId !== null}
                          onClick={() =>
                            void handleInterestStatus(
                              interest.interest_id,
                              "invited_to_apply",
                            )
                          }
                          type="button"
                        >
                          Invite to apply
                        </button>
                      </>
                    )}
                    {canUpdate && interest.status === "contacted" && (
                      <button
                        className="rental-interest-primary-button"
                        disabled={updatingInterestId !== null}
                        onClick={() =>
                          void handleInterestStatus(
                            interest.interest_id,
                            "invited_to_apply",
                          )
                        }
                        type="button"
                      >
                        Invite to apply
                      </button>
                    )}
                    {canUpdate && interest.status === "invited_to_apply" && (
                      <button
                        className="rental-interest-primary-button"
                        disabled={updatingInterestId !== null}
                        onClick={() =>
                          void handleInterestStatus(
                            interest.interest_id,
                            "converted",
                          )
                        }
                        type="button"
                      >
                        Mark converted
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </section>
  );
}
