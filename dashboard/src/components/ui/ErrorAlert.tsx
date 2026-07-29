import { AlertTriangle } from "lucide-react";

export function ErrorAlert({ message }: { message: string }) {
  return (
    <div
      className="flex items-start gap-2 rounded-lg border border-status-warning/40 bg-card p-4 text-sm text-status-warning"
      role="alert"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
