# Especialización en Desarrollo con IA Generativa (Accenture)

Repositorio único del Diplomado. En este momento contiene la miniaplicación del **Módulo 1 (Gate 1)**: un asistente de ventas de gas en cilindros que usa la API de Gemini. Dado el mensaje de un cliente, el asistente identifica qué quiere, extrae los datos del pedido y le responde, siempre con salida JSON validada.

## Requisitos

- Python 3.10 o superior
- Git
- Una API key de Gemini (Google AI Studio)

## Instalación

1. Clona el repositorio y entra a la carpeta:
   ```powershell
   git clone https://github.com/gxguerrav/Especializacion-IA-Aceenture.git
   cd Especializacion-IA-Aceenture
   ```
2. Crea y activa el entorno virtual:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   En macOS, Linux o WSL:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instala las dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
4. Crea tu archivo `.env` a partir de la plantilla y completa tu llave:
   ```powershell
   Copy-Item .env.example .env
   ```
   En macOS, Linux o WSL: `cp .env.example .env`. Luego abre `.env` y escribe tu llave en `GEMINI_API_KEY=""`.

El archivo `.env` está en `.gitignore` y nunca se sube al repositorio.

## Cómo ejecutar

Conversación con el asistente (escribe `salir` para terminar):

```powershell
python src/main.py
```

Un solo mensaje, sin interacción:

```powershell
python src/main.py "Quiero 2 cilindros de 15 kilos, mi dirección es Av. Los Leones 1234, Providencia."
```

Ejemplo de salida:

```
  [intención: comprar (0.99)]
  [pedido: 2 x 15 kg -> Av. Los Leones 1234, Providencia]
Asistente: ¡Perfecto! El total por 2 cilindros de 15 kg es $54.000 con despacho gratuito. ¿Deseas confirmar tu pedido?
  [total: $54.000]
```

Otros comandos:

```powershell
python -m unittest discover tests      # pruebas automatizadas (no usan la API)
python prompts/test_consistencia.py    # mide qué tan consistente es el JSON de cada prompt (usa la API)
```

Si la API responde con un error de cuota o "alta demanda" (429 o 503), es temporal y viene de Google: el programa muestra un mensaje claro, sin trazas. Vuelve a intentar en un momento.

## Cómo funciona

Por cada mensaje del cliente, `src/main.py` encadena tres prompts del banco:

1. `clasificar_intencion`: comprar, cotizar, consultar pedido, reclamo u otro.
2. `extraer_pedido`: tipo de cilindro, cantidad, dirección y datos faltantes (solo si quiere comprar o cotizar).
3. `respuesta_de_venta`: mensaje para el cliente, total y siguiente paso, con el catálogo de precios.

El módulo `src/consumir_gemini.py` separa el consumo de la API en funciones con una sola responsabilidad:

| Función | Qué hace |
|---|---|
| `armar_peticion` | Valida la entrada y la llave, y arma la URL y el cuerpo (prompt de sistema aparte del mensaje del usuario, y esquema JSON). |
| `enviar_peticion` | Hace el POST con timeout y traduce fallos de conexión a mensajes claros. |
| `extraer_texto` | Saca el texto de la respuesta, o informa el error que devolvió la API. |
| `parsear_respuesta_json` | Limpia bloques markdown, valida que sea JSON y que traiga las claves esperadas. |

## Banco de prompts y consistencia

Los prompts viven en `prompts/banco.py`, cada uno con su prompt de sistema, su mensaje de ejemplo, las claves esperadas y su esquema de respuesta. `prompts/test_consistencia.py` ejecuta cada prompt 3 veces y guarda el resultado en `prompts/registro_resultados.json`: los tres prompts dieron 3/3 respuestas válidas.

## Estructura de carpetas

- `src/` : código fuente (`main.py` y `consumir_gemini.py`).
- `prompts/` : banco de prompts, test de consistencia y su registro de resultados.
- `docs/` : diagrama de arquitectura, decisión de modelo y evidencias.
- `tests/` : pruebas automatizadas.
- `Tareas/` : entregables y formularios de las distintas unidades.
- `Modulo_1/` : material específico del módulo 1.
- `requirements.txt` : dependencias de Python.
- `.env.example` : plantilla de variables de entorno, sin valores reales.
- `.gitignore` : excluye el entorno virtual, `.env`, cachés y logs.

## Documentación

- Diagrama de arquitectura: `docs/diagrama_arquitectura.drawio.png`
- Decisión de modelo (`gemini-3.5-flash-lite`): `docs/decision-arquitectura.md`

## Seguridad

- Ninguna credencial va escrita en el código ni en archivos versionados. La llave se lee de `GEMINI_API_KEY` en el `.env` y se envía por header, no en la URL.
- `.env` está excluido con `.gitignore`; `.env.example` solo trae la plantilla vacía.

## Registro del ensayo de instalación limpia

- Fecha: 2026-10-22
- Procedimiento: clon en carpeta nueva, venv nuevo, `pip install -r requirements.txt`, `.env` desde `.env.example`, ejecución de la app y de las pruebas.
- Encontrado: sin hallazgos. `requirements.txt` está completo, no hay rutas absolutas en el código y `.env` no aparece en `git status` ni en `git ls-files`.
- Historial: `git log --all --oneline -- .env` muestra dos commits (agregado y retirado al crear el `.gitignore`), pero el archivo estaba vacío (0 bytes) cuando se agregó, así que nunca hubo una credencial real en el historial.
- Resultado: el proyecto corre de punta a punta sin intervención manual y las 8 pruebas pasan.
