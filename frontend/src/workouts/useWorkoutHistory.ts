/** Paged workout history (newest first) with load-more and local removal after delete. */
import { useCallback, useEffect, useState } from "react";

import type { Api } from "../api/endpoints";
import type { Workout, WorkoutType } from "../api/types";

export const PAGE_SIZE = 20;
const ALL_HISTORY_FROM = "2000-01-01"; // still one key-range query per page

type Status = "loading" | "ready" | "error" | "loadingMore";

export function useWorkoutHistory(api: Api, type: WorkoutType | null) {
  const [items, setItems] = useState<Workout[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    setItems([]);
    setCursor(null);
    api.listWorkouts({ from: ALL_HISTORY_FROM, type: type ?? undefined, limit: PAGE_SIZE }).then(
      (page) => {
        if (cancelled) return;
        setItems(page.items);
        setCursor(page.next_cursor ?? null);
        setStatus("ready");
      },
      (err: unknown) => {
        if (cancelled) return;
        setError(err);
        setStatus("error");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [api, type, attempt]);

  const loadMore = useCallback(async () => {
    if (!cursor) return;
    setStatus("loadingMore");
    setError(null);
    try {
      const page = await api.listWorkouts({ from: ALL_HISTORY_FROM, type: type ?? undefined, limit: PAGE_SIZE, cursor });
      setItems((current) => [...current, ...page.items]);
      setCursor(page.next_cursor ?? null);
      setStatus("ready");
    } catch (err) {
      setError(err);
      setStatus("ready"); // keep the loaded items visible; show the error beside "Load more"
    }
  }, [api, type, cursor]);

  const remove = useCallback((id: string) => setItems((current) => current.filter((w) => w.id !== id)), []);
  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  return { items, hasMore: cursor !== null, status, error, loadMore, remove, reload };
}
