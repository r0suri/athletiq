/**
 * Typed HTTP client for the AthletIQ API.
 *
 * - Attaches the Cognito access token to every request.
 * - On 401 it force-refreshes the token once and retries; if that still fails it
 *   calls onUnauthorized (the app signs the user out) and throws.
 * - Normalises both error formats into ApiError:
 *     our envelope  {"error": {"code", "message", "details", "request_id"}}
 *     API Gateway   {"message": "Unauthorized"}   (Lambda never ran)
 */

export interface ErrorDetail {
  field: string;
  issue: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorDetail[];
  readonly requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: ErrorDetail[] = [],
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  /** The issue reported for one field, if any (for inline form errors). */
  fieldIssue(field: string): string | undefined {
    return this.details.find((d) => d.field === field)?.issue;
  }
}

/** Returns an access token, or null if the user has no valid session. */
export type TokenProvider = (forceRefresh: boolean) => Promise<string | null>;

export interface ApiClientOptions {
  baseUrl: string;
  getToken: TokenProvider;
  onUnauthorized: () => void;
  fetchFn?: typeof fetch;
}

type Query = Record<string, string | number | undefined | null>;

export interface RequestOptions {
  query?: Query;
  body?: unknown;
}

export type ApiClient = <T>(method: string, path: string, options?: RequestOptions) => Promise<T>;

const STATUS_CODES: Record<number, string> = {
  401: "UNAUTHORIZED",
  403: "FORBIDDEN",
  404: "NOT_FOUND",
  422: "VALIDATION_ERROR",
  429: "RATE_LIMITED",
};

export async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error body (e.g. an HTML 502 page); fall through to a generic error.
  }
  if (body && typeof body === "object" && "error" in body) {
    const e = (body as { error: Record<string, unknown> }).error;
    return new ApiError(
      response.status,
      String(e.code ?? "ERROR"),
      String(e.message ?? "Request failed."),
      Array.isArray(e.details) ? (e.details as ErrorDetail[]) : [],
      typeof e.request_id === "string" ? e.request_id : null,
    );
  }
  const message =
    body && typeof body === "object" && "message" in body
      ? String((body as { message: unknown }).message)
      : `Request failed with status ${response.status}.`;
  return new ApiError(response.status, STATUS_CODES[response.status] ?? "HTTP_ERROR", message);
}

function buildUrl(baseUrl: string, path: string, query?: Query): string {
  const url = new URL(baseUrl + path);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export function createApiClient({
  baseUrl,
  getToken,
  onUnauthorized,
  fetchFn = (...args) => fetch(...args),
}: ApiClientOptions): ApiClient {
  const send = async (token: string, method: string, url: string, body: unknown) => {
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    try {
      return await fetchFn(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, "NETWORK_ERROR", "Can't reach AthletIQ. Check your connection and try again.");
    }
  };

  const unauthorized = () => {
    onUnauthorized();
    return new ApiError(401, "UNAUTHORIZED", "Your session has ended. Sign in again.");
  };

  return async function request<T>(method: string, path: string, options: RequestOptions = {}) {
    const url = buildUrl(baseUrl, path, options.query);

    const token = await getToken(false);
    if (!token) throw unauthorized();
    let response = await send(token, method, url, options.body);

    if (response.status === 401) {
      // The token may have expired between checks: refresh once, then retry.
      const refreshed = await getToken(true);
      if (!refreshed) throw unauthorized();
      response = await send(refreshed, method, url, options.body);
      if (response.status === 401) throw unauthorized();
    }

    if (!response.ok) throw await toApiError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  };
}
