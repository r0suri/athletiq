import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { routes } from "../App";
import { CONFIGURED, UNCONFIGURED } from "../test/profiles";
import { fakeAuth, renderRoutes } from "../test/utils";

const auth = fakeAuth({ status: "signedIn", email: "rahul@example.com" });

describe("profile gate", () => {
  it("sends users without a saved profile to onboarding", async () => {
    const { router } = renderRoutes(routes, { auth, api: { getProfile: vi.fn().mockResolvedValue(UNCONFIGURED) } });

    expect(await screen.findByRole("heading", { name: "Set up your training" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/onboarding");
  });

  it("also redirects deep links such as /settings", async () => {
    const { router } = renderRoutes(routes, {
      auth,
      api: { getProfile: vi.fn().mockResolvedValue(UNCONFIGURED) },
      path: "/settings",
    });
    await screen.findByRole("heading", { name: "Set up your training" });
    expect(router.state.location.pathname).toBe("/onboarding");
  });

  it("lets configured users into the app", async () => {
    renderRoutes(routes, { auth, api: { getProfile: vi.fn().mockResolvedValue(CONFIGURED) } });
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByText("Endurance")).toBeInTheDocument();
  });

  it("sends configured users away from onboarding", async () => {
    const { router } = renderRoutes(routes, {
      auth,
      api: { getProfile: vi.fn().mockResolvedValue(CONFIGURED) },
      path: "/onboarding",
    });
    await screen.findByRole("heading", { name: "Overview" });
    expect(router.state.location.pathname).toBe("/");
  });

  it("loads the profile once and shares it across pages", async () => {
    const user = userEvent.setup();
    const getProfile = vi.fn().mockResolvedValue(CONFIGURED);
    renderRoutes(routes, { auth, api: { getProfile } });
    await screen.findByRole("heading", { name: "Overview" });

    await user.click(screen.getByRole("link", { name: "Settings" }));

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(getProfile).toHaveBeenCalledTimes(1);
  });

  it("shows a retry when the profile can't be loaded", async () => {
    const user = userEvent.setup();
    const getProfile = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(0, "NETWORK_ERROR", "Can't reach AthletIQ. Check your connection and try again."))
      .mockResolvedValueOnce(CONFIGURED);
    renderRoutes(routes, { auth, api: { getProfile } });

    expect(await screen.findByRole("heading", { name: "We couldn't load your account" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
  });
});
