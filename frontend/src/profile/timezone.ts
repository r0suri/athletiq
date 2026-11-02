/** The browser's IANA timezone, e.g. "America/New_York" (null if unavailable). */
export function detectTimezone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

/**
 * Suggestions for the timezone field. The browser's list omits "UTC" and can use
 * older names, so the backend (which accepts both forms) stays the validator.
 */
export function timezoneSuggestions(): string[] {
  let zones: string[] = [];
  try {
    zones = Intl.supportedValuesOf("timeZone");
  } catch {
    // Older browsers: the field still accepts free text.
  }
  return zones.includes("UTC") ? zones : ["UTC", ...zones];
}
