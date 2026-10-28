"""
Cliente modular de consumo de modelos.

Único punto de entrada: consultar_modelo(pregunta). Por dentro arma la petición,
la envía con reintento (backoff exponencial con techo y jitter), clasifica los
errores, registra el costo de la operación y extrae el texto.

    ValueError    -> credencial inválida o sin permiso (no se reintenta)
    RuntimeError  -> el servicio no respondió tras varios intentos
"""
import random
import time
from typing import Any, Callable

from consumir_gemini import armar_peticion, enviar_peticion, extraer_texto

COSTO_POR_1000_TOKENS = 0.002  # referencial, ajusta según el modelo que uses
costo_total_sesion = 0.0


def con_reintento(
    funcion: Callable[[], Any],
    intentos: int = 3,
    espera_base: float = 2,
    espera_maxima: float = 30,
) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            if intento == intentos:
                raise
            espera = min(espera_base * (2 ** (intento - 1)), espera_maxima)
            espera_con_jitter = espera + random.uniform(0, espera * 0.1)
            print(f"Intento {intento} de {intentos} falló. Reintentando en {espera_con_jitter:.1f}s...")
            time.sleep(espera_con_jitter)


def registrar_costo(respuesta: dict) -> float:
    global costo_total_sesion
    uso = respuesta.get("usageMetadata", {})
    total_tokens = uso.get("totalTokenCount", 0)
    costo_estimado = (total_tokens / 1000) * COSTO_POR_1000_TOKENS
    costo_total_sesion += costo_estimado
    print(
        f"Operación: {total_tokens} tokens, costo estimado: ${costo_estimado:.5f} "
        f"(acumulado: ${costo_total_sesion:.5f})"
    )
    return costo_estimado


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
    registrar_costo(respuesta)
    return extraer_texto(respuesta)


if __name__ == "__main__":
    try:
        print(consultar_modelo("¿Cuál es la capital de Chile?"))
        print(f"Costo acumulado de la sesión: ${costo_total_sesion:.5f}")
    except ValueError as error:
        print(f"Error de configuración: {error}")
    except RuntimeError as error:
        print(f"El servicio no respondió tras varios intentos: {error}")
