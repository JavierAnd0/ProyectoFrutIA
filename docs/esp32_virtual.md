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

### Si abre la cámara del iPhone en vez de la del Mac

Con la **Cámara de Continuidad**, macOS ofrece el iPhone como cámara web y a veces
queda como cámara 0. Al abrirla, el iPhone se "desconecta" y pasa a ser la cámara.

```bash
.venv/bin/python simulador/capturar_dataset.py --listar-camaras
```

Muestra una vista de cada cámara con su número (cualquier tecla pasa a la
siguiente). Luego usa la del Mac, por ejemplo la 1, con `--camara 1`, o fíjala para
toda la sesión de la terminal: `export FRUITAI_CAMARA=1`.

Para que el iPhone no vuelva a aparecer: en el iPhone, **Ajustes → General →
AirPlay y Continuidad → Cámara de Continuidad** (desactivar).

## 1. Probar el flujo sin modelo

```bash
docker compose up -d
.venv/bin/python simulador/esp32_virtual.py
```

Pulsa `3` (la cámara "ve" una pera) → en ~1 s queda **CONFIRMADA** → `e` registra
una entrada → mira el stock en HA o con `./scripts/fruitai.sh db`. Si vuelves a
pulsar `e` sin retirar la fruta, se ignora. `0` (fondo) retira la fruta y rearma.

## 2. Dataset: Fruits-360 + fotos propias

El dataset es mixto:

| Origen | Clases | Por clase |
|---|---|---|
| [Fruits-360](https://github.com/fruits-360/fruits-360-100x100) (Mihai Oltean, CC BY-SA 4.0), 100×100, fondo blanco | manzana_roja, manzana_verde, pera, banano, kiwi | 150 |
| Fotos propias en el montaje (webcam ahora, ESP32 después) | las 5 frutas | 30–50 |
| Fotos propias | fondo | ~100 |

Fruits-360 aporta variedad (varias manzanas, peras y bananos); las fotos propias
adaptan el modelo a la luz, el fondo y la cámara reales, y "fondo" solo puede salir
del montaje. Variedades elegidas y excluidas: ver `scripts/preparar_fruits360.py`.

Para regenerar la parte de Fruits-360 (descarga solo nuestras frutas, ~150 MB):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/fruits-360/fruits-360-100x100.git /tmp/f360
.venv/bin/python scripts/preparar_fruits360.py --repo /tmp/f360 --imprimir-patrones | git -C /tmp/f360 sparse-checkout set --no-cone --stdin
.venv/bin/python scripts/preparar_fruits360.py --repo /tmp/f360 --por-clase 150
```

Esas fotos se llaman `<clase>.f360-*.jpg`; las propias, `<clase>.<n>.jpg`. Así se
pueden contar o quitar por separado (p. ej. para comparar en el documento un modelo
solo con Fruits-360 contra el mixto).

### Capturar las fotos propias con la webcam

```bash
.venv/bin/python simulador/capturar_dataset.py
```

- Fondo y luz fijos (cartulina blanca + lámpara), la fruta dentro del cuadrado.
- `1..6` guarda una foto de esa clase; `r` activa la ráfaga (una foto cada 0,4 s)
  mientras giras y mueves la fruta.
- Meta: 30–50 fotos por fruta y ~100 de "fondo" (sin fruta, con la mano, sombras…).
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
