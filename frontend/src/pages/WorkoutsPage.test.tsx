import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { routes } from "../App";
import { CONFIGURED } from "../test/profiles";
import { fakeAuth, renderRoutes } from "../test/utils";
import { workout } from "../test/workouts";

const auth = fakeAuth({ status: "signedIn", email: "rahul@example.com" });
const RUN = workout();
const RIDE = workout({ id: "2026-10-24_01M5Z7J1PNS8GB3BRGY4ERP2XA", type: "ride", date: "2026-10-24", duration_min: 90, rpe: 3, load: 270, distance_km: 40 });

function setup(api: Record<string, unknown>) {
  return renderRoutes(routes, { auth, api: { getProfile: vi.fn().mockResolvedValue(CONFIGURED), ...api }, path: "/workouts" });
}

describe("WorkoutsPage", () => {
  it("lists workouts newest first with load and effort", async () => {
    const listWorkouts = vi.fn().mockResolvedValue({ items: [RUN, RIDE], next_cursor: null });
    setup({ listWorkouts });

    const list = await screen.findByRole("list", { name: "Workout history" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Mon, Oct 26, 2026");
    expect(rows[0]).toHaveTextContent("50 min, 10 km");
    expect(rows[0]).toHaveTextContent("RPE 8");
    expect(rows[0]).toHaveTextContent("400");
    expect(listWorkouts).toHaveBeenCalledWith({ from: "2000-01-01", type: undefined, limit: 20 });
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("shows an empty state that points to logging", async () => {
    setup({ listWorkouts: vi.fn().mockResolvedValue({ items: [], next_cursor: null }) });
    expect(await screen.findByText("No workouts yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Log your first workout" })).toHaveAttribute("href", "/workouts/new");
  });

  it("filters by type through the API", async () => {
    const user = userEvent.setup();
    const listWorkouts = vi
      .fn()
      .mockResolvedValueOnce({ items: [RUN, RIDE], next_cursor: null })
      .mockResolvedValueOnce({ items: [RIDE], next_cursor: null });
    setup({ listWorkouts });
    await screen.findByRole("list", { name: "Workout history" });

    await user.click(screen.getByRole("button", { name: "Rides" }));

    expect(listWorkouts).toHaveBeenLastCalledWith({ from: "2000-01-01", type: "ride", limit: 20 });
    expect(await screen.findAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Rides" })).toHaveAttribute("aria-pressed", "true");
  });

  it("loads more with the cursor and appends", async () => {
    const user = userEvent.setup();
    const listWorkouts = vi
      .fn()
      .mockResolvedValueOnce({ items: [RUN], next_cursor: "abc" })
      .mockResolvedValueOnce({ items: [RIDE], next_cursor: null });
    setup({ listWorkouts });
    await screen.findByRole("list", { name: "Workout history" });

    await user.click(screen.getByRole("button", { name: "Load more" }));

    expect(listWorkouts).toHaveBeenLastCalledWith({ from: "2000-01-01", type: undefined, limit: 20, cursor: "abc" });
    expect(await screen.findByText("Sat, Oct 24, 2026")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("deletes after confirmation and removes the row", async () => {
    const user = userEvent.setup();
    const deleteWorkout = vi.fn().mockResolvedValue(undefined);
    setup({ listWorkouts: vi.fn().mockResolvedValue({ items: [RUN, RIDE], next_cursor: null }), deleteWorkout });
    await screen.findByRole("list", { name: "Workout history" });

    await user.click(screen.getByRole("button", { name: "Delete run on Mon, Oct 26, 2026" }));
    expect(deleteWorkout).not.toHaveBeenCalled(); // asks first
    await user.click(screen.getByRole("button", { name: "Delete run" }));

    expect(deleteWorkout).toHaveBeenCalledWith(RUN.id);
    expect(await screen.findAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByText("Mon, Oct 26, 2026")).not.toBeInTheDocument();
  });

  it("keeps the row and explains when a delete fails", async () => {
    const user = userEvent.setup();
    const deleteWorkout = vi.fn().mockRejectedValue(new ApiError(404, "NOT_FOUND", "Workout not found."));
    setup({ listWorkouts: vi.fn().mockResolvedValue({ items: [RUN], next_cursor: null }), deleteWorkout });
    await screen.findByRole("list", { name: "Workout history" });

    await user.click(screen.getByRole("button", { name: /^Delete run on/ }));
    await user.click(screen.getByRole("button", { name: "Delete run" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Workout not found.");
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("offers a retry when the list fails to load", async () => {
    const user = userEvent.setup();
    const listWorkouts = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(500, "INTERNAL_ERROR", "An unexpected error occurred.", [], "req-7"))
      .mockResolvedValueOnce({ items: [RUN], next_cursor: null });
    setup({ listWorkouts });

    expect(await screen.findByText("Reference: req-7")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("list", { name: "Workout history" })).toBeInTheDocument();
  });
});
