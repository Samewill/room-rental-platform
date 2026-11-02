import ListingCard, { type Listing } from "./ListingCard";

type ListingGridProps = {
  listings: Listing[];
  onNavigate: (path: string) => void;
};

export default function ListingGrid({
  listings,
  onNavigate,
}: ListingGridProps) {
  return (
    <ul
      style={{
        display: "grid",
        gap: 20,
        gridTemplateColumns: "repeat(auto-fit, minmax(270px, 1fr))",
        listStyle: "none",
        margin: 0,
        padding: 0,
      }}
    >
      {listings.map((listing) => (
        <li key={listing.listing_id}>
          <ListingCard listing={listing} onNavigate={onNavigate} />
        </li>
      ))}
    </ul>
  );
}
