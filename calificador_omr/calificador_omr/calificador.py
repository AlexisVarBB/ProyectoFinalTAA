"""
Núcleo de visión computacional del sistema (OMR: Optical Mark Recognition).
"""
from dataclasses import dataclass, field
import cv2
import numpy as np

import hoja


VERDE = (60, 200, 60)
ROJO = (50, 50, 230)
AMARILLO = (0, 200, 255)
MORADO = (200, 80, 200)

MAX_LADO = 1600


@dataclass
class ResultadoPregunta:
    numero: int
    marcada: str | None
    correcta: str
    estado: str
    rellenos: list = field(default_factory=list)


@dataclass
class Resultado:
    ok: bool
    mensaje: str = ""
    preguntas: list = field(default_factory=list)
    aciertos: int = 0
    total: int = 0
    etapas: dict = field(default_factory=dict)
    imagen_resultado: np.ndarray | None = None

    @property
    def porcentaje(self):
        return 100.0 * self.aciertos / self.total if self.total else 0.0

    @property
    def calificacion(self):
        return round(self.porcentaje / 10.0, 1)

    def contar(self, estado):
        return sum(1 for p in self.preguntas if p.estado == estado)

    def respuestas(self):

        return [p.marcada if p.marcada not in (None, "*") else None for p in self.preguntas]



def ordenar_puntos(pts):

    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)],
                     pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def matriz_perspectiva(pts):
    destino = np.array([[0, 0], [hoja.BW - 1, 0],
                        [hoja.BW - 1, hoja.BH - 1], [0, hoja.BH - 1]], dtype=np.float32)
    return cv2.getPerspectiveTransform(ordenar_puntos(pts), destino)


def _puntaje_marco(gris, pts):

    M = matriz_perspectiva(pts)
    w = cv2.warpPerspective(gris, M, (hoja.BW, hoja.BH))
    _, b = cv2.threshold(w, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    a, z = 2, hoja.GROSOR_MARCO - 2
    franjas = [b[a:z, :], b[-z:-a, :], b[:, a:z], b[:, -z:-a]]
    return float(np.mean([f.mean() / 255.0 for f in franjas]))


def encontrar_marco(gris, devolver_etapas=False):

    suave = cv2.GaussianBlur(gris, (5, 5), 0)
    bordes = cv2.Canny(suave, 50, 150)
    bordes = cv2.dilate(bordes, np.ones((3, 3), np.uint8), iterations=1)

    contornos, _ = cv2.findContours(bordes, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    area_min = 0.08 * gris.shape[0] * gris.shape[1]
    contornos = sorted([c for c in contornos if cv2.contourArea(c) > area_min],
                       key=cv2.contourArea, reverse=True)[:15]

    encontrado = None
    for c in contornos:
        peri = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(aprox) == 4 and cv2.isContourConvex(aprox):
            if _puntaje_marco(gris, aprox) > 0.55:
                encontrado = aprox.reshape(4, 2).astype(np.float32)
                break

    etapas = {"Suavizado (Gauss)": suave, "Bordes (Canny)": bordes} if devolver_etapas else {}
    return encontrado, etapas


def normalizar_iluminacion(gris):

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45))
    fondo = cv2.morphologyEx(gris, cv2.MORPH_CLOSE, k)
    return cv2.divide(gris, fondo, scale=255)



def porcentaje_relleno(binaria, centro, radio):
    mascara = np.zeros(binaria.shape, np.uint8)
    cv2.circle(mascara, centro, radio, 255, -1)
    total = cv2.countNonZero(mascara)
    return cv2.countNonZero(cv2.bitwise_and(binaria, mascara)) / total


def leer_burbujas(binaria, num_preguntas, umbral=0.40):

    r_int = int(hoja.RADIO * 0.72)
    lecturas = []
    for q in range(num_preguntas):
        rellenos = []
        for o in range(len(hoja.OPCIONES)):
            cx, cy = hoja.centro_burbuja(q, o)
            rellenos.append(porcentaje_relleno(binaria, (cx, cy), r_int))
        marcadas = [i for i, v in enumerate(rellenos) if v >= umbral]
        if not marcadas:
            letra = None
        elif len(marcadas) > 1:
            letra = "*"
        else:
            letra = hoja.OPCIONES[marcadas[0]]
        lecturas.append((letra, rellenos))
    return lecturas



def _dibujar_anotaciones(preguntas, tam):

    capa = np.zeros((hoja.BH, hoja.BW, 3), np.uint8)
    r = hoja.RADIO + 4
    for p in preguntas:
        q = p.numero - 1
        oc = hoja.OPCIONES.index(p.correcta) if p.correcta else None
        if p.estado == "correcta":
            cv2.circle(capa, hoja.centro_burbuja(q, oc), r, VERDE, 4, cv2.LINE_AA)
        else:
            if p.estado == "incorrecta":
                om = hoja.OPCIONES.index(p.marcada)
                cv2.circle(capa, hoja.centro_burbuja(q, om), r, ROJO, 4, cv2.LINE_AA)
            elif p.estado == "multiple":
                for i, v in enumerate(p.rellenos):
                    if v >= tam:
                        cv2.circle(capa, hoja.centro_burbuja(q, i), r, MORADO, 4, cv2.LINE_AA)
            if oc is not None:
                color = AMARILLO if p.estado == "vacia" else VERDE
                cv2.circle(capa, hoja.centro_burbuja(q, oc), r, color, 2, cv2.LINE_AA)
    return capa


def _banner(img, res):

    h, w = img.shape[:2]
    esc = max(0.6, w / 900)
    txt = f"{res.aciertos}/{res.total} = {res.porcentaje:.0f}%"
    (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, esc, int(2 * esc))
    pad = int(14 * esc)
    color = VERDE if res.porcentaje >= 60 else ROJO
    cv2.rectangle(img, (0, 0), (tw + 2 * pad, th + 2 * pad), (30, 30, 30), -1)
    cv2.rectangle(img, (0, th + 2 * pad - 6), (tw + 2 * pad, th + 2 * pad), color, -1)
    cv2.putText(img, txt, (pad, th + pad - 3), cv2.FONT_HERSHEY_SIMPLEX, esc,
                (255, 255, 255), int(2 * esc), cv2.LINE_AA)


def calificar(imagen, clave, umbral=0.40):

    if imagen is None:
        return Resultado(False, "No hay imagen para calificar.")
    num = len(clave)
    if not 1 <= num <= hoja.MAX_PREGUNTAS:
        return Resultado(False, f"La clave debe tener entre 1 y {hoja.MAX_PREGUNTAS} preguntas.")


    h, w = imagen.shape[:2]
    f = MAX_LADO / max(h, w)
    if f < 1:
        imagen = cv2.resize(imagen, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA)
    etapas = {"Original": imagen.copy()}


    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    etapas["Escala de grises"] = gris
    pts, et = encontrar_marco(gris, devolver_etapas=True)
    etapas.update(et)
    if pts is None:
        return Resultado(False, "No se encontró el marco de la hoja. Asegúrate de que el "
                                "rectángulo negro sea visible completo y con buena luz.",
                         etapas=etapas)

    contorno = imagen.copy()
    cv2.polylines(contorno, [pts.astype(np.int32)], True, VERDE, 4, cv2.LINE_AA)
    for p in pts:
        cv2.circle(contorno, tuple(int(v) for v in p), 10, ROJO, -1)
    etapas["Contorno detectado"] = contorno


    M = matriz_perspectiva(pts)
    alineada = cv2.warpPerspective(imagen, M, (hoja.BW, hoja.BH))
    alineada_gris = cv2.warpPerspective(gris, M, (hoja.BW, hoja.BH))
    etapas["Perspectiva corregida"] = alineada


    normal = normalizar_iluminacion(alineada_gris)
    etapas["Iluminación normalizada"] = normal
    _, binaria = cv2.threshold(normal, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    etapas["Umbral (Otsu)"] = binaria


    lecturas = leer_burbujas(binaria, num, umbral)


    zonas = cv2.cvtColor(binaria, cv2.COLOR_GRAY2BGR)
    r_int = int(hoja.RADIO * 0.72)
    for q, (_, rellenos) in enumerate(lecturas):
        for o, v in enumerate(rellenos):
            color = VERDE if v >= umbral else (130, 130, 130)
            cv2.circle(zonas, hoja.centro_burbuja(q, o), r_int, color, 2)
    etapas["Zonas de lectura"] = zonas


    preguntas, aciertos = [], 0
    for i, ((marcada, rellenos), correcta) in enumerate(zip(lecturas, clave)):
        correcta = (correcta or "").upper() or None
        if marcada is None:
            estado = "vacia"
        elif marcada == "*":
            estado = "multiple"
        elif marcada == correcta:
            estado = "correcta"
            aciertos += 1
        else:
            estado = "incorrecta"
        preguntas.append(ResultadoPregunta(i + 1, marcada, correcta, estado,
                                           [round(v, 3) for v in rellenos]))

    res = Resultado(True, "Examen calificado correctamente.", preguntas, aciertos, num, etapas)


    capa = _dibujar_anotaciones(preguntas, umbral)
    alineada_anot = alineada.copy()
    m = capa.any(axis=2)
    alineada_anot[m] = capa[m]
    etapas["Corrección (vista alineada)"] = alineada_anot

    Minv = np.linalg.inv(M)
    capa_orig = cv2.warpPerspective(capa, Minv, (imagen.shape[1], imagen.shape[0]),
                                    flags=cv2.INTER_NEAREST)
    final = imagen.copy()
    m = capa_orig.any(axis=2)
    final[m] = capa_orig[m]
    cv2.polylines(final, [pts.astype(np.int32)], True, VERDE, 2, cv2.LINE_AA)
    _banner(final, res)
    res.imagen_resultado = final
    etapas["Resultado"] = final
    return res
