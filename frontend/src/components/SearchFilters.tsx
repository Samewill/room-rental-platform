import type { ChangeEvent } from "react";

export type ListingFilters = {
  location: string;
  roomType: string;
  minimumRent: string;
  maximumRent: string;
};

type SearchFiltersProps = {
  filters: ListingFilters;
  onChange: (filters: ListingFilters) => void;
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
  filters,
  onChange,
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

  return (
    <section
      aria-label="Filter listings"
      style={{
        background: "white",
        border: "1px solid #e3e7ed",
        borderRadius: 14,
        display: "grid",
        gap: 16,
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        marginBottom: 24,
        padding: 20,
      }}
    >
      <label style={{ color: "#344054", display: "grid", gap: 6 }}>
        Location
        <input
          autoComplete="address-level2"
          onChange={(event) => updateField("location", event.currentTarget.value)}
          placeholder="Suburb or area"
          style={fieldStyle}
          type="search"
          value={filters.location}
        />
      </label>

      <label style={{ color: "#344054", display: "grid", gap: 6 }}>
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

      <label style={{ color: "#344054", display: "grid", gap: 6 }}>
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

      <label style={{ color: "#344054", display: "grid", gap: 6 }}>
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
    </section>
  );
}
