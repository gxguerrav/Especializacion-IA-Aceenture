"""Lee registros_latencia_costo.jsonl e imprime lo esencial de cada corrida (Bloque 28).

Uso:
    python src/leer_registros.py
"""

import json
from pathlib import Path

ARCHIVO_REGISTROS = Path(__file__).resolve().parent.parent / "registros_latencia_costo.jsonl"


def main():
    with open(ARCHIVO_REGISTROS, encoding="utf-8") as f:
        for linea in f:
            r = json.loads(linea)
            tokens_entrada = r["tokens"]["input_tokens"] if r["tokens"] else None
            t = r["tiempos_ms"]
            etapas = " ".join(f"{etapa}={ms}" for etapa, ms in t.items())
            print(
                f"k={r['k']} input_tokens={tokens_entrada} total={r['tiempo_total_ms']} ms "
                f"({etapas}) {r['pregunta'][:35]}"
            )


if __name__ == "__main__":
    main()
