"""Bloque 30 (Core): metodo de decision de personalizacion para el asistente de gas.

Paso 1: puntua RAG / Fine-tuning completo / PEFT con cinco respuestas sustentadas
        en evidencia del propio repositorio.
Paso 2: genera el esqueleto de decision_personalizacion.md (sin pisar el documento
        ya redactado a mano si existe).

Uso:  python decision.py
"""

import os


def recomendar_estrategia(respuestas):
    puntos = {"RAG": 0, "Fine-tuning completo": 0, "PEFT": 0}

    if respuestas["informacion_cambia_seguido"]:
        puntos["RAG"] += 3
    if respuestas["problema_de_formato_o_tono"]:
        puntos["PEFT"] += 2
        puntos["Fine-tuning completo"] += 1
    if respuestas["dataset_grande_y_de_calidad"]:
        puntos["Fine-tuning completo"] += 2
        puntos["PEFT"] += 1
    if respuestas["presupuesto_limitado_o_iterar_rapido"]:
        puntos["RAG"] += 2
        puntos["PEFT"] += 1
    if respuestas["necesita_multiples_variantes"]:
        puntos["PEFT"] += 2

    # Se conservan TODAS las tecnicas empatadas, no solo la primera que ve max().
    maximo = max(puntos.values())
    ganadoras = [tecnica for tecnica, p in puntos.items() if p == maximo]
    return puntos, ganadoras


def estimar_costo_de_etiquetar(num_ejemplos, minutos_por_ejemplo, costo_por_hora):
    horas = (num_ejemplos * minutos_por_ejemplo) / 60
    costo = horas * costo_por_hora
    return horas, costo


# Evidencia del repositorio (ver docs de cada archivo citado).
respuestas_mi_caso = {
    # Corpus de 6 documentos fijos en src/indexar_corpus.py (catalogo de 4 precios,
    # despacho gratis, pasos del pedido, reembolsos). No hay evidencia de cambios
    # mensuales: los commits que lo tocan son creacion/ampliacion, no actualizaciones.
    "informacion_cambia_seguido": False,
    # prompts/registro_resultados.json: 9 de 9 llamadas con JSON valido (3 pasos x 3
    # intentos) usando response_schema. 0 incumplimientos < 3 de 20 (umbral 15 %).
    "problema_de_formato_o_tono": False,
    # src/dataset_tuning.py: 15 ejemplos etiquetados, menos de 200 -> False.
    "dataset_grande_y_de_calidad": False,
    # Cuenta de Gemini con cuota limitada: tests/test_consistencia.py ya maneja 429/503
    # con pausas de 13 s. Supuesto: costeo como maximo 2 intentos de entrenamiento.
    "presupuesto_limitado_o_iterar_rapido": True,
    # Un solo asistente de gas, sin versiones por cliente, idioma o linea.
    "necesita_multiples_variantes": False,
}

if any(valor is None for valor in respuestas_mi_caso.values()):
    raise SystemExit("Completa las cinco respuestas con True o False antes de continuar.")

puntos, ganadoras = recomendar_estrategia(respuestas_mi_caso)
print(puntos)
print("candidatas:", ganadoras)

# Sensibilidad: que pasa si cambio una sola respuesta.
for clave in respuestas_mi_caso:
    variante = dict(respuestas_mi_caso)
    variante[clave] = not variante[clave]
    _, ganadoras_v = recomendar_estrategia(variante)
    cambio = "CAMBIA" if set(ganadoras_v) != set(ganadoras) else "igual"
    print(f"{clave} -> {variante[clave]}: {ganadoras_v} [{cambio}]")

# Costo de cerrar la brecha de datos si se quisiera PEFT (200 ejemplos, 5 min c/u, $25/h).
faltan = 200 - 15
horas, costo = estimar_costo_de_etiquetar(faltan, 5, 25)
print(f"llegar a 200 ejemplos: faltan {faltan}, {horas:.1f} horas, aprox ${costo:.2f}")


def generar_esqueleto_decision(problema, puntos, ganadoras):
    empate = len(ganadoras) > 1
    lineas = ["# Decision de personalizacion", "", "## 1. El problema", problema, ""]
    lineas.append("## 2. Resultado del metodo de decision")
    for tecnica, p in sorted(puntos.items(), key=lambda x: -x[1]):
        lineas.append(f"- {tecnica}: {p} puntos")
    if empate:
        lineas.append("")
        lineas.append(f"**Empate entre: {', '.join(ganadoras)}**")
    lineas.append("")
    lineas.append("## 3. Tecnica elegida y por que")
    if empate:
        lineas.append(
            "[COMPLETAR: el puntaje no resolvio el empate solo -- "
            "justifica aqui con criterio propio]"
        )
    else:
        lineas.append(f"[COMPLETAR: por que {ganadoras[0]} responde mejor a este caso]")
    lineas.append("")
    lineas.append("## 4. Que necesitarias para ejecutarla")
    lineas.append("[COMPLETAR: corpus faltante, o cantidad de ejemplos etiquetados que faltan]")
    return "\n".join(lineas)


esqueleto = generar_esqueleto_decision(
    "El asistente debe responder con datos vigentes del negocio (precios, despacho, "
    "reembolsos) sin inventarlos.",
    puntos,
    ganadoras,
)

ARCHIVO = "decision_personalizacion.md"
if os.path.exists(ARCHIVO):
    print(f"{ARCHIVO} ya existe: no se sobrescribe (borralo para regenerar el esqueleto).")
else:
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(esqueleto)
    print(f"esqueleto escrito en {ARCHIVO}")
