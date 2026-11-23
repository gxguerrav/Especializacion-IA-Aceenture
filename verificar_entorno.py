"""Verifica el entorno antes de la corrida final del Gate 2.

Muestra la versión de cada paquete y si las variables están definidas (nunca imprime la
clave). Termina con código 1 si falta algo obligatorio.

    python verificar_entorno.py
"""

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PAQUETES = ["langchain-core", "langchain-chroma", "langchain-google-genai", "langgraph",
            "python-dotenv", "pytest"]
VARIABLES_OPCIONALES = ["GEMINI_API_KEY"]  # solo hace falta con --real
INDICES = {"real": RAIZ / "vectorstore", "simulado": RAIZ / "vectorstore_sim"}

try:
    from dotenv import load_dotenv
    load_dotenv(RAIZ / ".env")
except ImportError:
    pass

problemas = []
print("Python:", sys.version.split()[0])
if sys.version_info < (3, 10):
    problemas.append("usar Python 3.10 o superior")

for paquete in PAQUETES:
    try:
        print(f"{paquete}: {version(paquete)}")
    except PackageNotFoundError:
        print(f"{paquete}: NO instalado")
        problemas.append(f"instalar {paquete} (pip install -r requirements.txt)")

for nombre in VARIABLES_OPCIONALES:
    estado = "definida" if os.getenv(nombre) else "no definida (solo se necesita con --real)"
    print(f"{nombre}: {estado}")

hay_indice = False
for modo, carpeta in INDICES.items():
    ok = carpeta.is_dir() and any(carpeta.iterdir())
    hay_indice = hay_indice or ok
    print(f"indice {modo} en {carpeta.name}/: {'ok' if ok else 'no existe o esta vacio'}")
if not hay_indice:
    problemas.append("crear el indice: python src/servicio_rag.py (simulado) "
                     "o python src/indexar_corpus.py (real)")

print()
if problemas:
    print("Pendiente: " + "; ".join(problemas))
    sys.exit(1)
print("Entorno listo para la corrida final")
