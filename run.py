"""
JARVIS Launcher
Run this file to start the JARVIS server.
"""
import uvicorn
import os

if __name__ == "__main__":
    # Render y otras nubes usan la variable PORT. Si no existe, usamos 8000.
    port = int(os.getenv("PORT", os.getenv("JARVIS_PORT", "8000")))
    print(f"==================================================")
    print(f"🚀 Iniciando JARVIS (Edición Nube) en el puerto {port}")
    print(f"==================================================")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Desactivado para producción en la nube
    )
