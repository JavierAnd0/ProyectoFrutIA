# ESP32-S3 virtual con la cámara del Mac

Mientras llega el ESP32-S3 con cámara, el Mac hace de ESP32. Se puede avanzar
todo el tramo TinyML del plan (días 6–10) con el mismo flujo que tendrá el
hardware:

```
webcam ─► modelo .tflite (Edge Impulse) ─► confirmación anti-duplicados ─► tecla e/s ─► MQTT ─► servicio ─► SQLite ─► HA
```

| Pieza del ESP32 real            | En el Mac                                                   |
|---------------------------------|-------------------------------------------------------------|
| Cámara OV2640                   | Webcam (cuadrado central de la imagen)                      |
| Modelo TinyML de Edge Impulse   | El mismo `.tflite` int8 exportado, con LiteRT               |
| Lógica de confirmación (C++)    | `simulador/confirmacion.py` (se traduce casi línea por línea)|
| Botones Entrada / Salida        | Teclas `e` / `s`                                            |
| Sensor de presencia             | Tecla `p`                                                   |
| LED                             | Círculo arriba a la derecha (gris, verde = confirmada, azul = registrada) |
| Puerto serie                    | La consola                                                  |
| MQTT (usuario `esp32`)          | Igual: mismos tópicos, mismo JSON, LWT en `fruitai/esp32/estado` |

**Límite:** la webcam no es la OV2640 (otro color, nitidez y ángulo). Sirve para
probar el flujo, ajustar el umbral y tener un primer modelo. Cuando llegue el
ESP32 hay que **recapturar el dataset con su cámara y reentrenar** (plan v4,
sección 5).

## Instalación (una vez)

```bash
.venv/bin/pip install -r requirements-camara.txt
```

La primera vez, macOS pide permiso de cámara para la app desde la que ejecutas el
comando (Terminal, iTerm, VS Code…). Si no aparece: Ajustes del Sistema →
Privacidad y seguridad → Cámara.

## 1. Probar el flujo sin modelo

```bash
docker compose up -d
.venv/bin/python simulador/esp32_virtual.py
```

Pulsa `3` (la cámara "ve" una pera) → en ~1 s queda **CONFIRMADA** → `e` registra
una entrada → mira el stock en HA o con `./scripts/fruitai.sh db`. Si vuelves a
pulsar `e` sin retirar la fruta, se ignora. `0` (fondo) retira la fruta y rearma.

## 2. Capturar el dataset con la webcam

```bash
.venv/bin/python simulador/capturar_dataset.py
```

- Fondo y luz fijos (cartulina blanca + lámpara), la fruta dentro del cuadrado.
- `1..6` guarda una foto de esa clase; `r` activa la ráfaga (una foto cada 0,4 s)
  mientras giras y mueves la fruta.
- Meta: ~100 fotos por clase, más "fondo" (sin fruta, con la mano, sombras…).
- Las fotos quedan en `dataset/<clase>/<clase>.<n>.jpg` (no se suben a git).

## 3. Entrenar en Edge Impulse

1. Proyecto nuevo → **Data acquisition → Upload data** → sube las carpetas de
   `dataset/`, con la etiqueta deducida del nombre del archivo y división
   automática entrenamiento/prueba.
2. **Impulse design**: imagen 96×96 → bloque **Image** (RGB) → **Transfer
   learning** (MobileNetV2 pequeño, p. ej. 0.35, cabe en el ESP32-S3 con PSRAM).
3. Entrena y guarda la **precisión y la matriz de confusión** (evidencia del día 7).
4. **Dashboard → descargar el modelo TensorFlow Lite (int8 quantized)** y guárdalo
   como `modelos/fruitai.tflite`.
5. Crea `modelos/etiquetas.txt` con una clase por línea **en orden alfabético**
   (así las ordena Edge Impulse):
   ```
   banano
   fondo
   kiwi
   manzana_roja
   manzana_verde
   pera
   ```

## 4. Ejecutar el ESP32 virtual con el modelo

```bash
.venv/bin/python simulador/esp32_virtual.py --modelo modelos/fruitai.tflite
```

Opciones útiles: `--umbral 0.75` (confianza mínima), `--frames 5` (fotogramas
seguidos para confirmar; a 5 inferencias/s es ~1 s), `--fps 5`, `--sin-mqtt`.

En pantalla se ve qué predice el modelo, con qué confianza y cuántos ms tarda.
Si el servicio rechaza un movimiento (p. ej. salida con stock 0), el aviso
aparece en la ventana.

## Qué sirve para el documento

- Captura del dataset y de la matriz de confusión (secciones 9.5–9.6).
- Pruebas de la lógica anti-duplicados: `.venv/bin/python -m pytest -q simulador/tests`
  (sección 9.7).
- Un video corto de la ventana del ESP32 virtual + HA actualizándose es un buen
  respaldo del checkpoint del día 10 mientras no hay hardware.
