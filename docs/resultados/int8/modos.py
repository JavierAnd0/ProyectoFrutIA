import numpy as np, tensorflow as tf
d = np.load("datos.npz"); X, y, tr, va = d["X"], d["y"], d["tr"], d["va"]
m = tf.keras.models.load_model("modelo_ei.keras", safe_mode=False)
rep = lambda: ([X[i:i+1]] for i in tr[:300])
def evaluar(tfl):
    it = tf.lite.Interpreter(model_content=tfl); it.allocate_tensors()
    ei, eo = it.get_input_details()[0], it.get_output_details()[0]
    ok = 0
    for i in va:
        x = X[i:i+1]
        if ei["dtype"] == np.int8:
            s, z = ei["quantization"]; x = np.clip(np.round(x / s + z), -128, 127).astype(np.int8)
        it.set_tensor(ei["index"], x); it.invoke()
        ok += int(np.argmax(it.get_tensor(eo["index"])[0]) == y[i])
    return ok / len(va)
def conv(**kw):
    c = tf.lite.TFLiteConverter.from_keras_model(m)
    for k, v in kw.items(): setattr(c, k, v) if k != "ops" else setattr(c.target_spec, "supported_ops", v)
    return c.convert()
O = [tf.lite.Optimize.DEFAULT]
print("MODO solo pesos int8 (dynamic range):", evaluar(conv(optimizations=O)))
print("MODO int8 completo, E/S float:", evaluar(conv(optimizations=O, representative_dataset=rep)))
print("MODO int8 completo, E/S int8:", evaluar(conv(optimizations=O, representative_dataset=rep, ops=[tf.lite.OpsSet.TFLITE_BUILTINS_INT8], inference_input_type=tf.int8, inference_output_type=tf.int8)))
print("MODO activaciones int16 + pesos int8:", evaluar(conv(optimizations=O, representative_dataset=rep, ops=[tf.lite.OpsSet.EXPERIMENTAL_TFLITE_BUILTINS_ACTIVATIONS_INT16_WEIGHTS_INT8])))
