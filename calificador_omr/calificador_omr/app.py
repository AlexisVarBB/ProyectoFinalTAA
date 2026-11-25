"""
Interfaz gráfica del Sistema Calificador de Exámenes (OMR).
"""
import json
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image

import calificador
import hoja

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


ACENTO = "#3B82F6"
ACENTO_HOVER = "#2563EB"
C_OK = "#22C55E"
C_MAL = "#EF4444"
C_VACIA = "#F59E0B"
C_MULT = "#C084FC"
FONDO_TARJETA = ("#FFFFFF", "#1E2230")
FONDO_PANEL = ("#EEF1F6", "#141722")
TEXTO_SUAVE = ("#5B6476", "#9AA3B5")

ICONOS = {"correcta": "✔", "incorrecta": "✘", "vacia": "○", "multiple": "◎"}
COLORES = {"correcta": C_OK, "incorrecta": C_MAL, "vacia": C_VACIA, "multiple": C_MULT}

UMBRAL = 0.40


def a_ctk_image(img, max_w, max_h):

    if img.ndim == 2:
        rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    f = min(max_w / w, max_h / h)
    tam = (max(1, int(w * f)), max(1, int(h * f)))
    pil = Image.fromarray(rgb)
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=tam)


class Tarjeta(ctk.CTkFrame):


    def __init__(self, master, titulo, color):
        super().__init__(master, fg_color=FONDO_TARJETA, corner_radius=12)
        ctk.CTkFrame(self, width=5, height=10, fg_color=color, corner_radius=3).pack(side="left", fill="y", padx=(8, 0), pady=10)
        cont = ctk.CTkFrame(self, fg_color="transparent")
        cont.pack(side="left", fill="both", expand=True, padx=10, pady=6)
        self.valor = ctk.CTkLabel(cont, text="–", font=ctk.CTkFont(size=24, weight="bold"), anchor="w")
        self.valor.pack(fill="x")
        ctk.CTkLabel(cont, text=titulo, text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=12), anchor="w").pack(fill="x")

    def set(self, v):
        self.valor.configure(text=str(v))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Calificador de Exámenes")
        self.geometry("1440x880")
        self.minsize(1150, 720)

        self.imagen = None
        self.ruta_imagen = ""
        self.resultado = None
        self.num_preguntas = 20
        self.clave_vars = []
        self._job_redibujo = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._construir_sidebar()
        self._construir_principal()
        self._construir_clave()
        self.mostrar_estado("Carga una imagen para comenzar.")


    def _construir_sidebar(self):
        sb = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color=FONDO_PANEL)
        sb.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="Calificador", font=ctk.CTkFont(size=28, weight="bold")).pack(padx=22, pady=(26, 0), anchor="w")
        ctk.CTkLabel(sb, text="Sistema calificador de exámenes",
                     justify="left", text_color=TEXTO_SUAVE).pack(padx=22, anchor="w")

        self._seccion(sb, "EXAMEN")
        fila = ctk.CTkFrame(sb, fg_color="transparent")
        fila.pack(fill="x", padx=22)
        ctk.CTkLabel(fila, text="Preguntas").pack(side="left")
        self.opt_preguntas = ctk.CTkOptionMenu(
            fila, values=["5", "10", "15", "20", "25", "30", "40", "50"], width=90,
            command=lambda v: self.cambiar_num_preguntas(int(v)))
        self.opt_preguntas.set(str(self.num_preguntas))
        self.opt_preguntas.pack(side="right")

        self._seccion(sb, "ACCIONES")
        self._boton(sb, "Cargar imagen", self.cargar_imagen)
        self.btn_calificar = self._boton(sb, "Calificar", self.calificar, color=C_OK, hover="#16A34A")
        self.btn_calificar.configure(font=ctk.CTkFont(size=15, weight="bold"), height=44)

        abajo = ctk.CTkFrame(sb, fg_color="transparent")
        abajo.pack(side="bottom", fill="x", padx=22, pady=18)
        self.sw_tema = ctk.CTkSwitch(abajo, text="Modo oscuro", command=self.cambiar_tema)
        self.sw_tema.select()
        self.sw_tema.pack(anchor="w")

    def _seccion(self, master, texto):
        ctk.CTkLabel(master, text=texto, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=TEXTO_SUAVE).pack(padx=22, pady=(22, 6), anchor="w")

    def _boton(self, master, texto, cmd, color=ACENTO, hover=ACENTO_HOVER):
        b = ctk.CTkButton(master, text=texto, command=cmd, anchor="w", height=38,
                          fg_color=color, hover_color=hover)
        b.pack(fill="x", padx=22, pady=4)
        return b

    def _construir_principal(self):
        self.tabs = ctk.CTkTabview(self, corner_radius=14, segmented_button_selected_color=ACENTO)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=18, pady=(10, 4))
        for t in ("Calificación", "Clave de respuestas"):
            self.tabs.add(t)


        tab = self.tabs.tab("Calificación")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self.marco_img = ctk.CTkFrame(tab, fg_color=FONDO_TARJETA, corner_radius=14)
        self.marco_img.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.lbl_img = ctk.CTkLabel(self.marco_img, text="Sin imagen\n\nCarga una foto o escaneo de la hoja de respuestas",
                                    text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=15))
        self.lbl_img.pack(fill="both", expand=True, padx=10, pady=10)
        self.marco_img.bind("<Configure>", lambda e: self._programar_redibujo())

        panel = ctk.CTkFrame(tab, width=360, fg_color="transparent")
        panel.grid(row=0, column=1, sticky="ns")
        panel.grid_propagate(False)
        panel.grid_rowconfigure(3, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        tarjeta = ctk.CTkFrame(panel, fg_color=FONDO_TARJETA, corner_radius=14)
        tarjeta.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(tarjeta, text="CALIFICACIÓN", text_color=TEXTO_SUAVE,
                     font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(14, 0))
        self.lbl_calif = ctk.CTkLabel(tarjeta, text="–", font=ctk.CTkFont(size=64, weight="bold"))
        self.lbl_calif.pack()
        self.lbl_aciertos = ctk.CTkLabel(tarjeta, text="Aún no se ha calificado", text_color=TEXTO_SUAVE,
                                         font=ctk.CTkFont(size=14))
        self.lbl_aciertos.pack()
        self.barra = ctk.CTkProgressBar(tarjeta, height=10, progress_color=C_OK)
        self.barra.set(0)
        self.barra.pack(fill="x", padx=22, pady=(10, 18))

        stats = ctk.CTkFrame(panel, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", pady=10)
        stats.grid_columnconfigure((0, 1), weight=1)
        self.t_ok = Tarjeta(stats, "Correctas", C_OK)
        self.t_mal = Tarjeta(stats, "Incorrectas", C_MAL)
        self.t_vac = Tarjeta(stats, "En blanco", C_VACIA)
        self.t_mul = Tarjeta(stats, "Múltiples", C_MULT)
        for i, t in enumerate((self.t_ok, self.t_mal, self.t_vac, self.t_mul)):
            t.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)

        ctk.CTkLabel(panel, text="DETALLE POR PREGUNTA", text_color=TEXTO_SUAVE,
                     font=ctk.CTkFont(size=11, weight="bold")).grid(row=2, column=0, sticky="w", padx=4)
        self.lista_detalle = ctk.CTkScrollableFrame(panel, fg_color=FONDO_TARJETA, corner_radius=14)
        self.lista_detalle.grid(row=3, column=0, sticky="nsew", pady=(6, 0))


        self.lbl_estado = ctk.CTkLabel(self, text="", anchor="w", text_color=TEXTO_SUAVE)
        self.lbl_estado.grid(row=1, column=1, sticky="ew", padx=24, pady=(0, 8))

    def _construir_clave(self):
        tk_ = self.tabs.tab("Clave de respuestas")
        barra = ctk.CTkFrame(tk_, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(barra, text="Selecciona la respuesta correcta de cada pregunta",
                     text_color=TEXTO_SUAVE).pack(side="left")
        for txt, cmd in (("Guardar", self.guardar_clave), ("Cargar", self.cargar_clave),
                         ("Leer desde hoja", self.leer_clave_hoja)):
            ctk.CTkButton(barra, text=txt, width=120, command=cmd).pack(side="right", padx=(8, 0))
        self.marco_clave = ctk.CTkScrollableFrame(tk_, fg_color=FONDO_TARJETA, corner_radius=14)
        self.marco_clave.pack(fill="both", expand=True)
        self._dibujar_clave()

    def _dibujar_clave(self, valores=None):
        anteriores = valores or [v.get() for v in self.clave_vars]
        for w in self.marco_clave.winfo_children():
            w.destroy()
        self.clave_vars = []
        cols = 2
        for c in range(cols):
            self.marco_clave.grid_columnconfigure(c, weight=1)
        filas = (self.num_preguntas + cols - 1) // cols
        for q in range(self.num_preguntas):
            var = ctk.StringVar(value=anteriores[q] if q < len(anteriores) and anteriores[q] else "A")
            self.clave_vars.append(var)
            f = ctk.CTkFrame(self.marco_clave, fg_color="transparent")
            f.grid(row=q % filas, column=q // filas, sticky="w", padx=24, pady=4)
            ctk.CTkLabel(f, text=f"{q + 1:>2}.", width=36, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
            ctk.CTkSegmentedButton(f, values=list(hoja.OPCIONES), variable=var, width=260,
                                   selected_color=ACENTO, selected_hover_color=ACENTO_HOVER).pack(side="left")

    # -------------------------------------------------------------- acciones
    def mostrar_estado(self, texto, color=None):
        self.lbl_estado.configure(text=texto, text_color=color or TEXTO_SUAVE)

    def cambiar_tema(self):
        ctk.set_appearance_mode("dark" if self.sw_tema.get() else "light")

    def cambiar_num_preguntas(self, n):
        self.num_preguntas = n
        self._dibujar_clave()
        self.mostrar_estado(f"Examen configurado con {n} preguntas.")

    def obtener_clave(self):
        return [v.get() or None for v in self.clave_vars]

    def cargar_imagen(self):
        ruta = filedialog.askopenfilename(title="Selecciona la imagen del examen",
                                          filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"), ("Todos", "*.*")])
        if not ruta:
            return
        img = cv2.imdecode(np.fromfile(ruta, np.uint8), cv2.IMREAD_COLOR)  # soporta acentos en la ruta
        if img is None:
            messagebox.showerror("Error", "No se pudo leer la imagen.")
            return
        self.establecer_imagen(img, ruta)

    def establecer_imagen(self, img, ruta):
        self.imagen, self.ruta_imagen, self.resultado = img, ruta, None
        self._img_mostrada = img
        self._redibujar()
        self._limpiar_resultado()
        self.tabs.set("Calificación")
        self.mostrar_estado(f"Imagen cargada: {os.path.basename(ruta)} — presiona Calificar.")

    def calificar(self):
        if self.imagen is None:
            messagebox.showinfo("Calificar", "Primero carga una imagen.")
            return
        res = calificador.calificar(self.imagen, self.obtener_clave(), UMBRAL)
        self.resultado = res
        if not res.ok:
            self.mostrar_estado("✘ " + res.mensaje, C_MAL)
            messagebox.showwarning("No se pudo calificar", res.mensaje)
            return
        self._img_mostrada = res.imagen_resultado
        self._redibujar()
        self._mostrar_resultado(res)
        self.mostrar_estado(f"✔ {res.mensaje}  {res.aciertos}/{res.total} aciertos.", C_OK)

    # ------------------------------------------------------------ resultados
    def _limpiar_resultado(self):
        self.lbl_calif.configure(text="–", text_color=("#1F2430", "#FFFFFF"))
        self.lbl_aciertos.configure(text="Aún no se ha calificado")
        self.barra.set(0)
        for t in (self.t_ok, self.t_mal, self.t_vac, self.t_mul):
            t.set("–")
        for w in self.lista_detalle.winfo_children():
            w.destroy()

    def _mostrar_resultado(self, res):
        color = C_OK if res.calificacion >= 6 else C_MAL
        self.lbl_calif.configure(text=f"{res.calificacion:.1f}", text_color=color)
        self.lbl_aciertos.configure(text=f"{res.aciertos} de {res.total} correctas · {res.porcentaje:.0f}%")
        self.barra.configure(progress_color=color)
        self.barra.set(res.porcentaje / 100)
        self.t_ok.set(res.contar("correcta"))
        self.t_mal.set(res.contar("incorrecta"))
        self.t_vac.set(res.contar("vacia"))
        self.t_mul.set(res.contar("multiple"))

        for w in self.lista_detalle.winfo_children():
            w.destroy()
        for p in res.preguntas:
            fila = ctk.CTkFrame(self.lista_detalle, fg_color="transparent")
            fila.pack(fill="x", padx=6, pady=1)
            ctk.CTkLabel(fila, text=ICONOS[p.estado], text_color=COLORES[p.estado], width=24,
                         font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
            ctk.CTkLabel(fila, text=f"Pregunta {p.numero}", anchor="w", width=110).pack(side="left")
            marcada = {"*": "Varias", None: "—"}.get(p.marcada, p.marcada)
            ctk.CTkLabel(fila, text=f"Marcó: {marcada}", anchor="w", width=90).pack(side="left")
            ctk.CTkLabel(fila, text=f"Clave: {p.correcta}", text_color=TEXTO_SUAVE, anchor="w").pack(side="left")

    def _programar_redibujo(self):
        if self._job_redibujo:
            self.after_cancel(self._job_redibujo)
        self._job_redibujo = self.after(120, self._redibujar)

    def _redibujar(self):
        img = getattr(self, "_img_mostrada", None)
        if img is None:
            return
        w = max(self.marco_img.winfo_width() - 30, 300)
        h = max(self.marco_img.winfo_height() - 30, 300)
        ci = a_ctk_image(img, w, h)
        self.lbl_img.configure(image=ci, text="")
        self.lbl_img.image = ci

    # ----------------------------------------------------------------- clave
    def guardar_clave(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".json", initialfile="clave.json",
                                            filetypes=[("JSON", "*.json")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump({"preguntas": self.num_preguntas, "clave": self.obtener_clave()}, f, indent=2)
            self.mostrar_estado("Clave guardada.", C_OK)

    def cargar_clave(self):
        ruta = filedialog.askopenfilename(title="Selecciona el archivo de la clave",
                                          filetypes=[("JSON", "*.json")])
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
            clave = [c.upper() if c else None for c in datos["clave"]][:hoja.MAX_PREGUNTAS]
        except Exception as e:
            messagebox.showerror("Error", f"Archivo de clave inválido:\n{e}")
            return
        self.num_preguntas = len(clave)
        valores = list(self.opt_preguntas.cget("values"))
        if str(self.num_preguntas) not in valores:
            self.opt_preguntas.configure(values=sorted(set(valores) | {str(self.num_preguntas)}, key=int))
        self.opt_preguntas.set(str(self.num_preguntas))
        self._dibujar_clave(clave)
        self.mostrar_estado(f"Clave cargada ({self.num_preguntas} preguntas).", C_OK)

    def leer_clave_hoja(self):
        ruta = filedialog.askopenfilename(title="Hoja contestada con las respuestas correctas",
                                          filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp"), ("Todos", "*.*")])
        if not ruta:
            return
        img = cv2.imdecode(np.fromfile(ruta, np.uint8), cv2.IMREAD_COLOR)
        res = calificador.calificar(img, ["A"] * self.num_preguntas, UMBRAL)
        if not res.ok:
            messagebox.showwarning("Clave", res.mensaje)
            return
        leidas = res.respuestas()
        faltantes = [i + 1 for i, l in enumerate(leidas) if l is None]
        self._dibujar_clave([l or "A" for l in leidas])
        msg = f"Clave leída desde la hoja ({self.num_preguntas} preguntas)."
        if faltantes:
            msg += f" Revisa las preguntas sin marca clara: {faltantes}"
        self.mostrar_estado(msg, C_VACIA if faltantes else C_OK)


if __name__ == "__main__":
    App().mainloop()
