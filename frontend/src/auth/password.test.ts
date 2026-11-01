import { describe, expect, it } from "vitest";

import { passwordMeetsPolicy } from "./password";

describe("passwordMeetsPolicy (mirrors the Cognito policy in template.yaml)", () => {
  it.each([
    ["Athletiq2026", true],
    ["athletiq2026", false], // no uppercase
    ["ATHLETIQ2026", false], // no lowercase
    ["AthletiqTest", false], // no number
    ["Short1A", false], // under 10 characters
  ])("%s -> %s", (password, expected) => {
    expect(passwordMeetsPolicy(password)).toBe(expected);
  });
});
