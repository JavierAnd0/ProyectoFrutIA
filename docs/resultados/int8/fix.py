import sys, numpy as np, tensorflow as tf
d = np.load("datos.npz"); X, y, tr, va = d["X"], d["y"], d["tr"], d["va"]
MODO = sys.argv[1]; tf.random.set_seed(0)
def entrenar_y_cuantizar(backbone, entrada):
    ent = tf.keras.Input((96, 96, 3)); x = ent * 2.0 - 1.0 if entrada == "-1_1" else ent
    x = backbone(x, training=False)
    x = tf.keras.layers.Reshape((-1, x.shape[-1]))(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x); x = tf.keras.layers.Dropout(0.1)(x)
    x = tf.keras.layers.Flatten()(x); sal = tf.keras.layers.Dense(5, activation="softmax")(x)
    m = tf.keras.Model(ent, sal)
    backbone.trainable = False
    m.compile(optimizer=tf.keras.optimizers.Adam(5e-4), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    m.fit(X[tr], y[tr], epochs=30, batch_size=32, verbose=0)
    if MODO.startswith("ft"):
        pct = {"ft65": 0.65, "ft100": 1.0}[MODO.split("_")[0]]
        backbone.trainable = True
        n = len(backbone.layers); desde = int(n * (1 - pct))
        for l in backbone.layers[:desde]: l.trainable = False
        for l in backbone.layers:
            if isinstance(l, tf.keras.layers.BatchNormalization): l.trainable = False
        m.compile(optimizer=tf.keras.optimizers.Adam(5e-5), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        m.fit(X[tr], y[tr], epochs=10, batch_size=32, verbose=0)
    facc = m.evaluate(X[va], y[va], verbose=0)[1]
    c = tf.lite.TFLiteConverter.from_keras_model(m); c.optimizations = [tf.lite.Optimize.DEFAULT]
    c.representative_dataset = lambda: ([X[i:i+1]] for i in tr[:300])
    it = tf.lite.Interpreter(model_content=c.convert()); it.allocate_tensors()
    ei, eo = it.get_input_details()[0], it.get_output_details()[0]; pred = []
    for i in va:
        it.set_tensor(ei["index"], X[i:i+1]); it.invoke(); pred.append(int(np.argmax(it.get_tensor(eo["index"])[0])))
    print(f"FIX {MODO} entrada={entrada} float32={facc:.3f} int8={np.mean(np.array(pred) == y[va]):.3f}", flush=True)
entrada = sys.argv[2]
if MODO.startswith("v1"):
    bb = tf.keras.applications.MobileNet(input_shape=(96, 96, 3), alpha=0.25, include_top=False, weights="imagenet")
else:
    bb = tf.keras.applications.MobileNetV2(input_shape=(96, 96, 3), alpha=0.35, include_top=False, weights="imagenet")
entrenar_y_cuantizar(bb, entrada)
