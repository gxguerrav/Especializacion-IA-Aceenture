"""Pruebas de las métricas (sin red): python -m pytest tests -v"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from metricas import (  # noqa: E402
    calcular_metricas,
    calcular_precision_cobertura_f1,
    contar_coincidencias,
    ordenar_peores_casos,
    resumir_metricas,
)
from pipeline_texto import procesar_texto  # noqa: E402


def test_contar_coincidencias_no_premia_repeticiones_de_mas():
    assert contar_coincidencias(["el", "gato"], ["el", "gato", "el", "gato"]) == 2


def test_contar_coincidencias_toma_el_minimo_por_palabra():
    referencia = procesar_texto("El gato duerme en el sofá.")
    respuesta = procesar_texto("El gato duerme en el sillón todo el día.")
    assert contar_coincidencias(referencia, respuesta) == 5


def test_ejemplo_calculado_a_mano_de_la_leccion():
    referencia = procesar_texto("El gato duerme en el sofá.")
    respuesta = procesar_texto("El gato duerme en el sillón todo el día.")
    m = calcular_precision_cobertura_f1(referencia, respuesta)
    assert m["precision"] == pytest.approx(5 / 9)
    assert m["cobertura"] == pytest.approx(5 / 6)
    assert m["f1"] == pytest.approx(0.67, abs=0.005)


@pytest.mark.parametrize("referencia, respuesta", [([], ["a"]), (["a"], []), ([], [])])
def test_listas_vacias_devuelven_ceros_sin_zerodivision(referencia, respuesta):
    assert calcular_precision_cobertura_f1(referencia, respuesta) == {
        "precision": 0.0,
        "cobertura": 0.0,
        "f1": 0.0,
    }


def test_sin_coincidencias_f1_es_cero():
    m = calcular_precision_cobertura_f1(["a", "b"], ["c", "d"])
    assert m == {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}


def test_textos_identicos_dan_f1_uno():
    assert calcular_metricas("Python es genial.", "python es GENIAL")["f1"] == 1.0


def test_limite_sinonimo_perfecto_da_05():
    m = calcular_metricas("El auto es veloz.", "El vehículo es rápido.")
    assert m == {"precision": 0.5, "cobertura": 0.5, "f1": 0.5}


def test_limite_dato_equivocado_sigue_dando_08():
    m = calcular_metricas("Python fue creado en 1991.", "Python fue creado en 1989.")
    assert m["f1"] == pytest.approx(0.8)


def test_limite_negacion_ausente_casi_no_baja_el_puntaje():
    m = calcular_metricas("Python no es un lenguaje compilado.", "Python es un lenguaje compilado.")
    assert m["precision"] == 1.0
    assert m["cobertura"] == pytest.approx(5 / 6)
    assert m["f1"] == pytest.approx(0.909, abs=0.001)


def test_caso_partido_omite_el_dato_clave_pero_f1_es_alto():
    m = calcular_metricas(
        "El equipo ganó el partido por 3 goles a 1, en su estadio local.",
        "El equipo ganó el partido en su estadio local.",
    )
    assert m["precision"] == 1.0
    assert m["cobertura"] == pytest.approx(0.643, abs=0.001)
    assert m["f1"] == pytest.approx(0.783, abs=0.001)


def test_texto_sin_tokenizar_es_un_error_comun_que_no_falla():
    """Un str cuenta caracteres como tokens: por eso calcular_metricas procesa antes."""
    assert contar_coincidencias("hola", "hola") == 4  # caracteres, no palabras
    assert calcular_metricas("hola", "hola")["f1"] == 1.0


def test_resumir_metricas_promedia():
    resultados = [
        {"precision": 0.83, "cobertura": 0.71, "f1": 0.77},
        {"precision": 0.40, "cobertura": 0.50, "f1": 0.44},
        {"precision": 0.62, "cobertura": 0.62, "f1": 0.62},
    ]
    resumen = resumir_metricas(resultados)
    assert resumen["f1_promedio"] == pytest.approx(0.61, abs=0.005)
    assert resumen["precision_promedio"] == pytest.approx(0.617, abs=0.001)


def test_resumir_metricas_lista_vacia():
    assert resumir_metricas([]) == {
        "precision_promedio": 0,
        "cobertura_promedio": 0,
        "f1_promedio": 0,
    }


def test_ordenar_peores_casos_pone_el_f1_menor_primero():
    resultados = [{"consulta": "a", "f1": 0.9}, {"consulta": "b", "f1": 0.1}, {"consulta": "c", "f1": 0.5}]
    orden = [r["consulta"] for r in ordenar_peores_casos(resultados)]
    assert orden == ["b", "c", "a"]
