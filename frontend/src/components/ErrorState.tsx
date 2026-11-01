import { ApiError } from "../api/client";
import { Alert } from "./Alert";
import { Button } from "./Button";

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something went wrong. Try again.";
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <Alert tone="error">
      <p>{errorMessage(error)}</p>
      {requestId && <p className="mt-1 text-xs text-muted">Reference: {requestId}</p>}
      {onRetry && (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      )}
    </Alert>
  );
}
