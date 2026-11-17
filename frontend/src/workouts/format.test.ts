import { describe, expect, it } from "vitest";

import { formatDate, formatDistance, formatDuration, formatLoad, localToday } from "./format";

describe("formatting", () => {
  it("formats durations", () => {
    expect(formatDuration(45)).toBe("45 min");
    expect(formatDuration(90)).toBe("1 h 30 min");
    expect(formatDuration(120)).toBe("2 h");
  });

  it("formats a local date without shifting it", () => {
    expect(formatDate("2026-10-26")).toBe("Mon, Oct 26, 2026");
  });

  it("formats distance and load", () => {
    expect(formatDistance(8.5)).toBe("8.5 km");
    expect(formatLoad(1750)).toBe("1,750");
  });

  it("uses the profile timezone for today", () => {
    const instant = new Date("2026-10-28T03:00:00Z");
    expect(localToday("America/Los_Angeles", instant)).toBe("2026-10-27");
    expect(localToday("Asia/Tokyo", instant)).toBe("2026-10-28");
  });
});
