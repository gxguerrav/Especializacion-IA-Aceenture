# Decisión de personalización: asistente de ventas de gas en cilindros

## 1. El problema

El asistente debe responder con datos vigentes del negocio (precios del catálogo, despacho, pasos del pedido, política de reembolsos) sin inventarlos. El modelo ya entiende los mensajes de los clientes y devuelve el formato esperado: en `prompts/registro_resultados.json` las 9 llamadas (3 pasos × 3 intentos) devolvieron JSON válido, 0 incumplimientos. Lo que le falta es información propia del negocio, que no está en el modelo.

## 2. Resultado del método de decisión

Respuestas, cada una con su evidencia:

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿La información cambia seguido? | False | Corpus fijo de 6 documentos en `src/indexar_corpus.py`; sin evidencia de cambios mensuales. |
| ¿Problema de formato o tono? | False | 0 fallos de formato en 9 llamadas (umbral: 3 de 20). |
| ¿Dataset grande y de calidad? | False | 15 ejemplos etiquetados (`src/dataset_tuning.py`), menos de 200. |
| ¿Presupuesto limitado o iterar rápido? | True | Cuenta con cuota limitada (se manejan 429/503 en `tests/test_consistencia.py`); supuesto: costeo como máximo 2 intentos de entrenamiento. |
| ¿Múltiples variantes? | False | Un solo asistente, sin versiones por cliente, idioma o línea. |

Puntaje:

- RAG: 2 puntos
- PEFT: 1 punto
- Fine-tuning completo: 0 puntos

No hay empate: RAG sale mejor puntuada. Aun así el margen es de un punto y el resultado es frágil: al cambiar una sola respuesta (formato, dataset, presupuesto o variantes) el ganador cambia o se produce un empate. Solo cambiar "la información cambia seguido" no lo altera.

## 3. Técnica elegida y por qué

Elijo **RAG**. El puntaje da un ganador claro y coincide con el análisis cualitativo: al modelo no le falta comportamiento sino información (precios, política de reembolsos, estados del pedido), y esa información vive en un corpus que se puede editar sin reentrenar. Los costos de la lección anterior refuerzan la decisión: RAG no exige datos etiquetados (hoy hay solo 15 ejemplos y llegar a 200 costaría unas 15,4 horas, unos US$385 a 5 minutos por ejemplo y US$25 por hora), itera en segundos o minutos y reutiliza el vector store Chroma que ya está construido. Descarto PEFT y fine-tuning completo porque no hay un problema de formato que resolver y porque con 15 ejemplos sobreajustarían.

El supuesto más débil es el presupuesto (cuota limitada, máximo 2 intentos de entrenamiento). Si el negocio pudiera costear más intentos, el puntaje de RAG bajaría a 0 y habría que revisar la decisión.

## 4. Qué necesitaría para ejecutarla

- **Corpus:** hoy hay 6 documentos indexados. Falta **1 documento** (medios de pago), para un total de 7: en `resultados_evaluacion.txt` la consulta "aceptan pago con tarjeta de credito" tiene precisión y recall en 0,00 porque ningún documento la responde.
- **Calidad de recuperación:** el recall promedio es 1,000 pero la precisión promedio es 0,308 (k=3 sobre un corpus de 6 documentos, con 1 documento relevante por consulta). Siguiente ajuste: probar k=1 o k=2 y volver a medir.
- **Datos etiquetados:** 0 necesarios para RAG. Los 15 ejemplos de `src/dataset_tuning.py` quedan como respaldo; si en el futuro apareciera un problema de formato, faltarían 185 para llegar a 200 (unas 15,4 horas de etiquetado).
