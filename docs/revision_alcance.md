# Revisión del alcance

Revisor: Gamaliel Guerra 
Fecha: 2026-11-26

- Hallazgo 1 (criterio 4): RF-03 es imprescindible pero su único criterio era el caso feliz; no había un caso negativo para un pedido que no existe.
  Decisión: aceptado. Cambio: se agregó CA-05, que consulta "GAS-9999" y exige que la respuesta diga que no existe el pedido sin inventar un estado; H4 ahora se comprueba con CA-04 y CA-05.

- Hallazgo 2 (criterio 5): H5 reúne pruebas, documentación y defensa en un solo hito de 6 h, difícil de dar por terminado.
  Decisión: rechazado. Motivo: las 6 h son la reserva del 30 % calculada con presupuesto_alcance.py y el hito se comprueba con CA-06, CA-07 y CA-09, que son las pruebas medibles.

- Hallazgo 3 (criterio 2): RF-04 (aprobación humana antes del reembolso) ya tiene una base construida en src/supervision.py y podría subir a imprescindible, pero el presupuesto de construcción ya está en 10 h de 10 h.
  Decisión: aplazado. Se vuelve a evaluar al terminar H4, solo si H1 a H4 cierran con horas sobrantes y sin tocar el margen de imprevistos.

Acierto: los criterios de los RNF reutilizan las cifras de la sección 2 (8 segundos, 10 consultas, 10 minutos, 8 de 10), así que no hay que reinterpretar nada.
