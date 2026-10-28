"""Pruebas del pipeline de texto (sin red): python -m pytest tests -v"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline_texto import (  # noqa: E402
    coincidencia,
    limpiar_texto,
    procesar_texto,
    tokenizar,
    vectorizar,
)


def test_procesar_texto_normaliza_mayusculas_y_puntuacion():
    resultado = procesar_texto("El Cielo, es AZUL!")
    assert resultado == ["el", "cielo", "es", "azul"]


def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia():
    resultado = procesar_texto("¡¡¡...!!!")
    assert resultado == []


def test_limpiar_texto_conserva_tildes_enie_y_numeros():
    assert limpiar_texto("¡Año 2026: canción!") == "año 2026 canción"


def test_limpiar_texto_colapsa_espacios():
    assert limpiar_texto("  hola    mundo \n") == "hola mundo"


@pytest.mark.parametrize("valor", [None, 42, {"texto": "hola"}])
def test_limpiar_texto_rechaza_no_str(valor):
    with pytest.raises(TypeError):
        limpiar_texto(valor)


def test_tokenizar_separa_por_espacios():
    assert tokenizar("el gato corre") == ["el", "gato", "corre"]


def test_vectorizar_cuenta_repeticiones():
    assert vectorizar(["el", "gato", "el"]) == {"el": 2, "gato": 1}


def test_coincidencia_cruda_vs_procesada():
    referencia, respuesta = "El cielo es azul.", "el cielo es azul"
    cruda = coincidencia(referencia.split(), respuesta.split())
    procesada = coincidencia(procesar_texto(referencia), procesar_texto(respuesta))
    assert cruda == 0.5
    assert procesada == 1.0


def test_coincidencia_referencia_vacia_no_divide_por_cero():
    assert coincidencia([], ["hola"]) == 0.0
