"""Pruebas del registro de latencia y costo (sin red: embeddings y modelo falsos):
python -m pytest tests/test_registro_rag.py -v"""
import json
import os
import sys

from langchain_chroma import Chroma
from langchain_core.embeddings import DeterministicFakeEmbedding

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from registro_rag import (  # noqa: E402
    NOMBRE_COLECCION,
    guardar_registro,
    medir,
    registrar_consulta,
)

CLAVES = {"timestamp", "pregunta", "k", "tiempos_ms", "tiempo_total_ms", "tokens"}


class _Respuesta:
    def __init__(self, usage):
        self.usage_metadata = usage


class _ModeloFalso:
    def __init__(self, usage="auto"):
        self.usage = usage
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        usage = self.usage
        if usage == "auto":  # tokens de entrada proporcionales al prompt
            usage = {"input_tokens": len(prompt) // 4, "output_tokens": 10,
                     "total_tokens": len(prompt) // 4 + 10}
        return _Respuesta(usage)


def _indice(tmp_path, embeddings):
    directorio = str(tmp_path / "vs")
    Chroma.from_texts(
        [f"documento numero {i} sobre cilindros de gas y despacho" for i in range(8)],
        embedding=embeddings,
        collection_name=NOMBRE_COLECCION,
        persist_directory=directorio,
    )
    return directorio


def test_medir_guarda_segundos_en_la_etapa():
    tiempos = {}
    with medir(tiempos, "x"):
        pass
    assert tiempos["x"] >= 0


def test_registro_tiene_la_estructura_pedida(tmp_path):
    emb = DeterministicFakeEmbedding(size=16)
    r = registrar_consulta("pregunta", _indice(tmp_path, emb), k=3,
                           embeddings=emb, chat_model=_ModeloFalso())
    assert set(r) == CLAVES
    assert set(r["tiempos_ms"]) == {"embed", "busqueda", "generacion"}
    assert r["tiempo_total_ms"] >= 0
    assert r["tokens"]["total_tokens"] == r["tokens"]["input_tokens"] + 10


def test_subir_k_sube_los_tokens_de_entrada(tmp_path):
    emb = DeterministicFakeEmbedding(size=16)
    directorio = _indice(tmp_path, emb)
    r3 = registrar_consulta("pregunta", directorio, k=3, embeddings=emb, chat_model=_ModeloFalso())
    r6 = registrar_consulta("pregunta", directorio, k=6, embeddings=emb, chat_model=_ModeloFalso())
    assert r6["tokens"]["input_tokens"] > r3["tokens"]["input_tokens"]


def test_sin_usage_metadata_tokens_es_none(tmp_path):
    emb = DeterministicFakeEmbedding(size=16)
    r = registrar_consulta("pregunta", _indice(tmp_path, emb), embeddings=emb,
                           chat_model=_ModeloFalso(usage=None))
    assert r["tokens"] is None


def test_guardar_registro_escribe_una_linea_json_por_corrida(tmp_path):
    archivo = tmp_path / "registros.jsonl"
    guardar_registro({"a": 1}, archivo)
    guardar_registro({"a": 2}, archivo)
    lineas = archivo.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x) for x in lineas] == [{"a": 1}, {"a": 2}]
