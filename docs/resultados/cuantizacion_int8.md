# Diagnóstico: el modelo int8 de Edge Impulse pierde precisión

## Síntoma (Edge Impulse, MobileNetV2 96x96 0.35)

| Intento | float32 | int8 |
|---|---|---|
| 16 neuronas, 30 ciclos | — | 72,5 % |
| 16 neuronas, 80 ciclos | 100 % | 71,2 % |
| 64 neuronas, dropout 0,2, 30 ciclos | — | 63,4 % |

En int8 casi todos los errores van a `manzana_roja` (kiwi → manzana_roja 60–92 %),
incluso con fotos de Fruits-360, que el float32 acierta todas.

## Reproducción local

Mismo dataset (muestra de Fruits-360, 5 frutas, 750 fotos), mismo modelo
(MobileNetV2 α=0,35, 96×96, base congelada, Dense(16) por posición + Flatten, como el
bloque de Edge Impulse) y cuantización int8 post-entrenamiento de TensorFlow Lite.
Scripts en `docs/resultados/int8/` (TensorFlow 2.21, CPU).

| Prueba | float32 | int8 |
|---|---|---|
| Igual que Edge Impulse (entrada 0–1) | 100 % | 67 % (kiwi 0/32, 27 → manzana_roja) |
| Igual, con fine-tuning del 65 % superior (como Edge Impulse) | 100 % | 69 % |
| Fine-tuning de toda la red | 100 % | 58 % |
| Entrada escalada a −1…1 | 100 % | 83–89 % |

Se reproduce el mismo patrón que en Edge Impulse.

## Dónde se pierde

| Qué se cuantiza | Precisión |
|---|---|
| Solo pesos int8 (activaciones float) | 100 % |
| Pesos y activaciones int8 | 75 % |
| Pesos int8 + activaciones int16 | 77 % |
| Todo int8 menos `expanded_conv_depthwise` (1.ª depthwise) | 97 % |
| Todo int8 menos las 4 primeras capas | 98 % |
| Todo int8 menos la cabeza (Dense/softmax) | 75 % |

- El error de cada capa por separado es el normal del redondeo (~0,3 pasos), y el
  float32 tolera ruido, cambios de brillo y desplazamientos sin perder precisión.
- La pérdida aparece al cuantizar las **activaciones** de la **primera capa depthwise**
  de MobileNetV2. Sus canales tienen rangos muy distintos y comparten una sola escala
  int8 (por tensor): los canales de valores pequeños quedan reducidos a 1–2 niveles.
  Ahí está la información fina de color que separa kiwi, pera y manzana verde de la
  manzana roja. Con int16 tampoco se arregla porque la pérdida no es solo de resolución.
- Es un problema conocido de MobileNetV2 con cuantización post-entrenamiento (rangos
  muy distintos entre canales en sus capas depthwise; ver Nagel et al., 2019, *Data-Free
  Quantization Through Weight Equalization and Bias Correction*).
- Edge Impulse congela esa capa (solo hace fine-tuning de las capas superiores), así que
  cambiar neuronas, dropout o ciclos no la afecta.

## Solución

| Backbone | float32 | int8 |
|---|---|---|
| MobileNetV2 0,35 | 100 % | 67–75 % |
| **MobileNetV1 0,25** | 95 % | **92 %** |

MobileNetV1 no tiene esta caída: pierde 3 puntos al pasar a int8 en vez de 25–33.
En Edge Impulse: **MobileNetV1 96x96 0.25**.

Límites: la prueba local usa solo Fruits-360 (sin `fondo` ni fotos propias) y los pesos
ImageNet de Keras, no los de Edge Impulse. Lo que se debe confirmar en Edge Impulse es
que la diferencia float32 → int8 quede en unos pocos puntos.

## Confirmación en Edge Impulse (dataset completo: Fruits-360 + fotos propias + fondo)

MobileNetV1 96x96 0.25, sin capa densa final, dropout 0,1, 30 ciclos, lr 0,0005,
data augmentation y auto-weight classes.

| Clase | MobileNetV2 0,35 (int8) | MobileNetV1 0,25 (int8) |
|---|---|---|
| banano | 77–90 % | 96,8 % |
| fondo | 64–93 % | 100 % |
| kiwi | 8–32 % | 100 % |
| manzana_roja | 100 % (recibía los errores) | 63,6 % |
| manzana_verde | 26–74 % | 87,1 % |
| pera | 68–79 % | 63,2 % |
| **Total** | **63–72 %** | **84,3 %** (pérdida 0,35) |

MobileNetV1 0,25 en float32: **92,8 %** (pérdida 0,25). Por clase: banano 96,8 %, fondo
100 %, kiwi 96 %, manzana_roja 84,8 %, manzana_verde 96,8 %, pera 84,2 %.

Diferencia float32 → int8: 8,5 puntos (con MobileNetV2 era de 28–37). Casi toda en
manzana_roja (84,8 → 63,6 %) y pera (84,2 → 63,2 %).

Rendimiento estimado (EON Compiler, objetivo ESP-EYE / ESP32 de 240 MHz): 615 ms por
inferencia, 135,4 KB de RAM y 296,7 KB de flash (con MobileNetV2: 946 ms, 228 KB y
546 KB). Falta medirlo en el ESP32-S3, que acelera las operaciones int8.

Desaparece el colapso hacia `manzana_roja`: los errores que quedan se reparten entre
frutas parecidas (manzana roja ↔ manzana verde, pera ↔ manzanas), lo que apunta a
datos y no a la cuantización.
