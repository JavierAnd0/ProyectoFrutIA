import numpy as np, tensorflow as tf, csv
d = np.load("datos.npz"); X, y, tr, va = d["X"], d["y"], d["tr"], d["va"]
m = tf.keras.models.load_model("modelo_ei.keras", safe_mode=False)
rep = lambda: ([X[i:i+1]] for i in tr[:300])
nombres = [f["tensor_name"] for f in csv.DictReader(open("stats.csv"))]
def evaluar(tfl):
    it = tf.lite.Interpreter(model_content=tfl); it.allocate_tensors()
    ei, eo = it.get_input_details()[0], it.get_output_details()[0]; ok = 0
    for i in va:
        it.set_tensor(ei["index"], X[i:i+1]); it.invoke()
        ok += int(np.argmax(it.get_tensor(eo["index"])[0]) == y[i])
    return ok / len(va)
def sin(nodos):
    c = tf.lite.TFLiteConverter.from_keras_model(m); c.optimizations = [tf.lite.Optimize.DEFAULT]; c.representative_dataset = rep
    dbg = tf.lite.experimental.QuantizationDebugger(converter=c, debug_dataset=lambda: ([X[i:i+1]] for i in va[:2]),
          debug_options=tf.lite.experimental.QuantizationDebugOptions(denylisted_nodes=nodos))
    return evaluar(dbg.get_nondebug_quantized_model())
n = len(nombres)
print("PRUEBA todo int8:", sin([]))
for k in (4, 12, 30, 50, 63, 66):
    print(f"PRUEBA capas 0..{k-1} en float, resto int8:", sin(nombres[:k]))
for k in (63, 66, 70):
    print(f"PRUEBA capas {k}.. en float (cabeza), resto int8:", sin(nombres[k:]))
