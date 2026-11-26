"""Lee la Ficha de Diseño Funcional como datos (Bloque 34).

Convierte docs/ficha_diseno_funcional.md en un diccionario: requerimientos,
cajones del alcance, criterios de aceptación y hitos con sus referencias.
Reutiliza leer_secciones de verificar_ficha.py (Bloque 33).
"""

import re

from verificar_ficha import RUTA, leer_secciones

NUMERO = r"(\d+(?:[.,]\d+)?)"


def a_numero(texto):
    return float(texto.replace(",", "."))


def cargar(ruta=RUTA):
    with open(ruta, encoding="utf-8") as archivo:
        secciones = leer_secciones(archivo.read())

    req = secciones[2][1]
    cuerpo4 = secciones.get(4, ("", ""))[1]
    cuerpo5 = secciones.get(5, ("", ""))[1]

    ficha = {
        "rf": dict(re.findall(r"(?m)^- (RF-\d{2}): (.+)$", req)),
        "rnf": dict(re.findall(r"(?m)^- (RNF-\d{2}): (.+)$", req)),
        "cajones": {},
        "criterios": [],
        "hitos": [],
        "texto4": cuerpo4,
        "texto5": cuerpo5,
    }

    for nombre in ("Imprescindible", "Deseable", "Fuera de alcance"):
        m = re.search(rf"(?m)^{nombre}:\s*(.*)$", req)
        ficha["cajones"][nombre] = (
            re.findall(r"RF-\d{2}", m.group(1)) if m else []
        )

    patron_ca = r"(?m)^- (CA-\d{2}) \(([^)]*)\): (.+)$"
    for id_, cubre, texto in re.findall(patron_ca, cuerpo4):
        ficha["criterios"].append(
            {
                "id": id_,
                "cubre": re.findall(r"RNF?-\d{2}|RF-\d{2}", cubre),
                "texto": texto,
            }
        )

    for clave, etiqueta in (
        ("disponibles", "Horas disponibles"),
        ("margen", "Margen de imprevistos"),
    ):
        m = re.search(rf"(?m)^{etiqueta}:\s*{NUMERO} h", cuerpo5)
        ficha[clave] = a_numero(m.group(1)) if m else None

    patron_h = rf"(?m)^- (H\d+) \({NUMERO} h\): (.+)$"
    for id_, horas, resto in re.findall(patron_h, cuerpo5):
        m = re.search(r"Cubre:(.*?)Se comprueba con:(.*)$", resto)
        ficha["hitos"].append(
            {
                "id": id_,
                "horas": a_numero(horas),
                "cubre": re.findall(r"RNF?-\d{2}|RF-\d{2}", m.group(1))
                if m
                else [],
                "criterios": re.findall(r"CA-\d{2}", m.group(2))
                if m
                else [],
            }
        )

    return ficha
