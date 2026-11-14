# FruitAI

Inventario de frutas con TinyML (ESP32-S3), Home Assistant, SQLite y un agente local (Ollama).
Documento del proyecto: `ProyectoFrutIA.docx`. Plan: v4.

## Estructura

```
docker-compose.yml       HA + Mosquitto + servicio (+ Ollama con --profile ollama)
mosquitto/config/        mosquitto.conf (passwd se genera, no se versiona)
servicio/                Python: MQTT → SQLite → stock/resúmenes → HA (discovery)
  tests/                 pruebas (pytest), no necesitan broker
simulador/               simula el ESP32 publicando los mismos mensajes MQTT
homeassistant/           configuration.yaml y automations.yaml (el resto lo crea HA)
scripts/                 utilidades (usuarios MQTT)
firmware/fruitai_camara/  ESP32-S3: cámara + TinyML + botones + MQTT (firmware principal)
firmware/esp32_ambiente/  ESP32: solo sensor DHT (prueba)
bitacora.md              bitácora diaria
```

## Arranque (Mac, PC con Linux o Raspberry Pi)

```bash
cp .env.example .env                 # y cambiar las claves
./scripts/crear_usuarios_mqtt.sh
docker compose up -d --build
```

Home Assistant: http://localhost:8123 (o la IP del equipo).
1. Crear el usuario (onboarding).
2. Ajustes → Dispositivos y servicios → Agregar → **MQTT**: broker `mosquitto`, puerto `1883`,
   usuario/clave `MQTT_USUARIO_HA` / `MQTT_CLAVE_HA` del `.env`.
3. Aparece el dispositivo **FruitAI** con los sensores "Stock manzana", "Salidas hoy banano", etc.

Guía completa (materiales, estación, Raspberry Pi, app, agente y ESP32): [docs/puesta_en_marcha.md](docs/puesta_en_marcha.md).

Respaldo y restauración en la Raspberry Pi (sin copiar la SD completa): [docs/restaurar.md](docs/restaurar.md).

## Simular el ESP32

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python simulador/simular_esp32.py movimiento manzana entrada --cantidad 3
.venv/bin/python simulador/simular_esp32.py movimiento banano salida     # stock 0 → aviso
.venv/bin/python simulador/simular_esp32.py ambiente 23.4 61
.venv/bin/python simulador/simular_esp32.py demo --eventos 20
.venv/bin/python simulador/simular_esp32.py escuchar --segundos 5
```

## Pruebas

```bash
.venv/bin/python -m pytest -q servicio/tests simulador/tests
```

## ESP32-S3 virtual (cámara del Mac)

Mientras no hay hardware: capturar el dataset con la webcam, entrenar en Edge Impulse y
correr el modelo con la misma lógica anti-duplicados y los mismos mensajes MQTT que el
firmware. Ver [docs/esp32_virtual.md](docs/esp32_virtual.md).

```bash
.venv/bin/pip install -r requirements-camara.txt
.venv/bin/python simulador/capturar_dataset.py
.venv/bin/python simulador/esp32_virtual.py --modelo modelos/fruitai.tflite
```

## Firmware del ESP32-S3

`firmware/fruitai_camara/`: cámara → modelo de Edge Impulse → confirmación → botones →
MQTT, con la misma lógica y los mismos mensajes que el ESP32 virtual. Conexiones, compilación
y ajustes: [firmware/fruitai_camara/README.md](firmware/fruitai_camara/README.md).

```bash
./scripts/probar_firmware.sh        # pruebas de la lógica anti-duplicados en C++ (sin hardware)
```

## Contrato MQTT (lo que el firmware debe respetar)

`fruitai/movimiento` (QoS 1, sin retain):
```json
{"fruta": "manzana", "tipo": "entrada", "cantidad": 1, "confianza": 0.91, "evento_id": "a1b2c3"}
```
- `fruta`: una de `FRUTAS` (.env). Si el modelo tiene clases `manzana_roja`/`manzana_verde`,
  el firmware las traduce a `manzana`.
- `evento_id`: único por evento. Con QoS 1 un mensaje puede llegar dos veces; el servicio
  ignora el repetido.
- La hora la pone el servicio al recibir (el ESP32 no tiene reloj confiable).

`fruitai/ambiente` (retain): `{"temperatura": 24.5, "humedad": 60}`

## Base de datos

`data/fruitai.db`. Ver contenido:
```bash
sqlite3 data/fruitai.db "SELECT * FROM movimientos ORDER BY id DESC LIMIT 10;"
```
