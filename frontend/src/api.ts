const API_URL = import.meta.env.VITE_API_URL || "https://voice-api.dan-ai.com";

export async function transcribeAndSend(agent: string, audioBlob: Blob) {
  const form = new FormData();
  form.append("audio", audioBlob, "voice.ogg");

  const resp = await fetch(`${API_URL}/voice?agent=${agent}`, {
    method: "POST",
    body: form,
  });

  if (!resp.ok) throw new Error(`API error: ${resp.status}`);
  return resp.json() as Promise<{
    ok: boolean;
    user_text: string;
    agent_text: string | null;
    audio_id: string | null;
  }>;
}

export function audioUrl(audioId: string) {
  return `${API_URL}/audio/${audioId}`;
}

export function createWebSocket(agent: string, onMessage: (data: unknown) => void) {
  const wsUrl = API_URL.replace(/^http/, "ws") + "/ws";
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: "subscribe", agent }));
  };

  ws.onmessage = (e) => {
    onMessage(JSON.parse(e.data));
  };

  return ws;
}
