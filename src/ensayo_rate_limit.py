"""
Ensayo de rate limit (Bloque 13): dispara varias consultas seguidas, sin espera
entre ellas, para provocar un 429 real y observar el backoff y el costo.

Usa la API real y gasta tokens: python src/ensayo_rate_limit.py [n_peticiones]
"""
import sys

import cliente


def main(n_peticiones: int = 10) -> None:
    for i in range(n_peticiones):
        try:
            respuesta = cliente.consultar_modelo(f"Pregunta de prueba número {i}")
            print(f"Respuesta {i}: {respuesta[:40]}...")
        except RuntimeError as error:
            print(f"Respuesta {i} falló definitivamente: {error}")
    print(f"Costo total del ensayo: ${cliente.costo_total_sesion:.5f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
