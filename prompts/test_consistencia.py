import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from consumir_gemini import (
    armar_peticion,
    enviar_peticion,
    extraer_texto,
    parsear_respuesta_json,
)
from banco import BANCO_DE_PROMPTS

INTENTOS = 3
PAUSA_SEGUNDOS = 13
ESPERA_REINTENTO = 45
REINTENTOS_API = 3


def llamar_api(prompt):
    # 429 (cuota) y 503 (alta demanda) son fallos de la API, no del prompt:
    # se espera y se repite para medir solo la consistencia del JSON.
    for _ in range(REINTENTOS_API):
        url, body = armar_peticion(
            prompt["ejemplo_usuario"],
            prompt["system_instruction"],
            prompt.get("response_schema"),
        )
        respuesta = enviar_peticion(url, body)
        if respuesta.get("error", {}).get("code") not in (429, 503):
            return respuesta
        print("  API ocupada o sin cuota, reintentando...")
        time.sleep(ESPERA_REINTENTO)
    return respuesta


registro = {}

for prompt in BANCO_DE_PROMPTS:
    exitos = 0
    for intento in range(INTENTOS):
        try:
            respuesta = llamar_api(prompt)
            texto = extraer_texto(respuesta)
            datos = parsear_respuesta_json(texto, prompt["claves_esperadas"])
            exitos += 1
        except (ValueError, RuntimeError) as error:
            print(f"  intento {intento + 1} falló: {error}")
        time.sleep(PAUSA_SEGUNDOS)
    print(f"{prompt['nombre']}: {exitos}/{INTENTOS} respuestas válidas")
    registro[prompt["nombre"]] = {"exitos": exitos, "intentos": INTENTOS}

ruta = os.path.join(os.path.dirname(__file__), "registro_resultados.json")
with open(ruta, "w", encoding="utf-8") as archivo:
    json.dump(registro, archivo, indent=2, ensure_ascii=False)