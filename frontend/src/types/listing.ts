export type ListingPhoto = {
  photo_id: number;
  url: string;
  uploaded_at: string;
};

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

export type Area = {
  area_id: number;
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
  date_available: string;
};

export type ListingUpdateRequest = Partial<ListingCreateRequest>;
