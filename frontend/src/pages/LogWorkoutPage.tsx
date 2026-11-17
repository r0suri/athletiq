import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { useApi } from "../api/ApiProvider";
import { ApiError } from "../api/client";
import type { WorkoutType } from "../api/types";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { EffortPicker } from "../components/EffortPicker";
import { errorMessage } from "../components/ErrorState";
import { TextField } from "../components/TextField";
import { useProfile } from "../profile/ProfileProvider";
import { cleanIssue, emptyExercise, LIMITS, newDraft, validateDraft, type FieldErrors, type WorkoutDraft } from "../workouts/draft";
import { localToday, TYPE_LABELS } from "../workouts/format";

const TYPES: WorkoutType[] = ["run", "ride", "strength"];

export function LogWorkoutPage() {
  const api = useApi();
  const navigate = useNavigate();
  const { profile } = useProfile();
  const today = useMemo(() => localToday(profile.timezone), [profile.timezone]);

  const [draft, setDraft] = useState<WorkoutDraft>(() => newDraft(today));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const update = (patch: Partial<WorkoutDraft>) => setDraft((d) => ({ ...d, ...patch }));
  const updateExercise = (index: number, patch: Partial<WorkoutDraft["exercises"][number]>) =>
    setDraft((d) => ({ ...d, exercises: d.exercises.map((ex, i) => (i === index ? { ...ex, ...patch } : ex)) }));

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    const { input, errors: clientErrors } = validateDraft(draft, today);
    setErrors(clientErrors);
    if (!input) return;

    setSaving(true);
    try {
      const saved = await api.createWorkout(input);
      navigate("/workouts", { state: { logged: { type: saved.type, load: saved.load, date: saved.date } } });
    } catch (error) {
      if (error instanceof ApiError && error.status === 422 && error.details.length > 0) {
        const mapped: FieldErrors = {};
        for (const d of error.details) mapped[d.field || "form"] = cleanIssue(d.issue);
        setErrors(mapped);
        if (mapped.form) setFormError(mapped.form);
      } else {
        setFormError(errorMessage(error));
      }
    } finally {
      setSaving(false);
    }
  }

  const hasErrors = Object.keys(errors).length > 0;

  return (
    <section className="max-w-2xl">
      <Link to="/workouts" className="text-sm text-muted hover:text-ink">
        ← Back to workouts
      </Link>
      <h1 className="mt-3 text-3xl font-semibold">Log a workout</h1>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-8" noValidate>
        {formError && <Alert tone="error">{formError}</Alert>}
        {hasErrors && !formError && <Alert tone="error">Fix the highlighted fields, then save again.</Alert>}

        <fieldset>
          <legend className="text-sm font-medium">Type</legend>
          <div className="mt-2 inline-flex rounded-md border border-line p-1">
            {TYPES.map((type) => (
              <label
                key={type}
                className={`cursor-pointer rounded px-4 py-2 text-sm ${draft.type === type ? "bg-raised text-ink" : "text-muted hover:text-ink"}`}
              >
                <input
                  type="radio"
                  name="type"
                  value={type}
                  checked={draft.type === type}
                  onChange={() => update({ type })}
                  className="sr-only"
                />
                {TYPE_LABELS[type]}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            label="Date"
            type="date"
            max={today}
            min={LIMITS.earliestDate}
            value={draft.date}
            onChange={(e) => update({ date: e.target.value })}
            error={errors.date}
          />
          <TextField
            label="Duration (minutes)"
            inputMode="decimal"
            placeholder="45"
            value={draft.duration}
            onChange={(e) => update({ duration: e.target.value })}
            error={errors.duration_min}
          />
          {draft.type !== "strength" && (
            <TextField
              label="Distance (km, optional)"
              inputMode="decimal"
              placeholder={draft.type === "run" ? "8.5" : "40"}
              value={draft.distance}
              onChange={(e) => update({ distance: e.target.value })}
              error={errors.distance_km}
            />
          )}
        </div>

        <EffortPicker value={draft.rpe} onChange={(rpe) => update({ rpe })} error={errors.rpe} />

        {draft.type === "strength" && (
          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium">Exercises (optional)</legend>
            <p className="text-sm text-muted">Sets, reps and weight are used to calculate your total volume lifted.</p>
            {errors.exercises && <p className="text-sm text-hard">{errors.exercises}</p>}
            {draft.exercises.map((ex, i) => (
              <div key={i} className="grid grid-cols-2 gap-3 rounded-md border border-line p-3 sm:grid-cols-[2fr_1fr_1fr_1fr_auto] sm:items-start">
                <TextField
                  className="col-span-2 sm:col-span-1"
                  label="Exercise"
                  placeholder="Back squat"
                  value={ex.name}
                  onChange={(e) => updateExercise(i, { name: e.target.value })}
                  error={errors[`exercises.${i}.name`]}
                />
                <TextField label="Sets" inputMode="numeric" value={ex.sets} onChange={(e) => updateExercise(i, { sets: e.target.value })} error={errors[`exercises.${i}.sets`]} />
                <TextField label="Reps" inputMode="numeric" value={ex.reps} onChange={(e) => updateExercise(i, { reps: e.target.value })} error={errors[`exercises.${i}.reps`]} />
                <TextField label="Weight (kg)" inputMode="decimal" placeholder="0" value={ex.weight} onChange={(e) => updateExercise(i, { weight: e.target.value })} error={errors[`exercises.${i}.weight_kg`]} />
                <Button
                  type="button"
                  variant="quiet"
                  className="col-span-2 sm:col-span-1 sm:mt-6"
                  onClick={() => update({ exercises: draft.exercises.filter((_, j) => j !== i) })}
                  aria-label={`Remove exercise ${i + 1}`}
                >
                  Remove
                </Button>
              </div>
            ))}
            {draft.exercises.length < LIMITS.exercisesMax && (
              <Button type="button" variant="secondary" className="self-start" onClick={() => update({ exercises: [...draft.exercises, emptyExercise()] })}>
                Add exercise
              </Button>
            )}
          </fieldset>
        )}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="notes" className="text-sm font-medium">
            Notes (optional)
          </label>
          <textarea
            id="notes"
            rows={3}
            maxLength={LIMITS.notesMax}
            value={draft.notes}
            onChange={(e) => update({ notes: e.target.value })}
            aria-invalid={errors.notes ? true : undefined}
            className="rounded-md border border-line bg-surface px-3 py-2 text-base text-ink focus:border-action aria-invalid:border-hard"
          />
          <p className="text-sm text-muted">
            {draft.notes.length}/{LIMITS.notesMax}
          </p>
          {errors.notes && <p className="text-sm text-hard">{errors.notes}</p>}
        </div>

        <div className="flex gap-3">
          <Button type="submit" busy={saving}>
            {saving ? "Saving…" : "Save workout"}
          </Button>
          <Link to="/workouts" className="inline-flex min-h-11 items-center px-4 text-muted hover:text-ink">
            Cancel
          </Link>
        </div>
      </form>
    </section>
  );
}
