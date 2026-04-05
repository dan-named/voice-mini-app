export interface Agent {
  id: string;
  name: string;
  voice: string;
  emoji: string;
}

export interface Message {
  id: string;
  role: "user" | "agent";
  text: string;
  audioId?: string;
  timestamp: number;
}

export const AGENTS: Agent[] = [
  { id: "osen", name: "Осень", voice: "onyx", emoji: "🍂" },
  { id: "vesna", name: "Весна", voice: "nova", emoji: "🌸" },
  { id: "leto", name: "Лето", voice: "echo", emoji: "☀️" },
  { id: "zima", name: "Зима", voice: "alloy", emoji: "❄️" },
];
