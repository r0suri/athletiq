import { useId, type InputHTMLAttributes, type ReactNode } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: ReactNode;
}

export function TextField({ label, error, hint, className = "", ...input }: TextFieldProps) {
  const id = useId();
  const describedBy = [error ? `${id}-error` : null, hint ? `${id}-hint` : null]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        {...input}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className="min-h-11 rounded-md border border-line bg-surface px-3 text-base text-ink placeholder:text-muted/70 focus:border-action aria-invalid:border-hard"
      />
      {hint && (
        <div id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </div>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-hard">
          {error}
        </p>
      )}
    </div>
  );
}
