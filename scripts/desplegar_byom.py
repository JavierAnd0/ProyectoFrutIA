"""Convierte modelos/fruitai.tflite (QAT int8) en la librería Arduino de Edge Impulse.

El firmware (firmware/fruitai_camara) usa la librería que genera Edge Impulse
(`run_classifier`). El modelo v5 se reentrenó fuera de Edge Impulse (QAT,
scripts/entrenar_qat.py), así que se sube como modelo propio ("Bring Your Own Model")
a un proyecto de Edge Impulse **aparte** y se descarga la librería. El firmware no cambia.

Importante: subir un modelo propio reemplaza el impulse del proyecto. Usar un proyecto
vacío (p. ej. "FruitAI-v5-BYOM"), nunca el proyecto donde están los datos.

  pip install edgeimpulse
  EI_API_KEY=ei_... python scripts/desplegar_byom.py
  # → firmware/fruitai_camara/libreria/fruitai_byom_arduino.zip
  #   (Arduino IDE → Sketch → Include Library → Add .ZIP Library)

La API key es la del proyecto vacío (Dashboard → Keys, rol Admin).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", type=Path, default=RAIZ / "modelos/fruitai.tflite")
    ap.add_argument("--etiquetas", type=Path, default=RAIZ / "modelos/etiquetas.txt")
    ap.add_argument("--salida", type=Path, default=RAIZ / "firmware/fruitai_camara/libreria")
    ap.add_argument("--motor", default="tflite-eon", choices=["tflite-eon", "tflite"],
                    help="EON compila el modelo a C++ (menos RAM); tflite usa el intérprete")
    args = ap.parse_args()

    import edgeimpulse as ei

    clave = os.environ.get("EI_API_KEY")
    if not clave:
        raise SystemExit("Falta EI_API_KEY (API key del proyecto VACÍO de Edge Impulse).")
    ei.API_KEY = clave

    etiquetas = [l.strip() for l in args.etiquetas.read_text().splitlines() if l.strip()]
    args.salida.mkdir(parents=True, exist_ok=True)
    print(f"Subiendo {args.modelo.name} ({args.modelo.stat().st_size // 1024} KB), clases {etiquetas}…")
    ei.model.deploy(
        model=str(args.modelo),
        model_output_type=ei.model.output_type.Classification(labels=etiquetas),
        # Igual que el bloque "Image" de Edge Impulse y que el ESP32 virtual: píxeles 0..1
        model_input_type=ei.model.input_type.ImageInput(scaling_range="0..1"),
        deploy_model_type="int8",
        engine=args.motor,
        deploy_target="arduino",
        output_directory=str(args.salida),
    )
    for f in sorted(args.salida.glob("*.zip")):
        print(f"Librería: {f.relative_to(RAIZ)} ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
