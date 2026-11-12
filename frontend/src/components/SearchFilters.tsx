import type { ChangeEvent } from "react";

import GoogleAddressSearch, {
  type GoogleAddressSelection,
} from "./GoogleAddressSearch";
import type { Amenity } from "../types/listing";
import "./SearchFilters.css";

export type ListingFilters = {
  location: string;
  roomType: string;
  minimumRent: string;
  maximumRent: string;
  amenities: string[];
};

type SearchFiltersProps = {
  amenities: Amenity[];
  availableBy: string;
  filters: ListingFilters;
  onAvailabilityChange: (value: string) => void;
  onChange: (filters: ListingFilters) => void;
  onLocationSelected: (selection: GoogleAddressSelection) => void;
  onRadiusChange: (radius: 5 | 10) => void;
  radius: 5 | 10;
  hasLocationSelection: boolean;
};

const fieldStyle = {
  background: "white",
  border: "1px solid #cbd3dd",
  borderRadius: 8,
  boxSizing: "border-box" as const,
  color: "#182230",
  font: "inherit",
  minHeight: 42,
  padding: "8px 10px",
  width: "100%",
};

export default function SearchFilters({
  amenities,
  availableBy,
  filters,
  onAvailabilityChange,
  onChange,
  onLocationSelected,
  onRadiusChange,
  radius,
  hasLocationSelection,
}: SearchFiltersProps) {
  function updateField(
    field: keyof ListingFilters,
    value: string,
  ): void {
    onChange({ ...filters, [field]: value });
  }

  function updateRent(
    field: "minimumRent" | "maximumRent",
    event: ChangeEvent<HTMLInputElement>,
  ): void {
    const value = event.currentTarget.value;
    if (value === "" || Number(value) >= 0) {
      updateField(field, value);
    }
  }

  function toggleAmenity(name: string, checked: boolean): void {
    const selected = new Set(filters.amenities);
    if (checked) {
      selected.add(name);
    } else {
      selected.delete(name);
    }
    onChange({ ...filters, amenities: Array.from(selected) });
  }

  return (
    <section
      aria-label="Filter listings"
      className="search-filters"
      style={{
        background: "white",
        border: "1px solid #e3e7ed",
        borderRadius: 14,
        display: "grid",
        gap: 16,
        marginBottom: 24,
        padding: 20,
      }}
    >
      <label
        className="search-filter-field"
        style={{ color: "#344054", display: "grid", gap: 6 }}
      >
        Suburb, city or province
        <GoogleAddressSearch
          onChange={(value) => updateField("location", value)}
          onResultSelected={onLocationSelected}
          value={filters.location}
        />
      </label>

      <label
        className="search-filter-field"
        style={{ color: "#344054", display: "grid", gap: 6 }}
      >
        Search radius
        <select
          disabled={!hasLocationSelection}
          onChange={(event) =>
            onRadiusChange(event.currentTarget.value === "10" ? 10 : 5)
          }
          style={fieldStyle}
          value={radius}
        >
          <option value={5}>Within 5 km</option>
          <option value={10}>Within 10 km</option>
        </select>
        {!hasLocationSelection && (
          <small>Select a Google Maps location to enable radius search.</small>
        )}
        {hasLocationSelection && (
          <small>Radius matches use private listing coordinates.</small>
        )}
      </label>

      <label
        className="search-filter-field"
        style={{ color: "#344054", display: "grid", gap: 6 }}
      >
        Room type
        <select
          onChange={(event) => updateField("roomType", event.currentTarget.value)}
          style={fieldStyle}
          value={filters.roomType}
        >
          <option value="">All room types</option>
          <option value="single_room">Single room</option>
          <option value="shared_room">Shared room</option>
          <option value="bachelor_flat">Bachelor flat</option>
          <option value="self_contained">Self-contained</option>
        </select>
      </label>

      <label
        className="search-filter-field"
        style={{ color: "#344054", display: "grid", gap: 6 }}
      >
        Minimum monthly rent
        <input
          min="0"
          onChange={(event) => updateRent("minimumRent", event)}
          placeholder="No minimum"
          style={fieldStyle}
          type="number"
          value={filters.minimumRent}
        />
      </label>

      <label
        className="search-filter-field"
        style={{ color: "#344054", display: "grid", gap: 6 }}
      >
        Maximum monthly rent
        <input
          min="0"
          onChange={(event) => updateRent("maximumRent", event)}
          placeholder="No maximum"
          style={fieldStyle}
          type="number"
          value={filters.maximumRent}
        />
      </label>

      <label
        className="search-filter-field"
        style={{ color: "#344054", display: "grid", gap: 6 }}
      >
        Available on or before
        <input
          onChange={(event) => onAvailabilityChange(event.currentTarget.value)}
          style={fieldStyle}
          type="date"
          value={availableBy}
        />
        <small>Leave blank to include any availability date.</small>
      </label>

      <fieldset
        className="search-filter-amenities"
        style={{
          border: 0,
          display: "grid",
          gap: 8,
          margin: 0,
          padding: 0,
        }}
      >
        <legend style={{ color: "#344054", marginBottom: 6 }}>Amenities</legend>
        {amenities.map((amenity) => (
          <label
            key={amenity.amenity_id}
            style={{ alignItems: "center", display: "flex", gap: 8 }}
          >
            <input
              checked={filters.amenities.includes(amenity.name)}
              onChange={(event) =>
                toggleAmenity(amenity.name, event.currentTarget.checked)
              }
              type="checkbox"
            />
            {amenity.name}
          </label>
        ))}
      </fieldset>
    </section>
  );
}
