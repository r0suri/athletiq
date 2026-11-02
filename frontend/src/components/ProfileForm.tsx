/** Goal + timezone form shared by onboarding and settings. Saves via PUT /v1/me/profile. */
import { useId, useMemo, useState, type FormEvent } from "react";

import { useApi } from "../api/ApiProvider";
import { ApiError } from "../api/client";
import type { Goal, Profile } from "../api/types";
import { GOALS } from "../profile/goals";
import { useProfile } from "../profile/ProfileProvider";
import { detectTimezone, timezoneSuggestions } from "../profile/timezone";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { errorMessage } from "./ErrorState";
import { TextField } from "./TextField";

export interface ProfileValues {
  goal: Goal;
  timezone: string;
}

interface ProfileFormProps {
  initial: ProfileValues;
  submitLabel: string;
  savingLabel: string;
  /** Disable the button until something changes (settings), or not (onboarding). */
  requireChange?: boolean;
  onSaved: (profile: Profile) => void;
}

type FieldErrors = Partial<Record<keyof ProfileValues, string>>;

/** "Value error, must be an IANA timezone…" -> "Must be an IANA timezone…" */
function cleanIssue(issue: string): string {
  const text = issue.replace(/^Value error,\s*/i, "");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function ProfileForm({ initial, submitLabel, savingLabel, requireChange = false, onSaved }: ProfileFormProps) {
  const api = useApi();
  const { setProfile } = useProfile();
  const listId = useId();
  const suggestions = useMemo(timezoneSuggestions, []);
  const detected = useMemo(detectTimezone, []);

  const [goal, setGoal] = useState<Goal>(initial.goal);
  const [timezone, setTimezone] = useState(initial.timezone);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const changed = goal !== initial.goal || timezone.trim() !== initial.timezone;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    const tz = timezone.trim();
    if (!tz) {
      setFieldErrors({ timezone: "Enter a timezone, for example America/New_York." });
      return;
    }
    setFieldErrors({});
    setSaving(true);
    try {
      const saved = await api.putProfile({ goal, timezone: tz });
      setProfile(saved);
      onSaved(saved);
    } catch (error) {
      if (error instanceof ApiError && error.status === 422 && error.details.length > 0) {
        const next: FieldErrors = {};
        for (const d of error.details) {
          if (d.field === "goal" || d.field === "timezone") next[d.field] = cleanIssue(d.issue);
        }
        if (Object.keys(next).length > 0) setFieldErrors(next);
        else setFormError(errorMessage(error));
      } else {
        setFormError(errorMessage(error));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-8" noValidate>
      {formError && <Alert tone="error">{formError}</Alert>}

      <fieldset className="flex flex-col gap-2" aria-describedby={fieldErrors.goal ? `${listId}-goal-error` : undefined}>
        <legend className="mb-2 text-sm font-medium">Training goal</legend>
        {GOALS.map((option) => {
          const selected = goal === option.value;
          return (
            <label
              key={option.value}
              className={`flex cursor-pointer items-start gap-3 rounded-md border px-4 py-3 transition-colors motion-reduce:transition-none ${
                selected ? "border-action bg-raised" : "border-line hover:border-muted"
              }`}
            >
              <input
                type="radio"
                name="goal"
                value={option.value}
                checked={selected}
                onChange={() => setGoal(option.value)}
                className="mt-1 accent-action"
              />
              <span>
                <span className="block font-medium">{option.label}</span>
                <span className="block text-sm text-muted">{option.description}</span>
              </span>
            </label>
          );
        })}
        {fieldErrors.goal && (
          <p id={`${listId}-goal-error`} className="text-sm text-hard">
            {fieldErrors.goal}
          </p>
        )}
      </fieldset>

      <div>
        <TextField
          label="Timezone"
          list={listId}
          autoComplete="off"
          spellCheck={false}
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          error={fieldErrors.timezone}
          hint={
            <>
              Used to decide which day your workouts count toward.
              {detected && timezone.trim() !== detected && (
                <>
                  {" "}
                  <button type="button" className="text-action underline-offset-4 hover:underline" onClick={() => setTimezone(detected)}>
                    Use {detected}
                  </button>
                </>
              )}
              {detected && timezone.trim() === detected && " Detected from this browser."}
            </>
          }
        />
        <datalist id={listId}>
          {suggestions.map((zone) => (
            <option key={zone} value={zone} />
          ))}
        </datalist>
      </div>

      <Button type="submit" busy={saving} disabled={requireChange && !changed} className="self-start">
        {saving ? savingLabel : submitLabel}
      </Button>
    </form>
  );
}
