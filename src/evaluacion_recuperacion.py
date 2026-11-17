"""Evaluación de la recuperación: precisión y recall sobre un conjunto de casos (Bloque 27).

Corre cada pregunta de `casos_evaluacion` contra el retriever real (índice Chroma creado
por indexar_corpus.py), compara los ids recuperados con los ids relevantes etiquetados a
mano y promedia precision@k y recall@k. Guarda el registro en resultados_evaluacion.txt
para poder comparar corridas cuando cambie el chunk_size, el k o el corpus.

Uso (con el entorno virtual activo, GEMINI_API_KEY en el .env y el índice ya creado con
`python src/indexar_corpus.py`):
    python src/evaluacion_recuperacion.py
"""

from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from indexar_corpus import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DIRECTORIO_VECTORSTORE,
    MODELO_EMBEDDINGS,
    NOMBRE_COLECCION,
)

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_RESULTADOS = RAIZ / "resultados_evaluacion.txt"

K = 3  # cuantos chunks recupera el retriever y cuantos evalua la funcion

# Conjunto de evaluacion. Se etiqueto leyendo el CORPUS de indexar_corpus.py (no lo que
# devuelve el retriever). Cada documento cabe en un solo chunk, asi que su id es
# "<fuente>-0". El ultimo caso no tiene respuesta en el corpus (ids_relevantes vacio):
# su recall es None y se excluye del promedio de recall.
casos_evaluacion = [
    {"pregunta": "cuanto cuesta el cilindro de 15 kilos",
     "ids_relevantes": {"catalogo_precios-0"}},
    {"pregunta": "que tamanos de cilindro venden",
     "ids_relevantes": {"catalogo_precios-0"}},
    {"pregunta": "el despacho a domicilio tiene costo",
     "ids_relevantes": {"despacho-0"}},
    {"pregunta": "que necesito para agendar la entrega",
     "ids_relevantes": {"despacho-0"}},
    {"pregunta": "que datos se necesitan para armar un pedido",
     "ids_relevantes": {"como_comprar-0"}},
    {"pregunta": "como se calcula el total de mi pedido",
     "ids_relevantes": {"como_comprar-0"}},
    {"pregunta": "por que pasos avanza el estado de un pedido",
     "ids_relevantes": {"estado_pedido-0"}},
    {"pregunta": "como consulto el historial de mi pedido",
     "ids_relevantes": {"estado_pedido-0"}},
    {"pregunta": "quien aprueba un reembolso",
     "ids_relevantes": {"reembolsos-0"}},
    {"pregunta": "se puede deshacer un reembolso",
     "ids_relevantes": {"reembolsos-0"}},
    {"pregunta": "que hace el asistente si tengo un reclamo",
     "ids_relevantes": {"reclamos-0"}},
    {"pregunta": "cuando procede un reembolso sobre un pedido",
     "ids_relevantes": {"reclamos-0"}},
    {"pregunta": "aceptan pago con tarjeta de credito",
     "ids_relevantes": set()},
]


def precision_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float:
    """Fraccion de los ids recuperados que son relevantes (0.0 si no hay ninguno)."""
    if not ids_recuperados:
        return 0.0
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_recuperados)


def recall_at_k(ids_recuperados: list[str], ids_relevantes: set[str]) -> float | None:
    """Fraccion de los ids relevantes que se recuperaron (None si el caso no tiene ninguno)."""
    if not ids_relevantes:
        return None
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_relevantes)


def promediar(valores) -> float:
    """Promedio que ignora los None y evita dividir por cero."""
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else 0.0


def evaluar_recuperacion(retriever, casos, k=3):
    """Corre cada caso contra el retriever y promedia precision y recall."""
    resultados = []
    for caso in casos:
        chunks = retriever.invoke(caso["pregunta"])
        ids_recuperados = [c.id for c in chunks][:k]
        p = precision_at_k(ids_recuperados, caso["ids_relevantes"])
        r = recall_at_k(ids_recuperados, caso["ids_relevantes"])
        resultados.append({"pregunta": caso["pregunta"], "precision": p, "recall": r})

    precision_promedio = promediar(x["precision"] for x in resultados)
    recall_promedio = promediar(x["recall"] for x in resultados)
    return resultados, precision_promedio, recall_promedio


def formatear_resultados(resultados, precision_promedio, recall_promedio) -> str:
    """Una linea por pregunta (precision, recall, pregunta) y la linea de promedios."""
    lineas = []
    for r in resultados:
        recall_txt = "n/a" if r["recall"] is None else f"{r['recall']:.2f}"
        lineas.append(f"{r['precision']:.2f}  {recall_txt}  {r['pregunta']}")
    lineas.append(
        f"\npromedio -> precision: {precision_promedio:.3f} recall: {recall_promedio:.3f}"
    )
    return "\n".join(lineas)


def main():
    load_dotenv()
    embeddings = GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)
    vectorstore = Chroma(
        collection_name=NOMBRE_COLECCION,
        persist_directory=DIRECTORIO_VECTORSTORE,
        embedding_function=embeddings,
    )

    # Un indice vacio (persist_directory equivocado) da precision y recall 0 en todo.
    if vectorstore._collection.count() == 0:
        raise SystemExit("El índice está vacío. Ejecuta primero: python src/indexar_corpus.py")

    retriever = vectorstore.as_retriever(search_kwargs={"k": K})
    resultados, precision_promedio, recall_promedio = evaluar_recuperacion(
        retriever, casos_evaluacion, k=K
    )

    reporte = formatear_resultados(resultados, precision_promedio, recall_promedio)
    print(reporte)

    with open(ARCHIVO_RESULTADOS, "w", encoding="utf-8") as archivo:
        archivo.write(f"Fecha: {date.today()}\n")
        archivo.write(f"Configuracion: k={K}, chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}\n\n")
        archivo.write(reporte + "\n")

    print("\nResultados guardados en resultados_evaluacion.txt")


if __name__ == "__main__":
    main()
