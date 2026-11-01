import { createContext, useContext } from "react";

export type AuthStatus = "loading" | "signedIn" | "signedOut";
export type SignInResult = "signedIn" | "needsConfirmation";
export type ConfirmResult = "signedIn" | "signInRequired";

export interface AuthContextValue {
  status: AuthStatus;
  email: string | null;
  /** One-off message for the sign-in screen, e.g. after a session expires. */
  notice: string | null;
  signIn: (email: string, password: string) => Promise<SignInResult>;
  signUp: (email: string, password: string) => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<ConfirmResult>;
  resendCode: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  /** Called by the API client when the session can't be refreshed. */
  expireSession: () => void;
  /** Access token for API calls (refreshes automatically; null if signed out). */
  getAccessToken: (forceRefresh: boolean) => Promise<string | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
