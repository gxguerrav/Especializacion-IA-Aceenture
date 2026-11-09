"""
Supervisión humana para herramientas de riesgo alto (Bloque 23).

    - esperar_aprobacion: pide un "s/n" a una persona, con límite de tiempo. Si no hay
      respuesta a tiempo (o no hay entrada estándar), devuelve False: lo seguro es no ejecutar.
    - registrar_aprobacion: guarda cada decisión (aprobada o no) en memoria.

La lección usa select.select() sobre stdin, que no funciona en Windows. Aquí la espera se
hace en un hilo aparte con un Event, que funciona igual en Windows, Linux y macOS.
"""
import threading
from datetime import datetime

registro_aprobaciones = []


def esperar_aprobacion(
    mensaje: str,
    tiempo_limite_segundos: int = 300,
    leer_respuesta=input,
) -> bool:
    """Muestra `mensaje` y espera una respuesta humana. Solo "s" aprueba.

    `leer_respuesta` es la función que obtiene el texto (por defecto, input) y se puede
    reemplazar en las pruebas. Ante timeout, EOF o cualquier otra respuesta: False.
    """
    print(mensaje)
    respuesta = []
    recibida = threading.Event()

    def leer():
        try:
            respuesta.append(leer_respuesta())
        except (EOFError, OSError):
            pass  # sin entrada estándar: se trata como "no aprobado"
        finally:
            recibida.set()

    # daemon=True: si nadie responde, el hilo no impide que el programa termine.
    threading.Thread(target=leer, daemon=True).start()

    if not recibida.wait(tiempo_limite_segundos):
        return False
    return bool(respuesta) and respuesta[0].strip().lower() == "s"


def registrar_aprobacion(herramienta: str, argumentos: dict, aprobado: bool) -> None:
    """Guarda quién/qué/cuándo de una decisión de aprobación en `registro_aprobaciones`."""
    registro_aprobaciones.append({
        "herramienta": herramienta,
        "argumentos": argumentos,
        "aprobado": aprobado,
        "momento": datetime.now().isoformat(),
    })
