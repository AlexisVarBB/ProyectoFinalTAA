# Calificador de Exámenes (OMR)

Califica exámenes de opción múltiple a partir de una **foto o escaneo** de la hoja de respuestas. Usa visión computacional con **OpenCV**, con la técnica conocida como *Optical Mark Recognition* (OMR). La foto puede tomarse en ángulo o con sombras: el sistema corrige la perspectiva y la iluminación por sí solo.

## Requisitos

* Python 3.10 o superior (desarrollado con Python 3.14 en Windows)
* Dependencias: opencv-python, numpy, pillow y customtkinter

## Instalación


python -m venv .venv
.venv\\\\Scripts\\\\activate          # En macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt


## Ejecución


python app.py


Para generar una hoja de respuestas en blanco lista para imprimir:


python hoja.py


Esto crea hoja\\\_respuestas.pdf y hoja\\\_respuestas.png (tamaño carta, 50 preguntas).

## Uso

1. **Número de preguntas:** elígelo en la barra lateral (de 5 a 50).
2. **Clave de respuestas:** en la pestaña *Clave de respuestas* hay dos formas de definirla:

   * Selecciona a mano la respuesta correcta de cada pregunta (A–E).
   * Presiona **Cargar** y elige la foto de una hoja contestada con las respuestas correctas. El sistema la lee y la usa como clave.
   * **Guardar** exporta la clave a un archivo .json.
3. **Cargar imagen:** selecciona la foto o el escaneo del examen del alumno.
4. **Calificar:** el resultado aparece en la pestaña *Calificación*:

   * Calificación de 0 a 10, aciertos y porcentaje.
   * Conteo de respuestas correctas, incorrectas, en blanco y múltiples.
   * Detalle por pregunta: qué marcó el alumno y cuál era la respuesta correcta.
   * La foto original con las correcciones dibujadas encima.

### Colores de la corrección

|Color|Significado|
|-|-|
|Verde|Respuesta correcta|
|Rojo|Respuesta incorrecta del alumno|
|Amarillo|Pregunta en blanco (marca la respuesta correcta)|
|Morado|El alumno marcó más de una opción|

### Consejos para la foto

* El **rectángulo negro** que rodea las burbujas debe verse completo.
* Usa buena iluminación y evita reflejos fuertes.
* Rellena las burbujas por completo con lápiz o pluma oscura. Una burbuja cuenta como marcada cuando está rellena al menos en un **40 %**.

## Ejemplos incluidos

La carpeta pruebas/ trae material para probar el sistema sin imprimir:

|Archivo|Contenido|
|-|-|
|clave.json|Clave de un examen de 20 preguntas|
|hoja\\\_clave.jpg|Hoja contestada con la clave (sirve para probar el botón **Cargar**)|
|examen\\\_01.jpg … examen\\\_03.jpg|Exámenes contestados, fotografiados en ángulo y con sombras|
|hoja\\\_blanco\\\_20\\\_preguntas.pdf|Hoja en blanco de 20 preguntas|



## Estructura del proyecto

|Archivo|Descripción|
|-|-|
|app.py|Interfaz gráfica (CustomTkinter)|
|calificador.py|Pipeline de visión computacional|
|hoja.py|Diseño de la hoja de respuestas y generador del PDF/PNG|
|requirements.txt|Dependencias|
|pruebas/|Imágenes y clave de ejemplo|

## ¿Cómo funciona?

|#|Etapa|Técnica (OpenCV)|Propósito|
|-|-|-|-|
|1|Escala de grises|cvtColor|Trabajar con un solo canal de intensidad|
|2|Suavizado|GaussianBlur|Reducir ruido antes de buscar bordes|
|3|Bordes|Canny + dilate|Encontrar cambios fuertes de intensidad|
|4|Contornos|findContours + approxPolyDP|Buscar figuras de 4 vértices|
|5|Validación|Umbral de Otsu sobre el borde|Confirmar que el cuadrilátero es el marco negro y no la orilla del papel|
|6|Perspectiva|getPerspectiveTransform + warpPerspective|Obtener una vista frontal normalizada de 1000×1160 px|
|7|Iluminación|Cierre morfológico + divide|Eliminar sombras y degradados|
|8|Binarización|Umbral de Otsu invertido|Separar la tinta del papel|
|9|Lectura|Máscara circular + countNonZero|Medir el % de relleno de cada burbuja|
|10|Decisión|Umbral de relleno (40 %)|Clasificar cada pregunta como marcada, en blanco o múltiple|
|11|Realidad aumentada|Matriz inversa + warpPerspective|Dibujar las correcciones sobre la foto original|

Al corregir la perspectiva, todas las fotos quedan en el mismo sistema de coordenadas. Por eso cada burbuja está siempre en la misma posición y basta con medir cuánto de cada círculo está relleno.

## Limitaciones

* Solo funciona con la hoja generada por hoja.py: máximo 50 preguntas y 5 opciones (A–E).
* Si el marco negro no aparece completo en la foto, el examen no se puede calificar.
* Las marcas muy tenues o borradas a medias pueden no detectarse.

