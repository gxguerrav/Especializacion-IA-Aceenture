"""Registro de latencia y costo del flujo RAG completo (Bloque 28).

Corre consultas RAG reales contra el índice Chroma creado por indexar_corpus.py y mide:
  - el tiempo de cada etapa por separado: embed de la pregunta (red), búsqueda vectorial
    (local) y generación (red);
  - los tokens reales que reporta el modelo (usage_metadata), base del costo real.
Cada consulta se agrega como una línea JSON a registros_latencia_costo.jsonl (JSON Lines).

Uso (con el entorno virtual activo, GEMINI_API_KEY en el .env y el índice ya creado con
`python src/indexar_corpus.py`):
    python src/registro_rag.py "cuanto cuesta el cilindro de 15 kilos" "el despacho tiene costo"
    python src/registro_rag.py --k 6 "cuanto cuesta el cilindro de 15 kilos"
Sin preguntas, usa las 3 primeras del conjunto de evaluación del Bloque 27.
"""

import argparse
import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from recuperacion import (
    DIRECTORIO_VECTORSTORE,
    MODELO_EMBEDDINGS,
    NOMBRE_COLECCION,
    PROMPT_TEMPLATE,
    formatear_contexto,
)

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_REGISTROS = RAIZ / "registros_latencia_costo.jsonl"
MODELO_CHAT = "gemini-3.5-flash-lite"  # el mismo modelo que usa el resto del proyecto


@contextmanager
def medir(tiempos, etapa):
    """Guarda en `tiempos[etapa]` los segundos que tarda el bloque (perf_counter, no time.time)."""
    inicio = time.perf_counter()
    yield
    tiempos[etapa] = time.perf_counter() - inicio


def registrar_consulta(
    pregunta,
    persist_directory=DIRECTORIO_VECTORSTORE,
    k=3,
    embeddings=None,
    chat_model=None,
):
    """Corre una consulta RAG midiendo cada etapa y devuelve el registro (un dict).

    `embeddings` y `chat_model` permiten inyectar objetos falsos en las pruebas; por
    defecto se usan los reales de Gemini.
    """
    if embeddings is None:
        embeddings = GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)
    if chat_model is None:
        chat_model = ChatGoogleGenerativeAI(model=MODELO_CHAT)

    vectorstore = Chroma(
        collection_name=NOMBRE_COLECCION,
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )

    tiempos = {}
    with medir(tiempos, "embed"):
        vector = embeddings.embed_query(pregunta)
    with medir(tiempos, "busqueda"):
        chunks = vectorstore.similarity_search_by_vector(vector, k=k)

    contexto, _citas = formatear_contexto(chunks)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)

    with medir(tiempos, "generacion"):
        respuesta = chat_model.invoke(prompt)

    usage = getattr(respuesta, "usage_metadata", None)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pregunta": pregunta,
        "k": k,
        "tiempos_ms": {etapa: round(s * 1000, 2) for etapa, s in tiempos.items()},
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "tokens": dict(usage) if usage else None,
    }


def guardar_registro(registro, archivo=ARCHIVO_REGISTROS):
    """Agrega el registro como una sola línea JSON (JSON Lines) al final del archivo."""
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Registra latencia y tokens del flujo RAG.")
    parser.add_argument("preguntas", nargs="*", help="preguntas a consultar")
    parser.add_argument("--k", type=int, default=3, help="chunks a recuperar (default 3)")
    args = parser.parse_args()

    preguntas = args.preguntas
    if not preguntas:
        from evaluacion_recuperacion import casos_evaluacion

        preguntas = [c["pregunta"] for c in casos_evaluacion[:3]]

    for pregunta in preguntas:
        registro = registrar_consulta(pregunta, k=args.k)
        print(json.dumps(registro, indent=2, ensure_ascii=False))
        guardar_registro(registro)

    print(f"\n{len(preguntas)} registro(s) agregados a {ARCHIVO_REGISTROS.name}")


if __name__ == "__main__":
    main()
