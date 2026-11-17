"""Chequeo sin API del flujo RAG (checklist del Bloque 28).

Confirma que la carpeta del índice existe y que está en .gitignore.

Uso (desde la raíz del proyecto):
    python src/preflight.py
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def preflight_check(persist_directory, gitignore_path=RAIZ / ".gitignore"):
    """Devuelve una lista de problemas (vacía si todo está en orden)."""
    problemas = []
    if not os.path.isdir(persist_directory):
        problemas.append(f"{persist_directory} no existe: corriste la indexacion?")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, encoding="utf-8") as archivo:
            contenido = archivo.read()
        nombre_carpeta = Path(persist_directory).name
        if nombre_carpeta not in contenido:
            problemas.append(f"{nombre_carpeta}/ no esta en {Path(gitignore_path).name}")
    else:
        problemas.append(f"no existe {gitignore_path} en este proyecto")
    return problemas


if __name__ == "__main__":
    problemas = preflight_check(RAIZ / "vectorstore")
    if problemas:
        print("Preflight con problemas:")
        for problema in problemas:
            print(" -", problema)
    else:
        print("Preflight OK: la carpeta del indice existe y esta en .gitignore")
