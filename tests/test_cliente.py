"""Pruebas del cliente modular sin red ni API key real: python -m pytest tests -v"""
import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cliente  # noqa: E402
from consumir_gemini import enviar_peticion  # noqa: E402

URL = "https://example.test/modelo"
CUERPO = {"pregunta": "test"}


@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    cliente.costo_total_sesion = 0
    yield


@pytest.fixture(autouse=True)
def api_key_falsa():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "x"}):
        yield


def respuesta_con_texto(texto="Santiago es la capital de Chile.", tokens=1000):
    return {
        "candidates": [{"content": {"parts": [{"text": texto}]}}],
        "usageMetadata": {"totalTokenCount": tokens},
    }


# --- enviar peticion: clasificación de errores ----------

@pytest.mark.parametrize("status", [401, 403])
def test_enviar_peticion_credencial_invalida(status):
    with patch("consumir_gemini.requests.post", return_value=Mock(status_code=status)):
        with pytest.raises(ValueError):
            enviar_peticion(URL, CUERPO)


@pytest.mark.parametrize("status", [429, 500, 503])
def test_enviar_peticion_limite_de_uso(status):
    with patch("consumir_gemini.requests.post", return_value=Mock(status_code=status, headers={})):
        with pytest.raises(TimeoutError):
            enviar_peticion(URL, CUERPO)


def test_enviar_peticion_exito():
    falsa = Mock(status_code=200)
    falsa.json.return_value = {"texto": "respuesta simulada"}
    with patch("consumir_gemini.requests.post", return_value=falsa):
        assert enviar_peticion(URL, CUERPO) == {"texto": "respuesta simulada"}


# --- con reintento ------------------------

def test_con_reintento_reintenta_ante_timeout():
    llamadas = {"n": 0}

    def falla_una_vez():
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise TimeoutError("simulado")
        return "ok"

    with patch("cliente.time.sleep") as mock_sleep:
        assert cliente.con_reintento(falla_una_vez) == "ok"
    mock_sleep.assert_called_once()


def test_con_reintento_agota_intentos():
    llamadas = {"n": 0}

    def siempre_falla():
        llamadas["n"] += 1
        raise TimeoutError("simulado")

    with patch("cliente.time.sleep"):
        with pytest.raises(TimeoutError, match="simulado"):
            cliente.con_reintento(siempre_falla, intentos=3)
    assert llamadas["n"] == 3


def test_con_reintento_no_reintenta_value_error():
    llamadas = {"n": 0}

    def credencial_mala():
        llamadas["n"] += 1
        raise ValueError("credencial")

    with patch("cliente.time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            cliente.con_reintento(credencial_mala)
    assert llamadas["n"] == 1
    mock_sleep.assert_not_called()


def test_con_reintento_backoff_respeta_techo():
    def siempre_falla():
        raise TimeoutError("simulado")

    with patch("cliente.time.sleep") as mock_sleep, patch("cliente.random.uniform", return_value=0):
        with pytest.raises(TimeoutError):
            cliente.con_reintento(siempre_falla, intentos=6, espera_base=2, espera_maxima=10)
    esperas = [llamada.args[0] for llamada in mock_sleep.call_args_list]
    assert esperas == [2, 4, 8, 10, 10]


# --- registrar costo ------------

def test_registrar_costo_calcula_costo_correcto():
    costo = cliente.registrar_costo({"usageMetadata": {"totalTokenCount": 1000}})
    assert costo == cliente.COSTO_POR_1000_TOKENS


def test_registrar_costo_acumula():
    cliente.registrar_costo({"usageMetadata": {"totalTokenCount": 1000}})
    cliente.registrar_costo({"usageMetadata": {"totalTokenCount": 500}})
    assert cliente.costo_total_sesion == pytest.approx(cliente.COSTO_POR_1000_TOKENS * 1.5)


def test_registrar_costo_sin_usage_metadata_es_cero():
    assert cliente.registrar_costo({}) == 0


# --- consultar modelo ----------------

def test_consultar_modelo_exito_registra_costo():
    with patch("consumir_gemini.requests.post") as post:
        post.return_value = Mock(status_code=200, headers={})
        post.return_value.json.return_value = respuesta_con_texto()
        assert cliente.consultar_modelo("hola") == "Santiago es la capital de Chile."
    assert cliente.costo_total_sesion == cliente.COSTO_POR_1000_TOKENS


def test_consultar_modelo_convierte_error():
    with patch("cliente.con_reintento", side_effect=TimeoutError("simulado")):
        with pytest.raises(RuntimeError):
            cliente.consultar_modelo("pregunta de prueba")


def test_consultar_modelo_no_registra_costo_si_falla():
    with patch("cliente.time.sleep"), \
            patch("consumir_gemini.requests.post", return_value=Mock(status_code=429, headers={})):
        with pytest.raises(RuntimeError):
            cliente.consultar_modelo("hola")
    assert cliente.costo_total_sesion == 0


def test_consultar_modelo_propaga_value_error():
    with patch("consumir_gemini.requests.post", return_value=Mock(status_code=401)) as post:
        with pytest.raises(ValueError):
            cliente.consultar_modelo("hola")
    assert post.call_count == 1


def test_consultar_modelo_reintenta_y_tiene_exito():
    ok = Mock(status_code=200, headers={})
    ok.json.return_value = respuesta_con_texto()
    limite = Mock(status_code=429, headers={})
    with patch("cliente.time.sleep"), \
            patch("consumir_gemini.requests.post", side_effect=[limite, limite, ok]) as post:
        assert "Santiago" in cliente.consultar_modelo("hola")
    assert post.call_count == 3
