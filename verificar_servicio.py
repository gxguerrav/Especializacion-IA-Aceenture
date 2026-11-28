"""Verifica el servicio FastAPI contra los criterios de aceptación de la ficha (sección 4).

Usa el cliente de pruebas de FastAPI: llama a la aplicación directamente, sin servidor.
Corre en modo simulado (sin clave ni red) salvo que se defina SERVICIO_MODO=real.

Cubre DOC-1 y DOC-2 (documentación) y CA-01 a CA-05. CA-06 a CA-09 (latencia, registros,
contenedor y precisión sobre las 10 consultas) pertenecen a los hitos H3 y H5.

Uso (desde la raíz del repositorio, con el entorno virtual activo):
    python verificar_servicio.py
"""

from fastapi.testclient import TestClient

from servicio.main import app

cliente = TestClient(app)
PREGUNTA_PRECIO = "¿Cuánto cuesta un cilindro de 15 kg?"
PREGUNTA_SIN_CORPUS = "¿Aceptan pagos con criptomonedas?"


def esquema():
    return cliente.get("/openapi.json").json()


def docs_navegables():
    r = cliente.get("/docs")
    if r.status_code != 200:
        return False, f"/docs responde {r.status_code}"
    return True, f"rutas documentadas: {sorted(esquema()['paths'])}"


def campos_documentados():
    esquemas = esquema()["components"]["schemas"]
    sin = [
        f"{nombre}.{campo}"
        for nombre in ("Consulta", "Respuesta", "EstadoPedido")
        for campo, datos in esquemas[nombre]["properties"].items()
        if "description" not in datos
    ]
    if sin:
        return False, f"sin descripcion: {sin}"
    return True, "todos los campos tienen descripcion"


def ca_01():
    r = cliente.post("/consultas", json={"pregunta": PREGUNTA_PRECIO})
    ok = r.status_code == 200 and set(r.json()) == {"respuesta", "fuentes"}
    return ok, f"estado {r.status_code}, campos {sorted(r.json())}"


def ca_02():
    r = cliente.post("/consultas", json={"pregunta": PREGUNTA_PRECIO})
    datos = r.json()
    ok = "catalogo_precios" in datos["fuentes"] and "$27.000" in datos["respuesta"]
    return ok, f"fuentes: {datos['fuentes']}"


def ca_03():
    r = cliente.post("/consultas", json={"pregunta": PREGUNTA_SIN_CORPUS})
    datos = r.json()
    ok = datos["fuentes"] == [] and "No tengo informacion" in datos["respuesta"]
    return ok, f"fuentes: {datos['fuentes']}, respuesta: {datos['respuesta']}"


def ca_04():
    r = cliente.get("/pedidos/GAS-1001")
    estado = r.json()["estado"]
    ok = r.status_code == 200 and "en camino" in estado and "15:00" in estado and "18:00" in estado
    return ok, f"estado: {estado}"


def ca_05():
    r = cliente.get("/pedidos/GAS-9999")
    estado = r.json()["estado"].lower()
    ok = r.status_code == 200 and "no existe" in estado and "en camino" not in estado
    return ok, f"estado: {r.json()['estado']}"


COMPROBACIONES = [
    ("DOC-1", "documentacion en /docs", docs_navegables),
    ("DOC-2", "campos documentados", campos_documentados),
    ("CA-01", "respuesta con respuesta y fuentes", ca_01),
    ("CA-02", "fuente catalogo_precios y $27.000", ca_02),
    ("CA-03", "sin informacion: no inventa", ca_03),
    ("CA-04", "pedido GAS-1001 en camino con hora", ca_04),
    ("CA-05", "pedido GAS-9999 no existe", ca_05),
]


def ejecutar(comprobaciones):
    cumplidas = 0
    for id_, descripcion, prueba in comprobaciones:
        try:
            ok, evidencia = prueba()
        except Exception as error:
            ok = False
            evidencia = f"error: {type(error).__name__}({error})"
        estado = "PASA " if ok else "FALLA"
        print(f"{estado} {id_} {descripcion} -> {evidencia}")
        cumplidas += 1 if ok else 0
    print(f"\n{cumplidas} de {len(comprobaciones)} comprobaciones cumplidas")
    return cumplidas == len(comprobaciones)


if __name__ == "__main__":
    raise SystemExit(0 if ejecutar(COMPROBACIONES) else 1)
