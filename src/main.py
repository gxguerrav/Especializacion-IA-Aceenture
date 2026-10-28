"""
Asistente de ventas de gas.

Uso:
    python src/main.py                      # modo conversación (escribe "salir" para terminar)
    python src/main.py "Quiero 2 de 15 kg"  # un solo mensaje
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "prompts"))

from consumir_gemini import (
    armar_peticion,
    enviar_peticion,
    extraer_texto,
    parsear_respuesta_json,
)
from banco import BANCO_DE_PROMPTS # type: ignore porque está en un directorio diferente

PROMPTS = {prompt["nombre"]: prompt for prompt in BANCO_DE_PROMPTS}
INTENCIONES_DE_COMPRA = ("comprar", "cotizar")


def ejecutar_prompt(nombre, mensaje_usuario):
    prompt = PROMPTS[nombre]
    url, body = armar_peticion(
        mensaje_usuario,
        prompt["system_instruction"],
        prompt.get("response_schema"),
    )
    texto = extraer_texto(enviar_peticion(url, body))
    return parsear_respuesta_json(texto, prompt["claves_esperadas"])


def atender_mensaje(mensaje):
    intencion = ejecutar_prompt("clasificar_intencion", mensaje)
    print(f"  [intención: {intencion['intencion']} ({intencion['confianza']:.2f})]")

    if intencion["intencion"] in INTENCIONES_DE_COMPRA:
        pedido = ejecutar_prompt("extraer_pedido", mensaje)
        faltantes = pedido["datos_faltantes"]
        print(f"  [pedido: {pedido['cantidad']} x {pedido['tipo_cilindro_kg']} kg"
              f" -> {pedido['direccion'] or 'sin dirección'}"
              f"{'; faltan: ' + ', '.join(faltantes) if faltantes else ''}]")

    respuesta = ejecutar_prompt("respuesta_de_venta", mensaje)
    print(f"Asistente: {respuesta['mensaje']}")
    if respuesta["total"]:
        print(f"  [total: ${respuesta['total']:,}]".replace(",", "."))


def responder(mensaje):
    try:
        atender_mensaje(mensaje)
    except (ValueError, RuntimeError, TimeoutError) as error:
        print("No se pudo completar la operación:", error)


def main():
    if len(sys.argv) > 1:
        responder(" ".join(sys.argv[1:]))
        return
    print("Asistente de ventas de gas. Escribe tu mensaje (o 'salir').")
    while True:
        mensaje = input("\nCliente: ").strip()
        if mensaje.lower() in ("salir", "exit", "q"):
            break
        if mensaje:
            responder(mensaje)
    print("Hasta luego.")


if __name__ == "__main__":
    main()
