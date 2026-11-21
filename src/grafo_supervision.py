"""Punto de supervisión humana para desplegar una versión nueva del prompt .

Grafo de LangGraph con tres nodos:
  proponer   -> toma la huella nueva del registro de prompts.
  supervisar -> interrupt(): pausa hasta que una persona apruebe o rechace.
  aplicar    -> activa la versión si fue aprobada; si no, mantiene la anterior.

Cada solicitud usa su propio thread_id y se reanuda siempre con Command(resume=<bool>).

Uso (con el entorno virtual activo):
    python src/grafo_supervision.py
"""

import sys
import uuid
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registro_prompts import NOMBRE_PROMPT, registro  # noqa: E402


class EstadoDespliegue(TypedDict):
    huella_nueva: str
    aprobado: bool


def proponer(estado: EstadoDespliegue):
    print("nodo: proponer, huella propuesta:", estado["huella_nueva"])
    return {}


def supervisar(estado: EstadoDespliegue):
    decision = interrupt({
        "motivo": "aprobar nueva version de prompt en produccion",
        "huella_propuesta": estado["huella_nueva"],
    })
    return {"aprobado": decision}


def aplicar(estado: EstadoDespliegue):
    if estado["aprobado"]:
        print("version", estado["huella_nueva"], "activada")
    else:
        print("version", estado["huella_nueva"], "rechazada, se mantiene la anterior")
    return {}


grafo = StateGraph(EstadoDespliegue)
grafo.add_node("proponer", proponer)
grafo.add_node("supervisar", supervisar)
grafo.add_node("aplicar", aplicar)
grafo.add_edge(START, "proponer")
grafo.add_edge("proponer", "supervisar")
grafo.add_edge("supervisar", "aplicar")
grafo.add_edge("aplicar", END)

app_despliegue = grafo.compile(checkpointer=InMemorySaver())


def nuevo_thread_id(prefijo="despliegue"):
    """Un thread_id único por solicitud: reutilizarlo sobrescribe la corrida anterior."""
    return f"{prefijo}-{uuid.uuid4().hex[:8]}"


def resolver(app, config, aprobar):
    """Reanuda solo si hay una aprobación pendiente; evita aprobar algo ya resuelto."""
    if not app.get_state(config).next:
        raise ValueError("este thread_id no tiene ninguna aprobacion pendiente")
    return app.invoke(Command(resume=bool(aprobar)), config=config)


if __name__ == "__main__":
    huella = registro.ultima(NOMBRE_PROMPT)["huella"]  # huella real del Paso 1

    # Camino de aprobación
    cfg1 = {"configurable": {"thread_id": nuevo_thread_id()}}
    r = app_despliegue.invoke({"huella_nueva": huella, "aprobado": False}, config=cfg1)
    print("1) tras invocar (interrumpido):", "__interrupt__" in r)
    print("2) pendiente:", app_despliegue.get_state(cfg1).interrupts[0].value)
    print("3) tras aprobar:", resolver(app_despliegue, cfg1, True))

    # Camino de rechazo, con otro thread_id
    cfg2 = {"configurable": {"thread_id": nuevo_thread_id()}}
    app_despliegue.invoke({"huella_nueva": huella, "aprobado": False}, config=cfg2)
    print("4) tras rechazar:", resolver(app_despliegue, cfg2, False))

    # Aprobar dos veces la misma solicitud debe fallar
    try:
        resolver(app_despliegue, cfg1, True)
    except ValueError as e:
        print("5) ValueError:", e)
