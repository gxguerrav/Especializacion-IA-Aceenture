"""
Métricas de evaluación de texto generado (Bloque 16).

"""
from collections import Counter

from pipeline_texto import procesar_texto


def contar_coincidencias(tokens_referencia: list[str], tokens_respuesta: list[str]) -> int:
    """Cuenta las coincidencias entre referencia y respuesta, respetando repeticiones."""
    interseccion = Counter(tokens_referencia) & Counter(tokens_respuesta)
    return sum(interseccion.values())


def calcular_precision_cobertura_f1(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> dict[str, float]:
    """Calcula precisión, cobertura y F1 de dos listas de tokens."""
    if not tokens_respuesta or not tokens_referencia:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}
    coincidencias = contar_coincidencias(tokens_referencia, tokens_respuesta)
    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)
    if precision + cobertura == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * cobertura / (precision + cobertura)
    return {"precision": precision, "cobertura": cobertura, "f1": f1}


def calcular_metricas(texto_referencia: str, texto_respuesta: str) -> dict[str, float]:
    """Procesa ambos textos y calcula precisión, cobertura y F1 en una sola llamada."""
    return calcular_precision_cobertura_f1(
        procesar_texto(texto_referencia),
        procesar_texto(texto_respuesta),
    )


def resumir_metricas(resultados: list[dict]) -> dict[str, float]:
    """Promedia precisión, cobertura y F1 de una lista de resultados."""
    if not resultados:
        return {"precision_promedio": 0, "cobertura_promedio": 0, "f1_promedio": 0}
    n = len(resultados)
    return {
        "precision_promedio": sum(r["precision"] for r in resultados) / n,
        "cobertura_promedio": sum(r["cobertura"] for r in resultados) / n,
        "f1_promedio": sum(r["f1"] for r in resultados) / n,
    }


def ordenar_peores_casos(resultados: list[dict]) -> list[dict]:
    """Ordena los resultados por F1 ascendente: los peores primero."""
    return sorted(resultados, key=lambda r: r["f1"])
