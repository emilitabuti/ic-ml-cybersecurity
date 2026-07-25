import { AlertTriangle, LayoutGrid, Target, Timer } from "lucide-react";
import { MetricCard } from "@/components/cards/MetricCard";

/**
 * Header com os 4 cards de métrica exigidos pela Story 5.1.
 * Valores são placeholders — integração real (Story 5.2) virá via
 * `GET /health` e `GET /model/info`.
 */
export function Header() {
  return (
    <header className="border-b border-border px-6 py-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Alertas Ativos" value="—" icon={AlertTriangle} />
        <MetricCard label="Janelas Analisadas" value="—" icon={LayoutGrid} />
        <MetricCard label="Precisão do Modelo" value="—" icon={Target} />
        <MetricCard label="Latência" value="—" icon={Timer} />
      </div>
    </header>
  );
}
