import { cn } from "@/lib/utils";
import { SEVERITY_CONFIG, type Severity } from "@/lib/severity";

/**
 * Badge de severidade — cor + icone + label textual
 */
export function SeverityBadge({ severity }: { severity: Severity }) {
  const { label, colorVar, icon: Icon } = SEVERITY_CONFIG[severity];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium",
      )}
      style={{ color: colorVar, backgroundColor: `color-mix(in oklch, ${colorVar} 15%, transparent)` }}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}
