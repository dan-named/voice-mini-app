import { useState } from "react";
import { AGENTS } from "./types";
import { AgentCard } from "./components/AgentCard";
import { ChatView } from "./components/ChatView";

export default function App() {
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "var(--tg-theme-bg-color, #fff)",
        color: "var(--tg-theme-text-color, #000)",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Agent selector */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "12px 12px 8px",
          borderBottom: "1px solid var(--tg-theme-secondary-bg-color, #eee)",
        }}
      >
        {AGENTS.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            selected={agent.id === selectedAgent.id}
            onSelect={() => setSelectedAgent(agent)}
          />
        ))}
      </div>

      {/* Chat */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <ChatView agent={selectedAgent} />
      </div>
    </div>
  );
}
