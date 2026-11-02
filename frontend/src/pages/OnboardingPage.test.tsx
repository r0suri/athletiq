import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { routes } from "../App";
import { mockBrowserTimezone, savingApi, timezone422, UNCONFIGURED } from "../test/profiles";
import { fakeAuth, renderRoutes } from "../test/utils";

const auth = fakeAuth({ status: "signedIn", email: "rahul@example.com" });

async function openOnboarding(api: Record<string, unknown>) {
  const rendered = renderRoutes(routes, { auth, api, path: "/onboarding" });
  await screen.findByRole("heading", { name: "Set up your training" });
  return rendered;
}

describe("OnboardingPage", () => {
  it("prefills the browser's timezone", async () => {
    mockBrowserTimezone("Europe/London");
    await openOnboarding(savingApi(UNCONFIGURED));

    expect(screen.getByLabelText("Timezone")).toHaveValue("Europe/London");
    expect(screen.getByText(/Detected from this browser/)).toBeInTheDocument();
  });

  it("saves the chosen goal and timezone, then goes to the app", async () => {
    mockBrowserTimezone("Europe/London");
    const user = userEvent.setup();
    const api = savingApi(UNCONFIGURED);
    const { router } = await openOnboarding(api);

    await user.click(screen.getByRole("radio", { name: /Endurance/ }));
    await user.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(api.putProfile).toHaveBeenCalledWith({ goal: "endurance", timezone: "Europe/London" });
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText("Endurance")).toBeInTheDocument(); // provider updated without refetching
    expect(api.getProfile).toHaveBeenCalledTimes(1);
  });

  it("lets the user change the detected timezone", async () => {
    mockBrowserTimezone("Europe/London");
    const user = userEvent.setup();
    const api = savingApi(UNCONFIGURED);
    await openOnboarding(api);

    const field = screen.getByLabelText("Timezone");
    await user.clear(field);
    await user.type(field, "Asia/Tokyo");
    await user.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(api.putProfile).toHaveBeenCalledWith({ goal: "general_fitness", timezone: "Asia/Tokyo" });
  });

  it("shows the backend's timezone error next to the field and stays on the page", async () => {
    const user = userEvent.setup();
    const api = { ...savingApi(UNCONFIGURED), putProfile: vi.fn().mockRejectedValue(timezone422()) };
    const { router } = await openOnboarding(api);

    await user.clear(screen.getByLabelText("Timezone"));
    await user.type(screen.getByLabelText("Timezone"), "Mars/Olympus");
    await user.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(await screen.findByText("Must be an IANA timezone name, e.g. 'America/New_York'")).toBeInTheDocument();
    expect(screen.getByLabelText("Timezone")).toHaveAttribute("aria-invalid", "true");
    expect(router.state.location.pathname).toBe("/onboarding");
  });

  it("requires a timezone before calling the API", async () => {
    const user = userEvent.setup();
    const api = savingApi(UNCONFIGURED);
    await openOnboarding(api);

    await user.clear(screen.getByLabelText("Timezone"));
    await user.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(screen.getByText(/Enter a timezone/)).toBeInTheDocument();
    expect(api.putProfile).not.toHaveBeenCalled();
  });

  it("shows other failures as a form error", async () => {
    const user = userEvent.setup();
    const api = {
      ...savingApi(UNCONFIGURED),
      putProfile: vi.fn().mockRejectedValue(new ApiError(500, "INTERNAL_ERROR", "An unexpected error occurred.")),
    };
    await openOnboarding(api);

    await user.click(screen.getByRole("button", { name: "Save and continue" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("An unexpected error occurred.");
    expect(screen.getByRole("button", { name: "Save and continue" })).toBeEnabled();
  });
});
