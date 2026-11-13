"""Imagen y clasificación comunes a la captura del dataset y al ESP32 virtual.

El recorte imita lo que verá el ESP32-S3: la cámara OV2640 entrega 320x240 y
Edge Impulse usa un cuadrado (normalmente 96x96). Aquí se toma el cuadrado
central de la webcam, que es lo que se marca en pantalla.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import cv2
import numpy as np


# Cámara por defecto. En el Mac, si el iPhone aparece como cámara (Cámara de
# Continuidad), la 0 puede ser el iPhone: fija la del Mac con
#   export FRUITAI_CAMARA=1      (el número que muestre --listar-camaras)
CAMARA_POR_DEFECTO = os.environ.get("FRUITAI_CAMARA", "0")


def listar_camaras(maximo: int = 4) -> None:
    """Muestra las cámaras disponibles: nombre (macOS) y una vista de cada índice.

    OpenCV no da el nombre de cada índice, así que se abre cada uno, se muestra
    un fotograma con su número y se reconoce a ojo cuál es la del Mac.
    """
    if platform.system() == "Darwin":
        try:
            info = subprocess.run(["system_profiler", "SPCameraDataType"],
                                  capture_output=True, text=True, timeout=10).stdout
            nombres = [l.strip().rstrip(":") for l in info.splitlines()
                       if l.startswith("    ") and not l.startswith("      ") and l.strip().endswith(":")]
            print("Cámaras conectadas:", ", ".join(nombres) or "ninguna")
        except (OSError, subprocess.SubprocessError):
            pass
    encontradas = []
    for i in range(maximo):
        cap = cv2.VideoCapture(i)
        ok, frame = cap.read() if cap.isOpened() else (False, None)
        cap.release()
        if not ok:
            continue
        h, w = frame.shape[:2]
        encontradas.append(i)
        print(f"  --camara {i}: {w}x{h}")
        cv2.putText(frame, f"--camara {i}   (tecla para seguir)", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        cv2.imshow("FruitAI - camaras", frame)
        cv2.waitKey(0)
    if encontradas:
        cv2.destroyAllWindows()
    if not encontradas:
        print("No se encontró ninguna cámara (¿permiso de cámara en macOS?).")
    else:
        print("Usa la del Mac con --camara N, o fíjala para siempre: export FRUITAI_CAMARA=N")


def abrir_camara(fuente: str | int) -> cv2.VideoCapture:
    """`fuente`: índice de cámara (0 = la del Mac) o ruta a un video."""
    if isinstance(fuente, str) and fuente.isdigit():
        fuente = int(fuente)
    cap = cv2.VideoCapture(fuente)
    if not cap.isOpened():
        raise SystemExit(
            f"No se pudo abrir la cámara {fuente!r}.\n"
            "En macOS: Ajustes del Sistema → Privacidad y seguridad → Cámara → "
            "activa la app desde la que ejecutas esto (Terminal, iTerm, VS Code…)."
        )
    return cap


def recorte_central(frame: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int]]:
    """Devuelve el cuadrado central y (x, y, lado) para dibujarlo."""
    h, w = frame.shape[:2]
    lado = min(h, w)
    x, y = (w - lado) // 2, (h - lado) // 2
    return frame[y:y + lado, x:x + lado], (x, y, lado)


def leer_etiquetas(ruta: Path) -> list[str]:
    return [l.strip() for l in ruta.read_text().splitlines() if l.strip()]


class ClasificadorTFLite:
    """Ejecuta un modelo .tflite (p. ej. el exportado de Edge Impulse).

    Lee del propio modelo el tamaño de entrada, si es en color o en gris y si
    está cuantizado (int8/uint8), así que sirve el mismo archivo que luego va al
    ESP32. Las imágenes se escalan a 0–1 como hace el bloque "Image" de Edge
    Impulse.
    """

    def __init__(self, modelo: Path, etiquetas: list[str]):
        from ai_edge_litert.interpreter import Interpreter

        self.interp = Interpreter(model_path=str(modelo))
        self.interp.allocate_tensors()
        self.ent = self.interp.get_input_details()[0]
        self.sal = self.interp.get_output_details()[0]
        _, self.alto, self.ancho, self.canales = self.ent["shape"]
        n_salidas = int(self.sal["shape"][-1])
        if n_salidas != len(etiquetas):
            raise SystemExit(
                f"El modelo tiene {n_salidas} clases y etiquetas.txt tiene {len(etiquetas)}. "
                "Edge Impulse ordena las clases alfabéticamente: escríbelas en ese orden."
            )
        self.etiquetas = etiquetas

    def preparar(self, cuadrado_bgr: np.ndarray) -> np.ndarray:
        img = cv2.resize(cuadrado_bgr, (self.ancho, self.alto), interpolation=cv2.INTER_AREA)
        if self.canales == 1:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[..., None]
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        x = img.astype(np.float32) / 255.0
        tipo = self.ent["dtype"]
        if tipo in (np.int8, np.uint8):
            escala, cero = self.ent["quantization"]
            info = np.iinfo(tipo)
            x = np.clip(np.round(x / escala + cero), info.min, info.max)
        return x.astype(tipo)[None, ...]

    def clasificar(self, cuadrado_bgr: np.ndarray) -> tuple[str, float, dict[str, float]]:
        self.interp.set_tensor(self.ent["index"], self.preparar(cuadrado_bgr))
        self.interp.invoke()
        y = self.interp.get_tensor(self.sal["index"])[0].astype(np.float32)
        escala, cero = self.sal["quantization"]
        if escala:
            y = (y - cero) * escala
        if not np.isclose(y.sum(), 1.0, atol=0.05) or y.min() < 0:   # logits → softmax
            y = np.exp(y - y.max())
            y = y / y.sum()
        i = int(np.argmax(y))
        return self.etiquetas[i], float(y[i]), dict(zip(self.etiquetas, map(float, y)))
