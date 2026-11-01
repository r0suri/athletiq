import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { Profile } from "../api/types";
import { fakeAuth, renderRoutes } from "../test/utils";
import { OverviewPage } from "./OverviewPage";

const routes = [{ path: "/", element: <OverviewPage /> }];
const auth = fakeAuth({ status: "signedIn", email: "rahul@example.com" });

describe("OverviewPage", () => {
  it("shows the profile returned by the API", async () => {
    const profile: Profile = { goal: "endurance", timezone: "America/New_York", configured: true, updated_at: "2026-11-01T23:00:20Z" };
    renderRoutes(routes, { auth, api: { getProfile: vi.fn().mockResolvedValue(profile) } });

    expect(await screen.findByText("Endurance")).toBeInTheDocument();
    expect(screen.getByText("America/New_York")).toBeInTheDocument();
  });

  it("shows the error and request reference, and retries", async () => {
    const user = userEvent.setup();
    const getProfile = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(500, "INTERNAL_ERROR", "An unexpected error occurred.", [], "req-9"))
      .mockResolvedValueOnce({ goal: "strength", timezone: "UTC", configured: false, updated_at: null });
    renderRoutes(routes, { auth, api: { getProfile } });

    expect(await screen.findByRole("alert")).toHaveTextContent("An unexpected error occurred.");
    expect(screen.getByText("Reference: req-9")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Strength")).toBeInTheDocument();
    expect(getProfile).toHaveBeenCalledTimes(2);
  });
});
