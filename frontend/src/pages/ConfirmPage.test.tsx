import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { fakeAuth, renderRoutes, withDestinations } from "../test/utils";
import { ConfirmPage } from "./ConfirmPage";

const routes = withDestinations("/confirm", <ConfirmPage />);
const state = { email: "rahul@example.com" };

describe("ConfirmPage", () => {
  it("confirms and signs in automatically when possible", async () => {
    const user = userEvent.setup();
    const confirmSignUp = vi.fn().mockResolvedValue("signedIn");
    renderRoutes(routes, { auth: fakeAuth({ confirmSignUp }), path: "/confirm", state });

    await user.type(screen.getByLabelText("Confirmation code"), "12a3456");
    await user.click(screen.getByRole("button", { name: "Confirm email" }));

    expect(confirmSignUp).toHaveBeenCalledWith("rahul@example.com", "123456"); // non-digits stripped
    expect(await screen.findByText("overview page")).toBeInTheDocument();
  });

  it("sends the user to sign in when auto sign-in isn't available", async () => {
    const user = userEvent.setup();
    const confirmSignUp = vi.fn().mockResolvedValue("signInRequired");
    renderRoutes(routes, { auth: fakeAuth({ confirmSignUp }), path: "/confirm", state });

    await user.type(screen.getByLabelText("Confirmation code"), "123456");
    await user.click(screen.getByRole("button", { name: "Confirm email" }));

    expect(await screen.findByText("sign-in page")).toBeInTheDocument();
  });

  it("resends the code", async () => {
    const user = userEvent.setup();
    const resendCode = vi.fn().mockResolvedValue(undefined);
    renderRoutes(routes, { auth: fakeAuth({ resendCode }), path: "/confirm", state });

    await user.click(screen.getByRole("button", { name: "Send a new code" }));

    expect(resendCode).toHaveBeenCalledWith("rahul@example.com");
    expect(await screen.findByText(/new code is on its way/)).toBeInTheDocument();
  });
});
