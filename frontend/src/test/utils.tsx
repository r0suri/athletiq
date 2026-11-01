import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";
import { vi } from "vitest";

import { ApiContext } from "../api/ApiProvider";
import type { Api } from "../api/endpoints";
import { AuthContext, type AuthContextValue } from "../auth/context";

export function fakeAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    status: "signedOut",
    email: null,
    notice: null,
    signIn: vi.fn(),
    signUp: vi.fn(),
    confirmSignUp: vi.fn(),
    resendCode: vi.fn(),
    signOut: vi.fn(),
    expireSession: vi.fn(),
    getAccessToken: vi.fn(),
    ...overrides,
  };
}

/** Render routes with a fake auth context and (optionally) a fake API. */
export function renderRoutes(
  routes: RouteObject[],
  { auth = fakeAuth(), api, path = "/", state }: { auth?: AuthContextValue; api?: Partial<Api>; path?: string; state?: unknown } = {},
) {
  const router = createMemoryRouter(routes, { initialEntries: [{ pathname: path, state }] });
  const tree: ReactElement = (
    <AuthContext.Provider value={auth}>
      <ApiContext.Provider value={(api ?? {}) as Api}>
        <RouterProvider router={router} />
      </ApiContext.Provider>
    </AuthContext.Provider>
  );
  return { router, ...render(tree) };
}

/** A page plus stub destinations, so tests can assert where navigation went. */
export function withDestinations(path: string, element: ReactElement): RouteObject[] {
  return [
    { path, element },
    { path: "/", element: <p>overview page</p> },
    { path: "/signin", element: <p>sign-in page</p> },
    { path: "/confirm", element: <p>confirm page</p> },
  ];
}
