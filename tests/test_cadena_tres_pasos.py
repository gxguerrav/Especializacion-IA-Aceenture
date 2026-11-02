"""Pruebas de la chain de tres pasos sin red ni API key: python -m pytest tests -v"""
import os
import sys
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cadena_tres_pasos import CATALOGO, construir_cadena  # noqa: E402


def modelo_falso_con(*respuestas):
    modelo = MagicMock()
    modelo.side_effect = [AIMessage(content=r) for r in respuestas]
    return modelo


def prompts_recibidos(modelo):
    return [str(llamada.args[0]) for llamada in modelo.call_args_list]


def test_cadena_conecta_los_tres_pasos():
    modelo = modelo_falso_con("reclamo", "borrador de respuesta", "- respuesta final")
    resultado = construir_cadena(modelo).invoke({"mensaje": "me llegó dañado"})
    assert modelo.call_count == 3
    assert resultado == "- respuesta final"


def test_el_paso_dos_recibe_la_clasificacion_y_el_mensaje_original():
    modelo = modelo_falso_con("reclamo", "borrador", "final")
    construir_cadena(modelo).invoke({"mensaje": "válvula dañada"})
    prompt_redaccion = prompts_recibidos(modelo)[1]
    assert "clasificado como: reclamo" in prompt_redaccion
    assert "válvula dañada" in prompt_redaccion
    assert CATALOGO in prompt_redaccion


def test_el_paso_tres_revisa_el_borrador_del_paso_dos():
    modelo = modelo_falso_con("pedido", "BORRADOR-UNICO-123", "final")
    construir_cadena(modelo).invoke({"mensaje": "quiero un cilindro"})
    assert "BORRADOR-UNICO-123" in prompts_recibidos(modelo)[2]


def test_el_paso_uno_no_ve_la_clasificacion_ni_el_borrador():
    modelo = modelo_falso_con("otro", "borrador", "final")
    construir_cadena(modelo).invoke({"mensaje": "hola"})
    primer_prompt = prompts_recibidos(modelo)[0]
    assert "hola" in primer_prompt
    assert "borrador" not in primer_prompt


def test_falta_la_clave_mensaje_lanza_error_antes_de_llamar_al_modelo():
    modelo = modelo_falso_con("x", "y", "z")
    with pytest.raises(KeyError):
        construir_cadena(modelo).invoke({"texto": "clave equivocada"})
    assert modelo.call_count == 0
