import json
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

MODELO = "gemini-3.5-flash-lite"
TIMEOUT_SEGUNDOS = 60


def armar_peticion(pregunta_usuario, system_instruction=None, response_schema=None):
    if not pregunta_usuario:
        raise ValueError("La pregunta no puede estar vacía")
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Falta GEMINI_API_KEY: copia .env.example a .env y completa tu llave.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"
    body = {"contents": [{"parts": [{"text": pregunta_usuario}]}]}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if response_schema is not None:
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }
    return url, body


def enviar_peticion(url, body):
    try:
        respuesta = requests.post(
            url,
            json=body,
            headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", "")},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("El servicio tardó demasiado en responder. Intenta de nuevo.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("No se pudo conectar con el servicio. Intenta de nuevo en unos segundos.")
    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError("La respuesta del servicio no llegó en el formato esperado.")


def extraer_texto(datos):
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        detalle = datos.get("error", {}).get("message", "respuesta sin texto")
        raise RuntimeError(f"La respuesta no trae el texto esperado: {detalle}")


def parsear_respuesta_json(texto, claves_esperadas=None):
    texto_limpio = texto.strip()
    texto_limpio = re.sub(r"^```(?:json)?\s*", "", texto_limpio)
    texto_limpio = re.sub(r"\s*```$", "", texto_limpio)
    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError:
        raise ValueError("La respuesta del modelo no es JSON válido.")
    if not isinstance(datos, dict):
        raise ValueError("La respuesta no tiene la estructura esperada.")
    if claves_esperadas and not all(clave in datos for clave in claves_esperadas):
        raise ValueError("La respuesta no tiene la estructura esperada.")
    return datos


def obtener_dato_de_prueba(pregunta):
    url, body = armar_peticion(pregunta)
    datos = enviar_peticion(url, body)
    return extraer_texto(datos)

