"""
Pruebas de manejo de errores del flujo orquestado (Bloque 20), sin red ni API key.
Cubren las filas "cada ruta de destino" y "el flujo completo" del checklist.

Ejecutar: python -m pytest tests -v
"""
import logging
import os
import sys
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from enrutamiento import (  # noqa: E402
    construir_cadena,
    construir_cadena_con_enrutamiento,
    construir_cadena_queja_segura,
    procesar_mensaje_seguro,
)


def fallar_a_proposito(x):
    raise ConnectionError("simulado")


def test_cadena_queja_usa_fallback_ante_fallo_del_modelo():
    cadena_queja_falsa = RunnableLambda(fallar_a_proposito)
    cadena_queja_segura = construir_cadena_queja_segura(cadena_queja_falsa)
    resultado = cadena_queja_segura.invoke({"mensaje": "esto no funciona"})
    assert "equipo" in resultado.lower()


def test_cadena_queja_sin_fallo_no_usa_el_fallback():
    cadena_queja_falsa = RunnableLambda(lambda x: "respuesta real")
    cadena_queja_segura = construir_cadena_queja_segura(cadena_queja_falsa)
    assert cadena_queja_segura.invoke({"mensaje": "hola"}) == "respuesta real"


def test_ruta_con_fallo_entrega_respuesta_dentro_del_flujo_completo():
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=RunnableLambda(lambda x: "reclamo"),
        cadena_reclamo=construir_cadena_queja_segura(RunnableLambda(fallar_a_proposito)),
    )
    resultado = procesar_mensaje_seguro(cadena, "la app se cierra sola")
    assert "equipo" in resultado.lower()


def test_procesar_mensaje_seguro_no_propaga_excepciones():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.side_effect = ConnectionError("simulado")
    cadena_falsa = construir_cadena_con_enrutamiento(paso_clasificacion=clasificacion_falsa)
    resultado = procesar_mensaje_seguro(cadena_falsa, "mensaje de prueba")
    assert "no pudimos procesar" in resultado.lower()


def test_procesar_mensaje_seguro_registra_el_error(caplog):
    cadena_falsa = construir_cadena_con_enrutamiento(
        paso_clasificacion=RunnableLambda(fallar_a_proposito)
    )
    with caplog.at_level(logging.ERROR):
        procesar_mensaje_seguro(cadena_falsa, "hola")
    assert "Error procesando mensaje" in caplog.text
    assert "simulado" in caplog.text


def test_procesar_mensaje_seguro_devuelve_la_respuesta_cuando_todo_sale_bien():
    cadena_falsa = construir_cadena_con_enrutamiento(
        paso_clasificacion=RunnableLambda(lambda x: "otro"),
        cadena_otro=RunnableLambda(lambda x: "hola, ¿en qué te ayudo?"),
    )
    assert procesar_mensaje_seguro(cadena_falsa, "hola") == "hola, ¿en qué te ayudo?"


def test_todas_las_rutas_reales_tienen_fallback_ante_fallo_del_modelo():
    """Con la chain real armada y un modelo que siempre falla, cada categoría responde igual."""
    for categoria in ("pedido", "cotizacion", "reclamo", "otro"):
        modelo = MagicMock()
        # 1ª llamada: clasificación; las siguientes (la ruta) fallan.
        modelo.side_effect = [AIMessage(content=categoria)] + [ConnectionError("simulado")] * 5
        resultado = construir_cadena(modelo).invoke({"mensaje": "hola"})
        assert "equipo" in resultado.lower(), categoria
