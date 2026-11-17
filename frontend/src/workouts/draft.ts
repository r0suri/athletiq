/**
 * Form state for logging a workout, client-side validation that mirrors the API
 * contract (backend stays the authority), and conversion to the exact request body.
 * Error keys use the backend's field paths so 422 details map onto the same fields.
 */
import type { WorkoutInput, WorkoutType } from "../api/types";

export interface ExerciseDraft {
  name: string;
  sets: string;
  reps: string;
  weight: string;
}

export interface WorkoutDraft {
  type: WorkoutType;
  date: string;
  duration: string;
  rpe: number | null;
  distance: string;
  notes: string;
  exercises: ExerciseDraft[];
}

export type FieldErrors = Record<string, string>;

export const LIMITS = {
  durationMax: 1440,
  distanceMax: { run: 500, ride: 1000 } as Record<string, number>,
  notesMax: 500,
  exercisesMax: 50,
  nameMax: 80,
  setsMax: 100,
  repsMax: 1000,
  weightMax: 1000,
  earliestDate: "2000-01-01",
};

export function emptyExercise(): ExerciseDraft {
  return { name: "", sets: "", reps: "", weight: "" };
}

export function newDraft(today: string): WorkoutDraft {
  return { type: "run", date: today, duration: "", rpe: null, distance: "", notes: "", exercises: [] };
}

function parseNumber(raw: string): number | null {
  const text = raw.trim();
  if (text === "") return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : Number.NaN;
}

function checkInteger(raw: string, min: number, max: number, label: string): [number | null, string | null] {
  const value = parseNumber(raw);
  if (value === null) return [null, `Enter ${label}.`];
  if (Number.isNaN(value) || !Number.isInteger(value)) return [null, `${capitalize(label)} must be a whole number.`];
  if (value < min || value > max) return [null, `${capitalize(label)} must be between ${min} and ${max}.`];
  return [value, null];
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function validateDraft(draft: WorkoutDraft, today: string): { input?: WorkoutInput; errors: FieldErrors } {
  const errors: FieldErrors = {};

  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.date)) errors.date = "Choose a date.";
  else if (draft.date > today) errors.date = "The date can't be in the future.";
  else if (draft.date < LIMITS.earliestDate) errors.date = "The date must be in 2000 or later.";

  const duration = parseNumber(draft.duration);
  if (duration === null) errors.duration_min = "Enter how long the workout took, in minutes.";
  else if (Number.isNaN(duration) || duration <= 0) errors.duration_min = "Duration must be more than 0 minutes.";
  else if (duration > LIMITS.durationMax) errors.duration_min = "Duration can be at most 1,440 minutes (24 hours).";

  if (draft.rpe === null) errors.rpe = "Choose how hard the session felt.";

  let distance: number | null = null;
  if (draft.type !== "strength") {
    distance = parseNumber(draft.distance);
    const max = LIMITS.distanceMax[draft.type]!;
    if (distance !== null && (Number.isNaN(distance) || distance < 0 || distance > max)) {
      errors.distance_km = `Distance must be between 0 and ${max} km.`;
    }
  }

  const notes = draft.notes.trim();
  if (notes.length > LIMITS.notesMax) errors.notes = `Notes can be at most ${LIMITS.notesMax} characters.`;

  const exercises: { name: string; sets: number; reps: number; weight_kg: number }[] = [];
  if (draft.type === "strength") {
    if (draft.exercises.length > LIMITS.exercisesMax) errors.exercises = `Add at most ${LIMITS.exercisesMax} exercises.`;
    draft.exercises.forEach((ex, i) => {
      const name = ex.name.trim();
      if (!name) errors[`exercises.${i}.name`] = "Enter the exercise name.";
      else if (name.length > LIMITS.nameMax) errors[`exercises.${i}.name`] = `Use at most ${LIMITS.nameMax} characters.`;
      const [sets, setsError] = checkInteger(ex.sets, 1, LIMITS.setsMax, "sets");
      if (setsError) errors[`exercises.${i}.sets`] = setsError;
      const [reps, repsError] = checkInteger(ex.reps, 1, LIMITS.repsMax, "reps");
      if (repsError) errors[`exercises.${i}.reps`] = repsError;
      const weight = parseNumber(ex.weight) ?? 0;
      if (Number.isNaN(weight) || weight < 0 || weight > LIMITS.weightMax) {
        errors[`exercises.${i}.weight_kg`] = `Weight must be between 0 and ${LIMITS.weightMax} kg.`;
      }
      if (name && sets !== null && reps !== null) exercises.push({ name, sets, reps, weight_kg: weight });
    });
  }

  if (Object.keys(errors).length > 0) return { errors };

  const base = { date: draft.date, duration_min: duration!, rpe: draft.rpe!, ...(notes ? { notes } : {}) };
  // Each type sends only its own fields: the API rejects unknown fields.
  const input: WorkoutInput =
    draft.type === "strength"
      ? { ...base, type: "strength", exercises }
      : { ...base, type: draft.type, ...(distance !== null ? { distance_km: distance } : {}) };
  return { input, errors };
}

/** "Value error, ..." / "Input should be ..." -> a sentence for the field. */
export function cleanIssue(issue: string): string {
  const text = issue.replace(/^Value error,\s*/i, "");
  return text.charAt(0).toUpperCase() + text.slice(1) + (/[.!?]$/.test(text) ? "" : ".");
}
