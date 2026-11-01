import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { useAuth } from "../auth/context";
import { authErrorMessage } from "../auth/errors";
import { Alert } from "../components/Alert";
import { AuthLayout } from "../components/AuthLayout";
import { Button } from "../components/Button";
import { TextField } from "../components/TextField";

interface LocationState {
  from?: string;
  email?: string;
  message?: string;
}

export function SignInPage() {
  const { signIn, notice } = useAuth();
  const navigate = useNavigate();
  const state = (useLocation().state ?? {}) as LocationState;
  const [email, setEmail] = useState(state.email ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await signIn(email.trim(), password);
      if (result === "needsConfirmation") {
        navigate("/confirm", { state: { email: email.trim() } });
      } else {
        navigate(state.from ?? "/", { replace: true });
      }
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Sign in" intro="Log your training and see how your load is trending.">
      <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
        {state.message && <Alert tone="success">{state.message}</Alert>}
        {notice && !state.message && <Alert tone="info">{notice}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" busy={busy} disabled={!email || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="mt-8 text-sm text-muted">
        New to AthletIQ?{" "}
        <Link to="/signup" className="text-action underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
