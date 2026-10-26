"""
Cliente modular de consumo de modelos.

Único punto de entrada: consultar_modelo(pregunta). Por dentro arma la petición,
la envía con reintento, clasifica los errores y extrae el texto.

    ValueError    -> credencial inválida o sin permiso (no se reintenta)
    RuntimeError  -> el servicio no respondió tras varios intentos
"""
import time
from typing import Any, Callable

from consumir_gemini import armar_peticion, enviar_peticion, extraer_texto


def con_reintento(
    funcion: Callable[[], Any],
    intentos: int = 3,
    espera_segundos: int = 2,
) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            if intento == intentos:
                raise
            print(f"Intento {intento} de {intentos} falló por límite de uso. Reintentando...")
            time.sleep(espera_segundos)


def consultar_modelo(
    pregunta: str,
    system_instruction: str = "",
    response_schema: dict | None = None,
) -> str:
    url, cuerpo = armar_peticion(pregunta, system_instruction, response_schema)
    try:
        respuesta = con_reintento(lambda: enviar_peticion(url, cuerpo))
    except TimeoutError:
        raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.")
    return extraer_texto(respuesta)


if __name__ == "__main__":
    try:
        print(consultar_modelo("¿Cuál es la capital de Chile?"))
    except ValueError as error:
        print(f"Error de configuración: {error}")
    except RuntimeError as error:
        print(f"El servicio no respondió tras varios intentos: {error}")
