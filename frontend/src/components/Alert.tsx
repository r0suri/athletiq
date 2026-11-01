import type { ReactNode } from "react";

type Tone = "error" | "info" | "success";

const TONES: Record<Tone, string> = {
  error: "border-hard/60 text-ink",
  info: "border-action/60 text-ink",
  success: "border-easy/60 text-ink",
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`rounded-md border-l-4 bg-surface px-4 py-3 text-sm ${TONES[tone]}`}
    >
      {children}
    </div>
  );
}
