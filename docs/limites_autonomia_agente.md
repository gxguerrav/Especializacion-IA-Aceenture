## Límites de autonomía: agente de atención de pedidos de gas en cilindros

Agente en `src/agente_con_herramientas.py` (`create_tool_calling_agent` + `AgentExecutor`, con memoria por `session_id`). Decide solo qué herramienta usar; este documento fija hasta dónde puede llegar sin que una persona intervenga. Describe el código tal como está implementado hoy.

#### Herramientas y nivel de riesgo

- `consultar_estado_pedido_con_historial`: **bajo** (solo lee el estado y el historial de un pedido; no modifica nada. Si el agente la usa de más, el peor resultado es una respuesta inútil).
- `calcular_costo_pedido`: **bajo** (solo calcula un total a partir de una tabla de precios; no ejecuta ninguna acción externa).
- `generar_reembolso`: **alto** (mueve dinero y no se puede deshacer; un error del modelo en el pedido o en el monto tiene un costo económico directo).

No hay herramientas de riesgo medio (escritura reversible): el agente no guarda ni edita datos. Las dos de riesgo bajo no se clasifican como altas "por las dudas": no pueden causar daño real.

#### Herramientas que requieren aprobación humana

- `generar_reembolso`: la acción es irreversible y tiene impacto económico, y es el modelo quien decide invocarla, con los argumentos que él mismo extrae de la conversación. Por eso la herramienta llama a `esperar_aprobacion()` (`src/supervision.py`) antes de ejecutar:
  - Solo la respuesta `s` aprueba. Cualquier otra, un timeout (300 s por defecto) o la ausencia de entrada estándar cuentan como **no aprobado**.
  - Cada decisión, aprobada o rechazada, queda en `registro_aprobaciones` con herramienta, argumentos y momento.
  - Antes de pedir aprobación se valida que el pedido exista y que el monto sea mayor que cero, para no gastar la atención del supervisor en solicitudes que no pueden proceder.
- `consultar_estado_pedido_con_historial` y `calcular_costo_pedido`: **no** piden aprobación. Pedirla en acciones de lectura haría que el supervisor aprobara por costumbre y dejara de leer las que sí importan.

Estado actual y límites de esta implementación:

- La aprobación se pide por consola (`input()` en un hilo con timeout). En un sistema real debería venir de un panel de aprobaciones o una notificación.
- El reembolso está simulado: tras la aprobación solo devuelve un texto, no llama a ningún sistema de pagos.
- `registro_aprobaciones` vive en memoria y se pierde al reiniciar; para auditoría real hay que guardarlo en una base de datos.
- Un timeout deja el hilo de lectura esperando; si la persona responde después, esa respuesta ya no se asocia a la solicitud vencida.

#### Revisión de trazas

- **Cómo se guarda:** cada interacción (pregunta, herramientas usadas con sus argumentos y observaciones, respuesta final) se agrega como una línea JSON a `trazas_agente.jsonl` mediante `registrar_traza()` (`src/trazas.py`), llamada desde `consultar()` en `src/agente_con_herramientas.py`.
- **Frecuencia:**
  - Una muestra pequeña (5 a 10 trazas) cada semana.
  - **Todas** las trazas donde se usó `generar_reembolso`, sin muestreo.
  - Una pasada automática con `marcar_repeticiones_sospechosas()` para reducir el archivo a unos pocos candidatos.
- **Qué se busca:**
  - La misma herramienta invocada dos o más veces seguidas (el agente no avanza o una observación ambigua lo hace reintentar). La pasada automática compara solo el nombre de la herramienta, no los argumentos, así que puede marcar falsos positivos.
  - `generar_reembolso` en una traza sin su entrada correspondiente en `registro_aprobaciones` (señal de que la supervisión falló).
  - Una respuesta final que no coincide con ninguna observación (el agente pudo haber inventado el dato).
- **Límite:** revisar trazas explica qué pasó después de que ocurrió; no reemplaza la aprobación humana ni las pruebas automatizadas.
  - Observado en la práctica: en una corrida con reembolso aprobado, la respuesta final decía que el reembolso aún requería aprobación, aunque la herramienta ya lo había generado. Se corrigió ajustando el prompt de sistema para que el agente informe lo que devuelve la herramienta.
#### Qué hacer ante un comportamiento inesperado

1. **Contener:** quitar la herramienta implicada de `HERRAMIENTAS` en `src/agente_con_herramientas.py` y reiniciar el agente. Si involucra dinero, empezar por `generar_reembolso`.
2. **Revisar el alcance:** buscar en `trazas_agente.jsonl` todas las sesiones donde se usó esa herramienta y confirmar, contra `registro_aprobaciones`, que cada acción de riesgo alto tuvo una aprobación humana.
3. **Corregir lo ocurrido:** si hubo un reembolso erróneo, avisar al responsable de pagos con el número de pedido y el monto de la traza para revertirlo manualmente.
4. **Buscar la causa:** revisar la descripción (docstring) de la herramienta y el prompt de sistema; ajustarlos (por ejemplo, aclarar cuándo usarla y cuándo no) en vez de solo reintentar.
5. **Cubrir el caso:** agregar una prueba en `tests/` que reproduzca el comportamiento y confirmar que pasa antes de volver a activar la herramienta.

#### Cómo verificar que este documento coincide con el código

```bash
grep -n "esperar_aprobacion(" src/agente_con_herramientas.py src/supervision.py
wc -l trazas_agente.jsonl
grep -c '"herramienta": "generar_reembolso"' trazas_agente.jsonl
python -m pytest tests -v
```

En PowerShell: `Select-String "esperar_aprobacion\(" src\*.py` y `(Get-Content trazas_agente.jsonl).Count`. La prueba `test_toda_herramienta_de_riesgo_alto_llama_a_esperar_aprobacion` automatiza la primera verificación.

