import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { fakeAuth, renderRoutes, withDestinations } from "../test/utils";
import { SignUpPage } from "./SignUpPage";

describe("SignUpPage", () => {
  it("keeps the button disabled until the password meets the policy", async () => {
    const user = userEvent.setup();
    renderRoutes(withDestinations("/signup", <SignUpPage />), { path: "/signup" });
    const button = screen.getByRole("button", { name: "Create account" });

    await user.type(screen.getByLabelText("Email"), "rahul@example.com");
    await user.type(screen.getByLabelText("Password"), "athletiq");
    expect(button).toBeDisabled();
    expect(screen.getByText(/An uppercase letter/)).toHaveTextContent("(not met)");

    await user.clear(screen.getByLabelText("Password"));
    await user.type(screen.getByLabelText("Password"), "Athletiq2026");
    expect(button).toBeEnabled();
  });

  it("creates the account and moves to confirmation", async () => {
    const user = userEvent.setup();
    const signUp = vi.fn().mockResolvedValue(undefined);
    renderRoutes(withDestinations("/signup", <SignUpPage />), { auth: fakeAuth({ signUp }), path: "/signup" });

    await user.type(screen.getByLabelText("Email"), "rahul@example.com");
    await user.type(screen.getByLabelText("Password"), "Athletiq2026");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(signUp).toHaveBeenCalledWith("rahul@example.com", "Athletiq2026");
    expect(await screen.findByText("confirm page")).toBeInTheDocument();
  });

  it("explains when the email is already registered", async () => {
    const user = userEvent.setup();
    const signUp = vi.fn().mockRejectedValue(Object.assign(new Error("x"), { name: "UsernameExistsException" }));
    renderRoutes(withDestinations("/signup", <SignUpPage />), { auth: fakeAuth({ signUp }), path: "/signup" });

    await user.type(screen.getByLabelText("Email"), "rahul@example.com");
    await user.type(screen.getByLabelText("Password"), "Athletiq2026");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
  });
});
