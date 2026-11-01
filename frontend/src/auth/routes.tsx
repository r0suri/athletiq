import { Navigate, Outlet, useLocation } from "react-router";

import { FullPageSpinner } from "../components/Spinner";
import { useAuth } from "./context";

/** Renders child routes only for signed-in users; otherwise sends them to sign in. */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "signedOut") {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

/** Sign-in and sign-up pages: signed-in users go straight to the app. */
export function PublicOnly() {
  const { status } = useAuth();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "signedIn") return <Navigate to="/" replace />;
  return <Outlet />;
}
