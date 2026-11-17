import type { WorkoutType } from "../api/types";

export const TYPE_LABELS: Record<WorkoutType, string> = { run: "Run", ride: "Ride", strength: "Strength" };

/** "2026-10-26" -> "Mon, Oct 26, 2026" (no timezone shift: the date is already local). */
export function formatDate(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(y!, m! - 1, d!)));
}

/** 45 -> "45 min", 90 -> "1 h 30 min", 120 -> "2 h". */
export function formatDuration(minutes: number): string {
  const total = Math.round(minutes);
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h === 0) return `${m} min`;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export function formatDistance(km: number): string {
  return `${km.toLocaleString("en-US", { maximumFractionDigits: 2 })} km`;
}

export function formatLoad(load: number): string {
  return Math.round(load).toLocaleString("en-US");
}

/** Today's date (YYYY-MM-DD) in an IANA timezone; falls back to the browser's zone. */
export function localToday(timezone: string, now: Date = new Date()): string {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(now);
  } catch {
    return new Intl.DateTimeFormat("en-CA").format(now);
  }
}
