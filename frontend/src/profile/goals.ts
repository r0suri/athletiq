import type { Goal } from "../api/types";

/** Copy for each goal. Session targets match GOAL_TARGET_SESSIONS in the backend. */
export const GOALS: { value: Goal; label: string; description: string }[] = [
  { value: "strength", label: "Strength", description: "Get stronger in the gym. Target: 3 strength sessions a week." },
  { value: "endurance", label: "Endurance", description: "Run and ride further. Target: 4 runs or rides a week." },
  {
    value: "general_fitness",
    label: "General fitness",
    description: "Stay active with a mix of training. Target: 3 sessions a week.",
  },
];

export function goalLabel(goal: Goal): string {
  return GOALS.find((g) => g.value === goal)?.label ?? goal;
}
