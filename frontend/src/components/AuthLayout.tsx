import type { ReactNode } from "react";

import { Wordmark } from "./Wordmark";

export function AuthLayout({ title, intro, children }: { title: string; intro: ReactNode; children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-sm flex-col justify-center px-5 py-12">
      <Wordmark className="mb-10" />
      <h1 className="text-3xl font-semibold">{title}</h1>
      <p className="mt-2 mb-8 text-muted">{intro}</p>
      {children}
    </main>
  );
}
