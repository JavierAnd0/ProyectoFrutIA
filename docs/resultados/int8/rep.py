# Reproduce el bloque "Transfer learning" de Edge Impulse y compara float32 vs int8.
import sys, glob, os, numpy as np, tensorflow as tf
from PIL import Image
rng = np.random.default_rng(0); tf.random.set_seed(0)
DS = sys.argv[1]; ESCALA = sys.argv[2]; CABEZA = sys.argv[3]
clases = sorted(os.listdir(DS))
X, y, grupo = [], [], []
for i, c in enumerate(clases):
    for f in sorted(glob.glob(f"{DS}/{c}/*.jpg")):
        X.append(np.asarray(Image.open(f).convert("RGB").resize((96, 96), Image.BILINEAR), np.float32) / 255.0)
        y.append(i); grupo.append(os.path.basename(f).split("-")[1] if "f360" in f else "propia")
X, y = np.stack(X), np.array(y)
idx = rng.permutation(len(X)); corte = int(.8 * len(X))
tr, va = idx[:corte], idx[corte:]
base = tf.keras.applications.MobileNetV2(input_shape=(96, 96, 3), alpha=0.35, include_top=False, weights="imagenet")
base.trainable = False
ent = tf.keras.Input((96, 96, 3))
x = ent * 2.0 - 1.0 if ESCALA == "-1_1" else ent
if CABEZA == "ei":   # como el bloque de Edge Impulse: corta en layers[-3], Dense(16) por posición, Flatten
    corte_m = tf.keras.Model(base.inputs, base.layers[-3].output); corte_m.trainable = False
    x = corte_m(x, training=False)
    x = tf.keras.layers.Reshape((-1, x.shape[-1]))(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.1)(x)
    x = tf.keras.layers.Flatten()(x)
elif CABEZA == "gap":
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.1)(x)
else:
    x = base(x, training=False)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.1)(x)
sal = tf.keras.layers.Dense(len(clases), activation="softmax")(x)
m = tf.keras.Model(ent, sal)
m.compile(optimizer=tf.keras.optimizers.Adam(0.0005), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
m.fit(X[tr], y[tr], validation_data=(X[va], y[va]), epochs=30, batch_size=32, verbose=0)
facc = m.evaluate(X[va], y[va], verbose=0)[1]
conv = tf.lite.TFLiteConverter.from_keras_model(m)
conv.optimizations = [tf.lite.Optimize.DEFAULT]
conv.representative_dataset = lambda: ([X[i:i+1]] for i in tr[:300])
conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
conv.inference_input_type = conv.inference_output_type = tf.int8
tfl = conv.convert(); open(f"/tmp/claude-0/exp/m_{CABEZA}_{ESCALA}.tflite", "wb").write(tfl)
it = tf.lite.Interpreter(model_content=tfl); it.allocate_tensors()
ei, eo = it.get_input_details()[0], it.get_output_details()[0]
s, z = ei["quantization"]; pred = []
for i in va:
    it.set_tensor(ei["index"], np.clip(np.round(X[i:i+1] / s + z), -128, 127).astype(np.int8)); it.invoke()
    pred.append(int(np.argmax(it.get_tensor(eo["index"])[0])))
pred = np.array(pred); print(f"RESULTADO cabeza={CABEZA} entrada={ESCALA} float32={facc:.3f} int8={(pred == y[va]).mean():.3f}")
cm = np.zeros((len(clases),) * 2, int)
for a, b in zip(y[va], pred): cm[a, b] += 1
print(cm.tolist())
