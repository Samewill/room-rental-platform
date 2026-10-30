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
  headers.set("Content-Type", "application/json");

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
