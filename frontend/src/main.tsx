import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { configureAmplify } from "./auth/AuthProvider";
import { readConfig } from "./config";
import "./index.css";

const root = createRoot(document.getElementById("root")!);

try {
  const config = readConfig();
  configureAmplify(config);
  root.render(
    <StrictMode>
      <App config={config} />
    </StrictMode>,
  );
} catch (error) {
  // A missing .env.local is a developer setup problem: say exactly how to fix it.
  root.render(
    <main className="mx-auto max-w-xl px-5 py-24">
      <h1 className="text-2xl font-semibold">AthletIQ isn't configured</h1>
      <p className="mt-3 text-muted">{error instanceof Error ? error.message : String(error)}</p>
    </main>,
  );
}
