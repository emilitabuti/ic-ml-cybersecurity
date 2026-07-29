import { AlertTriangle, LayoutGrid, Target, Timer } from "lucide-react";
import { MetricCard } from "@/components/cards/MetricCard";

interface HeaderMetrics {
  activeAlerts: number;
  analyzedWindows: number;
}

interface HeaderProps {
  metrics?: HeaderMetrics;
}

export function Header({ metrics }: HeaderProps) {
  return (
    <header className="border-b border-border px-6 py-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Alertas Ativos" value={metrics ? String(metrics.activeAlerts) : "—"} icon={AlertTriangle} />
        <MetricCard label="Janelas Analisadas" value={metrics ? String(metrics.analyzedWindows) : "—"} icon={LayoutGrid} />
        <MetricCard label="Precisão do Modelo" value="—" icon={Target} />
        <MetricCard label="Latência" value="—" icon={Timer} />
      </div>
    </header>
  );
}
