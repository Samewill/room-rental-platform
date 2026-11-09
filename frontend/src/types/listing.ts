export type ListingPhoto = {
  photo_id: number;
  url: string;
  uploaded_at: string;
};

export type ListingModerationRecord = {
  moderation_id: number;
  listing_id: number;
  admin_id: number;
  decision: "approved" | "rejected" | "flagged";
  reason: string | null;
  decided_at: string;
};

export type Listing = {
  listing_id: number;
  area_id: number;
  area_name?: string | null;
  title: string;
  description: string;
  room_type: string;
  monthly_rent: string | number;
  deposit_amount: string | number;
  address: string;
  date_available: string;
  status: string;
  created_at: string;
  google_place_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  approximate_latitude?: number | null;
  approximate_longitude?: number | null;
  has_map_location?: boolean;
  photos: ListingPhoto[];
  amenities: string[];
};

export type Area = {
  area_id: number;
  name: string;
};

export type Amenity = {
  amenity_id: number;
  name: string;
};

export type ListingCreateRequest = {
  area_id: number;
  title: string;
  description: string;
  room_type:
    | "single_room"
    | "shared_room"
    | "bachelor_flat"
    | "self_contained";
  monthly_rent: string;
  deposit_amount: string;
  address: string;
  google_place_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  date_available: string;
  amenities?: string[];
};

export type ListingUpdateRequest = Partial<ListingCreateRequest>;
