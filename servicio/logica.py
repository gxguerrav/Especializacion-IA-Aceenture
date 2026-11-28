"""Funcionalidad del servicio, sin nada de HTTP.

Conecta con lo construido en el Módulo 2:
  - `responder` usa el flujo RAG de `src/servicio_rag.py` (recuperar, filtrar, citar).
  - `estado_pedido` usa los pedidos simulados de `src/agente_con_herramientas.py`.

Modo del flujo RAG (variable de entorno SERVICIO_MODO):
  - "simulado" (por defecto): embeddings léxicos locales y modelo simulado; no necesita clave.
  - "real": Gemini; requiere GEMINI_API_KEY en el .env.

El flujo se construye la primera vez que se usa, no al importar: así el servicio arranca y
muestra /docs sin clave ni red.
"""

import os
import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parent.parent / "src")

SIN_INFORMACION = "No tengo informacion suficiente y verificada para responder esto."
PEDIDO_INEXISTENTE = "No existe ese pedido."

_consultar = None


def _obtener_consulta():
    """Crea el servicio RAG la primera vez que se necesita y lo reutiliza después."""
    global _consultar
    if _consultar is None:
        if SRC not in sys.path:
            sys.path.insert(0, SRC)
        from servicio_rag import crear_servicio

        modo = os.environ.get("SERVICIO_MODO", "simulado")
        if modo == "real":
            from dotenv import load_dotenv

            load_dotenv()
        _consultar = crear_servicio(modo)
    return _consultar


def responder(pregunta):
    """Devuelve (texto, fuentes). Si no hay fuente verificable, responde que no tiene
    información y la lista de fuentes va vacía, nunca una respuesta sin respaldo."""
    resultado = _obtener_consulta()(pregunta)
    if not resultado["fuentes"]:
        return SIN_INFORMACION, []
    return resultado["respuesta"], resultado["fuentes"]


def estado_pedido(pedido_id):
    """Estado del pedido simulado, o aviso de que no existe (sin inventar ningún estado)."""
    if SRC not in sys.path:
        sys.path.insert(0, SRC)
    from agente_con_herramientas import PEDIDOS

    pedido = PEDIDOS.get(pedido_id)
    return pedido["actual"] if pedido else PEDIDO_INEXISTENTE
