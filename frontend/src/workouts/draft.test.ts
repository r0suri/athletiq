import { describe, expect, it } from "vitest";

import { emptyExercise, newDraft, validateDraft, type WorkoutDraft } from "./draft";

const TODAY = "2026-11-01";
const draft = (patch: Partial<WorkoutDraft>): WorkoutDraft => ({ ...newDraft(TODAY), ...patch });

describe("validateDraft", () => {
  it("builds a run body with only run fields", () => {
    const { input, errors } = validateDraft(draft({ duration: "45", rpe: 6, distance: "8.5", notes: "  tempo  " }), TODAY);
    expect(errors).toEqual({});
    expect(input).toEqual({ type: "run", date: TODAY, duration_min: 45, rpe: 6, distance_km: 8.5, notes: "tempo" });
  });

  it("omits optional fields that were left empty", () => {
    const { input } = validateDraft(draft({ type: "ride", duration: "60", rpe: 5 }), TODAY);
    expect(input).toEqual({ type: "ride", date: TODAY, duration_min: 60, rpe: 5 });
  });

  it("builds a strength body with exercises and never a distance", () => {
    const { input } = validateDraft(
      draft({
        type: "strength",
        duration: "50",
        rpe: 7,
        distance: "12", // left over from a previous type: must not be sent
        exercises: [{ name: " Back squat ", sets: "5", reps: "5", weight: "100" }, { name: "Push-up", sets: "3", reps: "15", weight: "" }],
      }),
      TODAY,
    );
    expect(input).toEqual({
      type: "strength",
      date: TODAY,
      duration_min: 50,
      rpe: 7,
      exercises: [
        { name: "Back squat", sets: 5, reps: 5, weight_kg: 100 },
        { name: "Push-up", sets: 3, reps: 15, weight_kg: 0 },
      ],
    });
    expect(input).not.toHaveProperty("distance_km");
  });

  it.each([
    [{ duration: "" }, "duration_min", /Enter how long/],
    [{ duration: "0" }, "duration_min", /more than 0/],
    [{ duration: "abc" }, "duration_min", /more than 0/],
    [{ duration: "1441" }, "duration_min", /at most 1,440/],
    [{ rpe: null }, "rpe", /how hard/],
    [{ date: "2026-11-02" }, "date", /future/],
    [{ date: "1999-12-31" }, "date", /2000 or later/],
    [{ distance: "501" }, "distance_km", /between 0 and 500/],
    [{ distance: "-1" }, "distance_km", /between 0 and 500/],
  ])("rejects %o on %s", (patch, field, message) => {
    const { input, errors } = validateDraft(draft({ duration: "30", rpe: 5, ...patch }), TODAY);
    expect(input).toBeUndefined();
    expect(errors[field]).toMatch(message);
  });

  it("allows longer rides than runs", () => {
    expect(validateDraft(draft({ type: "ride", duration: "300", rpe: 5, distance: "800" }), TODAY).errors).toEqual({});
  });

  it("reports exercise errors with the backend's field paths", () => {
    const { errors } = validateDraft(
      draft({ type: "strength", duration: "40", rpe: 6, exercises: [emptyExercise(), { name: "Row", sets: "2.5", reps: "0", weight: "2000" }] }),
      TODAY,
    );
    expect(errors["exercises.0.name"]).toMatch(/exercise name/);
    expect(errors["exercises.1.sets"]).toMatch(/whole number/);
    expect(errors["exercises.1.reps"]).toMatch(/between 1 and 1000/);
    expect(errors["exercises.1.weight_kg"]).toMatch(/between 0 and 1000/);
  });
});
