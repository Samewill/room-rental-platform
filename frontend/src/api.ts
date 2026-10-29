import type {
  Area,
  Listing,
  ListingCreateRequest,
  ListingUpdateRequest,
} from "./types/listing";

export interface RegisterRequest {
  full_name: string;
  phone_no: string;
  email: string;
  password: string;
  role: "tenant" | "landlord";
  business_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserProfile {
  user_id: number;
  full_name: string;
  phone_no: string;
  email: string;
  business_name: string | null;
  created_at: string;
  roles: string[];
}

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body instanceof FormData) {
    headers.delete("Content-Type");
  } else if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });
  const contentType = response.headers.get("content-type") ?? "";
  const body: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new Error(getErrorMessage(body, response.status));
  }

  return body as T;
}

function getErrorMessage(body: unknown, statusCode: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = body.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "msg" in item &&
            typeof item.msg === "string"
          ) {
            return item.msg;
          }
          return null;
        })
        .filter((message): message is string => message !== null);
      if (messages.length > 0) {
        return messages.join(" ");
      }
    }
  }

  return `Request failed with status ${statusCode}.`;
}

export function registerAccount(
  payload: RegisterRequest,
): Promise<UserProfile> {
  return requestJson<UserProfile>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(
  payload: LoginRequest,
): Promise<TokenResponse> {
  return requestJson<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMyProfile(accessToken: string): Promise<UserProfile> {
  return requestJson<UserProfile>("/api/v1/users/me", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getAreas(): Promise<Area[]> {
  return requestJson<Area[]>("/api/v1/areas");
}

export function getMyListings(accessToken: string): Promise<Listing[]> {
  return requestJson<Listing[]>("/api/v1/users/me/listings", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function createListing(
  accessToken: string,
  payload: ListingCreateRequest,
): Promise<Listing> {
  return requestJson<Listing>("/api/v1/listings", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });
}

export function updateListing(
  accessToken: string,
  listingId: number,
  changes: ListingUpdateRequest,
): Promise<Listing> {
  return requestJson<Listing>(`/api/v1/listings/${listingId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(changes),
  });
}

export function submitListing(
  accessToken: string,
  listingId: number,
): Promise<Listing> {
  return requestJson<Listing>(`/api/v1/listings/${listingId}/submit`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function withdrawListing(
  accessToken: string,
  listingId: number,
): Promise<Listing> {
  return requestJson<Listing>(`/api/v1/listings/${listingId}/withdraw`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function uploadListingPhoto(
  accessToken: string,
  listingId: number,
  file: File,
): Promise<Listing> {
  const body = new FormData();
  body.append("photo", file);

  return requestJson<Listing>(`/api/v1/listings/${listingId}/photos`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body,
  });
}
