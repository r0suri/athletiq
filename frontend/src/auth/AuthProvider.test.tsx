import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const amplifyAuth = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  fetchAuthSession: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  confirmSignUp: vi.fn(),
  autoSignIn: vi.fn(),
  resendSignUpCode: vi.fn(),
  signOut: vi.fn(),
}));
vi.mock("aws-amplify/auth", () => amplifyAuth);

import { AuthProvider } from "./AuthProvider";
import { useAuth, type AuthContextValue } from "./context";

let captured: AuthContextValue;
function Probe() {
  captured = useAuth();
  return <p>status:{captured.status}</p>;
}

function renderProvider() {
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

beforeEach(() => {
  Object.values(amplifyAuth).forEach((fn) => fn.mockReset());
  amplifyAuth.signOut.mockResolvedValue(undefined);
});

describe("AuthProvider", () => {
  it("restores an existing session on load", async () => {
    amplifyAuth.getCurrentUser.mockResolvedValue({ username: "uuid", signInDetails: { loginId: "rahul@example.com" } });
    renderProvider();
    expect(await screen.findByText("status:signedIn")).toBeInTheDocument();
    expect(captured.email).toBe("rahul@example.com");
  });

  it("is signed out when there is no session", async () => {
    amplifyAuth.getCurrentUser.mockRejectedValue(new Error("UserUnAuthenticatedException"));
    renderProvider();
    expect(await screen.findByText("status:signedOut")).toBeInTheDocument();
  });

  it("returns the access token, or null when the session can't be refreshed", async () => {
    amplifyAuth.getCurrentUser.mockRejectedValue(new Error("none"));
    renderProvider();
    await screen.findByText("status:signedOut");

    amplifyAuth.fetchAuthSession.mockResolvedValueOnce({ tokens: { accessToken: { toString: () => "jwt-abc" } } });
    await expect(captured.getAccessToken(false)).resolves.toBe("jwt-abc");

    amplifyAuth.fetchAuthSession.mockRejectedValueOnce(new Error("refresh token expired"));
    await expect(captured.getAccessToken(true)).resolves.toBeNull();
    expect(amplifyAuth.fetchAuthSession).toHaveBeenLastCalledWith({ forceRefresh: true });
  });

  it("reports when an unconfirmed user tries to sign in", async () => {
    amplifyAuth.getCurrentUser.mockRejectedValue(new Error("none"));
    renderProvider();
    await screen.findByText("status:signedOut");
    amplifyAuth.signIn.mockResolvedValue({ isSignedIn: false, nextStep: { signInStep: "CONFIRM_SIGN_UP" } });

    await expect(captured.signIn("a@b.co", "pw")).resolves.toBe("needsConfirmation");
  });

  it("expires the session with a notice and signs out of Amplify", async () => {
    amplifyAuth.getCurrentUser.mockResolvedValue({ username: "uuid", signInDetails: { loginId: "a@b.co" } });
    renderProvider();
    await screen.findByText("status:signedIn");

    act(() => captured.expireSession());

    await waitFor(() => expect(screen.getByText("status:signedOut")).toBeInTheDocument());
    expect(captured.notice).toMatch(/session has ended/);
    expect(amplifyAuth.signOut).toHaveBeenCalled();
  });
});
