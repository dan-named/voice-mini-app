import type { Agent } from "../types";

interface Props {
  agent: Agent;
  selected: boolean;
  onSelect: () => void;
}

export function AgentCard({ agent, selected, onSelect }: Props) {
  return (
    <button
      onClick={onSelect}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        padding: "12px 16px",
        borderRadius: 12,
        border: selected ? "2px solid var(--tg-theme-button-color, #3390ec)" : "2px solid transparent",
        background: selected
          ? "var(--tg-theme-secondary-bg-color, #f0f0f0)"
          : "var(--tg-theme-bg-color, #fff)",
        color: "var(--tg-theme-text-color, #000)",
        cursor: "pointer",
        flex: 1,
        minWidth: 70,
      }}
    >
      <span style={{ fontSize: 28 }}>{agent.emoji}</span>
      <span style={{ fontSize: 13, fontWeight: selected ? 600 : 400 }}>{agent.name}</span>
    </button>
  );
}
