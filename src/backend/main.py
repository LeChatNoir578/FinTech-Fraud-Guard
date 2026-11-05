"""
FinTech Fraud Guard - Backend Entrypoint
Configurado para escuchar en 0.0.0.0 y con CORS universal para dispositivos móviles físicos.
"""
import sys
import os

# Asegurar que el directorio raíz del proyecto esté en el path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app

if __name__ == "__main__":
    import uvicorn
    # Servidor Uvicorn escuchando en '0.0.0.0' para permitir conexiones desde dispositivos en la red local
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
