# Calificador OMR

Sistema de escritorio desarrollado en Python para la calificación automática de exámenes de opción múltiple mediante técnicas clásicas de visión computacional y procesamiento digital de imágenes con **OpenCV**.

El sistema recibe una fotografía o escaneo de una hoja de respuestas estandarizada, corrige su perspectiva, detecta las burbujas rellenadas por el estudiante, compara las marcas contra una clave de respuestas y genera tanto la evaluación numérica como una imagen anotada proyectada sobre la fotografía original.

---

## Características principales

* **Procesamiento 100% local:** Opera mediante algoritmos clásicos de visión computacional sin depender de conexión a internet, servicios en la nube, bases de datos ni modelos de redes neuronales.
* **Corrección de perspectiva automática:** Localiza el marco negro de referencia de la hoja mediante detección de bordes Canny y contornos poligonales, rectificando fotografías inclinadas o con ángulo hacia un espacio frontal fijo (`1000 × 1160` px).
* **Normalización de iluminación:** Compensa sombras y variaciones de luz mediante cierre morfológico elíptico y división de fondo antes de binarizar con el método de Otsu.
* **Clasificación de 4 estados por pregunta:**
  * **Correcta (Verde):** Coincide con la clave de respuestas.
  * **Incorrecta (Rojo):** Opción marcada distinta a la clave.
  * **Vacía (Amarillo):** Ninguna burbuja supera el umbral de relleno (señala cuál era la correcta).
  * **Múltiple (Morado):** Dos o más opciones marcadas en la misma pregunta (invalidada).
* **Interfaz gráfica de escritorio (`CustomTkinter`):**
  * Selector de cantidad de preguntas: `5, 10, 15, 20, 25, 30, 40 y 50`.
  * Soporte para tema claro y tema oscuro.
  * Carga de imágenes en formatos `JPG`, `JPEG`, `PNG`, `BMP`, `TIFF` y `TIF` (incluyendo rutas con acentos o caracteres especiales).
  * Guardado y carga de claves en formato `.json`, además de la capacidad de **extraer la clave directamente desde una hoja física contestada por el docente**.
* **Generación de hojas imprimibles y exámenes sintéticos:** Incluye herramientas de línea de comandos para exportar plantillas en PDF/imagen y simular fotografías de prueba con ruido, sombras y perspectiva.

---

## Estructura del proyecto

```text
calificador_omr/
├── app.py                     # Interfaz gráfica de escritorio (CustomTkinter) y coordinación general
├── calificador.py             # Núcleo OMR: pipeline de visión computacional, lectura y calificación
├── hoja.py                    # Definición geométrica de la hoja y exportador de plantillas (PDF/JPG)
├── generar_pruebas.py         # Generador de exámenes sintéticos y simulación de fotografías
├── requirements.txt           # Dependencias del proyecto
├── README.md                  # Documentación técnica
├── hoja_20_preguntas.pdf      # Plantilla imprimible de ejemplo (20 preguntas)
├── hoja_50_preguntas.pdf      # Plantilla imprimible de ejemplo (50 preguntas)
└── pruebas/                   # Datos y exámenes simulados para validación
    ├── clave.json
    ├── respuestas_esperadas.json
    ├── hoja_clave.jpg
    └── examen_01.jpg ... examen_05.jpg
```

---

## Requisitos previos

* **Python 3.10** o superior.
* Dependencias especificadas en `requirements.txt`:
  * `opencv-python >= 4.8`
  * `numpy >= 1.24`
  * `pillow >= 10.0`
  * `customtkinter >= 5.2`

---

## Instalación

1. Clona o descarga este repositorio y ubícate en la carpeta raíz del proyecto:
   ```bash
   cd calificador_omr
   ```

2. *(Opcional, recomendado)* Crea y activa un entorno virtual:
   ```bash
   python -m venv .venv
   # En Windows:
   .venv\Scripts\activate
   # En Linux / macOS:
   source .venv/bin/activate
   ```

3. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```

---

## Uso y ejecución

### 1. Iniciar la aplicación gráfica principal
Ejecuta el punto de entrada de la interfaz de escritorio:
```bash
python app.py
```

**Flujo de trabajo en la interfaz:**
1. En la barra lateral izquierda, selecciona el **número de preguntas** del examen (`20` por defecto).
2. Ve a la pestaña **Clave de respuestas** para marcar manualmente las respuestas correctas, cargar un archivo `.json` existente, o importar la clave desde una fotografía de la hoja contestada por el profesor.
3. Haz clic en **Cargar imagen** para seleccionar la fotografía o escaneo del examen del estudiante.
4. Haz clic en **Calificar** para procesar la hoja. El sistema mostrará la imagen anotada, el desglose por pregunta y la calificación en escala de `0.0` a `10.0` (con umbral de relleno predeterminado de `0.40`).

### 2. Generar hojas de respuestas imprimibles
Puedes generar nuevas hojas en formato `.pdf` o imagen ejecutando directamente `hoja.py`:
```bash
python hoja.py
```
*(Este módulo define las coordenadas exactas en un espacio normalizado de `1000 × 1160` px y las escala a `1700 × 2200` px para impresión, admitiendo entre 1 y 50 preguntas).*

### 3. Generar exámenes sintéticos de prueba
Para probar el algoritmo OMR sin necesidad de imprimir y fotografiar hojas físicas, ejecuta `generar_pruebas.py`:
```bash
# Uso por defecto (genera 5 exámenes de 20 preguntas en la carpeta pruebas/)
python generar_pruebas.py

# Uso personalizado: python generar_pruebas.py <cantidad_examenes> <num_preguntas>
python generar_pruebas.py 8 30
```

---

## Arquitectura del pipeline OMR (`calificador.py`)

1. **Preprocesamiento:** Redimensionamiento proporcional (`MAX_LADO = 1600` px), conversión a escala de grises y suavizado Gaussiano (`5×5`).
2. **Detección del marco:** Detector de bordes **Canny** (`50, 150`), dilatación morfológica (`3×3`), filtrado de contornos mayores al 8% del área total y validación de borde oscuro (`_puntaje_marco > 0.55`).
3. **Rectificación:** Ordenamiento de vértices y transformación de perspectiva (`cv2.warpPerspective`) hacia `1000 × 1160` px.
4. **Normalización y binarización:** Cierre morfológico elíptico (`45×45`), división de fondo (`cv2.divide`), binarización inversa de **Otsu** y apertura morfológica (`2×2`).
5. **Lectura y calificación:** Evaluación de tinta dentro del radio interno (`0.72 × RADIO`) de cada burbuja (`A–E`) con umbral `0.40`.
6. **Reproyección:** Dibujo de anotaciones cromáticas y proyección inversa (`Minv`) sobre la fotografía original.

---

## Limitaciones técnicas conocidas

* La hoja fotografiada debe conservar **visible y completo el marco negro exterior** de referencia.
* El sistema está diseñado exclusivamente para la geometría fija definida en `hoja.py` (máximo 50 preguntas distribuidas en 2 columnas de 25 filas, con 5 opciones `A–E` por pregunta).
* Sombras muy pronunciadas, reflejos directos sobre la tinta o marcas excesivamente tenues (por debajo del 40% de relleno interno) pueden afectar la detección.
````[cite: 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
