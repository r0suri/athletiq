import { useNavigate } from "react-router";

import { useAuth } from "../auth/context";
import { Button } from "../components/Button";
import { ProfileForm } from "../components/ProfileForm";
import { Wordmark } from "../components/Wordmark";
import { useProfile } from "../profile/ProfileProvider";
import { detectTimezone } from "../profile/timezone";

export function OnboardingPage() {
  const navigate = useNavigate();
  const { signOut } = useAuth();
  const { profile } = useProfile();

  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex max-w-2xl items-center justify-between px-5 py-4">
        <Wordmark />
        <Button variant="quiet" onClick={() => void signOut()}>
          Sign out
        </Button>
      </header>
      <main className="mx-auto max-w-2xl px-5 pt-8 pb-16">
        <h1 className="text-3xl font-semibold">Set up your training</h1>
        <p className="mt-2 mb-10 max-w-prose text-muted">
          Your goal sets your weekly session target. Your timezone decides which day each workout counts toward. You can
          change both later in Settings.
        </p>
        <ProfileForm
          initial={{ goal: profile.goal, timezone: detectTimezone() ?? profile.timezone }}
          submitLabel="Save and continue"
          savingLabel="Saving…"
          onSaved={() => navigate("/", { replace: true })}
        />
      </main>
    </div>
  );
}
