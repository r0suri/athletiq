import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { routes } from "../App";
import { CONFIGURED } from "../test/profiles";
import { fakeAuth, renderRoutes } from "../test/utils";
import { workout } from "../test/workouts";
import { localToday } from "../workouts/format";

const auth = fakeAuth({ status: "signedIn", email: "rahul@example.com" });

function setup(createWorkout = vi.fn()) {
  const api = {
    getProfile: vi.fn().mockResolvedValue(CONFIGURED),
    createWorkout,
    listWorkouts: vi.fn().mockResolvedValue({ items: [], next_cursor: null }),
  };
  const rendered = renderRoutes(routes, { auth, api, path: "/workouts/new" });
  return { api, ...rendered };
}

describe("LogWorkoutPage", () => {
  it("logs a run with the right body and confirms it on the history page", async () => {
    const user = userEvent.setup();
    const createWorkout = vi.fn().mockResolvedValue(workout({ load: 270, date: localToday(CONFIGURED.timezone) }));
    const { router } = setup(createWorkout);
    await screen.findByRole("heading", { name: "Log a workout" });

    expect(screen.getByLabelText("Date")).toHaveValue(localToday(CONFIGURED.timezone));
    await user.type(screen.getByLabelText("Duration (minutes)"), "45");
    await user.type(screen.getByLabelText("Distance (km, optional)"), "8.5");
    await user.click(screen.getByRole("radio", { name: "6, Somewhat hard" }));
    expect(screen.getByText("6: Somewhat hard")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save workout" }));

    expect(createWorkout).toHaveBeenCalledWith({
      type: "run",
      date: localToday(CONFIGURED.timezone),
      duration_min: 45,
      rpe: 6,
      distance_km: 8.5,
    });
    expect(await screen.findByText(/Session load: 270/)).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/workouts");
  });

  it("logs strength with exercises and no distance field", async () => {
    const user = userEvent.setup();
    const createWorkout = vi.fn().mockResolvedValue(workout({ type: "strength", load: 350, distance_km: null }));
    setup(createWorkout);
    await screen.findByRole("heading", { name: "Log a workout" });

    await user.click(screen.getByRole("radio", { name: "Strength" }));
    expect(screen.queryByLabelText("Distance (km, optional)")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Duration (minutes)"), "50");
    await user.click(screen.getByRole("radio", { name: "7, Hard" }));
    await user.click(screen.getByRole("button", { name: "Add exercise" }));
    await user.type(screen.getByLabelText("Exercise"), "Back squat");
    await user.type(screen.getByLabelText("Sets"), "5");
    await user.type(screen.getByLabelText("Reps"), "5");
    await user.type(screen.getByLabelText("Weight (kg)"), "100");
    await user.click(screen.getByRole("button", { name: "Save workout" }));

    const body = createWorkout.mock.calls[0]![0];
    expect(body).toMatchObject({ type: "strength", duration_min: 50, rpe: 7, exercises: [{ name: "Back squat", sets: 5, reps: 5, weight_kg: 100 }] });
    expect(body).not.toHaveProperty("distance_km");
  });

  it("shows client-side errors and does not call the API", async () => {
    const user = userEvent.setup();
    const createWorkout = vi.fn();
    setup(createWorkout);
    await screen.findByRole("heading", { name: "Log a workout" });

    await user.click(screen.getByRole("button", { name: "Save workout" }));

    expect(screen.getByText(/Enter how long the workout took/)).toBeInTheDocument();
    expect(screen.getByText("Choose how hard the session felt.")).toBeInTheDocument();
    expect(screen.getByLabelText("Duration (minutes)")).toHaveAttribute("aria-invalid", "true");
    expect(createWorkout).not.toHaveBeenCalled();
  });

  it("maps a backend 422 onto the matching field", async () => {
    const user = userEvent.setup();
    const createWorkout = vi
      .fn()
      .mockRejectedValue(
        new ApiError(422, "VALIDATION_ERROR", "Request validation failed.", [{ field: "date", issue: "Value error, date cannot be in the future" }]),
      );
    const { router } = setup(createWorkout);
    await screen.findByRole("heading", { name: "Log a workout" });

    await user.type(screen.getByLabelText("Duration (minutes)"), "30");
    await user.click(screen.getByRole("radio", { name: "5, Moderate" }));
    await user.click(screen.getByRole("button", { name: "Save workout" }));

    expect(await screen.findByText("Date cannot be in the future.")).toBeInTheDocument();
    expect(screen.getByLabelText("Date")).toHaveAttribute("aria-invalid", "true");
    expect(router.state.location.pathname).toBe("/workouts/new");
  });

  it("keeps the form and shows server errors", async () => {
    const user = userEvent.setup();
    setup(vi.fn().mockRejectedValue(new ApiError(0, "NETWORK_ERROR", "Can't reach AthletIQ. Check your connection and try again.")));
    await screen.findByRole("heading", { name: "Log a workout" });

    await user.type(screen.getByLabelText("Duration (minutes)"), "30");
    await user.click(screen.getByRole("radio", { name: "5, Moderate" }));
    await user.click(screen.getByRole("button", { name: "Save workout" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Can't reach AthletIQ");
    expect(screen.getByLabelText("Duration (minutes)")).toHaveValue("30");
  });
});
