import os

GUARD_URL = os.environ.get("GUARD_URL", "http://127.0.0.1:8900")
GUARD_TOKEN = os.environ["GUARD_BEARER_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

BIND_HOST = os.environ.get("VOICE_BIND_HOST", "127.0.0.1")
BIND_PORT = int(os.environ.get("VOICE_BIND_PORT", "8901"))

# Agent voice mapping (OpenAI TTS voices)
AGENT_VOICES = {
    "osen": {"voice": "onyx", "name": "Осень", "chat_id": 8363371697},
    "vesna": {"voice": "nova", "name": "Весна", "chat_id": 8790692679},
    "leto": {"voice": "echo", "name": "Лето", "chat_id": 8749893876},
    "zima": {"voice": "alloy", "name": "Зима", "chat_id": 8600326333},
}

# Allowed origins for CORS (Telegram WebApp + local dev)
CORS_ORIGINS = [
    "https://voice.dan-ai.com",
    "https://dan-named.github.io",
    "http://localhost:5173",
]
