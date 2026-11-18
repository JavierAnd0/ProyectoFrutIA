"""Guarda como dataset las fotos que el ESP32-S3 manda por MQTT (fruitai/esp32/foto).

Sirve para recapturar el conjunto de datos con la cámara REAL del ESP32 (la OV2640 ve
distinto a la webcam), sin tocar el firmware: con PUBLICAR_FOTO 1 el ESP32 ya manda ~2
fotos por segundo.

  # una clase a la vez: pon la fruta bajo la cámara y muévela/gírala mientras guarda
  python scripts/capturar_desde_esp32.py banano --fotos 50
  python scripts/capturar_desde_esp32.py fondo --fotos 100

Las fotos quedan en dataset_esp32/<clase>/<clase>.esp32-<n>.jpg; Edge Impulse toma la
etiqueta de lo que va antes del primer punto ("Infer from filename").
Broker y credenciales: --host (IP de la Raspberry) y el usuario de Home Assistant del .env.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import paho.mqtt.client as mqtt

RAIZ = Path(__file__).resolve().parent.parent
CLASES = ["banano", "fondo", "kiwi", "manzana_roja", "manzana_verde", "pera"]


def leer_env() -> dict[str, str]:
    env = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clase", choices=CLASES)
    ap.add_argument("--fotos", type=int, default=50, help="cuántas fotos guardar")
    ap.add_argument("--cada", type=float, default=0.5, help="segundos mínimos entre fotos guardadas")
    ap.add_argument("--host", default="localhost", help="IP de la Raspberry (broker MQTT)")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--salida", type=Path, default=RAIZ / "dataset_esp32")
    args = ap.parse_args()

    carpeta = args.salida / args.clase
    carpeta.mkdir(parents=True, exist_ok=True)
    env = leer_env()
    estado = {"n": len(list(carpeta.glob("*.jpg"))), "guardadas": 0, "ultima": 0.0}

    def al_recibir(_c, _u, msg):
        ahora = time.time()
        if ahora - estado["ultima"] < args.cada or msg.payload[:2] != b"\xff\xd8":   # solo JPEG
            return
        estado["ultima"] = ahora
        estado["n"] += 1
        estado["guardadas"] += 1
        (carpeta / f"{args.clase}.esp32-{estado['n']}.jpg").write_bytes(msg.payload)
        print(f"\r{args.clase}: {estado['guardadas']}/{args.fotos}", end="", flush=True)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fruitai-captura-{int(time.time())}")
    c.username_pw_set(env.get("MQTT_USUARIO_HA", "homeassistant"), env.get("MQTT_CLAVE_HA"))
    c.on_message = al_recibir
    c.on_connect = lambda cl, _u, _f, rc, _p: cl.subscribe("fruitai/esp32/foto") if not rc.is_failure else print(f"MQTT rechazó: {rc}")
    c.connect(args.host, args.port)
    c.loop_start()
    print(f"Guardando {args.fotos} fotos de «{args.clase}» en {carpeta} (Ctrl+C para parar)…")
    inicio = time.time()
    try:
        while estado["guardadas"] < args.fotos:
            time.sleep(0.2)
            if estado["guardadas"] == 0 and time.time() - inicio > 15:
                raise SystemExit("\nNo llegan fotos: ¿ESP32 conectado y con PUBLICAR_FOTO 1? ¿--host es la IP de la Pi?")
    except KeyboardInterrupt:
        pass
    c.loop_stop()
    c.disconnect()
    print(f"\nListo: {estado['guardadas']} fotos en {carpeta}")


if __name__ == "__main__":
    main()
