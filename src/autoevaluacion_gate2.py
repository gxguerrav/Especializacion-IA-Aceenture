"""Autoevaluación del Gate 2: promedio ponderado + los cuatro criterios no compensables.

Los puntajes por dimensión son una ESTIMACION propia (con su justificación al lado):
ajústalos a tu criterio antes de entregar. Los cuatro criterios no compensables NO se
declaran a mano: se comprueban corriendo el servicio de verdad en modo simulado.

    python src/autoevaluacion_gate2.py
"""

import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import servicio_rag  # noqa: E402
from logging_rag import configurar_logger  # noqa: E402

PESOS = {
    "pipeline_funcional": 0.25,
    "recuperacion_citacion": 0.15,
    "costo_latencia": 0.10,
    "personalizacion": 0.15,
    "observabilidad": 0.15,
    "seguridad_gobernanza": 0.20,
}

# (puntaje 0-100, justificacion)
MI_PUNTAJE = {
    "pipeline_funcional": (88, "indexa de forma persistida e incremental, recupera, filtra, cita y "
                               "responde; corrida real documentada solo con modelo simulado en el Gate"),
    "recuperacion_citacion": (75, "recall 1.000 pero precision 0.308 con k=3 (mejora pendiente: k=1/2); "
                                  "falta el documento de medios de pago"),
    "costo_latencia": (85, "tiempos por etapa y tokens por consulta en registros_latencia_costo.jsonl, "
                           "con corridas reales"),
    "personalizacion": (85, "decision RAG con matriz de puntaje sobre el caso propio "
                            "(docs/decision_personalizacion.md); margen de 1 punto, frágil"),
    "observabilidad": (90, "logs JSON con trace_id por consulta, consumo por consulta y auditoria"),
    "seguridad_gobernanza": (85, "filtro de inyeccion (lista negra), versionado de prompts, "
                                 "supervision con interrupt() y matriz de 6 riesgos"),
}


def promedio_ponderado(puntajes, pesos):
    return sum(puntajes[d] * pesos[d] for d in pesos)


def comprobar_no_compensables():
    """Corre las cuatro comprobaciones sobre el servicio real (modo simulado, indice temporal)."""
    correo = "ana.perez@example.com"
    pregunta = f"cuanto cuesta el cilindro de 15 kilos? Mi correo es {correo}"
    resultados = {
        "pipeline_corre_de_punta_a_punta": False,
        "respuestas_citan_fuente": False,
        "logs_sin_contenido_crudo": False,
        "supervision_humana_funciona": False,
    }
    anterior = servicio_rag.DIRECTORIO_SIMULADO
    buffer = io.StringIO()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        servicio_rag.DIRECTORIO_SIMULADO = str(Path(carpeta) / "indice")
        try:
            configurar_logger(buffer)
            resultado = servicio_rag.crear_servicio("simulado")(pregunta)
            resultados["pipeline_corre_de_punta_a_punta"] = bool(resultado["respuesta"].strip())
            resultados["respuestas_citan_fuente"] = bool(resultado["fuentes"]) and any(
                f in resultado["respuesta"] for f in resultado["fuentes"])
            logs = buffer.getvalue()
            resultados["logs_sin_contenido_crudo"] = bool(logs) and correo not in logs and pregunta not in logs
        except Exception as error:  # una excepcion aqui es, por si misma, un criterio fallido
            print("fallo el pipeline:", type(error).__name__, error)
        finally:
            configurar_logger()
            servicio_rag.DIRECTORIO_SIMULADO = anterior
    try:
        pausas = []
        sup = servicio_rag.ejecutar_supervision(lambda p: pausas.append(p) or True)
        resultados["supervision_humana_funciona"] = bool(pausas) and sup["aprobado"] is True
    except Exception as error:
        print("fallo la supervision:", type(error).__name__, error)
    return resultados


def main():
    assert abs(sum(PESOS.values()) - 1.0) < 1e-9
    puntajes = {d: p for d, (p, _) in MI_PUNTAJE.items()}
    for dimension, (puntaje, nota) in MI_PUNTAJE.items():
        print(f"{dimension:24} {puntaje:3} (peso {PESOS[dimension]:.2f}) - {nota}")

    no_compensables = comprobar_no_compensables()
    print()
    for criterio, ok in no_compensables.items():
        print(f"{criterio:34} {'OK' if ok else 'FALLA'}")

    promedio = promedio_ponderado(puntajes, PESOS)
    todos_ok = all(no_compensables.values())
    print(f"\npromedio: {promedio:.1f}, no compensables OK? {todos_ok}, "
          f"aprueba? {promedio >= 80 and todos_ok}")
    sys.exit(0 if todos_ok else 1)


if __name__ == "__main__":
    main()
