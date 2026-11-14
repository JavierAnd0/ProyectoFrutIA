"""Reentrena el modelo de Edge Impulse con quantization-aware training (QAT) y exporta el int8.

Por qué: la cuantización post-entrenamiento de Edge Impulse pierde precisión en las clases
parecidas (ver docs/resultados/cuantizacion_int8.md). QAT entrena simulando int8, así el
modelo aprende a no depender de diferencias que el redondeo borra.

Toma del proyecto de Edge Impulse (por la API) los mismos datos y el modelo Keras ya
entrenado, hace QAT de toda la red y guarda modelos/fruitai.tflite (int8, misma entrada
que el de Edge Impulse: 96x96x3, escala 1/255, punto cero −128).

  pip install tensorflow tf_keras tensorflow-model-optimization
  EI_API_KEY=ei_... python scripts/entrenar_qat.py --proyecto 1164175

La clave se crea en Edge Impulse → Dashboard → Keys (basta Read-only).
"""
from __future__ import annotations

import argparse
import io
import os
import urllib.request
import zipfile
from pathlib import Path

os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")   # tfmot necesita Keras 2 (tf_keras)

RAIZ = Path(__file__).resolve().parent.parent


def bajar(url: str) -> bytes:
    req = urllib.request.Request(url)
    if os.environ.get("EI_API_KEY"):
        req.add_header("x-api-key", os.environ["EI_API_KEY"])
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proyecto", type=int, required=True, help="ID del proyecto de Edge Impulse")
    ap.add_argument("--bloque-dsp", type=int, default=4, help="ID del bloque Image")
    ap.add_argument("--bloque-learn", type=int, default=5, help="ID del bloque Transfer learning")
    ap.add_argument("--epocas", type=int, default=15)
    ap.add_argument("--salida", type=Path, default=RAIZ / "modelos/fruitai.tflite")
    args = ap.parse_args()

    import numpy as np
    import tensorflow as tf
    import tf_keras as k
    import tensorflow_model_optimization as tfmot

    tf.random.set_seed(0)
    np.random.seed(0)
    api = f"https://studio.edgeimpulse.com/v1/api/{args.proyecto}"
    npy = lambda ruta: np.load(io.BytesIO(bajar(f"{api}/{ruta}")))
    print("Descargando datos y modelo de Edge Impulse…")
    X = npy(f"dsp-data/{args.bloque_dsp}/x/training").reshape(-1, 96, 96, 3)
    Y = npy(f"dsp-data/{args.bloque_dsp}/y/training")[:, 0] - 1      # etiquetas de Edge Impulse: 1..N
    Xt = npy(f"dsp-data/{args.bloque_dsp}/x/testing").reshape(-1, 96, 96, 3)
    Yt = npy(f"dsp-data/{args.bloque_dsp}/y/testing")[:, 0] - 1
    zip_h5 = zipfile.ZipFile(io.BytesIO(bajar(f"{api}/learn-data/{args.bloque_learn}/model/tflite-h5")))
    ruta_h5 = Path("/tmp/fruitai_model.h5")
    ruta_h5.write_bytes(zip_h5.read("model.h5"))
    clases = int(Y.max()) + 1

    m = k.models.load_model(ruta_h5, compile=False)
    base = m.layers[0]
    # tfmot no acepta modelos anidados: se aplana la base (MobileNetV1 es una cadena simple)
    plano = k.Sequential([k.Input((96, 96, 3))] + list(base.layers[1:]) + m.layers[1:])
    plano.set_weights(base.get_weights() + [w for l in m.layers[1:] for w in l.get_weights()])
    for capa in plano.layers:
        capa.trainable = True
    print(f"float32 de Edge Impulse, prueba: {(plano.predict(Xt, verbose=0).argmax(1) == Yt).mean():.1%}")

    q = tfmot.quantization.keras.quantize_model(plano)
    q.compile(optimizer=k.optimizers.Adam(1e-4), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    cuenta = np.bincount(Y, minlength=clases)
    pesos = {i: len(Y) / (clases * c) for i, c in enumerate(cuenta)}     # como "auto-weight classes"

    def aumentar(x, y):
        x = tf.image.random_flip_left_right(x)
        x = tf.image.random_brightness(x, 0.1)
        return tf.clip_by_value(x, 0, 1), y

    ds = tf.data.Dataset.from_tensor_slices((X, Y)).shuffle(1000, seed=0).map(aumentar).batch(32)
    q.fit(ds, epochs=args.epocas, class_weight=pesos, verbose=2)

    conv = tf.lite.TFLiteConverter.from_keras_model(q)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = lambda: ([X[i:i + 1]] for i in range(0, len(X), 3))
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = conv.inference_output_type = tf.int8
    modelo = conv.convert()

    it = tf.lite.Interpreter(model_content=modelo)
    it.allocate_tensors()
    ent, sal = it.get_input_details()[0], it.get_output_details()[0]
    s, z = ent["quantization"]
    pred = []
    for x in Xt:
        it.set_tensor(ent["index"], np.clip(np.round(x[None] / s + z), -128, 127).astype(np.int8))
        it.invoke()
        pred.append(int(it.get_tensor(sal["index"])[0].argmax()))
    print(f"QAT int8, prueba: {(np.array(pred) == Yt).mean():.1%}")
    args.salida.write_bytes(modelo)
    print(f"Guardado {args.salida} ({len(modelo) // 1024} KB)")


if __name__ == "__main__":
    main()
