import { useEffect, useState } from "react";

import {
  getAmenities,
  getMyRentalInterests,
  getPublicInterestOpportunities,
  type InterestOpportunity,
  type RentalInterest,
  type RentalInterestStatus,
} from "../api";
import type { Amenity } from "../types/listing";
import RentalInterestRegistrationForm from "./RentalInterestRegistrationForm";
import "./RentalInterestPanels.css";

type TenantFutureRentalOpportunitiesPanelProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
  onRegistered: () => void;
};

const activeStatuses: RentalInterestStatus[] = [
  "active",
  "waitlisted",
  "contacted",
  "invited_to_apply",
];

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(date);
}

function formatRent(value: string | number): string {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat("en-ZA", {
        style: "currency",
        currency: "ZAR",
        maximumFractionDigits: 0,
      }).format(amount)
    : "Rent unavailable";
}

export default function TenantFutureRentalOpportunitiesPanel({
  accessToken,
  onNavigate,
  onRegistered,
}: TenantFutureRentalOpportunitiesPanelProps) {
  const [opportunities, setOpportunities] = useState<
    InterestOpportunity[]
  >([]);
  const [amenities, setAmenities] = useState<Amenity[]>([]);
  const [interests, setInterests] = useState<RentalInterest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [selectedOpportunity, setSelectedOpportunity] =
    useState<InterestOpportunity | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setLoadError(null);

    async function load(): Promise<void> {
      try {
        const [publicOpportunities, availableAmenities, tenantInterests] =
          await Promise.all([
            getPublicInterestOpportunities(),
            getAmenities(),
            getMyRentalInterests(accessToken),
          ]);
        if (active) {
          setOpportunities(publicOpportunities);
          setAmenities(availableAmenities);
          setInterests(tenantInterests);
        }
      } catch (error: unknown) {
        if (active) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Future availability could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [accessToken]);

  function toggleRegistrationForm(
    opportunity: InterestOpportunity,
  ): void {
    setActionNotice(null);
    if (selectedOpportunity?.opportunity_id === opportunity.opportunity_id) {
      setSelectedOpportunity(null);
      return;
    }
    setSelectedOpportunity(opportunity);
  }

  return (
    <section
      aria-labelledby="tenant-future-opportunities-heading"
      className="tenant-rental-opportunities-panel"
    >
      <div className="rental-interest-section-heading">
        <div>
          <p className="rental-interest-eyebrow">PLAN YOUR NEXT MOVE</p>
          <h2 id="tenant-future-opportunities-heading">
            Register future rental interest
          </h2>
        </div>
      </div>
      <p className="rental-interest-notice">
        Registration is free. It records your interest only; it does not
        reserve a room, guarantee a response, or create a rental agreement.
      </p>
      {isLoading && (
        <p className="rental-interest-inline-state" role="status">
          Loading rooms with future availability…
        </p>
      )}
      {loadError !== null && (
        <p className="message message-error" role="alert">
          Future availability could not be loaded: {loadError}
        </p>
      )}
      {actionNotice !== null && (
        <p className="message message-success" role="status">
          {actionNotice}
        </p>
      )}
      {!isLoading && loadError === null && opportunities.length === 0 && (
        <p className="rental-interest-empty-filter">
          There are no rooms open for future-interest registration right now.
        </p>
      )}
      {!isLoading && opportunities.length > 0 && (
        <ul className="rental-interest-opportunity-grid">
          {opportunities.map((opportunity) => {
            const existingInterest = interests.find(
              (interest) =>
                interest.opportunity.opportunity_id ===
                  opportunity.opportunity_id &&
                activeStatuses.includes(interest.status),
            );
            const isSelected =
              selectedOpportunity?.opportunity_id === opportunity.opportunity_id;
            return (
              <li
                className="rental-interest-opportunity-card"
                key={opportunity.opportunity_id}
              >
                <div className="rental-interest-card-heading">
                  <div>
                    <h3>{opportunity.listing_title}</h3>
                    <p>
                      {opportunity.area_name} ·{" "}
                      {formatRent(opportunity.monthly_rent)}/month
                    </p>
                  </div>
                  <div className="rental-interest-status-group">
                    <span
                      className={`rental-interest-status status-${opportunity.availability_status}`}
                    >
                      {opportunity.availability_status === "open"
                        ? "Open"
                        : opportunity.availability_status === "full"
                          ? "Full"
                          : "Closed"}
                    </span>
                    {existingInterest !== undefined && (
                      <span
                        className={`rental-interest-status status-${existingInterest.status}`}
                      >
                        {existingInterest.status === "waitlisted"
                          ? "Waitlisted"
                          : "Registered"}
                      </span>
                    )}
                  </div>
                </div>
                <div className="rental-interest-opportunity-summary">
                  <p>
                    {opportunity.room_type.replaceAll("_", " ")} ·{" "}
                    {opportunity.address} · {opportunity.area_name} ·{" "}
                    {formatRent(opportunity.monthly_rent)}/month
                  </p>
                  <p>
                    Expected availability: {formatDate(opportunity.available_from)}
                    {opportunity.available_until !== null
                      ? ` to ${formatDate(opportunity.available_until)}`
                      : ""}
                  </p>
                  {opportunity.expected_rental_duration_months !== null && (
                    <p>
                      Expected rental period:{" "}
                      {opportunity.expected_rental_duration_months} months
                    </p>
                  )}
                  <p>
                    Units available:{" "}
                    {opportunity.available_units ?? "Not specified"}
                  </p>
                  <p>
                    Active registration capacity:{" "}
                    {opportunity.active_registration_count}/
                    {opportunity.max_active_registrations}
                    {opportunity.waitlist_count > 0
                      ? ` · ${opportunity.waitlist_count} waitlisted`
                      : ""}
                  </p>
                  {opportunity.availability_status === "full" && (
                    <p>
                      Registration capacity is full.
                      {opportunity.waitlist_enabled
                        ? " You can submit your details, then explicitly confirm if you want to join the waiting list."
                        : " Waiting-list registration is unavailable."}
                    </p>
                  )}
                  {opportunity.availability_status === "closed" && (
                    <p>This opportunity is closed to new registrations.</p>
                  )}
                  {opportunity.amenities.length > 0 && (
                    <p>Amenities: {opportunity.amenities.join(", ")}</p>
                  )}
                </div>
                {existingInterest === undefined &&
                  opportunity.availability_status !== "closed" &&
                  (opportunity.availability_status === "open" ||
                    opportunity.waitlist_enabled) && (
                  <button
                    className="rental-interest-primary-button"
                    onClick={() => toggleRegistrationForm(opportunity)}
                    type="button"
                  >
                    {isSelected
                      ? "Cancel"
                      : "Register free interest"}
                  </button>
                )}
                {isSelected && opportunity.availability_status !== "closed" && (
                  <RentalInterestRegistrationForm
                    accessToken={accessToken}
                    amenities={amenities}
                    key={opportunity.opportunity_id}
                    onRegistered={(interest) => {
                      setInterests((current) => [interest, ...current]);
                      setSelectedOpportunity(null);
                      onRegistered();
                      setActionNotice(
                        `Your interest in ${opportunity.listing_title} was registered.`,
                      );
                    }}
                    opportunity={opportunity}
                  />
                )}
                <button
                  className="rental-interest-text-button"
                  onClick={() =>
                    onNavigate(`/listings/${opportunity.listing_id}`)
                  }
                  type="button"
                >
                  View room
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
