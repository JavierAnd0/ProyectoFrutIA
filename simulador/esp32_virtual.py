"""ESP32-S3 virtual: la cámara del Mac hace de cámara del ESP32 (mientras llega el hardware).

Reproduce el ciclo completo del firmware:
  cámara → modelo TinyML → confirmación anti-duplicados → botón → MQTT → servicio → HA

  # con el modelo exportado de Edge Impulse (TFLite int8)
  .venv/bin/python simulador/esp32_virtual.py --modelo modelos/fruitai.tflite --etiquetas modelos/etiquetas.txt

  # sin modelo todavía: tú "le dices" al clasificador qué ve, con números
  .venv/bin/python simulador/esp32_virtual.py

Teclas (equivalen al hardware):
  e / s   botón ENTRADA / SALIDA
  p       sensor de presencia on/off
  1..9    (sin modelo) la cámara "ve" la clase n;  0 = fondo
  q       salir

La lógica de confirmación es la de confirmacion.py, la misma que llevará el
firmware. La consola muestra lo que el ESP32 escribiría por el puerto serie.
"""
from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from pathlib import Path

import cv2

from camara import CAMARA_POR_DEFECTO, ClasificadorTFLite, abrir_camara, leer_etiquetas, listar_camaras, recorte_central
from confirmacion import CONFIRMADA, REGISTRADA, Confirmador

RAIZ = Path(__file__).resolve().parent.parent
T_MOVIMIENTO = "fruitai/movimiento"
T_ESTADO = "fruitai/esp32/estado"
T_AVISO = "fruitai/aviso"
CLASES = "manzana_roja,manzana_verde,pera,banano,kiwi,fondo"
COLOR_LED = {CONFIRMADA: (0, 200, 0), REGISTRADA: (255, 120, 0)}   # BGR


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


def serial(texto: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {texto}", flush=True)


class Mqtt:
    def __init__(self, host: str, port: int):
        import paho.mqtt.client as mqtt

        env = leer_env()
        self.avisos: list[str] = []
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"esp32-virtual-{uuid.uuid4().hex[:6]}")
        self.c.username_pw_set(env.get("MQTT_USUARIO_ESP32", "esp32"), env.get("MQTT_CLAVE_ESP32"))
        self.c.will_set(T_ESTADO, "offline", qos=1, retain=True)
        self.c.on_connect = self._conectado
        self.c.on_message = lambda _c, _u, msg: self.avisos.append(msg.payload.decode(errors="replace"))
        try:
            self.c.connect(host, port)
        except OSError as e:
            raise SystemExit(f"No hay broker en {host}:{port} ({e}). ¿Está corriendo `docker compose up -d`? "
                             "O usa --sin-mqtt.")
        self.c.loop_start()

    def _conectado(self, c, _u, _f, codigo, _p):
        if codigo.is_failure:
            serial(f"MQTT rechazó la conexión: {codigo} (revisa MQTT_USUARIO_ESP32/MQTT_CLAVE_ESP32 en .env)")
            return
        serial("MQTT conectado")
        c.publish(T_ESTADO, "online", qos=1, retain=True)
        c.subscribe(T_AVISO, qos=1)

    def publicar_movimiento(self, datos: dict) -> None:
        self.c.publish(T_MOVIMIENTO, json.dumps(datos, ensure_ascii=False), qos=1)

    def cerrar(self) -> None:
        self.c.publish(T_ESTADO, "offline", qos=1, retain=True).wait_for_publish(2)
        self.c.loop_stop()
        self.c.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", type=Path, help=".tflite exportado de Edge Impulse")
    ap.add_argument("--etiquetas", type=Path, help="una clase por línea, en el orden del modelo")
    ap.add_argument("--clases", default=CLASES, help="clases del modo sin modelo")
    ap.add_argument("--camara", default=CAMARA_POR_DEFECTO,
                    help="índice de cámara o ruta a un video (o variable FRUITAI_CAMARA)")
    ap.add_argument("--listar-camaras", action="store_true", help="ver qué número tiene cada cámara y salir")
    ap.add_argument("--fps", type=float, default=5, help="inferencias por segundo (un ESP32-S3 hace ~5)")
    ap.add_argument("--umbral", type=float, default=0.75)
    ap.add_argument("--frames", type=int, default=5, help="fotogramas seguidos para confirmar")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--sin-mqtt", action="store_true", help="no publicar, solo mostrar")
    args = ap.parse_args()
    if args.listar_camaras:
        listar_camaras()
        return

    if args.modelo:
        etiquetas = leer_etiquetas(args.etiquetas or args.modelo.with_name("etiquetas.txt"))
        clasificador = ClasificadorTFLite(args.modelo, etiquetas)
        serial(f"Modelo {args.modelo.name}: entrada {clasificador.ancho}x{clasificador.alto}x{clasificador.canales}, "
               f"{clasificador.ent['dtype'].__name__}, clases {etiquetas}")
        clases_manual = []
    else:
        clasificador = None
        clases_manual = [c.strip() for c in args.clases.split(",") if c.strip() and c.strip() != "fondo"][:9]
        serial("Sin modelo: pulsa 1..9 para simular lo que ve la cámara (0 = fondo): "
               + ", ".join(f"{i + 1}={c}" for i, c in enumerate(clases_manual)))

    conf = Confirmador(umbral=args.umbral, frames_confirmar=args.frames, frames_retiro=args.frames)
    cap = abrir_camara(args.camara)   # antes que MQTT: si no hay cámara, no se anuncia "online"
    mqtt = None if args.sin_mqtt else Mqtt(args.host, args.port)

    presencia, manual = True, "fondo"
    etiqueta, confianza = "fondo", 1.0
    periodo, ultima_inf, ms_inf = 1.0 / args.fps, 0.0, 0.0
    estado_previo, mensaje, mensaje_hasta = conf.estado, "", 0.0

    def mostrar(texto: str, segundos: float = 3.0) -> None:
        nonlocal mensaje, mensaje_hasta
        mensaje, mensaje_hasta = texto, time.time() + segundos
        serial(texto)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cuadrado, (x, y, lado) = recorte_central(frame)
            ahora = time.time()

            # ---- una inferencia cada 1/fps segundos, como en el ESP32 ----
            if ahora - ultima_inf >= periodo:
                ultima_inf = ahora
                t0 = time.perf_counter()
                if clasificador:
                    etiqueta, confianza, _ = clasificador.clasificar(cuadrado)
                else:
                    etiqueta = manual
                    confianza = 1.0 if manual == "fondo" else random.uniform(0.80, 0.97)
                ms_inf = (time.perf_counter() - t0) * 1000
                conf.procesar(etiqueta, confianza, presencia)
                if conf.estado != estado_previo:
                    mostrar(conf.mensaje)
                    estado_previo = conf.estado

            # ---- teclado = botones / sensores ----
            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                break
            if tecla in (ord("e"), ord("s")):
                tipo = "entrada" if tecla == ord("e") else "salida"
                mov = conf.boton(tipo)
                mostrar(conf.mensaje)
                estado_previo = conf.estado
                if mov:
                    datos = {"fruta": mov.fruta, "tipo": mov.tipo, "cantidad": 1,
                             "confianza": mov.confianza, "evento_id": f"virt-{uuid.uuid4().hex[:12]}"}
                    if mqtt:
                        mqtt.publicar_movimiento(datos)
                        serial(f"→ {T_MOVIMIENTO} {json.dumps(datos, ensure_ascii=False)}")
            elif tecla == ord("p"):
                presencia = not presencia
                mostrar(f"Presencia {'detectada' if presencia else 'NO detectada'}")
            elif not clasificador and tecla == ord("0"):
                manual = "fondo"
            elif not clasificador and ord("1") <= tecla <= ord("9") and tecla - ord("1") < len(clases_manual):
                manual = clases_manual[tecla - ord("1")]

            if mqtt and mqtt.avisos:
                mostrar(f"Aviso del servicio: {mqtt.avisos.pop(0)}", 5)

            # ---- pantalla ----
            vista = frame.copy()
            cv2.rectangle(vista, (x, y), (x + lado, y + lado), (255, 255, 255), 2)
            led = COLOR_LED.get(conf.estado, (90, 90, 90))
            cv2.circle(vista, (vista.shape[1] - 35, 35), 20, led, -1)
            lineas = [
                f"Ve: {etiqueta} {confianza:.0%}  ({ms_inf:.0f} ms)",
                f"Estado: {conf.estado}" + (f" - {conf.fruta}" if conf.fruta else ""),
                f"Presencia: {'si' if presencia else 'no'}   MQTT: {'si' if mqtt else 'no'}",
            ]
            for i, t in enumerate(lineas):
                cv2.putText(vista, t, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            ayuda = "e entrada | s salida | p presencia | q salir" + ("" if clasificador else " | 1-9/0 fruta")
            cv2.putText(vista, ayuda, (10, vista.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
            if ahora < mensaje_hasta:
                cv2.putText(vista, mensaje, (10, vista.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow("FruitAI - ESP32 virtual", vista)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if mqtt:
            mqtt.cerrar()


if __name__ == "__main__":
    main()
