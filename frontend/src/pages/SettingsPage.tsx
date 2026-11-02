import { useState } from "react";

import { useAuth } from "../auth/context";
import { Alert } from "../components/Alert";
import { ProfileForm } from "../components/ProfileForm";
import { useProfile } from "../profile/ProfileProvider";

export function SettingsPage() {
  const { profile } = useProfile();
  const { email } = useAuth();
  const [savedAt, setSavedAt] = useState<number | null>(null);

  return (
    <section className="max-w-2xl">
      <h1 className="text-3xl font-semibold">Settings</h1>
      <p className="mt-1 text-muted">Signed in as {email}.</p>

      <div className="mt-10">
        {savedAt && (
          <div className="mb-6">
            <Alert tone="success">Settings saved.</Alert>
          </div>
        )}
        <ProfileForm
          // Re-mount after each save so "unchanged" is measured from the saved values.
          key={`${profile.goal}|${profile.timezone}|${savedAt ?? 0}`}
          initial={{ goal: profile.goal, timezone: profile.timezone }}
          submitLabel="Save changes"
          savingLabel="Saving…"
          requireChange
          onSaved={() => setSavedAt(Date.now())}
        />
      </div>
    </section>
  );
}
