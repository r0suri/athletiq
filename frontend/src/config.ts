/** Runtime configuration from Vite env vars. Fails loudly if anything is missing. */

export interface AppConfig {
  apiUrl: string;
  userPoolId: string;
  userPoolClientId: string;
}

export function readConfig(env: ImportMetaEnv = import.meta.env): AppConfig {
  const entries = {
    VITE_API_URL: env.VITE_API_URL,
    VITE_COGNITO_USER_POOL_ID: env.VITE_COGNITO_USER_POOL_ID,
    VITE_COGNITO_CLIENT_ID: env.VITE_COGNITO_CLIENT_ID,
  };
  const missing = Object.entries(entries)
    .filter(([, value]) => !value)
    .map(([key]) => key);
  if (missing.length > 0) {
    throw new Error(
      `Missing configuration: ${missing.join(", ")}. Run ./scripts/write-env.sh to create .env.local.`,
    );
  }
  return {
    apiUrl: entries.VITE_API_URL!.replace(/\/+$/, ""),
    userPoolId: entries.VITE_COGNITO_USER_POOL_ID!,
    userPoolClientId: entries.VITE_COGNITO_CLIENT_ID!,
  };
}
