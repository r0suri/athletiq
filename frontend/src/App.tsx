import { createBrowserRouter, RouterProvider } from "react-router";

import { ApiProvider } from "./api/ApiProvider";
import { AuthProvider } from "./auth/AuthProvider";
import { PublicOnly, RequireAuth } from "./auth/routes";
import { AppShell } from "./components/AppShell";
import type { AppConfig } from "./config";
import { OnboardingOnly, ProfileProvider, RequireProfile } from "./profile/ProfileProvider";
import { ConfirmPage } from "./pages/ConfirmPage";
import { LogWorkoutPage } from "./pages/LogWorkoutPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { WorkoutsPage } from "./pages/WorkoutsPage";
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
    children: [
      {
        element: <ProfileProvider />,
        children: [
          { element: <OnboardingOnly />, children: [{ path: "/onboarding", element: <OnboardingPage /> }] },
          {
            element: <RequireProfile />,
            children: [
              {
                element: <AppShell />,
                children: [
                  { path: "/", element: <OverviewPage /> },
                  { path: "/workouts", element: <WorkoutsPage /> },
                  { path: "/workouts/new", element: <LogWorkoutPage /> },
                  { path: "/settings", element: <SettingsPage /> },
                ],
              },
            ],
          },
        ],
      },
    ],
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
