"""
Agente con dos herramientas (LangChain) para atención de clientes de gas en cilindros.

    - consultar_estado_pedido_con_historial: dónde está el pedido de un cliente y,
      opcionalmente, su historial de estados (args_schema con un campo por parámetro).
    - calcular_costo_pedido: cuánto cuesta un pedido según tamaño de cilindro y
      cantidad (también con args_schema).

El agente decide por sí mismo qué herramienta usar (o ninguna) según la pregunta.
Se arma con create_tool_calling_agent + AgentExecutor, con return_intermediate_steps=True
para verificar en código qué herramienta eligió, sin depender de la respuesta final.

Bloque 22: se envuelve con RunnableWithMessageHistory para que recuerde la conversación
(un historial por session_id, sin mezclarse entre clientes).
El modelo entra como parámetro para poder reemplazarlo en las pruebas.

Ejecutar: python src/agente_con_herramientas.py
"""
import sys

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from supervision import esperar_aprobacion, registrar_aprobacion, registro_aprobaciones
from trazas import registrar_traza

MODELO = "gemini-3.5-flash-lite"

PRECIOS_CILINDRO = {5: 12000, 11: 20000, 15: 27000, 45: 75000}

PEDIDOS = {
    "GAS-1001": {
        "actual": "en camino, llega hoy entre las 15:00 y las 18:00",
        "historial": ["recibido", "preparado en bodega", "en camino"],
    },
    "GAS-1002": {
        "actual": "entregado ayer",
        "historial": ["recibido", "preparado en bodega", "en camino", "entregado"],
    },
    "GAS-1003": {
        "actual": "recibido, sale a reparto mañana",
        "historial": ["recibido"],
    },
}


class ArgumentosConsultaPedido(BaseModel):
    numero_pedido: str = Field(
        description="Número del pedido, por ejemplo 'GAS-1001'."
    )
    incluir_historial: bool = Field(
        default=False,
        description="Si es True, incluye el historial completo de estados, no solo el actual.",
    )


class ArgumentosCostoPedido(BaseModel):
    kilos_cilindro: int = Field(
        description="Tamaño del cilindro en kilos: 5, 11, 15 o 45."
    )
    cantidad: int = Field(description="Cantidad de cilindros a comprar, mayor que cero.")


@tool("consultar_estado_pedido_con_historial", args_schema=ArgumentosConsultaPedido)
def consultar_estado_pedido(numero_pedido: str, incluir_historial: bool = False) -> str:
    """Consulta el estado de un pedido de gas a partir de su número de pedido, con
    la opción de incluir su historial completo. Usar cuando el cliente pregunta
    dónde está su pedido, si ya salió, cuándo le llega o por qué pasos ha pasado."""
    pedido = PEDIDOS.get(numero_pedido.strip().upper())
    if pedido is None:
        return f"No se encontró un pedido con el número {numero_pedido}."
    if not incluir_historial:
        return pedido["actual"]
    return f"{pedido['actual']} (historial: {', '.join(pedido['historial'])})"


@tool(args_schema=ArgumentosCostoPedido)
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


class ArgumentosReembolso(BaseModel):
    numero_pedido: str = Field(
        description="Número del pedido a reembolsar, por ejemplo 'GAS-1002'."
    )
    monto: float = Field(description="Monto a reembolsar en pesos, mayor que cero.")


@tool(args_schema=ArgumentosReembolso)
def generar_reembolso(numero_pedido: str, monto: float) -> str:
    """Genera un reembolso para un pedido. Acción irreversible que mueve dinero:
    requiere aprobación humana antes de ejecutarse. Usar solo cuando el cliente
    pide explícitamente un reembolso."""
    numero = numero_pedido.strip().upper()
    # Se valida antes de molestar a un supervisor con una solicitud que no puede proceder.
    if numero not in PEDIDOS:
        return f"No se encontró un pedido con el número {numero_pedido}."
    if monto <= 0:
        return "El monto del reembolso debe ser mayor que cero."

    mensaje = (
        f"El agente quiere reembolsar ${monto:,.0f} para el pedido {numero}. "
        "¿Aprobar? (s/n): "
    ).replace(",", ".")
    aprobado = esperar_aprobacion(mensaje)
    registrar_aprobacion(
        herramienta="generar_reembolso",
        argumentos={"numero_pedido": numero, "monto": monto},
        aprobado=aprobado,
    )
    if not aprobado:
        return "Reembolso no aprobado por el supervisor humano."
    # Simulado: en un sistema real, aquí se llamaría al sistema de pagos.
    return f"Reembolso de ${monto:,.0f} generado para el pedido {numero}.".replace(",", ".")


HERRAMIENTAS = [consultar_estado_pedido, calcular_costo_pedido, generar_reembolso]

PROMPT_AGENTE = ChatPromptTemplate.from_messages([
    (
        "system",
        "Eres un asistente de atención al cliente de una empresa que vende gas en "
        "cilindros a domicilio. Responde usando las herramientas disponibles cuando "
        "las necesites. No inventes datos que no tengas, como teléfonos, correos o "
        "direcciones: si no los conoces, di que no cuentas con esa información. "
        "Informa el resultado de un reembolso tal como lo devuelve la herramienta: "
        "si dice que no fue aprobado, dilo sin insistir; si dice que fue generado, "
        "confírmalo sin mencionar aprobaciones pendientes.",
    ),
    MessagesPlaceholder("chat_history"),
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


def crear_agente_con_memoria(ejecutor, historiales=None):
    """Envuelve el ejecutor con memoria. Devuelve (agente_con_memoria, obtener_historial).

    `historiales` es un diccionario en memoria (session_id -> historial); se pierde si
    el proceso se reinicia. Para persistir, basta reemplazar `obtener_historial`.
    """
    historiales = {} if historiales is None else historiales

    def obtener_historial(session_id: str):
        if session_id not in historiales:
            historiales[session_id] = InMemoryChatMessageHistory()
        return historiales[session_id]

    # Gemini devuelve "output" como lista de bloques; si eso se guarda tal cual en el
    # historial, el turno siguiente falla al reconstruir los mensajes. Se normaliza a texto.
    ejecutor_texto = ejecutor | RunnableLambda(
        lambda r: {**r, "output": texto_respuesta(r)}
    )

    agente_con_memoria = RunnableWithMessageHistory(
        ejecutor_texto,
        obtener_historial,
        input_messages_key="entrada",
        history_messages_key="chat_history",
    )
    return agente_con_memoria, obtener_historial


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


def consultar(agente, session_id, entrada):
    """Invoca al agente y deja la interacción en trazas_agente.jsonl (Bloque 23)."""
    resultado = agente.invoke(
        {"entrada": entrada}, {"configurable": {"session_id": session_id}}
    )
    registrar_traza(session_id, entrada, resultado)
    return resultado


def main():
    load_dotenv()
    ejecutor = crear_ejecutor()
    agente, obtener_historial = crear_agente_con_memoria(ejecutor)

    # Prueba 1: dos turnos con el mismo session_id; el segundo no repite el pedido.
    r1 = consultar(agente, "cliente_1", "¿Dónde está mi pedido GAS-1001, con su historial?")
    print("Respuesta:", texto_respuesta(r1))
    print("Herramientas:", herramientas_usadas(r1))
    assert herramientas_usadas(r1)[0] == "consultar_estado_pedido_con_historial"

    r2 = consultar(agente, "cliente_1", "¿Y ese pedido ya fue entregado?")
    print("Respuesta:", texto_respuesta(r2))
    print("Herramientas:", herramientas_usadas(r2))
    assert len(obtener_historial("cliente_1").messages) == 4

    # Prueba 2: otro session_id no debe saber nada del primero.
    r3 = consultar(agente, "cliente_2", "¿De qué pedido te pregunté?")
    print("Respuesta:", texto_respuesta(r3))
    assert herramientas_usadas(r3) == []
    assert len(obtener_historial("cliente_2").messages) == 2
    assert len(obtener_historial("cliente_1").messages) == 4

    # Prueba 3: la herramienta de costo sigue funcionando.
    r4 = consultar(agente, "cliente_2", "¿Cuánto me cuestan 3 cilindros de 15 kilos?")
    print("Respuesta:", texto_respuesta(r4))
    print("Herramientas:", herramientas_usadas(r4))
    assert herramientas_usadas(r4)[0] == "calcular_costo_pedido"

    # Prueba 4 (Bloque 23, solo con --reembolso): herramienta de riesgo alto. Pide
    # aprobación por consola (responde s/n); sin respuesta en 5 minutos, se rechaza.
    if "--reembolso" in sys.argv:
        r5 = consultar(agente, "cliente_3", "Quiero que me reembolsen $15000 del pedido GAS-1002")
        print("Respuesta:", texto_respuesta(r5))
        print("Herramientas:", herramientas_usadas(r5))
        print("Registro de aprobaciones:", registro_aprobaciones)
        assert herramientas_usadas(r5)[0] == "generar_reembolso"
        assert len(registro_aprobaciones) == 1


if __name__ == "__main__":
    main()
