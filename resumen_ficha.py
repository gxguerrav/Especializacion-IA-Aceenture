"""Resumen de hechos objetivos de la ficha para quien la revisa (Bloque 34).

Ejecutar desde la raíz del repositorio:  python resumen_ficha.py
No juzga ni aprueba: solo muestra los números.
"""

import os
import sys

from ficha_datos import RUTA, cargar


def lista(elementos):
    return ", ".join(elementos) if elementos else "ninguno"


def resumen(ficha):
    rf, rnf, cajones = ficha["rf"], ficha["rnf"], ficha["cajones"]
    con_criterio = {r for c in ficha["criterios"] for r in c["cubre"]}
    probados = {c for h in ficha["hitos"] for c in h["criterios"]}
    ids_criterios = {c["id"] for c in ficha["criterios"]}
    exigidos = cajones["Imprescindible"] + list(rnf)

    print(f"RF: {len(rf)} | RNF: {len(rnf)}")
    print(
        f"Alcance: imprescindibles {len(cajones['Imprescindible'])}, "
        f"deseables {len(cajones['Deseable'])}, "
        f"fuera de alcance {len(cajones['Fuera de alcance'])}"
    )
    print(f"Criterios de aceptacion: {len(ficha['criterios'])}")
    print(
        "Imprescindibles y RNF sin criterio:",
        lista([r for r in exigidos if r not in con_criterio]),
    )

    total = sum(h["horas"] for h in ficha["hitos"])
    disponibles, margen = ficha["disponibles"], ficha["margen"]
    linea = f"Hitos: {len(ficha['hitos'])}"
    linea += f" | Horas planificadas: {total:.1f} h"
    if disponibles is not None and margen is not None:
        tope = disponibles - margen
        linea += f" de {tope:.1f} h posibles"
        linea += f" ({disponibles:.1f} h menos {margen:.1f} h de margen)"
    print(linea)
    print(
        "Criterios que ningun hito comprueba:",
        lista(sorted(ids_criterios - probados)),
    )
    print(
        "Hitos sin criterio:",
        lista([h["id"] for h in ficha["hitos"] if not h["criterios"]]),
    )


if __name__ == "__main__":
    if not os.path.exists(RUTA):
        sys.exit(f"No existe {RUTA}. Ejecuta el script desde la raiz.")
    resumen(cargar())
