import { useEffect, useState } from "react";
import type { FormEvent, ChangeEvent } from "react";

import {
  createListing,
  getAreas,
  getMyListings,
  submitListing,
  updateListing,
  uploadListingPhoto,
  withdrawListing,
  type UserProfile,
} from "../api";
import type {
  Area,
  Listing,
  ListingCreateRequest,
} from "../types/listing";
import "./LandlordDashboardPage.css";

type LandlordDashboardPageProps = {
  accessToken: string;
  profile: UserProfile;
  onSignOut: () => void;
};

type ListingFormFields = {
  areaId: string;
  title: string;
  description: string;
  roomType: ListingCreateRequest["room_type"] | "";
  monthlyRent: string;
  depositAmount: string;
  address: string;
  dateAvailable: string;
};

const emptyForm: ListingFormFields = {
  areaId: "",
  title: "",
  description: "",
  roomType: "",
  monthlyRent: "",
  depositAmount: "",
  address: "",
  dateAvailable: "",
};

const roomTypes: Array<{
  value: ListingCreateRequest["room_type"];
  label: string;
}> = [
  { value: "single_room", label: "Single room" },
  { value: "shared_room", label: "Shared room" },
  { value: "bachelor_flat", label: "Bachelor flat" },
  { value: "self_contained", label: "Self-contained" },
];

function isRoomType(value: string): value is ListingCreateRequest["room_type"] {
  return roomTypes.some((roomType) => roomType.value === value);
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The request could not be completed. Please try again.";
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "draft":
      return "Draft";
    case "pending":
      return "Awaiting moderation";
    case "active":
      return "Active";
    case "closed":
      return "Closed";
    default:
      return status;
  }
}

export default function LandlordDashboardPage({
  accessToken,
  profile,
  onSignOut,
}: LandlordDashboardPageProps) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [form, setForm] = useState<ListingFormFields>(emptyForm);
  const [editingListingId, setEditingListingId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  async function refreshListings(): Promise<void> {
    setListings(await getMyListings(accessToken));
  }

  useEffect(() => {
    let active = true;

    async function loadDashboard(): Promise<void> {
      try {
        const [myListings, availableAreas] = await Promise.all([
          getMyListings(accessToken),
          getAreas(),
        ]);
        if (active) {
          setListings(myListings);
          setAreas(availableAreas);
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

  function updateField(
    field: keyof ListingFormFields,
    value: string,
  ): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEditing(listing: Listing): void {
    setEditingListingId(listing.listing_id);
    setForm({
      areaId: String(listing.area_id),
      title: listing.title,
      description: listing.description,
      roomType: isRoomType(listing.room_type) ? listing.room_type : "",
      monthlyRent: String(listing.monthly_rent),
      depositAmount: String(listing.deposit_amount),
      address: listing.address,
      dateAvailable: listing.date_available,
    });
    setErrorMessage(null);
    setNotice(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEditing(): void {
    setEditingListingId(null);
    setForm(emptyForm);
    setErrorMessage(null);
    setNotice(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isRoomType(form.roomType)) {
      setErrorMessage("Choose a valid room type.");
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setNotice(null);

    const payload: ListingCreateRequest = {
      area_id: Number(form.areaId),
      title: form.title,
      description: form.description,
      room_type: form.roomType,
      monthly_rent: form.monthlyRent,
      deposit_amount: form.depositAmount,
      address: form.address,
      date_available: form.dateAvailable,
    };

    try {
      if (editingListingId === null) {
        await createListing(accessToken, payload);
        setNotice("Your listing was saved as a draft.");
      } else {
        await updateListing(accessToken, editingListingId, payload);
        setNotice("Your changes were saved as a draft.");
      }
      setEditingListingId(null);
      setForm(emptyForm);
      await refreshListings();
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleListingAction(
    listingId: number,
    action: (token: string, id: number) => Promise<Listing>,
    successMessage: string,
  ): Promise<void> {
    setErrorMessage(null);
    setNotice(null);
    try {
      await action(accessToken, listingId);
      setNotice(successMessage);
      await refreshListings();
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    }
  }

  async function handlePhotoSelected(
    listingId: number,
    event: ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (file === undefined) {
      return;
    }

    setErrorMessage(null);
    setNotice(null);
    try {
      await uploadListingPhoto(accessToken, listingId, file);
      setNotice("The photo was uploaded.");
      await refreshListings();
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      input.value = "";
    }
  }

  const areaNames = new Map(areas.map((area) => [area.area_id, area.name]));

  return (
    <main className="page-shell landlord-page">
      <section className="landlord-dashboard">
        <header className="landlord-header">
          <div>
            <p className="eyebrow">Room Rentals</p>
            <h1>Your landlord dashboard</h1>
            <p className="intro">Welcome, {profile.full_name}.</p>
          </div>
          <button
            className="secondary-button landlord-signout"
            onClick={onSignOut}
            type="button"
          >
            Sign out
          </button>
        </header>

        <p className="landlord-moderation-note">
          New listings and edits stay private while they await admin
          moderation. Approved listings can then appear in public room search.
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
          className="landlord-panel"
          aria-labelledby="listing-form-heading"
        >
          <h2 id="listing-form-heading">
            {editingListingId === null ? "Create a listing" : "Edit listing"}
          </h2>
          <form className="landlord-form" onSubmit={handleSubmit}>
            <label>
              Listing title
              <input
                maxLength={150}
                onChange={(event) => updateField("title", event.target.value)}
                required
                value={form.title}
              />
            </label>
            <label>
              Description
              <textarea
                onChange={(event) =>
                  updateField("description", event.target.value)
                }
                required
                rows={4}
                value={form.description}
              />
            </label>
            <div className="landlord-form-grid">
              <label>
                Area
                <select
                  onChange={(event) => updateField("areaId", event.target.value)}
                  required
                  value={form.areaId}
                >
                  <option value="">Choose an area</option>
                  {areas.map((area) => (
                    <option key={area.area_id} value={area.area_id}>
                      {area.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Room type
                <select
                  onChange={(event) =>
                    updateField("roomType", event.target.value)
                  }
                  required
                  value={form.roomType}
                >
                  <option value="">Choose a room type</option>
                  {roomTypes.map((roomType) => (
                    <option key={roomType.value} value={roomType.value}>
                      {roomType.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Monthly rent (R)
                <input
                  min="0.01"
                  onChange={(event) =>
                    updateField("monthlyRent", event.target.value)
                  }
                  required
                  step="0.01"
                  type="number"
                  value={form.monthlyRent}
                />
              </label>
              <label>
                Deposit (R)
                <input
                  min="0"
                  onChange={(event) =>
                    updateField("depositAmount", event.target.value)
                  }
                  required
                  step="0.01"
                  type="number"
                  value={form.depositAmount}
                />
              </label>
              <label>
                Address
                <input
                  maxLength={255}
                  onChange={(event) => updateField("address", event.target.value)}
                  required
                  value={form.address}
                />
              </label>
              <label>
                Available from
                <input
                  onChange={(event) =>
                    updateField("dateAvailable", event.target.value)
                  }
                  required
                  type="date"
                  value={form.dateAvailable}
                />
              </label>
            </div>
            <div className="landlord-form-actions">
              <button
                className="primary-button landlord-form-submit"
                disabled={isSaving || areas.length === 0}
                type="submit"
              >
                {isSaving
                  ? "Saving..."
                  : editingListingId === null
                    ? "Save draft"
                    : "Save changes"}
              </button>
              {editingListingId !== null && (
                <button
                  className="secondary-button"
                  disabled={isSaving}
                  onClick={cancelEditing}
                  type="button"
                >
                  Cancel editing
                </button>
              )}
            </div>
          </form>
        </section>

        <section
          className="landlord-panel"
          aria-labelledby="my-listings-heading"
        >
          <div className="landlord-listings-heading">
            <h2 id="my-listings-heading">Your listings</h2>
            <button
              className="secondary-button"
              disabled={isLoading}
              onClick={() => {
                setIsLoading(true);
                void Promise.all([refreshListings(), getAreas()])
                  .then(([, availableAreas]) => setAreas(availableAreas))
                  .catch((error: unknown) =>
                    setErrorMessage(getErrorMessage(error)),
                  )
                  .finally(() => setIsLoading(false));
              }}
              type="button"
            >
              Refresh
            </button>
          </div>

          {isLoading && <p role="status">Loading your listings...</p>}
          {!isLoading && listings.length === 0 && (
            <p className="landlord-empty-state">
              You do not have any listings yet. Use the form above to create
              your first draft.
            </p>
          )}
          {!isLoading && listings.length > 0 && (
            <ul className="landlord-list">
              {listings.map((listing) => (
                <li className="landlord-listing" key={listing.listing_id}>
                  <div className="landlord-listing-header">
                    <div>
                      <h3>{listing.title}</h3>
                      <p>
                        {areaNames.get(listing.area_id) ?? "Area unavailable"}
                        {" · "}
                        {listing.room_type.replaceAll("_", " ")}
                      </p>
                    </div>
                    <span className={`listing-status status-${listing.status}`}>
                      {getStatusLabel(listing.status)}
                    </span>
                  </div>
                  <p className="landlord-listing-summary">
                    R {Number(listing.monthly_rent).toLocaleString("en-ZA")} /
                    month · Available {listing.date_available}
                  </p>
                  {listing.photos.length > 0 && (
                    <div className="landlord-photo-list">
                      {listing.photos.map((photo) => (
                        <img
                          alt={`Room photo for ${listing.title}`}
                          key={photo.photo_id}
                          src={photo.url}
                        />
                      ))}
                    </div>
                  )}
                  <div className="landlord-listing-actions">
                    {listing.status !== "closed" && (
                      <>
                        <button
                          className="secondary-button"
                          onClick={() => startEditing(listing)}
                          type="button"
                        >
                          Edit
                        </button>
                        {listing.status === "draft" && (
                          <button
                            className="secondary-button"
                            onClick={() =>
                              void handleListingAction(
                                listing.listing_id,
                                submitListing,
                                "Your listing was submitted for moderation.",
                              )
                            }
                            type="button"
                          >
                            Submit for review
                          </button>
                        )}
                        <label className="photo-upload-button">
                          Add photo
                          <input
                            accept="image/jpeg,image/png,image/webp"
                            onChange={(event) =>
                              void handlePhotoSelected(listing.listing_id, event)
                            }
                            type="file"
                          />
                        </label>
                        <button
                          className="secondary-button danger-button"
                          onClick={() =>
                            void handleListingAction(
                              listing.listing_id,
                              withdrawListing,
                              "Your listing was closed.",
                            )
                          }
                          type="button"
                        >
                          Withdraw
                        </button>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <footer className="landlord-footer">
          <a href="/">Browse public rooms</a>
        </footer>
      </section>
    </main>
  );
}
