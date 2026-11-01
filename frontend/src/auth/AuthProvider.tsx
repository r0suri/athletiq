/**
 * Cognito authentication via Amplify Auth (v6). Amplify keeps tokens in browser
 * storage and refreshes them with the refresh token; the app never stores tokens
 * itself and only passes passwords straight to Cognito.
 */
import { Amplify } from "aws-amplify";
import * as auth from "aws-amplify/auth";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import type { AppConfig } from "../config";
import { AuthContext, type AuthContextValue, type AuthStatus } from "./context";

let configured = false;

export function configureAmplify(config: AppConfig): void {
  if (configured) return;
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.userPoolId,
        userPoolClientId: config.userPoolClientId,
        loginWith: { email: true },
      },
    },
  });
  configured = true;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [email, setEmail] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadUser = useCallback(async () => {
    try {
      const user = await auth.getCurrentUser();
      setEmail(user.signInDetails?.loginId ?? user.username);
      setStatus("signedIn");
    } catch {
      setEmail(null);
      setStatus("signedOut");
    }
  }, []);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  const expireSession = useCallback(() => {
    setNotice("Your session has ended. Sign in again to continue.");
    setEmail(null);
    setStatus("signedOut");
    void auth.signOut().catch(() => undefined);
  }, []);

  const getAccessToken = useCallback(async (forceRefresh: boolean) => {
    try {
      const session = await auth.fetchAuthSession({ forceRefresh });
      return session.tokens?.accessToken?.toString() ?? null;
    } catch {
      return null;
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      email,
      notice,
      signIn: async (userEmail, password) => {
        setNotice(null);
        const result = await auth.signIn({ username: userEmail, password });
        if (result.nextStep.signInStep === "CONFIRM_SIGN_UP") return "needsConfirmation";
        if (!result.isSignedIn) {
          throw new Error(`Unsupported sign-in step: ${result.nextStep.signInStep}`);
        }
        await loadUser();
        return "signedIn";
      },
      signUp: async (userEmail, password) => {
        await auth.signUp({
          username: userEmail,
          password,
          options: { userAttributes: { email: userEmail }, autoSignIn: true },
        });
      },
      confirmSignUp: async (userEmail, code) => {
        const result = await auth.confirmSignUp({ username: userEmail, confirmationCode: code });
        if (result.nextStep.signUpStep === "COMPLETE_AUTO_SIGN_IN") {
          try {
            await auth.autoSignIn();
            await loadUser();
            return "signedIn";
          } catch {
            // Auto sign-in only works in the same browser session as sign-up.
          }
        }
        return "signInRequired";
      },
      resendCode: async (userEmail) => {
        await auth.resendSignUpCode({ username: userEmail });
      },
      signOut: async () => {
        try {
          await auth.signOut();
        } finally {
          setEmail(null);
          setStatus("signedOut");
        }
      },
      expireSession,
      getAccessToken,
    }),
    [status, email, notice, loadUser, expireSession, getAccessToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
