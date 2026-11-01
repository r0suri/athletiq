/** One function per backend endpoint. Paths and shapes follow the OpenAPI contract. */
import type { ApiClient } from "./client";
import type {
  AnalyticsSummary,
  CheckIn,
  CheckInInput,
  Profile,
  ProfileInput,
  Workout,
  WorkoutInput,
  WorkoutList,
  WorkoutType,
} from "./types";

export interface ListWorkoutsParams {
  from?: string;
  to?: string;
  type?: WorkoutType;
  limit?: number;
  cursor?: string | null;
}

export function endpoints(request: ApiClient) {
  return {
    getProfile: () => request<Profile>("GET", "/v1/me/profile"),
    putProfile: (input: ProfileInput) => request<Profile>("PUT", "/v1/me/profile", { body: input }),

    listWorkouts: (params: ListWorkoutsParams = {}) =>
      request<WorkoutList>("GET", "/v1/workouts", { query: { ...params } }),
    createWorkout: (input: WorkoutInput) => request<Workout>("POST", "/v1/workouts", { body: input }),
    deleteWorkout: (id: string) =>
      request<void>("DELETE", `/v1/workouts/${encodeURIComponent(id)}`),

    putCheckIn: (date: string, input: CheckInInput) =>
      request<CheckIn>("PUT", `/v1/checkins/${encodeURIComponent(date)}`, { body: input }),

    getSummary: () => request<AnalyticsSummary>("GET", "/v1/analytics/summary"),
  };
}

export type Api = ReturnType<typeof endpoints>;
