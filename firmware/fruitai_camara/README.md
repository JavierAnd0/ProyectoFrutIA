# Firmware principal: ESP32-S3 con cámara

```
cámara OV2640 ─► modelo TinyML ─► confirmación anti-duplicados ─► Entrada/Salida (panel de HA) ─► MQTT ─► Pi
```

Hace lo mismo que `simulador/esp32_virtual.py` y publica los mismos mensajes
(`fruitai/movimiento`, `fruitai/esp32/estado`, opcionalmente `fruitai/ambiente`).
Si funcionaba con el ESP32 virtual, funciona igual con este firmware: el servicio,
SQLite y Home Assistant no cambian.

| Archivo | Qué es |
|---|---|
| `fruitai_camara.ino` | cámara, inferencia, LED, Wi-Fi y MQTT (pulsadores, PIR y DHT22 opcionales) |
| `confirmacion.h` | lógica anti-duplicados, traducida línea por línea de `simulador/confirmacion.py` |
| `test/test_confirmacion.cpp` | las mismas pruebas que la versión Python, se corren en el PC |
| `secrets.h.example` | plantilla de Wi-Fi y MQTT (copiar como `secrets.h`, no va a git) |


## Alcance actual: solo el ESP32 con cámara

Por ahora no hay estación física: el ESP32-S3 solo necesita la cámara y el cable USB, y
**todo se opera desde Home Assistant** (la cámara en el panel, "Fruta detectada" y los
botones Entrada / Salida). Configuración por defecto del `.ino`:

| Opción | Valor | Significado |
|---|---|---|
| `PUBLICAR_FOTO` | 1 | manda ~2 fotos/s al panel de HA |
| `USAR_BOTONES` | 0 | sin pulsadores físicos |
| `USAR_PIR` | 0 | cámara siempre activa |
| `USAR_DHT` | 0 | sin sensor de ambiente |

Las secciones de conexiones y sensor de presencia de abajo son para la **estación física**,
que quedó como mejora futura ([docs/mejoras_futuras.md](../../docs/mejoras_futuras.md)).

## Placas soportadas

Se elige con un `#define` al inicio del `.ino`:

- `PLACA_FREENOVE_S3`: Freenove ESP32-S3 WROOM CAM y clones "ESP32-S3-EYE" (N8R8/N16R8).
- `PLACA_XIAO_S3`: Seeed XIAO ESP32S3 Sense.

Otra placa: copiar sus pines de cámara del ejemplo `CameraWebServer` (`camera_pins.h`).

## Conexiones (estación física, mejora futura)

| Pieza | Freenove S3 | XIAO S3 Sense | Notas |
|---|---|---|---|
| Botón ENTRADA | GPIO14 | D0 (GPIO1) | entre el pin y GND (usa la resistencia interna) |
| Botón SALIDA | GPIO21 | D1 (GPIO2) | entre el pin y GND |
| PIR (HC-SR501 / AM312) | GPIO1 | D2 (GPIO3) | OUT al pin; AM312 a 3,3 V, HC-SR501 a 5 V (su salida es de 3,3 V) |
| DHT22 (opcional) | GPIO47 | D3 (GPIO4) | `USAR_DHT 1`; resistencia de 10 kΩ entre DATA y 3,3 V si el módulo no la trae |
| LED | GPIO2 (de la placa) | GPIO21 (de la placa) | |

LED: **apagado** = esperando fruta · **fijo** = fruta confirmada, pulsa un botón ·
**parpadeo lento** = registrada, retira la fruta · **2 destellos** = pulsación ignorada ·
**3 destellos** = el servicio rechazó el movimiento (p. ej. salida con stock 0) ·
**parpadeo de 1 s sin parar** = falla la cámara o la PSRAM.

## Sensor de presencia (mejora futura)

El PIR solo **activa** la cámara (el plan: "sensor de presencia para activar la
detección"). Sin movimiento durante `PRESENCIA_MS` (15 s) la cámara descansa y el
estado se congela. La falta de presencia **no** se toma como "fruta retirada": un
PIR deja de detectar una fruta quieta, y si eso rearmara el sistema se podría
registrar la misma fruta dos veces. El retiro lo decide la cámara al ver `fondo`
durante `FRAMES_RETIRO` fotogramas. Sin PIR: `USAR_PIR 0`.

## Compilar y cargar

1. **Arduino IDE 2** → Gestor de placas → **esp32** de Espressif (3.x).
2. Gestor de librerías → **PubSubClient** (Nick O'Leary). Con `USAR_DHT 1`, también
   **DHT sensor library** (Adafruit).
3. **Edge Impulse** → *Deployment* → **Arduino library** → *Build* (con el
   optimizador EON y la versión int8). En el IDE: *Sketch → Include Library →
   Add .ZIP Library…*.
4. En el `.ino`, cambiar `#include <fruitai_inferencing.h>` por el nombre de la
   librería descargada (`<nombre-del-proyecto>_inferencing.h`).
5. `cp secrets.h.example secrets.h` y completar Wi-Fi (2,4 GHz) y la IP de la Pi.
   Usuario y clave MQTT: `MQTT_USUARIO_ESP32` / `MQTT_CLAVE_ESP32` del `.env`.
6. Herramientas: placa **ESP32S3 Dev Module** (Freenove) o **XIAO_ESP32S3**;
   **PSRAM: OPI PSRAM**; **Partition scheme: Huge APP (3MB No OTA)**.
7. Cargar y abrir el monitor serie a 115200.

La primera compilación de la librería de Edge Impulse tarda varios minutos; es normal.

Salida esperada en el monitor serie:

```
== FruitAI ESP32-S3: cámara + TinyML ==
Modelo: 96x96, 6 clases: banano fondo kiwi manzana_roja manzana_verde pera
Wi-Fi OK (192.168.1.50, -58 dBm). MQTT 192.168.1.20:1883 como esp32... OK
Presencia: cámara activa
ve: pera 93% (142 ms) | ESPERANDO
pera confirmada (91%). Pulsa entrada o salida
Registrado: entrada de pera
→ fruitai/movimiento {"fruta": "pera", "tipo": "entrada", "cantidad": 1, "confianza": 0.91, "evento_id": "cam-1a2b3c4d-1"}
```

Los milisegundos de `ve:` son la latencia de captura + inferencia en el ESP32
(sección de pruebas del documento).

## Ajustes

| Constante | Por defecto | Para qué |
|---|---|---|
| `UMBRAL` | 0.75 | confianza mínima; súbela si confirma frutas que no son |
| `FRAMES_CONFIRMAR` | 5 | fotogramas seguidos para confirmar (~1 s a 5 inf/s) |
| `FRAMES_RETIRO` | 5 | fotogramas de `fondo` para rearmar |
| `PERIODO_INF_MS` | 200 | intervalo entre inferencias |

Son los mismos parámetros que `--umbral` y `--frames` del ESP32 virtual: los
valores que funcionaron allí son un buen punto de partida.

## Registrar desde Home Assistant y ver la cámara

- El panel FruitAI tiene **Entrada / Salida** que registran la fruta que confirmó el ESP32:
  llegan por `fruitai/esp32/boton` y pasan por la misma lógica que los botones físicos. Si la
  pulsación se ignora (sin fruta confirmada o ya registrada), el motivo llega al celular.
- El ESP32 informa lo que ve en `fruitai/esp32/deteccion` (sensor "Fruta detectada").
- `PUBLICAR_FOTO 1` manda 2 fotos por segundo (`PERIODO_FOTO_MS`) (el JPEG de la cámara, unos 10 KB) para verla
  en el panel. Por defecto está apagado: así ninguna imagen sale del ESP32.

## Si se cae la red

PubSubClient publica con QoS 0. Para no perder un registro, cada movimiento se
guarda en una cola (8 como máximo) y se envía cuando hay conexión. Si llega dos
veces, el servicio descarta el repetido por `evento_id`. Mientras tanto el ESP32
sigue clasificando y aceptando botones.

## Probar la lógica sin hardware

```bash
./scripts/probar_firmware.sh        # 24/24 comprobaciones OK
```

## Importante: reentrenar con la cámara del ESP32

El modelo entrenado con Fruits-360 y la webcam sirve para arrancar, pero la OV2640
tiene otro color y nitidez. Con la placa montada, captura 30–50 fotos por fruta y
unas 100 de `fondo` con **esta** cámara (Edge Impulse → *Data acquisition*, o el
ejemplo `CameraWebServer` para tomar fotos), súbelas y reentrena (plan v4, sección 5).
