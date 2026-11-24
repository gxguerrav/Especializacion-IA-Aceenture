"""Presupuesto de alcance del asistente de ventas de gas (Bloque 33).

Aplica las cuatro reglas de la lección: factor de novedad, reserva para pruebas/docs/defensa,
margen de imprevistos y orden de entrada (imprescindibles primero, los más baratos antes).

Ejecutar:  python presupuesto/presupuesto_alcance.py
"""

# Tareas con tecnologia que nunca usaste cuestan mas de lo que parece
FACTOR_NOVEDAD = 1.5
# Horas de laboratorio y evidencia que quedan en el modulo (AJUSTAR a las horas reales)
HORAS_DISPONIBLES = 20
# Parte reservada para pruebas, documentacion y ensayo de la defensa
RESERVA_PRUEBAS_DOCS = 0.30
# Parte reservada para imprevistos
MARGEN_IMPREVISTOS = 0.20
CAPAS_OBLIGATORIAS = {"api", "rag", "contenedor"}

# Horas: RF-02 y RF-03 reutilizan piezas ya construidas (servicio_rag.py y la herramienta
# consultar_estado_pedido); FastAPI y Docker son tecnología nueva, por eso novedad=True.
# RNF-03 figura aquí como tarea porque empaquetar en contenedor cuesta horas.
funcionalidades = [
    {"id": "RF-01", "horas": 2, "capa": "api",
     "nombre": "Endpoint de consulta con respuesta en JSON",
     "tipo": "imprescindible", "novedad": True, "sistema_real": False},
    {"id": "RF-02", "horas": 2, "capa": "rag",
     "nombre": "Respuesta con fuente citada desde el indice persistido",
     "tipo": "imprescindible", "novedad": False, "sistema_real": False},
    {"id": "RF-03", "horas": 2, "capa": "otra",
     "nombre": "Estado de un pedido por numero con datos simulados",
     "tipo": "imprescindible", "novedad": False, "sistema_real": False},
    {"id": "RNF-03", "horas": 2, "capa": "contenedor",
     "nombre": "Contenedor que levanta el servicio con un comando",
     "tipo": "imprescindible", "novedad": True, "sistema_real": False},
    {"id": "RF-04", "horas": 3, "capa": "otra",
     "nombre": "Aprobacion humana antes de generar un reembolso",
     "tipo": "deseable", "novedad": False, "sistema_real": False},
    {"id": "RF-05", "horas": 12, "capa": "otra",
     "nombre": "Interfaz web con historial de conversaciones",
     "tipo": "deseable", "novedad": True, "sistema_real": False},
    {"id": "RF-06", "horas": 10, "capa": "otra",
     "nombre": "Consulta al sistema de pedidos real de la empresa",
     "tipo": "imprescindible", "novedad": True, "sistema_real": True},
]


def horas_reales(f):
    return f["horas"] * (FACTOR_NOVEDAD if f["novedad"] else 1)


def presupuesto():
    neto = 1 - RESERVA_PRUEBAS_DOCS - MARGEN_IMPREVISTOS
    return round(HORAS_DISPONIBLES * neto, 2)


def recortar(lista):
    limite = presupuesto()
    usado = 0.0
    dentro, fuera = [], []
    orden = sorted(
        lista,
        key=lambda f: (f["tipo"] != "imprescindible", horas_reales(f)),
    )
    for f in orden:
        h = horas_reales(f)
        if f["sistema_real"]:
            fuera.append((f, "requiere datos o sistemas reales"))
        elif usado + h <= limite:
            dentro.append(f)
            usado += h
        else:
            fuera.append((f, "no cabe en el presupuesto"))
    return dentro, fuera, usado


def informe(lista):
    pedido = sum(horas_reales(f) for f in lista)
    dentro, fuera, usado = recortar(lista)
    print(
        f"Pedido: {pedido:.1f} h | Presupuesto: {presupuesto():.1f} h "
        f"({pedido / presupuesto():.1f} veces lo disponible)"
    )
    print(f"\nDENTRO DEL MVP ({usado:.1f} h):")
    for f in dentro:
        print(
            f"  {f['id']} {f['nombre']} [{f['capa']}, {horas_reales(f):.1f} h]"
        )
    print("\nFUERA DE ALCANCE:")
    for f, motivo in fuera:
        print(f"  {f['id']} {f['nombre']} -> {motivo}")
    faltantes = CAPAS_OBLIGATORIAS - {f["capa"] for f in dentro}
    if faltantes:
        print(
            "\nATENCION: capas obligatorias sin cubrir:",
            ", ".join(sorted(faltantes)),
        )
    else:
        print("\nLas tres capas obligatorias estan cubiertas.")


if __name__ == "__main__":
    informe(funcionalidades)
