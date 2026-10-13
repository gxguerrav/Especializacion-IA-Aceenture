# Especialización en Desarrollo con IA Generativa (Accenture)

Repositorio único para todo el Diplomado. Cada módulo se va a ir reflejando acá como avanza el programa, hasta llegar a la aplicación completa que se entrega en el Gate 3.

## Cómo empezar (nuevo entorno)

1. Clona este repositorio.
2. Crea tu entorno virtual de Python y actívalo:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Instala las dependencias:
   ```powershell
   pip install -r requirements.txt
   ```
4. Copia `.env.example` a un archivo nuevo llamado `.env`, y completa ahí tus credenciales reales (llaves de API, tokens). El archivo `.env` nunca se sube al repositorio: ya está excluido en `.gitignore`.

## Estructura de carpetas

- `src/` : todo el código fuente del proyecto.
- `docs/` : documentación técnica (diagramas, decisiones de arquitectura, notas).
- `tests/` : pruebas automatizadas.
- `Tareas/` : entregables y formularios de las distintas unidades.
- `Modulo_1/`, `Modulo_2/`, ... : notas y material específico de cada módulo.
- `requirements.txt` : dependencias de Python del proyecto.
- `.env.example` : plantilla de las variables de entorno necesarias, sin valores reales.
- `.gitignore` : archivos y carpetas que Git debe ignorar (entorno virtual, `.env`, cachés, etc.).

## Reglas que se mantienen durante todo el programa

- Ningún secreto (contraseña, llave de API, token) va escrito directamente en el código ni en ningún archivo que se suba al repositorio.
- Todo el trabajo que se entrega en este programa vive en este repositorio de GitHub, sin excepción.
