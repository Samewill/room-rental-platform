import type {
  Area,
  Amenity,
  Listing,
  ListingCreateRequest,
  ListingModerationRecord,
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
  email: string;
  business_name: string | null;
  created_at: string;
  roles: string[];
}

export type ReportTarget = "listing" | "landlord" | "user";
export type ReportReason =
  | "scam"
  | "fake_listing"
  | "inaccurate_info"
  | "abusive"
  | "other";
export type ReportStatus =
  | "open"
  | "under_review"
  | "resolved"
  | "dismissed";

export interface ReportCreateRequest {
  target: ReportTarget;
  listing_id?: number;
  target_user_id?: number;
  reason: ReportReason;
  details: string;
}

export interface ReportResolutionRequest {
  note?: string;
}

export interface ReportResponse {
  report_id: number;
  listing_id: number | null;
  target_user_id: number | null;
  tenant_id: number;
  admin_id: number | null;
  reason: ReportReason;
  status: ReportStatus;
  details: string | null;
  created_at: string;
}

export interface ReportHistoryRecord {
  history_id: number;
  report_id: number;
  actor_user_id: number;
  action: "submitted" | "assigned" | "resolved" | "dismissed";
  note: string | null;
  created_at: string;
}

export interface ContactRequest {
  request_id: number;
  listing_id: number;
  status: "pending" | "approved" | "rejected" | "cancelled";
  requested_at: string;
}

export interface Conversation {
  conversation_id: number;
  contact_request_id: number;
  created_at: string;
}

export type AssistantRole = "tenant" | "landlord";

export interface AssistantConversation {
  conversation_id: number;
  assistant_role: AssistantRole;
  created_at: string;
  updated_at: string;
  last_message: string | null;
}

export interface AssistantListingResult {
  listing: Listing;
  area_name: string;
}

export interface AssistantNotification {
  kind: "listing_approved" | "listing_rejected";
  listing_id: number;
  listing_title: string;
  reason: string | null;
}

export interface AssistantDraft {
  area_id: number | null;
  area_name: string | null;
  title: string | null;
  description: string | null;
  room_type: string | null;
  monthly_rent: string | null;
  deposit_amount: string | null;
  address: string | null;
  date_available: string | null;
  amenities: string[];
  missing_fields: string[];
  ready_to_confirm: boolean;
}

export interface AssistantMessage {
  message_id: number;
  sender_role: "user" | "assistant";
  content: string;
  created_at: string;
  listings: AssistantListingResult[];
  draft: AssistantDraft | null;
  created_listing: Listing | null;
  notification: AssistantNotification | null;
}

export interface AssistantConversationDetail extends AssistantConversation {
  messages: AssistantMessage[];
}

export type MessageStatus = "sent" | "read";

export interface ConversationMessage {
  message_id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  status: MessageStatus;
  sent_at: string;
  read_at: string | null;
  whatsapp_delivery_status: "sent" | "failed" | null;
}

export interface WhatsAppStatus {
  enabled: boolean;
}

export type SavedSearchRoomType =
  | "single_room"
  | "shared_room"
  | "bachelor_flat"
  | "self_contained";

export interface SavedSearch {
  saved_search_id: number;
  location: string | null;
  room_type: SavedSearchRoomType | null;
  minimum_rent: string | number | null;
  maximum_rent: string | number | null;
  amenities: string[];
  created_at: string;
}

export interface SavedSearchCreateRequest {
  location?: string;
  room_type?: SavedSearchRoomType;
  minimum_rent?: number;
  maximum_rent?: number;
  amenities?: string[];
}

export interface Review {
  review_id: number;
  contact_request_id: number;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface ReviewCreateRequest {
  contact_request_id: number;
  rating: number;
  comment?: string;
}

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly statusCode: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function buildApiUrl(path: string): string {
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

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

  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers,
  });
  const contentType = response.headers.get("content-type") ?? "";
  const body: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(getErrorMessage(body, response.status), response.status);
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

export function createContactRequest(
  accessToken: string,
  listingId: number,
): Promise<ContactRequest> {
  return requestJson<ContactRequest>(
    `/api/v1/listings/${listingId}/contact-requests`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function getMyContactRequests(
  accessToken: string,
): Promise<ContactRequest[]> {
  return requestJson<ContactRequest[]>("/api/v1/users/me/contact-requests", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getReceivedContactRequests(
  accessToken: string,
): Promise<ContactRequest[]> {
  return requestJson<ContactRequest[]>(
    "/api/v1/users/me/received-requests",
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function cancelContactRequest(
  accessToken: string,
  requestId: number,
): Promise<ContactRequest> {
  return requestJson<ContactRequest>(`/api/v1/contact-requests/${requestId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ status: "cancelled" }),
  });
}

export function respondToContactRequest(
  accessToken: string,
  requestId: number,
  status: "approved" | "rejected",
): Promise<ContactRequest> {
  return requestJson<ContactRequest>(`/api/v1/contact-requests/${requestId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ status }),
  });
}

export function getMyConversations(
  accessToken: string,
): Promise<Conversation[]> {
  return requestJson<Conversation[]>("/api/v1/users/me/conversations", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getConversationMessages(
  accessToken: string,
  conversationId: number,
): Promise<ConversationMessage[]> {
  return requestJson<ConversationMessage[]>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function sendConversationMessage(
  accessToken: string,
  conversationId: number,
  content: string,
): Promise<ConversationMessage> {
  return requestJson<ConversationMessage>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ content }),
    },
  );
}

export function markConversationMessageRead(
  accessToken: string,
  conversationId: number,
  messageId: number,
): Promise<ConversationMessage> {
  return requestJson<ConversationMessage>(
    `/api/v1/conversations/${conversationId}/messages/${messageId}/read`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function getWhatsAppStatus(
  accessToken: string,
): Promise<WhatsAppStatus> {
  return requestJson<WhatsAppStatus>("/api/v1/users/me/whatsapp", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function startWhatsAppVerification(
  accessToken: string,
  phoneNumber: string,
): Promise<{ detail: string }> {
  return requestJson<{ detail: string }>(
    "/api/v1/users/me/whatsapp/verification",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ phone_number: phoneNumber, consent: true }),
    },
  );
}

export function confirmWhatsAppVerification(
  accessToken: string,
  code: string,
): Promise<WhatsAppStatus> {
  return requestJson<WhatsAppStatus>(
    "/api/v1/users/me/whatsapp/verification/confirm",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ code }),
    },
  );
}

export function unlinkWhatsApp(accessToken: string): Promise<WhatsAppStatus> {
  return requestJson<WhatsAppStatus>("/api/v1/users/me/whatsapp", {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function retryWhatsAppDelivery(
  accessToken: string,
  conversationId: number,
  messageId: number,
): Promise<ConversationMessage> {
  return requestJson<ConversationMessage>(
    `/api/v1/conversations/${conversationId}/messages/${messageId}/whatsapp/retry`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function getAssistantConversations(
  accessToken: string,
): Promise<AssistantConversation[]> {
  return requestJson<AssistantConversation[]>("/api/v1/assistant/conversations", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function createAssistantConversation(
  accessToken: string,
  assistantRole: AssistantRole,
): Promise<AssistantConversation> {
  return requestJson<AssistantConversation>(
    "/api/v1/assistant/conversations",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ assistant_role: assistantRole }),
    },
  );
}

export function getAssistantConversation(
  accessToken: string,
  conversationId: number,
): Promise<AssistantConversationDetail> {
  return requestJson<AssistantConversationDetail>(
    `/api/v1/assistant/conversations/${conversationId}`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function sendAssistantMessage(
  accessToken: string,
  conversationId: number,
  content: string,
): Promise<AssistantMessage> {
  return requestJson<AssistantMessage>(
    `/api/v1/assistant/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ content }),
    },
  );
}

export function confirmAssistantListing(
  accessToken: string,
  conversationId: number,
): Promise<{ conversation_id: number; listing: Listing }> {
  return requestJson<{ conversation_id: number; listing: Listing }>(
    `/api/v1/assistant/conversations/${conversationId}/confirm-listing`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function createSavedSearch(
  accessToken: string,
  payload: SavedSearchCreateRequest,
): Promise<SavedSearch> {
  return requestJson<SavedSearch>("/api/v1/users/me/saved-searches", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + accessToken,
    },
    body: JSON.stringify(payload),
  });
}

export function getMySavedSearches(
  accessToken: string,
): Promise<SavedSearch[]> {
  return requestJson<SavedSearch[]>("/api/v1/users/me/saved-searches", {
    headers: {
      Authorization: "Bearer " + accessToken,
    },
  });
}

export function deleteSavedSearch(
  accessToken: string,
  savedSearchId: number,
): Promise<void> {
  return requestJson<void>(
    `/api/v1/users/me/saved-searches/${savedSearchId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: "Bearer " + accessToken,
      },
    },
  );
}

export function createReview(
  accessToken: string,
  payload: ReviewCreateRequest,
): Promise<Review> {
  return requestJson<Review>("/api/v1/users/me/reviews", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + accessToken,
    },
    body: JSON.stringify(payload),
  });
}

export function getMyReviews(accessToken: string): Promise<Review[]> {
  return requestJson<Review[]>("/api/v1/users/me/reviews", {
    headers: {
      Authorization: "Bearer " + accessToken,
    },
  });
}

export function getAreas(search?: string): Promise<Area[]> {
  const query = search?.trim();
  const path =
    query === undefined || query === ""
      ? "/api/v1/areas"
      : `/api/v1/areas?search=${encodeURIComponent(query)}`;
  return requestJson<Area[]>(path);
}

export function resolveArea(
  accessToken: string,
  name: string,
): Promise<Area> {
  return requestJson<Area>("/api/v1/areas/resolve", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ name }),
  });
}

export function getAmenities(signal?: AbortSignal): Promise<Amenity[]> {
  return requestJson<Amenity[]>("/api/v1/amenities", { signal });
}

export function getMyListings(accessToken: string): Promise<Listing[]> {
  return requestJson<Listing[]>("/api/v1/users/me/listings", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getPublicListingMapLocation(
  listingId: number,
  signal?: AbortSignal,
): Promise<PublicListingLocation> {
  return requestJson<PublicListingLocation>(
    `/api/v1/listings/${listingId}/map-location`,
    { signal },
  );
}

export type PublicListingLocation = {
  approximate_latitude: number;
  approximate_longitude: number;
};

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

export function getPendingListings(accessToken: string): Promise<Listing[]> {
  return requestJson<Listing[]>("/api/v1/admin/listings/pending", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getPublishedListings(accessToken: string): Promise<Listing[]> {
  return requestJson<Listing[]>("/api/v1/admin/listings/published", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getListingModerationHistory(
  accessToken: string,
  listingId: number,
): Promise<ListingModerationRecord[]> {
  return requestJson<ListingModerationRecord[]>(
    `/api/v1/admin/listings/${listingId}/moderation-history`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function approveListing(
  accessToken: string,
  listingId: number,
  reason?: string,
): Promise<Listing> {
  return requestJson<Listing>(
    `/api/v1/admin/listings/${listingId}/approve`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ reason }),
    },
  );
}

export function rejectListing(
  accessToken: string,
  listingId: number,
  reason: string,
): Promise<Listing> {
  return requestJson<Listing>(
    `/api/v1/admin/listings/${listingId}/reject`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ reason }),
    },
  );
}

export function hideListing(
  accessToken: string,
  listingId: number,
  reason: string,
): Promise<Listing> {
  return requestJson<Listing>(
    `/api/v1/admin/listings/${listingId}/hide`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ reason }),
    },
  );
}

export function submitReport(
  accessToken: string,
  payload: ReportCreateRequest,
): Promise<ReportResponse> {
  return requestJson<ReportResponse>("/api/v1/reports", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });
}

export function getMyReports(
  accessToken: string,
): Promise<ReportResponse[]> {
  return requestJson<ReportResponse[]>("/api/v1/users/me/reports", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getAdminReports(
  accessToken: string,
  statusFilter?: ReportStatus,
): Promise<ReportResponse[]> {
  const query = statusFilter
    ? `?${new URLSearchParams({ status: statusFilter })}`
    : "";
  return requestJson<ReportResponse[]>(`/api/v1/admin/reports${query}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export function getReportHistory(
  accessToken: string,
  reportId: number,
): Promise<ReportHistoryRecord[]> {
  return requestJson<ReportHistoryRecord[]>(
    `/api/v1/admin/reports/${reportId}/history`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function assignReportToSelf(
  accessToken: string,
  reportId: number,
): Promise<ReportResponse> {
  return requestJson<ReportResponse>(
    `/api/v1/admin/reports/${reportId}/assign`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export function resolveReport(
  accessToken: string,
  reportId: number,
  payload: ReportResolutionRequest = {},
): Promise<ReportResponse> {
  return requestJson<ReportResponse>(
    `/api/v1/admin/reports/${reportId}/resolve`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    },
  );
}

export function dismissReport(
  accessToken: string,
  reportId: number,
  payload: ReportResolutionRequest = {},
): Promise<ReportResponse> {
  return requestJson<ReportResponse>(
    `/api/v1/admin/reports/${reportId}/dismiss`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    },
  );
}
