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

# Base de conocimiento del asistente de gas en cilindros. Cada documento es un tema
# distinto del negocio (su nombre queda como "fuente" en los metadatos) y solo usa
# datos que ya existen en el proyecto: catalogo de prompts/banco.py y herramientas
# de src/agente_con_herramientas.py.
CORPUS = [
    {
        "fuente": "catalogo_precios",
        "texto": (
            "Vendemos cilindros de gas de 5 kg a $12.000, de 11 kg a $20.000, de "
            "15 kg a $27.000 y de 45 kg a $75.000. No existen otros tamanos ni "
            "precios fuera de este catalogo."
        ),
    },
    {
        "fuente": "despacho",
        "texto": (
            "El despacho a domicilio es gratuito para todos los pedidos. Para "
            "agendar la entrega necesitamos la direccion completa del cliente."
        ),
    },
    {
        "fuente": "como_comprar",
        "texto": (
            "Para armar un pedido se necesitan tres datos: el tipo de cilindro "
            "(5, 11, 15 o 45 kg), la cantidad de cilindros y la direccion de "
            "entrega. El total es el precio del cilindro multiplicado por la "
            "cantidad."
        ),
    },
    {
        "fuente": "estado_pedido",
        "texto": (
            "Cada pedido tiene un numero con formato GAS-1001. Su estado avanza "
            "por estos pasos: recibido, preparado en bodega, en camino y "
            "entregado. El cliente puede consultar el estado actual o el "
            "historial completo con su numero de pedido."
        ),
    },
    {
        "fuente": "reembolsos",
        "texto": (
            "Los reembolsos solo se generan cuando el cliente los pide "
            "explicitamente. Mueven dinero y no se pueden deshacer, por lo que "
            "requieren aprobacion de un supervisor humano antes de ejecutarse."
        ),
    },
    {
        "fuente": "reclamos",
        "texto": (
            "Si el cliente tiene un reclamo, el asistente lo clasifica como "
            "reclamo y no inventa soluciones. Un reembolso solo procede sobre "
            "un pedido existente y con un monto mayor que cero."
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

    # ids predecibles por chunk (fuente-0, fuente-1...): permiten etiquetar el conjunto
    # de evaluacion de recuperacion del Bloque 27.
    ids, contador = [], {}
    for chunk in chunks:
        fuente = chunk.metadata["fuente"]
        ids.append(f"{fuente}-{contador.get(fuente, 0)}")
        contador[fuente] = contador.get(fuente, 0) + 1

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
            ids=ids,
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
