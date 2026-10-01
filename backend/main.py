"""
JARVIS Main Server
FastAPI application with WebSocket chat, REST API, and static file serving.
"""
import asyncio
import os
import socket
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import edge_tts

from . import database as db
from . import ai_engine
from . import memory
from . import actions


# ─── Config ──────────────────────────────────────────────────
MODEL = os.getenv("JARVIS_MODEL", "llama3.1:8b")
HOST = os.getenv("JARVIS_HOST", "0.0.0.0")
PORT = int(os.getenv("JARVIS_PORT", "8000"))

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)


def get_local_ip() -> str:
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ─── App Lifecycle ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    local_ip = get_local_ip()
    print()
    print("=" * 55)
    print("   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗")
    print("   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝")
    print("   ██║███████║██████╔╝██║   ██║██║███████╗")
    print("██ ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║")
    print("╚████║██║  ██║██║  ██║ ╚████╔╝ ██║███████║")
    print(" ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝")
    print("=" * 55)
    print(f"  🤖 JARVIS está en línea (Modo Stark activado)")
    print(f"  🧠 Modelo: {MODEL}")
    print(f"  💻 Laptop:   http://localhost:{PORT}")
    print(f"  📱 Teléfono: http://{local_ip}:{PORT}")
    print("=" * 55)
    print()
    yield
    print("\n  👋 JARVIS se desconecta...\n")


app = FastAPI(title="JARVIS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ────────────────────────────────────────
class ConversationCreate(BaseModel):
    title: Optional[str] = "Nueva conversación"

class ConversationUpdate(BaseModel):
    title: str

class MemoryCreate(BaseModel):
    category: str
    content: str
    
class ActionRequest(BaseModel):
    action: str
    payload: str

class TTSRequest(BaseModel):
    text: str


# ─── REST API: Status & Features ────────────────────────────
@app.get("/api/status")
async def get_status():
    ollama = await ai_engine.check_ollama_status()
    return {
        "jarvis": "online",
        "ollama": ollama["status"],
        "models": ollama["models"],
        "current_model": MODEL,
    }


# ─── REST API: Actions & TTS ────────────────────────────────
@app.post("/api/action")
async def perform_action(req: ActionRequest):
    result = actions.execute_action(req.action, req.payload)
    return result

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    # Using a professional sounding Mexican Spanish voice
    communicate = edge_tts.Communicate(req.text, "es-MX-JorgeNeural")
    
    # We must save to a temporary file, then serve it.
    temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(temp_fd) # Close the file descriptor, edge-tts will open it
    
    await communicate.save(temp_path)
    
    return FileResponse(
        temp_path, 
        media_type="audio/mpeg", 
        background=None  # We should technically clean this up later, but for local it's okay
    )


# ─── REST API: Conversations ────────────────────────────────
@app.get("/api/conversations")
async def list_conversations():
    return db.get_conversations()


@app.post("/api/conversations")
async def create_conversation(data: ConversationCreate):
    conv_id = db.create_conversation(data.title)
    return {"id": conv_id, "title": data.title}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: int):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversación no encontrada")
    conv["messages"] = db.get_messages(conv_id)
    return conv


@app.put("/api/conversations/{conv_id}")
async def update_conversation(conv_id: int, data: ConversationUpdate):
    db.update_conversation_title(conv_id, data.title)
    return {"ok": True}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation_endpoint(conv_id: int):
    db.delete_conversation(conv_id)
    return {"ok": True}


# ─── REST API: Memories ─────────────────────────────────────
@app.get("/api/memories")
async def list_memories():
    return db.get_memories()


@app.post("/api/memories")
async def create_memory_endpoint(data: MemoryCreate):
    mem_id = db.add_memory(data.category, data.content)
    return {"id": mem_id}


@app.delete("/api/memories/{memory_id}")
async def delete_memory_endpoint(memory_id: int):
    db.delete_memory(memory_id)
    return {"ok": True}


# ─── WebSocket Chat ─────────────────────────────────────────
@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: int):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("content", "").strip()

            if not user_message:
                continue

            # Ensure conversation exists
            conv = db.get_conversation(conversation_id)
            if not conv:
                db.create_conversation()

            # Save user message
            db.add_message(conversation_id, "user", user_message)
            print(f"\n[USER] {user_message}")
            print(f"[JARVIS] Analizando respuesta...")

            # Build chat history (last 20 messages for context window)
            messages = db.get_messages(conversation_id, limit=20)
            chat_history = [
                {"role": m["role"], "content": m["content"]} 
                for m in messages if m["content"] and m["content"].strip()
            ]

            # Build system prompt with memories
            all_memories = db.get_memories()
            system_prompt = memory.get_system_prompt(all_memories)

            # Stream the response
            full_response = ""
            try:
                async for chunk in ai_engine.chat_stream(
                    messages=chat_history,
                    model=MODEL,
                    system_prompt=system_prompt,
                ):
                    full_response += chunk
                    await websocket.send_json({"type": "chunk", "content": chunk})

                # Save complete assistant response
                if full_response.strip():
                    db.add_message(conversation_id, "assistant", full_response)
                await websocket.send_json({"type": "done", "full_text": full_response})
                
                print(f"[JARVIS] Respuesta enviada. (Longitud: {len(full_response)} caracteres)")
                if len(full_response) > 0:
                    print(f"[TEXTO INVISIBLE]: {full_response[:150]}...")
                else:
                    print(f"[ALERTA]: El modelo de IA devolvió un texto completamente en blanco.")

                # Auto-title the conversation from the first message
                if len(messages) <= 1:
                    title = user_message[:50]
                    if len(user_message) > 50:
                        title += "..."
                    db.update_conversation_title(conversation_id, title)
                    await websocket.send_json(
                        {"type": "title_update", "title": title}
                    )

                # Extract memories in background (non-blocking)
                asyncio.create_task(
                    memory.extract_and_save_memories(
                        user_message, conversation_id, MODEL
                    )
                )

            except Exception as e:
                error_msg = str(e)
                if "Connection refused" in error_msg or "ConnectError" in error_msg:
                    error_msg = "No se pudo conectar con Ollama. ¿Está corriendo? Ejecuta 'ollama serve' en otra terminal."
                await websocket.send_json({"type": "error", "content": error_msg})

    except WebSocketDisconnect:
        pass


# ─── Serve Frontend ─────────────────────────────────────────
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"))
