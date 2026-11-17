/** Session RPE (1–10) mapped onto the app's effort ramp. */
export type EffortBand = "easy" | "moderate" | "hard";

export const RPE_LABELS: Record<number, string> = {
  1: "Very easy",
  2: "Easy",
  3: "Easy",
  4: "Moderate",
  5: "Moderate",
  6: "Somewhat hard",
  7: "Hard",
  8: "Very hard",
  9: "Very hard",
  10: "Maximal",
};

export function effortBand(rpe: number): EffortBand {
  if (rpe <= 3) return "easy";
  if (rpe <= 6) return "moderate";
  return "hard";
}

/** Literal class names so Tailwind can find them. */
export const BAND_STYLES: Record<EffortBand, { solid: string; text: string; ring: string }> = {
  easy: { solid: "bg-easy text-bg", text: "text-easy", ring: "border-easy" },
  moderate: { solid: "bg-moderate text-bg", text: "text-moderate", ring: "border-moderate" },
  hard: { solid: "bg-hard text-bg", text: "text-hard", ring: "border-hard" },
};
