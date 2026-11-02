/**
 * Loads the signed-in user's profile once and gates the app on it:
 * users without a saved profile are sent to onboarding first.
 */
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useApi } from "../api/ApiProvider";
import type { Profile } from "../api/types";
import { useAuth } from "../auth/context";
import { Button } from "../components/Button";
import { ErrorState } from "../components/ErrorState";
import { FullPageSpinner } from "../components/Spinner";

interface ProfileContextValue {
  profile: Profile;
  /** Store a freshly saved profile without refetching. */
  setProfile: (profile: Profile) => void;
}

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function useProfile(): ProfileContextValue {
  const value = useContext(ProfileContext);
  if (!value) throw new Error("useProfile must be used inside <ProfileProvider>");
  return value;
}

type LoadState = { status: "loading" } | { status: "error"; error: unknown } | { status: "ready"; profile: Profile };

export function ProfileProvider({ children }: { children?: ReactNode }) {
  const api = useApi();
  const { signOut } = useAuth();
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    api.getProfile().then(
      (profile) => !cancelled && setState({ status: "ready", profile }),
      (error: unknown) => !cancelled && setState({ status: "error", error }),
    );
    return () => {
      cancelled = true;
    };
  }, [api, attempt]);

  const setProfile = useCallback((profile: Profile) => setState({ status: "ready", profile }), []);

  if (state.status === "loading") return <FullPageSpinner />;
  if (state.status === "error") {
    return (
      <main className="mx-auto max-w-md px-5 py-24">
        <h1 className="mb-4 text-2xl font-semibold">We couldn't load your account</h1>
        <ErrorState error={state.error} onRetry={() => setAttempt((n) => n + 1)} />
        <Button variant="quiet" className="mt-4" onClick={() => void signOut()}>
          Sign out
        </Button>
      </main>
    );
  }
  return (
    <ProfileContext.Provider value={{ profile: state.profile, setProfile }}>
      {children ?? <Outlet />}
    </ProfileContext.Provider>
  );
}

/** App pages: only for users who have finished onboarding. */
export function RequireProfile() {
  const { profile } = useProfile();
  const location = useLocation();
  if (!profile.configured) return <Navigate to="/onboarding" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

/** The onboarding page: users who already have a profile go to the app. */
export function OnboardingOnly() {
  const { profile } = useProfile();
  if (profile.configured) return <Navigate to="/" replace />;
  return <Outlet />;
}
