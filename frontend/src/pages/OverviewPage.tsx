import { Link } from "react-router";

import { useAuth } from "../auth/context";
import { goalLabel } from "../profile/goals";
import { useProfile } from "../profile/ProfileProvider";

export function OverviewPage() {
  const { email } = useAuth();
  const { profile } = useProfile();

  return (
    <section className="max-w-2xl">
      <h1 className="text-3xl font-semibold">Overview</h1>
      <p className="mt-1 text-muted">Signed in as {email}.</p>

      <h2 className="mt-10 text-xl font-semibold">Your profile</h2>
      <dl className="mt-3 grid grid-cols-[8rem_1fr] gap-y-2 text-base">
        <dt className="text-muted">Goal</dt>
        <dd>{goalLabel(profile.goal)}</dd>
        <dt className="text-muted">Timezone</dt>
        <dd>{profile.timezone}</dd>
      </dl>
      <Link to="/settings" className="mt-4 inline-block text-action underline-offset-4 hover:underline">
        Change in Settings
      </Link>
    </section>
  );
}
