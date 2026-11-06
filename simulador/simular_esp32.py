"""Simulador del ESP32-S3: publica en MQTT los mismos mensajes que publicará el firmware.

Sirve mientras no hay hardware (plan v4, días 2–4) y después para pruebas.

  python simulador/simular_esp32.py movimiento manzana entrada
  python simulador/simular_esp32.py movimiento banano salida --cantidad 2
  python simulador/simular_esp32.py ambiente 24.5 60
  python simulador/simular_esp32.py demo --eventos 20
  python simulador/simular_esp32.py escuchar          # ver todo lo que pasa en fruitai/#
"""
from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt

RAIZ = Path(__file__).resolve().parent.parent


def leer_env() -> dict[str, str]:
    env = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def conectar(args) -> mqtt.Client:
    env = leer_env()
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-esp32-{uuid.uuid4().hex[:6]}")
    c.username_pw_set(env.get("MQTT_USUARIO_ESP32", "esp32"), env.get("MQTT_CLAVE_ESP32"))
    c.connect(args.host, args.port)
    c.loop_start()
    return c


def publicar(c: mqtt.Client, topico: str, datos: dict, retain=False) -> None:
    texto = json.dumps(datos, ensure_ascii=False)
    c.publish(topico, texto, qos=1, retain=retain).wait_for_publish(5)
    print(f"→ {topico}  {texto}")


def movimiento(fruta, tipo, cantidad=1, confianza=None) -> dict:
    return {
        "fruta": fruta,
        "tipo": tipo,
        "cantidad": cantidad,
        "confianza": round(confianza if confianza is not None else random.uniform(0.80, 0.99), 2),
        "evento_id": uuid.uuid4().hex[:12],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("movimiento")
    m.add_argument("fruta")
    m.add_argument("tipo", choices=["entrada", "salida"])
    m.add_argument("--cantidad", type=int, default=1)
    m.add_argument("--confianza", type=float)

    a = sub.add_parser("ambiente")
    a.add_argument("temperatura", type=float)
    a.add_argument("humedad", type=float)

    d = sub.add_parser("demo")
    d.add_argument("--eventos", type=int, default=15)
    d.add_argument("--pausa", type=float, default=1.0)
    d.add_argument("--frutas", default=leer_env().get("FRUTAS", "manzana,pera,banano,kiwi"))

    e = sub.add_parser("escuchar")
    e.add_argument("--segundos", type=float, default=0, help="0 = hasta Ctrl+C")
    args = ap.parse_args()

    c = conectar(args)
    if args.cmd == "movimiento":
        publicar(c, "fruitai/movimiento", movimiento(args.fruta, args.tipo, args.cantidad, args.confianza))
    elif args.cmd == "ambiente":
        publicar(c, "fruitai/ambiente", {"temperatura": args.temperatura, "humedad": args.humedad}, retain=True)
    elif args.cmd == "demo":
        frutas = args.frutas.split(",")
        for _ in range(args.eventos):
            # 65 % entradas para que el stock suba; algunas salidas serán
            # rechazadas a propósito (stock 0) para probar los avisos.
            tipo = "entrada" if random.random() < 0.65 else "salida"
            publicar(c, "fruitai/movimiento", movimiento(random.choice(frutas), tipo))
            time.sleep(args.pausa)
        publicar(c, "fruitai/ambiente",
                 {"temperatura": round(random.uniform(18, 28), 1), "humedad": round(random.uniform(45, 75))},
                 retain=True)
    elif args.cmd == "escuchar":
        c.on_message = lambda _c, _u, msg: print(f"{msg.topic}{' (retain)' if msg.retain else ''}  {msg.payload.decode(errors='replace')}")
        c.subscribe([("fruitai/#", 1)])
        print("Escuchando fruitai/# (Ctrl+C para salir)…")
        fin = time.time() + args.segundos if args.segundos else float("inf")
        try:
            while time.time() < fin:
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


if __name__ == "__main__":
    main()
