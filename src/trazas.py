"""
Trazas de decisión del agente (Bloque 23).

    - registrar_traza: guarda cada interacción (pregunta, herramientas usadas con sus
      argumentos, respuesta final) como una línea JSON en trazas_agente.jsonl.
    - marcar_repeticiones_sospechosas: primera pasada automática que señala sesiones donde
      la misma herramienta se invocó dos veces seguidas. Es un candidato a revisar, no una
      conclusión.
"""
import json
from datetime import datetime, timezone

ARCHIVO_TRAZAS = "trazas_agente.jsonl"


def registrar_traza(
    session_id: str,
    entrada: str,
    resultado: dict,
    archivo: str = ARCHIVO_TRAZAS,
) -> None:
    """Agrega una línea al archivo de trazas. Sin "intermediate_steps", acciones queda vacía."""
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "entrada": entrada,
        "acciones": [
            {
                "herramienta": accion.tool,
                "argumentos": accion.tool_input,
                "observacion": observacion,
            }
            for accion, observacion in resultado.get("intermediate_steps", [])
        ],
        "respuesta_final": resultado.get("output"),
    }
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")


def marcar_repeticiones_sospechosas(archivo: str = ARCHIVO_TRAZAS) -> list:
    """Imprime y devuelve [(session_id, herramienta)] con repeticiones consecutivas."""
    try:
        with open(archivo, encoding="utf-8") as f:
            lineas = [linea for linea in f if linea.strip()]
    except FileNotFoundError:
        print(f"No se encontró '{archivo}'. Corre el agente al menos una vez antes de revisar.")
        return []

    sospechosas = []
    for numero, linea in enumerate(lineas, start=1):
        try:
            registro = json.loads(linea)
        except json.JSONDecodeError:
            print(f"Línea {numero} ilegible en '{archivo}', se omite.")
            continue
        herramientas = [a["herramienta"] for a in registro.get("acciones", [])]
        for i in range(1, len(herramientas)):
            if herramientas[i] == herramientas[i - 1]:
                sospechosas.append((registro.get("session_id"), herramientas[i]))
                print(
                    f"Revisar: {registro.get('session_id')} usó "
                    f"'{herramientas[i]}' dos veces seguidas"
                )
                break
    return sospechosas
