/** Friendly aliases over the generated OpenAPI types (src/api/schema.ts). */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Health = Schemas["HealthResponse"];
export type Profile = Schemas["ProfileOut"];
export type ProfileInput = Schemas["ProfilePut"];
export type Goal = Schemas["Goal"];
export type Workout = Schemas["WorkoutOut"];
export type WorkoutList = Schemas["WorkoutList"];
export type WorkoutInput = Schemas["RunCreate"] | Schemas["RideCreate"] | Schemas["StrengthCreate"];
export type WorkoutType = Workout["type"];
export type CheckIn = Schemas["CheckInOut"];
export type CheckInInput = Schemas["CheckInPut"];
export type AnalyticsSummary = Schemas["AnalyticsSummaryOut"];
