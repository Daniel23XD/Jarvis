"""
JARVIS AI Engine Module (GROQ CLOUD EDITION)
Handles communication with Groq API for lightning-fast LLM inference.
"""
import httpx
import json
import os
from typing import AsyncGenerator

# Cargamos la clave desde las variables de entorno
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Usamos Llama 3.1 70B (¡Es mucho más inteligente que el 8B y rapidísimo en Groq!)
DEFAULT_MODEL = "llama-3.1-70b-versatile"


async def check_ollama_status() -> dict:
    """Mock status check to keep the frontend happy."""
    if not GROQ_API_KEY:
        return {"status": "error", "models": ["FALTA GROQ_API_KEY"]}
    return {"status": "online", "models": [DEFAULT_MODEL]}


async def chat_stream(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """Stream chat response from Groq token by token."""
    if not GROQ_API_KEY:
        yield "ERROR: No has configurado tu GROQ_API_KEY."
        return

    groq_messages = []
    if system_prompt:
        groq_messages.append({"role": "system", "content": system_prompt})

    # Mezclar mensajes consecutivos del mismo rol para evitar errores de la API
    for m in messages:
        if not groq_messages or groq_messages[-1]["role"] != m["role"] or groq_messages[-1]["role"] == "system":
            groq_messages.append({"role": m["role"], "content": m["content"]})
        else:
            groq_messages[-1]["content"] += "\n" + m["content"]

    payload = {
        "model": model,
        "messages": groq_messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        async with client.stream(
            "POST", f"{GROQ_BASE_URL}/chat/completions", json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                err_text = await response.aread()
                raise Exception(f"Error de Groq {response.status_code}: {err_text.decode('utf-8', errors='ignore')}")
                
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue


async def chat_single(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
) -> str:
    """Get a single (non-streaming) response from Groq."""
    if not GROQ_API_KEY:
        return ""

    groq_messages = []
    if system_prompt:
        groq_messages.append({"role": "system", "content": system_prompt})
    
    for m in messages:
        if not groq_messages or groq_messages[-1]["role"] != m["role"] or groq_messages[-1]["role"] == "system":
            groq_messages.append({"role": m["role"], "content": m["content"]})
        else:
            groq_messages[-1]["content"] += "\n" + m["content"]

    payload = {
        "model": model,
        "messages": groq_messages,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.post(
            f"{GROQ_BASE_URL}/chat/completions", json=payload, headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0].get("message", {}).get("content", "")
        return ""


async def pull_model(model: str = DEFAULT_MODEL) -> AsyncGenerator[str, None]:
    """Mock pull model for Groq."""
    yield "Groq es un servicio en la nube."
    yield "El modelo ya está alojado y listo."
    yield "success"
