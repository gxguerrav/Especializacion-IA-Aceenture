"""Indexa el corpus de la miniaplicación en un vector store Chroma persistido en disco.

Flujo: corpus -> chunking recursivo -> embeddings (Gemini) -> Chroma en "vectorstore/".
Se ejecuta una sola vez (o cuando el corpus cambia); las consultas posteriores se
reconectan al índice con Chroma(persist_directory=...) sin recalcular embeddings.

Uso (con el entorno virtual activo y GEMINI_API_KEY en el .env):
    python src/indexar_corpus.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_VECTORSTORE = str(RAIZ / "vectorstore")
NOMBRE_COLECCION = "corpus_miniaplicacion"
MODELO_EMBEDDINGS = "models/gemini-embedding-001"

# Se eligió el splitter recursivo porque el corpus es documentación con ideas
# completas por párrafo: respeta esos límites en vez de cortar cada N caracteres.
# 250 caracteres cubren una idea completa; el overlap de 40 (16%) está en el
# 15-20% recomendado y solo actúa cuando un documento hay que dividirlo.
CHUNK_SIZE = 250
CHUNK_OVERLAP = 40

# Cada documento tiene un tema distinto de la miniaplicación (fuente en metadatos).
CORPUS = [
    {
        "fuente": "reintentos",
        "texto": (
            "El cliente de la API reintenta hasta 3 veces ante un TimeoutError o un "
            "error temporal (429, 5xx), con espera creciente entre intentos "
            "(backoff exponencial con techo y jitter)."
        ),
    },
    {
        "fuente": "autenticacion",
        "texto": (
            "Los errores de autenticación (401 y 403) nunca se reintentan: fallan de "
            "inmediato con un ValueError, porque una clave rechazada no se arregla "
            "reintentando."
        ),
    },
    {
        "fuente": "costo",
        "texto": (
            "El costo de cada llamada se calcula a partir de totalTokenCount en "
            "usageMetadata y la tarifa vigente por cada 1000 tokens, y se acumula "
            "en una variable de sesión."
        ),
    },
    {
        "fuente": "agente",
        "texto": (
            "El agente de atención de pedidos decide por sí mismo qué herramienta "
            "usar según su descripción: consultar el estado de un pedido, calcular "
            "el costo de un pedido o generar un reembolso, que exige aprobación "
            "humana antes de ejecutarse."
        ),
    },
    {
        "fuente": "pruebas",
        "texto": (
            "Las pruebas unitarias del cliente usan mocks en lugar de llamar a la "
            "API real, de forma que la suite completa corre en menos de un segundo "
            "y no gasta tokens."
        ),
    },
]


def main():
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit('Falta GEMINI_API_KEY. Defínela en tu archivo ".env" y vuelve a ejecutar.')

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.create_documents(
        [doc["texto"] for doc in CORPUS],
        metadatas=[{"fuente": doc["fuente"]} for doc in CORPUS],
    )

    embeddings = GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)

    # Reindexar debe reemplazar el índice, no acumular duplicados: from_documents
    # agrega a la colección existente. Es una operación local (sin red).
    Chroma(
        collection_name=NOMBRE_COLECCION,
        persist_directory=DIRECTORIO_VECTORSTORE,
        embedding_function=embeddings,
    ).delete_collection()

    # Solo la llamada que depende de la red va dentro del try.
    try:
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=NOMBRE_COLECCION,
            persist_directory=DIRECTORIO_VECTORSTORE,
        )
    except Exception as error:
        mensaje = str(error)
        if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
            print("Límite de peticiones alcanzado. Espera un minuto y vuelve a ejecutar.")
        elif "API key" in mensaje or "401" in mensaje or "403" in mensaje:
            print('La API rechazó tu clave. Revisa el valor de GEMINI_API_KEY en tu ".env".')
        else:
            print("No se pudo indexar el corpus:", type(error).__name__)
        print("Detalle técnico:", mensaje)
        raise SystemExit(1)

    print(f"Indexados {len(chunks)} chunks en vectorstore/")

    # Comprobación de persistencia: reconectar sin recalcular embeddings.
    recargado = Chroma(
        collection_name=NOMBRE_COLECCION,
        persist_directory=DIRECTORIO_VECTORSTORE,
        embedding_function=embeddings,
    )
    print(f"Chunks en el índice recargado: {recargado._collection.count()}")


if __name__ == "__main__":
    main()
