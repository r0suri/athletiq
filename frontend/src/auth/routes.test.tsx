import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { fakeAuth, renderRoutes } from "../test/utils";
import { PublicOnly, RequireAuth } from "./routes";

const routes = [
  { element: <RequireAuth />, children: [{ path: "/", element: <p>private overview</p> }] },
  { element: <PublicOnly />, children: [{ path: "/signin", element: <p>sign-in form</p> }] },
];

describe("route guards", () => {
  it("sends signed-out users to sign in", () => {
    const { router } = renderRoutes(routes, { auth: fakeAuth({ status: "signedOut" }) });
    expect(screen.getByText("sign-in form")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/signin");
    expect(router.state.location.state).toEqual({ from: "/" });
  });

  it("shows protected pages to signed-in users", () => {
    renderRoutes(routes, { auth: fakeAuth({ status: "signedIn", email: "a@b.co" }) });
    expect(screen.getByText("private overview")).toBeInTheDocument();
  });

  it("waits while the session is being restored", () => {
    renderRoutes(routes, { auth: fakeAuth({ status: "loading" }) });
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("private overview")).not.toBeInTheDocument();
  });

  it("sends signed-in users away from the sign-in page", () => {
    renderRoutes(routes, { auth: fakeAuth({ status: "signedIn" }), path: "/signin" });
    expect(screen.getByText("private overview")).toBeInTheDocument();
  });
});
