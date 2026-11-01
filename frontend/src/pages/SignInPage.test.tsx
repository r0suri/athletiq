import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { fakeAuth, renderRoutes, withDestinations } from "../test/utils";
import { SignInPage } from "./SignInPage";

function cognitoError(name: string) {
  return Object.assign(new Error(name), { name });
}

async function fillAndSubmit() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), "  rahul@example.com ");
  await user.type(screen.getByLabelText("Password"), "Athletiq2026");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("SignInPage", () => {
  it("signs in with the trimmed email and returns to the requested page", async () => {
    const signIn = vi.fn().mockResolvedValue("signedIn");
    const routes = [...withDestinations("/signin", <SignInPage />), { path: "/workouts", element: <p>workouts page</p> }];
    renderRoutes(routes, { auth: fakeAuth({ signIn }), path: "/signin", state: { from: "/workouts" } });

    await fillAndSubmit();

    expect(signIn).toHaveBeenCalledWith("rahul@example.com", "Athletiq2026");
    expect(await screen.findByText("workouts page")).toBeInTheDocument();
  });

  it("sends unconfirmed users to the confirmation step", async () => {
    const signIn = vi.fn().mockResolvedValue("needsConfirmation");
    renderRoutes(withDestinations("/signin", <SignInPage />), { auth: fakeAuth({ signIn }), path: "/signin" });

    await fillAndSubmit();

    expect(await screen.findByText("confirm page")).toBeInTheDocument();
  });

  it("explains a wrong password without saying whether the account exists", async () => {
    const signIn = vi.fn().mockRejectedValue(cognitoError("NotAuthorizedException"));
    renderRoutes(withDestinations("/signin", <SignInPage />), { auth: fakeAuth({ signIn }), path: "/signin" });

    await fillAndSubmit();

    expect(await screen.findByRole("alert")).toHaveTextContent("That email and password don't match");
  });

  it("shows the session-expired notice", () => {
    renderRoutes(withDestinations("/signin", <SignInPage />), {
      auth: fakeAuth({ notice: "Your session has ended. Sign in again to continue." }),
      path: "/signin",
    });
    expect(screen.getByText(/session has ended/)).toBeInTheDocument();
  });
});
