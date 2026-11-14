# Dónde se pierde la precisión al pasar a int8: error por capa (QuantizationDebugger).
import sys, numpy as np, tensorflow as tf
exec(open("rep.py").read().split("conv = tf.lite")[0])   # entrena igual que rep.py
conv = tf.lite.TFLiteConverter.from_keras_model(m)
conv.optimizations = [tf.lite.Optimize.DEFAULT]
rep = lambda: ([X[i:i+1]] for i in tr[:300])
conv.representative_dataset = rep
dbg = tf.lite.experimental.QuantizationDebugger(converter=conv, debug_dataset=lambda: ([X[i:i+1]] for i in va[:60]))
dbg.run()
dbg.layer_statistics_dump(open("stats.csv","w"))
m.save("modelo_ei.keras"); np.savez("datos.npz", X=X, y=y, tr=tr, va=va)
print("RESULTADO", facc)
