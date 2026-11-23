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

## Cliente modular (`src/cliente.py`)

`consultar_modelo` es la única función pública; por dentro orquesta:

| Función | Qué hace |
|---|---|
| `con_reintento` | Reintenta solo ante `TimeoutError`, con backoff exponencial (2, 4, 8 s...), techo de 30 s y jitter de hasta 10 %. |
| `registrar_costo` | Lee `usageMetadata.totalTokenCount`, estima el costo y lo acumula en `costo_total_sesion`. Solo se llama tras una respuesta exitosa. |
| `consultar_modelo` | Convierte el `TimeoutError` agotado en `RuntimeError`; un `ValueError` (credencial) se propaga sin reintentar. |

`COSTO_POR_1000_TOKENS` es un valor referencial: ajústalo al precio real del modelo.

Las pruebas (`tests/test_cliente.py`, 18 casos) cubren `enviar_peticion`, `con_reintento`, `registrar_costo` y `consultar_modelo` con mocks de `requests.post` y `time.sleep`.

## Pipeline de texto (`src/pipeline_texto.py`)

Deja el texto en un formato comparable antes de medir las salidas del cliente:

| Función | Qué hace |
|---|---|
| `limpiar_texto` | Minúsculas, sin puntuación y sin espacios repetidos. Lanza `TypeError` si no recibe `str`. |
| `tokenizar` | Separa el texto limpio en una lista de palabras. |
| `procesar_texto` | Junta las dos anteriores para no olvidar ninguna. |
| `vectorizar` | Cuenta cuántas veces aparece cada token (bolsa de palabras). |
| `coincidencia` | Proporción de palabras de la referencia presentes en la respuesta; devuelve 0.0 si la referencia queda vacía. |

`src/evaluar_pipeline.py` consulta al modelo con tres preguntas sobre gas (qué es el GLP, olor a gas, mangueras), las compara con una referencia propia y guarda la coincidencia sobre texto crudo y procesado en `prompts/registro_pipeline.json`. Resultado: 87.5 % → 93.8 %, 26.7 % → 33.3 % y 56.2 % → 56.2 %. La métrica no distingue orden ni repeticiones, así que no reemplaza leer la respuesta.

Las pruebas (`tests/test_pipeline_texto.py`, 11 casos) no usan red ni mocks.

## Chain de tres pasos con LangChain (`src/cadena_tres_pasos.py`)

Atiende un mensaje de cliente encadenando tres `PromptTemplate`, cada uno con una responsabilidad:

1. `plantilla_clasificar`: ubica el mensaje en un tema (pedido, cotizacion, reclamo u otro).
2. `plantilla_redactar`: escribe un borrador según ese tema, usando solo el catálogo.
3. `plantilla_revisar`: corrige el tono y quita promesas sin respaldo.

`construir_cadena(modelo)` recibe el modelo como parámetro y devuelve la chain sin ejecutarla, así las pruebas (`tests/test_cadena_tres_pasos.py`, 5 casos) usan un mock y no gastan tokens. Para correrla con la API: `python src/cadena_tres_pasos.py`.

Ejemplo de corrida real (reclamo por válvula dañada y consulta de precio del cilindro de 45 kg):

> Lamentamos el inconveniente con tu cilindro de 15 kg; gestionaremos la solicitud a la brevedad. El cilindro de 45 kg tiene un valor de $75.000. Quedamos a tu disposición para coordinar el retiro y la nueva entrega.

`gemini-3.5-flash-lite` usa valores de muestreo fijos, por eso la chain no fija `temperature`. La revisión del paso 3 todavía deja pasar promesas de plazo ("a la brevedad"), una mejora pendiente del prompt.

## Enrutamiento y manejo de errores (`src/enrutamiento.py`)

Clasifica el mensaje (pedido, cotizacion, reclamo u otro) y lo envía a una ruta con su propio prompt; una categoría desconocida cae en la ruta `otro`. Protecciones ante fallos:

- **Por ruta:** cada ruta usa `with_fallbacks([respuesta_generica])`; si el modelo falla, el cliente recibe un texto genérico ("un miembro de nuestro equipo te va a responder pronto") en vez de una excepción.
- **Flujo completo:** `procesar_mensaje_seguro(cadena, mensaje)` envuelve `.invoke()` en `try/except`, registra el error con `logger.exception` (incluye traceback) y devuelve un mensaje seguro. Cubre fallos fuera de las rutas, como la clasificación.

Pruebas sin red: `tests/test_enrutamiento.py` (clasificación y bifurcación, incluida la ruta por defecto) y `tests/test_orquestacion.py` (fallback de ruta, fallo en la clasificación, registro del error). Se corren con `python -m pytest tests -v`.

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
- Resultado: el proyecto corre de punta a punta sin intervención manual y las 8 pruebas pasan sin problemas.

## Registro del ensayo de rate limit

- Fecha: 2026-10-27
- Peticiones enviadas: 10
- Petición donde apareció el primer 429: No se alcanzo el limite de uso
- Esperas observadas: Ninguna (no hubo reintentos)
- Costo total del ensayo: $0.00091
- Resultado: las 10 peticiones terminaron con éxito a la primera; el registro de costo acumuló correctamente en cada operación

## Agente con herramientas (`src/agente_con_herramientas.py`)

A diferencia de la chain, aquí el modelo decide qué acción tomar. El agente (`create_tool_calling_agent` + `AgentExecutor`) tiene dos herramientas con `@tool`:

| Herramienta | Cuándo se usa |
|---|---|
| `consultar_estado_pedido` | El cliente pregunta dónde está su pedido (por número, ej. GAS-1001). |
| `calcular_costo_pedido` | El cliente pregunta cuánto cuesta cierta cantidad de cilindros de un tamaño. |

Ambas devuelven texto, también ante errores (pedido inexistente, cilindro que no existe), para que el agente pueda seguir razonando en vez de caerse. `return_intermediate_steps=True` permite verificar qué herramienta eligió.

`python src/agente_con_herramientas.py` hace tres pruebas manuales con la API y confirma en `intermediate_steps` que cada pregunta usa la herramienta correcta, y que una pregunta general no usa ninguna. El prompt le pide no inventar datos que no tenga (teléfonos, correos), porque sin esa instrucción los inventaba.

## Herramienta personalizada y memoria (Bloque 22)

Sobre el mismo agente se agregaron dos piezas:

- **Herramientas con `args_schema` (Pydantic):** cada parámetro tiene su propia descripción y se valida antes de ejecutar la función. `consultar_estado_pedido` ahora se llama `consultar_estado_pedido_con_historial` (nombre explícito, el que sale en la traza) y recibe `numero_pedido` e `incluir_historial` (por defecto `False`). `calcular_costo_pedido` también usa `args_schema`.
- **Memoria entre turnos:** `crear_agente_con_memoria` envuelve el ejecutor con `RunnableWithMessageHistory`. El prompt tiene `chat_history` antes del mensaje humano y `agent_scratchpad` después. Cada llamada necesita `config={"configurable": {"session_id": ...}}`; sesiones distintas tienen historiales separados.
- **Salida normalizada a texto:** Gemini devuelve `output` como lista de bloques. Si esa lista se guarda tal cual en el historial, el segundo turno falla al reconstruir los mensajes. Por eso el ejecutor se encadena con una función que convierte la salida a texto antes de que llegue a la memoria.

Limitaciones: el historial vive en un diccionario en memoria (se pierde al reiniciar) y crece con cada turno, lo que aumenta el costo por llamada. `RunnableWithMessageHistory` imprime un `LangChainDeprecationWarning`; es un aviso, no un error.

Pruebas sin red en `tests/test_agente_herramientas.py` (herramientas, validación Pydantic, memoria de dos turnos, aislamiento entre sesiones y salida en bloques de Gemini). `python src/agente_con_herramientas.py` hace las pruebas reales con la API.
## Límites de autonomía y supervisión humana (Bloque 23)

Se agregó una tercera herramienta, `generar_reembolso`, de **riesgo alto** (mueve dinero de forma irreversible), y tres piezas para controlarla:

- **Aprobación humana (`src/supervision.py`):** `esperar_aprobacion` pide `s/n` por consola con límite de tiempo (300 s). Solo `s` aprueba; timeout o falta de entrada cuentan como rechazo. Usa un hilo con `Event` en vez de `select()` de la lección, porque `select()` no funciona sobre stdin en Windows. `registrar_aprobacion` guarda cada decisión.
- **Trazas (`src/trazas.py`):** `registrar_traza` agrega cada interacción a `trazas_agente.jsonl`; `marcar_repeticiones_sospechosas` señala sesiones donde la misma herramienta se llamó dos veces seguidas.
- **Documento de límites:** `docs/limites_autonomia_agente.md` (riesgo por herramienta, cuáles piden aprobación, revisión de trazas y plan ante comportamiento inesperado).

`python src/agente_con_herramientas.py --reembolso` agrega una cuarta prueba real que pide aprobación por consola. Sin la bandera, el script no pide nada. El reembolso está simulado (no llama a un sistema de pagos). Pruebas sin red en `tests/test_supervision_trazas.py`.

## Logging estructurado e inyección de prompt (Bloque 31)

`src/logging_rag.py` instrumenta el flujo RAG con tres piezas:

- **Logs JSON con `trace_id`:** un evento por línea; el `trace_id` vive en un `contextvar` que se fija en cada consulta (no es global), así que dos consultas no se mezclan. Con solo leer los logs se reconstruye cuántos documentos se recuperaron, cuántos se descartaron y cuánto costó la llamada al modelo.
- **Registro de consumo:** `registrar_consumo` loguea `input/output/total_tokens` de `usage_metadata` con el `trace_id` de su consulta (con `.get()`, no rompe si el campo falta).
- **Filtro de inyección:** descarta documentos recuperados que coinciden con patrones sospechosos y lo loguea (`documento_descartado_por_inyeccion`). Se combina con roles `System`/`Human` separados y contexto delimitado en `<contexto>`.

Gobernanza: los logs guardan longitud y huella (sha256 truncado) de la pregunta y los documentos, nunca su contenido. El filtro es una lista negra: no detecta sinónimos ni otros idiomas, es una capa entre varias, no una garantía.

`python src/logging_rag.py` corre la demo sin red; `python src/logging_rag.py --real "pregunta"` usa el índice y Gemini reales. Pruebas sin red en `tests/test_logging_rag.py`.

## Gate 2: servicio RAG integrado (`src/servicio_rag.py`)

Un solo flujo que reúne las piezas del Módulo 2: índice persistido, recuperación con cita, filtro de inyección, logging con `trace_id`, latencia y costo, versionado de prompts y supervisión humana.

### Instalar y ejecutar de punta a punta

Con el entorno virtual activo y las dependencias instaladas (ver *Instalación*):

```powershell
python verificar_entorno.py                  # comprueba paquetes, .env e índice
python src/servicio_rag.py                   # indexa (1a vez), consulta y corre la supervisión
python src/servicio_rag.py "el despacho a domicilio tiene costo" --decision aprobar
```

- **Modo simulado (por defecto):** embeddings léxicos locales y un modelo simulado; no necesita clave ni red. El índice queda en `vectorstore_sim/` y la salida lo marca como simulado.
- **Modo real:** `python src/servicio_rag.py "pregunta" --real` usa Gemini y el índice `vectorstore/`. Requiere `GEMINI_API_KEY` en el `.env`; el servicio crea o actualiza ese índice por su cuenta (o puedes crearlo antes con `python src/indexar_corpus.py`).
- **Supervisión:** sin `--decision`, el servicio pide `s/n` por consola antes de activar la versión del prompt; `--decision aprobar|rechazar` lo resuelve sin interacción.

Cada consulta devuelve `respuesta` (con línea `Fuentes:`), `fuentes`, `trace_id`, `metricas` (tiempos por etapa, tokens y costo estimado) y `auditoria` (un evento por etapa).

### Qué cubre cada dimensión de la rúbrica

| Dimensión | Dónde está |
|---|---|
| Pipeline RAG funcional | `src/servicio_rag.py`; índice persistido y actualización incremental por huella en `sincronizar_indice` (`indice_creado` / `indice_actualizado` / `indice_reutilizado`) |
| Recuperación y citación | Contexto numerado `[N]` y fuentes en la respuesta; sin cita válida no se entrega la respuesta. Métricas en `src/evaluacion_recuperacion.py` y `resultados_evaluacion.txt` (precisión 0.308, recall 1.000 con k=3) |
| Costo, latencia y checklist | `latencia_y_costo` por consulta; corridas reales en `registros_latencia_costo.jsonl` (`src/registro_rag.py`) |
| Personalización justificada | `docs/decision_personalizacion.md` (RAG, con matriz de puntaje sobre este caso) |
| Observabilidad | `src/logging_rag.py`: logs JSON con `trace_id` por consulta y registro de consumo |
| Seguridad, versionado y gobernanza | Filtro de inyección (`src/logging_rag.py`), versiones de prompt (`src/registro_prompts.py`), supervisión con `interrupt()`/`Command` (`src/grafo_supervision.py`) y matriz de riesgos (`src/matriz_riesgos.py`) |

Los logs guardan longitudes, conteos y huellas (sha256 truncado), nunca la pregunta ni el texto de los documentos. El filtro de inyección es una lista negra: no detecta sinónimos ni otros idiomas.

### Pruebas y autoevaluación

```powershell
python -m pytest test_gate2.py -v            # los 4 criterios no compensables + índice, inyección y trace_id
python -m pytest tests -v                    # pruebas del resto del proyecto
python src/autoevaluacion_gate2.py           # promedio ponderado y criterios no compensables
python src/matriz_riesgos.py                 # matriz de riesgos
```

Los cuatro criterios no compensables: el pipeline corre sin excepciones, cada respuesta cita su fuente, los logs no exponen contenido crudo y la supervisión humana pausa y reanuda de verdad. `test_gate2.py` los comprueba sobre el servicio real, con un índice temporal.

### Limitaciones conocidas

- El modo simulado sirve para ensayar el pipeline; su calidad de respuesta no es la del modelo real.
- `InMemorySaver` guarda el estado de la supervisión solo mientras vive el proceso.
- El corpus no tiene un documento de medios de pago, por lo que esa consulta no se puede responder (ver `docs/decision_personalizacion.md`).

### Registro del ensayo funcional del Gate 2

- Fecha: 2026-11-23
- Procedimiento: venv nuevo, `pip install -r requirements.txt`, `python verificar_entorno.py`, `python src/servicio_rag.py` (índice borrado antes de la primera corrida), segunda corrida con `--decision rechazar`, `python -m pytest test_gate2.py -v` y `python -m pytest tests -q`.
- Resultado: `test_gate2.py` 7/7 y `tests/` 99/99 pasan. Primera corrida: `indice_creado` (6 chunks); segunda: `indice_reutilizado`. La respuesta cita su fuente, los eventos comparten un `trace_id` por consulta y la supervisión pausa y reanuda con aprobación y con rechazo.
- Limitación: este ensayo corrió en modo **simulado** (sin `GEMINI_API_KEY`). La corrida real con Gemini (`python src/servicio_rag.py "pregunta" --real`) queda por documentar aquí antes de entregar.
