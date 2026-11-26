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

- CA-01 (RF-01): Al enviar la pregunta "¿Cuánto cuesta un cilindro de 15 kg?" al endpoint de consulta, la respuesta es un JSON con los campos "respuesta" y "fuentes".
- CA-02 (RF-02): Para esa misma pregunta, "fuentes" contiene "catalogo_precios" y la respuesta menciona "$27.000".
- CA-03 (RF-02): Ante la pregunta "¿Aceptan pagos con criptomonedas?", que el corpus no cubre, la respuesta contiene el texto "No tengo informacion" y "fuentes" va vacía.
- CA-04 (RF-03): Al consultar el estado del pedido simulado "GAS-1001", la respuesta indica "en camino" y la hora de llegada que figura en los datos simulados.
- CA-05 (RF-03): Al consultar el pedido inexistente "GAS-9999", la respuesta dice que no existe ese pedido y no inventa ningún estado.
- CA-06 (RNF-01): En las 10 consultas de prueba, al menos 9 responden en menos de 8 segundos.
- CA-07 (RNF-02): Tras ejecutar las 10 consultas de prueba, ninguna línea del registro contiene el texto completo de una pregunta.
- CA-08 (RNF-03): Siguiendo solo el README en un equipo limpio, el servicio responde a CA-01 a los 10 minutos o antes desde el inicio.
- CA-09 (RNF-04): En las 10 consultas de prueba con documento esperado conocido, al menos 8 devuelven ese documento en "fuentes".

## 5. Plan de construcción por hitos

Horas disponibles: 20 h
Margen de imprevistos: 4 h

- H1 (3 h): Servicio FastAPI con el endpoint de consulta. Cubre: RF-01. Se comprueba con: CA-01.
- H2 (2 h): Respuestas con fuente desde el índice persistido. Cubre: RF-02. Se comprueba con: CA-02, CA-03.
- H3 (3 h): Servicio empaquetado en un contenedor. Cubre: RNF-03. Se comprueba con: CA-08.
- H4 (2 h): Consulta de estado de pedido con datos simulados. Cubre: RF-03. Se comprueba con: CA-04, CA-05.
- H5 (6 h): Pruebas, documentación y ensayo de la defensa. Cubre: RNF-01, RNF-02, RNF-04. Se comprueba con: CA-06, CA-07, CA-09.
