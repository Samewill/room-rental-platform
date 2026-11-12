import { useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  createRentalInterest,
  type InterestOpportunity,
  type RentalInterest,
  type RentalInterestRoomType,
} from "../api";
import type { Amenity } from "../types/listing";

type RentalInterestRegistrationFormProps = {
  accessToken: string;
  amenities: Amenity[];
  opportunity: InterestOpportunity;
  onRegistered: (interest: RentalInterest) => void;
};

const roomTypes: Array<{ value: RentalInterestRoomType; label: string }> = [
  { value: "single_room", label: "Single room" },
  { value: "shared_room", label: "Shared room" },
  { value: "bachelor_flat", label: "Bachelor flat" },
  { value: "self_contained", label: "Self-contained" },
];

function todayString(): string {
  const now = new Date();
  const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}

export default function RentalInterestRegistrationForm({
  accessToken,
  amenities,
  opportunity,
  onRegistered,
}: RentalInterestRegistrationFormProps) {
  const today = todayString();
  const minimumMoveInDate =
    opportunity.available_from > today ? opportunity.available_from : today;
  const [expectedMoveInDate, setExpectedMoveInDate] =
    useState(minimumMoveInDate);
  const [expectedDurationMonths, setExpectedDurationMonths] = useState(
    String(opportunity.expected_rental_duration_months ?? 12),
  );
  const [monthlyBudget, setMonthlyBudget] = useState("");
  const [preferredRoomType, setPreferredRoomType] = useState("");
  const [requiredAmenities, setRequiredAmenities] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [waitlistConsentRequired, setWaitlistConsentRequired] =
    useState(false);

  function updateAmenity(amenity: string, checked: boolean): void {
    setRequiredAmenities((current) => {
      const selected = new Set(current);
      if (checked) {
        selected.add(amenity);
      } else {
        selected.delete(amenity);
      }
      return Array.from(selected);
    });
  }

  async function submitRegistration(joinWaitlist: boolean): Promise<void> {
    setError(null);
    setIsSubmitting(true);
    try {
      const interest = await createRentalInterest(
        accessToken,
        opportunity.opportunity_id,
        {
          expected_move_in_date: expectedMoveInDate,
          expected_duration_months: Number(expectedDurationMonths),
          monthly_budget: Number(monthlyBudget),
          ...(preferredRoomType === ""
            ? {}
            : {
                preferred_room_type:
                  preferredRoomType as RentalInterestRoomType,
              }),
          required_amenities: requiredAmenities,
          join_waitlist: joinWaitlist,
        },
      );
      onRegistered(interest);
    } catch (requestError: unknown) {
      if (
        requestError instanceof ApiError &&
        requestError.code === "waitlist_consent_required"
      ) {
        setWaitlistConsentRequired(true);
      } else if (
        requestError instanceof ApiError &&
        requestError.code === "capacity_full"
      ) {
        setWaitlistConsentRequired(false);
        setError(
          "This opportunity is full, and the landlord is not accepting waiting-list registrations. No registration was created.",
        );
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Your interest could not be registered.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void submitRegistration(false);
  }

  return (
    <form
      className="rental-interest-form"
      onSubmit={handleSubmit}
    >
      <label>
        Expected move-in date
        <input
          max={opportunity.available_until ?? undefined}
          min={minimumMoveInDate}
          onChange={(event) => setExpectedMoveInDate(event.target.value)}
          required
          type="date"
          value={expectedMoveInDate}
        />
      </label>
      <label>
        Expected rental duration (months)
        <input
          max="60"
          min="1"
          onChange={(event) => setExpectedDurationMonths(event.target.value)}
          required
          type="number"
          value={expectedDurationMonths}
        />
      </label>
      <label>
        Monthly budget (R)
        <input
          min="0.01"
          onChange={(event) => setMonthlyBudget(event.target.value)}
          required
          step="0.01"
          type="number"
          value={monthlyBudget}
        />
      </label>
      <label>
        Preferred room type (optional)
        <select
          onChange={(event) => setPreferredRoomType(event.target.value)}
          value={preferredRoomType}
        >
          <option value="">No preference</option>
          {roomTypes.map((roomType) => (
            <option key={roomType.value} value={roomType.value}>
              {roomType.label}
            </option>
          ))}
        </select>
      </label>
      {amenities.length > 0 && (
        <fieldset className="rental-interest-amenities">
          <legend>Required amenities (optional, up to 4)</legend>
          {amenities.map((amenity) => (
            <label key={amenity.amenity_id}>
              <input
                checked={requiredAmenities.includes(amenity.name)}
                disabled={
                  requiredAmenities.length >= 4 &&
                  !requiredAmenities.includes(amenity.name)
                }
                onChange={(event) =>
                  updateAmenity(amenity.name, event.currentTarget.checked)
                }
                type="checkbox"
              />
              {amenity.name}
            </label>
          ))}
        </fieldset>
      )}
      {error !== null && (
        <p className="message message-error" role="alert">
          {error}
        </p>
      )}
      {waitlistConsentRequired ? (
        <div className="rental-interest-consent" role="status">
          <p>
            This opportunity is full. Joining the waiting list records your
            interest only; it does not reserve a room or guarantee
            accommodation.
          </p>
          <div className="rental-interest-actions">
            <button
              className="rental-interest-primary-button"
              disabled={isSubmitting}
              onClick={() => void submitRegistration(true)}
              type="button"
            >
              {isSubmitting ? "Joining…" : "Confirm and join waitlist"}
            </button>
            <button
              className="rental-interest-text-button"
              disabled={isSubmitting}
              onClick={() => setWaitlistConsentRequired(false)}
              type="button"
            >
              No, cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          className="rental-interest-primary-button"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Registering…" : "Submit registration"}
        </button>
      )}
    </form>
  );
}
