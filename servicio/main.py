"""Capa HTTP: un endpoint por funcionalidad imprescindible de la ficha, más el de salud.

Sin lógica de negocio: cada endpoint llama a una función de `logica.py`.
Arranque (desde la raíz del repositorio):
    uvicorn servicio.main:app --reload
"""

from fastapi import FastAPI

from servicio import logica
from servicio.esquemas import Consulta, EstadoPedido, Respuesta

app = FastAPI(
    title="Asistente de atención de gas en cilindros",
    version="0.1.0",
    description="Responde sobre precios, despacho y reembolsos con sus fuentes, "
    "y consulta el estado de pedidos simulados.",
)


@app.get("/salud", tags=["sistema"], summary="Comprobar el servicio")
def salud():
    return {"estado": "ok"}


@app.post(
    "/consultas",
    response_model=Respuesta,
    tags=["consultas"],
    summary="Consultar el corpus",
)
def consultar(consulta: Consulta):
    """Devuelve la respuesta y los documentos que la respaldan (RF-01, RF-02)."""
    texto, fuentes = logica.responder(consulta.pregunta)
    return Respuesta(respuesta=texto, fuentes=fuentes)


@app.get(
    "/pedidos/{pedido_id}",
    response_model=EstadoPedido,
    tags=["pedidos"],
    summary="Consultar el estado de un pedido",
)
def consultar_pedido(pedido_id: str):
    """Devuelve el estado del pedido según los datos simulados (RF-03)."""
    return EstadoPedido(pedido_id=pedido_id, estado=logica.estado_pedido(pedido_id))
