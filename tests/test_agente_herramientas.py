"""
Pruebas del agente con herramientas y memoria (Bloque 22), sin red ni API key.

Ejecutar: python -m pytest tests -v
"""
import os
import sys

import pytest
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agente_con_herramientas import (  # noqa: E402
    calcular_costo_pedido,
    consultar_estado_pedido,
    crear_agente_con_memoria,
)


def test_nombre_explicito_de_la_herramienta():
    assert consultar_estado_pedido.name == "consultar_estado_pedido_con_historial"


def test_estado_actual_sin_historial():
    r = consultar_estado_pedido.invoke({"numero_pedido": "GAS-1001"})
    assert r == "en camino, llega hoy entre las 15:00 y las 18:00"


def test_incluir_historial_cambia_el_resultado():
    r = consultar_estado_pedido.invoke(
        {"numero_pedido": "GAS-1001", "incluir_historial": True}
    )
    assert "historial: recibido, preparado en bodega, en camino" in r


def test_pedido_inexistente_devuelve_texto():
    r = consultar_estado_pedido.invoke({"numero_pedido": "GAS-9999"})
    assert "No se encontró" in r


def test_pydantic_rechaza_booleano_invalido():
    with pytest.raises(ValidationError):
        consultar_estado_pedido.invoke(
            {"numero_pedido": "GAS-1001", "incluir_historial": "tal vez"}
        )


def test_pydantic_rechaza_falta_de_campo_obligatorio():
    with pytest.raises(ValidationError):
        consultar_estado_pedido.invoke({"incluir_historial": True})


def test_costo_pedido_correcto_y_errores_como_texto():
    assert calcular_costo_pedido.invoke({"kilos_cilindro": 15, "cantidad": 3}) == (
        "El costo total es de $81.000."
    )
    assert "No existe" in calcular_costo_pedido.invoke(
        {"kilos_cilindro": 7, "cantidad": 1}
    )
    assert "mayor que cero" in calcular_costo_pedido.invoke(
        {"kilos_cilindro": 5, "cantidad": 0}
    )


def ejecutor_falso():
    """Stand-in del AgentExecutor: responde cuántos mensajes de historial recibió."""
    return RunnableLambda(
        lambda x: {
            "output": f"previos={len(x['chat_history'])}",
            "intermediate_steps": [],
        }
    )


def test_memoria_acumula_entre_turnos_de_la_misma_sesion():
    agente, obtener = crear_agente_con_memoria(ejecutor_falso())
    cfg = {"configurable": {"session_id": "a"}}
    assert agente.invoke({"entrada": "hola"}, cfg)["output"] == "previos=0"
    assert agente.invoke({"entrada": "y ahora"}, cfg)["output"] == "previos=2"
    assert len(obtener("a").messages) == 4


def test_dos_sesiones_no_se_mezclan():
    agente, obtener = crear_agente_con_memoria(ejecutor_falso())
    agente.invoke({"entrada": "GAS-1001"}, {"configurable": {"session_id": "c1"}})
    r = agente.invoke(
        {"entrada": "¿qué dije?"}, {"configurable": {"session_id": "c2"}}
    )
    assert r["output"] == "previos=0"
    assert len(obtener("c1").messages) == 2
    assert len(obtener("c2").messages) == 2


def test_salida_en_bloques_de_gemini_no_rompe_el_segundo_turno():
    bloques = [{"type": "text", "text": "hola", "index": 0, "extras": {"signature": "x"}}]
    ejecutor = RunnableLambda(
        lambda x: {"output": bloques, "intermediate_steps": [], "n": len(x["chat_history"])}
    )
    agente, obtener = crear_agente_con_memoria(ejecutor)
    cfg = {"configurable": {"session_id": "g"}}
    r1 = agente.invoke({"entrada": "uno"}, cfg)
    r2 = agente.invoke({"entrada": "dos"}, cfg)
    assert r1["output"] == "hola"
    assert r2["n"] == 2
    assert len(obtener("g").messages) == 4


def test_sin_session_id_lanza_error():
    agente, _ = crear_agente_con_memoria(ejecutor_falso())
    with pytest.raises(ValueError):
        agente.invoke({"entrada": "hola"})
