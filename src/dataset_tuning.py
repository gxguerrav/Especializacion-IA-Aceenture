"""Dataset de tuning (PEFT) para el asistente de ventas de gas (Bloque 29).

Tarea: convertir el mensaje libre de un cliente en un JSON de formato fijo con dos
campos, "intencion" y "prioridad". No es un problema de información faltante (el modelo
ya entiende un mensaje de cliente), sino de comportamiento consistente en el formato de
salida: el caso de PEFT, no de RAG. Las intenciones son las mismas del banco de prompts
del proyecto (comprar, cotizar, consultar_pedido, reclamo, otro).

Uso (con el entorno virtual activo):
    python dataset_tuning.py            # balance + validación, sin llamar a la API
    python dataset_tuning.py --enviar   # además envía el trabajo de tuning (puede costar)
"""

import json
import sys
import time
from collections import Counter

from dotenv import load_dotenv
from google import genai
from google.genai import types

CLAVES_ESPERADAS = ("intencion", "prioridad")

# Paso 1: al menos 10 ejemplos propios, variados y con más de una categoría.
ejemplos_raw = [
    ("Quiero 2 cilindros de 15 kilos, mi direccion es Av. Los Leones 1234, Providencia.",
     {"intencion": "comprar", "prioridad": "media"}),
    ("Necesito un cilindro de 45 kilos urgente, me quede sin gas y tengo un restaurante abierto.",
     {"intencion": "comprar", "prioridad": "alta"}),
    ("Quiero pedir un cilindro de 5 kilos para la semana que viene, sin apuro.",
     {"intencion": "comprar", "prioridad": "baja"}),
    ("Cuanto cuesta el cilindro de 15 kilos con despacho a Nunoa?",
     {"intencion": "cotizar", "prioridad": "baja"}),
    ("Me pueden cotizar 10 cilindros de 45 kilos para mi empresa, necesito el valor hoy.",
     {"intencion": "cotizar", "prioridad": "media"}),
    ("Hay descuento si compro 3 cilindros de 11 kilos al mes?",
     {"intencion": "cotizar", "prioridad": "baja"}),
    ("En que estado esta mi pedido 4821? Dijeron que llegaba esta tarde.",
     {"intencion": "consultar_pedido", "prioridad": "media"}),
    ("Mi pedido 3307 no llega y llevo tres horas sin gas con un bebe en casa.",
     {"intencion": "consultar_pedido", "prioridad": "alta"}),
    ("Solo queria saber a que hora pasa el camion por mi sector manana.",
     {"intencion": "consultar_pedido", "prioridad": "baja"}),
    ("Me cobraron dos veces el cilindro y necesito que me devuelvan uno de los cargos.",
     {"intencion": "reclamo", "prioridad": "alta"}),
    ("El repartidor dejo el cilindro de 15 kilos con la valvula danada, huele a gas.",
     {"intencion": "reclamo", "prioridad": "alta"}),
    ("El cilindro llego con el sello roto, quisiera que me lo cambien cuando puedan.",
     {"intencion": "reclamo", "prioridad": "media"}),
    ("Buenas tardes, trabajan los fines de semana?",
     {"intencion": "otro", "prioridad": "baja"}),
    ("Gracias por la atencion de ayer, todo llego perfecto.",
     {"intencion": "otro", "prioridad": "baja"}),
    ("Quisiera saber si ofrecen revision de instalaciones de gas a domicilio.",
     {"intencion": "otro", "prioridad": "media"}),
]

examples = [
    types.TuningExample(text_input=texto, output=json.dumps(salida, ensure_ascii=False))
    for texto, salida in ejemplos_raw
]


# Paso 2: balance entre categorías.
def chequear_balance(ejemplos_raw: list[tuple[str, dict]], clave: str) -> Counter:
    return Counter(salida[clave] for _, salida in ejemplos_raw)


# Paso 3: validación local, gratis, antes de enviar nada.
def validar_dataset(
    examples: list[types.TuningExample], claves_esperadas: tuple[str, ...]
) -> list[str]:
    problemas = []
    vistos = set()
    for i, ej in enumerate(examples):
        if not ej.text_input or not ej.text_input.strip():
            problemas.append(f"ejemplo {i}: text_input vacio")
        if not ej.output or not ej.output.strip():
            problemas.append(f"ejemplo {i}: output vacio")
            continue
        if ej.text_input in vistos:
            problemas.append(f"ejemplo {i}: text_input duplicado")
        vistos.add(ej.text_input)
        try:
            salida = json.loads(ej.output)
        except json.JSONDecodeError:
            problemas.append(f"ejemplo {i}: output no es JSON valido")
            continue
        for clave in claves_esperadas:
            if clave not in salida:
                problemas.append(f'ejemplo {i}: output no tiene la clave "{clave}"')
    return problemas


# Paso 4: el tuning es asíncrono; hay que consultar el estado aparte.
def esperar_a_que_termine(
    client: genai.Client, nombre_trabajo: str, intervalo_segundos: int = 30
) -> types.TuningJob:
    estados_finales = {
        types.JobState.JOB_STATE_SUCCEEDED,
        types.JobState.JOB_STATE_FAILED,
        types.JobState.JOB_STATE_CANCELLED,
        types.JobState.JOB_STATE_PARTIALLY_SUCCEEDED,
    }
    while True:
        trabajo = client.tunings.get(name=nombre_trabajo)
        print(f"estado actual: {trabajo.state}")
        if trabajo.state in estados_finales:
            return trabajo
        time.sleep(intervalo_segundos)


def enviar_trabajo(examples: list[types.TuningExample]) -> None:
    load_dotenv()
    client = genai.Client()
    config = types.CreateTuningJobConfig(
        tuning_mode=types.TuningMode.TUNING_MODE_PEFT_ADAPTER,
        adapter_size=types.AdapterSize.ADAPTER_SIZE_FOUR,
        epoch_count=5,
        tuned_model_display_name="clasificador-mensajes-gas",
    )
    try:
        trabajo = client.tunings.tune(
            base_model="models/gemini-2.0-flash",
            training_dataset=types.TuningDataset(examples=examples),
            config=config,
        )
        print("Trabajo creado:", trabajo.name)
        esperar_a_que_termine(client, trabajo.name)
    except Exception as error:
        print("No se pudo crear el trabajo de tuning:", error)


def main() -> None:
    print(len(examples), "ejemplos construidos")
    print(examples[0])

    print("\n--- Balance por intencion ---")
    balance = chequear_balance(ejemplos_raw, "intencion")
    for categoria, cuenta in balance.most_common():
        print(f"{categoria}: {cuenta}")
    print(f"razon max/min: {max(balance.values()) / min(balance.values()):.1f}x")

    print("\n--- Validacion ---")
    problemas = validar_dataset(examples, CLAVES_ESPERADAS)
    print(f"{len(examples)} ejemplos, {len(problemas)} problemas encontrados")
    for p in problemas:
        print(" -", p)

    print("\n--- El validador detecta errores (dataset roto a proposito) ---")
    rotos = examples + [
        types.TuningExample(text_input="", output='{"intencion": "otro"}'),
        types.TuningExample(text_input=ejemplos_raw[0][0], output="no es json"),
    ]
    problemas_rotos = validar_dataset(rotos, CLAVES_ESPERADAS)
    print(f"{len(rotos)} ejemplos, {len(problemas_rotos)} problemas encontrados")
    for p in problemas_rotos:
        print(" -", p)

    if "--enviar" in sys.argv:
        if problemas:
            raise SystemExit("Corrige los problemas del dataset antes de enviar.")
        enviar_trabajo(examples)


if __name__ == "__main__":
    main()
