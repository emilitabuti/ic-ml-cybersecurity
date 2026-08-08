import { SeverityBadge } from "@/components/alerts/SeverityBadge";
import type { Severity } from "@/lib/severity";

/**
 * RecentEventsTable — placeholder da tabela de alertas recentes
 */
interface RecentEvent {
  timestamp: string;
  tipoAmeaca: string;
  severity: Severity;
}

const MOCK_EVENTS: RecentEvent[] = [
  { timestamp: "—", tipoAmeaca: "Aguardando integração com a API (Story 5.2)", severity: "info" },
];

export function RecentEventsTable() {
  return (
    <div className="rounded-lg border border-border bg-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="px-4 py-2 font-medium">Timestamp</th>
            <th className="px-4 py-2 font-medium">Tipo de Ameaça</th>
            <th className="px-4 py-2 font-medium">Severidade</th>
          </tr>
        </thead>
        <tbody>
          {MOCK_EVENTS.map((event, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{event.timestamp}</td>
              <td className="px-4 py-2">{event.tipoAmeaca}</td>
              <td className="px-4 py-2">
                <SeverityBadge severity={event.severity} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
