"""
Pruebas de supervisión humana y trazas (Bloque 23), sin red ni API key.

Ejecutar: python -m pytest tests -v
"""
import inspect
import json
import os
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import agente_con_herramientas as agente  # noqa: E402
import supervision  # noqa: E402
from trazas import marcar_repeticiones_sospechosas, registrar_traza  # noqa: E402


@pytest.fixture(autouse=True)
def registro_limpio():
    supervision.registro_aprobaciones.clear()
    yield
    supervision.registro_aprobaciones.clear()


def reembolso(**kwargs):
    return agente.generar_reembolso.invoke(
        {"numero_pedido": "GAS-1002", "monto": 15000.0, **kwargs}
    )


# --- esperar_aprobacion ---------------------------------------------------

def test_aprobacion_solo_con_s():
    assert supervision.esperar_aprobacion("?", leer_respuesta=lambda: " S ") is True
    assert supervision.esperar_aprobacion("?", leer_respuesta=lambda: "n") is False
    assert supervision.esperar_aprobacion("?", leer_respuesta=lambda: "si") is False


def test_timeout_devuelve_false_sin_esperar_de_mas():
    def nunca_responde():
        time.sleep(5)
        return "s"

    inicio = time.monotonic()
    assert supervision.esperar_aprobacion(
        "?", tiempo_limite_segundos=0.2, leer_respuesta=nunca_responde
    ) is False
    assert time.monotonic() - inicio < 2


def test_sin_entrada_estandar_se_rechaza():
    def sin_stdin():
        raise EOFError

    assert supervision.esperar_aprobacion("?", leer_respuesta=sin_stdin) is False


# --- generar_reembolso ----------------------------------------------------

def test_reembolso_aprobado_se_ejecuta_y_se_registra(monkeypatch):
    monkeypatch.setattr(agente, "esperar_aprobacion", lambda m: True)
    assert reembolso() == "Reembolso de $15.000 generado para el pedido GAS-1002."
    registro = supervision.registro_aprobaciones
    assert len(registro) == 1
    assert registro[0]["aprobado"] is True
    assert registro[0]["argumentos"] == {"numero_pedido": "GAS-1002", "monto": 15000.0}


def test_reembolso_rechazado_no_se_ejecuta_pero_se_registra(monkeypatch):
    monkeypatch.setattr(agente, "esperar_aprobacion", lambda m: False)
    assert "no aprobado" in reembolso()
    assert supervision.registro_aprobaciones[0]["aprobado"] is False


def test_reembolso_invalido_no_llega_al_supervisor(monkeypatch):
    def no_debe_llamarse(m):
        raise AssertionError("no se debía pedir aprobación")

    monkeypatch.setattr(agente, "esperar_aprobacion", no_debe_llamarse)
    assert "No se encontró" in reembolso(numero_pedido="GAS-9999")
    assert "mayor que cero" in reembolso(monto=-5.0)
    assert supervision.registro_aprobaciones == []


def test_toda_herramienta_de_riesgo_alto_llama_a_esperar_aprobacion():
    """El documento de límites dice que estas herramientas piden aprobación: verificarlo."""
    for herramienta in (agente.generar_reembolso,):
        assert "esperar_aprobacion(" in inspect.getsource(herramienta.func)


# --- trazas ---------------------------------------------------------------

def accion(herramienta, **argumentos):
    return SimpleNamespace(tool=herramienta, tool_input=argumentos), "ok"


def test_registrar_traza_guarda_una_linea_json(tmp_path):
    archivo = tmp_path / "trazas.jsonl"
    resultado = {
        "intermediate_steps": [accion("calcular_costo_pedido", kilos_cilindro=15, cantidad=3)],
        "output": "Son $81.000.",
    }
    registrar_traza("c1", "¿cuánto cuestan 3 de 15?", resultado, archivo=str(archivo))
    lineas = archivo.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 1
    registro = json.loads(lineas[0])
    assert registro["session_id"] == "c1"
    assert registro["acciones"][0]["herramienta"] == "calcular_costo_pedido"
    assert registro["acciones"][0]["argumentos"] == {"kilos_cilindro": 15, "cantidad": 3}
    assert registro["respuesta_final"] == "Son $81.000."


def test_registrar_traza_sin_intermediate_steps_no_falla(tmp_path):
    archivo = tmp_path / "trazas.jsonl"
    registrar_traza("c1", "hola", {"output": "Hola"}, archivo=str(archivo))
    assert json.loads(archivo.read_text(encoding="utf-8"))["acciones"] == []


def test_marcar_repeticiones_solo_consecutivas(tmp_path):
    archivo = str(tmp_path / "trazas.jsonl")
    registrar_traza("una_vez", "a", {"intermediate_steps": [accion("calcular_costo_pedido")], "output": ""}, archivo)
    registrar_traza("seguidas", "b", {"intermediate_steps": [accion("consultar_estado_pedido_con_historial"), accion("consultar_estado_pedido_con_historial")], "output": ""}, archivo)
    registrar_traza("no_seguidas", "c", {"intermediate_steps": [accion("calcular_costo_pedido"), accion("consultar_estado_pedido_con_historial"), accion("calcular_costo_pedido")], "output": ""}, archivo)
    assert marcar_repeticiones_sospechosas(archivo) == [
        ("seguidas", "consultar_estado_pedido_con_historial")
    ]


def test_marcar_repeticiones_archivo_inexistente(tmp_path, capsys):
    assert marcar_repeticiones_sospechosas(str(tmp_path / "no_existe.jsonl")) == []
    assert "No se encontró" in capsys.readouterr().out


def test_marcar_repeticiones_omite_linea_corrupta(tmp_path):
    archivo = tmp_path / "trazas.jsonl"
    archivo.write_text('{"session_id": "x", "acc\n', encoding="utf-8")
    assert marcar_repeticiones_sospechosas(str(archivo)) == []
