# Diplomado en IA Generativa (Accenture)

Mi repositorio del diplomado. Acá voy dejando el trabajo de cada módulo. Lo que hay hoy es la miniaplicación del Módulo 1 (Gate 1): un script en Python que le manda una pregunta a la API de Gemini y procesa la respuesta, con un banco de prompts que devuelven JSON.

## Instalación

Necesitas Python 3 y Git. En PowerShell (Windows):

```powershell
git clone https://github.com/gxguerrav/Especializacion-IA-Aceenture.git
cd Especializacion-IA-Aceenture
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

En macOS, Linux o WSL cambia `python` por `python3`, la activación por `source venv/bin/activate` y `Copy-Item` por `cp`.

Después abre el `.env` y pega tu llave en `GEMINI_API_KEY` (se saca en Google AI Studio). El `.env` está en el `.gitignore`, así que no se sube.

## Cómo correrlo

```powershell
python src/consumir_gemini.py
```

Hace una consulta de prueba y muestra la respuesta del modelo. Si algo falla (pregunta vacía, falta la llave, no hay conexión, timeout o una respuesta que no se puede leer), imprime un mensaje corto en vez de un error largo.

Otros comandos:

```powershell
python -m unittest discover tests      # pruebas del módulo, no usan la API
python prompts/test_consistencia.py    # prueba cada prompt 3 veces contra la API real
```

## Cómo está armado

El módulo `src/consumir_gemini.py` tiene las funciones separadas:

- `armar_peticion`: valida la pregunta y la llave, y arma la URL y el cuerpo de la petición.
- `enviar_peticion`: hace el POST (la llave va en un header, no en la URL) y devuelve el JSON.
- `extraer_texto`: saca el texto de la respuesta.
- `parsear_respuesta_json`: limpia y valida las respuestas que deben venir en JSON.

El modelo es `gemini-3.5-flash-lite`. Por qué lo elegí y contra qué lo comparé está en [docs/decision-arquitectura.md](docs/decision-arquitectura.md), y el flujo completo está en el diagrama [docs/diagrama_arquitectura.drawio.png](docs/diagrama_arquitectura.drawio.png).

## Banco de prompts

En `prompts/banco.py` hay tres prompts para una empresa de gas en cilindros, cada uno con su instrucción de sistema separada del mensaje del usuario y con un esquema de salida JSON:

| Prompt | Para qué sirve |
|---|---|
| `clasificar_intencion` | Dice si el mensaje es una compra, cotización, reclamo, etc. |
| `extraer_pedido` | Saca tipo de cilindro, cantidad y dirección |
| `respuesta_de_venta` | Responde al cliente usando el catálogo y calcula el total |

`prompts/test_consistencia.py` llama a cada prompt 3 veces y guarda cuántas respuestas fueron JSON válido en `prompts/registro_resultados.json`. En mi última corrida salió 3 de 3 en los tres prompts. La captura está en `docs/Evidencia de test de consistencia.png`.

## Carpetas

- `src/`: código de la miniaplicación
- `prompts/`: banco de prompts y su prueba de consistencia
- `tests/`: pruebas unitarias
- `docs/`: decisión de modelo, diagrama y capturas de evidencia
- `Modulo_1/`, `Tareas/`: material de las actividades del diplomado

## Credenciales

Ninguna llave va escrita en el código ni en archivos que se suban. Solo está en mi `.env` local; en el repo queda el `.env.example` con los nombres de las variables y sin valores.

