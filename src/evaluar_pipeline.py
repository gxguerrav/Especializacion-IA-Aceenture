"""
Actividad Bloque 15: tres respuestas reales de consultar_modelo comparadas contra
una referencia propia, midiendo coincidencia sobre texto crudo y sobre texto procesado.

    python src/evaluar_pipeline.py

Guarda el registro del antes y el después en prompts/registro_pipeline.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cliente import consultar_modelo  # noqa: E402
from pipeline_texto import coincidencia, procesar_texto  # noqa: E402

CASOS = [
    {
        "consulta": "¿Qué es el gas licuado de petróleo (GLP)? Responde en una sola oración.",
        "referencia": "El gas licuado de petróleo es una mezcla de propano y butano que se usa como combustible.",
    },
    {
        "consulta": "¿Qué debo hacer si siento olor a gas en mi casa? Responde en una sola oración.",
        "referencia": "Cierra la llave del cilindro, ventila el lugar y no enciendas fuego ni aparatos eléctricos.",
    },
    {
        "consulta": "¿Cada cuánto debo revisar las mangueras de mi balón de gas? Responde en una sola oración.",
        "referencia": "Debes revisar las mangueras de tu balón de gas periódicamente y cambiarlas si están dañadas o vencidas.",
    },
]

RUTA_REGISTRO = os.path.join(os.path.dirname(__file__), "..", "prompts", "registro_pipeline.json")


def evaluar_caso(caso: dict) -> dict:
    respuesta = consultar_modelo(caso["consulta"])
    pct_crudo = coincidencia(caso["referencia"].split(), respuesta.split())
    pct_proc = coincidencia(procesar_texto(caso["referencia"]), procesar_texto(respuesta))
    return {**caso, "respuesta": respuesta, "coincidencia_cruda": pct_crudo, "coincidencia_procesada": pct_proc}


def main() -> None:
    registro = []
    for numero, caso in enumerate(CASOS, start=1):
        resultado = evaluar_caso(caso)
        registro.append(resultado)
        print(f"[Caso {numero}] Coincidencia texto crudo: {resultado['coincidencia_cruda']:.1%}")
        print(f"[Caso {numero}] Coincidencia texto procesado: {resultado['coincidencia_procesada']:.1%}")
    with open(RUTA_REGISTRO, "w", encoding="utf-8") as archivo:
        json.dump(registro, archivo, ensure_ascii=False, indent=2)
    print(f"Registro guardado en {os.path.normpath(RUTA_REGISTRO)}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"Error de configuración: {error}")
    except RuntimeError as error:
        print(f"El servicio no respondió tras varios intentos: {error}")
