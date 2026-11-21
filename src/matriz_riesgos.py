"""Matriz de riesgos del asistente RAG de gas en cilindros .

Puntaje = probabilidad x impacto (ambos 1 a 5). Cortes fijados de antemano para todas las
filas: >=15 CRITICO, >=9 ALTO, >=4 MEDIO, resto BAJO. Todo riesgo ALTO o CRITICO lleva un
punto de supervisión humana concreto ("supervision"); es un campo documental, no lo usa el
cálculo.

Uso (con el entorno virtual activo):
    python src/matriz_riesgos.py
"""


def puntaje_riesgo(probabilidad, impacto):
    return probabilidad * impacto


def categoria_riesgo(puntaje):
    if puntaje >= 15:
        return "CRITICO"
    if puntaje >= 9:
        return "ALTO"
    if puntaje >= 4:
        return "MEDIO"
    return "BAJO"


def esta_en_el_limite(probabilidad, impacto):
    categoria_actual = categoria_riesgo(puntaje_riesgo(probabilidad, impacto))
    vecinos = [
        (probabilidad + 1, impacto),
        (probabilidad - 1, impacto),
        (probabilidad, impacto + 1),
        (probabilidad, impacto - 1),
    ]
    for p2, i2 in vecinos:
        if not (1 <= p2 <= 5 and 1 <= i2 <= 5):
            continue
        if categoria_riesgo(puntaje_riesgo(p2, i2)) != categoria_actual:
            return True
    return False


mis_riesgos = [
    {"riesgo": "Inyeccion de prompt indirecta via documento recuperado del corpus de gas",
     "probabilidad": 4,  # el indice se alimenta de texto que no controlo del todo
     "impacto": 4,       # puede revelar instrucciones internas o desviar la respuesta
     "mitigacion": "Filtro de patrones + contexto delimitado en <contexto> + roles "
                   "System/Human (Bloque 31, src/logging_rag.py)",
     "supervision": "Revision humana antes de responder cuando el filtro marca un documento"},
    {"riesgo": "Respuesta inventada o sin sustento sobre seguridad del gas (fuga, "
               "instalacion) que el cliente toma como instruccion",
     "probabilidad": 3,
     "impacto": 5,       # un consejo erroneo puede causar dano fisico
     "mitigacion": "Responder solo con el contexto recuperado y citar [n] (Bloque 31); "
                   "precision/recall de la recuperacion medidos (Bloque 27)",
     "supervision": "Escalar a una persona toda consulta de fuga o emergencia antes "
                    "de responder"},
    {"riesgo": "Cambio de prompt de sistema desplegado sin revision ni historial "
               "(regresion de seguridad no rastreable)",
     "probabilidad": 3,
     "impacto": 4,
     "mitigacion": "Registro de versiones con huella y diff (Bloque 32, "
                   "src/registro_prompts.py)",
     "supervision": "interrupt() de LangGraph antes de activar una version nueva "
                    "(src/grafo_supervision.py)"},
    {"riesgo": "Fuga de datos de clientes (nombre, direccion, telefono) por logs "
               "con contenido sin redactar",
     "probabilidad": 2,  # bajo porque ya se registra solo huella y longitud
     "impacto": 5,
     "mitigacion": "Logs con huella/longitud en vez de contenido (Bloque 31, "
                   "src/logging_rag.py)",
     "supervision": "Aprobacion explicita para quien pueda leer los logs"},
    {"riesgo": "Dataset de tuning desbalanceado que sesga las respuestas de la "
               "personalizacion",
     "probabilidad": 2,
     "impacto": 3,
     "mitigacion": "Chequeo de balance por categoria antes de enviar (Bloque 29, "
                   "src/dataset_tuning.py)",
     "supervision": "No aplica (MEDIO)"},
    {"riesgo": "Modelo de embeddings queda deprecado sin aviso y rompe la recuperacion",
     "probabilidad": 2,
     "impacto": 4,
     "mitigacion": "Verificacion previa del modelo y revision de documentacion "
                   "(Bloque 28, src/preflight.py)",
     "supervision": "No aplica (MEDIO)"},
]

for r in mis_riesgos:
    r["puntaje"] = puntaje_riesgo(r["probabilidad"], r["impacto"])
    r["categoria"] = categoria_riesgo(r["puntaje"])
    r["al_limite"] = esta_en_el_limite(r["probabilidad"], r["impacto"])


if __name__ == "__main__":
    for r in sorted(mis_riesgos, key=lambda x: -x["puntaje"]):
        marca = "[AL LIMITE]" if r["al_limite"] else ""
        print(f"{r['categoria']:8} ({r['puntaje']:2}) - {r['riesgo']} {marca}")
        if r["categoria"] in ("ALTO", "CRITICO"):
            print(f"{'':14}supervision: {r['supervision']}")

    print()
    for r in mis_riesgos:
        if r["al_limite"]:
            print("revisar con otra persona:", r["riesgo"])

    # Reglas de la actividad
    assert len(mis_riesgos) >= 5
    assert any(r["categoria"] in ("ALTO", "CRITICO") for r in mis_riesgos)
    assert all(r["supervision"] and not r["supervision"].startswith("No aplica")
               for r in mis_riesgos if r["categoria"] in ("ALTO", "CRITICO"))
