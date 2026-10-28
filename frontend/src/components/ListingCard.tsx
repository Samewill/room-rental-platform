export type Listing = {
  listing_id: number;
  area_id: number;
  title: string;
  description: string;
  room_type: string;
  monthly_rent: string | number;
  deposit_amount: string | number;
  address: string;
  date_available: string;
  status: string;
  created_at: string;
  photos: ListingPhoto[];
};

export type ListingPhoto = {
  photo_id: number;
  url: string;
  uploaded_at: string;
};

type ListingCardProps = {
  listing: Listing;
};

function formatRent(value: string | number): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return "Rent unavailable";
  }

  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatAvailability(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "Availability date unavailable";
  }

  return `Available ${new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
  }).format(date)}`;
}

export default function ListingCard({ listing }: ListingCardProps) {
  return (
    <article
      aria-labelledby={`listing-${listing.listing_id}`}
      style={{
        background: "white",
        border: "1px solid #e3e7ed",
        borderRadius: 14,
        overflow: "hidden",
      }}
    >
      {listing.photos[0] ? (
        <img
          alt={`Room interior for ${listing.title}`}
          height={150}
          src={listing.photos[0].url}
          style={{ display: "block", height: 150, objectFit: "cover", width: "100%" }}
        />
      ) : (
        <div
          aria-hidden="true"
          style={{
            alignItems: "center",
            background: "linear-gradient(135deg, #dce9df, #f1e8d8)",
            color: "#355b43",
            display: "flex",
            fontSize: 14,
            fontWeight: 600,
            height: 150,
            justifyContent: "center",
          }}
        >
          Room photo
        </div>
      )}
      <div style={{ padding: 20 }}>
        <p style={{ color: "#476b55", margin: "0 0 6px" }}>
          {listing.room_type}
        </p>
        <h2
          id={`listing-${listing.listing_id}`}
          style={{ fontSize: 20, margin: "0 0 8px" }}
        >
          {listing.title}
        </h2>
        <p
          style={{
            color: "#596579",
            lineHeight: 1.5,
            margin: "0 0 14px",
          }}
        >
          {listing.description}
        </p>
        <p style={{ fontWeight: 700, margin: "0 0 8px" }}>
          {formatRent(listing.monthly_rent)}{" "}
          <span style={{ color: "#596579", fontWeight: 400 }}>/ month</span>
        </p>
        <p style={{ color: "#596579", margin: "0 0 6px" }}>
          {listing.address}
        </p>
        <p style={{ color: "#596579", margin: "0 0 6px" }}>
          Area #{listing.area_id}
        </p>
        <p style={{ color: "#596579", margin: 0 }}>
          {formatAvailability(listing.date_available)}
        </p>
        <a
          href={`/listings/${listing.listing_id}`}
          style={{
            background: "#244b35",
            borderRadius: 8,
            color: "white",
            display: "inline-block",
            fontWeight: 600,
            marginTop: 16,
            padding: "10px 14px",
            textDecoration: "none",
          }}
        >
          View details
        </a>
      </div>
    </article>
  );
}
