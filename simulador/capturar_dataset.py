"""Captura del dataset con la cámara del Mac (plan v4, día 6, mientras llega el ESP32).

  .venv/bin/python simulador/capturar_dataset.py
  .venv/bin/python simulador/capturar_dataset.py --clases manzana_roja,pera,banano,kiwi,fondo

Teclas:
  1..9   guardar una foto de la clase con ese número
  r      ráfaga on/off: guarda una foto cada --cada segundos de la clase elegida
  q      salir

Las fotos se guardan en dataset/<clase>/<clase>.<n>.jpg (cuadrado central). Con
ese nombre, Edge Impulse deduce la etiqueta al subirlas ("Infer from filename").

Consejos: fondo y luz fijos (cartulina blanca + lámpara), distintas posiciones y
giros de cada fruta, y fotos de "fondo" sin fruta. Cuando llegue el ESP32-S3 hay
que recapturar con su cámara: el modelo funciona mejor con la cámara real.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from camara import abrir_camara, recorte_central

RAIZ = Path(__file__).resolve().parent.parent
CLASES = "manzana_roja,manzana_verde,pera,banano,kiwi,fondo"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clases", default=CLASES)
    ap.add_argument("--camara", default="0", help="índice de cámara o ruta a un video")
    ap.add_argument("--salida", type=Path, default=RAIZ / "dataset")
    ap.add_argument("--lado", type=int, default=240, help="lado en píxeles de la foto guardada")
    ap.add_argument("--cada", type=float, default=0.4, help="segundos entre fotos en ráfaga")
    args = ap.parse_args()

    clases = [c.strip() for c in args.clases.split(",") if c.strip()][:9]
    for c in clases:
        (args.salida / c).mkdir(parents=True, exist_ok=True)
    cuenta = {c: len(list((args.salida / c).glob("*.jpg"))) for c in clases}

    cap = abrir_camara(args.camara)
    elegida, rafaga, ultima = 0, False, 0.0
    aviso, aviso_hasta = "", 0.0

    def guardar(i: int, cuadrado) -> None:
        c = clases[i]
        cuenta[c] += 1
        foto = cv2.resize(cuadrado, (args.lado, args.lado), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(args.salida / c / f"{c}.{int(time.time() * 1000)}.jpg"), foto)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cuadrado, (x, y, lado) = recorte_central(frame)
        cuadrado = cuadrado.copy()
        ahora = time.time()
        if rafaga and ahora - ultima >= args.cada:
            guardar(elegida, cuadrado)
            ultima = ahora

        vista = frame.copy()
        color = (0, 0, 255) if rafaga else (0, 255, 0)
        cv2.rectangle(vista, (x, y), (x + lado, y + lado), color, 3)
        for i, c in enumerate(clases):
            marca = ">" if i == elegida else " "
            cv2.putText(vista, f"{marca}{i + 1} {c}: {cuenta[c]}", (10, 30 + 28 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        estado = f"RAFAGA {clases[elegida]}" if rafaga else "1-9 foto | r rafaga | q salir"
        cv2.putText(vista, estado, (10, vista.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        if ahora < aviso_hasta:
            cv2.putText(vista, aviso, (10, vista.shape[0] - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow("FruitAI - captura de dataset", vista)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla == ord("r"):
            rafaga = not rafaga
        elif ord("1") <= tecla <= ord("9") and tecla - ord("1") < len(clases):
            elegida = tecla - ord("1")
            if not rafaga:
                guardar(elegida, cuadrado)
                aviso, aviso_hasta = f"Guardada: {clases[elegida]}", ahora + 0.8

    cap.release()
    cv2.destroyAllWindows()
    print("Fotos por clase:", ", ".join(f"{c}={n}" for c, n in cuenta.items()))
    print(f"Carpeta: {args.salida}")


if __name__ == "__main__":
    main()
