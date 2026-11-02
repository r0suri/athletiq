import { vi } from "vitest";

import { ApiError } from "../api/client";
import type { Profile } from "../api/types";

export const UNCONFIGURED: Profile = { goal: "general_fitness", timezone: "UTC", configured: false, updated_at: null };
export const CONFIGURED: Profile = {
  goal: "endurance",
  timezone: "America/New_York",
  configured: true,
  updated_at: "2026-11-01T23:00:20Z",
};

/** Echo the saved values back, as PUT /v1/me/profile does. */
export function savingApi(initial: Profile) {
  return {
    getProfile: vi.fn().mockResolvedValue(initial),
    putProfile: vi.fn(async (input: { goal: Profile["goal"]; timezone: string }) => ({
      ...input,
      configured: true,
      updated_at: "2026-11-02T00:00:00Z",
    })),
  };
}

export function timezone422() {
  return new ApiError(422, "VALIDATION_ERROR", "Request validation failed.", [
    { field: "timezone", issue: "Value error, must be an IANA timezone name, e.g. 'America/New_York'" },
  ], "req-422");
}

export function mockBrowserTimezone(zone: string) {
  const real = Intl.DateTimeFormat.prototype.resolvedOptions;
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockImplementation(function (this: Intl.DateTimeFormat) {
    return { ...real.call(this), timeZone: zone };
  });
}
