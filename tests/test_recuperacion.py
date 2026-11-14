"""Pruebas de recuperación y prompt con citas (sin red, embeddings falsos):
python -m pytest tests/test_recuperacion.py -v"""
import os
import sys

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import recuperacion  # noqa: E402
from recuperacion import (  # noqa: E402
    NOMBRE_COLECCION,
    construir_prompt,
    formatear_contexto,
    resolver_citas,
)


def test_formatear_contexto_numera_y_mapea_fuentes():
    chunks = [
        Document(page_content="A", metadata={"fuente": "catalogo_precios"}),
        Document(page_content="B", metadata={"fuente": "despacho"}),
    ]
    contexto, citas = formatear_contexto(chunks)
    assert contexto == "[1] A\n\n[2] B"
    assert citas == {1: "catalogo_precios", 2: "despacho"}


def test_formatear_contexto_sin_metadata_marca_desconocida():
    _, citas = formatear_contexto([Document(page_content="A", metadata={})])
    assert citas == {1: "desconocida"}


def test_resolver_citas_marca_cita_alucinada():
    resultado = resolver_citas("Uno [1] y otro [99].", {1: "catalogo_precios"})
    assert resultado[1] == "catalogo_precios"
    assert resultado[99] == "Cita invalida / no encontrada"


def test_construir_prompt_cumple_condiciones(tmp_path):
    emb = DeterministicFakeEmbedding(size=16)
    textos = [f"texto {i}" for i in range(5)]
    Chroma.from_texts(
        textos,
        embedding=emb,
        metadatas=[{"fuente": f"doc{i}"} for i in range(5)],
        collection_name=NOMBRE_COLECCION,
        persist_directory=str(tmp_path),
    )
    pregunta = "¿Cuanto cuesta el cilindro de 15 kilos?"
    prompt, citas = construir_prompt(pregunta, str(tmp_path), k=3, embeddings=emb)

    assert list(citas) == [1, 2, 3]
    assert all(f.startswith("doc") for f in citas.values())
    assert f"Pregunta: {pregunta}" in prompt
    assert all(f"[{n}] " in prompt for n in (1, 2, 3))
    assert "[4]" not in prompt
    assert "dilo explicitamente" in prompt
    assert recuperacion.PROMPT_TEMPLATE.startswith("Responde la pregunta usando SOLO")
