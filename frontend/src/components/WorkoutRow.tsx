import { useState } from "react";

import type { Workout } from "../api/types";
import { BAND_STYLES, effortBand, RPE_LABELS } from "../workouts/effort";
import { formatDate, formatDistance, formatDuration, formatLoad, TYPE_LABELS } from "../workouts/format";
import { Button } from "./Button";

interface WorkoutRowProps {
  workout: Workout;
  onDelete: (workout: Workout) => Promise<void>;
}

export function WorkoutRow({ workout, onDelete }: WorkoutRowProps) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const band = BAND_STYLES[effortBand(workout.rpe)];
  const label = TYPE_LABELS[workout.type];

  const details = [formatDuration(workout.duration_min)];
  if (workout.distance_km != null) details.push(formatDistance(workout.distance_km));
  if (workout.type === "strength" && workout.exercises && workout.exercises.length > 0) {
    details.push(`${workout.exercises.length} exercise${workout.exercises.length === 1 ? "" : "s"}`);
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      await onDelete(workout);
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <li className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-2 border-b border-line py-4 sm:grid-cols-[9rem_1fr_7rem_6rem_auto]">
      <p className="text-sm text-muted sm:order-none">{formatDate(workout.date)}</p>
      <div className="col-span-2 sm:col-span-1">
        <p className="font-medium">{label}</p>
        <p className="text-sm text-muted">{details.join(", ")}</p>
        {workout.notes && <p className="mt-1 line-clamp-2 text-sm text-muted">{workout.notes}</p>}
      </div>
      <p className={`text-sm ${band.text}`} title={`Session RPE ${workout.rpe}: ${RPE_LABELS[workout.rpe]}`}>
        RPE {workout.rpe}
      </p>
      <p className="font-display text-lg font-semibold tabular" title="Session load: duration × RPE">
        {formatLoad(workout.load)} <span className="text-xs font-normal text-muted">load</span>
      </p>
      <div className="col-span-2 flex justify-end gap-2 sm:col-span-1">
        {confirming ? (
          <>
            <Button variant="secondary" busy={deleting} onClick={() => void confirmDelete()} className="border-hard/60 text-hard">
              {deleting ? "Deleting…" : `Delete ${label.toLowerCase()}`}
            </Button>
            <Button variant="quiet" onClick={() => setConfirming(false)} disabled={deleting}>
              Cancel
            </Button>
          </>
        ) : (
          <Button variant="quiet" onClick={() => setConfirming(true)} aria-label={`Delete ${label.toLowerCase()} on ${formatDate(workout.date)}`}>
            Delete
          </Button>
        )}
      </div>
    </li>
  );
}
