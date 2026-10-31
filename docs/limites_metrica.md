# Límites de la métrica de evaluación

## Qué mide

Coincidencia de palabras entre una respuesta del asistente de gas y una referencia escrita por nosotros, contando repeticiones (precisión, cobertura y F1 de `src/metricas.py`). Mide parecido de vocabulario, no si la respuesta es correcta.

## Modos de falla conocidos

Cada punto sale de un caso de `revision_manual.json` (14 casos leídos a mano sobre `resultados_metricas.json`).

- **Respuestas correctas pero largas o parafraseadas puntúan muy bajo.** Las 5 respuestas con F1 más bajo eran correctas en lo factual: ninguna decía algo falso. Ejemplo: "¿Se puede acostar un cilindro para transportarlo?" obtuvo F1 0.08 con un "No, nunca" bien justificado; la referencia dice "vertical", la respuesta "acostado". Otro: "¿Qué hago si mi cilindro está oxidado?" obtuvo 0.12 con una paráfrasis equivalente.
- **Datos equivocados puntúan en el medio, sin alerta.** "¿Cuánto dura un cilindro de 15 kilos?": la respuesta dice "3 a 4 semanas", la referencia "entre uno y dos meses", y el F1 es 0.52. En "¿Cada cuánto se cambia el regulador?" la respuesta amplió "cinco años" a "5 a 10 años" y sacó 0.41.
- **Omisiones importantes no bajan el puntaje lo suficiente.** "¿Qué gas tóxico produce la combustión incompleta?" acierta el monóxido de carbono pero omite que no tiene olor, y saca 0.67. "¿Qué tamaños de cilindro son comunes?" omite el de 5 kilos y saca 0.57. En "olor a gas" la respuesta omite cerrar la llave del cilindro (F1 0.22, ahí sí se nota).
- **La limpieza de texto (`pipeline_texto.py`) altera las cifras.** Borra el signo menos: "-42 °C" y "42 °C" dan el mismo F1 (0.667). No equipara "cinco" con "5": contra "cinco años", tanto "5 años" (correcto) como "seis años" (incorrecto) dan 0.889. Une los rangos y las barras: "3-4 semanas" queda como `34` y "gas/aire" como `gasaire`.
- **Una negación ausente casi no baja el puntaje.** No apareció por sí sola en las 24 respuestas del modelo; está probada con texto fijo en `tests/test_metricas.py` ("Python no es compilado" contra "Python es compilado" da 0.909). Se documenta porque invierte el significado, pero no hay un caso real propio.
- **El F1 promedio mezcla dos cosas.** Sobre las 24 respuestas la precisión promedio es 0.36 y la cobertura 0.62: el modelo responde bastante más largo que las referencias, y eso baja el F1 sin que la respuesta sea peor.

## Muestra revisada

14 de 24 respuestas, revisadas el 2026-10-31 con la rúbrica de tres preguntas (corrección factual, completitud, contradicción):

- Las 5 con F1 más bajo (0.08 a 0.22).
- Las 5 con F1 más alto (0.67 a 0.73).
- 4 del medio con cifras o rangos (0.41 a 0.57), porque cualquier respuesta con números merece lectura sin importar su F1.

Resultado: factualmente 11 correctas, 2 parciales y 1 incorrecta; completas 8 y parciales 6; ninguna contradicción. Las referencias son de elaboración propia y no son la única forma correcta de responder; donde no pude confirmar un dato contra la referencia lo marqué "parcialmente".

## Recomendación de uso

Usar el F1 promedio solo para comparar versiones del cliente o del prompt sobre las mismas 24 consultas; no sirve para decidir si una respuesta de seguridad es correcta. Un F1 bajo no es motivo para descartar una respuesta sin leerla (ninguno de los 5 peores decía algo falso), y un F1 alto no la da por buena. Revisar siempre a mano las respuestas con cifras, rangos, temperaturas o plazos, y toda la categoría de seguridad (fugas, olor a gas, almacenamiento).
