import { createBrowserRouter, RouterProvider } from "react-router";

import { ApiProvider } from "./api/ApiProvider";
import { AuthProvider } from "./auth/AuthProvider";
import { PublicOnly, RequireAuth } from "./auth/routes";
import { AppShell } from "./components/AppShell";
import type { AppConfig } from "./config";
import { ConfirmPage } from "./pages/ConfirmPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SignInPage } from "./pages/SignInPage";
import { SignUpPage } from "./pages/SignUpPage";

export const routes = [
  {
    element: <PublicOnly />,
    children: [
      { path: "/signin", element: <SignInPage /> },
      { path: "/signup", element: <SignUpPage /> },
      { path: "/confirm", element: <ConfirmPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [{ element: <AppShell />, children: [{ path: "/", element: <OverviewPage /> }] }],
  },
  { path: "*", element: <NotFoundPage /> },
];

const router = createBrowserRouter(routes);

export function App({ config }: { config: AppConfig }) {
  return (
    <AuthProvider>
      <ApiProvider baseUrl={config.apiUrl}>
        <RouterProvider router={router} />
      </ApiProvider>
    </AuthProvider>
  );
}
