import { describe, expect, it } from "vitest";

import { readConfig } from "./config";

describe("readConfig", () => {
  it("reads values and trims a trailing slash from the API URL", () => {
    const config = readConfig({
      VITE_API_URL: "https://api.example.com/",
      VITE_COGNITO_USER_POOL_ID: "us-east-1_abc",
      VITE_COGNITO_CLIENT_ID: "client123",
    } as ImportMetaEnv);
    expect(config).toEqual({
      apiUrl: "https://api.example.com",
      userPoolId: "us-east-1_abc",
      userPoolClientId: "client123",
    });
  });

  it("names every missing variable", () => {
    expect(() => readConfig({ VITE_API_URL: "https://x" } as ImportMetaEnv)).toThrow(
      /VITE_COGNITO_USER_POOL_ID, VITE_COGNITO_CLIENT_ID/,
    );
  });
});
