import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { routes } from "../App";
import { CONFIGURED, mockBrowserTimezone, savingApi, timezone422 } from "../test/profiles";
import { fakeAuth, renderRoutes } from "../test/utils";

const auth = fakeAuth({ status: "signedIn", email: "rahul@example.com" });

async function openSettings(api: Record<string, unknown>) {
  const rendered = renderRoutes(routes, { auth, api, path: "/settings" });
  await screen.findByRole("heading", { name: "Settings" });
  return rendered;
}

describe("SettingsPage", () => {
  it("shows the saved profile and disables saving until something changes", async () => {
    mockBrowserTimezone("America/New_York");
    await openSettings(savingApi(CONFIGURED));

    expect(screen.getByRole("radio", { name: /Endurance/ })).toBeChecked();
    expect(screen.getByLabelText("Timezone")).toHaveValue("America/New_York");
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
  });

  it("saves a new goal and confirms it", async () => {
    mockBrowserTimezone("America/New_York");
    const user = userEvent.setup();
    const api = savingApi(CONFIGURED);
    await openSettings(api);

    await user.click(screen.getByRole("radio", { name: /Strength/ }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(api.putProfile).toHaveBeenCalledWith({ goal: "strength", timezone: "America/New_York" });
    expect(await screen.findByText("Settings saved.")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Strength/ })).toBeChecked();
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled(); // clean again

    await user.click(screen.getByRole("link", { name: "Overview" }));
    expect(await screen.findByText("Strength")).toBeInTheDocument(); // shared profile updated
  });

  it("offers the browser's timezone when it differs from the saved one", async () => {
    mockBrowserTimezone("Europe/Berlin");
    const user = userEvent.setup();
    const api = savingApi(CONFIGURED);
    await openSettings(api);

    await user.click(screen.getByRole("button", { name: "Use Europe/Berlin" }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(api.putProfile).toHaveBeenCalledWith({ goal: "endurance", timezone: "Europe/Berlin" });
  });

  it("shows a backend validation error on the timezone field", async () => {
    const user = userEvent.setup();
    const api = { ...savingApi(CONFIGURED), putProfile: vi.fn().mockRejectedValue(timezone422()) };
    await openSettings(api);

    await user.clear(screen.getByLabelText("Timezone"));
    await user.type(screen.getByLabelText("Timezone"), "Nowhere/Land");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText(/Must be an IANA timezone name/)).toBeInTheDocument();
    expect(screen.queryByText("Settings saved.")).not.toBeInTheDocument();
  });
});
