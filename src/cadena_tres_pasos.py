"""
Chain de tres pasos (LangChain) para atender mensajes de clientes de gas en cilindros.

    1. clasificar: el mensaje del cliente -> tema (pedido, cotizacion, reclamo, otro)
    2. redactar:   mensaje + tema         -> borrador de respuesta según ese tema
    3. revisar:    borrador               -> respuesta final con tono cordial y sin promesas

Cada paso depende del anterior: la redacción cambia según la clasificación y la
revisión trabaja sobre el borrador. El modelo entra como parámetro para poder
reemplazarlo por un mock en las pruebas.

Ejecutar: python src/cadena_tres_pasos.py
"""
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_google_genai import ChatGoogleGenerativeAI

MODELO = "gemini-3.5-flash-lite"

CATALOGO = (
    "Catálogo: cilindro de 5 kg $12.000, de 11 kg $20.000, "
    "de 15 kg $27.000, de 45 kg $75.000. Despacho a domicilio gratis."
)

# Responsabilidad: ubicar el mensaje en un único tema.
plantilla_clasificar = PromptTemplate.from_template(
    "Eres el clasificador de mensajes de una empresa que vende gas en "
    "cilindros a domicilio. Responde con una sola palabra en minúsculas, "
    "sin puntuación: pedido, cotizacion, reclamo u otro.\n\n"
    "Mensaje del cliente:\n{mensaje}"
)

# Responsabilidad: redactar un borrador adecuado al tema detectado.
plantilla_redactar = PromptTemplate.from_template(
    "Eres un agente de atención al cliente de una empresa de gas en "
    "cilindros. El mensaje del cliente fue clasificado como: {clasificacion}.\n"
    "Redacta una respuesta breve (máximo 4 líneas) adecuada a ese tipo de "
    "mensaje. Usa solo estos datos y no inventes precios ni plazos.\n"
    "{catalogo}\n\n"
    "Mensaje del cliente:\n{mensaje}"
)

# Responsabilidad: corregir el tono y quitar compromisos que la empresa no puede cumplir.
plantilla_revisar = PromptTemplate.from_template(
    "Revisa este borrador de respuesta a un cliente. Corrige el tono para que "
    "sea cordial y profesional, elimina cualquier promesa que no esté "
    "respaldada por el catálogo y devuelve únicamente el texto final, sin "
    "comentarios ni explicaciones:\n\n{borrador}"
)


def construir_cadena(modelo):
    """Devuelve la chain armada, sin ejecutarla. Entrada: {"mensaje": str}."""
    paso_clasificar = plantilla_clasificar | modelo | StrOutputParser()
    paso_redactar = plantilla_redactar | modelo | StrOutputParser()
    paso_revisar = plantilla_revisar | modelo | StrOutputParser()

    return (
        # El mensaje original se conserva porque el paso 2 lo necesita junto con la clasificación.
        RunnableParallel(
            clasificacion=paso_clasificar,
            mensaje=lambda entrada: entrada["mensaje"],
        )
        | (lambda datos: {**datos, "catalogo": CATALOGO})
        | paso_redactar
        | (lambda borrador: {"borrador": borrador})
        | paso_revisar
    )


if __name__ == "__main__":
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(model=MODELO)
    cadena = construir_cadena(modelo)

    mensaje_cliente = (
        "Hola, ayer me trajeron un cilindro de 15 kilos y llegó con la válvula "
        "dañada. Casi no pude usarlo. Quiero que me lo cambien hoy mismo y "
        "además saber cuánto me costaría pedir otro de 45 kilos para el negocio."
    )
    resultado = cadena.invoke({"mensaje": mensaje_cliente})
    print(resultado)
