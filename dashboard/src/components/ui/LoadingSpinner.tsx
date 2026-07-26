import { LoaderCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", className)} role="status">
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
      <span>Carregando alertas...</span>
    </div>
  );
}
