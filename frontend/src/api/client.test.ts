import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient } from "./client";

const BASE = "https://api.example.com";

function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setup(responses: Response[], tokens: (string | null)[] = ["token-1", "token-2"]) {
  const fetchFn = vi.fn<typeof fetch>();
  responses.forEach((r) => fetchFn.mockResolvedValueOnce(r));
  const getToken = vi.fn(async () => tokens.shift() ?? null);
  const onUnauthorized = vi.fn();
  const request = createApiClient({ baseUrl: BASE, getToken, onUnauthorized, fetchFn });
  return { request, fetchFn, getToken, onUnauthorized };
}

describe("createApiClient", () => {
  it("sends the bearer token and returns parsed JSON", async () => {
    const { request, fetchFn } = setup([jsonResponse(200, { goal: "endurance" })]);

    await expect(request("GET", "/v1/me/profile")).resolves.toEqual({ goal: "endurance" });

    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe(`${BASE}/v1/me/profile`);
    expect((init!.headers as Record<string, string>).Authorization).toBe("Bearer token-1");
  });

  it("serialises JSON bodies and skips empty query values", async () => {
    const { request, fetchFn } = setup([jsonResponse(200, { items: [], next_cursor: null })]);

    await request("GET", "/v1/workouts", { query: { from: "2026-10-01", type: undefined, cursor: null, limit: 20 } });
    await expect(Promise.resolve(fetchFn.mock.calls[0]![0])).resolves.toBe(
      `${BASE}/v1/workouts?from=2026-10-01&limit=20`,
    );
  });

  it("sends a JSON body with a content type", async () => {
    const { request, fetchFn } = setup([jsonResponse(201, { id: "x" })]);
    await request("POST", "/v1/workouts", { body: { type: "run" } });
    const init = fetchFn.mock.calls[0]![1]!;
    expect(init.body).toBe('{"type":"run"}');
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("returns undefined for 204 No Content", async () => {
    const { request } = setup([new Response(null, { status: 204 })]);
    await expect(request("DELETE", "/v1/workouts/abc")).resolves.toBeUndefined();
  });

  it("parses the backend error envelope", async () => {
    const { request } = setup([
      jsonResponse(422, {
        error: {
          code: "VALIDATION_ERROR",
          message: "Request validation failed.",
          details: [{ field: "rpe", issue: "must be at most 10" }],
          request_id: "req-123",
        },
      }),
    ]);

    const error = await request("POST", "/v1/workouts", { body: {} }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.code).toBe("VALIDATION_ERROR");
    expect(apiError.requestId).toBe("req-123");
    expect(apiError.fieldIssue("rpe")).toBe("must be at most 10");
  });

  it("refreshes the token once after a gateway 401 and retries", async () => {
    const { request, fetchFn, getToken, onUnauthorized } = setup([
      jsonResponse(401, { message: "Unauthorized" }),
      jsonResponse(200, { ok: true }),
    ]);

    await expect(request("GET", "/v1/me/profile")).resolves.toEqual({ ok: true });

    expect(getToken).toHaveBeenNthCalledWith(2, true); // forced refresh
    const retryHeaders = fetchFn.mock.calls[1]![1]!.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer token-2");
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("signs out when the retry is also unauthorized", async () => {
    const { request, onUnauthorized } = setup([
      jsonResponse(401, { message: "Unauthorized" }),
      jsonResponse(401, { message: "Unauthorized" }),
    ]);

    await expect(request("GET", "/v1/me/profile")).rejects.toMatchObject({ status: 401, code: "UNAUTHORIZED" });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("signs out without calling the API when there is no session", async () => {
    const { request, fetchFn, onUnauthorized } = setup([], [null]);
    await expect(request("GET", "/v1/me/profile")).rejects.toMatchObject({ status: 401 });
    expect(fetchFn).not.toHaveBeenCalled();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("reports network failures clearly", async () => {
    const fetchFn = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("Failed to fetch"));
    const request = createApiClient({ baseUrl: BASE, getToken: async () => "t", onUnauthorized: vi.fn(), fetchFn });
    await expect(request("GET", "/v1/me/profile")).rejects.toMatchObject({ status: 0, code: "NETWORK_ERROR" });
  });

  it("handles non-JSON error bodies", async () => {
    const { request } = setup([new Response("<html>Bad gateway</html>", { status: 502 })]);
    await expect(request("GET", "/v1/me/profile")).rejects.toMatchObject({ status: 502, code: "HTTP_ERROR" });
  });
});
