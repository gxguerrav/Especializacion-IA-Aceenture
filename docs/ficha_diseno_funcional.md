# Ficha de Diseño Funcional

## 1. Problema de negocio

El equipo de atención de una distribuidora ficticia de gas en cilindros responde unas 80 consultas semanales (estimación) sobre precios por tamaño de cilindro, despacho, reembolsos y estado de pedidos. Hoy busca la respuesta a mano entre documentos sueltos y planillas, y las respuestas varían según quién conteste. Cada consulta toma cerca de 6 minutos (estimación), es decir, unas 8 horas semanales del equipo. Se espera que cualquier integrante obtenga una respuesta con su fuente, o el estado de un pedido, en menos de un minuto.

## 2. Requerimientos y alcance (MVP)

### Requerimientos funcionales

- RF-01: El usuario envía una pregunta de texto a un endpoint de consulta y recibe una respuesta en JSON.
- RF-02: Cada respuesta incluye al menos una fuente citada con el nombre del documento del que sale el dato.
- RF-03: El servicio consulta el estado de un pedido por su número (por ejemplo, GAS-1001) usando datos simulados.
- RF-04: Una persona aprueba o rechaza antes de que se genere un reembolso.
- RF-05: Una interfaz web muestra el historial de conversaciones.
- RF-06: El servicio consulta el sistema de pedidos real de la empresa.

### Requerimientos no funcionales

- RNF-01: El endpoint de consulta responde en menos de 8 segundos en al menos 9 de cada 10 consultas de prueba.
- RNF-02: En los registros de las 10 consultas de prueba, ninguna línea contiene el texto completo de la pregunta ni de los documentos, solo longitudes, conteos y huellas.
- RNF-03: El servicio levanta desde cero en un contenedor, siguiendo el README, en menos de 10 minutos.
- RNF-04: Al menos 8 de las 10 respuestas del conjunto de prueba citan la fuente correcta.

### Alcance

Imprescindible: RF-01, RF-02, RF-03
Deseable: RF-04
Fuera de alcance: RF-05 (no hay frontend en el programa), RF-06 (requiere sistemas y datos reales)

## 3. Arquitectura de la solución

Diagrama: docs/diagrama_arquitectura.png

- Modelo: Gemini mediante API, con la clave en el archivo .env.
- Vector store: Chroma persistido en la carpeta vectorstore/.
- Orquestación: recuperación, filtro de inyección y generación con citas; aprobación humana con LangGraph.
- Exposición: servicio FastAPI con un endpoint de consulta.
- Empaquetado: imagen Docker con el índice montado como volumen.

## 4. Criterios de aceptación

[PENDIENTE: se completa en el Bloque 34]

## 5. Plan de construcción por hitos

[PENDIENTE: se completa en el Bloque 34]
