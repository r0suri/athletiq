import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { useAuth } from "../auth/context";
import { authErrorMessage } from "../auth/errors";
import { Alert } from "../components/Alert";
import { AuthLayout } from "../components/AuthLayout";
import { Button } from "../components/Button";
import { TextField } from "../components/TextField";

export function ConfirmPage() {
  const { confirmSignUp, resendCode } = useAuth();
  const navigate = useNavigate();
  const initialEmail = ((useLocation().state ?? {}) as { email?: string }).email ?? "";
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await confirmSignUp(email.trim(), code.trim());
      if (result === "signedIn") {
        navigate("/", { replace: true });
      } else {
        navigate("/signin", {
          replace: true,
          state: { email: email.trim(), message: "Email confirmed. Sign in to continue." },
        });
      }
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setError(null);
    setInfo(null);
    try {
      await resendCode(email.trim());
      setInfo(`A new code is on its way to ${email.trim()}.`);
    } catch (err) {
      setError(authErrorMessage(err));
    }
  }

  return (
    <AuthLayout
      title="Confirm your email"
      intro={initialEmail ? `Enter the 6-digit code we sent to ${initialEmail}.` : "Enter the 6-digit code from your email."}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
        {error && <Alert tone="error">{error}</Alert>}
        {info && <Alert tone="success">{info}</Alert>}
        {!initialEmail && (
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        )}
        <TextField
          label="Confirmation code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        />
        <Button type="submit" busy={busy} disabled={!email || code.length !== 6}>
          {busy ? "Confirming…" : "Confirm email"}
        </Button>
        <Button type="button" variant="quiet" onClick={() => void handleResend()} disabled={!email}>
          Send a new code
        </Button>
      </form>
      <p className="mt-8 text-sm text-muted">
        <Link to="/signin" className="text-action underline-offset-4 hover:underline">
          Back to sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
