"""Servicio RAG integrado del Gate 2: indexar, recuperar, filtrar, citar, generar y registrar.

Reúne en un solo flujo las piezas construidas en el Módulo 2, sin reescribirlas:
  - Indexación persistida con actualización incremental (Bloque 25): `sincronizar_indice`.
    Solo agrega/actualiza/borra los chunks que cambiaron; nunca reconstruye todo.
  - Recuperación con citación (Bloque 26): el contexto va numerado [N] y la respuesta final
    lista sus fuentes. Si el modelo no cita nada válido, el servicio no entrega la respuesta.
  - Latencia y consumo por etapa (Bloque 28): embed, búsqueda y generación por separado.
  - Logging estructurado con trace_id y filtro de inyección (Bloque 31): se reutiliza
    `src/logging_rag.py`. Los logs llevan longitudes, conteos y huellas, nunca contenido.
  - Versionado de prompts y supervisión humana (Bloque 32): `ejecutar_supervision` corre el
    grafo `interrupt()`/`Command` de `src/grafo_supervision.py` sobre la versión del prompt.

Dos modos:
  - simulado (por defecto): embeddings léxicos locales y un modelo simulado. No necesita
    clave ni red; su índice vive en `vectorstore_sim/`. Toda salida lo marca como simulado.
  - real (`--real`): embeddings y modelo de Gemini sobre el índice `vectorstore/` de
    `indexar_corpus.py`. Requiere GEMINI_API_KEY en el `.env`.

Uso (con el entorno virtual activo):
    python src/servicio_rag.py
    python src/servicio_rag.py "cuanto cuesta el cilindro de 15 kilos" --decision aprobar
    python src/servicio_rag.py "el despacho tiene costo" --real
"""

import argparse
import hashlib
import json
import math
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_chroma import Chroma  # noqa: E402
from langchain_core.embeddings import Embeddings  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from cliente import COSTO_POR_1000_TOKENS  # noqa: E402
from grafo_supervision import app_despliegue, nuevo_thread_id, resolver  # noqa: E402
from indexar_corpus import CHUNK_OVERLAP, CHUNK_SIZE, CORPUS  # noqa: E402
from logging_rag import (  # noqa: E402
    construir_mensajes,
    filtrar_documentos_sospechosos,
    huella,
    logger,
    registrar_consumo,
    trace_id_var,
)
from recuperacion import NOMBRE_COLECCION, resolver_citas  # noqa: E402
from registro_prompts import NOMBRE_PROMPT, registro  # noqa: E402
from registro_rag import medir  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_REAL = str(RAIZ / "vectorstore")
DIRECTORIO_SIMULADO = str(RAIZ / "vectorstore_sim")
COLECCION_SIMULADA = "corpus_simulado"

SIN_CONTEXTO = "No tengo informacion suficiente y verificada para responder esto."
SIN_CITA = "No pude respaldar la respuesta con una fuente verificable, asi que no la entrego."


# --- Componentes simulados (modo sin red) ----------------------------------------------

class EmbeddingsLexicos(Embeddings):
    """Embeddings locales y deterministas: bolsa de palabras hasheada a 256 dimensiones.

    A diferencia de DeterministicFakeEmbedding (vectores aleatorios), documentos y
    preguntas que comparten palabras quedan cerca, así la recuperación simulada es
    razonable. No reemplaza a un modelo de embeddings real.
    """

    DIMENSION = 256
    PALABRAS_VACIAS = {"de", "el", "la", "los", "las", "a", "en", "un", "una", "y", "o", "que",
                       "mi", "es", "para", "con", "por", "se", "del", "al", "cual", "como"}

    @classmethod
    def _palabras(cls, texto):
        """Minúsculas, sin palabras vacías, 'kilos' -> 'kg', sinónimos de precio y sin 's' final."""
        palabras = []
        for palabra in re.findall(r"\w+", texto.lower()):
            if palabra in cls.PALABRAS_VACIAS:
                continue
            if palabra in ("kilo", "kilos"):
                palabra = "kg"
            elif palabra in ("cuesta", "cuanto", "costo", "valor"):
                palabra = "precio"  # sinonimos minimos del dominio, solo para el modo simulado
            elif len(palabra) > 3 and palabra.endswith("s"):
                palabra = palabra[:-1]
            palabras.append(palabra)
        return palabras

    def _vector(self, texto):
        vector = [0.0] * self.DIMENSION
        for palabra in self._palabras(texto):
            indice = int(hashlib.md5(palabra.encode("utf-8")).hexdigest(), 16) % self.DIMENSION
            vector[indice] += 1.0
        norma = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norma for v in vector]

    def embed_documents(self, textos):
        return [self._vector(t) for t in textos]

    def embed_query(self, texto):
        return self._vector(texto)


class ModeloSimulado:
    """Responde con la línea del contexto que más palabras comparte con la pregunta y la cita
    con su número. Es una SIMULACION: sirve para ensayar el pipeline sin gastar cuota, no
    para evaluar la calidad de una respuesta."""

    def invoke(self, mensajes):
        pedido = mensajes[-1].content
        lineas = re.findall(r"^\[(\d+)\] (.+)$", pedido, flags=re.MULTILINE)
        pregunta = re.search(r"^Pregunta: (.+)$", pedido, flags=re.MULTILINE)
        palabras = set(EmbeddingsLexicos._palabras(pregunta.group(1) if pregunta else ""))
        if lineas:
            numero, linea = max(
                lineas, key=lambda nl: len(palabras & set(EmbeddingsLexicos._palabras(nl[1]))))
            texto = f"Segun el contexto recuperado: {linea} [{numero}]"
        else:
            texto = "El contexto recuperado no contiene la informacion pedida."
        entrada = sum(len(m.content) for m in mensajes) // 4
        salida = len(texto) // 4
        return AIMessage(content=texto, usage_metadata={
            "input_tokens": entrada, "output_tokens": salida, "total_tokens": entrada + salida})


# --- Indexación persistida e incremental (Bloque 25) -----------------------------------

def construir_chunks():
    """Corpus -> chunks con id predecible `<fuente>-<n>` y huella del contenido en metadata
    (la huella permite detectar qué chunks cambiaron sin recalcular nada)."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.create_documents(
        [doc["texto"] for doc in CORPUS],
        metadatas=[{"fuente": doc["fuente"]} for doc in CORPUS],
    )
    ids, contador = [], {}
    for chunk in chunks:
        fuente = chunk.metadata["fuente"]
        ids.append(f"{fuente}-{contador.get(fuente, 0)}")
        contador[fuente] = contador.get(fuente, 0) + 1
        chunk.metadata["huella"] = huella(chunk.page_content)
    return chunks, ids


def sincronizar_indice(vectorstore, chunks, ids):
    """Deja el índice igual al corpus tocando solo lo necesario. Devuelve un dict con los
    conteos {agregados, actualizados, eliminados, sin_cambios} y el estado resumido."""
    existentes = vectorstore.get(include=["metadatas"])
    huellas_actuales = {i: (m or {}).get("huella") for i, m in zip(existentes["ids"], existentes["metadatas"])}

    nuevos_ids = set(ids)
    obsoletos = [i for i in huellas_actuales if i not in nuevos_ids]
    por_escribir = [
        (chunk, i) for chunk, i in zip(chunks, ids)
        if huellas_actuales.get(i) != chunk.metadata["huella"]
    ]
    actualizados = [i for _, i in por_escribir if i in huellas_actuales]

    if obsoletos or actualizados:
        vectorstore.delete(ids=obsoletos + actualizados)
    if por_escribir:
        vectorstore.add_documents([c for c, _ in por_escribir], ids=[i for _, i in por_escribir])

    cuentas = {
        "agregados": len(por_escribir) - len(actualizados),
        "actualizados": len(actualizados),
        "eliminados": len(obsoletos),
        "sin_cambios": len(ids) - len(por_escribir),
    }
    if not huellas_actuales:
        estado = "indice_creado"
    elif por_escribir or obsoletos:
        estado = "indice_actualizado"
    else:
        estado = "indice_reutilizado"
    return {"estado": estado, **cuentas}


def abrir_indice(modo="simulado"):
    """Abre (y sincroniza) el vector store persistido. Devuelve (vectorstore, embeddings, resumen)."""
    if modo == "real":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from recuperacion import MODELO_EMBEDDINGS

        embeddings = GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)
        directorio, coleccion = DIRECTORIO_REAL, NOMBRE_COLECCION
    else:
        embeddings = EmbeddingsLexicos()
        directorio, coleccion = DIRECTORIO_SIMULADO, COLECCION_SIMULADA

    vectorstore = Chroma(collection_name=coleccion, persist_directory=directorio,
                         embedding_function=embeddings)
    chunks, ids = construir_chunks()
    return vectorstore, embeddings, sincronizar_indice(vectorstore, chunks, ids)


# --- Pipeline ---------------------------------------------------------------------------

def extraer_texto(contenido):
    """Texto plano de `AIMessage.content`. Gemini puede devolver una lista de bloques
    ({'type': 'text', 'text': ...}) en vez de un str; str(lista) mostraría la firma interna."""
    if isinstance(contenido, str):
        return contenido
    partes = []
    for bloque in contenido or []:
        if isinstance(bloque, str):
            partes.append(bloque)
        elif isinstance(bloque, dict) and bloque.get("type") == "text":
            partes.append(bloque.get("text", ""))
    return "".join(partes)


def _evento(auditoria, nombre, **campos):
    """Escribe el log JSON (con trace_id) y guarda el mismo evento en la traza de auditoría.
    Solo recibe longitudes, conteos y huellas: nunca texto de la pregunta ni de documentos."""
    logger.info(nombre, extra={"extra_data": {"evento": nombre, **campos}})
    auditoria.append({"evento": nombre, "trace_id": trace_id_var.get(), **campos})


def responder(pregunta, vectorstore, embeddings, chat_model, resumen_indice=None, k=3,
              simulado=True):
    """Corre una consulta completa y devuelve un dict con respuesta, fuentes, trace_id,
    métricas (tiempos, tokens, costo) y la traza de auditoría.

    No lanza excepciones por falta de contexto o de cita: responde con un mensaje explícito
    y deja el motivo en los logs (`sin_contexto_confiable`, `respuesta_sin_cita`).
    """
    token = trace_id_var.set("trace-" + uuid.uuid4().hex[:8])
    auditoria = []
    try:
        trace_id = trace_id_var.get()
        _evento(auditoria, "consulta_recibida", pregunta_len=len(pregunta),
                pregunta_huella=huella(pregunta), modo="simulado" if simulado else "real")
        if resumen_indice:
            _evento(auditoria, resumen_indice["estado"], **{
                c: v for c, v in resumen_indice.items() if c != "estado"})

        tiempos = {}
        with medir(tiempos, "embed"):
            vector = embeddings.embed_query(pregunta)
        with medir(tiempos, "busqueda"):
            documentos = vectorstore.similarity_search_by_vector(vector, k=k)
        _evento(auditoria, "documentos_recuperados", n_recuperados=len(documentos),
                huellas=[huella(d.page_content) for d in documentos])

        limpios, descartados = filtrar_documentos_sospechosos(documentos)
        _evento(auditoria, "contexto_filtrado", n_limpios=len(limpios),
                n_descartados=len(descartados))

        def salida(texto, fuentes, extra=None):
            return {"trace_id": trace_id, "respuesta": texto, "fuentes": fuentes,
                    "simulado": simulado, "auditoria": auditoria, **(extra or {})}

        if not limpios:
            _evento(auditoria, "sin_contexto_confiable", n_recuperados=len(documentos),
                    n_descartados=len(descartados))
            return salida(SIN_CONTEXTO, [])

        mensajes, citas = construir_mensajes(pregunta, limpios)
        with medir(tiempos, "generacion"):
            mensaje = chat_model.invoke(mensajes)
        registrar_consumo(mensaje)
        texto = extraer_texto(mensaje.content)

        usados = {n: f for n, f in resolver_citas(texto, citas).items() if n in citas}
        uso = getattr(mensaje, "usage_metadata", None) or {}
        total_tokens = uso.get("total_tokens") or 0
        metricas = {
            "tiempos_ms": {e: round(s * 1000, 2) for e, s in tiempos.items()},
            "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
            "tokens": {c: uso.get(c) for c in ("input_tokens", "output_tokens", "total_tokens")},
            "costo_estimado_usd": round(total_tokens / 1000 * COSTO_POR_1000_TOKENS, 6),
        }
        _evento(auditoria, "latencia_y_costo", respuesta_len=len(texto), **metricas)

        if not usados:
            _evento(auditoria, "respuesta_sin_cita", respuesta_len=len(texto))
            return salida(SIN_CITA, [], {"metricas": metricas})

        fuentes = sorted(set(usados.values()))
        lista = ", ".join(f"[{n}] {f}" for n, f in sorted(usados.items()))
        return salida(f"{texto}\n\nFuentes: {lista}", fuentes, {"metricas": metricas})
    finally:
        trace_id_var.reset(token)


def crear_servicio(modo="simulado", k=3):
    """Arma el servicio y devuelve una función `consultar(pregunta) -> dict`.

    Indexa (o reutiliza) el índice persistido una sola vez al crearlo. El modelo real se
    importa solo en modo real, así el modo simulado no necesita la clave de API.
    """
    simulado = modo != "real"
    vectorstore, embeddings, resumen = abrir_indice(modo)
    if simulado:
        chat_model = ModeloSimulado()
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from registro_rag import MODELO_CHAT

        chat_model = ChatGoogleGenerativeAI(model=MODELO_CHAT)

    pendiente = {"resumen": resumen}  # el estado del índice se reporta solo en la 1a consulta

    def consultar(pregunta):
        resumen_indice, pendiente["resumen"] = pendiente["resumen"], None
        return responder(pregunta, vectorstore, embeddings, chat_model,
                         resumen_indice=resumen_indice, k=k, simulado=simulado)

    return consultar


def ejecutar_supervision(decidir, huella_nueva=None):
    """Punto de supervisión humana (Bloque 32) sobre la acción de mayor riesgo: activar una
    versión nueva del prompt en producción.

    El grafo se pausa con `interrupt()`; `decidir(pendiente)` devuelve True/False (una
    persona, o un valor fijo en pruebas) y solo entonces se reanuda con `Command`.
    """
    huella_nueva = huella_nueva or registro.ultima(NOMBRE_PROMPT)["huella"]
    config = {"configurable": {"thread_id": nuevo_thread_id()}}
    pausado = app_despliegue.invoke({"huella_nueva": huella_nueva, "aprobado": False}, config=config)
    if "__interrupt__" not in pausado:
        raise RuntimeError("el grafo de supervision no se pauso")
    pendiente = app_despliegue.get_state(config).interrupts[0].value
    aprobado = bool(decidir(pendiente))
    final = resolver(app_despliegue, config, aprobado)
    return {"pendiente": pendiente, "aprobado": aprobado, "estado_final": final}


def main():
    parser = argparse.ArgumentParser(description="Servicio RAG del Gate 2 (indexar, recuperar, responder).")
    parser.add_argument("pregunta", nargs="?", default="cuanto cuesta el cilindro de 15 kilos")
    parser.add_argument("--real", action="store_true", help="usa Gemini real (requiere GEMINI_API_KEY)")
    parser.add_argument("--k", type=int, default=3, help="chunks a recuperar (default 3)")
    parser.add_argument("--decision", choices=["aprobar", "rechazar", "preguntar"], default="preguntar",
                        help="decision para la version de prompt (default: preguntar por consola)")
    args = parser.parse_args()

    if args.real:
        from dotenv import load_dotenv
        import os

        load_dotenv()
        if not os.environ.get("GEMINI_API_KEY"):
            sys.exit('Falta GEMINI_API_KEY. Defínela en tu archivo ".env" o ejecuta sin --real.')

    try:
        consultar = crear_servicio("real" if args.real else "simulado", k=args.k)
        resultado = consultar(args.pregunta)
    except Exception as error:  # el servicio no debe terminar con un Traceback
        mensaje = str(error)
        if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
            sys.exit("Limite de peticiones alcanzado. Espera un minuto y vuelve a ejecutar.")
        sys.exit(f"No se pudo completar la consulta: {type(error).__name__}: {mensaje}")

    print("--- respuesta completa del servicio ---")
    if resultado["simulado"]:
        print("(modo SIMULADO: embeddings locales y modelo simulado, sin llamar a la API)")
    resumen = {c: v for c, v in resultado.items() if c != "auditoria"}
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    assert resultado["fuentes"], "la respuesta debe citar al menos una fuente"

    print("--- punto de supervision humana ---")
    if args.decision == "preguntar":
        from supervision import esperar_aprobacion

        def decidir(pendiente):
            return esperar_aprobacion(
                f"Aprobar {pendiente['motivo']} (huella {pendiente['huella_propuesta']})? [s/n]")
    else:
        def decidir(pendiente):
            print("pausado, pendiente:", pendiente)
            return args.decision == "aprobar"

    supervision = ejecutar_supervision(decidir)
    print("decision:", "aprobada" if supervision["aprobado"] else "rechazada")
    print("estado final:", supervision["estado_final"])
    print("Proceso terminado sin errores.")


if __name__ == "__main__":
    main()
