"""
Agente con dos herramientas (LangChain) para atención de clientes de gas en cilindros.

    - consultar_estado_pedido: dónde está el pedido de un cliente (por número de pedido).
    - calcular_costo_pedido:   cuánto cuesta un pedido según tamaño de cilindro y cantidad.

El agente decide por sí mismo qué herramienta usar (o ninguna) según la pregunta.
Se arma con create_tool_calling_agent + AgentExecutor, con return_intermediate_steps=True
para verificar en código qué herramienta eligió, sin depender de la respuesta final.
El modelo entra como parámetro para poder reemplazarlo en las pruebas.

Ejecutar: python src/agente_con_herramientas.py
"""
from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

MODELO = "gemini-3.5-flash-lite"

PRECIOS_CILINDRO = {5: 12000, 11: 20000, 15: 27000, 45: 75000}

PEDIDOS = {
    "GAS-1001": "en camino, llega hoy entre las 15:00 y las 18:00",
    "GAS-1002": "entregado ayer",
    "GAS-1003": "recibido, sale a reparto mañana",
}


@tool
def consultar_estado_pedido(numero_pedido: str) -> str:
    """Consulta el estado actual de un pedido de gas a partir de su número de
    pedido (por ejemplo GAS-1001). Usar cuando el cliente pregunta dónde está
    su pedido, si ya salió o cuándo le llega."""
    try:
        return PEDIDOS[numero_pedido.strip().upper()]
    except KeyError:
        return f"No se encontró un pedido con el número {numero_pedido}."


@tool
def calcular_costo_pedido(kilos_cilindro: int, cantidad: int) -> str:
    """Calcula el costo total de un pedido según el tamaño del cilindro en kilos
    (5, 11, 15 o 45) y la cantidad de cilindros. Usar cuando el cliente pregunta
    cuánto va a pagar o cuánto cuesta comprar cierta cantidad de cilindros."""
    try:
        if cantidad <= 0:
            return "La cantidad debe ser mayor que cero."
        total = PRECIOS_CILINDRO[kilos_cilindro] * cantidad
        return f"El costo total es de ${total:,}.".replace(",", ".")
    except KeyError:
        disponibles = ", ".join(f"{k} kg" for k in PRECIOS_CILINDRO)
        return f"No existe el cilindro de {kilos_cilindro} kg. Disponibles: {disponibles}."


HERRAMIENTAS = [consultar_estado_pedido, calcular_costo_pedido]

PROMPT_AGENTE = ChatPromptTemplate.from_messages([
    (
        "system",
        "Eres un asistente de atención al cliente de una empresa que vende gas en "
        "cilindros a domicilio. Responde usando las herramientas disponibles cuando "
        "las necesites. No inventes datos que no tengas, como teléfonos, correos o "
        "direcciones: si no los conoces, di que no cuentas con esa información.",
    ),
    ("human", "{entrada}"),
    MessagesPlaceholder("agent_scratchpad"),
])


def crear_ejecutor(modelo=None, verbose=True):
    """Arma el agente y su ejecutor. `modelo` permite inyectar uno distinto."""
    if modelo is None:
        modelo = ChatGoogleGenerativeAI(model=MODELO)
    agente = create_tool_calling_agent(modelo, HERRAMIENTAS, PROMPT_AGENTE)
    return AgentExecutor(
        agent=agente,
        tools=HERRAMIENTAS,
        verbose=verbose,
        return_intermediate_steps=True,
    )


def herramientas_usadas(resultado):
    """Nombres de las herramientas que el agente invocó, en orden."""
    return [accion.tool for accion, _ in resultado["intermediate_steps"]]


def texto_respuesta(resultado):
    """Texto de la respuesta final. Gemini puede devolver una lista de bloques."""
    salida = resultado["output"]
    if isinstance(salida, list):
        return "".join(
            bloque.get("text", "") if isinstance(bloque, dict) else str(bloque)
            for bloque in salida
        )
    return salida


def main():
    load_dotenv()
    ejecutor = crear_ejecutor()

    # Prueba manual 1: debe disparar consultar_estado_pedido.
    r1 = ejecutor.invoke({"entrada": "¿Dónde está mi pedido GAS-1001?"})
    print("Respuesta:", texto_respuesta(r1))
    print("Herramientas:", herramientas_usadas(r1))
    assert herramientas_usadas(r1)[0] == "consultar_estado_pedido"

    # Prueba manual 2: debe disparar calcular_costo_pedido.
    r2 = ejecutor.invoke(
        {"entrada": "¿Cuánto me cuestan 3 cilindros de 15 kilos?"}
    )
    print("Respuesta:", texto_respuesta(r2))
    print("Herramientas:", herramientas_usadas(r2))
    assert herramientas_usadas(r2)[0] == "calcular_costo_pedido"

    # Prueba manual 3: pregunta general, no debe usar ninguna herramienta.
    r3 = ejecutor.invoke({"entrada": "¿Cómo puedo contactar a soporte?"})
    print("Respuesta:", texto_respuesta(r3))
    print("Herramientas:", herramientas_usadas(r3))
    assert r3["intermediate_steps"] == []


if __name__ == "__main__":
    main()
