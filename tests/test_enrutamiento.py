"""Pruebas del enrutamiento (Bloque 19) sin red ni API key: python -m pytest tests -v"""
import os
import sys
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from enrutamiento import (  # noqa: E402
    construir_cadena_con_enrutamiento,
    construir_paso_clasificacion,
)


def cadena_con_clasificacion(categoria):
    """Cadena cuyas rutas devuelven su propio nombre, para saber cuál se ejecutó."""
    return construir_cadena_con_enrutamiento(
        paso_clasificacion=RunnableLambda(lambda x: categoria),
        cadena_pedido=RunnableLambda(lambda x: "ruta-pedido"),
        cadena_cotizacion=RunnableLambda(lambda x: "ruta-cotizacion"),
        cadena_reclamo=RunnableLambda(lambda x: "ruta-reclamo"),
        cadena_otro=RunnableLambda(lambda x: "ruta-otro"),
    )


def test_clasificacion_normaliza_antes_de_comparar():
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content=" Queja \n")
    resultado = construir_paso_clasificacion(modelo_falso).invoke({"mensaje": "algo salió mal"})
    assert resultado == "queja"


@pytest.mark.parametrize(
    "categoria, ruta",
    [
        ("pedido", "ruta-pedido"),
        ("cotizacion", "ruta-cotizacion"),
        ("reclamo", "ruta-reclamo"),
        ("otro", "ruta-otro"),
    ],
)
def test_enrutamiento_va_a_la_ruta_de_cada_categoria(categoria, ruta):
    assert cadena_con_clasificacion(categoria).invoke({"mensaje": "hola"}) == ruta


def test_enrutamiento_usa_default_ante_categoria_desconocida():
    assert cadena_con_clasificacion("zzz").invoke({"mensaje": "hola"}) == "ruta-otro"


def test_enrutamiento_usa_default_ante_texto_vacio():
    assert cadena_con_clasificacion("").invoke({"mensaje": ""}) == "ruta-otro"
