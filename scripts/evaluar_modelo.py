"""Evalúa el modelo .tflite con fotos ya etiquetadas, separando las propias de las de Fruits-360.

Sirve para saber POR QUÉ falla el modelo frente a la cámara, sin adivinar:

  # tus fotos y las de Fruits-360 (dataset/<clase>/...)
  .venv/bin/python scripts/evaluar_modelo.py

  # fotos guardadas con la tecla g del ESP32 virtual (capturas/), sin etiqueta:
  # muestra qué predice y con qué confianza
  .venv/bin/python scripts/evaluar_modelo.py --capturas

  # hoja con tus fotos mal clasificadas (cada una con real → predicho) para revisarlas
  .venv/bin/python scripts/evaluar_modelo.py --errores errores.jpg

  # el modelo float32, para compararlo con el int8
  .venv/bin/python scripts/evaluar_modelo.py --modelo modelos/fruitai_f32.tflite

Usa el mismo preprocesado que el ESP32 virtual (simulador/camara.py).
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "simulador"))
from camara import ClasificadorTFLite, leer_etiquetas  # noqa: E402
from confirmacion import MAPA_POR_DEFECTO  # noqa: E402


def a_fruta(clase: str) -> str:
    """Fruta del inventario (manzana_roja y manzana_verde → manzana)."""
    return MAPA_POR_DEFECTO.get(clase, clase)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", type=Path, default=RAIZ / "modelos/fruitai.tflite")
    ap.add_argument("--etiquetas", type=Path, default=RAIZ / "modelos/etiquetas.txt")
    ap.add_argument("--dataset", type=Path, default=RAIZ / "dataset")
    ap.add_argument("--capturas", action="store_true", help="clasificar las fotos de capturas/")
    ap.add_argument("--errores", type=Path, help="guardar una hoja con las fotos propias mal clasificadas")
    args = ap.parse_args()

    etiquetas = leer_etiquetas(args.etiquetas)
    clf = ClasificadorTFLite(args.modelo, etiquetas)
    print(f"Modelo: {args.modelo.name}\n")

    if args.capturas:
        fotos = sorted((RAIZ / "capturas").glob("*.jpg"))
        if not fotos:
            raise SystemExit("No hay fotos en capturas/ (se guardan con la tecla g del ESP32 virtual).")
        for f in fotos:
            _, _, probs = clf.clasificar(cv2.imread(str(f)))
            top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
            print(f"{f.name:45} " + "  ".join(f"{k} {v:.0%}" for k, v in top))
        return

    # origen → clase real → [aciertos, total, Counter(predicciones erradas), suma confianza, aciertos inventario]
    res: dict = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, collections.Counter(), 0.0, 0]))
    errores_propias: list = []   # (imagen, real, predicho, confianza)
    for carpeta in sorted(p for p in args.dataset.iterdir() if p.is_dir()):
        real = carpeta.name
        for f in sorted(carpeta.glob("*.jpg")):
            origen = "Fruits-360" if ".f360-" in f.name else "propias"
            img = cv2.imread(str(f))
            pred, conf, _ = clf.clasificar(img)
            if origen == "propias" and pred != real:
                errores_propias.append((img, real, pred, conf))
            r = res[origen][real]
            r[1] += 1
            r[3] += conf
            r[4] += a_fruta(pred) == a_fruta(real)
            if pred == real:
                r[0] += 1
            else:
                r[2][pred] += 1

    for origen in ("propias", "Fruits-360"):
        if origen not in res:
            continue
        print(f"== Fotos {origen}")
        print(f"   {'clase':14} {'fotos':>5} {'acierta':>8} {'inventario':>10} {'conf. media':>11}   se confunde con")
        for real, (ok, n, err, suma, inv) in sorted(res[origen].items()):
            errores = ", ".join(f"{k} {v}" for k, v in err.most_common(3)) or "-"
            print(f"   {real:14} {n:5} {ok / n:8.0%} {inv / n:10.0%} {suma / n:11.0%}   {errores}")
        print()
    if args.errores:
        guardar_hoja(errores_propias, args.errores)
    print("inventario = acierto contando manzana_roja y manzana_verde como 'manzana' (así se registra el stock).")
    print("Ojo: casi todas estas fotos se usaron para entrenar, así que el resultado es optimista.\n"
          "Si una clase falla aquí, el modelo ni siquiera aprendió sus propias fotos de entrenamiento.")


def guardar_hoja(errores: list, ruta: Path, lado: int = 160, por_fila: int = 8, maximo: int = 64) -> None:
    """Junta las fotos mal clasificadas en una sola imagen, con 'real → predicho (conf)'."""
    import numpy as np

    if not errores:
        print("No hay fotos propias mal clasificadas: no se generó la hoja.\n")
        return
    errores = sorted(errores, key=lambda e: (e[1], e[2]))[:maximo]
    celdas = []
    for img, real, pred, conf in errores:
        c = cv2.resize(img, (lado, lado))
        cv2.rectangle(c, (0, lado - 34), (lado, lado), (0, 0, 0), -1)
        cv2.putText(c, real, (4, lado - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(c, f"-> {pred} {conf:.0%}", (4, lado - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
        celdas.append(c)
    while len(celdas) % por_fila:
        celdas.append(np.zeros((lado, lado, 3), np.uint8))
    filas = [np.hstack(celdas[i:i + por_fila]) for i in range(0, len(celdas), por_fila)]
    cv2.imwrite(str(ruta), np.vstack(filas))
    print(f"Hoja de errores: {ruta} ({len(errores)} fotos)\n")


if __name__ == "__main__":
    main()
