import { SEVERITY_CONFIG, type Severity } from "@/lib/severity";
import { RecentEventsTable } from "@/components/alerts/RecentEventsTable";

const SEVERITIES: Severity[] = ["critical", "warning", "info", "safe"];

/**
 * Seção "Monitor" — visão principal do Command Center.
 * A legenda de severidade e a tabela de eventos recentes reaproveitam o
 * conceito de "cards de resumo + tabela de eventos" do protótipo da Isabela
 * (branch `Isa252-patch-1`); a integração com dados reais é da Story 5.2.
 */
export function MonitorSection() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span>Legenda de severidade:</span>
        {SEVERITIES.map((severity) => {
          const { label, colorVar, icon: Icon } = SEVERITY_CONFIG[severity];
          return (
            <span key={severity} className="inline-flex items-center gap-1" style={{ color: colorVar }}>
              <Icon className="size-3.5" aria-hidden="true" />
              {label}
            </span>
          );
        })}
      </div>
      <RecentEventsTable />
    </div>
  );
}
