"""
Bloques 16 y 17: aplica calcular_metricas a respuestas reales de consultar_modelo
(24 consultas; las lee a mano revision_manual.py).

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
    (
        "¿Qué tamaños de cilindro de gas son los más comunes en los hogares de Chile? Responde en una sola oración.",
        "Los cilindros domésticos más comunes en Chile son de 5, 11, 15 y 45 kilos.",
    ),
    (
        "¿El gas licuado es más pesado o más liviano que el aire? Responde en una sola oración.",
        "El gas licuado es más pesado que el aire, por eso se acumula cerca del suelo.",
    ),
    (
        "¿Se puede guardar un cilindro de gas dentro de un dormitorio? Responde en una sola oración.",
        "No, los cilindros de gas no deben usarse ni guardarse en dormitorios ni en lugares sin ventilación.",
    ),
    (
        "¿Cómo puedo comprobar si hay una fuga en las uniones de mi cilindro? Responde en una sola oración.",
        "Se aplica agua con jabón en las uniones y, si aparecen burbujas, hay una fuga.",
    ),
    (
        "¿Puedo usar un fósforo o un encendedor para buscar una fuga de gas? Responde en una sola oración.",
        "No, nunca se debe usar fuego para buscar una fuga de gas.",
    ),
    (
        "¿Qué sustancia se le agrega al gas para que tenga olor? Responde en una sola oración.",
        "Se le agrega un compuesto llamado mercaptano para que las fugas se puedan detectar por el olor.",
    ),
    (
        "¿A qué temperatura hierve el propano a presión normal? Responde en una sola oración.",
        "El propano hierve a menos 42 grados Celsius a presión normal.",
    ),
    (
        "¿Cuántos kilos de gas contiene un cilindro de 15 kilos? Responde en una sola oración.",
        "Un cilindro de 15 kilos contiene 15 kilos de gas licuado.",
    ),
    (
        "¿Cómo se debe guardar un cilindro de gas? Responde en una sola oración.",
        "Los cilindros deben guardarse de pie, en un lugar ventilado y lejos de fuentes de calor.",
    ),
    (
        "¿Se puede acostar un cilindro de gas para transportarlo? Responde en una sola oración.",
        "No, los cilindros deben mantenerse siempre en posición vertical.",
    ),
    (
        "¿Cuánto tiempo dura un cilindro de 15 kilos en un hogar promedio? Responde en una sola oración.",
        "Un cilindro de 15 kilos dura entre uno y dos meses en un hogar promedio.",
    ),
    (
        "¿Qué es una estufa catalítica? Responde en una sola oración.",
        "Una estufa catalítica es un calefactor a gas que calienta sin llama visible mediante una placa catalítica.",
    ),
    (
        "¿Es seguro dormir con una estufa a gas encendida? Responde en una sola oración.",
        "No, dormir con una estufa a gas encendida es peligroso por el riesgo de intoxicación con monóxido de carbono.",
    ),
    (
        "¿Qué gas tóxico produce la combustión incompleta del gas licuado? Responde en una sola oración.",
        "La combustión incompleta produce monóxido de carbono, un gas tóxico que no tiene olor.",
    ),
    (
        "¿De qué color debe ser la llama de una cocina a gas? Responde en una sola oración.",
        "La llama de una cocina a gas debe ser azul; si es amarilla, la combustión es deficiente.",
    ),
    (
        "¿Cada cuánto tiempo se debe cambiar el regulador de gas? Responde en una sola oración.",
        "El regulador de gas debe cambiarse cada cinco años.",
    ),
    (
        "¿Qué institución fiscaliza el gas en Chile? Responde en una sola oración.",
        "La Superintendencia de Electricidad y Combustibles, SEC, fiscaliza el gas en Chile.",
    ),
    (
        "¿Puedo rellenar yo mismo un cilindro de gas en mi casa? Responde en una sola oración.",
        "No, los cilindros solo deben ser rellenados en plantas autorizadas.",
    ),
    (
        "¿Qué hago si mi cilindro de gas está oxidado o abollado? Responde en una sola oración.",
        "Si el cilindro está oxidado, abollado o con fuga, no debe usarse y se debe devolver al distribuidor.",
    ),
    (
        "¿Cuál es la diferencia entre el gas licuado y el gas natural? Responde en una sola oración.",
        "El gas licuado se vende en cilindros y el gas natural llega a la vivienda por cañería.",
    ),
    (
        "¿Puedo usar mi teléfono celular dentro de la casa si hay una fuga de gas? Responde en una sola oración.",
        "No, durante una fuga no se deben usar interruptores ni aparatos eléctricos; el teléfono se usa solo desde el exterior.",
    ),
]

RUTA_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resultados_metricas.json")


def guardar(resultados: list[dict]) -> None:
    with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, indent=2, ensure_ascii=False)


def cargar_guardados() -> list[dict]:
    """Retoma los resultados ya guardados, para no repetir consultas si una corrida se cortó."""
    try:
        with open(RUTA_RESULTADOS, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main() -> None:
    resultados = [r for r in cargar_guardados() if r["consulta"] in {c for c, _ in CASOS}]
    hechas = {r["consulta"] for r in resultados}
    for consulta, referencia in CASOS:
        if consulta in hechas:
            continue
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
