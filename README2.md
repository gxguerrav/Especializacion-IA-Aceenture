# Gate 2: servicio IA modular con RAG

Este documento complementa el `README.md` (que cubre el Módulo 1 y los bloques anteriores) y reúne todo lo que pide el Gate 2: cómo instalar, indexar un corpus y correr una consulta de punta a punta, y dónde está la evidencia de cada dimensión de la rúbrica.

El servicio es un asistente de atención de clientes de una empresa de gas en cilindros. Responde con datos del negocio (catálogo, despacho, pedidos, reembolsos), cita de qué documento sale cada dato y deja trazabilidad de cada consulta.

## 1. Requisitos

- Python 3.10 o superior
- Git
- Opcional: una API key de Gemini (solo para el modo real)

## 2. Instalación

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

En macOS, Linux o WSL: `python3 -m venv venv`, `source venv/bin/activate` y `cp .env.example .env`.

Para el modo real, escribe tu llave en `.env` (`GEMINI_API_KEY=""`). El `.env` está en `.gitignore`; se puede comprobar con `git check-ignore .env`. El modo simulado no necesita llave.

Comprueba el entorno antes de correr:

```powershell
python verificar_entorno.py
```

Muestra la versión de cada paquete, si la variable está definida (nunca imprime la clave) y si existe un índice. Termina con código 1 si falta algo obligatorio.

## 3. Cómo indexar y consultar de punta a punta

```powershell
python src/servicio_rag.py
python src/servicio_rag.py "el despacho a domicilio tiene costo" --decision aprobar
python src/servicio_rag.py "cuanto cuesta el cilindro de 15 kilos" --real
```

| Modo | Qué usa | Índice | Necesita |
|---|---|---|---|
| Simulado (por defecto) | Embeddings léxicos locales y un modelo simulado | `vectorstore_sim/` | Nada |
| Real (`--real`) | Gemini (embeddings y chat) | `vectorstore/` | `GEMINI_API_KEY` |

- **Indexación:** en la primera consulta el servicio crea el índice (`indice_creado`); en las siguientes lo reutiliza (`indice_reutilizado`). No se reconstruye en cada corrida. En modo real también se puede crear antes con `python src/indexar_corpus.py`.
- **Actualización incremental:** `sincronizar_indice` compara la huella (sha256 truncado) de cada chunk. Solo agrega los nuevos, reescribe los cambiados y borra los que ya no están en el corpus (`indice_actualizado`).
- **Supervisión humana:** al final, el servicio pausa antes de activar una versión nueva del prompt y pregunta `s/n`. Solo `s` aprueba; un timeout de 300 s o cualquier otra respuesta cuenta como rechazo. Con `--decision aprobar|rechazar` se resuelve sin interacción.

Cada consulta devuelve:

| Campo | Contenido |
|---|---|
| `respuesta` | Texto del modelo más una línea `Fuentes: [N] documento` |
| `fuentes` | Lista de documentos citados |
| `trace_id` | Identificador único de la consulta |
| `metricas` | Tiempo por etapa (embed, búsqueda, generación), tokens y costo estimado |
| `auditoria` | Un evento por etapa, todos con el mismo `trace_id` |

## 4. Flujo del pipeline

1. **Indexar o reutilizar:** corpus, chunking recursivo (250 caracteres, solape de 40) e índice Chroma persistido.
2. **Recuperar:** embedding de la pregunta y búsqueda vectorial de los k chunks más cercanos (k=3 por defecto).
3. **Filtrar inyección:** se descartan los documentos que coinciden con patrones sospechosos.
4. **Sin contexto confiable:** si no queda ningún documento limpio, el servicio responde "No tengo informacion suficiente y verificada" sin llamar al modelo.
5. **Generar:** roles System/Human separados y contexto numerado dentro de `<contexto>`.
6. **Citar:** se resuelven los `[N]` de la respuesta contra los documentos. Si no hay ninguna cita válida, no se entrega la respuesta.
7. **Registrar:** latencia por etapa, consumo de tokens y costo estimado.

## 5. Evidencia por dimensión de la rúbrica

| Dimensión (peso) | Dónde está la evidencia |
|---|---|
| Pipeline RAG funcional (25 %) | `src/servicio_rag.py`; `indexar_corpus.py` e índice persistido e incremental (`sincronizar_indice`); pruebas en `test_gate2.py` |
| Calidad de recuperación y citación (15 %) | Citas `[N]` resueltas por `resolver_citas` (`src/recuperacion.py`); métricas en `src/evaluacion_recuperacion.py` y `resultados_evaluacion.txt` |
| Costo, latencia y checklist (10 %) | Evento `latencia_y_costo` por consulta; corridas reales en `registros_latencia_costo.jsonl` (`src/registro_rag.py`) |
| Personalización justificada (15 %) | `docs/decision_personalizacion.md`: matriz de puntaje entre RAG, PEFT y fine-tuning sobre este caso; resultado RAG |
| Observabilidad y trazabilidad (15 %) | `src/logging_rag.py`: logs JSON, `trace_id` en un `contextvar`, registro de consumo |
| Seguridad, versionado y gobernanza (20 %) | Filtro de inyección (`src/logging_rag.py`), versiones de prompt (`src/registro_prompts.py`), supervisión con `interrupt()`/`Command` (`src/grafo_supervision.py`) y matriz de riesgos (`src/matriz_riesgos.py`) |

### Métricas de recuperación (corpus propio, k=3)

Medidas con 13 preguntas sobre el corpus de 6 documentos (`resultados_evaluacion.txt`): **recall promedio 1.000** y **precisión promedio 0.308**. La precisión es baja porque cada pregunta tiene un solo documento relevante y se recuperan 3. El siguiente ajuste es probar k=1 o k=2. La pregunta sobre pago con tarjeta no tiene respuesta en el corpus (precisión y recall 0), lo que muestra que falta un documento de medios de pago.

### Decisión de personalización

RAG, con 2 puntos frente a 1 de PEFT y 0 de fine-tuning completo. Al modelo no le falta comportamiento sino información del negocio, y esa información vive en un corpus editable sin reentrenar. El margen es de un punto, así que la decisión es frágil; el supuesto más débil es el presupuesto. Detalle en `docs/decision_personalizacion.md`.

### Versionado de prompts

`src/registro_prompts.py` registra cada versión del prompt de sistema con huella, autor, fecha, nota y modelo validado, y calcula el diff entre versiones. Hay dos versiones: la original y la que agrega la instrucción anti-inyección (Bloque 31).

### Matriz de riesgos

`python src/matriz_riesgos.py` imprime la matriz: 6 riesgos propios con puntaje = probabilidad × impacto, y los cortes CRITICO ≥ 15, ALTO ≥ 9, MEDIO ≥ 4. Todo riesgo ALTO o CRITICO está conectado a un punto de supervisión humana concreto, y el script lo verifica con `assert`.

## 6. Los cuatro criterios no compensables

| Criterio | Cómo se cumple | Prueba |
|---|---|---|
| El pipeline corre sin excepciones | El flujo maneja contexto vacío y falta de cita con mensajes explícitos; `main()` captura errores de API sin Traceback | `test_1_pipeline_sin_excepciones` |
| Cada respuesta cita su fuente | La respuesta incluye `Fuentes:`; sin cita válida no se entrega | `test_2_respuesta_cita_fuente` |
| Sin contenido crudo sensible en logs | Los logs llevan solo longitudes, conteos y huellas | `test_3_logs_sin_contenido_crudo` |
| Supervisión humana real | `interrupt()` pausa el grafo y `Command(resume=...)` lo retoma con la decisión | `test_4_supervision_pausa_y_reanuda` |

```powershell
python -m pytest test_gate2.py -v
python -m pytest tests -v
python src/autoevaluacion_gate2.py
```

`test_gate2.py` corre sobre el servicio real en modo simulado con un índice temporal, e incluye tres pruebas extra: índice persistido e incremental, documento con inyección descartado y aislamiento del `trace_id` entre consultas. `autoevaluacion_gate2.py` calcula el promedio ponderado con mi estimación por dimensión y ejecuta los cuatro criterios de verdad.

## 7. Gobernanza y seguridad

- Ninguna credencial va en el código ni en archivos versionados; la llave se lee de `GEMINI_API_KEY` en el `.env`.
- Los logs no guardan la pregunta ni el texto de los documentos, solo longitud y huella.
- El filtro de inyección es una lista negra: es una capa entre varias, no una garantía. No detecta sinónimos ni otros idiomas.
- Los reembolsos y el despliegue de versiones de prompt requieren aprobación humana.

## 8. Limitaciones conocidas

- El modo simulado sirve para ensayar el pipeline; la calidad de su respuesta no es la del modelo real. Por ejemplo, ante la pregunta de precio puede citar `como_comprar` en lugar de `catalogo_precios`.
- `InMemorySaver` guarda el estado de la supervisión solo mientras vive el proceso.
- El corpus no tiene un documento de medios de pago.
- La precisión de recuperación (0.308) está pendiente de mejora con un k menor.

## 9. Registro del ensayo funcional

- Fecha: 2026-11-23
- Procedimiento: venv nuevo, `pip install -r requirements.txt`, `python verificar_entorno.py`, `python src/servicio_rag.py` con el índice borrado, segunda corrida con `--decision rechazar`, `python -m pytest test_gate2.py -v` y `python -m pytest tests -q`.
- Resultado: `test_gate2.py` 7/7 y `tests/` 99/99. La primera corrida creó el índice (6 chunks) y la segunda lo reutilizó. La respuesta cita su fuente, los eventos comparten un `trace_id` por consulta y la supervisión pausa y reanuda tanto con aprobación como con rechazo.
- **Corrida real con Gemini** (2026-11-23, `python src/servicio_rag.py "cuanto cuesta el cilindro de 15 kilos" --real --decision aprobar`):
  - Respuesta: "El cilindro de gas de 15 kg cuesta $27.000 [1]", con `Fuentes: [1] catalogo_precios`.
  - Tokens: 345 de entrada, 21 de salida, 366 en total; costo estimado US$0.000732.
  - Tiempos: embed 898 ms, búsqueda 1.8 ms, generación 47 989 ms (total 48.9 s). La generación fue lenta por la API, no por el servicio.
  - Índice: el log dice `indice_actualizado` con 6 actualizados porque el índice de `vectorstore/` se había creado con `indexar_corpus.py`, que no guardaba la huella; el servicio la agregó. Las siguientes corridas muestran `indice_reutilizado`.
  - Hallazgo corregido: Gemini devuelve el contenido como lista de bloques y la respuesta salió con ese texto crudo; se agregó `extraer_texto` y una prueba.
  - Supervisión: pausó y reanudó con `--decision aprobar`.

## 10. Mapa de archivos del Gate 2

| Archivo | Para qué sirve |
|---|---|
| `src/servicio_rag.py` | Servicio integrado |
| `src/logging_rag.py` | Logging con `trace_id`, consumo y filtro de inyección |
| `src/registro_prompts.py` | Versionado de prompts |
| `src/grafo_supervision.py` | Supervisión humana con `interrupt()` |
| `src/matriz_riesgos.py` | Matriz de riesgos |
| `src/autoevaluacion_gate2.py` | Autoevaluación |
| `test_gate2.py` | Pruebas de los criterios no compensables |
| `verificar_entorno.py` | Verificación del entorno |
| `docs/decision_personalizacion.md` | Decisión RAG, PEFT o fine-tuning |
