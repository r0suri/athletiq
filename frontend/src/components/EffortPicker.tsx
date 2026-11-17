/** Session RPE picker (1–10) colored by the effort ramp. Native radios for keyboard and screen readers. */
import { BAND_STYLES, effortBand, RPE_LABELS } from "../workouts/effort";

interface EffortPickerProps {
  value: number | null;
  onChange: (rpe: number) => void;
  error?: string;
}

export function EffortPicker({ value, onChange, error }: EffortPickerProps) {
  return (
    <fieldset aria-describedby={error ? "rpe-error" : "rpe-hint"}>
      <legend className="text-sm font-medium">How hard did it feel?</legend>
      <p id="rpe-hint" className="mt-1 text-sm text-muted">
        Rate the whole session from 1 (very easy) to 10 (maximal effort).
      </p>
      <div className="mt-3 grid grid-cols-5 gap-2 sm:grid-cols-10">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((rpe) => {
          const selected = value === rpe;
          const band = BAND_STYLES[effortBand(rpe)];
          return (
            <label
              key={rpe}
              className={`flex h-11 cursor-pointer items-center justify-center rounded-md border font-display text-lg font-semibold tabular ${
                selected ? `${band.solid} border-transparent` : `border-line ${band.text} hover:bg-raised`
              }`}
            >
              <input
                type="radio"
                name="rpe"
                value={rpe}
                checked={selected}
                onChange={() => onChange(rpe)}
                className="sr-only"
                aria-label={`${rpe}, ${RPE_LABELS[rpe]}`}
              />
              {rpe}
            </label>
          );
        })}
      </div>
      <p className="mt-2 min-h-6 text-sm" aria-live="polite">
        {value !== null && (
          <span className={BAND_STYLES[effortBand(value)].text}>
            {value}: {RPE_LABELS[value]}
          </span>
        )}
      </p>
      {error && (
        <p id="rpe-error" className="text-sm text-hard">
          {error}
        </p>
      )}
    </fieldset>
  );
}
