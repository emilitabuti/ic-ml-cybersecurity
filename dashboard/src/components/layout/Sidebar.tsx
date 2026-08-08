import { Activity, Bell, History, BarChart3, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type Section = "monitor" | "alertas" | "historico" | "modelos";

const NAV_ITEMS: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: "monitor", label: "Monitor", icon: Activity },
  { id: "alertas", label: "Alertas", icon: Bell },
  { id: "historico", label: "Histórico", icon: History },
  { id: "modelos", label: "Modelos", icon: BarChart3 },
];

interface SidebarProps {
  active: Section;
  onSelect: (section: Section) => void;
}

/** Sidebar fixa (220px) com as 4 seções do Command Center */
export function Sidebar({ active, onSelect }: SidebarProps) {
  return (
    <aside className="flex h-screen w-[220px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="px-4 py-5">
        <p className="text-sm font-semibold text-sidebar-foreground">IC ML Cybersecurity</p>
        <p className="text-xs text-muted-foreground">Detecção de Anomalias</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-2">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onSelect(id)}
            aria-current={active === id ? "page" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active === id
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
