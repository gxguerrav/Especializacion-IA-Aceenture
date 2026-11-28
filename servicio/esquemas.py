"""Contrato del servicio: qué entra y qué sale de cada endpoint (ficha: RF-01, RF-02, RF-03)."""

from pydantic import BaseModel, Field


class Consulta(BaseModel):
    pregunta: str = Field(
        description="Pregunta del usuario, en lenguaje natural.",
        examples=["¿Cuánto cuesta un cilindro de 15 kg?"],
    )


class Respuesta(BaseModel):
    respuesta: str = Field(description="Texto de la respuesta.")
    fuentes: list[str] = Field(
        description="Documentos que respaldan la respuesta; vacía si no hay información."
    )


class EstadoPedido(BaseModel):
    pedido_id: str = Field(description="Número del pedido consultado, por ejemplo GAS-1001.")
    estado: str = Field(
        description="Estado del pedido según los datos simulados, o aviso de que no existe."
    )
