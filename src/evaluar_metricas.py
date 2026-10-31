"""
Bloque 16: aplica calcular_metricas a respuestas reales de consultar_modelo.

    python src/evaluar_metricas.py

"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cliente import consultar_modelo  # noqa: E402
from metricas import calcular_metricas, ordenar_peores_casos, resumir_metricas  # noqa: E402

CASOS = [
    (
        "¿Qué es el gas licuado de petróleo (GLP)? Responde en una sola oración.",
        "El gas licuado de petróleo es una mezcla de propano y butano que se usa como combustible.",
    ),
    (
        "¿Qué debo hacer si siento olor a gas en mi casa? Responde en una sola oración.",
        "Cierra la llave del cilindro, ventila el lugar y no enciendas fuego ni aparatos eléctricos.",
    ),
    (
        "¿Cada cuánto debo revisar las mangueras de mi balón de gas? Responde en una sola oración.",
        "Debes revisar las mangueras de tu balón de gas periódicamente y cambiarlas si están dañadas o vencidas.",
    ),
]

RUTA_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resultados_metricas.json")


def guardar(resultados: list[dict]) -> None:
    with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, indent=2, ensure_ascii=False)


def main() -> None:
    resultados = []
    for consulta, referencia in CASOS:
        respuesta = consultar_modelo(consulta)
        metricas = calcular_metricas(referencia, respuesta)
        resultados.append({"consulta": consulta, "referencia": referencia, "respuesta": respuesta, **metricas})
        guardar(resultados)
        print(f"{consulta}\n  {metricas}")

    resumen = resumir_metricas(resultados)
    print(f"\nF1 promedio: {resumen['f1_promedio']:.2f}")
    print("Peores casos primero:")
    for caso in ordenar_peores_casos(resultados)[:3]:
        print(f"  {caso['f1']:.2f}  {caso['consulta']}")
    print(f"Resultados guardados en {os.path.normpath(RUTA_RESULTADOS)}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"Error de configuración: {error}")
    except RuntimeError as error:
        print(f"El servicio no respondió tras varios intentos: {error}")
