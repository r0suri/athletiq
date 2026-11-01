import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useAuth } from "../auth/context";
import { createApiClient } from "./client";
import { endpoints, type Api } from "./endpoints";

const ApiContext = createContext<Api | null>(null);

export function ApiProvider({ baseUrl, children }: { baseUrl: string; children: ReactNode }) {
  const { getAccessToken, expireSession } = useAuth();
  const api = useMemo(
    () =>
      endpoints(
        createApiClient({ baseUrl, getToken: getAccessToken, onUnauthorized: expireSession }),
      ),
    [baseUrl, getAccessToken, expireSession],
  );
  return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>;
}

export function useApi(): Api {
  const api = useContext(ApiContext);
  if (!api) throw new Error("useApi must be used inside <ApiProvider>");
  return api;
}

export { ApiContext };
