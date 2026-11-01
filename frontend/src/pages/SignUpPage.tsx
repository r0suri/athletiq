import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { useAuth } from "../auth/context";
import { authErrorMessage } from "../auth/errors";
import { PASSWORD_RULES, passwordMeetsPolicy } from "../auth/password";
import { Alert } from "../components/Alert";
import { AuthLayout } from "../components/AuthLayout";
import { Button } from "../components/Button";
import { TextField } from "../components/TextField";

export function SignUpPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const valid = email.includes("@") && passwordMeetsPolicy(password);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setError(null);
    setBusy(true);
    try {
      await signUp(email.trim(), password);
      navigate("/confirm", { state: { email: email.trim() } });
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const rules = (
    <ul className="mt-1 space-y-0.5" aria-label="Password requirements">
      {PASSWORD_RULES.map((rule) => {
        const met = rule.test(password);
        return (
          <li key={rule.id} className={met ? "text-easy" : "text-muted"}>
            <span aria-hidden>{met ? "✓" : "○"}</span> {rule.label}
            <span className="sr-only">{met ? " (met)" : " (not met)"}</span>
          </li>
        );
      })}
    </ul>
  );

  return (
    <AuthLayout title="Create an account" intro="We'll email you a code to confirm your address.">
      <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
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
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint={rules}
        />
        <Button type="submit" busy={busy} disabled={!valid}>
          {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-8 text-sm text-muted">
        Already have an account?{" "}
        <Link to="/signin" className="text-action underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
