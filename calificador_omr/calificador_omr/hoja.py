
import cv2
import numpy as np
from PIL import Image


BW, BH = 1000, 1160
GROSOR_MARCO = 10


MAX_PREGUNTAS = 50
OPCIONES = "ABCDE"
FILAS_POR_COLUMNA = 25
COLUMNAS_X = [0, 500]
Y0, DY = 140, 40
NUM_X = 60
BX0, DX = 150, 64
RADIO = 15


HOJA_W, HOJA_H = 1700, 2200
ESCALA = 1.45
OFFSET_X, OFFSET_Y = 125, 380


def centro_burbuja(pregunta: int, opcion: int):

    col, fila = divmod(pregunta, FILAS_POR_COLUMNA)
    x = COLUMNAS_X[col] + BX0 + opcion * DX
    y = Y0 + fila * DY
    return x, y


def _a_hoja(x, y):

    return int(round(OFFSET_X + x * ESCALA)), int(round(OFFSET_Y + y * ESCALA))


def _texto(img, txt, pos, escala=1.0, grosor=2, color=(0, 0, 0), centrado=False):
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    if centrado:
        (tw, th), _ = cv2.getTextSize(txt, fuente, escala, grosor)
        pos = (int(pos[0] - tw / 2), int(pos[1] + th / 2))
    cv2.putText(img, txt, pos, fuente, escala, color, grosor, cv2.LINE_AA)


def generar_hoja(num_preguntas: int = MAX_PREGUNTAS, titulo: str = "HOJA DE RESPUESTAS"):

    num_preguntas = 20
    img = np.full((HOJA_H, HOJA_W, 3), 255, np.uint8)


    _texto(img, titulo, (HOJA_W // 2, 110), 1.6, 3, centrado=True)
    campos = [("Nombre:", 125, 200, 1100), ("Grupo:", 1150, 200, 1575),
              ("Examen:", 125, 270, 1100), ("Fecha:", 1150, 270, 1575)]
    for etiqueta, x, y, x_fin in campos:
        _texto(img, etiqueta, (x, y), 0.9, 2)
        (tw, _), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.line(img, (x + tw + 10, y + 5), (x_fin, y + 5), (0, 0, 0), 2)
    _texto(img, "Rellena COMPLETAMENTE un circulo por pregunta con lapiz o pluma oscura. "
                "No escribas dentro del marco.", (125, 335), 0.62, 1, (60, 60, 60))


    x0, y0 = _a_hoja(0, 0)
    x1, y1 = _a_hoja(BW, BH)
    g = int(GROSOR_MARCO * ESCALA)
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 0), -1)
    cv2.rectangle(img, (x0 + g, y0 + g), (x1 - g, y1 - g), (255, 255, 255), -1)


    columnas_usadas = 1 if num_preguntas <= FILAS_POR_COLUMNA else 2
    for c in range(columnas_usadas):
        for o, letra in enumerate(OPCIONES):
            x, _ = centro_burbuja(c * FILAS_POR_COLUMNA, o)
            _texto(img, letra, _a_hoja(x, 85), 1.0, 2, centrado=True)


    r = int(RADIO * ESCALA)
    for q in range(num_preguntas):
        _, y = centro_burbuja(q, 0)
        col = q // FILAS_POR_COLUMNA
        _texto(img, f"{q + 1:>2}.", _a_hoja(COLUMNAS_X[col] + NUM_X, y + 8), 0.85, 2)
        for o, letra in enumerate(OPCIONES):
            cx, cy = _a_hoja(*centro_burbuja(q, o))
            cv2.circle(img, (cx, cy), r, (0, 0, 0), 2, cv2.LINE_AA)
            # Letra en gris claro: guía visual que el umbral de Otsu ignora
            _texto(img, letra, (cx, cy), 0.55, 1, (175, 175, 175), centrado=True)

    _texto(img, "Calificador",
           (HOJA_W // 2, HOJA_H - 60), 0.6, 1, (120, 120, 120), centrado=True)
    return img


def guardar_hoja(ruta: str, num_preguntas: int = MAX_PREGUNTAS, titulo="HOJA DE RESPUESTAS"):

    img = generar_hoja(num_preguntas, titulo)
    if ruta.lower().endswith(".pdf"):
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        pil.save(ruta, "PDF", resolution=200.0)
    else:
        cv2.imwrite(ruta, img)
    return ruta


if __name__ == "__main__":
    guardar_hoja("hoja_respuestas.pdf")
    guardar_hoja("hoja_respuestas.png")
    print("Hoja generada: hoja_respuestas.pdf / .png")
