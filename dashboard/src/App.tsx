import { useState } from "react";
import { Sidebar, type Section } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { MonitorSection } from "@/components/sections/MonitorSection";
import { PlaceholderSection } from "@/components/sections/PlaceholderSection";

function App() {
  const [section, setSection] = useState<Section>("monitor");

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar active={section} onSelect={setSection} />
      <div className="flex flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          {section === "monitor" && <MonitorSection />}
          {section === "alertas" && (
            <PlaceholderSection title="Alertas" story="Story 5.3 (Painel de Detalhe do Alerta)" />
          )}
          {section === "historico" && (
            <PlaceholderSection title="Histórico" story="Story 5.4 (Histórico de Alertas)" />
          )}
          {section === "modelos" && (
            <PlaceholderSection title="Modelos" story="Story 5.5 (Configuração de Threshold e Comparação de Modelos)" />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
