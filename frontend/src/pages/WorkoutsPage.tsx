import { useState } from "react";
import { Link, useLocation } from "react-router";

import { useApi } from "../api/ApiProvider";
import type { Workout, WorkoutType } from "../api/types";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { ErrorState, errorMessage } from "../components/ErrorState";
import { Spinner } from "../components/Spinner";
import { WorkoutRow } from "../components/WorkoutRow";
import { formatDate, formatLoad, TYPE_LABELS } from "../workouts/format";
import { useWorkoutHistory } from "../workouts/useWorkoutHistory";

const FILTERS: { value: WorkoutType | null; label: string }[] = [
  { value: null, label: "All" },
  { value: "run", label: "Runs" },
  { value: "ride", label: "Rides" },
  { value: "strength", label: "Strength" },
];

interface LoggedState {
  logged?: { type: WorkoutType; load: number; date: string };
}

export function WorkoutsPage() {
  const api = useApi();
  const logged = ((useLocation().state ?? {}) as LoggedState).logged;
  const [filter, setFilter] = useState<WorkoutType | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const history = useWorkoutHistory(api, filter);

  async function handleDelete(workout: Workout) {
    setDeleteError(null);
    try {
      await api.deleteWorkout(workout.id);
      history.remove(workout.id);
    } catch (error) {
      setDeleteError(errorMessage(error));
    }
  }

  const filterLabel = FILTERS.find((f) => f.value === filter)!.label.toLowerCase();

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Workouts</h1>
          <p className="mt-1 text-muted">Every session you've logged, newest first.</p>
        </div>
        <Link
          to="/workouts/new"
          className="inline-flex min-h-11 items-center rounded-md bg-action px-4 font-semibold text-bg hover:bg-action/90"
        >
          Log workout
        </Link>
      </div>

      {logged && (
        <div className="mt-6">
          <Alert tone="success">
            {TYPE_LABELS[logged.type]} on {formatDate(logged.date)} saved. Session load: {formatLoad(logged.load)}.
          </Alert>
        </div>
      )}

      <div className="mt-8 flex gap-1 overflow-x-auto" role="group" aria-label="Filter by type">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            type="button"
            aria-pressed={filter === f.value}
            onClick={() => setFilter(f.value)}
            className={`rounded-md px-3 py-2 text-sm whitespace-nowrap ${filter === f.value ? "bg-raised text-ink" : "text-muted hover:text-ink"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {deleteError && (
        <div className="mt-4">
          <Alert tone="error">{deleteError}</Alert>
        </div>
      )}

      <div className="mt-4">
        {history.status === "loading" && <Spinner label="Loading workouts" />}
        {history.status === "error" && <ErrorState error={history.error} onRetry={history.reload} />}
        {(history.status === "ready" || history.status === "loadingMore") && history.items.length === 0 && (
          <div className="rounded-md border border-dashed border-line px-6 py-10">
            {filter === null ? (
              <>
                <p className="font-medium">No workouts yet</p>
                <p className="mt-1 text-muted">Log your first session to start tracking your training load.</p>
                <Link to="/workouts/new" className="mt-4 inline-block text-action underline-offset-4 hover:underline">
                  Log your first workout
                </Link>
              </>
            ) : (
              <p className="text-muted">No {filterLabel} logged yet.</p>
            )}
          </div>
        )}
        {history.items.length > 0 && (
          <ul aria-label="Workout history" className="border-t border-line">
            {history.items.map((w) => (
              <WorkoutRow key={w.id} workout={w} onDelete={handleDelete} />
            ))}
          </ul>
        )}
        {history.hasMore && history.status !== "loading" && (
          <div className="mt-6 flex flex-col items-start gap-3">
            {history.error != null && <Alert tone="error">{errorMessage(history.error)}</Alert>}
            <Button variant="secondary" busy={history.status === "loadingMore"} onClick={() => void history.loadMore()}>
              {history.status === "loadingMore" ? "Loading…" : "Load more"}
            </Button>
          </div>
        )}
      </div>
    </section>
  );
}
