"""
Voice Mini App Backend
- Audio pipeline: Whisper STT + OpenAI TTS
- Guard proxy: controlled access to Telegram MTProto
- WebSocket: real-time message delivery
"""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from config import (
    GUARD_URL, GUARD_TOKEN, OPENAI_API_KEY,
    BIND_HOST, BIND_PORT, AGENT_VOICES, CORS_ORIGINS,
)
from auth import require_telegram_user

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("voice-backend")

app = FastAPI(title="Voice Mini App Backend", docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
guard = httpx.AsyncClient(base_url=GUARD_URL, headers={"Authorization": f"Bearer {GUARD_TOKEN}"})

# --- WebSocket connections ---

active_connections: dict[str, WebSocket] = {}

# --- Audio temp dir ---

AUDIO_DIR = Path("/tmp/voice-mini-app")
AUDIO_DIR.mkdir(exist_ok=True)


# --- Endpoints ---

@app.get("/health")
async def health():
    guard_resp = await guard.get("/health")
    return {
        "status": "ok",
        "guard": guard_resp.json(),
        "agents": list(AGENT_VOICES.keys()),
    }


@app.post("/transcribe")
async def transcribe(audio: UploadFile, user: dict = Depends(require_telegram_user)):
    """Speech-to-text via Whisper API."""
    audio_bytes = await audio.read()
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio file too large (max 25MB)")

    tmp_path = AUDIO_DIR / f"{uuid.uuid4()}.ogg"
    tmp_path.write_bytes(audio_bytes)

    try:
        transcript = await openai.audio.transcriptions.create(
            model="whisper-1",
            file=tmp_path,
            language="ru",
        )
        log.info(f"Transcribed: {transcript.text[:100]}...")
        return {"ok": True, "text": transcript.text}
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/synthesize")
async def synthesize(agent: str, text: str, user: dict = Depends(require_telegram_user)):
    """Text-to-speech via OpenAI TTS."""
    if agent not in AGENT_VOICES:
        raise HTTPException(400, f"Unknown agent: {agent}")

    voice = AGENT_VOICES[agent]["voice"]

    response = await openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="opus",
    )

    audio_path = AUDIO_DIR / f"{uuid.uuid4()}.opus"
    audio_path.write_bytes(response.content)

    from fastapi.responses import FileResponse
    return FileResponse(
        audio_path,
        media_type="audio/opus",
        headers={"X-Agent": agent, "X-Voice": voice},
        background=_cleanup(audio_path),
    )


@app.post("/send")
async def send_message(agent: str, text: str, user: dict = Depends(require_telegram_user)):
    """Send text message to agent via Guard."""
    if agent not in AGENT_VOICES:
        raise HTTPException(400, f"Unknown agent: {agent}")

    chat_id = AGENT_VOICES[agent]["chat_id"]
    resp = await guard.post("/send", json={"chat_id": chat_id, "text": text})

    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.json())

    return resp.json()


@app.post("/voice")
async def voice_message(agent: str, audio: UploadFile, user: dict = Depends(require_telegram_user)):
    """Full pipeline: audio → transcribe → send to agent → poll response → TTS → return audio."""
    if agent not in AGENT_VOICES:
        raise HTTPException(400, f"Unknown agent: {agent}")

    # 1. Transcribe
    audio_bytes = await audio.read()
    tmp_path = AUDIO_DIR / f"{uuid.uuid4()}.ogg"
    tmp_path.write_bytes(audio_bytes)

    try:
        transcript = await openai.audio.transcriptions.create(
            model="whisper-1",
            file=tmp_path,
            language="ru",
        )
        user_text = transcript.text
        log.info(f"User said: {user_text[:100]}")
    finally:
        tmp_path.unlink(missing_ok=True)

    # 2. Send to agent via Guard
    chat_id = AGENT_VOICES[agent]["chat_id"]
    send_resp = await guard.post("/send", json={"chat_id": chat_id, "text": user_text})
    if send_resp.status_code != 200:
        raise HTTPException(502, f"Guard send failed: {send_resp.text}")

    sent_msg_id = send_resp.json()["message_id"]

    # 3. Poll for response (max 60 seconds)
    agent_text = await _poll_response(chat_id, sent_msg_id, timeout=60)

    if not agent_text:
        return {"ok": True, "user_text": user_text, "agent_text": None, "audio_url": None}

    # 4. TTS
    voice = AGENT_VOICES[agent]["voice"]
    tts_resp = await openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=agent_text,
        response_format="opus",
    )
    audio_path = AUDIO_DIR / f"{uuid.uuid4()}.opus"
    audio_path.write_bytes(tts_resp.content)

    # Return text + audio path (frontend will fetch audio separately)
    return {
        "ok": True,
        "user_text": user_text,
        "agent_text": agent_text,
        "audio_id": audio_path.name,
    }


@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Serve generated audio file."""
    audio_path = AUDIO_DIR / audio_id
    if not audio_path.exists() or not audio_path.name.endswith(".opus"):
        raise HTTPException(404, "Audio not found")

    from fastapi.responses import FileResponse
    return FileResponse(audio_path, media_type="audio/opus", background=_cleanup(audio_path))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for real-time message push."""
    await ws.accept()
    conn_id = str(uuid.uuid4())[:8]
    active_connections[conn_id] = ws
    log.info(f"WS connected: {conn_id}")

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "subscribe":
                # Client subscribes to agent updates
                agent = msg.get("agent")
                if agent in AGENT_VOICES:
                    asyncio.create_task(_ws_poll_loop(ws, agent, conn_id))
    except WebSocketDisconnect:
        log.info(f"WS disconnected: {conn_id}")
        active_connections.pop(conn_id, None)


# --- Helpers ---

async def _poll_response(chat_id: int, since_id: int, timeout: int = 60) -> str | None:
    """Poll Guard for new messages after since_id."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = await guard.post("/messages", json={
            "chat_id": chat_id,
            "since_id": since_id,
            "limit": 5,
        })
        if resp.status_code == 200:
            messages = resp.json().get("messages", [])
            for m in messages:
                if m["sender_id"] != 1558206160:  # not accside itself
                    continue
                # Actually we want bot responses, not accside
                # Bot responses come from the bot's user ID
                pass
            # Any new message that's not from us
            for m in messages:
                if m["id"] > since_id and m["text"]:
                    return m["text"]
        await asyncio.sleep(2)
    return None


async def _ws_poll_loop(ws: WebSocket, agent: str, conn_id: str):
    """Background loop to push new messages to WebSocket client."""
    chat_id = AGENT_VOICES[agent]["chat_id"]
    last_id = 0

    # Get current last message ID
    resp = await guard.post("/messages", json={"chat_id": chat_id, "limit": 1})
    if resp.status_code == 200:
        messages = resp.json().get("messages", [])
        if messages:
            last_id = messages[-1]["id"]

    while conn_id in active_connections:
        try:
            resp = await guard.post("/messages", json={
                "chat_id": chat_id,
                "since_id": last_id,
                "limit": 10,
            })
            if resp.status_code == 200:
                messages = resp.json().get("messages", [])
                for m in messages:
                    if m["id"] > last_id:
                        last_id = m["id"]
                        await ws.send_json({
                            "type": "message",
                            "agent": agent,
                            "message": m,
                        })
        except Exception:
            break
        await asyncio.sleep(3)


def _cleanup(path: Path):
    """Background task to delete temp file after response."""
    from starlette.background import BackgroundTask
    return BackgroundTask(lambda: path.unlink(missing_ok=True))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT)
