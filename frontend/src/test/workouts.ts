import type { Workout } from "../api/types";

export function workout(overrides: Partial<Workout> = {}): Workout {
  return {
    id: "2026-10-26_01M5Z7J1PNS8GB3BRGY4ERP2XT",
    type: "run",
    date: "2026-10-26",
    duration_min: 50,
    rpe: 8,
    load: 400,
    distance_km: 10,
    exercises: [],
    notes: null,
    source: "manual",
    created_at: "2026-10-27T17:47:03Z",
    ...overrides,
  };
}
