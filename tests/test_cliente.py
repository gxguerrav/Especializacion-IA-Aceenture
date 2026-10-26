"""Pruebas del cliente modular sin red ni API key real: python -m unittest tests.test_cliente"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cliente  # noqa: E402


def respuesta(status, json=None, headers=None):
    r = MagicMock(status_code=status, headers=headers or {})
    r.json.return_value = json or {}
    return r


OK = respuesta(200, {"candidates": [{"content": {"parts": [{"text": "Santiago es la capital de Chile."}]}}]})


@patch.dict(os.environ, {"GEMINI_API_KEY": "x"})
@patch("cliente.time.sleep")
class TestCliente(unittest.TestCase):
    @patch("consumir_gemini.requests.post", return_value=OK)
    def test_consulta_normal(self, post, _sleep):
        self.assertEqual(cliente.consultar_modelo("¿Capital de Chile?"), "Santiago es la capital de Chile.")

    @patch("consumir_gemini.requests.post", return_value=respuesta(401))
    def test_credencial_invalida_no_reintenta(self, post, _sleep):
        with self.assertRaises(ValueError):
            cliente.consultar_modelo("hola")
        self.assertEqual(post.call_count, 1)

    @patch("consumir_gemini.requests.post", side_effect=[respuesta(429), respuesta(503), OK])
    def test_reintenta_y_tiene_exito(self, post, _sleep):
        self.assertIn("Santiago", cliente.consultar_modelo("hola"))
        self.assertEqual(post.call_count, 3)

    @patch("consumir_gemini.requests.post", return_value=respuesta(429))
    def test_reintentos_agotados(self, post, _sleep):
        with self.assertRaises(RuntimeError):
            cliente.consultar_modelo("hola")
        self.assertEqual(post.call_count, 3)


if __name__ == "__main__":
    unittest.main()
