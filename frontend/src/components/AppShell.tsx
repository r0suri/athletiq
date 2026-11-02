import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/context";
import { Button } from "./Button";
import { Wordmark } from "./Wordmark";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/settings", label: "Settings" },
];

export function AppShell() {
  const { email, signOut } = useAuth();
  return (
    <div className="min-h-dvh">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-8 gap-y-2 px-5 py-3">
          <Wordmark />
          <nav aria-label="Main" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm whitespace-nowrap ${isActive ? "bg-raised text-ink" : "text-muted hover:text-ink"}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden max-w-48 truncate text-sm text-muted sm:inline" title={email ?? ""}>
              {email}
            </span>
            <Button variant="secondary" onClick={() => void signOut()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-8">
        <Outlet />
      </main>
    </div>
  );
}
