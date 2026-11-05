"""
Enrutamiento condicional (LangChain) para mensajes de clientes de gas en cilindros.

    1. clasificar: el mensaje del cliente -> categoría (pedido, cotizacion, reclamo, otro)
    2. bifurcar:   según la categoría, el mensaje sigue una ruta con su propio prompt

Cada ruta tiene un prompt distinto porque cada tipo de mensaje necesita algo distinto.
Una categoría que ninguna condición reconoce cae en la ruta por defecto ("otro").
El modelo y las rutas entran como parámetros para poder reemplazarlos por mocks en las pruebas.

Ejecutar: python src/enrutamiento.py
"""
import logging

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

MODELO = "gemini-3.5-flash-lite"

MENSAJE_ERROR_FINAL = (
    "No pudimos procesar tu mensaje en este momento. Intenta de nuevo más tarde."
)

# Fallback de las rutas: texto fijo, último recurso si el modelo falla.
respuesta_generica = RunnableLambda(
    lambda x: (
        "Gracias por tu mensaje. Un miembro de nuestro equipo te va a responder pronto."
    )
)

CATALOGO = (
    "Catálogo: cilindro de 5 kg $12.000, de 11 kg $20.000, "
    "de 15 kg $27.000, de 45 kg $75.000. Despacho a domicilio gratis."
)

# Bloque 1: clasificación de la entrada.
plantilla_clasificacion = PromptTemplate.from_template(
    "Clasifica el siguiente mensaje de un cliente de una empresa que vende gas "
    "en cilindros a domicilio en una sola palabra: pedido, cotizacion, reclamo "
    "u otro. Responde solo con esa palabra.\n\n{mensaje}"
)

# Bloque 2: las rutas posibles, cada una con un prompt realmente distinto.
plantilla_pedido = PromptTemplate.from_template(
    "Eres un agente de una empresa de gas en cilindros. El cliente quiere hacer "
    "un pedido. Confirma qué pidió y pide solo los datos que falten (cantidad, "
    "tamaño o dirección). No inventes precios ni plazos.\n"
    "{catalogo}\n\nMensaje del cliente:\n{mensaje}"
)

plantilla_cotizacion = PromptTemplate.from_template(
    "Eres un agente de una empresa de gas en cilindros. El cliente pide una "
    "cotización. Responde con los precios que correspondan usando solo este "
    "catálogo, sin inventar descuentos.\n"
    "{catalogo}\n\nMensaje del cliente:\n{mensaje}"
)

plantilla_reclamo = PromptTemplate.from_template(
    "Responde a este reclamo con empatía, reconociendo el problema antes de "
    "ofrecer una solución. No prometas plazos ni compensaciones que no estén "
    "respaldadas por el catálogo.\n"
    "{catalogo}\n\nMensaje del cliente:\n{mensaje}"
)

plantilla_otro = PromptTemplate.from_template(
    "Eres un agente de una empresa de gas en cilindros. Responde de forma breve "
    "y cordial a este mensaje y ofrece ayuda con pedidos o cotizaciones.\n"
    "{catalogo}\n\nMensaje del cliente:\n{mensaje}"
)


def construir_paso_clasificacion(modelo):
    """Clasifica el mensaje y normaliza la salida para que la comparación no falle por formato."""
    return (
        plantilla_clasificacion
        | modelo
        | StrOutputParser()
        | (lambda texto: texto.strip().lower())
    )


def _construir_ruta(plantilla, modelo):
    return (
        (lambda x: {**x, "catalogo": CATALOGO})
        | plantilla
        | modelo
        | StrOutputParser()
    )


def construir_cadena_queja_segura(cadena_queja):
    """Ruta de reclamo protegida: si falla, responde con el texto genérico en vez de propagar el error."""
    return cadena_queja.with_fallbacks([respuesta_generica])


def construir_rutas(modelo):
    """Devuelve las cuatro rutas reales armadas con el modelo recibido, cada una con su fallback."""
    return {
        "pedido": _construir_ruta(plantilla_pedido, modelo).with_fallbacks([respuesta_generica]),
        "cotizacion": _construir_ruta(plantilla_cotizacion, modelo).with_fallbacks(
            [respuesta_generica]
        ),
        "reclamo": construir_cadena_queja_segura(_construir_ruta(plantilla_reclamo, modelo)),
        "otro": _construir_ruta(plantilla_otro, modelo).with_fallbacks([respuesta_generica]),
    }


def construir_cadena_con_enrutamiento(
    paso_clasificacion,
    cadena_pedido=None,
    cadena_cotizacion=None,
    cadena_reclamo=None,
    cadena_otro=None,
):
    """
    Bloque 3: la bifurcación que conecta la clasificación con las rutas.
    Entrada: {"mensaje": str}. Una ruta no recibida solo se ejecuta si la elige la bifurcación.
    """
    cadena_pedido = cadena_pedido or RunnablePassthrough()
    cadena_cotizacion = cadena_cotizacion or RunnablePassthrough()
    cadena_reclamo = cadena_reclamo or RunnablePassthrough()
    cadena_otro = cadena_otro or RunnablePassthrough()

    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "reclamo", cadena_reclamo),
        (lambda x: x["categoria"] == "pedido", cadena_pedido),
        (lambda x: x["categoria"] == "cotizacion", cadena_cotizacion),
        cadena_otro,  # ruta por defecto: cualquier categoría no prevista
    )
    # assign agrega "categoria" sin perder "mensaje", que cada ruta usa en su prompt.
    return RunnablePassthrough.assign(categoria=paso_clasificacion) | bifurcacion


def construir_cadena(modelo):
    """Chain completa con el modelo real (o un mock) en la clasificación y en las cuatro rutas."""
    rutas = construir_rutas(modelo)
    return construir_cadena_con_enrutamiento(
        paso_clasificacion=construir_paso_clasificacion(modelo),
        cadena_pedido=rutas["pedido"],
        cadena_cotizacion=rutas["cotizacion"],
        cadena_reclamo=rutas["reclamo"],
        cadena_otro=rutas["otro"],
    )


def procesar_mensaje_seguro(cadena, mensaje):
    """
    Red de seguridad final: ningún fallo (ni siquiera en la clasificación) deja sin respuesta.
    El error se registra con traceback antes de devolver el mensaje seguro.
    """
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception:
        logger.exception("Error procesando mensaje")
        return MENSAJE_ERROR_FINAL


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    cadena = construir_cadena(ChatGoogleGenerativeAI(model=MODELO))

    for mensaje_cliente in (
        "Quiero 2 cilindros de 15 kilos, mi dirección es Av. Los Leones 1234.",
        "¿Cuánto cuesta un cilindro de 45 kilos?",
        "Ayer me trajeron un cilindro con la válvula dañada.",
        "Buenas tardes, ¿a qué hora abren?",
    ):
        print(f"> {mensaje_cliente}")
        print(procesar_mensaje_seguro(cadena, mensaje_cliente), end="\n\n")
