import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  className?: string;
}

/** Card de métrica do header — alertas ativos, janelas analisadas, precisão, latência. */
export function MetricCard({ label, value, icon: Icon, className }: MetricCardProps) {
  return (
    <div className={cn("flex items-center gap-3 rounded-lg border border-border bg-card p-4", className)}>
      <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-mono text-lg font-semibold text-card-foreground">{value}</p>
      </div>
    </div>
  );
}
