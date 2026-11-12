import { useEffect, useState } from "react";
import type { FormEvent, ChangeEvent } from "react";

import {
  createListing,
  getAmenities,
  getAreas,
  getReceivedContactRequests,
  getMyListings,
  respondToContactRequest,
  submitListing,
  resolveArea,
  updateListing,
  uploadListingPhoto,
  withdrawListing,
  type ContactRequest,
  type UserProfile,
} from "../api";
import AppLink from "../components/AppLink";
import GoogleAddressSearch, {
  type GoogleAddressSelection,
} from "../components/GoogleAddressSearch";
import LandlordRentalInterestsPanel from "../components/LandlordRentalInterestsPanel";
import RentalInterestNotificationsPanel from "../components/RentalInterestNotificationsPanel";
import RoomMap, { type MapPoint } from "../components/RoomMap";
import type {
  Amenity,
  Area,
  Listing,
  ListingCreateRequest,
} from "../types/listing";
import "./LandlordDashboardPage.css";

type LandlordDashboardPageProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
  profile: UserProfile;
  onSignOut: () => void;
};

type ListingFormFields = {
  areaName: string;
  title: string;
  description: string;
  roomType: ListingCreateRequest["room_type"] | "";
  monthlyRent: string;
  depositAmount: string;
  address: string;
  googlePlaceId: string | null;
  latitude: number | null;
  longitude: number | null;
  dateAvailable: string;
  amenities: string[];
};

const emptyForm: ListingFormFields = {
  areaName: "",
  title: "",
  description: "",
  roomType: "",
  monthlyRent: "",
  depositAmount: "",
  address: "",
  googlePlaceId: null,
  latitude: null,
  longitude: null,
  dateAvailable: "",
  amenities: [],
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

export default function LandlordDashboardPage({
  accessToken,
  onNavigate,
  profile,
  onSignOut,
}: LandlordDashboardPageProps) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [contactRequests, setContactRequests] = useState<ContactRequest[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [areaSuggestions, setAreaSuggestions] = useState<Area[]>([]);
  const [areaSearchError, setAreaSearchError] = useState<string | null>(null);
  const [amenities, setAmenities] = useState<Amenity[]>([]);
  const [form, setForm] = useState<ListingFormFields>(emptyForm);
  const [mapSearchAddress, setMapSearchAddress] = useState("");
  const [editingListingId, setEditingListingId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingContactRequests, setIsLoadingContactRequests] =
    useState(true);
  const [listingSearch, setListingSearch] = useState("");
  const [contactRequestError, setContactRequestError] = useState<
    string | null
  >(null);
  const [contactRequestNotice, setContactRequestNotice] = useState<
    string | null
  >(null);
  const [updatingContactRequestId, setUpdatingContactRequestId] = useState<
    number | null
  >(null);

  async function refreshListings(): Promise<void> {
    setListings(await getMyListings(accessToken));
  }

  useEffect(() => {
    const query = form.areaName.trim();
    if (query.length < 2) {
      setAreaSuggestions([]);
      setAreaSearchError(null);
      return;
    }

    let active = true;
    const timeout = window.setTimeout(() => {
      void getAreas(query)
        .then((matches) => {
          if (active) {
            setAreaSuggestions(matches);
            setAreaSearchError(null);
          }
        })
        .catch((error: unknown) => {
          if (active) {
            setAreaSearchError(getErrorMessage(error));
          }
        });
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [form.areaName]);

  useEffect(() => {
    let active = true;

    async function loadDashboard(): Promise<void> {
      try {
        const [myListings, availableAmenities] = await Promise.all([
          getMyListings(accessToken),
          getAmenities(),
        ]);
        if (active) {
          setListings(myListings);
          setAmenities(availableAmenities);
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

  useEffect(() => {
    let active = true;

    async function loadContactRequests(): Promise<void> {
      try {
        const requests = await getReceivedContactRequests(accessToken);
        if (active) {
          setContactRequests(requests);
          setContactRequestError(null);
        }
      } catch (error: unknown) {
        if (active) {
          setContactRequestError(getErrorMessage(error));
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
  }, [accessToken]);

  async function refreshContactRequests(): Promise<void> {
    setIsLoadingContactRequests(true);
    setContactRequestError(null);
    try {
      setContactRequests(await getReceivedContactRequests(accessToken));
    } catch (error: unknown) {
      setContactRequestError(getErrorMessage(error));
    } finally {
      setIsLoadingContactRequests(false);
    }
  }

  async function handleContactRequestDecision(
    requestId: number,
    decision: "approved" | "rejected",
  ): Promise<void> {
    setContactRequestError(null);
    setContactRequestNotice(null);
    setUpdatingContactRequestId(requestId);
    try {
      const updatedRequest = await respondToContactRequest(
        accessToken,
        requestId,
        decision,
      );
      setContactRequests((requests) =>
        requests.map((request) =>
          request.request_id === updatedRequest.request_id
            ? updatedRequest
            : request,
        ),
      );
      setContactRequestNotice(
        decision === "approved"
          ? "Contact request approved."
          : "Contact request rejected.",
      );
    } catch (error: unknown) {
      setContactRequestError(getErrorMessage(error));
    } finally {
      setUpdatingContactRequestId(null);
    }
  }

  function updateField(
    field: keyof ListingFormFields,
    value: string,
  ): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateAddress(value: string): void {
    setMapSearchAddress(value);
    setForm((current) => ({
      ...current,
      address: value,
      googlePlaceId: null,
      ...(value === current.address
        ? {}
        : {
            latitude: null,
            longitude: null,
          }),
    }));
  }

  function selectAddress(result: GoogleAddressSelection): void {
    setMapSearchAddress(result.displayAddress ?? result.address);
    setForm((current) => ({
      ...current,
      address: result.address,
      googlePlaceId: result.placeId,
      latitude: result.latitude,
      longitude: result.longitude,
    }));
  }

  function updateMapPoint(point: MapPoint): void {
    setForm((current) => ({
      ...current,
      googlePlaceId: null,
      latitude: point.latitude,
      longitude: point.longitude,
    }));
  }

  function startEditing(listing: Listing): void {
    setMapSearchAddress(listing.address);
    setEditingListingId(listing.listing_id);
    setForm({
      areaName:
        listing.area_name ??
        areas.find((area) => area.area_id === listing.area_id)?.name ??
        "",
      title: listing.title,
      description: listing.description,
      roomType: isRoomType(listing.room_type) ? listing.room_type : "",
      monthlyRent: String(listing.monthly_rent),
      depositAmount: String(listing.deposit_amount),
      address: listing.address,
      googlePlaceId: listing.google_place_id ?? null,
      latitude: listing.latitude ?? null,
      longitude: listing.longitude ?? null,
      dateAvailable: listing.date_available,
      amenities: [...listing.amenities],
    });
    setErrorMessage(null);
    setNotice(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEditing(): void {
    setMapSearchAddress("");
    setEditingListingId(null);
    setForm(emptyForm);
    setErrorMessage(null);
    setNotice(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (form.areaName.trim() === "") {
      setErrorMessage("Enter the area or suburb for this room.");
      return;
    }
    if (form.address.trim() === "") {
      setErrorMessage("Enter or select the room address.");
      return;
    }
    if (!isRoomType(form.roomType)) {
      setErrorMessage("Choose a valid room type.");
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    setNotice(null);

    try {
      const area = await resolveArea(accessToken, form.areaName.trim());
      setAreas((current) =>
        current.some((existing) => existing.area_id === area.area_id)
          ? current
          : [...current, area],
      );
      const payload: ListingCreateRequest = {
        area_id: area.area_id,
        title: form.title,
        description: form.description,
        room_type: form.roomType,
        monthly_rent: form.monthlyRent,
        deposit_amount: form.depositAmount,
        address: form.address,
        google_place_id: form.googlePlaceId,
        latitude: form.googlePlaceId === null ? form.latitude : null,
        longitude: form.googlePlaceId === null ? form.longitude : null,
        date_available: form.dateAvailable,
        amenities: form.amenities,
      };

      if (editingListingId === null) {
        await createListing(accessToken, payload);
        setNotice("Your listing was saved as a draft.");
      } else {
        await updateListing(accessToken, editingListingId, payload);
        setNotice("Your changes were saved as a draft.");
      }
      setEditingListingId(null);
      setForm(emptyForm);
      setMapSearchAddress("");
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
  const activeListingCount = listings.filter(
    (listing) => listing.status === "active",
  ).length;
  const pendingListingCount = listings.filter(
    (listing) => listing.status === "pending",
  ).length;
  const pendingRequestCount = contactRequests.filter(
    (request) => request.status === "pending",
  ).length;
  const normalizedListingSearch = listingSearch.trim().toLocaleLowerCase();
  const landlordInitials = profile.full_name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase() ?? "")
    .join("");
  const filteredListings = listings.filter((listing) => {
    if (normalizedListingSearch === "") {
      return true;
    }

    return [
      listing.title,
      listing.address,
      listing.area_name ?? areaNames.get(listing.area_id) ?? "",
      listing.room_type.replaceAll("_", " "),
      getStatusLabel(listing.status),
    ].some((value) =>
      value.toLocaleLowerCase().includes(normalizedListingSearch),
    );
  });
  const areaChoices = Array.from(
    new Map(
      [...areas, ...areaSuggestions].map((area) => [
        area.name.toLocaleLowerCase(),
        area,
      ]),
    ).values(),
  );

  return (
    <main className="page-shell landlord-page">
      <aside aria-label="Landlord workspace" className="landlord-sidebar">
        <AppLink
          className="landlord-brand"
          href="/landlord"
          onNavigate={onNavigate}
        >
          <span aria-hidden="true" className="landlord-brand-mark">
            R
          </span>
          <span>
            <strong>Room Rentals</strong>
            <small>LANDLORD PORTAL</small>
          </span>
        </AppLink>
        <p className="landlord-nav-label">WORKSPACE</p>
        <nav aria-label="Dashboard sections" className="landlord-sidebar-nav">
          <a className="active" href="#overview">
            <span aria-hidden="true">▦</span> Dashboard
          </a>
          <a href="#my-listings-heading">
            <span aria-hidden="true">⌂</span> Listings
          </a>
          <AppLink href="/conversations" onNavigate={onNavigate}>
            <span aria-hidden="true">▤</span> Messages
          </AppLink>
          <a href="#contact-requests-heading">
            <span aria-hidden="true">◷</span> Inquiries
            {pendingRequestCount > 0 && (
              <span className="landlord-nav-count">{pendingRequestCount}</span>
            )}
          </a>
          <a href="#future-interest">
            <span aria-hidden="true">⌁</span> Future interest
          </a>
        </nav>
        <div className="landlord-sidebar-bottom">
          <AppLink href="/" onNavigate={onNavigate}>
            Browse public rooms
          </AppLink>
          <button onClick={onSignOut} type="button">
            <span aria-hidden="true">↪</span> Sign out
          </button>
        </div>
      </aside>
      <section className="landlord-dashboard">
        <header className="landlord-header">
          <div className="landlord-welcome">
            <span aria-hidden="true" className="landlord-welcome-avatar">
              {landlordInitials}
            </span>
            <p className="eyebrow">LANDLORD WORKSPACE</p>
            <h1>Good day, {profile.full_name.trim().split(/\s+/)[0]}</h1>
            <p>Manage your properties and keep up with tenant enquiries.</p>
          </div>
          <div className="landlord-header-tools">
            <label className="landlord-global-search">
              <span aria-hidden="true">⌕</span>
              <input
                aria-label="Search your listings"
                onChange={(event) => setListingSearch(event.target.value)}
                placeholder="Search your listings..."
                type="search"
                value={listingSearch}
              />
            </label>
            <span
              aria-label={`${pendingRequestCount} pending inquiries`}
              className="landlord-notification"
              title={`${pendingRequestCount} pending inquiries`}
            >
              ♧
              {pendingRequestCount > 0 && (
                <span aria-hidden="true" className="landlord-notification-dot" />
              )}
            </span>
            <button
              className="primary-button landlord-add-listing"
              onClick={() =>
                document
                  .getElementById("listing-form-heading")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" })
              }
              type="button"
            >
              <span aria-hidden="true">+</span> Add a new listing
            </button>
          </div>
        </header>

        <section
          aria-labelledby="landlord-overview-heading"
          className="landlord-overview"
          id="overview"
        >
          <div className="landlord-section-heading">
            <div>
              <p className="landlord-section-eyebrow">YOUR PORTFOLIO</p>
              <h2 id="landlord-overview-heading">Performance overview</h2>
            </div>
            <span className="landlord-updated-label">
              <span aria-hidden="true" /> Live account data
            </span>
          </div>
          <div className="landlord-stat-grid">
            <article className="landlord-stat-card stat-total">
              <span aria-hidden="true" className="landlord-stat-icon">⌂</span>
              <div>
                <p>Total listings</p>
                <strong>{isLoading ? "—" : listings.length}</strong>
                <span>Across your portfolio</span>
              </div>
            </article>
            <article className="landlord-stat-card stat-active">
              <span aria-hidden="true" className="landlord-stat-icon">✓</span>
              <div>
                <p>Active listings</p>
                <strong>{isLoading ? "—" : activeListingCount}</strong>
                <span>Visible to room seekers</span>
              </div>
            </article>
            <article className="landlord-stat-card stat-review">
              <span aria-hidden="true" className="landlord-stat-icon">◷</span>
              <div>
                <p>Pending approval</p>
                <strong>{isLoading ? "—" : pendingListingCount}</strong>
                <span>Awaiting moderation</span>
              </div>
            </article>
            <article className="landlord-stat-card stat-inquiries">
              <span aria-hidden="true" className="landlord-stat-icon">✉</span>
              <div>
                <p>New inquiries</p>
                <strong>
                  {isLoadingContactRequests ? "—" : pendingRequestCount}
                </strong>
                <span>Requests needing a reply</span>
              </div>
            </article>
          </div>
        </section>

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

        {!isLoading && (
          <RentalInterestNotificationsPanel
            accessToken={accessToken}
            onNavigate={onNavigate}
          />
        )}

        {!isLoading && (
          <LandlordRentalInterestsPanel
            accessToken={accessToken}
            listings={listings}
          />
        )}

        <div className="landlord-dashboard-grid">
          <aside className="landlord-inquiries-column">
          <section
            className="landlord-panel landlord-inquiries-panel"
            aria-labelledby="contact-requests-heading"
          >
          <div className="landlord-listings-heading">
            <div>
              <h2 id="contact-requests-heading">Recent inquiries</h2>
              <p className="landlord-panel-subtitle">
                Messages from prospective tenants
              </p>
            </div>
            <button
              aria-label="Refresh inquiries"
              className="landlord-icon-button"
              disabled={isLoadingContactRequests}
              onClick={() => void refreshContactRequests()}
              type="button"
            >
              ↻
            </button>
          </div>
          <AppLink
            className="landlord-inquiry-messages-link"
            href="/conversations"
            onNavigate={onNavigate}
          >
            Open messages <span aria-hidden="true">→</span>
          </AppLink>
          {contactRequestError !== null && (
            <p className="message message-error" role="alert">
              {contactRequestError}
            </p>
          )}
          {contactRequestNotice !== null && (
            <p className="message message-success" role="status">
              {contactRequestNotice}
            </p>
          )}
          {isLoadingContactRequests && (
            <p role="status">Loading contact requests...</p>
          )}
          {!isLoadingContactRequests &&
            contactRequestError === null &&
            contactRequests.length === 0 && (
              <p className="landlord-empty-state">
                You have not received any contact requests.
              </p>
            )}
          {!isLoadingContactRequests &&
            contactRequests.length > 0 && (
              <ul className="landlord-list">
                {contactRequests.map((contactRequest) => (
                  <li
                    className="landlord-contact-request"
                    key={contactRequest.request_id}
                  >
                    <div className="landlord-listing-header">
                      <div>
                        <h3>
                          {listings.find(
                            (listing) =>
                              listing.listing_id === contactRequest.listing_id,
                          )?.title ?? `Listing #${contactRequest.listing_id}`}
                        </h3>
                        <p>
                          {areaNames.get(
                            listings.find(
                              (listing) =>
                                listing.listing_id === contactRequest.listing_id,
                            )?.area_id ?? -1,
                          ) ?? `Room listing #${contactRequest.listing_id}`}
                        </p>
                        <p>
                          Requested{" "}
                          {formatRequestDate(contactRequest.requested_at)}
                        </p>
                      </div>
                      <span
                        className={`listing-status status-${contactRequest.status}`}
                      >
                        {contactRequest.status}
                      </span>
                    </div>
                    {contactRequest.status === "pending" && (
                      <div className="landlord-listing-actions">
                        <button
                          className="secondary-button"
                          disabled={updatingContactRequestId !== null}
                          onClick={() =>
                            void handleContactRequestDecision(
                              contactRequest.request_id,
                              "approved",
                            )
                          }
                          type="button"
                        >
                          {updatingContactRequestId ===
                          contactRequest.request_id
                            ? "Updating..."
                            : "Approve"}
                        </button>
                        <button
                          className="secondary-button danger-button"
                          disabled={updatingContactRequestId !== null}
                          onClick={() =>
                            void handleContactRequestDecision(
                              contactRequest.request_id,
                              "rejected",
                            )
                          }
                          type="button"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
        </section>
          </aside>

          <div className="landlord-primary-column">
        <section
          className="landlord-panel landlord-form-panel"
          aria-labelledby="listing-form-heading"
          id="listing-form"
        >
          <div className="landlord-section-heading">
            <div>
              <p className="landlord-section-eyebrow">PROPERTY MANAGEMENT</p>
              <h2 id="listing-form-heading">
                {editingListingId === null ? "Create a listing" : "Edit listing"}
              </h2>
            </div>
            <span className="landlord-form-hint">
              {editingListingId === null
                ? "New listings start as drafts"
                : `Editing listing #${editingListingId}`}
            </span>
          </div>
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
                Area or suburb
                <input
                  autoComplete="off"
                  list="landlord-area-suggestions"
                  maxLength={150}
                  onChange={(event) =>
                    updateField("areaName", event.target.value)
                  }
                  placeholder="Search or enter an area or suburb"
                  required
                  value={form.areaName}
                />
                <datalist id="landlord-area-suggestions">
                  {areaChoices.map((area) => (
                    <option key={area.area_id} value={area.name} />
                  ))}
                </datalist>
                <small className="landlord-area-hint">
                  If your area is not suggested, enter its name and it will be
                  saved with your listing.
                </small>
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
                Address (shown to renters)
                <input
                  autoComplete="street-address"
                  maxLength={255}
                  onChange={(event) => updateAddress(event.currentTarget.value)}
                  placeholder="Enter the address for your listing"
                  required
                  value={form.address}
                />
              </label>
              <label>
                Search and select an address
                <GoogleAddressSearch
                  onChange={updateAddress}
                  onResultSelected={selectAddress}
                  value={mapSearchAddress}
                />
                <small>
                  Search suggestions appear as you type. Select a Google Maps
                  result to fill in the room address and place it on the map.
                </small>
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
            {areaSearchError !== null && (
              <p className="landlord-area-search-error" role="status">
                Area suggestions could not be loaded: {areaSearchError} You can
                still enter any area name.
              </p>
            )}
            <div className="landlord-location-picker">
              <h3>Room location preview</h3>
              <p>
                Your exact pin is private. Public room details will show only
                an approximate location.
              </p>
              <p>
                Drag the pin to adjust its location. Moving it clears the
                selected Google Place ID and saves the adjusted coordinates.
              </p>
              <RoomMap
                draggable
                label="Choose the room's map location"
                onPointChange={updateMapPoint}
                placeId={form.googlePlaceId}
                point={
                  form.latitude === null || form.longitude === null
                    ? null
                    : {
                        latitude: form.latitude,
                        longitude: form.longitude,
                      }
                }
              />
            </div>
            <fieldset className="landlord-amenities">
              <legend>Amenities</legend>
              {amenities.map((amenity) => (
                <label key={amenity.amenity_id}>
                  <input
                    checked={form.amenities.includes(amenity.name)}
                    onChange={(event) => {
                      const selected = new Set(form.amenities);
                      if (event.currentTarget.checked) {
                        selected.add(amenity.name);
                      } else {
                        selected.delete(amenity.name);
                      }
                      setForm((current) => ({
                        ...current,
                        amenities: Array.from(selected),
                      }));
                    }}
                    type="checkbox"
                  />
                  {amenity.name}
                </label>
              ))}
            </fieldset>
            <div className="landlord-form-actions">
              <button
                className="primary-button landlord-form-submit"
                disabled={isSaving}
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
          className="landlord-panel landlord-listings-panel"
          aria-labelledby="my-listings-heading"
          id="listings"
        >
          <div className="landlord-listings-heading">
            <div>
              <p className="landlord-section-eyebrow">YOUR PROPERTIES</p>
              <h2 id="my-listings-heading">Manage listings</h2>
            </div>
            <button
              className="secondary-button"
              disabled={isLoading}
              onClick={() => {
                setIsLoading(true);
                void Promise.all([
                  refreshListings(),
                  getAmenities(),
                ])
                  .then(([, availableAmenities]) => {
                    setAmenities(availableAmenities);
                  })
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
          {!isLoading &&
            listings.length > 0 &&
            filteredListings.length === 0 && (
              <p className="landlord-empty-state">
                No listings match “{listingSearch}”. Try another search.
              </p>
            )}
          {!isLoading && filteredListings.length > 0 && (
            <ul className="landlord-list">
              {filteredListings.map((listing) => (
                <li className="landlord-listing" key={listing.listing_id}>
                  {listing.photos.length > 0 ? (
                    <img
                      alt={`Room interior for ${listing.title}`}
                      className="landlord-listing-cover"
                      src={listing.photos[0].url}
                    />
                  ) : (
                    <div
                      aria-hidden="true"
                      className="landlord-listing-cover landlord-listing-placeholder"
                    >
                      <span>⌂</span>
                      <small>Room listing</small>
                    </div>
                  )}
                  <div className="landlord-listing-card-content">
                  <div className="landlord-listing-header">
                    <div>
                      <h3>{listing.title}</h3>
                      <p>
                        {listing.area_name ??
                          areaNames.get(listing.area_id) ??
                          "Area unavailable"}
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
                  {listing.amenities.length > 0 && (
                    <p className="landlord-listing-summary">
                      Amenities: {listing.amenities.join(", ")}
                    </p>
                  )}
                  {listing.photos.length > 0 && (
                    <div className="landlord-photo-list landlord-extra-photos">
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
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
          </div>
        </div>

        <footer className="landlord-footer">
          <span>Room Rentals landlord workspace</span>
        </footer>
      </section>
    </main>
  );
}
