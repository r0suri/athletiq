import { useApi } from "../api/ApiProvider";
import { useAuth } from "../auth/context";
import { ErrorState } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";

const GOAL_LABELS = {
  strength: "Strength",
  endurance: "Endurance",
  general_fitness: "General fitness",
} as const;

export function OverviewPage() {
  const api = useApi();
  const { email } = useAuth();
  const profile = useAsync(() => api.getProfile(), [api]);

  return (
    <section className="max-w-2xl">
      <h1 className="text-3xl font-semibold">Overview</h1>
      <p className="mt-1 text-muted">Signed in as {email}.</p>

      <h2 className="mt-10 text-xl font-semibold">Your profile</h2>
      <div className="mt-3">
        {profile.status === "loading" && <Spinner label="Loading your profile" />}
        {profile.status === "error" && <ErrorState error={profile.error} onRetry={profile.reload} />}
        {profile.status === "success" && (
          <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-base">
            <dt className="text-muted">Goal</dt>
            <dd>{GOAL_LABELS[profile.data.goal]}</dd>
            <dt className="text-muted">Timezone</dt>
            <dd>{profile.data.timezone}</dd>
            <dt className="text-muted">Saved</dt>
            <dd>{profile.data.configured ? "Yes" : "Not yet, these are the defaults"}</dd>
          </dl>
        )}
      </div>
    </section>
  );
}
