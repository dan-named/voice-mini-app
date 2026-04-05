import { useState, useRef, useEffect } from "react";
import type { Agent, Message } from "../types";
import { useRecorder } from "../hooks/useRecorder";
import { transcribeAndSend, audioUrl } from "../api";

interface Props {
  agent: Agent;
}

export function ChatView({ agent }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { recording, start, stop, permissionError } = useRecorder();
  const bottomRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Reset messages when switching agents
  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [agent.id]);

  const handleRecord = async () => {
    if (recording) {
      const blob = await stop();
      if (blob.size === 0) return;

      setLoading(true);
      setError(null);

      try {
        const result = await transcribeAndSend(agent.id, blob);

        const userMsg: Message = {
          id: crypto.randomUUID(),
          role: "user",
          text: result.user_text,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, userMsg]);

        if (result.agent_text) {
          const agentMsg: Message = {
            id: crypto.randomUUID(),
            role: "agent",
            text: result.agent_text,
            audioId: result.audio_id || undefined,
            timestamp: Date.now(),
          };
          setMessages((prev) => [...prev, agentMsg]);

          // Auto-play response
          if (result.audio_id && audioRef.current) {
            audioRef.current.src = audioUrl(result.audio_id);
            audioRef.current.play().catch(() => {});
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    } else {
      try {
        await start();
      } catch {
        setError("Microphone access denied");
      }
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 8 }}>
      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {messages.length === 0 && !loading && (
          <div style={{ textAlign: "center", color: "var(--tg-theme-hint-color, #999)", marginTop: 40 }}>
            {agent.emoji} {agent.name}
            <br />
            <span style={{ fontSize: 13 }}>Hold the button to record a voice message</span>
          </div>
        )}

        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              padding: "8px 12px",
              borderRadius: 12,
              background:
                m.role === "user"
                  ? "var(--tg-theme-button-color, #3390ec)"
                  : "var(--tg-theme-secondary-bg-color, #f0f0f0)",
              color:
                m.role === "user"
                  ? "var(--tg-theme-button-text-color, #fff)"
                  : "var(--tg-theme-text-color, #000)",
              fontSize: 14,
              lineHeight: 1.4,
            }}
          >
            {m.text}
            {m.audioId && (
              <button
                onClick={() => {
                  if (audioRef.current) {
                    audioRef.current.src = audioUrl(m.audioId!);
                    audioRef.current.play().catch(() => {});
                  }
                }}
                style={{
                  display: "block",
                  marginTop: 4,
                  background: "none",
                  border: "none",
                  color: "inherit",
                  opacity: 0.7,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                ▶ Play audio
              </button>
            )}
          </div>
        ))}

        {loading && (
          <div
            style={{
              alignSelf: "flex-start",
              padding: "8px 12px",
              borderRadius: 12,
              background: "var(--tg-theme-secondary-bg-color, #f0f0f0)",
              color: "var(--tg-theme-hint-color, #999)",
              fontSize: 14,
            }}
          >
            {agent.name} thinking...
          </div>
        )}

        {(error || permissionError) && (
          <div style={{ color: "red", fontSize: 13, textAlign: "center", padding: "0 12px" }}>
            {permissionError || error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Record button */}
      <div style={{ padding: 12, display: "flex", justifyContent: "center" }}>
        <button
          onClick={handleRecord}
          disabled={loading}
          style={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            border: "none",
            background: recording
              ? "#e53935"
              : loading
                ? "var(--tg-theme-hint-color, #999)"
                : "var(--tg-theme-button-color, #3390ec)",
            color: "var(--tg-theme-button-text-color, #fff)",
            fontSize: 24,
            cursor: loading ? "default" : "pointer",
            transition: "all 0.2s",
            transform: recording ? "scale(1.1)" : "scale(1)",
          }}
        >
          {recording ? "⏹" : loading ? "..." : "🎤"}
        </button>
      </div>

      <audio ref={audioRef} style={{ display: "none" }} />
    </div>
  );
}
