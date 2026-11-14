"""Recuperación semántica y prompt dinámico con fuente citada (Bloque 26).

Asistente de atención de clientes de gas en cilindros: responde preguntas sobre
catálogo, despacho, pedidos y reembolsos citando de qué documento sale cada dato.

Se reconecta al índice persistido por indexar_corpus.py (sin reindexar ni recalcular
embeddings del corpus), recupera los k chunks más cercanos a la pregunta y arma un
prompt que obliga al modelo a citar cada afirmación con su número [N].

Uso (con el entorno virtual activo, GEMINI_API_KEY en el .env y el índice ya creado
con `python src/indexar_corpus.py`):
    python src/recuperacion.py "cuanto cuesta el cilindro de 15 kilos"
"""

import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

RAIZ = Path(__file__).resolve().parent.parent
# Ruta absoluta: una relativa haría que Chroma cree un índice vacío si el script se
# ejecuta desde otra carpeta.
DIRECTORIO_VECTORSTORE = str(RAIZ / "vectorstore")
NOMBRE_COLECCION = "corpus_miniaplicacion"  # misma colección que indexar_corpus.py
MODELO_EMBEDDINGS = "models/gemini-embedding-001"

PROMPT_TEMPLATE = """Responde la pregunta usando SOLO el contexto de abajo. Cita la \
fuente de cada afirmacion con su numero entre corchetes, como [1]. Si el contexto no \
alcanza para responder, dilo explicitamente en vez de inventar.

Contexto:
{contexto}

Pregunta: {pregunta}

Respuesta:"""


def formatear_contexto(chunks_recuperados):
    """Arma un bloque de contexto numerado para el prompt, y un mapa numero -> fuente
    para reconstruir la cita después."""
    lineas = []
    citas = {}
    for i, doc in enumerate(chunks_recuperados, start=1):
        fuente = doc.metadata.get("fuente", "desconocida")
        lineas.append(f"[{i}] {doc.page_content}")
        citas[i] = fuente
    contexto = "\n\n".join(lineas)
    return contexto, citas


def resolver_citas(respuesta, citas):
    """Extrae los [N] de la respuesta del modelo y los mapea a su fuente.

    Un número que no existe en `citas` (cita alucinada, p. ej. [99]) no lanza error:
    se marca como inválido para poder detectarlo.
    """
    indices = [int(n) for n in re.findall(r"\[(\d+)\]", respuesta)]
    return {i: citas.get(i, "Cita invalida / no encontrada") for i in indices}


def construir_prompt(pregunta, persist_directory=DIRECTORIO_VECTORSTORE, k=3, embeddings=None):
    """Recupera los k chunks más relevantes para la pregunta y arma el prompt dinámico
    con contexto numerado, listo para pasarle al modelo.

    Solo se reconecta al índice existente: nunca llama a from_documents.
    `embeddings` permite inyectar otro objeto (p. ej. uno falso en pruebas).
    """
    if embeddings is None:
        embeddings = GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)
    vectorstore = Chroma(
        collection_name=NOMBRE_COLECCION,
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})

    chunks_recuperados = retriever.invoke(pregunta)
    contexto, citas = formatear_contexto(chunks_recuperados)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)
    return prompt, citas


if __name__ == "__main__":
    load_dotenv()
    pregunta = " ".join(sys.argv[1:]) or "cuanto cuesta el cilindro de 15 kilos"
    prompt, citas = construir_prompt(pregunta)
    print(prompt)
    print(citas)
