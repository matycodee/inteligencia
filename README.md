# Asistente RAG para NutriFit Chile

Este repositorio tiene el código del proyecto para la Evaluación Parcial N°1 de la asignatura de Soluciones con IA. Armamos un asistente inteligente conectado a una base de datos local y documentos de la empresa para responder consultas de inventario y políticas al instante.

## Contenido del proyecto
* **data/**: Archivos con el inventario en CSV y las políticas en PDF.
* **app.py**: El script principal que levanta el agente y procesa las preguntas.
* **requirements.txt**: Las librerías necesarias de Python.

## Cómo correrlo en tu equipo

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Opción A - Interfaz Web Interactiva (Recomendado):**
   ```bash
   python web_app.py
   ```
   Luego abre tu navegador en **`http://localhost:8000`** para interactuar con la interfaz visual, chat en vivo y catálogo en tiempo real.

3. **Opción B - Modo Consola (Terminal CLI):**
   ```bash
   python app.py
   ```
